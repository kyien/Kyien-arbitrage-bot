# Monitoring Integration Guide

**Purpose**: How to integrate the monitoring and alerting system into your arbitrage bot
**Files**: monitoring_alerts.py, logging_config.py, scripts/health_check.py

---

## Quick Integration

### Step 1: Update Imports

Add to the top of `multi_chain_bot.py` and `arbitrage_bot.py`:

```python
# Add these imports
from monitoring_alerts import alert_manager
from logging_config import setup_logging, log_trade, log_performance
from scripts.health_check import update_heartbeat
```

### Step 2: Setup Logging (Start of main())

```python
async def main():
    """Main function"""
    # Setup logging first
    setup_logging(
        log_dir=os.getenv('LOG_DIR', '/var/log/arbitrage-bot'),
        retention="7 days",
        rotation="daily"
    )

    logger.info("Arbitrage bot starting...")

    # Send startup alert
    chains = ['polygon', 'arbitrum', 'optimism', 'bsc']
    await alert_manager.bot_started(chains)

    # Rest of your code...
```

### Step 3: Add Heartbeat Updates

In your main loop, update heartbeat every 60 seconds:

```python
class MultiChainArbitrageBot:
    async def monitor_status(self):
        """Monitor and update status"""
        while self.running:
            # Update heartbeat for health checks
            rpc_status = {}
            gas_balances = {}

            for chain, bot in self.chain_bots.items():
                # Check RPC connectivity
                try:
                    is_connected = bot.w3.is_connected()
                    rpc_status[chain] = 'connected' if is_connected else 'disconnected'
                except:
                    rpc_status[chain] = 'disconnected'

                # Get gas balance (in USD)
                try:
                    balance = bot.w3.eth.get_balance(config.WALLET_ADDRESS)
                    balance_eth = bot.w3.from_wei(balance, 'ether')
                    # Convert to USD (you can get price from your price feed)
                    balance_usd = float(balance_eth) * 2000  # Placeholder price
                    gas_balances[chain] = balance_usd
                except:
                    gas_balances[chain] = 0

            # Update heartbeat
            update_heartbeat(
                rpc_status=rpc_status,
                gas_balances=gas_balances,
                trade_count=sum(s['trades_executed'] for s in self.stats.values()),
                error_count=0
            )

            await asyncio.sleep(60)
```

### Step 4: Add Alerts for Events

#### Opportunity Found

```python
async def check_dex_arbitrage(self):
    """Check for arbitrage opportunities"""
    for pair in config.TRADING_PAIRS['DEX']:
        # ... your existing code to find opportunity ...

        if profit_usd > config.MIN_PROFIT_THRESHOLD:
            # Alert: Opportunity found
            await alert_manager.opportunity_found(
                chain=self.chain,
                dex1=dex1,
                dex2=dex2,
                token_pair=pair,
                profit=profit_usd
            )

            # Execute arbitrage...
```

#### Execution Started

```python
async def execute_dex_flashswap(self, ...):
    """Execute flash swap"""

    # Alert: Execution started
    await alert_manager.execution_started(
        chain=chain,
        token_pair=f"{token_in}/{token_out}",
        expected_profit=expected_profit
    )

    # Execute transaction...
```

#### Execution Completed

```python
# After successful execution
if receipt.status == 1:
    # Log trade
    log_trade(
        trade_type="DEX_ARBITRAGE",
        chain=chain,
        token_pair=f"{token_in}/{token_out}",
        profit=actual_profit,
        tx_hash=tx_hash,
        gas_used=receipt.gasUsed
    )

    # Alert: Execution successful
    await alert_manager.execution_completed(
        chain=chain,
        tx_hash=tx_hash,
        token_pair=f"{token_in}/{token_out}",
        actual_profit=actual_profit,
        gas_cost=gas_cost,
        net_profit=net_profit
    )
else:
    # Alert: Execution failed
    await alert_manager.execution_failed(
        chain=chain,
        token_pair=f"{token_in}/{token_out}",
        reason="Transaction reverted",
        tx_hash=tx_hash
    )
```

#### MEV Detected

```python
# In MEV detection logic
if mev_detected:
    await alert_manager.mev_detected(
        chain=chain,
        tx_hash=tx_hash,
        mev_type="front-run",  # or "sandwich", "back-run"
        estimated_loss=estimated_loss
    )
```

#### High Slippage

```python
# After executing trade
if slippage_pct > config.SLIPPAGE_TOLERANCE:
    await alert_manager.slippage_alert(
        chain=chain,
        tx_hash=tx_hash,
        expected=expected_amount,
        actual=actual_amount,
        slippage_pct=slippage_pct
    )
```

#### Gas Exhaustion

