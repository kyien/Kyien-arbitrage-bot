# Quick Start Guide - VPS Deployment

## Prerequisites Checklist

- [ ] VPS with Ubuntu 20.04+ or Debian 11+
- [ ] Root or sudo access
- [ ] Binance API key and secret
- [ ] OKX API key and secret
- [ ] Wallet address and private key (for DEX trading)
- [ ] Private RPC endpoints (recommended: Alchemy, Infura, or QuickNode)

## Step-by-Step Deployment

### 1. Connect to Your VPS

```bash
ssh user@your-vps-ip
```

### 2. Clone Repository

```bash
cd ~
git clone <your-repo-url> crypto-arbitrage-bot
cd crypto-arbitrage-bot
```

### 3. Run Deployment Script

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
- Install all system dependencies
- Set up Python virtual environment
- Install Python packages
- Configure systemd service

### 4. Configure Environment Variables

```bash
cp env.example .env
nano .env
```

**Required Configuration:**
- Exchange API keys (Binance, OKX)
- Wallet address and private key
- RPC URLs (use private endpoints!)
- Trading parameters

**Important Security Notes:**
- Never commit `.env` file
- Keep private keys secure
- Use strong API key permissions

### 5. Test Configuration

```bash
source venv/bin/activate
python arbitrage_bot.py
```

Let it run for a few minutes and check for errors. Press `Ctrl+C` to stop.

### 6. Start as Service

```bash
sudo systemctl enable crypto-arbitrage-bot.service
sudo systemctl start crypto-arbitrage-bot.service
```

### 7. Monitor the Bot

```bash
# Check status
sudo systemctl status crypto-arbitrage-bot.service

# View logs
sudo journalctl -u crypto-arbitrage-bot.service -f

# View recent logs
sudo journalctl -u crypto-arbitrage-bot.service --since "1 hour ago"
```

## Essential Configuration Tips

### 1. Use Private RPC Endpoints (CRITICAL)

Replace public RPC URLs with private endpoints:

```env
# Example: Alchemy
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

**Why:** Public RPCs have rate limits and high latency. Private endpoints are 10-50x faster.

### 2. Start Conservative

Begin with small trade amounts:

```env
MIN_PROFIT_THRESHOLD=1.0
MAX_TRADE_AMOUNT=100
MAX_POSITION_SIZE=500
```

Gradually increase as you gain confidence.

### 3. Set Up Monitoring

Configure Telegram or Discord alerts:

```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Monitor Gas Prices

Adjust based on network conditions:

```env
MAX_GAS_PRICE_GWEI=100  # Adjust based on chain
```

## Common Commands

```bash
# Start bot
sudo systemctl start crypto-arbitrage-bot.service

# Stop bot
sudo systemctl stop crypto-arbitrage-bot.service

# Restart bot
sudo systemctl restart crypto-arbitrage-bot.service

# View logs
sudo journalctl -u crypto-arbitrage-bot.service -f

# Check status
sudo systemctl status crypto-arbitrage-bot.service

# Update bot
cd ~/crypto-arbitrage-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-arbitrage-bot.service
```

## Troubleshooting

### Bot Won't Start

1. Check logs: `sudo journalctl -u crypto-arbitrage-bot.service -n 50`
2. Verify `.env` file exists and is configured
3. Check Python dependencies: `pip list`
4. Verify API keys are correct
5. Test RPC endpoints

### Connection Issues

1. Test RPC endpoints manually
2. Check firewall: `sudo ufw status`
3. Verify network connectivity
4. Check WebSocket connections

### Low Profitability

1. Review [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md)
2. Use private RPC endpoints
3. Optimize gas prices
4. Adjust trading parameters
5. Monitor gas costs

## Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] Private keys are secure
- [ ] API keys have restricted permissions
- [ ] Firewall is configured
- [ ] SSH keys are used (not passwords)
- [ ] System is updated regularly

## Next Steps

1. **Monitor Performance**: Watch logs closely for first few days
2. **Optimize Parameters**: Adjust based on results
3. **Scale Gradually**: Increase position sizes slowly
4. **Review Regularly**: Check performance weekly
5. **Stay Updated**: Keep bot and dependencies updated

## Support Resources

- Full deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Efficiency tips: [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md)
- Configuration reference: `env.example`

## Important Reminders

- ⚠️ Start with small amounts
- ⚠️ Monitor closely initially
- ⚠️ Use private RPC endpoints
- ⚠️ Keep API keys secure
- ⚠️ Test thoroughly before scaling
- ⚠️ Review logs regularly

