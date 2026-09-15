#!/usr/bin/env bash
# Launch/stop one-robot MicroDuck policy inference in the browser VNC desktop.
set -euo pipefail

LAB_ROOT="${LAB_ROOT:-/workspace/microduck_rl_tutorial}"
MICRODUCK_ROOT="${MICRODUCK_ROOT:-/opt/microduck_rl_unilab}"
RUN_ROOT="${LAB_LOG_ROOT:-/workspace/runs}"
PID_FILE="${RUN_ROOT}/.microduck_teleop.pid"
LOG_FILE="${RUN_ROOT}/logs/teleop.log"
SELECTOR="${1:-latest}"
mkdir -p "$(dirname "${LOG_FILE}")"

is_teleop_pid() {
  local pid="${1:-}"
  [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
  [[ -r "/proc/${pid}/cmdline" ]] || return 1
  tr '\0' ' ' <"/proc/${pid}/cmdline" | grep -q "microduck_teleop.py"
}

stop_teleop() {
  if [[ -s "${PID_FILE}" ]]; then
    local pid
    pid="$(cat "${PID_FILE}")"
    if is_teleop_pid "${pid}"; then
      kill "${pid}" 2>/dev/null || true
      for _ in $(seq 1 30); do
        kill -0 "${pid}" 2>/dev/null || break
        sleep 0.1
      done
      kill -9 "${pid}" 2>/dev/null || true
      echo "Stopped MicroDuck teleop (PID ${pid})."
    fi
    rm -f "${PID_FILE}"
  fi
}

if [[ "${SELECTOR}" == "stop" ]]; then
  stop_teleop
  exit 0
fi

stop_teleop

find_latest_run() {
  python3 - "${RUN_ROOT}/MicroduckVelocityFlat" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
candidates = []
for summary in root.glob("*_mujoco/run_summary.json"):
    run = summary.parent
    try:
        completed = int(json.loads(summary.read_text()).get("completed_iterations", -1))
    except (OSError, ValueError, TypeError):
        continue
    if completed >= 299 and any(run.glob("model_*.pt")):
        candidates.append(run)
if candidates:
    print(max(candidates, key=lambda path: path.stat().st_mtime))
PY
}

case "${SELECTOR}" in
  demo)
    RUN_DIR="${LAB_ROOT}/examples/velocity_flat_demo"
    ;;
  latest|auto)
    RUN_DIR="$(find_latest_run)"
    if [[ -z "${RUN_DIR}" ]]; then
      if [[ "${SELECTOR}" == "auto" ]]; then
        RUN_DIR="${LAB_ROOT}/examples/velocity_flat_demo"
        echo "No completed 300-iteration run found; using bundled demo."
      else
        echo "No completed 300-iteration run found under ${RUN_ROOT}/MicroduckVelocityFlat." >&2
        echo "Run phase 1 first, or launch the bundled model with: run_teleop.sh demo" >&2
        exit 2
      fi
    fi
    ;;
  /*)
    RUN_DIR="${SELECTOR}"
    ;;
  *)
    echo "Usage: $0 [auto|latest|demo|/absolute/run/path|stop]" >&2
    exit 2
    ;;
esac

if [[ ! -d "${RUN_DIR}" ]] || ! compgen -G "${RUN_DIR}/model_*.pt" >/dev/null; then
  echo "Checkpoint run is invalid or has no model_*.pt: ${RUN_DIR}" >&2
  exit 2
fi

: >"${LOG_FILE}"
cd "${MICRODUCK_ROOT}"
nohup env \
  DISPLAY="${DISPLAY:-:1}" \
  MUJOCO_GL=glfw \
  PYOPENGL_PLATFORM=glfw \
  UNILAB_EXTRA_REGISTRY_PACKAGES="${UNILAB_EXTRA_REGISTRY_PACKAGES:-microduck_rl_unilab.tasks}" \
  python3 -u "${LAB_ROOT}/scripts/microduck_teleop.py" \
  --algo ppo --task microduck_velocity_flat --sim mujoco \
  "hydra.searchpath=[file://${MICRODUCK_ROOT}/src/microduck_rl_unilab/conf/ppo]" \
  "algo.load_run=${RUN_DIR}" \
  "training.log_root=${RUN_ROOT}" \
  interactive.action_mode=policy \
  interactive.policy_obs_mode=actor \
  interactive.keyboard=true \
  interactive.keyboard_step_lin=0.1 \
  interactive.keyboard_step_ang=0.2 \
  interactive.camera_distance=0.9 \
  interactive.camera_elevation=-18 \
  >>"${LOG_FILE}" 2>&1 </dev/null &
TELEOP_PID=$!
echo "${TELEOP_PID}" >"${PID_FILE}"

for _ in $(seq 1 90); do
  if grep -q "Opening viewer" "${LOG_FILE}"; then
    echo "MicroDuck teleop is ready (PID ${TELEOP_PID})."
    echo "Checkpoint: ${RUN_DIR}"
    echo "Log: ${LOG_FILE}"
    exit 0
  fi
  if ! kill -0 "${TELEOP_PID}" 2>/dev/null; then
    echo "MicroDuck teleop failed to start. Last log lines:" >&2
    tail -30 "${LOG_FILE}" >&2
    rm -f "${PID_FILE}"
    exit 1
  fi
  sleep 0.5
done

echo "Teleop is still starting; inspect ${LOG_FILE}." >&2
exit 1
