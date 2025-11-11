#!/bin/bash

# Crypto Arbitrage Bot Deployment Script
# Run this script on your VPS to set up the bot

set -e

echo "=========================================="
echo "Crypto Arbitrage Bot Deployment Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Please do not run as root. Run as a regular user.${NC}"
    exit 1
fi

# Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install required system packages
echo -e "${YELLOW}Installing system dependencies...${NC}"
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    pkg-config \
    wget \
    curl \
    systemd

# Install TA-Lib dependencies
echo -e "${YELLOW}Installing TA-Lib dependencies...${NC}"
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Get project directory
PROJECT_DIR=$(pwd)
echo -e "${GREEN}Project directory: $PROJECT_DIR${NC}"

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Please edit .env file with your API keys and configuration!${NC}"
    echo -e "${RED}Run: nano .env${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Create logs directory
mkdir -p logs

# Create systemd service file
echo -e "${YELLOW}Setting up systemd service...${NC}"
sudo tee /etc/systemd/system/crypto-arbitrage-bot.service > /dev/null <<EOF
[Unit]
Description=Crypto Arbitrage Bot Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/bin:/usr/local/bin"
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/arbitrage_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

echo -e "${GREEN}=========================================="
echo "Deployment completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys: nano .env"
echo "2. Test the bot: python3 arbitrage_bot.py"
echo "3. Enable and start the service:"
echo "   sudo systemctl enable crypto-arbitrage-bot.service"
echo "   sudo systemctl start crypto-arbitrage-bot.service"
echo "4. Check status: sudo systemctl status crypto-arbitrage-bot.service"
echo "5. View logs: sudo journalctl -u crypto-arbitrage-bot.service -f"

