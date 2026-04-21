#!/bin/bash

# Code Formatting Script
# This script formats Python and JavaScript/TypeScript code

set -e

echo "🎨 Formatting Code"
echo "=================="

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Format Python code with Black
echo -e "${YELLOW}🐍 Formatting Python code with Black...${NC}"
black src/ tests/ --line-length=100
echo -e "${GREEN}✓ Python code formatted${NC}"

# Format JavaScript/TypeScript code with Prettier
echo -e "${YELLOW}📝 Formatting JavaScript/TypeScript code with Prettier...${NC}"
npx prettier --write "frontend/**/*.{ts,tsx,json,md}" || true
echo -e "${GREEN}✓ JavaScript/TypeScript code formatted${NC}"

echo ""
echo -e "${GREEN}✅ Code formatting complete!${NC}"
