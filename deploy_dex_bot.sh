#!/bin/bash
"""
Automated Deployment Script for DEX Arbitrage Bot
Safely deploys and configures the bot for DEX trading
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CHAIN=${1:-"polygon"}
BUDGET=${2:-"450"}
CONFIG_FILE=".env.deploy"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
    fi
    
    # Check Node.js for Hardhat/Truffle
    if ! command -v node &> /dev/null; then
        warn "Node.js not found - required for contract compilation"
    fi
    
    # Check for .env file
    if [[ ! -f ".env" ]]; then
        error ".env file not found. Copy from .env.example and configure"
    fi
    
    log "✅ Prerequisites check passed"
}

# Set up virtual environment
setup_environment() {
    log "Setting up Python environment..."
    
    # Check if running in Docker
    if [[ -f "/.dockerenv" ]]; then
        info "Running inside Docker container"
        log "✅ Docker environment detected"
        return 0
    fi
    
    # Local environment setup
    if [[ ! -d "venv" ]]; then
        python3 setup_environment.py
    fi
    
    source venv/bin/activate
    log "✅ Local environment activated"
}

# Validate configuration
validate_config() {
    log "Validating configuration..."
    
    # Check for critical environment variables
    required_vars=("WALLET_ADDRESS" "PRIVATE_KEY" "POLYGON_RPC_URL")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Required environment variable $var is not set in .env"
        fi
    done
    
    # Validate wallet address format
    if ! [[ $WALLET_ADDRESS =~ ^0x[a-fA-F0-9]{40}$ ]]; then
        error "Invalid WALLET_ADDRESS format. Should be 0x followed by 40 hex characters"
    fi
    
    log "✅ Configuration validation passed"
}

# Deploy smart contracts
deploy_contracts() {
    log "Deploying smart contracts to $CHAIN..."
    
    # Check if already deployed
    if [[ -f "deployed_contracts_v2.json" ]]; then
        warn "Deployment file exists. Skipping deployment."
        warn "Delete deployed_contracts_v2.json to redeploy"
        return 0
    fi
    
    # Deploy using Hardhat or Brownie
    if command -v npx &> /dev/null; then
        info "Using Hardhat for deployment..."
        npx hardhat run scripts/deploy_arbitrage_v2.js --network $CHAIN
    else
        info "Using deployment script..."
        python3 scripts/deploy_arbitrage_v2.py --chain $CHAIN
    fi
    
    if [[ ! -f "deployed_contracts_v2.json" ]]; then
        error "Contract deployment failed"
    fi
    
    log "✅ Contracts deployed successfully"
}

# Setup whitelists
setup_whitelists() {
    log "Setting up contract whitelists..."
    
    # Run whitelist setup
    python3 scripts/whitelist_setup.py --chain $CHAIN
    
    log "✅ Whitelists configured"
}

# Test the setup
test_setup() {
    log "Testing bot setup..."
    
    # Run basic connectivity test
    python3 scripts/verify_setup.py --chain $CHAIN
    
    # Test contract interface
    python3 -c "
from contract_interface_v2 import ContractInterfaceV2
import asyncio

async def test():
    try:
        interface = ContractInterfaceV2(chain='$CHAIN')
        stats = await interface.get_contract_stats()
        print(f'Contract stats: {stats}')
        print('✅ Contract test passed')
    except Exception as e:
        print(f'❌ Contract test failed: {e}')
        exit(1)

asyncio.run(test())
"
    
    log "✅ Setup test passed"
}

# Create monitoring service
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create systemd service if running on Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        info "Creating systemd service..."
        
        sudo tee /etc/systemd/system/dex-arbitrage-bot.service > /dev/null <<EOF
[Unit]
Description=DEX Arbitrage Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/arbitrage_bot.py --chain $CHAIN
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Service]
# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$(pwd)

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        log "✅ Systemd service created"
        log "Start with: sudo systemctl start dex-arbitrage-bot"
    else
        warn "Non-Linux system detected. Create manual monitoring script."
    fi
}

# Create emergency stop script
create_emergency_stop() {
    log "Creating emergency stop script..."
    
    cat > emergency_stop.sh <<'EOF'
#!/bin/bash
# Emergency stop script for arbitrage bot

echo "🚨 EMERGENCY STOP TRIGGERED"

# Stop systemd service
sudo systemctl stop dex-arbitrage-bot 2>/dev/null

# Kill any running Python processes
pkill -f "arbitrage_bot.py"

# Send alert
./send_alert.sh "EMERGENCY STOP ACTIVATED - All trading halted"

echo "✅ All bot processes stopped"
EOF
    
    chmod +x emergency_stop.sh
    log "✅ Emergency stop script created"
}

# Create alert script
create_alert_script() {
    log "Creating alert script..."
    
    cat > send_alert.sh <<'EOF'
#!/bin/bash
# Alert sending script

MESSAGE=$1

# Telegram alert (if configured)
if [[ ! -z "$TELEGRAM_BOT_TOKEN" ]]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=🚨 DEX Bot Alert: ${MESSAGE}" > /dev/null
fi

# Discord alert (if configured)
if [[ ! -z "$DISCORD_WEBHOOK_URL" ]]; then
    curl -H "Content-Type: application/json" \
        -d "{\"content\": \"🚨 DEX Bot Alert: ${MESSAGE}\"}" \
        $DISCORD_WEBHOOK_URL
fi

# Log locally
echo "[$(date)] ALERT: ${MESSAGE}" >> alerts.log
EOF
    
    chmod +x send_alert.sh
    log "✅ Alert script created"
}

# Create profit tracker
create_profit_tracker() {
    log "Setting up profit tracking..."
    
    cat > track_profits.py <<'EOF'
#!/usr/bin/env python3
"""
Profit tracking for DEX arbitrage bot
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

