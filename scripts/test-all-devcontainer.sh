#!/bin/bash
# Run all tests from within the DevContainer
# This ensures reproducible test environments across all machines

set -e

echo "🐳 Running tests inside DevContainer..."
echo "====================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;94m'
NC='\033[0m' # No Color

# Check if we're inside a container
if [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
    echo -e "${YELLOW}⚠️  Not running inside a container!${NC}"
    echo "This script should be run inside the DevContainer."
    echo ""
    echo "To run tests in DevContainer:"
    echo "  devcontainer exec --workspace-folder . bash scripts/test-all-devcontainer.sh"
    echo ""
    echo "Or open in VS Code and run from integrated terminal."
    exit 1
fi

# Verify all tools are available
echo -e "${BLUE}Verifying environment...${NC}"
python --version
node --version
bun --version
echo ""

# Install dependencies if needed
echo -e "${BLUE}Installing dependencies...${NC}"

# Python dependencies
if [ ! -d "/workspace/.venv" ]; then
    python -m venv /workspace/.venv
fi
source /workspace/.venv/bin/activate
pip install -q -r requirements-dev.txt

# Bun dependencies
cd /workspace/core/server
if [ ! -d "node_modules" ]; then
    bun install
fi

# Vue dependencies  
cd /workspace/core/dashboard
if [ ! -d "node_modules" ]; then
    npm install
fi

cd /workspace

# Run tests
echo -e "\n${BLUE}Running test suite...${NC}"

# Python tests
echo -e "\n${YELLOW}Python tests:${NC}"
python -m pytest templates/hooks/.claude/hooks/tests/ \
    -v --tb=short \
    --junit-xml=test-results/python.xml \
    --cov --cov-report=xml --cov-report=html

# Bun tests
echo -e "\n${YELLOW}Bun/TypeScript tests:${NC}"
cd /workspace/core/server
bun test

# Vue tests
echo -e "\n${YELLOW}Vue tests:${NC}"
cd /workspace/core/dashboard
npm test

# Integration tests (if hub is running)
cd /workspace
if curl -f http://localhost:4000/health >/dev/null 2>&1; then
    echo -e "\n${YELLOW}Integration tests:${NC}"
    python -m pytest tests/integration/ -v \
        --junit-xml=test-results/integration.xml
else
    echo -e "\n${YELLOW}⚠️  Skipping integration tests (hub not running)${NC}"
fi

# Summary
echo -e "\n${BLUE}Generating test summary...${NC}"
cd /workspace
python scripts/test-summary.py

echo -e "\n${GREEN}✅ DevContainer tests complete!${NC}"