"""watchdog.py -- restart main_loop if it dies.

Run this in a second terminal (or a Windows Task Scheduler task set to run at
logon). It checks every 30s that main_loop is alive via its lockfile PID and its
heartbeat file. If the process is gone OR the heartbeat is stale > 5 min, it
relaunches main_loop.

    python -m scripts.watchdog

NOTE: no alerting is wired up yet (no notification channel configured). This
only restarts + logs. Wire a Telegram/push call into `_alert()` when ready.
See docs/research/REAL_MONEY_READINESS.md part IV.1.
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core import resilience  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
CHECK_EVERY = 30
HEARTBEAT_MAX_AGE = 300  # seconds
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = sys.executable


def _now():
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _alert(msg: str):
    # TODO: wire a real notification channel here.
    print(f"[{_now()}] ALERT: {msg}")


def _loop_alive() -> bool:
    if not os.path.exists(resilience.LOCK_FILE):
        return False
    try:
        pid = int(open(resilience.LOCK_FILE).read().strip())
    except (ValueError, OSError):
        return False
    if not resilience._pid_alive(pid):
        return False
    # process is alive -- is it actually working?
    try:
        age = time.time() - os.path.getmtime(resilience.HEARTBEAT_FILE)
        if age > HEARTBEAT_MAX_AGE:
            print(f"[{_now()}] heartbeat stale ({age:.0f}s) though PID {pid} is alive")
            return False
    except OSError:
        return False
    return True


def _start_loop():
    print(f"[{_now()}] starting main_loop ...")
    log_path = os.path.join(ROOT, "logs", "main_loop.log")
    env = dict(os.environ, PYTHONPATH=ROOT)
    with open(log_path, "a") as logf:
        subprocess.Popen([PYTHON, "-u", "-m", "src.core.main_loop"],
                         cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)


def main():
    print(f"[{_now()}] watchdog started (check every {CHECK_EVERY}s)")
    consecutive_restarts = 0
    last_restart = 0.0
    while True:
        if os.path.exists(resilience.STOP_FILE):
            print(f"[{_now()}] STOP file present -- watchdog standing down (not restarting).")
            time.sleep(CHECK_EVERY)
            continue
        if not _loop_alive():
            now = time.time()
            if now - last_restart < 120:
                consecutive_restarts += 1
            else:
                consecutive_restarts = 1
            last_restart = now
            _alert(f"main_loop down -- restart #{consecutive_restarts}")
            if consecutive_restarts >= 5:
                _alert("5 restarts in a row -- something is broken. Watchdog pausing 30 min.")
                time.sleep(1800)
                consecutive_restarts = 0
            resilience.release_lock()
            _start_loop()
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
