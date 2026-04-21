@echo off
REM Development Environment Setup Script for Windows
REM This script sets up the local development environment for the Trading Platform

setlocal enabledelayedexpansion

echo.
echo 🚀 Trading Platform - Development Environment Setup
echo ==================================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Desktop first.
    exit /b 1
)

echo ✓ Docker and Docker Compose are installed
echo.

REM Check if .env.development exists
if not exist .env.development (
    echo ⚠ .env.development not found. Creating from template...
    copy .env.example .env.development
    echo ✓ Created .env.development
    echo.
)

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist sql mkdir sql
if not exist logs mkdir logs
if not exist scripts mkdir scripts
echo ✓ Directories created
echo.

REM Check if Python virtual environment exists
if not exist venv (
    echo 🐍 Creating Python virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
    echo.
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo 📦 Installing Python dependencies...
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo ✓ Python dependencies installed
echo.

REM Install Node dependencies
if exist package.json (
    echo 📦 Installing Node dependencies...
    call npm install
    echo ✓ Node dependencies installed
    echo.
)

REM Setup pre-commit hooks
echo 🪝 Setting up pre-commit hooks...
pip install pre-commit
pre-commit install
echo ✓ Pre-commit hooks installed
echo.

REM Build Docker images
echo 🐳 Building Docker images...
docker-compose build
echo ✓ Docker images built
echo.

echo.
echo ✅ Development environment setup complete!
echo.
echo Next steps:
echo 1. Start the development environment: .\scripts\dev-start.bat
echo 2. Run tests: .\scripts\dev-test.bat
echo 3. Format code: .\scripts\dev-format.bat
echo 4. Lint code: .\scripts\dev-lint.bat
echo.

pause
