 ┌───────────────────────────────────────────────────────────────────────┐
 │                      CRYPTO ARBITRAGE BOT SYSTEM                       │
 └───────────────────────────────────────────────────────────────────────┘
                                     │
         ┌────────────────────┬─────┴─────────┬────────────────────┐
         │                    │               │                    │
 ┌───────┴───────┐    ┌───────┴───────┐┌───────┴───────┐    ┌───────┴───────┐
 │  CEX MODULE   │    │  DEX MODULE   ││ CROSS-CHAIN   │    │  MONITORING   │
 │               │    │               ││   MODULE      │    │     MODULE    │
 └───────────────┘    └───────────────┘└───────────────┘    └───────────────┘
         │                    │               │                    │
         ▼                    ▼               ▼                    ▼
 ┌───────────────┐    ┌───────────────┐┌───────────────┐    ┌───────────────┐
 │Binance/OKX API│    │Smart Contracts││Bridge Services│    │Alert Systems  │
 │WebSockets     │    │Web3 Interface ││Multi-Chain    │    │Logging Systems│
 └───────────────┘    └───────────────┘└───────────────┘    └───────────────┘# Crypto Arbitrage Bot

This bot monitors and executes arbitrage opportunities between centralized exchanges (Binance and OKX) and decentralized exchanges on the Polygon network.

## Features

- Real-time price monitoring on Binance and OKX
- Automated arbitrage execution when profitable opportunities are found
- Configurable profit thresholds and trade sizes
- Logging system for monitoring trades and errors
- Support for multiple trading pairs

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your API keys and settings:
   ```bash
   cp .env.example .env
   ```

## Configuration

Edit the `.env` file with your:
- Exchange API keys for Binance and OKX
- Polygon RPC URL
- Trading parameters (profit threshold, maximum trade amount, etc.)

## Running the Bot

### Local Development

```bash
python arbitrage_bot.py
```

### Production Deployment

For production deployment on VPS, see [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick Start (Linux VPS):**
```bash
chmod +x deploy.sh
./deploy.sh
# Edit .env file with your configuration
sudo systemctl enable crypto-arbitrage-bot.service
sudo systemctl start crypto-arbitrage-bot.service
```

**Docker Deployment:**
```bash
docker-compose up -d --build
```

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide for VPS hosting
- **[EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md)** - Recommendations for increasing efficiency and profitability
- **[MEV_PROTECTION_GUIDE.md](MEV_PROTECTION_GUIDE.md)** - Comprehensive MEV protection and gas optimization guide
- **[MEV_RECOMMENDATIONS.md](MEV_RECOMMENDATIONS.md)** - Quick summary of MEV protection recommendations

## Key Features

- **CEX Arbitrage**: Binance ↔ OKX price differences
- **DEX Arbitrage**: Cross-DEX opportunities on Polygon (QuickSwap, SushiSwap, Uniswap V3)
- **Cross-Chain Arbitrage**: Multi-chain opportunities using bridge protocols
- **Advanced Strategies**: Market condition analysis, dynamic position sizing
- **Flash Swaps**: Capital-efficient DEX arbitrage execution
- **Monitoring**: Real-time alerts via Telegram/Discord
- **Risk Management**: Circuit breakers, slippage protection, gas optimization

## Critical Configuration Recommendations

1. **Use Private RPC Endpoints**: Essential for production (Alchemy, Infura, QuickNode)
2. **Optimize Gas Strategy**: Dynamic gas pricing for cost efficiency
3. **MEV Protection**: Implement anti-MEV measures
4. **Low Latency**: Deploy near exchange servers
5. **Monitor Closely**: Set up comprehensive monitoring and alerts

See [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md) for detailed recommendations.

## Safety Notes

- Start with small trade amounts while testing
- Monitor the bot's performance closely
- Ensure you have sufficient funds on both exchanges
- Keep your API keys secure and never share them
- Use private RPC endpoints for production
- Test thoroughly before deploying with real funds
- Regularly review and optimize configuration

## Disclaimer

Trading cryptocurrencies involves risk. This bot is provided as-is with no guarantees. Always test with small amounts first and monitor its performance carefully. Past performance does not guarantee future results.
