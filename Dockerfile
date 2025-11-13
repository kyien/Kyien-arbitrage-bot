# Multi-stage Dockerfile for Arbitrage Bot
# Optimized for VPS deployment with 8GB RAM, 2 vCPUs

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set working directory
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
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib (for technical analysis if needed)
RUN cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/ta-lib*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies to a temporary location
RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set metadata
LABEL maintainer="arbitrage-bot"
LABEL description="Multi-chain DEX Arbitrage Bot with MEV Protection"
LABEL version="2.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Resource limits for 8GB RAM VPS (2 malloc arenas max)
    MALLOC_ARENA_MAX=2 \
    PYTHONMALLOC=malloc \
    # Logging
    LOG_DIR=/var/log/arbitrage-bot \
    LOG_LEVEL=INFO

# Install runtime dependencies and TA-Lib
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    libssl-dev \
    && cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/ta-lib* && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash arbitrage-bot && \
    mkdir -p /var/log/arbitrage-bot/trades && \
    mkdir -p /var/log/arbitrage-bot/errors && \
    mkdir -p /var/log/arbitrage-bot/alerts && \
    mkdir -p /app/config && \
    chown -R arbitrage-bot:arbitrage-bot /var/log/arbitrage-bot /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/arbitrage-bot/.local

# Copy application files
COPY --chown=arbitrage-bot:arbitrage-bot . .

# Make sure scripts are executable
RUN chmod +x scripts/*.py 2>/dev/null || true

# Update PATH to include local pip packages
ENV PATH=/home/arbitrage-bot/.local/bin:$PATH

# Switch to non-root user
USER arbitrage-bot

# Create volume mount points
VOLUME ["/var/log/arbitrage-bot", "/app/config"]

# Health check (checks if bot is responsive every 60 seconds)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Expose port for monitoring API (optional)
EXPOSE 8080

# Default command - run multi-chain bot
CMD ["python", "multi_chain_bot.py"]

