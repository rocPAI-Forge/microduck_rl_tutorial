#!/usr/bin/env bash
set -euo pipefail

export LAB_ROOT="${LAB_ROOT:-/workspace/microduck_rl_lab}"
export MICRODUCK_ROOT="${MICRODUCK_ROOT:-/opt/microduck_rl_unilab}"
export UNILAB_EXTRA_REGISTRY_PACKAGES="${UNILAB_EXTRA_REGISTRY_PACKAGES:-microduck_rl_unilab.tasks}"
export MUJOCO_GL="${MUJOCO_GL:-osmesa}"
export PYOPENGL_PLATFORM="${PYOPENGL_PLATFORM:-osmesa}"

mkdir -p /workspace/runs
# XML assets are resolved relative to the task repo, not the notebook repo.
cd "${MICRODUCK_ROOT}"

if [[ "${1:-}" == "jupyter" || "${1:-}" == "lab" ]]; then
  shift || true
  "${LAB_ROOT}/scripts/start_web_desktop.sh"
  if [[ "${TELEOP_AUTOSTART:-demo}" != "off" ]]; then
    bash "${LAB_ROOT}/scripts/run_teleop.sh" "${TELEOP_AUTOSTART:-demo}" \
      > /tmp/microduck-teleop-autostart.log 2>&1 &
  fi
  exec jupyter lab \
    --ip=0.0.0.0 \
    --port="${JUPYTER_PORT:-8888}" \
    --no-browser \
    --allow-root \
    --notebook-dir="${LAB_ROOT}/notebooks" \
    "$@"
fi

if [[ "${1:-}" == "bash" ]]; then
  exec bash "$@"
fi

exec "$@"
