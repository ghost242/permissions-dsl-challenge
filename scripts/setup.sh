#!/bin/bash
###############################################################################
# Quick Setup Script for Permission DSL Challenge
# This script automates the initial setup for new developers
###############################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up Permission DSL Challenge...${NC}\n"

###############################################################################
# 1. Check Prerequisites
###############################################################################

echo -e "${BLUE}📋 Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo "Please install Python 3.13+ from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Check Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed${NC}"
    echo "Please install Git from https://git-scm.com/"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git found"

###############################################################################
# 2. Install uv Package Manager
###############################################################################

echo -e "\n${BLUE}📦 Installing uv package manager...${NC}"

if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓${NC} uv is already installed"
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$PATH"

    if command -v uv &> /dev/null; then
        echo -e "${GREEN}✓${NC} uv installed successfully"
        echo -e "${YELLOW}⚠️  Please restart your terminal or run: source ~/.bashrc${NC}"
    else
        echo -e "${RED}❌ uv installation failed${NC}"
        exit 1
    fi
fi

###############################################################################
# 3. Install Dependencies
###############################################################################

echo -e "\n${BLUE}📚 Installing project dependencies...${NC}"

uv sync

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi

###############################################################################
# 4. Setup Database Directory
###############################################################################

echo -e "\n${BLUE}💾 Setting up database directory...${NC}"

mkdir -p data
echo -e "${GREEN}✓${NC} Database directory created"

###############################################################################
# 5. Create .env File
###############################################################################

echo -e "\n${BLUE}⚙️  Setting up environment configuration...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Created .env file from template"
    echo -e "${YELLOW}⚠️  Please edit .env with your configuration${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists, skipping${NC}"
fi

###############################################################################
# 6. Run Database Migrations
###############################################################################

echo -e "\n${BLUE}🗄️  Running database migrations...${NC}"

uv run python -c "
from src.database.connection import DatabaseConnection, DatabaseConfig

config = DatabaseConfig(db_type='sqlite', sqlite_path='data/permissions.db')
db = DatabaseConnection(config)
db.connect()

print('Running migration 001_initial_schema.sql...')
with open('migrations/001_initial_schema.sql', 'r') as f:
    db.get_connection().executescript(f.read())

print('Running migration 002_add_indexes.sql...')
with open('migrations/002_add_indexes.sql', 'r') as f:
    db.get_connection().executescript(f.read())

db.commit()
db.close()
print('✓ Migrations completed')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Database migrations completed"
else
    echo -e "${YELLOW}⚠️  Database migrations will run on first application start${NC}"
fi

###############################################################################
# 7. Run Tests to Verify Setup
###############################################################################

echo -e "\n${BLUE}🧪 Running tests to verify setup...${NC}"

uv run pytest tests/unit/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${YELLOW}⚠️  Some tests failed, but setup is complete${NC}"
fi

###############################################################################
# Success Message
###############################################################################

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}\n"
echo -e "${BLUE}To start the development server:${NC}"
echo -e "  ${GREEN}uv run python -m uvicorn src.main:app --reload --port 8000${NC}\n"
echo -e "${BLUE}API Documentation:${NC}"
echo -e "  ${GREEN}http://localhost:8000/docs${NC}\n"
echo -e "${BLUE}Health Check:${NC}"
echo -e "  ${GREEN}http://localhost:8000/api/v1/health${NC}\n"
echo -e "${BLUE}Run tests:${NC}"
echo -e "  ${GREEN}uv run pytest tests/ -v${NC}\n"
echo -e "${BLUE}Run with coverage:${NC}"
echo -e "  ${GREEN}uv run pytest --cov=src --cov-report=html tests/${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
echo -e "${YELLOW}📖 For more information, see:${NC}"
echo -e "  - README.md"
echo -e "  - docs/6_LOCAL_DEVELOPMENT_PLAN.yaml"
echo -e ""
