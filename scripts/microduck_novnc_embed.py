"""Embed the MicroDuck noVNC desktop in notebook 02.

The iframe host is always the hostname in the Jupyter URL (so a jump host
works). The port defaults to TELEOP_PUBLIC_PORT, which must be the noVNC
port on *that* hostname — not an internal container port.

If a jump host remaps Jupyter to 18888 but keeps noVNC at 16080, leave the
default. If it remaps noVNC as well, type the browser-side port in the widget
or set TELEOP_PUBLIC_PORT before compose up.
"""
from __future__ import annotations

import os
from html import escape
from pathlib import Path

from IPython.display import HTML, Javascript, display

PID_FILE = Path("/workspace/runs/.microduck_teleop.pid")
NOVNC_QUERY = "autoconnect=1&resize=scale"


def _teleop_running() -> tuple[bool, str]:
    try:
        teleop_pid = int(PID_FILE.read_text().strip())
        cmdline = Path(f"/proc/{teleop_pid}/cmdline").read_bytes().replace(b"\0", b" ")
        return b"microduck_teleop.py" in cmdline, str(teleop_pid)
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        return False, "?"


def display_teleop_frame(*, lang: str = "en") -> None:
    running, teleop_pid = _teleop_running()
    if not running:
        if lang == "zh":
            raise RuntimeError(
                "MicroDuck teleop 后台进程未运行。请先重新运行上方的模型启动 cell，"
                "看到新的 'teleop is ready' 输出后再运行本 cell；不要依据旧的已保存输出判断状态。"
            )
        raise RuntimeError(
            "The MicroDuck teleop background process is not running. Re-run the "
            "model-start cell above, wait for a fresh 'teleop is ready' line, then "
            "run this cell. Do not trust stale saved output."
        )

    port = int(os.environ.get("TELEOP_PUBLIC_PORT", os.environ.get("TELEOP_HOST_PORT", "16080")))
    password = escape(os.environ.get("TELEOP_VNC_PASSWORD", "microduck"))
    frame_id = "microduck-novnc-frame"
    port_input_id = "microduck-novnc-port"
    url_id = "microduck-novnc-url"

    if lang == "zh":
        title = f"MicroDuck 实时交互窗口（teleop PID：<code>{escape(teleop_pid)}</code>）"
        hint = (
            f"VNC 密码：<code>{password}</code>。连接后请点击桌面画面，使键盘焦点进入窗口。"
            "iframe 使用当前 Jupyter 的主机名，端口必须是你浏览器能打开的 noVNC 端口。"
        )
        reconnect = "重新连接"
        new_tab = "在新标签页打开"
        port_label = "此主机名上的 noVNC 端口"
        apply_label = "应用"
        footer = (
            "默认端口来自 GPU 宿主机的 TELEOP_PUBLIC_PORT。"
            "经跳板访问时：Jupyter 可以换端口，但 noVNC 应在同一主机名上保持这个端口；"
            "若跳板改了 noVNC 端口，在此改正并点应用。"
        )
    else:
        title = f"MicroDuck live interaction window (teleop PID: <code>{escape(teleop_pid)}</code>)"
        hint = (
            f"VNC password: <code>{password}</code>. After connecting, click the desktop "
            "so keyboard focus enters the window. The iframe uses this Jupyter hostname; "
            "the port must be the noVNC port reachable on that hostname."
        )
        reconnect = "Reconnect"
        new_tab = "Open in a new tab"
        port_label = "noVNC port on this hostname"
        apply_label = "Apply"
        footer = (
            "The default port is TELEOP_PUBLIC_PORT on the GPU host. Through a jump host, "
            "Jupyter may use another port, but noVNC should keep this number on the same "
            "hostname. If the jump remaps noVNC, correct the port here and apply."
        )

    display(
        HTML(
            f"""
<div style="padding:14px;border:1px solid #888;border-radius:8px;max-width:1000px">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap">
    <div>
      <b>{title}</b><br>
      {hint}
    </div>
    <div>
      <label>{port_label}
        <input id="{port_input_id}" type="number" min="1" max="65535" value="{port}"
               style="width:6em">
      </label>
      <button type="button" id="microduck-novnc-apply">{apply_label}</button>
      <button type="button" id="microduck-novnc-reconnect">{reconnect}</button>
      <a id="microduck-novnc-newtab" href="#" target="_blank" rel="noopener">{new_tab}</a>
    </div>
  </div>
  <div style="margin-top:8px;font-size:12px;opacity:0.85">
    URL: <code id="{url_id}"></code>
  </div>
  <iframe id="{frame_id}" title="MicroDuck noVNC teleop"
          style="width:100%;height:680px;margin-top:12px;border:1px solid #555;background:#111"
          allow="clipboard-read; clipboard-write; fullscreen"
          allowfullscreen></iframe>
  <small>{footer}</small>
</div>
"""
        )
    )
    display(
        Javascript(
            f"""
(() => {{
  const defaultPort = String({port});
  const frame = document.getElementById('{frame_id}');
  const input = document.getElementById('{port_input_id}');
  const urlEl = document.getElementById('{url_id}');
  const applyBtn = document.getElementById('microduck-novnc-apply');
  const reconnectBtn = document.getElementById('microduck-novnc-reconnect');
  const newTab = document.getElementById('microduck-novnc-newtab');
  const storageKey = 'microduck-novnc-port:' + window.location.hostname;

  function teleopUrl(p) {{
    return window.location.protocol + '//' + window.location.hostname +
           ':' + p + '/vnc.html?{NOVNC_QUERY}';
  }}

  function currentPort() {{
    const typed = (input && input.value) ? input.value.trim() : '';
    if (/^[0-9]+$/.test(typed)) return typed;
    return window.localStorage.getItem(storageKey) || defaultPort;
  }}

  function apply(save) {{
    const p = currentPort();
    if (save && input) window.localStorage.setItem(storageKey, p);
    const url = teleopUrl(p);
    if (urlEl) urlEl.textContent = url;
    if (newTab) newTab.href = url;
    if (frame) frame.src = url;
  }}

  if (input) {{
    const saved = window.localStorage.getItem(storageKey);
    if (saved) input.value = saved;
  }}
  if (applyBtn) applyBtn.onclick = () => apply(true);
  if (reconnectBtn) reconnectBtn.onclick = () => apply(false);
  if (newTab) newTab.onclick = () => {{ newTab.href = teleopUrl(currentPort()); }};
  apply(false);
}})();
"""
        )
    )
