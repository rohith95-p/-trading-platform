#!/bin/bash

# Development Environment Stop Script
# This script stops all services

set -e

echo "🛑 Stopping Trading Platform Development Environment"
echo "===================================================="

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🐳 Stopping Docker Compose services...${NC}"
docker-compose down

echo -e "${GREEN}✅ Development environment stopped${NC}"