class ProfitTracker:
    def __init__(self):
        self.db_path = Path("trading_data.db")
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for trade tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                chain TEXT,
                dex_in TEXT,
                dex_out TEXT,
                token_in TEXT,
                token_out TEXT,
                amount REAL,
                profit_usd REAL,
                gas_cost_usd REAL,
                net_profit REAL,
                successful BOOLEAN,
                tx_hash TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_profit REAL,
                total_trades INTEGER,
                successful_trades INTEGER,
                gas_costs REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_trade(self, trade_data):
        """Record a completed trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (
                timestamp, chain, dex_in, dex_out, token_in, token_out,
                amount, profit_usd, gas_cost_usd, net_profit, successful, tx_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            trade_data['chain'],
            trade_data['dex_in'],
            trade_data['dex_out'],
            trade_data['token_in'],
            trade_data['token_out'],
            trade_data['amount'],
            trade_data['profit_usd'],
            trade_data['gas_cost_usd'],
            trade_data['net_profit'],
            trade_data['successful'],
            trade_data.get('tx_hash', '')
        ))
        
        conn.commit()
        conn.close()
    
    def get_daily_summary(self):
        """Get today's trading summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                SUM(profit_usd) as total_profit,
                COUNT(*) as total_trades,
                SUM(CASE WHEN successful THEN 1 ELSE 0 END) as successful_trades,
                SUM(gas_cost_usd) as total_gas
            FROM trades
            WHERE date(timestamp) = ?
        """, (today,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'date': today,
            'total_profit': result[0] or 0,
            'total_trades': result[1] or 0,
            'successful_trades': result[2] or 0,
            'total_gas_costs': result[3] or 0
        }

if __name__ == "__main__":
    tracker = ProfitTracker()
    print("✅ Profit tracker initialized")
EOF
    
    chmod +x track_profits.py
    log "✅ Profit tracker created"
}

# Main deployment function
main() {
    log "Starting DEX Bot Deployment for $CHAIN chain"
    log "Budget: \$$BUDGET"
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    validate_config
    
    # Deployment with safety checks
    read -p "Deploy smart contracts? (y/n): " deploy_contracts_choice
    if [[ $deploy_contracts_choice == "y" ]]; then
        deploy_contracts
        setup_whitelists
    fi
    
    # Test setup
    read -p "Run tests? (y/n): " run_tests_choice
    if [[ $run_tests_choice == "y" ]]; then
        test_setup
    fi
    
    # Monitoring setup
    read -p "Set up monitoring? (y/n): " monitoring_choice
    if [[ $monitoring_choice == "y" ]]; then
        setup_monitoring
        create_emergency_stop
        create_alert_script
        create_profit_tracker
    fi
    
    log "🎉 Deployment completed!"
    log ""
    log "📋 Quick Start Commands:"
    log "  Start trading: ./start_bot.sh"
    log "  Stop trading: ./emergency_stop.sh"
    log "  View profits: ./venv/bin/python track_profits.py"
    log "  Check status: systemctl status dex-arbitrage-bot"
    log ""
    log "⚠️  REMEMBER:"
    log "  - Start with small amounts (\$1-5 trades)"
    log "  - Monitor for 24 hours before scaling up"
    log "  - Set up alerts for daily P&L tracking"
    log "  - Never risk more than 12.5% of capital per trade"
}

# Run main function
main "$@"
