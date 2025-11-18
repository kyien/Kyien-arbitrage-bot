# Multi-stage Dockerfile for Arbitrage Bot
# Optimized for VPS deployment with 8GB RAM, 2 vCPUs

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    gcc \
    g++ \
    make \
    git \
    libssl-dev \
    libffi-dev \
    pkg-config \
    python3-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Solidity dependencies
COPY package.json .
RUN npm install && \
    # Verify installation
    ls -la node_modules/@openzeppelin && \
    ls -la node_modules/@uniswap

# Install TA-Lib C library
RUN cd /tmp && \
    wget --timeout=30 --tries=3 \
       https://github.com/TA-Lib/ta-lib/releases/download/v0.4.0/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/ta-lib*

# Set environment variables for Python wrapper compilation
ENV TA_LIBRARY_PATH=/usr/lib
ENV TA_INCLUDE_PATH=/usr/include
ENV NODE_PATH=/build/node_modules

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    nodejs \
    npm \
    && cd /tmp \
    && wget --timeout=30 --tries=3 \
       https://github.com/TA-Lib/ta-lib/releases/download/v0.4.0/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && ldconfig \
    && rm -rf /tmp/ta-lib* \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV TA_LIBRARY_PATH=/usr/lib
ENV TA_INCLUDE_PATH=/usr/include
ENV NODE_PATH=/app/node_modules
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MALLOC_ARENA_MAX=2 \
    PYTHONMALLOC=malloc \
    LOG_DIR=/var/log/arbitrage-bot \
    LOG_LEVEL=INFO

# Create non-root user and directories
RUN useradd -m -u 1000 -s /bin/bash arbitrage-bot && \
    mkdir -p /var/log/arbitrage-bot/trades && \
    mkdir -p /var/log/arbitrage-bot/errors && \
    mkdir -p /var/log/arbitrage-bot/alerts && \
    mkdir -p /app/config && \
    chown -R arbitrage-bot:arbitrage-bot /var/log/arbitrage-bot /app

WORKDIR /app

# CRITICAL: Copy node_modules FIRST (before COPY . .)
COPY --from=builder /build/node_modules /app/node_modules

# Copy Python dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files (this will NOT overwrite node_modules now)
COPY --chown=arbitrage-bot:arbitrage-bot . .

# Verify node_modules still exists
RUN ls -la /app/node_modules/@openzeppelin && \
    ls -la /app/node_modules/@uniswap

# Make sure scripts are executable
RUN chmod +x scripts/*.py 2>/dev/null || true

# Update PATH
ENV PATH=/home/arbitrage-bot/.local/bin:$PATH

# Switch to non-root user
USER arbitrage-bot

# Create volume mount points
VOLUME ["/var/log/arbitrage-bot", "/app/config"]

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Expose port for monitoring API (optional)
EXPOSE 8080

# Default command
CMD ["python", "multi_chain_bot.py"]