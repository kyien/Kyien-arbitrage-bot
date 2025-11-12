# Advanced Features Guide - Arbitrage Bot v2.1

## Overview

This guide covers the new advanced features:
1. **Separate CEX/DEX trade limits**
2. **Multi-chain DEX support**
3. **Volatility-triggered trading**
4. **Mempool monitoring for backrunning**

---

## 1. CEX vs DEX Trade Limits

### Configuration

You can now set different limits for CEX and DEX trades:

```bash
# .env configuration
MAX_TRADE_AMOUNT_CEX=1000    # CEX arbitrage limit
MAX_TRADE_AMOUNT_DEX=500     # DEX arbitrage limit (usually lower due to gas)
MAX_TRADE_AMOUNT=1000        # Fallback if above not specified
```

### Why Separate Limits?

**CEX Trading**:
- No gas costs
- Instant execution
- Can handle larger amounts
- **Recommended**: $500-$5000

**DEX Trading**:
- Gas costs per trade (~$0.005-$5 depending on chain)
- Requires gas cost verification
- Limited by liquidity
- **Recommended**: $100-$1000

### Usage in Code

```python
import config

# For CEX arbitrage
max_cex_amount = config.MAX_TRADE_AMOUNT_CEX

# For DEX arbitrage
max_dex_amount = config.MAX_TRADE_AMOUNT_DEX

# Backward compatible
fallback = config.MAX_TRADE_AMOUNT
```

---

## 2. Multi-Chain DEX Support

### Supported Chains

The bot now supports:
- **Polygon** (QuickSwap, SushiSwap, Uniswap V3)
- **Ethereum** (Uniswap V2/V3, SushiSwap)
- **Arbitrum** (Uniswap V3, SushiSwap, Camelot)
- **Optimism** (Uniswap V3, SushiSwap, Velodrome)
- **BSC** (PancakeSwap, SushiSwap, Biswap)

### Configuration

All chain configurations are in `config.py`:

```python
import config

# Get routers for a specific chain
polygon_routers = config.DEX_ROUTERS['polygon']
# {'quickswap': '0x...', 'sushiswap': '0x...', ...}

# Get tokens for a specific chain
arbitrum_tokens = config.TOKENS_BY_CHAIN['arbitrum']
# {'WETH': '0x...', 'USDC': '0x...', ...}

# Get factories for pair lookups
eth_factories = config.DEX_FACTORIES['ethereum']
```

### Enable Multi-Chain Trading

Update your `.env` to add RPC endpoints:

```bash
# Ethereum
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
ETHEREUM_WSS_URL=wss://eth-mainnet.g.alchemy.com/v2/YOUR_KEY

# Arbitrum
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
ARBITRUM_WSS_URL=wss://arb-mainnet.g.alchemy.com/v2/YOUR_KEY

# Optimism
OPTIMISM_RPC_URL=https://opt-mainnet.g.alchemy.com/v2/YOUR_KEY
OPTIMISM_WSS_URL=wss://opt-mainnet.g.alchemy.com/v2/YOUR_KEY

# BSC
BSC_RPC_URL=https://bsc-dataseed1.binance.org
BSC_WSS_URL=wss://bsc-ws-node.nariox.org:443
```

### Using Multi-Chain in Bot

```python
from rpc_manager import ChainRPCManager
from dex_interface import DexInterface

# Initialize multi-chain RPC manager
chain_rpc = ChainRPCManager()

# Get Web3 for specific chain
w3_arbitrum = chain_rpc.get_web3('arbitrum')
w3_optimism = chain_rpc.get_web3('optimism')

# Create DEX interface for each chain
dex_arbitrum = DexInterface(config.ARBITRUM_RPC_URL)
dex_optimism = DexInterface(config.OPTIMISM_RPC_URL)

# Query prices on different chains
arb_price = await dex_arbitrum.get_token_price(
    'uniswap_v3',
    config.TOKENS_BY_CHAIN['arbitrum']['WETH'],
    config.TOKENS_BY_CHAIN['arbitrum']['USDC']
)
```

---

## 3. Volatility-Triggered Trading

### What is it?

The volatility detector monitors market activity and increases bot activity during high-volatility periods when arbitrage opportunities are more likely.

### Configuration

```python
from volatility_detector import VolatilityDetector

# Create detector
detector = VolatilityDetector(
    high_volatility_threshold=2.0,  # 2% volatility = "high"
    window_size_1h=60,              # 60 samples for 1-hour avg
    window_size_24h=1440,           # 1440 samples for 24-hour avg
    check_interval=60               # Check every 60 seconds
)
```

### Integration with Bot

```python
from volatility_detector import VolatilityTriggeredBot
from arbitrage_bot import ArbitrageBot

# Create bot instances
arb_bot = ArbitrageBot()
detector = VolatilityDetector()

# Create volatility-triggered wrapper
vol_bot = VolatilityTriggeredBot(arb_bot, detector)

# Start adaptive trading
await vol_bot.adaptive_trading_loop()
```

