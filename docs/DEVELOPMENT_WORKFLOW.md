# Development Workflow Guide

This guide explains how to set up and work with the Unified Trading Intelligence Platform in a local development environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Starting Development Environment](#starting-development-environment)
4. [Development Workflow](#development-workflow)
5. [Code Quality Tools](#code-quality-tools)
6. [Testing](#testing)
7. [Database Management](#database-management)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **Docker Desktop** - For PostgreSQL and Redis containers
- **Git** - Version control

### Verify Installation

```bash
python --version  # Should be 3.11 or higher
node --version    # Should be 18 or higher
docker --version  # Should be installed and running
git --version     # Should be installed
```

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd unified-trading-platform
```

### 2. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (CMD):
.\venv\Scripts\activate.bat

# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Frontend Environment

```bash
cd frontend
npm install
cd ..
```

### 4. Setup Pre-commit Hooks

```bash
pre-commit install
```

### 5. Create Environment File

```bash
# Copy development environment template
cp .env.development .env

# Edit .env and add your API keys (optional for basic development)
```

---

## Starting Development Environment

### Quick Start (Recommended)

**On Windows (PowerShell):**
```powershell
.\dev.ps1
```

**On Linux/Mac:**
```bash
./dev.sh
```

This script will:
- Check prerequisites
- Start PostgreSQL and Redis containers
- Wait for services to be ready
- Display connection information
- Show next steps

### Manual Start

If you prefer to start services manually:

```bash
# Start Docker services
docker-compose up -d postgres redis

# Wait for services to be ready
docker-compose ps

# Start backend (in terminal 1)
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in terminal 2)
cd frontend
npm run dev
```

### Access the Application

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **PostgreSQL**: postgresql://trading_user:trading_password@localhost:5432/trading_db
- **Redis**: redis://localhost:6379

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit files in `src/` (backend) or `frontend/` (frontend).

### 3. Run Code Quality Checks

```bash
# Format code
black src/
cd frontend && npm run format

# Run linting
pylint src/
cd frontend && npm run lint

# Run type checking
mypy src/
cd frontend && npm run type-check
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_interfaces.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

Pre-commit hooks will automatically:
- Format code with Black and Prettier
- Run linting with Pylint and ESLint
- Run type checking with mypy
- Check for common issues

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

---

## Code Quality Tools

### Python Tools

#### Black (Code Formatting)

```bash
# Format all Python files
black src/

# Check formatting without making changes
black --check src/

# Format specific file
black src/main.py
```

Configuration: `pyproject.toml` (line length: 100)

#### Pylint (Linting)

```bash
# Lint all Python files
pylint src/

# Lint specific file
pylint src/main.py

# Lint with specific configuration
pylint --rcfile=.pylintrc src/
```

Configuration: `.pylintrc` and `pyproject.toml`

#### Mypy (Type Checking)

```bash
# Type check all Python files
mypy src/

# Type check specific file
mypy src/main.py

# Type check with strict mode
mypy --strict src/
```

Configuration: `mypy.ini` and `pyproject.toml`

### Frontend Tools

#### Prettier (Code Formatting)

```bash
cd frontend

# Format all files
npm run format

# Check formatting
npm run format:check
```

Configuration: `frontend/.prettierrc`

#### ESLint (Linting)

```bash
cd frontend

# Lint all files
npm run lint

# Fix auto-fixable issues
npm run lint:fix
```

Configuration: `frontend/.eslintrc.json`

#### TypeScript (Type Checking)

```bash
cd frontend

# Type check
npm run type-check

# Type check in watch mode
npm run type-check:watch
```

Configuration: `frontend/tsconfig.json`

---

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_interfaces.py::TestExchangeConnector::test_place_order

# Run tests matching pattern
pytest -k "test_exchange"

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Property-Based Tests

Property-based tests use Hypothesis to generate test cases:

```bash
# Run property tests
pytest -m property

# Run with more examples
pytest -m property --hypothesis-seed=12345
```

---

## Database Management

### Access PostgreSQL

```bash
# Using Docker
docker-compose exec postgres psql -U trading_user -d trading_db

# Using psql directly
psql postgresql://trading_user:trading_password@localhost:5432/trading_db
```

### Common Database Commands

```sql
-- List tables
\dt

-- Describe table
\d users

-- View table data
SELECT * FROM users;

-- Exit psql
\q
```

### Reset Database

```bash
# Stop containers
docker-compose down

# Remove volumes (WARNING: This deletes all data)
docker-compose down -v

# Start fresh
docker-compose up -d postgres redis
```

### Run Migrations

```bash
# Apply schema
docker-compose exec postgres psql -U trading_user -d trading_db -f /docker-entrypoint-initdb.d/01-init.sql

# Apply seed data
docker-compose exec postgres psql -U trading_user -d trading_db -f /docker-entrypoint-initdb.d/02-seed.sql
```

### Access Redis

```bash
# Using Docker
docker-compose exec redis redis-cli

# Common Redis commands
PING          # Test connection
KEYS *        # List all keys
GET key       # Get value
SET key value # Set value
FLUSHALL      # Clear all data (WARNING: Deletes everything)
```

---

## Troubleshooting

### Docker Issues

**Problem**: Docker containers won't start

```bash
# Check Docker is running
docker info

# Check container logs
docker-compose logs postgres
docker-compose logs redis

# Restart containers
docker-compose restart

# Rebuild containers
docker-compose up -d --build
```

**Problem**: Port already in use

```bash
# Find process using port 5432 (PostgreSQL)
# Windows:
netstat -ano | findstr :5432

# Linux/Mac:
lsof -i :5432

# Kill the process or change port in docker-compose.yml
```

### Python Issues

**Problem**: Module not found

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Problem**: Import errors

```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"  # Linux/Mac
$env:PYTHONPATH = "$env:PYTHONPATH;$PWD\src"  # Windows PowerShell
```

### Frontend Issues

**Problem**: npm install fails

```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf frontend/node_modules
cd frontend && npm install
```

**Problem**: Port 3000 already in use

```bash
# Change port in package.json or use different port
cd frontend
PORT=3001 npm run dev
```

### Database Issues

**Problem**: Cannot connect to PostgreSQL

```bash
# Check container is running
docker-compose ps

# Check logs
docker-compose logs postgres

# Verify connection string
echo $DATABASE_URL
```

**Problem**: Tables not created

```bash
# Manually run init script
docker-compose exec postgres psql -U trading_user -d trading_db -f /docker-entrypoint-initdb.d/01-init.sql
```

---

## Best Practices

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions small and focused
- Use meaningful variable names

### Git Workflow

- Create feature branches from `main`
- Write descriptive commit messages
- Keep commits atomic and focused
- Rebase before merging to keep history clean
- Delete branches after merging

### Testing

- Write tests for all new features
- Aim for 80%+ code coverage
- Use property-based tests for complex logic
- Mock external dependencies
- Test edge cases and error conditions

### Documentation

- Update README when adding features
- Document API endpoints in code
- Keep this guide up to date
- Add inline comments for complex logic
- Update type hints when changing signatures

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Pylint Documentation](https://pylint.pycqa.org/)
- [Mypy Documentation](https://mypy.readthedocs.io/)

---

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting](#troubleshooting) section
2. Search existing GitHub issues
3. Ask in the team chat
4. Create a new GitHub issue with:
   - Description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

---

**Happy coding! 🚀**
