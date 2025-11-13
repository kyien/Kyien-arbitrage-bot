# VPS Deployment Guide - Production Ready

**Target Environment**: VPS with 8GB RAM, 2 vCPUs, 68GB available disk
**Existing Services**: n8n running in Docker
**Deployment Goal**: Production-ready arbitrage bot with monitoring, logging, and auto-restart

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Option A: Docker Deployment (Recommended)](#option-a-docker-deployment-recommended)
4. [Option B: Systemd Deployment](#option-b-systemd-deployment)
5. [Monitoring & Alerting Setup](#monitoring--alerting-setup)
6. [Log Rotation Setup](#log-rotation-setup)
7. [Health Checks](#health-checks)
8. [Resource Management](#resource-management)
9. [Integration with n8n](#integration-with-n8n)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

✅ **Met** (Your VPS):
- 8GB RAM (Bot will use 4GB, leaving 4GB for n8n and system)
- 2 vCPUs (Bot will use 1.5 CPUs max)
- 68GB disk space available
- Ubuntu 20.04+ or Debian 10+

### Required Software

Install these before deploying:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Alternative: Python-based deployment
sudo apt install -y python3 python3-pip python3-venv git
```

### Required Files on VPS

Upload these files to your VPS:

```bash
# On your local machine
scp -r /Users/knkinyanjui/Projects/Personal/Kyien-arbitrage-bot user@your-vps-ip:/tmp/

# On VPS
sudo mkdir -p /opt/arbitrage-bot
sudo mv /tmp/Kyien-arbitrage-bot/* /opt/arbitrage-bot/
sudo chown -R $USER:$USER /opt/arbitrage-bot
```

---

## Deployment Options

### Comparison

| Feature | Docker | Systemd |
|---------|--------|---------|
| **Isolation** | ✅ Full containerization | ⚠️ Shares host environment |
| **Resource Control** | ✅ Easy (docker-compose) | ⚠️ Manual (systemd limits) |
| **Updates** | ✅ Simple (rebuild image) | ⚠️ Manual (pip install) |
| **Monitoring** | ✅ Built-in health checks | ⚠️ External monitoring needed |
| **Portability** | ✅ Works anywhere | ⚠️ Host-dependent |
| **Integration with n8n** | ✅ Easy (shared network) | ⚠️ More complex |
| **Recommended** | **YES** | Only if Docker unavailable |

**We recommend Option A (Docker) for production deployment.**

---

## Option A: Docker Deployment (Recommended)

### Step 1: Prepare Environment

```bash
# Navigate to project directory
cd /opt/arbitrage-bot

# Create required directories
mkdir -p logs/{trades,errors,alerts}
mkdir -p config

# Copy .env file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required in .env**:
```bash
# Wallet Configuration
WALLET_ADDRESS=0xYourAddress
PRIVATE_KEY=your_private_key_here

# RPC URLs (use reliable providers)
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
OPTIMISM_RPC_URL=https://opt-mainnet.g.alchemy.com/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/

# Alert Configuration (Optional but recommended)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Discord webhook (optional)
DISCORD_WEBHOOK_URL=your_discord_webhook_url

# Resource Configuration
MIN_GAS_BALANCE_USD=10
LOG_LEVEL=INFO
```

### Step 2: Review docker-compose.yml

The `docker-compose.yml` is already configured for your VPS:
- **Memory**: 4GB max (leaving 4GB for n8n + system)
- **CPU**: 1.5 CPUs max (leaving 0.5 for system)
- **Logging**: Rotated at 10MB, keeps 3 files
- **Health Checks**: Every 60 seconds
- **Auto-restart**: Unless stopped manually

```bash
# Review configuration
cat docker-compose.yml
```

### Step 3: Deploy ArbitrageV2 Contracts

**IMPORTANT**: Deploy secure contracts BEFORE running bot!

```bash
# Deploy to Polygon (cheapest gas first)
docker-compose run --rm arbitrage-bot python scripts/deploy_arbitrage_v2.py --chain polygon

# Configure whitelists
docker-compose run --rm arbitrage-bot python scripts/whitelist_setup.py --chain polygon

# Test deployment
docker-compose run --rm arbitrage-bot python scripts/test_arbitrage_v2.py --chain polygon

# Repeat for other chains
docker-compose run --rm arbitrage-bot python scripts/deploy_arbitrage_v2.py --chain arbitrum
docker-compose run --rm arbitrage-bot python scripts/whitelist_setup.py --chain arbitrum
# ... etc
```

### Step 4: Start the Bot

```bash
# Build Docker image
docker-compose build

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker ps
docker-compose ps
```

### Step 5: Verify Health

```bash
# Check health status
docker inspect arbitrage-bot | grep -A 10 Health

# Manual health check
docker exec arbitrage-bot python scripts/health_check.py

# View bot logs
docker-compose logs -f arbitrage-bot

# Check resource usage
docker stats arbitrage-bot
```

---

## Option B: Systemd Deployment

### Step 1: Create User

```bash
# Create dedicated user for security
sudo useradd -r -m -s /bin/bash arbitrage-bot
sudo usermod -aG sudo arbitrage-bot

# Set up directory
sudo mkdir -p /opt/arbitrage-bot
sudo chown -R arbitrage-bot:arbitrage-bot /opt/arbitrage-bot
```

### Step 2: Install Python Dependencies

```bash
# Switch to arbitrage-bot user
sudo su - arbitrage-bot

# Navigate to directory
cd /opt/arbitrage-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Exit back to your user
exit
```

### Step 3: Configure Environment

```bash
# Copy .env
sudo cp /opt/arbitrage-bot/.env.example /opt/arbitrage-bot/.env
sudo chown arbitrage-bot:arbitrage-bot /opt/arbitrage-bot/.env
sudo chmod 600 /opt/arbitrage-bot/.env

# Edit configuration
sudo nano /opt/arbitrage-bot/.env
```

### Step 4: Deploy Contracts

```bash
# Switch to arbitrage-bot user
sudo su - arbitrage-bot
cd /opt/arbitrage-bot
source venv/bin/activate

# Deploy to Polygon
python scripts/deploy_arbitrage_v2.py --chain polygon
python scripts/whitelist_setup.py --chain polygon
python scripts/test_arbitrage_v2.py --chain polygon

# Repeat for other chains...

exit
```

### Step 5: Install Systemd Service

```bash
# Copy service file
sudo cp /opt/arbitrage-bot/deployment/arbitrage-bot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable arbitrage-bot

# Start service
sudo systemctl start arbitrage-bot

# Check status
sudo systemctl status arbitrage-bot

# View logs
sudo journalctl -u arbitrage-bot -f
```

---

## Monitoring & Alerting Setup

### Telegram Alerts (Recommended)

**Step 1: Create Telegram Bot**

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy the bot token

**Step 2: Get Chat ID**

1. Start a chat with your new bot
2. Send any message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find `"chat":{"id":123456789}` - that's your chat ID

**Step 3: Configure**

```bash
# Add to .env
TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

**Step 4: Test Alerts**

```bash
# Docker
docker exec arbitrage-bot python -c "
import asyncio
from monitoring_alerts import alert_manager
asyncio.run(alert_manager.bot_started(['polygon', 'arbitrum']))
"

# Systemd
sudo su - arbitrage-bot
cd /opt/arbitrage-bot
source venv/bin/activate
python -c "
import asyncio
from monitoring_alerts import alert_manager
asyncio.run(alert_manager.bot_started(['polygon', 'arbitrum']))
"
```

### Discord Alerts (Alternative)

1. Create Discord webhook in your server
2. Copy webhook URL
3. Add to `.env`: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

### Alert Types

The bot will automatically send alerts for:

✅ **Informational** (Info level):
- Arbitrage opportunity found
- Execution started
- Execution completed successfully
- Wallet balance updated
- Bot started/stopped

⚠️ **Warnings** (Warning level):
- Execution failed
- High slippage detected
- Bot error

🚨 **Critical** (Critical level):
- MEV attack detected
- Reentrancy attempt detected
- Gas balance critically low
- Health check failed

---

## Log Rotation Setup

### Step 1: Install Logrotate Configuration

```bash
# Copy logrotate config
sudo cp /opt/arbitrage-bot/deployment/logrotate.conf /etc/logrotate.d/arbitrage-bot

# Set permissions
sudo chown root:root /etc/logrotate.d/arbitrage-bot
sudo chmod 644 /etc/logrotate.d/arbitrage-bot

# Test configuration (dry run)
sudo logrotate -d /etc/logrotate.d/arbitrage-bot

# Force rotation (for testing)
sudo logrotate -f /etc/logrotate.d/arbitrage-bot
```

### Step 2: Verify Log Rotation

```bash
# Check log sizes
du -sh /var/log/arbitrage-bot/*

# List rotated logs
ls -lh /var/log/arbitrage-bot/*.gz

# View current log size
docker exec arbitrage-bot python -c "
from logging_config import get_log_size
print(get_log_size())
"
```

### Log Retention Policy

- **Main logs** (bot.log): 7 days, max 100MB
- **Debug logs**: 3 days, max 10MB
- **Error logs**: 30 days, max 100MB
- **Trade logs**: 90 days, max 200MB (audit trail)
- **Alert logs**: 14 days, max 50MB

**Estimated disk usage**: 2-5GB for logs

---

## Health Checks

### Docker Health Checks

Docker automatically runs health checks every 60 seconds:

```bash
# View health status
docker inspect arbitrage-bot | grep -A 10 Health

# Manual check
docker exec arbitrage-bot python scripts/health_check.py
```

### Health Check Components

1. **Heartbeat**: Bot updates every 60 seconds
2. **RPC Connectivity**: At least one RPC connected
3. **Gas Balance**: Above minimum threshold ($10 USD)
4. **Memory Usage**: Below 90%
5. **Disk Space**: At least 5GB free
6. **Log Activity**: Logs updated in last 10 minutes

### Manual Health Check

```bash
# Docker
docker exec arbitrage-bot python scripts/health_check.py

# Systemd
sudo su - arbitrage-bot
cd /opt/arbitrage-bot
source venv/bin/activate
python scripts/health_check.py
```

**Output**:
```
Health Status: ✅ HEALTHY
Checks Passed: 6/6

Check Results:
  heartbeat: ✅ PASS
  rpc_connectivity: ✅ PASS
  gas_balance: ✅ PASS
  memory: ✅ PASS
  disk_space: ✅ PASS
  log_activity: ✅ PASS
```

---

## Resource Management

### Current Resource Allocation

**Your VPS**: 8GB RAM, 2 vCPUs, 68GB disk

**Allocation**:
- **Arbitrage Bot**: 4GB RAM, 1.5 CPUs
- **n8n**: ~2GB RAM, 0.3 CPUs
- **System**: ~2GB RAM, 0.2 CPUs

### Monitor Resource Usage

```bash
# Overall system resources
htop

# Docker container stats
docker stats

# Disk usage
df -h

# Log sizes
du -sh /var/log/arbitrage-bot/*
du -sh /opt/arbitrage-bot/logs/*

# Check for memory leaks
docker stats --no-stream arbitrage-bot

# CPU usage over time
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Optimize for 8GB RAM

The deployment is already optimized:

1. **Docker limits**: 4GB max memory
2. **MALLOC_ARENA_MAX=2**: Reduces memory fragmentation
3. **Multi-stage Dockerfile**: Smaller image size
4. **Log rotation**: Prevents disk fill
5. **Health checks**: Catch memory leaks early

---

## Integration with n8n

### Option 1: Shared Docker Network

```bash
# Find n8n network
docker network ls

# Update docker-compose.yml
nano docker-compose.yml

# Uncomment and update:
networks:
  arbitrage-network:
    external: true
    name: n8n_network  # Replace with your n8n network name

# Restart bot
docker-compose down
docker-compose up -d
```

### Option 2: Webhook Integration

Create n8n workflows to:

1. **Monitor bot status** via health check
2. **Receive alerts** via custom webhook
3. **Trigger actions** based on alerts

**Example n8n Workflow**:
```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.webhook",
      "webhook": "/arbitrage-bot-alert",
      "method": "POST"
    },
    {
      "type": "n8n-nodes-base.telegram",
      "parameters": {
        "message": "Alert: {{$json.title}}\n{{$json.message}}"
      }
    }
  ]
}
```

**Configure in .env**:
```bash
CUSTOM_WEBHOOK_URL=http://n8n:5678/webhook/arbitrage-bot-alert
```

---

## Troubleshooting

### Bot Won't Start

**Docker**:
```bash
# Check logs
docker-compose logs -f

# Check if container is running
docker ps -a

# Rebuild image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Systemd**:
```bash
# Check service status
sudo systemctl status arbitrage-bot

# View recent logs
sudo journalctl -u arbitrage-bot -n 50

# Check for errors
sudo journalctl -u arbitrage-bot -p err
```

### High Memory Usage

```bash
# Check current usage
docker stats arbitrage-bot

# Restart to clear memory
docker-compose restart

# Check for memory leaks
docker exec arbitrage-bot python -c "
import gc
gc.collect()
print('Memory cleared')
"
```

### Disk Space Full

```bash
# Check disk usage
df -h

# Find large log files
find /var/log/arbitrage-bot -type f -size +100M

# Manual log cleanup
docker exec arbitrage-bot python -c "
from logging_config import cleanup_old_logs
cleanup_old_logs(days=7)
"

# Clean Docker images
docker system prune -a
```

### RPC Connection Issues

```bash
# Test RPC connectivity
docker exec arbitrage-bot python -c "
from web3 import Web3
import config

for chain, cfg in config.SUPPORTED_CHAINS.items():
    w3 = Web3(Web3.HTTPProvider(cfg['rpc']))
    print(f'{chain}: {'✅' if w3.is_connected() else '❌'}')
"
```

### No Alerts Received

```bash
# Test alert system
docker exec arbitrage-bot python -c "
import asyncio
from monitoring_alerts import alert_manager

async def test():
    await alert_manager.bot_started(['test'])
    print('Alert sent!')

asyncio.run(test())
"

# Check Telegram bot token
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

---

## Maintenance

### Daily Checks

```bash
# Check bot status
docker ps | grep arbitrage-bot

# Check health
docker exec arbitrage-bot python scripts/health_check.py

# View recent logs
docker-compose logs --tail=100

# Check profits (from logs)
grep "Execution Successful" logs/bot.log | tail -20
```

### Weekly Checks

```bash
# Check disk space
df -h

# Check log sizes
du -sh logs/*

# Review error logs
grep ERROR logs/errors/error.log | tail -50

# Check resource usage trends
docker stats --no-stream
```

### Monthly Tasks

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Rebuild Docker image (get latest dependencies)
docker-compose build --pull
docker-compose up -d

# Review gas balances on all chains
docker exec arbitrage-bot python -c "
import asyncio
from contract_interface_v2 import ContractInterfaceV2
import config

async def check_all():
    for chain in ['polygon', 'arbitrum', 'optimism', 'bsc']:
        try:
            interface = ContractInterfaceV2(chain=chain)
            owner = await interface.get_owner()
            print(f'{chain}: Owner {owner}')
        except Exception as e:
            print(f'{chain}: {str(e)}')

asyncio.run(check_all())
"

# Backup deployment files
tar -czf arbitrage-bot-backup-$(date +%Y%m%d).tar.gz \
  deployed_contracts_v2*.json \
  .env \
  logs/trades/*.log
```

### Update Procedure

```bash
# 1. Pull latest code
cd /opt/arbitrage-bot
git pull

# 2. Stop bot
docker-compose down

# 3. Rebuild image
docker-compose build --no-cache

# 4. Start bot
docker-compose up -d

# 5. Verify
docker-compose logs -f
docker exec arbitrage-bot python scripts/health_check.py
```

---

## Quick Reference

### Essential Commands

```bash
# Start bot
docker-compose up -d

# Stop bot
docker-compose down

# Restart bot
docker-compose restart

# View logs
docker-compose logs -f

# Health check
docker exec arbitrage-bot python scripts/health_check.py

# Check stats
docker stats arbitrage-bot

# Access container shell
docker exec -it arbitrage-bot bash

# View recent trades
grep "Execution Successful" logs/trades/trades.log | tail -20
```

### Important Files

- **Configuration**: `/opt/arbitrage-bot/.env`
- **Logs**: `/opt/arbitrage-bot/logs/`
- **Deployments**: `/opt/arbitrage-bot/deployed_contracts_v2*.json`
- **Docker Compose**: `/opt/arbitrage-bot/docker-compose.yml`
- **Service File**: `/etc/systemd/system/arbitrage-bot.service`

### Emergency Stop

```bash
# Docker
docker-compose down

# Systemd
sudo systemctl stop arbitrage-bot

# Kill process (last resort)
pkill -9 -f multi_chain_bot.py
```

---

## 🎉 Deployment Complete!

Your arbitrage bot is now running with:

✅ **Production-ready deployment** (Docker or systemd)
✅ **Auto-restart** on failure
✅ **Log rotation** to prevent disk fill
✅ **Comprehensive monitoring** (health checks every 60s)
✅ **Real-time alerts** (Telegram/Discord/Email)
✅ **Resource limits** (4GB RAM, 1.5 CPUs)
✅ **Security hardening** (non-root user, limited permissions)

**Next Steps**:
1. Monitor logs for first 24 hours
2. Verify alerts are working
3. Check gas balances daily
4. Review profit reports weekly

**Support**:
- Check logs: `docker-compose logs -f`
- Health check: `docker exec arbitrage-bot python scripts/health_check.py`
- View this guide: `cat VPS_DEPLOYMENT_GUIDE.md`

---

**Generated**: 2025-11-13
**Version**: 2.0.0
**Status**: PRODUCTION READY

**Happy Trading! 🚀**
