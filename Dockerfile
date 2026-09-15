# One-hour MicroDuck Jupyter lab on AMD ROCm.
# Base image keeps a HIP-enabled torch 2.11.0 build; do not run `make sync-rocm`
# inside this container or uv may replace it with a CUDA wheel.
FROM rocm/pytorch:rocm7.14.1_ubuntu24.04_py3.12_pytorch_release_2.11.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    MUJOCO_GL=osmesa \
    PYOPENGL_PLATFORM=osmesa \
    LAB_ROOT=/workspace/microduck_rl_tutorial \
    MICRODUCK_ROOT=/opt/microduck_rl_unilab \
    LAB_LOG_ROOT=/workspace/runs \
    UNILAB_EXTRA_REGISTRY_PACKAGES=microduck_rl_unilab.tasks \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    ffmpeg \
    fluxbox \
    novnc \
    websockify \
    x11vnc \
    xvfb \
    libosmesa6 \
    libgl1 \
    libgl1-mesa-dri \
    libglfw3 \
    libxcursor1 \
    libxi6 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir \
    jupyterlab \
    matplotlib \
    pandas \
    ipywidgets \
    tensorboard

ARG MICRODUCK_REPO=https://github.com/rocPAI-Forge/microduck_rl_unilab.git
ARG MICRODUCK_REF=main
# Optional: fail the build if main drifts (default pins validated upstream main).
ARG MICRODUCK_EXPECTED_SHA=20fb528fa6c4a9559155b33e5304568668c7b7e2
RUN git clone "${MICRODUCK_REPO}" /opt/microduck_rl_unilab \
    && cd /opt/microduck_rl_unilab \
    && git fetch --depth 1 origin "${MICRODUCK_REF}" \
    && git checkout "${MICRODUCK_REF}" \
    && if [ -n "${MICRODUCK_EXPECTED_SHA}" ]; then \
         actual="$(git rev-parse HEAD)"; \
         case "${actual}" in \
           "${MICRODUCK_EXPECTED_SHA}"|${MICRODUCK_EXPECTED_SHA}*) ;; \
           *) echo "microduck_rl_unilab SHA mismatch: got ${actual}, expected ${MICRODUCK_EXPECTED_SHA}" >&2; exit 1;; \
         esac; \
       fi

# Keep the image torch; install UniLab wheels from PyPI.
RUN pip install --no-cache-dir \
    'unilab[mujoco]==1.0.0' \
    'unilab-rl==1.0.0' \
    'unisim-core==1.0.0' \
    && pip install --no-cache-dir --no-deps -e /opt/microduck_rl_unilab

WORKDIR /opt/microduck_rl_unilab
COPY . /workspace/microduck_rl_tutorial
RUN chmod +x /workspace/microduck_rl_tutorial/scripts/entrypoint.sh \
    /workspace/microduck_rl_tutorial/scripts/check_env.sh \
    /workspace/microduck_rl_tutorial/scripts/run_train.sh \
    /workspace/microduck_rl_tutorial/scripts/train_log_filter.py \
    /workspace/microduck_rl_tutorial/scripts/start_web_desktop.sh \
    /workspace/microduck_rl_tutorial/scripts/run_teleop.sh \
    /workspace/microduck_rl_tutorial/scripts/microduck_teleop.py

EXPOSE 8888 6080
ENTRYPOINT ["/workspace/microduck_rl_tutorial/scripts/entrypoint.sh"]
CMD ["jupyter"]
