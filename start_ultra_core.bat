@echo off
cd /d "c:\projects\ultra_core"
call venv\Scripts\activate.bat 2>nul
echo Starting Ultra Core Watchdog...
python scripts\watchdog.py
