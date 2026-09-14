#!/usr/bin/env bash
# Full log → file only; notebook sees throttled status (no raw microduck-train stdout)
set -euo pipefail

MICRODUCK_ROOT="${MICRODUCK_ROOT:-/opt/microduck_rl_unilab}"
LAB_ROOT="${LAB_ROOT:-/workspace/microduck_rl_lab}"
LOG="${LAB_TRAIN_LOG:-/workspace/runs/logs/last_train.log}"
LAB_LOG_EVERY="${LAB_LOG_EVERY:-10}"
FILTER="${LAB_ROOT}/scripts/train_log_filter.py"
mkdir -p "$(dirname "$LOG")"

echo "=== microduck-train (quiet) ==="
echo "Full log: ${LOG}"
echo "Status: 单行每 ${LAB_LOG_EVERY} iter 刷新（export LAB_LOG_EVERY=10 可调）"
echo ""

cd "${MICRODUCK_ROOT}"
export LAB_LOG_EVERY

# Train in background — nothing from microduck-train goes to notebook stdout
: > "${LOG}"
microduck-train "$@" >> "${LOG}" 2>&1 &
TRAIN_PID=$!

cleanup() {
  kill "${TRAIN_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Tail log through filter until training exits
tail -F -n +1 "${LOG}" 2>/dev/null | python3 -u "${FILTER}" &
FILTER_PID=$!

wait "${TRAIN_PID}"
TRAIN_RC=$?
kill "${FILTER_PID}" 2>/dev/null || true
wait "${FILTER_PID}" 2>/dev/null || true
trap - EXIT INT TERM

echo ""
echo "=== done ==="
echo "Full log: ${LOG}"
if [[ -d /workspace/runs/MicroduckVelocityFlat ]]; then
  latest="$(ls -td /workspace/runs/MicroduckVelocityFlat/*_mujoco 2>/dev/null | head -1 || true)"
  [[ -n "${latest}" ]] && echo "Latest run: ${latest}"
fi

exit "${TRAIN_RC}"
