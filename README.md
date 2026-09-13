# microduck_rl_lab

One-hour, hands-on Jupyter lab for training MicroDuck locomotion policies with
**UniLab** (PyPI wheels) and the downstream task package
[`microduck_rl_unilab`](https://github.com/unilabsim/microduck_rl_unilab).

This repository contains only the tutorial surface:

- Docker image recipe (ROCm base + notebook)
- `notebooks/01_microduck_hour_lab.ipynb`
- small helper scripts under `scripts/`

It does **not** vendor the task code or published checkpoints. Those come from
`microduck_rl_unilab` inside the container.

## Base image

Pinned to the ROCm image we validated against UniLab's Python / torch contract:

```text
rocm/pytorch:rocm7.14.1_ubuntu24.04_py3.12_pytorch_release_2.11.0
```

- Python 3.12 (`unilab` requires `<3.14`)
- PyTorch 2.11.0 (inside UniLab's `torch>=2.8,<2.12` window)
- ROCm 7.14.1 (docs require host ROCm `>=7.1`)

Do **not** run `make sync-rocm` inside this container. The image already ships a
HIP torch build; replacing it with the CUDA lockfile is the most common failure
mode.

Training configs still use **`cuda` device semantics** on ROCm. That is expected.

## Quick start

Requirements on the host:

- AMD GPU + ROCm driver
- Docker with `/dev/kfd` and `/dev/dri` access

```bash
git clone https://github.com/rocPAI-Forge/microduck_rl_lab.git
cd microduck_rl_lab
docker compose build
docker compose up
```

Open the Jupyter URL printed in the terminal (token shown on first launch).

Training artifacts are written to `./runs` on the host.

## What the notebook does

| Block | Task owner | Goal |
|---|---|---|
| 0 | — | Environment smoke check |
| 1 | `microduck_velocity_flat` | ~2000 PPO iters, basic walking gait |
| 2 | `microduck_sprint_flat` | ~2000–4000 PPO iters, forward sprint behavior |
| 3 | published examples | Play pre-trained checkpoints when available |

The hour lab teaches the **workflow** (train → read curves → render video). It
does not reproduce the multi-day sprint straightening curriculum from the
research branch.

## Build arguments

Override the task package revision baked into the image:

```bash
docker compose build \
  --build-arg MICRODUCK_REF=main \
  --build-arg MICRODUCK_REPO=https://github.com/unilabsim/microduck_rl_unilab.git
```

To include published example checkpoints before they land on `main`, point
`MICRODUCK_REF` at the commit that contains `examples/sprint_*`.

## Layout

```text
microduck_rl_lab/
├── Dockerfile
├── docker-compose.yml
├── notebooks/
│   └── 01_microduck_hour_lab.ipynb
├── scripts/
│   ├── entrypoint.sh
│   └── lab_utils.py
└── runs/                 # host-mounted training output (gitignored)
```

## Related repos

- UniLab distribution: https://github.com/unilabsim/UniLab
- MicroDuck task owners: https://github.com/unilabsim/microduck_rl_unilab
- Long-form training notes branch (local research): `tutorial` on the task repo
