#!/bin/bash
# Run all tests across the stack

set -e

echo "🧪 Running Claude Observability Hub Test Suite"
echo "============================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

# Function to run tests and report status
run_test() {
    local name=$1
    local command=$2
    
    echo -e "\n${YELLOW}Running $name tests...${NC}"
    
    if eval "$command"; then
        echo -e "${GREEN}✅ $name tests passed${NC}"
    else
        echo -e "${RED}❌ $name tests failed${NC}"
        OVERALL_STATUS=1
    fi
}

# Change to project root
cd "$(dirname "$0")/.." || exit 1

# Python tests
run_test "Python" "./scripts/test-python.sh"

# Bun/TypeScript tests
run_test "Bun/TypeScript" "cd core/server && bun test"

# Vue tests
run_test "Vue" "cd core/dashboard && npm test"

# Integration tests (optional - requires Docker)
if command -v docker-compose &> /dev/null; then
    echo -e "\n${YELLOW}Running integration tests...${NC}"
    
    # Start test environment
    docker-compose -f docker-compose.test.yml up -d test-hub
    
    # Wait for services
    echo "Waiting for services to be ready..."
    sleep 5
    
    # Run integration tests
    if pip install -q pytest requests websocket-client && \
       pytest tests/integration/ -v; then
        echo -e "${GREEN}✅ Integration tests passed${NC}"
    else
        echo -e "${RED}❌ Integration tests failed${NC}"
        OVERALL_STATUS=1
    fi
    
    # Cleanup
    docker-compose -f docker-compose.test.yml down -v
else
    echo -e "${YELLOW}⚠️  Skipping integration tests (Docker not found)${NC}"
fi

# Summary
echo -e "\n============================================="
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed!${NC}"
fi

exit $OVERALL_STATUS