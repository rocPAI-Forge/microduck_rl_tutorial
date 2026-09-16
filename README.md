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

Notebooks are split by language:

- Chinese: [`notebooks/zh/01_velocity_lab.ipynb`](notebooks/zh/01_velocity_lab.ipynb)
- English: [`notebooks/en/01_velocity_lab.ipynb`](notebooks/en/01_velocity_lab.ipynb)

The companion `02_interactive_teleop.ipynb` (same `zh/` or `en/` folder)
loads either the student's 300-iteration checkpoint or the bundled demo into a
single-robot MuJoCo viewer. A browser noVNC desktop provides live
direction keyboard commands (`↑/↓/←/→`, with `Q/E` for yaw) while the PPO actor
runs inference at 50 Hz.

`03_quiz.ipynb` (same language folder) holds a Start button and five fixed
beginner questions about the commands students just ran. Questions and scoring
live in [`scripts/microduck_quiz.py`](scripts/microduck_quiz.py), which also runs
standalone: `python3 scripts/microduck_quiz.py --lang en`.

Shared eval clips live in [`notebooks/assets/`](notebooks/assets/) and are
referenced by both Chinese and English `01` notebooks.

Demo checkpoint: [`examples/velocity_flat_demo/`](examples/velocity_flat_demo/) (`model_950.pt`, ~4.7 MB).

## Quick start

**Students / one-click (pull the published image):**

```bash
bash scripts/bring_up_lab.sh
```

Uses [`docker-compose.hub.yml`](docker-compose.hub.yml) and
`alexhegit/microduck-rl-tutorial:rocm714-py312` (JupyterLab hotfix included).
The script checks ROCm devices, picks a free `LAB_HOST_PORT` if `8888` is
taken, and prints the Jupyter URL with token.

**Maintainers (build from the ROCm PyTorch base image):**

```bash
bash scripts/bring_up_lab.sh --rebuild
```

Uses [`docker-compose.yml`](docker-compose.yml) and this repo's `Dockerfile`.

Agents: follow [`AGENTS.md`](AGENTS.md). Do not use the Kubernetes templates
for this.

Equivalent Compose without the helper script:

```bash
# Hub, out of the box
docker compose -f docker-compose.hub.yml pull && docker compose -f docker-compose.hub.yml up

# Source build
docker compose -f docker-compose.yml build && docker compose -f docker-compose.yml up
```

Open [`notebooks/zh/01_velocity_lab.ipynb`](notebooks/zh/01_velocity_lab.ipynb)
(Chinese) or [`notebooks/en/01_velocity_lab.ipynb`](notebooks/en/01_velocity_lab.ipynb)
(English).

Default endpoints (the bring-up script may choose another Jupyter port if
`8888` is already in use):

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
