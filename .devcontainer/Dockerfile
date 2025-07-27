FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

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

# Install global npm packages
RUN npm install -g \
    @vue/cli \
    vite \
    typescript \
    prettier \
    eslint

# Create workspace directory
WORKDIR /workspace

# Install Python tools
RUN pip install --upgrade pip \
    && pip install \
    aiohttp \
    aiofiles \
    pytest \
    pytest-asyncio \
    black \
    pylint \
    ipython

# Set up non-root user (done by base image)
USER vscode

# Configure git
RUN git config --global core.editor "code --wait" \
    && git config --global init.defaultBranch main