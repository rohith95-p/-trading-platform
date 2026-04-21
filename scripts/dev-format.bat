@echo off
REM Code Formatting Script for Windows

echo.
echo 🎨 Formatting Code
echo ==================
echo.

REM Activate virtual environment if it exists
if exist venv (
    call venv\Scripts\activate.bat
)

REM Format Python code with Black
echo 🐍 Formatting Python code with Black...
black src\ tests\ --line-length=100
echo ✓ Python code formatted
echo.

REM Format JavaScript/TypeScript code with Prettier
echo 📝 Formatting JavaScript/TypeScript code with Prettier...
call npx prettier --write "frontend/**/*.{ts,tsx,json,md}"
echo ✓ JavaScript/TypeScript code formatted
echo.

echo.
echo ✅ Code formatting complete!
echo.

pause
