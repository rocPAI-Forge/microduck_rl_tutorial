# AGENTS.md

Instructions for coding agents working in this repository.

Kubernetes is out of scope. Use Docker Compose on the host.

## When the user asks to bring the lab up

Treat phrases such as「把 lab 拉起来」「一键部署」「start the lab」「bring up the tutorial」as this workflow. Do not invent a second deploy path.

1. Read this file. Do not start from K8s manifests.
2. Default (out-of-the-box Hub image, includes the JupyterLab static-file hotfix):

   ```bash
   bash scripts/bring_up_lab.sh
   ```

   This uses `docker-compose.hub.yml` and image
   `alexhegit/microduck-rl-tutorial:rocm714-py312`.

3. Source build from `rocm/pytorch` (Dockerfile, UniLab pin, or unpublished Hub image):

   ```bash
   bash scripts/bring_up_lab.sh --rebuild
   ```

   This uses `docker-compose.yml` and local tag `microduck-rl-tutorial:rocm714-py312`.

4. Paste the script’s Jupyter URL (including `token=`) back to the user. Prefer the LAN URL if they are not on this machine. Also give the English and Chinese `01` notebook links.

5. Stop with the `docker compose -f … down` line the script printed (same compose file that was used to start).

## Preconditions the script already checks

- `docker` and `docker compose` on PATH
- `/dev/kfd` and `/dev/dri` (AMD ROCm GPU)

If those fail, report the missing item. Do not try CUDA, do not try `pip install` on the host, do not rewrite the Compose GPU device list unless the user asks.

Hub pull requires Docker Hub access. If pull fails with auth errors, tell the user to run `docker login -u alexhegit` in their own terminal (use a Hub access token as the password; do not ask them to paste the token into chat).

## Ports

| Service | Container | Host env | Default |
|---|---|---|---|
| JupyterLab | `8888` | `LAB_HOST_PORT` | `8888` |
| noVNC teleop | `6080` | `TELEOP_HOST_PORT` | `16080` |

`scripts/bring_up_lab.sh` keeps the preferred port if it is free **or already owned by container `microduck-rl-tutorial`**. If another process holds it, it falls back (`8888` → `18888` → `28888` → `8889`; `16080` → `16081` → `16082` → `26080`).

Do not hard-code `8888` in the reply. Use the port the script printed.

## What not to rebuild

Bind mounts already overlay `notebooks/`, `scripts/`, `examples/`, and `runs/`. Edits there are live after refresh.

`--rebuild` is only for image layers: ROCm/PyTorch, UniLab wheels, `jupyter_server>=2.21.1`, `microduck_rl_unilab` SHA.

## Image names

| Role | Name |
|---|---|
| Container | `microduck-rl-tutorial` |
| Local source-build tag | `microduck-rl-tutorial:rocm714-py312` |
| Docker Hub (students) | `alexhegit/microduck-rl-tutorial:rocm714-py312` |

Do not rename the container in a deploy session.

## Publishing a new Hub image (maintainers)

After a successful `--rebuild`:

```bash
docker tag microduck-rl-tutorial:rocm714-py312 alexhegit/microduck-rl-tutorial:rocm714-py312
docker push alexhegit/microduck-rl-tutorial:rocm714-py312
```

The published image must include `jupyter_server>=2.21.1`. Do not push an older local tag that predates that pin.

## Notebooks after the lab is up

Jupyter `notebook-dir` is `notebooks/`:

- Chinese: `zh/01_velocity_lab.ipynb`, `zh/02_interactive_teleop.ipynb`, `zh/03_quiz.ipynb`
- English: `en/01_velocity_lab.ipynb`, `en/02_interactive_teleop.ipynb`, `en/03_quiz.ipynb`

Quiz logic is `scripts/microduck_quiz.py`. Shared clips are `notebooks/assets/_phase1.mp4` and `_phase2.mp4`.

## If JupyterLab renders as unstyled HTML

The running image is missing `jupyter_server>=2.21.1` (Tornado 6.5.9+). Rebuild from source and republish; do not treat an in-container `pip install` as the Hub image.

## Manual URL recovery

```bash
docker exec microduck-rl-tutorial jupyter server list
```

Rewrite the hostname to `127.0.0.1` or the host LAN IP, and the port to the printed `LAB_HOST_PORT`.
