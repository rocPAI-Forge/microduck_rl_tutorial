#!/usr/bin/env python3
"""Read microduck-train stdout; emit one throttled status line for Jupyter."""
import os
import re
import sys

REFRESH = max(1, int(os.environ.get("LAB_LOG_EVERY", "10") or "10"))
ANSI = re.compile(r"\033\[[0-9;]*m")
ITER_RE = re.compile(r"Learning iteration\s+(\d+)/(\d+)")
ERR_RE = re.compile(r"Error|Traceback|ModuleNotFoundError|Resuming from")


def plain(raw: str) -> str:
    return ANSI.sub("", raw).strip()


cur = mx = 0
reward = ep_len = elapsed = eta = it_time = ""


def show(final: bool = False) -> None:
    if mx <= 0:
        return
    line = (
        f"[train] iter {cur:4d}/{mx} | "
        f"reward {reward:>7} | ep {ep_len:>6} | "
        f"{elapsed:>8} | ETA {eta:>8} | {it_time:>5}/iter"
    )
    if final:
        sys.stdout.write("\r\033[K" + line + "\n")
    else:
        sys.stdout.write("\r\033[K" + line)
    sys.stdout.flush()


for raw in sys.stdin:
    line = plain(raw)
    m = ITER_RE.search(line)
    if m:
        cur, mx = int(m.group(1)), int(m.group(2))
        reward = ep_len = elapsed = eta = it_time = "..."
        continue
    if line.startswith("Mean reward:"):
        reward = line.split(":", 1)[1].strip()
    elif line.startswith("Mean episode length:"):
        ep_len = line.split(":", 1)[1].strip()
    elif line.startswith("Iteration time:"):
        it_time = line.split(":", 1)[1].strip()
    elif line.startswith("Time elapsed:"):
        elapsed = line.split(":", 1)[1].strip()
    elif line.startswith("ETA:"):
        eta = line.split(":", 1)[1].strip()
        if cur <= 1 or cur % REFRESH == 0 or cur >= mx - 1:
            show(final=(cur >= mx - 1))
    elif ERR_RE.search(line):
        sys.stdout.write("\n")
        print(line, flush=True)

sys.stdout.write("\n")
sys.stdout.flush()
