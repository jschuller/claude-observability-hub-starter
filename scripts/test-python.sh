#!/bin/bash
# Run Python tests with coverage

echo "🧪 Running Python tests..."

# Change to project root
cd "$(dirname "$0")/.." || exit 1

# Install test dependencies if needed
if ! python -m pytest --version >/dev/null 2>&1; then
    echo "📦 Installing test dependencies..."
    pip install -r requirements-dev.txt
fi

# Run tests with coverage
python -m pytest \
    templates/hooks/.claude/hooks/tests/ \
    -v \
    --cov=templates/hooks/.claude/hooks \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=80

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ All Python tests passed!"
    echo "📊 Coverage report saved to htmlcov/index.html"
else
    echo "❌ Some tests failed!"
    exit 1
fi