### How It Works

**Normal Volatility**:
- Check interval: 1 second
- Conservative trading
- Lower gas costs

**High Volatility**:
- Check interval: 0.01 seconds (10ms)
- Aggressive scanning
- More opportunities detected

### Monitoring Volatility

```python
# Add price data
detector.add_price_data('ETH/USDT', 2000, volume=1000000)

# Calculate metrics
metrics = detector.calculate_volatility('ETH/USDT')

if metrics:
    print(f"Current volatility: {metrics.current_volatility:.2f}%")
    print(f"Trend: {metrics.volatility_trend}")
    print(f"High volatility: {metrics.is_high_volatility}")

# Check overall state
is_high_vol = detector.is_high_volatility_period(['ETH/USDT', 'BTC/USDT'])

# Get volatility score (0-100)
score = detector.get_volatility_score()
print(f"Volatility score: {score:.1f}/100")
```

### Callbacks

Register a callback for volatility changes:

```python
async def on_volatility_change(event_type):
    if event_type == "high_volatility_start":
        print("🔥 High volatility detected! Increasing scan rate...")
    elif event_type == "high_volatility_end":
        print("📉 Volatility normalized. Returning to normal mode.")

detector.register_callback(on_volatility_change)
```

---

## 4. Mempool Monitoring & Backrunning

### What is Backrunning?

**Backrunning** is the ETHICAL and LEGAL practice of executing trades AFTER a large transaction to capture arbitrage opportunities it creates.

**NOT a sandwich attack** - we don't front-run or harm the original trader.

### Configuration

```python
from mempool_monitor import MempoolMonitor
from web3 import Web3

# Create Web3 with WebSocket
w3 = Web3(Web3.WebsocketProvider(config.POLYGON_WSS_URL))

# Create monitor
monitor = MempoolMonitor(
    w3=w3,
    min_swap_size_usd=50000,  # Only track swaps > $50k
    opportunity_callback=handle_opportunity
)
```

### Integration with Bot

```python
from mempool_monitor import BackrunStrategy

# Create callback for opportunities
async def handle_opportunity(swap):
    logger.warning(
        f"🎯 Large swap detected: "
        f"${swap.amount_in / 1e6:,.0f} on {swap.dex}"
    )

    # Prepare to backrun
    backrun = BackrunStrategy(arb_bot, monitor)
    await backrun.execute_backrun(swap)

# Create monitor with callback
monitor = MempoolMonitor(
    w3=w3,
    min_swap_size_usd=50000,
    opportunity_callback=handle_opportunity
)

# Start monitoring
await monitor.start_monitoring()
```

### How Backrunning Works

1. **Detect**: Large swap enters mempool
2. **Wait**: Wait for transaction to confirm
3. **Verify**: Check if it created price imbalance
4. **Execute**: Execute arbitrage on resulting opportunity

### Example

```
1. Large trader swaps $100k USDC → WETH on Uniswap
2. This moves the price up on Uniswap
3. Now price difference exists: Uniswap (higher) vs SushiSwap (lower)
4. Bot executes: Buy WETH on SushiSwap, Sell on Uniswap
5. Profit from the price imbalance
```

### Monitoring

```python
# Get pending opportunities
opportunities = monitor.get_pending_opportunities()

for opp in opportunities:
    print(f"DEX: {opp.dex}")
    print(f"Amount: ${opp.amount_in / 1e6:,.0f}")
    print(f"Gas: {opp.gas_price / 1e9:.1f} gwei")

# Get monitor status
status = monitor.get_status()
print(f"Pending: {status['pending_opportunities']}")
print(f"Processed: {status['total_transactions_processed']}")
```

---

## Complete Integration Example

Here's how to use all features together:

```python
import asyncio
from web3 import Web3
from loguru import logger

from arbitrage_bot import ArbitrageBot
from volatility_detector import VolatilityDetector, VolatilityTriggeredBot
from mempool_monitor import MempoolMonitor, BackrunStrategy
from rpc_manager import ChainRPCManager
import config


class AdvancedArbitrageBot:
    """Arbitrage bot with all advanced features"""

    def __init__(self):
        # Initialize base bot
        self.bot = ArbitrageBot()

        # Initialize RPC manager for multiple chains
        self.chain_rpc = ChainRPCManager()

        # Initialize volatility detector
        self.volatility_detector = VolatilityDetector(
            high_volatility_threshold=2.0,
            check_interval=60
        )

        # Initialize mempool monitor
        w3 = Web3(Web3.WebsocketProvider(config.POLYGON_WSS_URL))
        self.mempool_monitor = MempoolMonitor(
            w3=w3,
            min_swap_size_usd=50000,
            opportunity_callback=self.handle_mempool_opportunity
        )

        # Initialize backrun strategy
        self.backrun = BackrunStrategy(self.bot, self.mempool_monitor)

        # Create volatility-triggered wrapper
        self.vol_bot = VolatilityTriggeredBot(self.bot, self.volatility_detector)

    async def handle_mempool_opportunity(self, swap):
        """Handle detected mempool opportunity"""
        logger.warning(f"🎯 Large swap: ${swap.amount_in / 1e6:,.0f} on {swap.dex}")

        # Execute backrun
        await self.backrun.execute_backrun(swap)

    async def start(self):
        """Start all monitoring systems"""
        logger.info("Starting Advanced Arbitrage Bot...")

        # Start all monitors in parallel
        tasks = [
            self.vol_bot.adaptive_trading_loop(),
            self.mempool_monitor.start_monitoring(),
            self.chain_rpc.health_check_all()
        ]

        await asyncio.gather(*tasks)


# Run the bot
if __name__ == "__main__":
    bot = AdvancedArbitrageBot()
    asyncio.run(bot.start())
```

