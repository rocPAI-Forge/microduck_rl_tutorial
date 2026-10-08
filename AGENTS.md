# AGENTS.md

Instructions for coding agents working in this repository.

Kubernetes is out of scope. Use Docker Compose on the host.

## When the user asks to bring the lab up

Treat phrases such as「把 lab 拉起来」「一键部署」「start the lab」「bring up the tutorial」as this workflow. Do not invent a second deploy path.

1. Read this file. Do not start from K8s manifests.
2. Default image, one command for Instinct and Radeon. HIP PyTorch in this image already contains `gfx90a`, `gfx942`, `gfx1100`, `gfx1201`, and `gfx1151`. The container sets no architecture override; it uses the GPU the host driver exposes.

   ```bash
   bash scripts/bring_up_lab.sh
   ```

   This uses `docker-compose.yml` and local tag `microduck-rl-tutorial:rocm724-py312`. When that tag is absent, the script builds it from `rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_release_2.10.0`.

3. Download the published image when the user asks to pull the ready-made image:

   ```bash
   bash scripts/bring_up_lab.sh --pull
   ```

   This pulls `alexhegit/microduck-rl-tutorial:rocm724-py312`, tags it as `microduck-rl-tutorial:rocm724-py312`, and starts the same compose file. Do not start from `docker-compose.hub.yml`.

4. Rebuild that same image from source:

   ```bash
   bash scripts/bring_up_lab.sh --rebuild
   ```

5. Paste browser URLs from **Ports and browser access** below (Jupyter with `token=`, Chinese and English `01`, noVNC `/vnc.html`). Prefer the hostname the user’s browser will actually open (GPU LAN, or jump-host LAN after forwarding).

6. Stop with the `docker compose -f … down` line the script printed (same compose file that was used to start). If you started `scripts/forward_lab_ports.sh`, stop that SSH tunnel too.

## Preconditions the script already checks

- `docker` and `docker compose` on PATH
- `/dev/kfd` and `/dev/dri` (AMD ROCm GPU)

If those fail, report the missing item. Do not try CUDA, do not try `pip install` on the host, do not rewrite the Compose GPU device list unless the user asks.

The default image is local. Do not set `HSA_OVERRIDE_GFX_VERSION` or a GPU-family switch; PyTorch selects the architecture from the GPU on `/dev/kfd`.

## Ports and browser access

One URL formula for **direct GPU access and jump-host access**. Do not invent a second notebook embed scheme.

### Formula

Notebook 02 (`scripts/microduck_novnc_embed.py`) builds noVNC as:

```text
http(s)://<hostname in the Jupyter address bar>:<TELEOP_PUBLIC_PORT>/vnc.html
```

| Name | Meaning | Default |
|---|---|---|
| `LAB_HOST_PORT` | Jupyter **docker publish on the GPU host** | `8888` (fallback `18888` → `28888` → `8889`) |
| `TELEOP_HOST_PORT` | noVNC **docker publish on the GPU host** (container `6080`) | `16080` (fallback `16081` → `16082` → `26080`) |
| `TELEOP_PUBLIC_PORT` | noVNC port in the **browser** and in the 02 iframe | same as `TELEOP_HOST_PORT` |

Jupyter may use a different port than noVNC. noVNC must still listen on **the same hostname as Jupyter** at `TELEOP_PUBLIC_PORT`. Always open `/vnc.html` (bare `/` is a directory listing). Password default: `microduck`.

Do not hard-code `8888` or `16080` in replies. Use the ports `bring_up_lab.sh` / `forward_lab_ports.sh` printed.

`bring_up_lab.sh` keeps a preferred port if it is free **or already owned by container `microduck-rl-tutorial`**.

### How to choose the path

1. Bring the lab up **on the GPU host** with `bash scripts/bring_up_lab.sh` (never on the jump host unless that machine has the ROCm GPU and the compose devices).
2. Decide where the user’s **browser** will connect:
   - Browser can reach the GPU IP/ports → **no jump**. Paste GPU LAN URLs.
   - Browser can only reach a jump host (or `localhost` via SSH `-L`) → **jump**. On the **browser-facing machine**, run `bash scripts/forward_lab_ports.sh <gpu-host>`, then paste **that** machine’s URLs.
3. Before sending links, check that **both** Jupyter and noVNC answer on the hostname you are about to paste (`curl -sI http://<host>:<lab>/lab` and `http://<host>:<teleop>/vnc.html`).

### Port table (what the user types)

