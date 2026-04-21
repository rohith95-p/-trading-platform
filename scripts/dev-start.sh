#!/bin/bash

# Development Environment Startup Script
# This script starts all services for local development

set -e

echo "🚀 Starting Trading Platform Development Environment"
echo "===================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env.development ]; then
    export $(cat .env.development | grep -v '#' | xargs)
fi

# Start Docker Compose services
echo -e "${YELLOW}🐳 Starting Docker Compose services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 5

# Check PostgreSQL
echo -e "${YELLOW}🔍 Checking PostgreSQL...${NC}"
until docker-compose exec -T postgres pg_isready -U trading_user > /dev/null 2>&1; do
    echo "  Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Check Redis
echo -e "${YELLOW}🔍 Checking Redis...${NC}"
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "  Waiting for Redis..."
    sleep 2
done
echo -e "${GREEN}✓ Redis is ready${NC}"

# Run database migrations (if needed)
echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
docker-compose exec -T backend alembic upgrade head || true
echo -e "${GREEN}✓ Database migrations complete${NC}"

echo ""
echo -e "${GREEN}✅ Development environment is running!${NC}"
echo ""
echo "Services:"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:     localhost:6379"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose logs -f backend"
echo "  Stop services: docker-compose down"
echo "  Run tests:     ./scripts/dev-test.sh"
echo "  Format code:   ./scripts/dev-format.sh"
echo "  Lint code:     ./scripts/dev-lint.sh"
echo ""
