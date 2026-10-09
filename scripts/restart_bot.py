"""
Quick bot restart with state cleanup.
Use when dedup bug detected or bot needs hard reset.
"""
import subprocess
import time
from pathlib import Path

def restart_bot():
    print("1. Stopping bot...")
    subprocess.run(
        ["powershell", "-Command", 
         "Get-Process python | Where-Object { $_.CommandLine -like '*main_loop.py*' } | Stop-Process -Force"],
        shell=True,
        capture_output=True
    )
    
    print("2. Clearing stale state...")
    loop_state = Path("c:/projects/ultra_core/logs/loop_state.json")
    if loop_state.exists():
        loop_state.unlink()
        print("   ✅ Deleted loop_state.json")
    
    print("3. Starting bot...")
    time.sleep(2)
    subprocess.Popen(
        ["python", "-m", "src.core.main_loop"],
        cwd="c:/projects/ultra_core"
    )
    
    print("✅ Bot restarted with clean state")
    print("   Check heartbeat in 30 seconds: python scripts/bot_status.py")

if __name__ == "__main__":
    restart_bot()
