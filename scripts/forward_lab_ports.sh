#!/usr/bin/env bash
# Run on the machine the browser will use (laptop or jump host).
# Forwards Jupyter + noVNC from a GPU lab host.
#
# Invariant: keep the noVNC listen port on *this* host equal to the GPU
# host's TELEOP_HOST_PORT, so notebook 02 iframes
#   hostname-in-Jupyter-URL + ':' + TELEOP_PUBLIC_PORT
# keep working. Jupyter may fall back to another local port.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/forward_lab_ports.sh [user@]gpu-host

Forward the running microduck-rl-tutorial ports from gpu-host to this machine.

Environment:
  BIND_ADDRESS     listen address on this host (default 0.0.0.0)
  LAB_LOCAL_PORT   override Jupyter listen port on this host
  TELEOP_LOCAL_PORT  override noVNC listen port (breaks 02 iframe unless you
                   type the new port in the notebook widget)
  CONTAINER        default microduck-rl-tutorial
  SSH_OPTS         extra ssh options

Example (from a jump host):
  bash scripts/forward_lab_ports.sh tw39
EOF
}

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

REMOTE="$1"
CONTAINER="${CONTAINER:-microduck-rl-tutorial}"
BIND_ADDRESS="${BIND_ADDRESS:-0.0.0.0}"
SSH_OPTS="${SSH_OPTS:-}"

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

pick_local() {
  local preferred="$1"
  shift
  local p
  for p in "${preferred}" "$@"; do
    if ! port_busy "${p}"; then
      echo "${p}"
      return 0
    fi
  done
  echo "no free local port among: ${preferred} $*" >&2
  return 1
}

echo "== probe ${REMOTE} container ${CONTAINER} =="
remote_ports="$(ssh ${SSH_OPTS} -o BatchMode=yes "${REMOTE}" "docker port ${CONTAINER}")"
echo "${remote_ports}"

remote_lab="$(echo "${remote_ports}" | awk '/8888\/tcp/ {gsub(/.*:/,""); print $1; exit}')"
remote_teleop="$(echo "${remote_ports}" | awk '/6080\/tcp/ {gsub(/.*:/,""); print $1; exit}')"
if [[ -z "${remote_lab}" || -z "${remote_teleop}" ]]; then
  echo "could not parse published 8888/tcp and 6080/tcp from docker port" >&2
  exit 1
fi

LAB_LOCAL_PORT="${LAB_LOCAL_PORT:-$(pick_local "${remote_lab}" 18888 28888 8889)}"
if [[ -n "${TELEOP_LOCAL_PORT:-}" ]]; then
  :
else
  if port_busy "${remote_teleop}"; then
    echo "warning: local ${remote_teleop} is busy; 02 iframe expects this port on this hostname." >&2
    TELEOP_LOCAL_PORT="$(pick_local 16081 16082 26080)"
    echo "warning: forwarding noVNC as ${TELEOP_LOCAL_PORT}. Type that port in the 02 widget." >&2
  else
    TELEOP_LOCAL_PORT="${remote_teleop}"
  fi
fi

token=""
token="$(ssh ${SSH_OPTS} -o BatchMode=yes "${REMOTE}" \
  "docker exec ${CONTAINER} jupyter server list 2>/dev/null" \
  | sed -n 's/.*token=\([a-f0-9]*\).*/\1/p' | head -n1 || true)"

host_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo
echo "== forwarding =="
echo "Jupyter:  ${BIND_ADDRESS}:${LAB_LOCAL_PORT}  ->  ${REMOTE}:127.0.0.1:${remote_lab}"
echo "noVNC:    ${BIND_ADDRESS}:${TELEOP_LOCAL_PORT}  ->  ${REMOTE}:127.0.0.1:${remote_teleop}"
if [[ "${TELEOP_LOCAL_PORT}" != "${remote_teleop}" ]]; then
  echo "NOTE: noVNC local port != GPU TELEOP_HOST_PORT (${remote_teleop})."
  echo "      Notebook 02 must use ${TELEOP_LOCAL_PORT} in the port box."
fi

# shellcheck disable=SC2086
ssh ${SSH_OPTS} -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L "${BIND_ADDRESS}:${LAB_LOCAL_PORT}:127.0.0.1:${remote_lab}" \
  -L "${BIND_ADDRESS}:${TELEOP_LOCAL_PORT}:127.0.0.1:${remote_teleop}" \
  "${REMOTE}"

echo
echo "== browser URLs on this host =="
if [[ -n "${token}" ]]; then
  echo "Jupyter (local):  http://127.0.0.1:${LAB_LOCAL_PORT}/lab?token=${token}"
  if [[ -n "${host_ip}" ]]; then
    echo "Jupyter (LAN):    http://${host_ip}:${LAB_LOCAL_PORT}/lab?token=${token}"
  fi
else
  echo "Jupyter (local):  http://127.0.0.1:${LAB_LOCAL_PORT}/lab"
fi
echo "noVNC:            http://127.0.0.1:${TELEOP_LOCAL_PORT}/vnc.html  (password: microduck)"
if [[ -n "${host_ip}" ]]; then
  echo "noVNC (LAN):      http://${host_ip}:${TELEOP_LOCAL_PORT}/vnc.html"
fi
echo "Stop tunnel:      pkill -f 'ssh .* -L ${BIND_ADDRESS}:${LAB_LOCAL_PORT}:127.0.0.1:${remote_lab}'"
