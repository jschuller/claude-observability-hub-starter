#!/bin/bash
set -e

echo "🚀 Setting up Claude Observability Hub development environment..."

# Create necessary directories
mkdir -p core/{server,dashboard,hooks-minimal}/src
mkdir -p scripts
mkdir -p templates/hooks/.claude/hooks

# Initialize git if not already
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit" || true
fi

# Create minimal package.json files if they don't exist
if [ ! -f core/server/package.json ]; then
    cat > core/server/package.json << 'EOF'
{
  "name": "observability-hub",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "bun run --watch src/index.ts",
    "build": "bun build src/index.ts --outdir dist",
    "test": "bun test"
  },
  "dependencies": {
    "sqlite3": "^5.1.6"
  }
}
EOF
fi

if [ ! -f core/dashboard/package.json ]; then
    cat > core/dashboard/package.json << 'EOF'
{
  "name": "observability-dashboard",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.3.0",
    "d3": "^7.8.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.0",
    "vite": "^5.0.0"
  }
}
EOF
fi

# Install dependencies
echo "📦 Installing server dependencies..."
cd /workspace/core/server && bun install

echo "📦 Installing dashboard dependencies..."
cd /workspace/core/dashboard && npm install

echo "✅ Development environment ready!"
echo ""
echo "Quick commands:"
echo "  Start all services:  docker-compose up"
echo "  Start hub only:      cd core/server && bun run dev"
echo "  Start dashboard:     cd core/dashboard && npm run dev"
echo ""