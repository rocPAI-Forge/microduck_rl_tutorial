"""Helpers for the one-hour MicroDuck Jupyter lab."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
from IPython.display import Video, display
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


DEFAULT_MICRODUCK_ROOT = Path(os.environ.get("MICRODUCK_ROOT", "/opt/microduck_rl_unilab"))
DEFAULT_LOG_ROOT = Path(os.environ.get("LAB_LOG_ROOT", "/workspace/runs"))

OVERVIEW_TAGS = (
    "Train/mean_reward",
    "Train/mean_episode_length",
    "Loss/value_function",
    "Loss/surrogate",
    "Policy/mean_noise_std",
)


@dataclass(frozen=True)
class TrainJob:
    task: str
    task_name: str
    sim: str = "mujoco"
    algo: str = "ppo"
    num_envs: int = 512
    max_iterations: int = 2000
    save_interval: int = 200
    run_name: str = ""
    extra_overrides: tuple[str, ...] = ()


def microduck_root() -> Path:
    root = DEFAULT_MICRODUCK_ROOT
    if not root.is_dir():
        raise FileNotFoundError(
            f"MicroDuck task repo not found at {root}. "
            "Set MICRODUCK_ROOT or rebuild the lab image."
        )
    return root


def log_root() -> Path:
    path = DEFAULT_LOG_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_environment() -> dict[str, Any]:
    import torch
    import unilab
    import uni_rl
    import unisim

    hip = getattr(getattr(torch, "version", None), "hip", None)
    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torch_cuda_available": bool(torch.cuda.is_available()),
        "torch_hip": hip,
        "unilab": unilab.__version__,
        "unilab_rl": uni_rl.__version__,
        "unisim_core": unisim.__version__,
        "microduck_root": str(microduck_root()),
        "mujoco_gl": os.environ.get("MUJOCO_GL"),
        "device_note": "training configs still use cuda semantics on ROCm",
    }


def _train_command(job: TrainJob) -> list[str]:
    overrides = [
        f"algo.num_envs={job.num_envs}",
        f"algo.max_iterations={job.max_iterations}",
        f"algo.save_interval={job.save_interval}",
        "training.no_play=true",
        "training.logger=tensorboard",
        f"training.log_root={log_root()}",
    ]
    if job.run_name:
        overrides.append(f"algo.run_name={job.run_name}")
    overrides.extend(job.extra_overrides)
    return [
        "microduck-train",
        "--algo",
        job.algo,
        "--task",
        job.task,
        "--sim",
        job.sim,
        *overrides,
    ]


def run_train(job: TrainJob, *, dry_run: bool = False) -> subprocess.CompletedProcess[str] | list[str]:
    env = os.environ.copy()
    env.setdefault("UNILAB_EXTRA_REGISTRY_PACKAGES", "microduck_rl_unilab.tasks")
    env.setdefault("MUJOCO_GL", "osmesa")
    env.setdefault("PYOPENGL_PLATFORM", "osmesa")
    command = _train_command(job)
    if dry_run:
        return command
    return subprocess.run(
        command,
        cwd=microduck_root(),
        env=env,
        check=True,
        text=True,
        capture_output=False,
    )


def _candidate_run_dirs(job: TrainJob) -> list[Path]:
    base = log_root() / job.task_name
    if not base.is_dir():
        return []
    runs = sorted(base.glob("*_mujoco"), key=lambda path: path.stat().st_mtime)
    if job.run_name:
        runs = [path for path in runs if job.run_name in path.name]
    return runs


def latest_run_dir(job: TrainJob) -> Path:
    runs = _candidate_run_dirs(job)
    if not runs:
        raise FileNotFoundError(
            f"No run directories found under {log_root() / job.task_name}"
        )
    return runs[-1]


def latest_checkpoint(run_dir: Path) -> Path:
    checkpoints = sorted(run_dir.glob("model_*.pt"), key=_checkpoint_iteration)
    if not checkpoints:
        raise FileNotFoundError(f"No checkpoints found in {run_dir}")
    return checkpoints[-1]


def _checkpoint_iteration(path: Path) -> int:
    match = re.search(r"model_(\d+)\.pt$", path.name)
    return int(match.group(1)) if match else -1


def load_scalar_curves(run_dir: Path, tags: Iterable[str] = OVERVIEW_TAGS) -> dict[str, list[tuple[int, float]]]:
    accumulator = EventAccumulator(str(run_dir), size_guidance={"scalars": 0})
    accumulator.Reload()
    curves: dict[str, list[tuple[int, float]]] = {}
    for tag in tags:
        if tag not in accumulator.Tags().get("scalars", []):
            continue
        curves[tag] = [
            (int(event.step), float(event.value))
            for event in accumulator.Scalars(tag)
        ]
    return curves


def plot_training_curves(
    run_dir: Path,
    *,
    title: str,
    tags: Iterable[str] = OVERVIEW_TAGS,
) -> plt.Figure:
    curves = load_scalar_curves(run_dir, tags=tags)
    if not curves:
        raise RuntimeError(f"No scalar curves found in {run_dir}")

    fig, axes = plt.subplots(len(curves), 1, figsize=(9, 2.6 * len(curves)), sharex=True)
    if len(curves) == 1:
        axes = [axes]
    for axis, (tag, series) in zip(axes, curves.items()):
        steps = [step for step, _ in series]
        values = [value for _, value in series]
        axis.plot(steps, values, linewidth=1.5)
        axis.set_title(tag)
        axis.grid(True, alpha=0.3)
    axes[-1].set_xlabel("iteration")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    return fig


def render_playback(
    *,
    task: str,
    run_dir: Path,
    checkpoint: Path | None = None,
    play_steps: int = 500,
    speed: float | None = None,
    extra_overrides: Iterable[str] = (),
) -> Path:
    ckpt = checkpoint or latest_checkpoint(run_dir)
    iteration = _checkpoint_iteration(ckpt)
    overrides = [
        f"algo.load_run={run_dir}",
        f"algo.checkpoint={iteration}",
        "algo.num_envs=1",
        f"training.play_steps={play_steps}",
        "training.cam_tracking=true",
        "training.cam_tracking_extra_envs=0",
        "training.cam_azimuth=135",
        "training.cam_elevation=-15",
    ]
    if speed is not None:
        overrides.append(f"env.commands.twist.ranges.lin_vel_x=[{speed},{speed}]")
        overrides.append("env.commands.twist.ranges.lin_vel_y=[0.0,0.0]")
        overrides.append("env.commands.twist.ranges.ang_vel_z=[0.0,0.0]")
    overrides.extend(extra_overrides)

    env = os.environ.copy()
    env.setdefault("UNILAB_EXTRA_REGISTRY_PACKAGES", "microduck_rl_unilab.tasks")
    env.setdefault("MUJOCO_GL", "osmesa")
    env.setdefault("PYOPENGL_PLATFORM", "osmesa")

    subprocess.run(
        [
            "microduck-eval",
            "--algo",
            "ppo",
            "--task",
            task,
            "--sim",
            "mujoco",
            *overrides,
        ],
        cwd=microduck_root(),
        env=env,
        check=True,
    )
    video = run_dir / "play_video.mp4"
    if not video.is_file():
        raise FileNotFoundError(f"Expected playback video at {video}")
    return video


def show_video(path: Path, *, width: int = 720) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    display(Video(str(path), embed=True, width=width))


def load_metrics_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
