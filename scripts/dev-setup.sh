#!/bin/bash

# Development Environment Setup Script
# This script sets up the local development environment for the Trading Platform

set -e

echo "🚀 Trading Platform - Development Environment Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"

# Check if .env.development exists
if [ ! -f .env.development ]; then
    echo -e "${YELLOW}⚠ .env.development not found. Creating from template...${NC}"
    cp .env.example .env.development
    echo -e "${GREEN}✓ Created .env.development${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p sql
mkdir -p logs
mkdir -p scripts
echo -e "${GREEN}✓ Directories created${NC}"

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install Node dependencies
if [ -f "package.json" ]; then
    echo -e "${YELLOW}📦 Installing Node dependencies...${NC}"
    npm install
    echo -e "${GREEN}✓ Node dependencies installed${NC}"
fi

# Setup pre-commit hooks
echo -e "${YELLOW}🪝 Setting up pre-commit hooks...${NC}"
pip install pre-commit
pre-commit install
echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"

# Build Docker images
echo -e "${YELLOW}🐳 Building Docker images...${NC}"
docker-compose build
echo -e "${GREEN}✓ Docker images built${NC}"

echo ""
echo -e "${GREEN}✅ Development environment setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Start the development environment: ./scripts/dev-start.sh"
echo "2. Run tests: ./scripts/dev-test.sh"
echo "3. Format code: ./scripts/dev-format.sh"
echo "4. Lint code: ./scripts/dev-lint.sh"
echo ""