| Scenario | Jupyter URL host:port | noVNC URL | Agent action |
|---|---|---|---|
| No jump (direct) | `<GPU_IP>:<LAB_HOST_PORT>` | `http://<GPU_IP>:<TELEOP_PUBLIC_PORT>/vnc.html` | After `bring_up_lab.sh`, paste the script’s LAN Jupyter URL, `01` links, and noVNC `/vnc.html`. |
| Jump, recommended | `<JUMP_IP>:<local Jupyter>` | `http://<JUMP_IP>:<GPU TELEOP_HOST_PORT>/vnc.html` | On the jump host (or laptop): `bash scripts/forward_lab_ports.sh <gpu-host>`. That script forwards **both** ports and **keeps the noVNC local port equal to the GPU `TELEOP_HOST_PORT`**. Jupyter may fall back locally if that number is busy. Paste the URLs the script printed. |
| Jump, Jupyter remapped only | e.g. `<JUMP_IP>:18888` → GPU `8888` | still `<JUMP_IP>:16080` → GPU `16080` | Allowed. 02 ignores the Jupyter port; it uses hostname + `TELEOP_PUBLIC_PORT`. You **must** still forward noVNC as `TELEOP_PUBLIC_PORT` on that hostname. |
| Jump, noVNC remapped too | any | e.g. `<JUMP_IP>:26080` → GPU `16080` | Not silent. Either recreate on the GPU with `TELEOP_PUBLIC_PORT=26080`, or tell the user to type `26080` in the 02 embed port box. Do not leave iframe on `16080`. |

Manual jump equivalent (same invariant: noVNC number unchanged):

```bash
ssh -N -L ${LAB_HOST_PORT}:127.0.0.1:${LAB_HOST_PORT} \
        -L ${TELEOP_HOST_PORT}:127.0.0.1:${TELEOP_HOST_PORT} <gpu-host>
```

If Jupyter’s GPU port is busy on the jump host, remap Jupyter only, and keep:

```bash
ssh -N -L 18888:127.0.0.1:${LAB_HOST_PORT} \
        -L ${TELEOP_HOST_PORT}:127.0.0.1:${TELEOP_HOST_PORT} <gpu-host>
```

Then paste Jupyter as `http://<jump-ip>:18888/lab?token=...` and noVNC as `http://<jump-ip>:${TELEOP_HOST_PORT}/vnc.html`.

### What to paste after bring-up

- Jupyter Lab URL with `token=`
- Chinese notebook: `/lab/tree/zh/microduck_lab.ipynb?token=`
- English notebook: `/lab/tree/en/microduck_lab.ipynb?token=`
- noVNC: `/vnc.html` on `TELEOP_PUBLIC_PORT` (password `microduck` unless overridden)
- Stop: the `docker compose -f … down` line from the GPU host

### If 02 iframe is blank but `/vnc.html` in a new tab works

Hostname/port mismatch: the iframe uses Jupyter’s hostname + container `TELEOP_PUBLIC_PORT`. Forward noVNC onto that host:port, or set the port in the 02 widget. Do not rebuild the image for this.

Same-origin Jupyter proxy for noVNC is out of scope until a Hub image rebuild (`jupyter-server-proxy`). Bind-mounted `scripts/` and `notebooks/` already pick up the iframe helper without rebuild.

## What not to rebuild

Bind mounts already overlay `notebooks/`, `scripts/`, `examples/`, and `runs/`. Edits there are live after refresh.

`--rebuild` is only for image layers: ROCm/PyTorch, UniLab wheels, `jupyter_server>=2.21.1`, `microduck_rl_unilab` SHA.

## Image names

| Role | Name |
|---|---|
| Container | `microduck-rl-tutorial` |
| Unified local tag | `microduck-rl-tutorial:rocm724-py312` |
| Published Hub tag | `alexhegit/microduck-rl-tutorial:rocm724-py312` |
| Base image | `rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_release_2.10.0` |

Do not rename the container in a deploy session.

## Publishing a new Hub image (maintainers)

After a successful `--rebuild`:

```bash
docker tag microduck-rl-tutorial:rocm724-py312 alexhegit/microduck-rl-tutorial:rocm724-py312
docker push alexhegit/microduck-rl-tutorial:rocm724-py312
```

The published image must include `jupyter_server>=2.21.1`. Do not push an older local tag that predates that pin.

## Notebooks after the lab is up

Jupyter `notebook-dir` is `notebooks/`:

- Chinese: `zh/microduck_lab.ipynb`
- English: `en/microduck_lab.ipynb`

Quiz logic is `scripts/microduck_quiz.py`. Shared clips are `notebooks/assets/_phase1.mp4` and `_phase2.mp4`.

## If JupyterLab renders as unstyled HTML

The running image is missing `jupyter_server>=2.21.1` (Tornado 6.5.9+). Rebuild from source and republish; do not treat an in-container `pip install` as the Hub image.

## Manual URL recovery

```bash
docker exec microduck-rl-tutorial jupyter server list
```

Rewrite the hostname to `127.0.0.1` or the host LAN IP, and the port to the printed `LAB_HOST_PORT`.
