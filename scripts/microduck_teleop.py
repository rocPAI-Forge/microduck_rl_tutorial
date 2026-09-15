#!/usr/bin/env python3
"""MicroDuck omnidirectional keyboard bindings for UniLab interactive playback."""

from __future__ import annotations

import numpy as np

from unilab.scripts import play_interactive


def _matches(keycode: int, *keys: str) -> bool:
    return any(keycode in (ord(key.lower()), ord(key.upper())) for key in keys)


def _handle_command_key(commander, keycode: int) -> None:
    """Map one key to an absolute, single-axis body-frame command."""
    axis = None
    value = 0.0
    if keycode == play_interactive._KEY_UP:
        axis, value = commander.AXIS_VX, +0.2
    elif keycode == play_interactive._KEY_DOWN:
        axis, value = commander.AXIS_VX, -0.2
    elif keycode == play_interactive._KEY_LEFT:
        axis, value = commander.AXIS_VY, +0.2
    elif keycode == play_interactive._KEY_RIGHT:
        axis, value = commander.AXIS_VY, -0.2
    elif _matches(keycode, "q"):
        axis, value = commander.AXIS_VYAW, +0.8
    elif _matches(keycode, "e"):
        axis, value = commander.AXIS_VYAW, -0.8
    elif keycode in (
        play_interactive._KEY_ENTER,
        play_interactive._KEY_KP_ENTER,
    ) or _matches(keycode, "x"):
        pass
    else:
        return

    commander.zero()
    if axis is not None:
        commander.command[axis] = np.clip(
            value, commander.low[axis], commander.high[axis]
        )
    print(f"[microduck-teleop] {commander.describe()}", flush=True)


def _print_keyboard_legend(args) -> None:
    del args
    print("[microduck-teleop] Arrow-key absolute direction control:", flush=True)
    print("  Up / Down   : vx = +0.2 / -0.2 m/s", flush=True)
    print("  Left / Right: vy = +0.2 / -0.2 m/s", flush=True)
    print("  Q / E       : yaw = +0.8 / -0.8 rad/s", flush=True)
    print("  Each movement key clears the other command axes.", flush=True)
    print("  Green/blue arrows show linear velocity only (not Q/E yaw).", flush=True)
    print("  X or Enter         : zero command (stop)", flush=True)
    print("  Backspace          : reset robot", flush=True)
    print("  Space              : resume (accidental pause disabled)", flush=True)


def _make_space_resume_only() -> None:
    """Prevent an accidental Space press from freezing browser teleoperation."""

    def resume_only(controls) -> bool:
        controls.resume()
        return False

    play_interactive.PlaybackControls.toggle_pause = resume_only


def _twist_term(env):
    """Return the manager-based MicroDuck twist command, if available."""
    try:
        term = env.command_manager.get_term("twist")
        command = np.asarray(env.command_manager.get_command("twist"))
    except (AttributeError, KeyError, TypeError):
        return None
    if command.ndim != 2 or command.shape[0] < 1 or command.shape[1] < 3:
        return None
    return term


def _state_has_velocity_commands(env) -> bool:
    return _twist_term(env) is not None


def _policy_obs_contains_command(env, *, reset_fn) -> bool:
    # microduck_velocity_flat has a fixed deploy contract whose 61D actor
    # observation includes the 3D twist command. The generic UniLab probe only
    # understands legacy state.info["commands"], so use the task contract here.
    del reset_fn
    return _twist_term(env) is not None