---

## Performance Impact

### Multi-Chain Support

**Benefits**:
- 5x more DEXes to arbitrage
- 3-5x more opportunities
- Diversified across chains

**Costs**:
- Need RPC for each chain ($0-49/month per chain)
- More gas on expensive chains (Ethereum)

**Recommendation**: Start with Polygon + Arbitrum (cheapest gas)

### Volatility Detector

**Benefits**:
- 2-5x more opportunities during high volatility
- Lower costs during quiet periods
- Better risk management

**Costs**:
- Negligible (just monitoring)

**Recommendation**: Always enable

### Mempool Monitoring

**Benefits**:
- Early opportunity detection
- Capture opportunities created by large traders
- 10-30% more opportunities

**Costs**:
- Requires WebSocket RPC (included with Alchemy)
- Slightly higher CPU usage

**Recommendation**: Enable for production

---

## Configuration Summary

### Minimal Configuration (.env)

```bash
# Basic
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
POLYGON_WSS_URL=wss://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY

# Trade limits
MAX_TRADE_AMOUNT_CEX=1000
MAX_TRADE_AMOUNT_DEX=500
```

### Recommended Configuration

```bash
# Multi-chain RPCs
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
POLYGON_WSS_URL=wss://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
ARBITRUM_WSS_URL=wss://arb-mainnet.g.alchemy.com/v2/YOUR_KEY

# Trade limits (different for each type)
MAX_TRADE_AMOUNT_CEX=2000
MAX_TRADE_AMOUNT_DEX=500

# Volatility settings (in code)
HIGH_VOLATILITY_THRESHOLD=2.0
CHECK_INTERVAL=60

# Mempool settings (in code)
MIN_SWAP_SIZE_USD=50000
```

### Full Production Configuration

Add Ethereum, Optimism, BSC for maximum coverage (see .env.example)

---

## Testing New Features

### Test Volatility Detector

```bash
python volatility_detector.py
```

### Test Mempool Monitor

```bash
python mempool_monitor.py
```

### Test Multi-Chain

```python
from rpc_manager import ChainRPCManager

rpc = ChainRPCManager()
await rpc.health_check_all()
```

---

## Cost Analysis

### RPC Costs (per month)

| Chains | Free Tier | Paid |
|--------|-----------|------|
| 1 chain (Polygon) | $0 | $49 |
| 2 chains (Poly + Arb) | $0 | $98 |
| 5 chains (All) | $0-49 | $245 |

**Recommendation**: Start with 1-2 chains on free tier

### Gas Costs (per trade)

| Chain | Gas Cost | Break-even |
|-------|----------|------------|
| Polygon | $0.005-$0.05 | $0.10+ profit |
| Arbitrum | $0.10-$0.50 | $1.00+ profit |
| Optimism | $0.10-$0.50 | $1.00+ profit |
| BSC | $0.10-$0.30 | $0.50+ profit |
| Ethereum | $5-$50 | $100+ profit |

**Recommendation**: Focus on Polygon/Arbitrum for low gas costs

---

## Ethical Considerations

### Mempool Monitoring

✅ **Ethical**:
- Backrunning (execute AFTER confirmed trades)
- Defensive front-running (protect your own trades)
- Opportunity detection

❌ **Unethical**:
- Sandwich attacks (front-run + back-run user trades)
- Front-running user trades
- Causing losses to retail traders

### Our Implementation

This bot focuses on BACKRUNNING only:
1. Waits for transaction to confirm
2. Then executes arbitrage on resulting price imbalance
3. No harm to original trader

---

## Next Steps

1. **Week 1**: Test volatility detector
2. **Week 2**: Add one more chain (Arbitrum)
3. **Week 3**: Enable mempool monitoring
4. **Week 4**: Full multi-chain deployment

---

## Support

For issues or questions:
1. Check logs for errors
2. Run test scripts
3. Review DEPLOYMENT_GUIDE_V2.md

---

Generated: 2025-11-11
Version: 2.1.0
