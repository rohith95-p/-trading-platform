# Development Environment Startup Script (PowerShell)
# This script starts all services for local development

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Unified Trading Platform - Development" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if .env exists, if not copy from .env.development
if (-not (Test-Path .env)) {
    Write-Host "Creating .env from .env.development..." -ForegroundColor Yellow
    Copy-Item .env.development .env
    Write-Host "✓ .env created" -ForegroundColor Green
} else {
    Write-Host "✓ .env exists" -ForegroundColor Green
}

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker and try again." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host ""
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
docker-compose down

# Start services
Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
Write-Host ""
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        docker-compose exec -T postgres pg_isready -U trading_user | Out-Null
        break
    } catch {
        Write-Host "  Waiting for PostgreSQL..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $attempt++
    }
}
Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green

# Wait for Redis to be ready
Write-Host ""
Write-Host "Waiting for Redis to be ready..." -ForegroundColor Yellow
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        docker-compose exec -T redis redis-cli ping | Out-Null
        break
    } catch {
        Write-Host "  Waiting for Redis..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $attempt++
    }
}
Write-Host "✓ Redis is ready" -ForegroundColor Green

# Display service status
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Services Status" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
docker-compose ps

# Display connection information
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Connection Information" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "PostgreSQL: " -NoNewline
Write-Host "postgresql://trading_user:trading_password@localhost:5432/trading_db" -ForegroundColor Yellow
Write-Host "Redis:      " -NoNewline
Write-Host "redis://localhost:6379" -ForegroundColor Yellow
Write-Host ""

# Instructions for starting backend and frontend
Write-Host "========================================" -ForegroundColor Green
Write-Host "Next Steps" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "1. Start the backend:"
Write-Host "   " -NoNewline
Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "   " -NoNewline
Write-Host "uvicorn src.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Start the frontend (in a new terminal):"
Write-Host "   " -NoNewline
Write-Host "cd frontend" -ForegroundColor Yellow
Write-Host "   " -NoNewline
Write-Host "npm run dev" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Access the application:"
Write-Host "   Backend:  " -NoNewline
Write-Host "http://localhost:8000" -ForegroundColor Yellow
Write-Host "   Frontend: " -NoNewline
Write-Host "http://localhost:3000" -ForegroundColor Yellow
Write-Host "   API Docs: " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Development Tools" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Run tests:           " -NoNewline
Write-Host "pytest" -ForegroundColor Yellow
Write-Host "Run linting:         " -NoNewline
Write-Host "pylint src/" -ForegroundColor Yellow
Write-Host "Run type checking:   " -NoNewline
Write-Host "mypy src/" -ForegroundColor Yellow
Write-Host "Run formatting:      " -NoNewline
Write-Host "black src/" -ForegroundColor Yellow
Write-Host "Run pre-commit:      " -NoNewline
Write-Host "pre-commit run --all-files" -ForegroundColor Yellow
Write-Host ""
Write-Host "Stop services:       " -NoNewline
Write-Host "docker-compose down" -ForegroundColor Yellow
Write-Host "View logs:           " -NoNewline
Write-Host "docker-compose logs -f" -ForegroundColor Yellow
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Green
