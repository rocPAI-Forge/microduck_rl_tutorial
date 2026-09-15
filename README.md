# microduck_rl_tutorial

Beginner-friendly Jupyter lab for MicroDuck omnidirectional velocity RL on AMD ROCm.

## Course workflow (v2.6)

The notebook starts from RL/MDP fundamentals, explains why PPO is used, maps the
reward and domain-randomization design to MicroDuck, and shows how ROCm,
PyTorch, UniLab, `microduck_rl_unilab`, and this teaching repository fit
together.

| Phase | Config | Activity |
|---|---|---|
| **Smoke** | **4 × 2 iter** | Validate the full stack and inspect raw training logs |
| **1** | **500 × 300 iter** (~5 min GPU) | Student trains from scratch |
| **2** | **2048-env selected reference** | Student evals the bundled direction-tuned checkpoint |
| **3** | Compare | reward, episode length, video, curriculum |
| **4** | Single-robot teleop | Load a checkpoint and drive policy inference by keyboard |

Phase 1 keeps notebook output throttled to one status refresh every 10
iterations, writes the complete log to `runs/logs/phase1_500x300.log`, and
renders a 10-second (500 control-step) evaluation video.

The companion [`02_interactive_teleop.ipynb`](notebooks/02_interactive_teleop.ipynb)
loads either the student's 300-iteration checkpoint or the bundled demo into a
single-robot MuJoCo viewer. A browser noVNC desktop provides live
direction keyboard commands (`↑/↓/←/→`, with `Q/E` for yaw) while the PPO actor
runs inference at 50 Hz.

Demo checkpoint: [`examples/velocity_flat_demo/`](examples/velocity_flat_demo/) (`model_950.pt`, ~4.7 MB).

## Quick start

```bash
docker compose build && docker compose up
```

Open [`notebooks/01_velocity_lab.ipynb`](notebooks/01_velocity_lab.ipynb).

Default endpoints:

- JupyterLab: host port `8888` (`LAB_HOST_PORT`)
- Interactive MuJoCo/noVNC: host port `16080` (`TELEOP_HOST_PORT`)

The default noVNC password is `microduck`. Override it before startup with
`TELEOP_VNC_PASSWORD`.

## Demo metrics

The reference checkpoint was selected with 32 parallel, 10-second trials for
each body-frame direction. All four linear directions passed the automated
gate. Yaw is stable and improved but remains less accurate, especially for
right turns across randomized seeds. Training performance was measured on
AMD Instinct MI210; the model is not tied to MI210 hardware.

## Related

- [microduck_rl_unilab](https://github.com/rocPAI-Forge/microduck_rl_unilab)
- [UniLab](https://github.com/Motphys/UniLab)
