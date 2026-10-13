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
from src.core import alerts  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
CHECK_EVERY = 30
HEARTBEAT_MAX_AGE = 300  # seconds
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = sys.executable


def _now():
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _alert(msg: str, severity: str = alerts.WARN):
    """Real notification channel as of 2026-09-06 (IV.1). Configure via
    ULTRA_ALERT_TELEGRAM_TOKEN/_CHAT or ULTRA_ALERT_WEBHOOK; without them this
    still records to logs/alerts.log and stdout."""
    alerts.send(msg, severity=severity, context={"source": "watchdog"})


def _protect_profit_alive() -> bool:
    """Check if protect_profit.py is running without relying on deprecated wmic."""
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = " ".join(proc.info.get('cmdline') or [])
                if "protect_profit" in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except Exception:
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Select-Object -ExpandProperty CommandLine"],
                capture_output=True, text=True, timeout=10)
            return "protect_profit" in (out.stdout or "")
        except Exception:
            return True  # can't tell -> don't cry wolf


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
            print(f"[{_now()}] heartbeat stale ({age:.0f}s) though PID {pid} is alive "
                  f"-- HUNG. force-killing {pid}.")
            _force_kill(pid)
            return False
    except OSError:
        return False
    return True


def _force_kill(pid):
    """Kill a hung process so acquire_lock() won't refuse the restart."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
        else:
            os.kill(pid, 9)
        time.sleep(2)
    except Exception as e:
        print(f"[{_now()}] force-kill failed: {e}")


def _start_loop():
    print(f"[{_now()}] starting main_loop ...")
    log_path = os.path.join(ROOT, "logs", "main_loop.log")
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if os.path.exists(resilience.LOCK_FILE):
        try:
            old_pid = int(open(resilience.LOCK_FILE).read().strip())
            if not resilience._pid_alive(old_pid):
                os.remove(resilience.LOCK_FILE)
        except Exception:
            pass
    with open(log_path, "a", encoding="utf-8") as logf:
        subprocess.Popen([PYTHON, "-X", "utf8", "-u", "-m", "src.core.main_loop"],
                         cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)


def main():
    print(f"[{_now()}] watchdog started (check every {CHECK_EVERY}s)")
    if not alerts.configured():
        print(f"[{_now()}] NOTE: no alert channel configured "
              f"(set ULTRA_ALERT_TELEGRAM_TOKEN/_CHAT or ULTRA_ALERT_WEBHOOK). "
              f"Alerts will still be written to logs/alerts.log.")
    _alert("watchdog started", alerts.INFO)
    consecutive_restarts = 0
    last_restart = 0.0
    pp_warned = False
    while True:
        if os.path.exists(resilience.STOP_FILE):
            print(f"[{_now()}] STOP file present -- watchdog standing down (not restarting).")
            time.sleep(CHECK_EVERY)
            continue

        # Watch the other safety layer too, not just main_loop.
        if not _protect_profit_alive():
            if not pp_warned:
                _alert("protect_profit.py is NOT running -- ATTEMPTING RESTART.", alerts.WARN)
                pp_warned = True
                
            # Actually restart protect_profit.py safely (avoid fork bomb if it crashes immediately)
            now = time.time()
            if 'last_pp_restart' not in locals() or now - last_pp_restart > 300:
                print(f"[{_now()}] starting protect_profit.py ...")
                pp_log_path = os.path.join(ROOT, "logs", "protect_profit.log")
                env = dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
                with open(pp_log_path, "a", encoding="utf-8") as logf:
                    subprocess.Popen([PYTHON, "-X", "utf8", "-u", "scripts/protect_profit.py"],
                                     cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)
                last_pp_restart = now
                time.sleep(2)  # Give it a moment to start
        else:
            pp_warned = False

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
            if os.path.exists(resilience.LOCK_FILE):
                try:
                    old_pid = int(open(resilience.LOCK_FILE).read().strip())
                    if not resilience._pid_alive(old_pid):
                        os.remove(resilience.LOCK_FILE)
                except Exception:
                    pass
            _start_loop()
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
