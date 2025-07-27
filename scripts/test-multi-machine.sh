#!/bin/bash
# Multi-machine simulation test
# Tests observability across multiple machines/projects

set -e

echo "🌐 Starting Multi-Machine Simulation Test"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;94m'
NC='\033[0m' # No Color

# Change to tests directory
cd "$(dirname "$0")/../tests/multi-machine" || exit 1

# Function to cleanup
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker-compose -f docker-compose.multi.yml down -v
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Start the multi-machine environment
echo -e "${BLUE}Starting multi-machine environment...${NC}"
docker-compose -f docker-compose.multi.yml up -d --build

# Wait for hub to be healthy
echo -e "${BLUE}Waiting for hub to be ready...${NC}"
timeout 30s bash -c 'until curl -f http://localhost:4000/health >/dev/null 2>&1; do sleep 1; done'

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Hub is healthy${NC}"
else
    echo -e "${RED}❌ Hub failed to start${NC}"
    exit 1
fi

# Let simulations run for a bit
echo -e "${BLUE}Running simulations for 60 seconds...${NC}"
sleep 60

# Check events are being received
echo -e "\n${BLUE}Checking event statistics...${NC}"

# Query events from each machine
for machine in "machine-web-dev" "machine-data-science" "machine-api-dev" "machine-offline"; do
    COUNT=$(curl -s "http://localhost:4000/events?limit=1000" | \
        jq -r ".[] | select(.machine_id == \"$machine\") | .event_uuid" | \
        wc -l | tr -d ' ')
    
    if [ "$COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ $machine: $COUNT events${NC}"
    else
        echo -e "${RED}❌ $machine: No events received${NC}"
    fi
done

# Check for subagent events
SUBAGENT_COUNT=$(curl -s "http://localhost:4000/events?limit=1000" | \
    jq -r '.[] | select(.agent_type == "subagent") | .event_uuid' | \
    wc -l | tr -d ' ')

echo -e "\n${BLUE}Subagent events: ${SUBAGENT_COUNT}${NC}"

# Check dashboard is accessible
if curl -f http://localhost:5173 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard is accessible${NC}"
else
    echo -e "${RED}❌ Dashboard is not accessible${NC}"
fi

# Show recent events
echo -e "\n${BLUE}Recent events:${NC}"
curl -s "http://localhost:4000/events?limit=10" | \
    jq -r '.[] | "\(.timestamp) [\(.machine_id)] \(.agent_name // .agent_id): \(.hook_event_type)"'

# Summary
echo -e "\n${BLUE}=== Multi-Machine Test Summary ===${NC}"
TOTAL_EVENTS=$(curl -s "http://localhost:4000/events?limit=1000" | jq '. | length')
UNIQUE_MACHINES=$(curl -s "http://localhost:4000/events?limit=1000" | jq -r '.[].machine_id' | sort -u | wc -l)
UNIQUE_SESSIONS=$(curl -s "http://localhost:4000/events?limit=1000" | jq -r '.[].session_id' | sort -u | wc -l)

echo -e "Total events: ${TOTAL_EVENTS}"
echo -e "Unique machines: ${UNIQUE_MACHINES}"
echo -e "Unique sessions: ${UNIQUE_SESSIONS}"

if [ "$TOTAL_EVENTS" -gt 20 ] && [ "$UNIQUE_MACHINES" -ge 3 ]; then
    echo -e "\n${GREEN}✅ Multi-machine simulation test PASSED!${NC}"
    echo -e "Dashboard available at: http://localhost:5173"
    echo -e "Press Ctrl+C to stop the simulation..."
    
    # Keep running until interrupted
    docker-compose -f docker-compose.multi.yml logs -f
else
    echo -e "\n${RED}❌ Multi-machine simulation test FAILED!${NC}"
    echo -e "Not enough events or machines detected."
    exit 1
fi