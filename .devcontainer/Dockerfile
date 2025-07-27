# Pin specific version for reproducibility
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Install Node.js first (required for npm)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash \
    && mv /root/.bun /usr/local/bun \
    && ln -s /usr/local/bun/bin/bun /usr/local/bin/bun

# Install additional tools
RUN apt-get update && apt-get install -y \
    sqlite3 \
    httpie \
    jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install global npm packages (after Node.js is available)
RUN npm install -g \
    @vue/cli@5.0.8 \
    vite@5.0.10 \
    typescript@5.3.3 \
    prettier@3.1.1 \
    eslint@8.55.0

# Create workspace directory
WORKDIR /workspace

# Install Python tools with pinned versions
RUN pip install --upgrade pip==23.3.2 \
    && pip install \
    aiohttp==3.9.1 \
    aiofiles==23.2.1 \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    black==23.7.0 \
    pylint==3.0.3 \
    ipython==8.14.0

# Set up non-root user (done by base image)
USER vscode

# Configure git
RUN git config --global core.editor "code --wait" \
    && git config --global init.defaultBranch main