```python
# Check gas balance periodically
if gas_balance_usd < float(os.getenv('MIN_GAS_BALANCE_USD', '10')):
    await alert_manager.gas_exhaustion_alert(
        chain=chain,
        current_balance=gas_balance_usd,
        threshold=float(os.getenv('MIN_GAS_BALANCE_USD', '10'))
    )
```

#### Wallet Balance Update

```python
# After withdrawal or significant balance change
await alert_manager.wallet_balance_update(
    chain=chain,
    token=token_symbol,
    old_balance=old_balance_usd,
    new_balance=new_balance_usd
)
```

#### Error Handling

```python
try:
    # Your bot logic
    pass
except Exception as e:
    # Log error
    logger.error(f"Bot error: {str(e)}")
    import traceback
    tb = traceback.format_exc()

    # Alert: Bot error
    await alert_manager.bot_error(
        error=str(e),
        traceback=tb
    )
```

### Step 5: Graceful Shutdown

```python
async def shutdown(signal, loop):
    """Graceful shutdown"""
    logger.info(f"Received exit signal {signal.name}")

    # Alert: Bot stopping
    await alert_manager.bot_stopped(reason=f"Signal {signal.name}")

    # Stop bot
    bot.running = False

    # Cancel all tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

# Register signal handlers
import signal
for sig in (signal.SIGTERM, signal.SIGINT):
    asyncio.get_event_loop().add_signal_handler(
        sig, lambda s=sig: asyncio.create_task(shutdown(s, asyncio.get_event_loop()))
    )
```

---

## Complete Example Integration

Here's a complete example of multi_chain_bot.py with monitoring:

```python
import asyncio
import os
import signal
from typing import Dict, List
from loguru import logger
from arbitrage_bot import ArbitrageBot
import config

# Import monitoring
from monitoring_alerts import alert_manager
from logging_config import setup_logging, log_trade, log_performance
from scripts.health_check import update_heartbeat


class MultiChainArbitrageBot:
    def __init__(self, chains: List[str] = None, enable_cex: bool = False):
        """Initialize multi-chain bot with monitoring"""
        # Setup logging first
        setup_logging(
            log_dir=os.getenv('LOG_DIR', '/var/log/arbitrage-bot'),
            retention="7 days",
            rotation="daily"
        )

        logger.info("Initializing Multi-Chain Arbitrage Bot with Monitoring...")

        if chains is None:
            chains = ['polygon', 'arbitrum', 'optimism', 'bsc']

        self.chains = chains
        self.running = False
        self.chain_bots: Dict[str, ArbitrageBot] = {}
        self.stats = {}

        # Initialize bots
        for chain in chains:
            logger.info(f"Initializing bot for {chain}")
            bot = ArbitrageBot(chain=chain, enable_cex=(enable_cex and chain == chains[0]))
            self.chain_bots[chain] = bot
            self.stats[chain] = {
                'opportunities_found': 0,
                'trades_executed': 0,
                'total_profit': 0.0
            }

    async def start_chain(self, chain: str):
        """Start bot for specific chain with monitoring"""
        logger.info(f"Starting bot for {chain}")
        bot = self.chain_bots[chain]
        bot.running = True

        try:
            # Run DEX arbitrage
            dex_task = self.check_dex_with_monitoring(chain)
            await dex_task
        except Exception as e:
            logger.error(f"Error on {chain}: {str(e)}")
            await alert_manager.bot_error(
                error=f"{chain}: {str(e)}",
                traceback=None
            )

    async def check_dex_with_monitoring(self, chain: str):
        """DEX arbitrage with monitoring"""
        bot = self.chain_bots[chain]

        while bot.running:
            try:
                # Your existing DEX arbitrage logic
                # When opportunity found:
                # await alert_manager.opportunity_found(...)

                # When trade executed:
                # await alert_manager.execution_completed(...)

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"DEX check error on {chain}: {str(e)}")
                await alert_manager.bot_error(error=str(e))

    async def monitor_status(self):
        """Monitor status and update heartbeat"""
        while self.running:
            try:
                # Collect RPC status
                rpc_status = {}
                gas_balances = {}

                for chain, bot in self.chain_bots.items():
                    try:
                        rpc_status[chain] = 'connected' if bot.w3.is_connected() else 'disconnected'

                        balance = bot.w3.eth.get_balance(config.WALLET_ADDRESS)
                        balance_eth = float(bot.w3.from_wei(balance, 'ether'))
                        gas_balances[chain] = balance_eth * 2000  # Convert to USD

                        # Check gas threshold
                        if gas_balances[chain] < float(os.getenv('MIN_GAS_BALANCE_USD', '10')):
                            await alert_manager.gas_exhaustion_alert(
                                chain=chain,
                                current_balance=gas_balances[chain],
                                threshold=float(os.getenv('MIN_GAS_BALANCE_USD', '10'))
                            )
                    except:
                        rpc_status[chain] = 'disconnected'
                        gas_balances[chain] = 0

                # Update heartbeat
                update_heartbeat(
                    rpc_status=rpc_status,
                    gas_balances=gas_balances,
                    trade_count=sum(s['trades_executed'] for s in self.stats.values()),
                    error_count=0
                )

                # Log status
                logger.info("=== Multi-Chain Status ===")
                for chain, stats in self.stats.items():
                    logger.info(
                        f"{chain}: Opportunities: {stats['opportunities_found']}, "
                        f"Trades: {stats['trades_executed']}, "
                        f"Profit: ${stats['total_profit']:.2f}"
                    )

            except Exception as e:
                logger.error(f"Status monitoring error: {str(e)}")

            await asyncio.sleep(60)

    async def start_all(self):
        """Start all chains with monitoring"""
        self.running = True

        # Send startup alert
        await alert_manager.bot_started(list(self.chains))

        # Start all chains
        tasks = [self.start_chain(chain) for chain in self.chains]
        tasks.append(self.monitor_status())

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in start_all: {str(e)}")
            await alert_manager.bot_error(error=str(e))

    async def stop_all(self, reason: str = "Manual stop"):
        """Stop all chains"""
        logger.info(f"Stopping all chains: {reason}")

        self.running = False
        for bot in self.chain_bots.values():
            bot.running = False

        # Send shutdown alert
        await alert_manager.bot_stopped(reason=reason)


async def shutdown(signal_name, loop, bot):
    """Graceful shutdown"""
    logger.info(f"Received exit signal {signal_name}")
    await bot.stop_all(reason=f"Signal {signal_name}")

    # Cancel all tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main():
    """Main function"""
    # Initialize bot
    bot = MultiChainArbitrageBot(
        chains=['polygon', 'arbitrum', 'optimism', 'bsc'],
        enable_cex=False
    )

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(shutdown(s.name, loop, bot))
        )

    # Start bot
    try:
        await bot.start_all()
    except KeyboardInterrupt:
        await bot.stop_all(reason="Keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        await alert_manager.bot_error(error=str(e))
        await bot.stop_all(reason=f"Fatal error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Testing Alerts

### Test Alert Delivery

```python
# Test all alert types
import asyncio
from monitoring_alerts import alert_manager

