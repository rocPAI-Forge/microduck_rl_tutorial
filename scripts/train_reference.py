#!/usr/bin/env python3
"""Train a reference policy with extra body-frame cardinal command coverage."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

import numpy as np

from microduck_rl_unilab.tasks.microduck.manager_terms import MicroduckVelocityCommand


CARDINAL_COMMANDS = np.asarray(
    [
        [0.2, 0.0, 0.0],
        [-0.2, 0.0, 0.0],
        [0.0, 0.2, 0.0],
        [0.0, -0.2, 0.0],
        [0.0, 0.0, 0.4],
        [0.0, 0.0, -0.4],
    ],
    dtype=np.float64,
)


def install_cardinal_sampler(fraction: float, weights: np.ndarray) -> None:
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("REFERENCE_CARDINAL_FRACTION must be in [0, 1]")
    if weights.shape != (len(CARDINAL_COMMANDS),) or np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError("REFERENCE_CARDINAL_WEIGHTS must contain six non-negative values")
    probabilities = weights / weights.sum()
    original = MicroduckVelocityCommand._resample_command

    def resample_with_cardinals(self, env_ids: np.ndarray) -> None:
        original(self, env_ids)
        if fraction == 0.0 or len(env_ids) == 0:
            return
        rng = self._env.rng
        selected = rng.uniform(0.0, 1.0, len(env_ids)) < fraction
        selected_ids = env_ids[selected]
        if len(selected_ids) == 0:
            return
        command_ids = rng.choice(
            len(CARDINAL_COMMANDS), size=len(selected_ids), p=probabilities
        )
        self.vel_command_b[selected_ids] = CARDINAL_COMMANDS[command_ids]
        self.vel_command_w[selected_ids] = self.vel_command_b[selected_ids]
        self.is_standing_env[selected_ids] = False
        self.is_heading_env[selected_ids] = False
        self.is_world_env[selected_ids] = False
        self.is_forward_env[selected_ids] = False

    MicroduckVelocityCommand._resample_command = resample_with_cardinals


def main() -> None:
    fraction = float(os.environ.get("REFERENCE_CARDINAL_FRACTION", "0.60"))
    weights = np.fromstring(
        os.environ.get("REFERENCE_CARDINAL_WEIGHTS", "1,1,1,1,1,1"),
        sep=",",
        dtype=np.float64,
    )
    install_cardinal_sampler(fraction, weights)
    print(
        f"[reference-train] cardinal command sampling fraction={fraction:.0%}, "
        f"weights={weights.tolist()}",
        flush=True,
    )

    script = Path("/opt/venv/lib/python3.12/site-packages/unilab/scripts/train_rsl_rl.py")
    if not script.is_file():
        raise FileNotFoundError(script)
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
