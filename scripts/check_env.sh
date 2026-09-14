#!/usr/bin/env bash
# Print lab runtime versions — no training logic.
set -euo pipefail

MICRODUCK_ROOT="${MICRODUCK_ROOT:-/opt/microduck_rl_unilab}"
LAB_ROOT="${LAB_ROOT:-/workspace/microduck_rl_lab}"

echo "=== MicroDuck RL Lab environment ==="
echo "LAB_ROOT=${LAB_ROOT}"
echo "MICRODUCK_ROOT=${MICRODUCK_ROOT}"
echo "UNILAB_EXTRA_REGISTRY_PACKAGES=${UNILAB_EXTRA_REGISTRY_PACKAGES:-<unset>}"
echo

python3 - <<'PY'
import importlib.metadata as md
import os
import sys

import torch

print(f"Python          {sys.version.split()[0]}")
print(f"PyTorch         {torch.__version__}")
hip = getattr(torch.version, "hip", None)
print(f"HIP (ROCm)      {hip or 'none (CUDA build?)'}")
print(f"CUDA available  {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU count       {torch.cuda.device_count()}")
    print(f"GPU 0           {torch.cuda.get_device_name(0)}")

for pkg in ("unilab", "unilab-rl", "unisim-core", "microduck_rl_unilab"):
    try:
        print(f"{pkg:18} {md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"{pkg:18} NOT INSTALLED")
PY

echo
if [[ -d "${MICRODUCK_ROOT}/.git" ]]; then
  echo "microduck_rl_unilab commit:"
  git -C "${MICRODUCK_ROOT}" log -1 --format="  %H %s"
else
  echo "microduck_rl_unilab: (no .git at ${MICRODUCK_ROOT})"
fi

echo
echo "Contract (deploy_contract.py): actor=61 critic=76 action=14"
echo "=== OK ==="
