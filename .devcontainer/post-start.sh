#!/bin/bash

echo "🔄 Starting Claude Observability Hub services..."

# Check if services are already running
if ! curl -s http://localhost:4000/health > /dev/null 2>&1; then
    echo "📡 Starting hub service..."
    cd /workspace && docker-compose up -d hub
else
    echo "✅ Hub already running"
fi

if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "🎨 Starting dashboard service..."
    cd /workspace && docker-compose up -d dashboard
else
    echo "✅ Dashboard already running"
fi

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
timeout 30 bash -c 'until curl -s http://localhost:4000/health > /dev/null 2>&1; do sleep 1; done'

echo ""
echo "✨ Claude Observability Hub is ready!"
echo ""
echo "  📊 Dashboard:  http://localhost:5173"
echo "  🔌 API:        http://localhost:4000"
echo "  📚 Docs:       http://localhost:4000/docs"
echo ""
echo "To test the system:"
echo "  ./scripts/test-event.sh"
echo ""