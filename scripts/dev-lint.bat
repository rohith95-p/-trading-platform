@echo off
REM Code Linting Script for Windows

echo.
echo 🔍 Linting Code
echo ===============
echo.

REM Activate virtual environment if it exists
if exist venv (
    call venv\Scripts\activate.bat
)

REM Run Pylint on Python code
echo 🐍 Running Pylint on Python code...
pylint src\ --max-line-length=100 --disable=C0111,C0103
echo ✓ Pylint check complete
echo.

REM Run mypy for type checking
echo 🔬 Running mypy for type checking...
mypy src\ --ignore-missing-imports
echo ✓ Type checking complete
echo.

REM Run ESLint on JavaScript/TypeScript code
echo 📝 Running ESLint on JavaScript/TypeScript code...
call npx eslint frontend\ --ext .ts,.tsx
echo ✓ ESLint check complete
echo.

REM Run TypeScript compiler
echo 📝 Running TypeScript compiler...
cd frontend
call npx tsc --noEmit
cd ..
echo ✓ TypeScript compilation check complete
echo.

echo.
echo ✅ Linting complete!
echo.

pause