async def test_alerts():
    # Test opportunity found
    await alert_manager.opportunity_found(
        chain='polygon',
        dex1='QuickSwap',
        dex2='SushiSwap',
        token_pair='WETH/USDC',
        profit=15.50
    )

    await asyncio.sleep(2)

    # Test execution completed
    await alert_manager.execution_completed(
        chain='polygon',
        tx_hash='0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        token_pair='WETH/USDC',
        actual_profit=14.80,
        gas_cost=0.50,
        net_profit=14.30
    )

    await asyncio.sleep(2)

    # Test gas exhaustion
    await alert_manager.gas_exhaustion_alert(
        chain='polygon',
        current_balance=5.00,
        threshold=10.00
    )

asyncio.run(test_alerts())
```

### Test Health Checks

```bash
# Test health check
python scripts/health_check.py

# Should output:
# Health Status: ✅ HEALTHY or ❌ UNHEALTHY
# Checks Passed: X/6
# ...
```

### Test Logging

```python
from logging_config import log_trade, log_performance

# Test trade logging
log_trade(
    trade_type="DEX_ARBITRAGE",
    chain="polygon",
    token_pair="WETH/USDC",
    profit=15.50,
    tx_hash="0x1234...",
    gas_used=250000
)

# Test performance logging
log_performance(
    metric="execution_time",
    value=85.5,
    unit="ms",
    chain="polygon",
    success=True
)
```

---

## Best Practices

1. **Always call setup_logging() first** in your main function
2. **Update heartbeat every 60 seconds** for health checks
3. **Send alerts for all important events** (opportunities, executions, errors)
4. **Use structured logging** with log_trade() and log_performance()
5. **Implement graceful shutdown** to send bot_stopped alert
6. **Test alerts before production** to ensure delivery working
7. **Monitor resource usage** to stay within VPS limits

---

## Troubleshooting

### Alerts Not Received

1. Check Telegram bot token and chat ID in .env
2. Test with monitoring_alerts.py directly
3. Check firewall/network connectivity
4. Verify webhook URLs are accessible

### Health Checks Failing

1. Ensure heartbeat is being updated every 60 seconds
2. Check RPC connectivity
3. Verify log files are being written
4. Check disk space and memory usage

### Logs Not Rotating

1. Verify logrotate configuration installed
2. Check log directory permissions
3. Test rotation: `sudo logrotate -f /etc/logrotate.d/arbitrage-bot`

---

**You're now ready to deploy with full monitoring and alerting! 🚀**
