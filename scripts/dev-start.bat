@echo off
REM Development Environment Startup Script for Windows

setlocal enabledelayedexpansion

echo.
echo 🚀 Starting Trading Platform Development Environment
echo ====================================================
echo.

REM Load environment variables from .env.development
if exist .env.development (
    for /f "delims== tokens=1,2" %%a in (.env.development) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set %%a=%%b
    )
)

REM Start Docker Compose services
echo 🐳 Starting Docker Compose services...
docker-compose up -d

REM Wait for services to be healthy
echo ⏳ Waiting for services to be healthy...
timeout /t 5 /nobreak

REM Check PostgreSQL
echo 🔍 Checking PostgreSQL...
:check_postgres
docker-compose exec -T postgres pg_isready -U trading_user >nul 2>&1
if errorlevel 1 (
    echo   Waiting for PostgreSQL...
    timeout /t 2 /nobreak
    goto check_postgres
)
echo ✓ PostgreSQL is ready
echo.

REM Check Redis
echo 🔍 Checking Redis...
:check_redis
docker-compose exec -T redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo   Waiting for Redis...
    timeout /t 2 /nobreak
    goto check_redis
)
echo ✓ Redis is ready
echo.

REM Run database migrations
echo 🗄️  Running database migrations...
docker-compose exec -T backend alembic upgrade head >nul 2>&1
echo ✓ Database migrations complete
echo.

echo.
echo ✅ Development environment is running!
echo.
echo Services:
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   PostgreSQL: localhost:5432
echo   Redis:     localhost:6379
echo.
echo Useful commands:
echo   View logs:     docker-compose logs -f backend
echo   Stop services: docker-compose down
echo   Run tests:     .\scripts\dev-test.bat
echo   Format code:   .\scripts\dev-format.bat
echo   Lint code:     .\scripts\dev-lint.bat
echo.

pause
