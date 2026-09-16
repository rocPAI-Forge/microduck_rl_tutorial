#!/usr/bin/env bash
# Host-side lab bring-up. Not used inside the container.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

CONTAINER="${CONTAINER:-microduck-rl-tutorial}"
HUB_IMAGE="${HUB_IMAGE:-alexhegit/microduck-rl-tutorial:rocm714-py312}"
LOCAL_IMAGE="${LOCAL_IMAGE:-microduck-rl-tutorial:rocm714-py312}"
REBUILD=0
PREFERRED_LAB_PORT="${LAB_HOST_PORT:-8888}"
PREFERRED_TELEOP_PORT="${TELEOP_HOST_PORT:-16080}"

usage() {
  cat <<'EOF'
Usage: scripts/bring_up_lab.sh [--rebuild]

Bring up the MicroDuck Jupyter lab on this host.

  (default)   Pull alexhegit/microduck-rl-tutorial:rocm714-py312 and start it
              (docker-compose.hub.yml). No local Dockerfile build.
  --rebuild   Build from rocm/pytorch via docker-compose.yml, then start.

Environment:
  LAB_HOST_PORT        preferred Jupyter host port (default 8888; falls back if busy)
  TELEOP_HOST_PORT     preferred noVNC host port (default 16080; falls back if busy)
  TELEOP_PUBLIC_PORT   noVNC port in the browser URL / notebook iframe
                       (default: same as TELEOP_HOST_PORT)
  HIP_VISIBLE_DEVICES  GPU index (default 0)
  TELEOP_VNC_PASSWORD  noVNC password (default microduck)
  TELEOP_AUTOSTART     teleop at container start: off (default) | demo | latest | auto
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rebuild) REBUILD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "${REBUILD}" -eq 1 ]]; then
  COMPOSE_FILE="${ROOT}/docker-compose.yml"
  IMAGE="${LOCAL_IMAGE}"
else
  COMPOSE_FILE="${ROOT}/docker-compose.hub.yml"
  IMAGE="${HUB_IMAGE}"
fi

port_busy() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -qE ":${port}[[:space:]]"
    return $?
  fi
  python3 - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", port))
except OSError:
    sys.exit(0)
s.close()
sys.exit(1)
PY
}

pick_port() {
  local preferred="$1"
  shift
  local candidates=("${preferred}" "$@")
  local p
  for p in "${candidates[@]}"; do
    if ! port_busy "${p}"; then
      echo "${p}"
      return 0
    fi
    if docker inspect "${CONTAINER}" --format '{{json .HostConfig.PortBindings}}' 2>/dev/null \
      | grep -q "\"HostPort\":\"${p}\""; then
      echo "${p}"
      return 0
    fi
  done
  echo "no free host port among: ${candidates[*]}" >&2
  return 1
}

echo "== preflight =="
command -v docker >/dev/null || { echo "docker is not on PATH" >&2; exit 1; }
docker compose version >/dev/null || { echo "docker compose plugin is missing" >&2; exit 1; }
[[ -e /dev/kfd ]] || { echo "missing /dev/kfd (ROCm kernel device)" >&2; exit 1; }
[[ -e /dev/dri ]] || { echo "missing /dev/dri (DRM device)" >&2; exit 1; }

LAB_HOST_PORT="$(pick_port "${PREFERRED_LAB_PORT}" 18888 28888 8889)"
TELEOP_HOST_PORT="$(pick_port "${PREFERRED_TELEOP_PORT}" 16081 16082 26080)"
# Browser-facing noVNC port. Keep equal to TELEOP_HOST_PORT unless a jump
# host remaps noVNC; then set TELEOP_PUBLIC_PORT to the port in the URL bar.
export TELEOP_PUBLIC_PORT="${TELEOP_PUBLIC_PORT:-${TELEOP_HOST_PORT}}"
export LAB_HOST_PORT TELEOP_HOST_PORT
export HIP_VISIBLE_DEVICES="${HIP_VISIBLE_DEVICES:-0}"
export TELEOP_VNC_PASSWORD="${TELEOP_VNC_PASSWORD:-microduck}"

echo "compose:              ${COMPOSE_FILE}"
echo "image:                ${IMAGE}"
echo "LAB_HOST_PORT:        ${LAB_HOST_PORT}"
echo "TELEOP_HOST_PORT:     ${TELEOP_HOST_PORT}"
echo "TELEOP_PUBLIC_PORT:   ${TELEOP_PUBLIC_PORT}"
echo "HIP_VISIBLE_DEVICES:  ${HIP_VISIBLE_DEVICES}"

if [[ "${REBUILD}" -eq 1 ]]; then
  echo "== docker compose -f docker-compose.yml build =="
  docker compose -f "${COMPOSE_FILE}" build
else
  if docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "== ${IMAGE} present locally; skip pull =="
  else
    echo "== docker compose -f docker-compose.hub.yml pull =="
    docker compose -f "${COMPOSE_FILE}" pull
  fi
fi

echo "== docker compose up -d =="
docker compose -f "${COMPOSE_FILE}" up -d

echo "== wait for Jupyter =="
token=""
for _ in $(seq 1 30); do
  if docker exec "${CONTAINER}" jupyter server list >/tmp/microduck-jupyter-list.txt 2>/dev/null; then
    token="$(sed -n 's/.*token=\([a-f0-9]*\).*/\1/p' /tmp/microduck-jupyter-list.txt | head -n1)"
    if [[ -n "${token}" ]]; then
      break
    fi
  fi
  sleep 2
done

host_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "== lab is up =="
echo "container: ${CONTAINER}"
echo "image:     ${IMAGE}"
if [[ -n "${token}" ]]; then
  echo "Jupyter (local):  http://127.0.0.1:${LAB_HOST_PORT}/lab?token=${token}"
  if [[ -n "${host_ip}" ]]; then
    echo "Jupyter (LAN):    http://${host_ip}:${LAB_HOST_PORT}/lab?token=${token}"
  fi
  echo "Chinese 01:       http://127.0.0.1:${LAB_HOST_PORT}/lab/tree/zh/01_velocity_lab.ipynb?token=${token}"
  echo "English 01:       http://127.0.0.1:${LAB_HOST_PORT}/lab/tree/en/01_velocity_lab.ipynb?token=${token}"
else
  echo "Jupyter token not ready yet. Print it with:"
  echo "  docker exec ${CONTAINER} jupyter server list"
fi
echo "noVNC:            http://127.0.0.1:${TELEOP_HOST_PORT}/vnc.html  (password: ${TELEOP_VNC_PASSWORD})"
echo "Stop:             docker compose -f ${COMPOSE_FILE} down"
echo
echo "Jump host / browser on another machine: forward BOTH ports and keep"
echo "the noVNC number unchanged (02 iframe = Jupyter hostname + TELEOP_PUBLIC_PORT):"
echo "  bash scripts/forward_lab_ports.sh <gpu-host>"
echo "  # or: ssh -N -L ${LAB_HOST_PORT}:127.0.0.1:${LAB_HOST_PORT} \\"
echo "  #           -L ${TELEOP_HOST_PORT}:127.0.0.1:${TELEOP_HOST_PORT} <gpu-host>"
echo "Do not remap only Jupyter to a new local port without also forwarding"
echo "noVNC as ${TELEOP_PUBLIC_PORT} on the hostname in the Jupyter URL."
