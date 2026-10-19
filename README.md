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
| **1** | **500 × 300 iter** | Student trains from scratch |
| **2** | **2048-env selected reference** | Student evals the bundled direction-tuned checkpoint |
| **3** | Compare | reward, episode length, video, curriculum |
| **4** | Single-robot teleop | Load a checkpoint and drive policy inference by keyboard |

Phase 1 keeps notebook output throttled to one status refresh every 10
iterations, writes the complete log to `runs/logs/phase1_500x300.log`, and
renders a 10-second (500 control-step) evaluation video.

Each language is one notebook. Training, keyboard teleop, and the five-question
quiz are sections of the same file:

- Chinese: [`notebooks/zh/microduck_lab.ipynb`](notebooks/zh/microduck_lab.ipynb)
- English: [`notebooks/en/microduck_lab.ipynb`](notebooks/en/microduck_lab.ipynb)

The teleop section loads either the student's 300-iteration checkpoint or the
bundled demo into a single-robot MuJoCo viewer. A browser noVNC desktop provides
live direction keyboard commands (`↑/↓/←/→`, with `Q/E` for yaw) while the PPO
actor runs inference at 50 Hz.

The quiz section holds a Start button and five fixed beginner questions about
the commands students just ran. Questions and scoring live in
[`scripts/microduck_quiz.py`](scripts/microduck_quiz.py), which also runs
standalone: `python3 scripts/microduck_quiz.py --lang en`.

Shared eval clips live in [`notebooks/assets/`](notebooks/assets/) and are
referenced by both language notebooks.

Demo checkpoint: [`examples/velocity_flat_demo/`](examples/velocity_flat_demo/) (`model_950.pt`, ~4.7 MB).

## Quick start

**One image, one code path, one GPU.** The full tutorial was executed on each of these with `microduck-rl-tutorial:rocm724-py312`. The container does not set `HSA_OVERRIDE_GFX_VERSION` or any GPU-family switch.

| Validated hardware | Architecture | GPUs required |
|---|---|---|
| AMD Instinct™ MI300X | `gfx942` | 1 |
| AMD Radeon™ R9700 | `gfx1201` | 1 |
| AMD Ryzen™ AI Max (Strix Halo APU) | `gfx1151` | 1 |

HIP PyTorch in that image also ships `gfx90a` and `gfx1100`. Those targets are not part of the validation table above.

Clone this repository, then pick one of the two commands below. Both use
[`docker-compose.yml`](docker-compose.yml), check `/dev/kfd` and `/dev/dri`,
pick a free `LAB_HOST_PORT` if `8888` is taken, and print the Jupyter URL
with token.

### Download the published image

```bash
bash scripts/bring_up_lab.sh --pull
```

Downloads [`alexhegit/microduck-rl-tutorial:rocm724-py312`](https://hub.docker.com/r/alexhegit/microduck-rl-tutorial)
from Docker Hub, tags it locally as `microduck-rl-tutorial:rocm724-py312`,
and starts the lab. That image is already built on
`rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_release_2.10.0`.

### Build locally

```bash
bash scripts/bring_up_lab.sh
```

Builds `microduck-rl-tutorial:rocm724-py312` from
`rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_release_2.10.0` when
that local tag is absent, then starts the lab. Build again from the same
AMD base image with `bash scripts/bring_up_lab.sh --rebuild`.

Agents: follow [`AGENTS.md`](AGENTS.md). Do not use the Kubernetes templates
for this.

Equivalent Compose without the helper script:

```bash
docker compose -f docker-compose.yml up
```

Open [`notebooks/zh/microduck_lab.ipynb`](notebooks/zh/microduck_lab.ipynb)
(Chinese) or [`notebooks/en/microduck_lab.ipynb`](notebooks/en/microduck_lab.ipynb)
(English).

Default endpoints (the bring-up script may choose another Jupyter port if
`8888` is already in use):

- JupyterLab: host port `8888` (`LAB_HOST_PORT`)
- Interactive MuJoCo/noVNC: host port `16080` (`TELEOP_HOST_PORT`), open `/vnc.html`

The default noVNC password is `microduck`. Override it before startup with
`TELEOP_VNC_PASSWORD`.

Notebook 02 embeds noVNC as `Jupyter-URL-hostname:TELEOP_PUBLIC_PORT`.
`TELEOP_PUBLIC_PORT` defaults to `TELEOP_HOST_PORT`. Through a jump host,
forward **both** ports and keep the noVNC number unchanged:

```bash
bash scripts/forward_lab_ports.sh <gpu-host>
```

## Demo metrics

The reference checkpoint was selected with 32 parallel, 10-second trials for
each body-frame direction. All four linear directions passed the automated
gate. Yaw is stable and improved but remains less accurate, especially for
right turns across randomized seeds. The full tutorial was executed on one
GPU at a time: AMD Instinct MI300X, AMD Radeon R9700, and an AMD Ryzen AI Max
(Strix Halo) APU, using the same code and container. The bundled demo
checkpoint was selected on MI210 and is not tied to one GPU.

## Related

- [microduck_rl_unilab](https://github.com/rocPAI-Forge/microduck_rl_unilab)
- [UniLab](https://github.com/Motphys/UniLab)
