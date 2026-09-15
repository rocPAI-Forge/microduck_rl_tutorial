#!/usr/bin/env python3
"""Evaluate a MicroDuck policy on fixed body-frame velocity commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

from unilab.base.config_adapter import create_env
from unilab.scripts import play_interactive


def _commands(linear_speed: float, yaw_rate: float) -> dict[str, tuple[float, ...]]:
    return {
        "forward": (linear_speed, 0.0, 0.0),
        "backward": (-linear_speed, 0.0, 0.0),
        "left": (0.0, linear_speed, 0.0),
        "right": (0.0, -linear_speed, 0.0),
        "yaw_left": (0.0, 0.0, yaw_rate),
        "yaw_right": (0.0, 0.0, -yaw_rate),
    }


def _as_numpy(value: Any) -> np.ndarray:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def _compose_config(checkpoint: Path, seed: int):
    root = Path(os.environ.get("MICRODUCK_ROOT", "/opt/microduck_rl_unilab"))
    parsed = play_interactive._parse_interactive_cli(
        [
            "--algo",
            "ppo",
            "--task",
            "microduck_velocity_flat",
            "--sim",
            "mujoco",
            f"hydra.searchpath=[file://{root}/src/microduck_rl_unilab/conf/ppo]",
            f"algo.load_run={checkpoint.parent}",
            f"algo.checkpoint={checkpoint.name}",
            f"algo.seed={seed}",
            "training.play_only=true",
            "training.log_root=/workspace/runs",
            "interactive.action_mode=policy",
            "interactive.policy_obs_mode=actor",
        ]
    )
    cfg = play_interactive._compose_interactive_config(parsed.algo, parsed.overrides)
    return cfg, play_interactive._build_play_args(cfg, algo=parsed.algo)


def _create_session(cfg, args, num_envs: int):
    device = play_interactive._select_playback_device(cfg)
    sim_backend = str(args.sim)
    play_interactive.configure_backend_process_device(sim_backend, device)
    env_cfg_override = play_interactive.build_play_backend_adapter(
        cfg, root_dir=Path.cwd(), algo_name="ppo"
    ).build_task_env_cfg_override()

    def env_factory(count: int):
        return create_env(
            cfg,
            num_envs=count,
            env_cfg_override=env_cfg_override,
            sim_backend=sim_backend,
            task_name=args.task,
        )

    playback_cfg = play_interactive.build_playback_config(args, num_envs=num_envs)
    session, policy_obs_mode, resolved_checkpoint = (
        play_interactive.create_rsl_rl_playback_session(
            playback_cfg=playback_cfg,
            env_factory=env_factory,
            algo_config=play_interactive._algo_config_dict(cfg),
            root_dir=Path.cwd(),
            device=device,
            checkpoint_resolver=play_interactive.resolve_checkpoint,
            checkpoint_input_dim_reader=play_interactive.infer_checkpoint_actor_input_dim,
            entrypoint_log_root=play_interactive.get_entrypoint_log_root,
            wrapper_cls=play_interactive.RslRlVecEnvWrapper,
            runner_cls=play_interactive.OnPolicyRunner,
            policy_obs_dims_getter=play_interactive.get_policy_obs_dims,
            train_cfg_normalizer=play_interactive.normalize_ppo_train_cfg,
            guard_algo_name="ppo",
            log=lambda message: print(f"[cardinal-eval] {message}", flush=True),
        )
    )
    if resolved_checkpoint is None:
        raise FileNotFoundError(f"Could not resolve checkpoint {args.checkpoint}")
    return session, policy_obs_mode, resolved_checkpoint


def _freeze_term(term) -> None:
    term._resampling_time_range = (1.0e9, 1.0e9)
    term.time_left[:] = 1.0e9


def _lock_commands(env, command: np.ndarray) -> None:
    term = env.command_manager.get_term("twist")
    target = env.command_manager.get_command("twist")
    target[:] = command
    world_target = getattr(term, "vel_command_w", None)
    if isinstance(world_target, np.ndarray):
        world_target[:] = command
    _freeze_term(term)
    for name in (
        "rel_standing_envs",
        "rel_heading_envs",
        "rel_world_envs",
        "rel_forward_envs",
    ):
        if hasattr(term.cfg, name):
            setattr(term.cfg, name, 0.0)
    if hasattr(term, "_turn_fraction"):
        term._turn_fraction = 0.0
    env.state.info["commands"] = target

    # Head/body targets are independent random command terms in this task.
    # Neutralize them so checkpoint comparisons differ only by twist command,
    # reset randomization, and policy behavior.
    for name in ("head_pose", "body_pose"):
        pose_term = env.command_manager.get_term(name)
        pose_target = env.command_manager.get_command(name)
        pose_target[:] = 0.0
        _freeze_term(pose_term)


def _body_velocities(env) -> tuple[np.ndarray, np.ndarray]:
    robot_data = env.scene["robot"].data
    return (
        np.asarray(robot_data.root_link_lin_vel_b, dtype=np.float64),
        np.asarray(robot_data.root_link_ang_vel_b, dtype=np.float64),
    )


def _evaluate_command(session, name: str, command: np.ndarray, steps: int) -> dict[str, Any]:
    env = session.env
    env.set_autoreset(True)
    session.reset()
    _lock_commands(env, command)

    num_envs = int(session.num_envs)
    alive = np.ones(num_envs, dtype=bool)
    first_done = np.full(num_envs, steps, dtype=np.int64)
    component_sum = np.zeros(num_envs, dtype=np.float64)
    component_abs_error = np.zeros(num_envs, dtype=np.float64)
    drift_sum = np.zeros(num_envs, dtype=np.float64)
    sample_count = np.zeros(num_envs, dtype=np.int64)

    is_yaw = name.startswith("yaw_")
    if is_yaw:
        target_component = float(command[2])
    elif command[0] != 0.0:
        target_component = float(command[0])
    else:
        target_component = float(command[1])

    with torch.inference_mode():
        for step in range(steps):
            _lock_commands(env, command)
            actions = session._build_actions()
            session.obs, _reward, done, _info = session.wrapped_env.step(actions)
            done_np = _as_numpy(done).astype(bool).reshape(-1)

            linvel, angvel = _body_velocities(env)
            if is_yaw:
                component = angvel[:, 2]
                drift = np.linalg.norm(linvel[:, :2], axis=1)
            elif command[0] != 0.0:
                component = linvel[:, 0]
                drift = np.abs(linvel[:, 1])
            else:
                component = linvel[:, 1]
                drift = np.abs(linvel[:, 0])

            valid = alive & ~done_np
            component_sum[valid] += component[valid]
            component_abs_error[valid] += np.abs(component[valid] - target_component)
            drift_sum[valid] += drift[valid]
            sample_count[valid] += 1

            newly_done = alive & done_np
            first_done[newly_done] = step + 1
            alive[newly_done] = False

    safe_count = np.maximum(sample_count, 1)
    mean_component_per_env = component_sum / safe_count
    expected_sign = np.sign(target_component)
    sign_correct = expected_sign * mean_component_per_env > 0.02
    valid_env = sample_count > 0
    sign_accuracy = float(np.mean(sign_correct[valid_env])) if np.any(valid_env) else 0.0
    mean_abs_error = float(component_abs_error.sum() / safe_count.sum())
    mean_drift = float(drift_sum.sum() / safe_count.sum())
    survival_rate = float(np.mean(first_done == steps))
    normalized_mae = mean_abs_error / abs(target_component)

    tracking_score = max(0.0, 1.0 - normalized_mae)
    drift_score = max(0.0, 1.0 - mean_drift / 0.15)
    score = 100.0 * (
        0.40 * survival_rate
        + 0.25 * sign_accuracy
        + 0.25 * tracking_score
        + 0.10 * drift_score
    )
    return {
        "command": command.tolist(),
        "steps": steps,
        "survival_rate": survival_rate,
        "fall_rate": 1.0 - survival_rate,
        "mean_lifetime_steps": float(np.mean(first_done)),
        "mean_component_velocity": float(component_sum.sum() / safe_count.sum()),
        "mean_absolute_tracking_error": mean_abs_error,
        "normalized_tracking_mae": normalized_mae,
        "sign_accuracy": sign_accuracy,
        "mean_cross_axis_drift": mean_drift,
        "score": score,
        "passes": bool(
            survival_rate >= 0.80
            and sign_accuracy >= 0.90
            and normalized_mae <= 0.50
            and mean_drift <= 0.10
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--num-envs", type=int, default=32)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--linear-speed", type=float, default=0.2)
    parser.add_argument("--yaw-rate", type=float, default=0.4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    if not checkpoint.is_file():
        parser.error(f"checkpoint does not exist: {checkpoint}")
    if (
        args.num_envs < 1
        or args.steps < 1
        or args.linear_speed <= 0.0
        or args.yaw_rate <= 0.0
    ):
        parser.error("environment counts, steps, and command magnitudes must be positive")

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    os.chdir(os.environ.get("MICRODUCK_ROOT", "/opt/microduck_rl_unilab"))
    cfg, play_args = _compose_config(checkpoint, args.seed)
    session, obs_mode, resolved = _create_session(cfg, play_args, args.num_envs)

    results: dict[str, Any] = {}
    try:
        for name, values in _commands(args.linear_speed, args.yaw_rate).items():
            command = np.asarray(values, dtype=np.float64)
            result = _evaluate_command(session, name, command, args.steps)
            results[name] = result
            print(
                f"{name:10s} score={result['score']:5.1f} "
                f"survival={result['survival_rate']:.1%} "
                f"sign={result['sign_accuracy']:.1%} "
                f"mae={result['mean_absolute_tracking_error']:.3f}",
                flush=True,
            )
    finally:
        close = getattr(session.env, "close", None)
        if callable(close):
            close()

    scores = [float(item["score"]) for item in results.values()]
    report = {
        "checkpoint": resolved,
        "seed": args.seed,
        "num_envs": args.num_envs,
        "steps": args.steps,
        "control_frequency_hz": 50,
        "policy_obs_mode": obs_mode,
        "directions": results,
        "mean_score": float(np.mean(scores)),
        "worst_direction_score": float(np.min(scores)),
        "all_directions_pass": all(bool(item["passes"]) for item in results.values()),
    }
    output = args.output or checkpoint.with_name(f"{checkpoint.stem}_cardinal_eval.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"report={output}", flush=True)
    print(
        f"mean_score={report['mean_score']:.1f} "
        f"worst={report['worst_direction_score']:.1f} "
        f"all_pass={report['all_directions_pass']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
