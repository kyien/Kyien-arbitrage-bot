# Deployment Guide for Crypto Arbitrage Bot

This guide will help you deploy the crypto arbitrage bot to your VPS hosting.

## Prerequisites

- VPS with Ubuntu 20.04+ or Debian 11+
- At least 2GB RAM, 2 CPU cores recommended
- Root or sudo access
- Domain name (optional, for monitoring)
- API keys for Binance and OKX exchanges
- Private key for your wallet (for DEX operations)

## Option 1: Manual Deployment (Recommended for Production)

### Step 1: Connect to Your VPS

```bash
ssh user@your-vps-ip
```

### Step 2: Clone the Repository

```bash
cd ~
git clone <your-repo-url> crypto-arbitrage-bot
cd crypto-arbitrage-bot
```

### Step 3: Run Deployment Script

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
- Install system dependencies
- Install TA-Lib library
- Create Python virtual environment
- Install Python packages
- Set up systemd service

### Step 4: Configure Environment Variables

```bash
nano .env
```

Fill in all required values:
- Exchange API keys (Binance, OKX)
- Wallet address and private key
- RPC URLs (recommend using private RPC endpoints)
- Trading parameters
- Alert configuration (Telegram/Discord)

**SECURITY WARNING:** Never commit your `.env` file or share your private keys!

### Step 5: Deploy Smart Contracts (Optional)

If you haven't deployed contracts yet:

```bash
source venv/bin/activate
python deploy_contracts.py
```

This will deploy contracts to all configured chains.

### Step 6: Test the Bot

```bash
source venv/bin/activate
python arbitrage_bot.py
```

Monitor for errors and ensure everything works correctly.

### Step 7: Enable and Start Service

```bash
sudo systemctl enable crypto-arbitrage-bot.service
sudo systemctl start crypto-arbitrage-bot.service
```

### Step 8: Monitor the Bot

```bash
# Check status
sudo systemctl status crypto-arbitrage-bot.service

# View logs
sudo journalctl -u crypto-arbitrage-bot.service -f

# View recent logs
sudo journalctl -u crypto-arbitrage-bot.service --since "1 hour ago"
```

## Option 2: Docker Deployment

### Step 1: Install Docker and Docker Compose

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

Log out and log back in for group changes to take effect.

### Step 2: Clone and Configure

```bash
cd ~
git clone <your-repo-url> crypto-arbitrage-bot
cd crypto-arbitrage-bot
cp .env.example .env
nano .env  # Configure your settings
```

### Step 3: Build and Run

```bash
docker-compose up -d --build
```

### Step 4: Monitor

```bash
# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop the bot
docker-compose down

# Restart the bot
docker-compose restart
```

## Post-Deployment Checklist

- [ ] Verify API keys are working
- [ ] Test WebSocket connections
- [ ] Verify RPC connections to all chains
- [ ] Check wallet has sufficient funds
- [ ] Set up monitoring alerts (Telegram/Discord)
- [ ] Review and adjust trading parameters
- [ ] Set up log rotation
- [ ] Configure firewall rules (if needed)
- [ ] Set up automated backups

## Monitoring and Maintenance

### View Logs

```bash
# Systemd
sudo journalctl -u crypto-arbitrage-bot.service -f

# Docker
docker-compose logs -f arbitrage-bot
```

### Restart Service

```bash
# Systemd
sudo systemctl restart crypto-arbitrage-bot.service

# Docker
docker-compose restart arbitrage-bot
```

### Update Bot

```bash
# Systemd
cd ~/crypto-arbitrage-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-arbitrage-bot.service

# Docker
cd ~/crypto-arbitrage-bot
git pull
docker-compose up -d --build
```

## Security Best Practices

1. **Never commit sensitive data**: Use `.env` file and add it to `.gitignore`
2. **Use private RPC endpoints**: Public RPCs have rate limits
3. **Restrict API key permissions**: Only enable trading permissions needed
4. **Use firewall**: Block unnecessary ports
5. **Keep system updated**: Regular security updates
6. **Monitor for unauthorized access**: Check logs regularly
7. **Use strong passwords**: For SSH and system access
8. **Consider VPN**: For additional security layer

## Troubleshooting

### Bot Won't Start

1. Check logs: `sudo journalctl -u crypto-arbitrage-bot.service -n 50`
2. Verify `.env` file exists and is configured
3. Check Python dependencies: `pip list`
4. Verify API keys are correct
5. Check RPC endpoints are accessible

### Connection Issues

1. Test RPC endpoints: `curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' <RPC_URL>`
2. Check firewall: `sudo ufw status`
3. Verify network connectivity
4. Check WebSocket connections

### High Memory Usage

1. Reduce `MAX_TRADE_AMOUNT` in `.env`
2. Reduce number of trading pairs
3. Increase VPS RAM
4. Add swap space: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`

### Low Profitability

1. Review recommendations in `EFFICIENCY_IMPROVEMENTS.md`
2. Adjust `MIN_PROFIT_THRESHOLD`
3. Use faster RPC endpoints
4. Monitor gas prices
5. Consider MEV protection

## Performance Optimization

1. **Use Private RPC Endpoints**: Significantly faster than public RPCs
   - Alchemy: https://www.alchemy.com/
   - Infura: https://www.infura.io/
   - QuickNode: https://www.quicknode.com/

2. **Optimize Trading Parameters**: Start conservative, then optimize based on results

3. **Monitor Gas Prices**: Adjust `MAX_GAS_PRICE_GWEI` based on network conditions

4. **Reduce Latency**: Deploy bot close to exchange servers or use cloud regions near exchanges

## Backup Strategy

1. **Configuration Backup**: Regularly backup `.env` file securely
2. **Contract Addresses**: Backup `deployed_contracts.json`
3. **Logs**: Archive logs periodically
4. **Code**: Use version control (Git)

## Support

For issues or questions:
- Check logs first
- Review configuration
- Test components individually
- Check exchange API status
- Verify blockchain network status

