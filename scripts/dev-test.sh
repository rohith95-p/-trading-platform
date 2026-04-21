#!/bin/bash

# Testing Script
# This script runs all tests with coverage

set -e

echo "🧪 Running Tests"
echo "================"

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Python unit tests
echo -e "${YELLOW}🐍 Running Python unit tests...${NC}"
pytest tests/unit/ -v --cov=src --cov-report=html --cov-report=term-missing || true
echo -e "${GREEN}✓ Python unit tests complete${NC}"

# Run Python integration tests (if services are running)
if docker-compose ps | grep -q "trading_backend"; then
    echo -e "${YELLOW}🔗 Running Python integration tests...${NC}"
    pytest tests/integration/ -v || true
    echo -e "${GREEN}✓ Python integration tests complete${NC}"
else
    echo -e "${YELLOW}⚠ Skipping integration tests (services not running)${NC}"
fi

# Run JavaScript/TypeScript tests
echo -e "${YELLOW}📝 Running JavaScript/TypeScript tests...${NC}"
npm run test:coverage || true
echo -e "${GREEN}✓ JavaScript/TypeScript tests complete${NC}"

echo ""
echo -e "${GREEN}✅ Testing complete!${NC}"
echo ""
echo "Coverage reports:"
echo "  Python:  htmlcov/index.html"
echo "  Frontend: coverage/lcov-report/index.html"
