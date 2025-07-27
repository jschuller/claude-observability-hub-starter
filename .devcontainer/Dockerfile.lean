# Optimized lean DevContainer for Claude Observability Hub
# Multi-stage build to minimize final image size

# Stage 1: Python builder
FROM python:3.11-slim as python-builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements-dev.txt /tmp/
RUN pip install --user --no-cache-dir -r /tmp/requirements-dev.txt

# Stage 2: Node.js builder
FROM node:20.10.0-alpine as node-builder

# Install global npm packages
RUN npm install -g --no-cache \
    @vue/cli@5.0.8 \
    vite@5.0.10 \
    typescript@5.3.3 \
    prettier@3.1.1 \
    eslint@8.55.0

# Stage 3: Bun builder
FROM alpine:3.19 as bun-builder

RUN apk add --no-cache curl bash
RUN curl -fsSL https://bun.sh/install | bash

# Stage 4: Final image
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    sqlite3 \
    jq \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js runtime
COPY --from=node:20.10.0-alpine /usr/local/bin/node /usr/local/bin/
COPY --from=node:20.10.0-alpine /usr/local/lib/node_modules /usr/local/lib/node_modules

# Link npm and global packages
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Copy Python packages
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy Bun
COPY --from=bun-builder /root/.bun /usr/local/bun
RUN ln -s /usr/local/bun/bin/bun /usr/local/bin/bun

# Create non-root user
RUN useradd -m -s /bin/bash vscode && \
    mkdir -p /workspace && \
    chown -R vscode:vscode /workspace

# Switch to non-root user
USER vscode
WORKDIR /workspace

# Copy Python packages for vscode user
COPY --from=python-builder --chown=vscode:vscode /root/.local /home/vscode/.local
ENV PATH=/home/vscode/.local/bin:$PATH

# Configure git
RUN git config --global core.editor "code --wait" && \
    git config --global init.defaultBranch main

# Labels
LABEL maintainer="Claude Observability Hub"
LABEL description="Lean DevContainer for multi-stack observability development"