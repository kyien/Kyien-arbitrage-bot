# Crypto Arbitrage Bot

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

```bash
python arbitrage_bot.py
```

## Safety Notes

- Start with small trade amounts while testing
- Monitor the bot's performance closely
- Ensure you have sufficient funds on both exchanges
- Keep your API keys secure and never share them

## Disclaimer

Trading cryptocurrencies involves risk. This bot is provided as-is with no guarantees. Always test with small amounts first and monitor its performance carefully.
