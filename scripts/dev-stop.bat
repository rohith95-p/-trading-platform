@echo off
REM Development Environment Stop Script for Windows

echo.
echo 🛑 Stopping Trading Platform Development Environment
echo ====================================================
echo.

echo 🐳 Stopping Docker Compose services...
docker-compose down

echo.
echo ✅ Development environment stopped
echo.

pause
