#!/bin/bash
# Development Environment Startup Script
# This script starts all services for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Unified Trading Platform - Development${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if .env exists, if not copy from .env.development
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from .env.development...${NC}"
    cp .env.development .env
    echo -e "${GREEN}✓ .env created${NC}"
else
    echo -e "${GREEN}✓ .env exists${NC}"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Stop any existing containers
echo ""
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo ""
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
until docker-compose exec -T postgres pg_isready -U trading_user > /dev/null 2>&1; do
    echo -e "${YELLOW}  Waiting for PostgreSQL...${NC}"
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Wait for Redis to be ready
echo ""
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo -e "${YELLOW}  Waiting for Redis...${NC}"
    sleep 2
done
echo -e "${GREEN}✓ Redis is ready${NC}"

# Display service status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Services Status${NC}"
echo -e "${GREEN}========================================${NC}"
docker-compose ps

# Display connection information
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Connection Information${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "PostgreSQL: ${YELLOW}postgresql://trading_user:trading_password@localhost:5432/trading_db${NC}"
echo -e "Redis:      ${YELLOW}redis://localhost:6379${NC}"
echo ""

# Instructions for starting backend and frontend
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Next Steps${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "1. Start the backend:"
echo -e "   ${YELLOW}source venv/bin/activate${NC}  # Activate virtual environment"
echo -e "   ${YELLOW}uvicorn src.main:app --reload --host 0.0.0.0 --port 8000${NC}"
echo ""
echo -e "2. Start the frontend (in a new terminal):"
echo -e "   ${YELLOW}cd frontend${NC}"
echo -e "   ${YELLOW}npm run dev${NC}"
echo ""
echo -e "3. Access the application:"
echo -e "   Backend:  ${YELLOW}http://localhost:8000${NC}"
echo -e "   Frontend: ${YELLOW}http://localhost:3000${NC}"
echo -e "   API Docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Development Tools${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Run tests:           ${YELLOW}pytest${NC}"
echo -e "Run linting:         ${YELLOW}pylint src/${NC}"
echo -e "Run type checking:   ${YELLOW}mypy src/${NC}"
echo -e "Run formatting:      ${YELLOW}black src/${NC}"
echo -e "Run pre-commit:      ${YELLOW}pre-commit run --all-files${NC}"
echo ""
echo -e "Stop services:       ${YELLOW}docker-compose down${NC}"
echo -e "View logs:           ${YELLOW}docker-compose logs -f${NC}"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
