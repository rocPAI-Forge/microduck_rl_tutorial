#!/usr/bin/env bash
# Start a private X desktop and expose it through noVNC for MuJoCo teleoperation.
set -euo pipefail

DISPLAY="${DISPLAY:-:1}"
DISPLAY_NUM="${DISPLAY#:}"
DISPLAY_NUM="${DISPLAY_NUM%%.*}"
SCREEN="${TELEOP_SCREEN:-1280x800x24}"
VNC_PASSWORD="${TELEOP_VNC_PASSWORD:-microduck}"
RUNTIME_DIR="/tmp/microduck-web-desktop"
mkdir -p "${RUNTIME_DIR}"

if [[ -s "${RUNTIME_DIR}/websockify.pid" ]] \
   && kill -0 "$(cat "${RUNTIME_DIR}/websockify.pid")" 2>/dev/null; then
  exit 0
fi

rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}"

Xvfb "${DISPLAY}" -screen 0 "${SCREEN}" -ac +extension GLX +render -noreset \
  >"${RUNTIME_DIR}/xvfb.log" 2>&1 &
echo "$!" >"${RUNTIME_DIR}/xvfb.pid"

# Give Xvfb time to create its socket before window-manager/VNC startup.
for _ in $(seq 1 50); do
  [[ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ]] && break
  sleep 0.1
done
if [[ ! -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ]]; then
  echo "Xvfb failed to start; see ${RUNTIME_DIR}/xvfb.log" >&2
  exit 1
fi

DISPLAY="${DISPLAY}" fluxbox >"${RUNTIME_DIR}/fluxbox.log" 2>&1 &
echo "$!" >"${RUNTIME_DIR}/fluxbox.pid"

x11vnc -storepasswd "${VNC_PASSWORD}" "${RUNTIME_DIR}/passwd" >/dev/null
x11vnc -display "${DISPLAY}" -rfbauth "${RUNTIME_DIR}/passwd" \
  -rfbport 5900 -localhost -forever -shared -noxdamage \
  >"${RUNTIME_DIR}/x11vnc.log" 2>&1 &
echo "$!" >"${RUNTIME_DIR}/x11vnc.pid"

NOVNC_WEB="${RUNTIME_DIR}/novnc-web"
mkdir -p "${NOVNC_WEB}"
ln -sfn /usr/share/novnc/* "${NOVNC_WEB}/"
printf '%s\n' '<!DOCTYPE html><meta http-equiv="refresh" content="0;url=vnc.html?autoconnect=1&resize=scale">' \
  >"${NOVNC_WEB}/index.html"

websockify --web="${NOVNC_WEB}" 6080 localhost:5900 \
  >"${RUNTIME_DIR}/websockify.log" 2>&1 &
echo "$!" >"${RUNTIME_DIR}/websockify.pid"

echo "MicroDuck web desktop ready on container port 6080 (DISPLAY=${DISPLAY})."
