#!/bin/bash

# Code Linting Script
# This script runs linting and type checking

set -e

echo "🔍 Linting Code"
echo "==============="

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Pylint on Python code
echo -e "${YELLOW}🐍 Running Pylint on Python code...${NC}"
pylint src/ --max-line-length=100 --disable=C0111,C0103 || true
echo -e "${GREEN}✓ Pylint check complete${NC}"

# Run mypy for type checking
echo -e "${YELLOW}🔬 Running mypy for type checking...${NC}"
mypy src/ --ignore-missing-imports || true
echo -e "${GREEN}✓ Type checking complete${NC}"

# Run ESLint on JavaScript/TypeScript code
echo -e "${YELLOW}📝 Running ESLint on JavaScript/TypeScript code...${NC}"
npx eslint frontend/ --ext .ts,.tsx || true
echo -e "${GREEN}✓ ESLint check complete${NC}"

# Run TypeScript compiler
echo -e "${YELLOW}📝 Running TypeScript compiler...${NC}"
cd frontend && npx tsc --noEmit || true
cd ..
echo -e "${GREEN}✓ TypeScript compilation check complete${NC}"

echo ""
echo -e "${GREEN}✅ Linting complete!${NC}"