def _build_keyboard_commander(env, args):
    """Bridge UniLab keyboard control to manager-based command term ``twist``."""
    if not bool(getattr(args, "keyboard", False)):
        return None
    term = _twist_term(env)
    if term is None:
        print("[microduck-teleop] task has no manager-based twist command.", flush=True)
        return None

    ranges = term.cfg.ranges
    vel_limit = np.array(
        [
            [ranges.lin_vel_x[0], ranges.lin_vel_y[0], ranges.ang_vel_z[0]],
            [ranges.lin_vel_x[1], ranges.lin_vel_y[1], ranges.ang_vel_z[1]],
        ],
        dtype=np.float64,
    )
    commander = play_interactive.KeyboardCommander.from_vel_limit(
        vel_limit,
        step_lin=float(getattr(args, "keyboard_step_lin", 0.1)),
        step_ang=float(getattr(args, "keyboard_step_ang", 0.2)),
    )

    # Keep the command under keyboard authority. A very long interval also
    # survives Backspace/reset without random command resampling.
    term._resampling_time_range = (1.0e9, 1.0e9)
    term.time_left[:] = 1.0e9
    term.cfg.rel_standing_envs = 0.0
    term.cfg.rel_heading_envs = 0.0
    term.cfg.rel_world_envs = 0.0
    term.cfg.rel_forward_envs = 0.0
    if hasattr(term, "_turn_fraction"):
        term._turn_fraction = 0.0
    for flag in ("is_standing_env", "is_heading_env", "is_world_env"):
        value = getattr(term, flag, None)
        if isinstance(value, np.ndarray):
            value[:] = False

    command = env.command_manager.get_command("twist")
    command[:] = commander.command
    world_command = getattr(term, "vel_command_w", None)
    if isinstance(world_command, np.ndarray):
        world_command[:] = commander.command
    # UniLab's viewer loop and velocity-arrow overlay consume this legacy key.
    # It aliases the manager term's array, so writes update policy observations.
    env.state.info["commands"] = command
    robot_data = env.scene["robot"].data
    # UniLab's generic velocity-arrow overlay expects this legacy accessor,
    # while manager-based MicroDuck exposes body velocity through EntityData.
    env.get_local_linvel = lambda: robot_data.root_link_lin_vel_b

    # UniLab 1.0's viewer disables autoreset for keyboard mode, but its playback
    # loop then steps a terminated manager-based env once more and raises. Keep
    # autoreset enabled so a fallen robot restarts and teleoperation continues;
    # Backspace still provides an explicit immediate reset.
    original_set_autoreset = env.set_autoreset
    original_set_autoreset(True)
    env.set_autoreset = lambda enabled: original_set_autoreset(True)
    return commander


def _install_follow_camera() -> None:
    """Keep the tiny robot in frame while preserving user rotation/zoom."""
    original_render = play_interactive._render_velocity_arrows

    def render_with_follow(
        viewer,
        viz_data,
        focus_body_id,
        env,
        *,
        height,
        scale,
        width,
        lateral_offset,
    ):
        # UniLab's defaults produce a 9 cm arrow for this lab's 0.2 m/s
        # command, and place target/current arrows on top of each other.
        # Enlarge and separate them so they remain legible through noVNC.
        del height, scale, width, lateral_offset
        original_render(
            viewer,
            viz_data,
            focus_body_id,
            env,
            height=0.35,
            scale=1.2,
            width=0.04,
            lateral_offset=0.10,
        )
        if hasattr(viewer, "cam"):
            base_pos = np.asarray(viz_data.xpos[focus_body_id], dtype=np.float64)
            viewer.cam.lookat[0] = float(base_pos[0])
            viewer.cam.lookat[1] = float(base_pos[1])
            viewer.cam.lookat[2] = float(base_pos[2] + 0.15)

    play_interactive._render_velocity_arrows = render_with_follow


def main() -> None:
    # Reuse UniLab's tested checkpoint loading, policy inference, command
    # injection, velocity arrows, camera, and real-time 50 Hz playback loop.
    play_interactive._handle_command_key = _handle_command_key
    play_interactive._print_keyboard_legend = _print_keyboard_legend
    play_interactive._state_has_velocity_commands = _state_has_velocity_commands
    play_interactive._policy_obs_contains_command = _policy_obs_contains_command
    play_interactive._should_render_velocity_arrows = (
        lambda env, *, reset_fn=None: _twist_term(env) is not None
    )
    play_interactive._build_keyboard_commander = _build_keyboard_commander
    _make_space_resume_only()
    _install_follow_camera()
    play_interactive.main()


if __name__ == "__main__":
    main()
