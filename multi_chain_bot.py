"""
Multi-Chain Arbitrage Bot
Manages multiple ArbitrageBot instances across different chains simultaneously
"""

import asyncio
from loguru import logger
from arbitrage_bot import ArbitrageBot
import config
from typing import List, Dict
import time


class MultiChainArbitrageBot:
    """
    Multi-chain arbitrage bot that runs separate bot instances on multiple chains simultaneously

    This enables:
    - 3-5x more arbitrage opportunities
    - Better capital efficiency
    - Risk diversification across chains
    """

    def __init__(self, chains: List[str] = None, enable_cex: bool = False):
        """
        Initialize multi-chain arbitrage bot

        Args:
            chains: List of chains to operate on. Defaults to all supported chains.
                   Example: ['polygon', 'arbitrum', 'optimism', 'bsc']
            enable_cex: Whether to enable CEX trading (requires API keys and capital)
        """
        # Use all supported chains if none specified
        if chains is None:
            chains = ['polygon', 'arbitrum', 'optimism', 'bsc']

        self.chains = chains
        self.enable_cex = enable_cex
        self.chain_bots: Dict[str, ArbitrageBot] = {}
        self.running = False

        # Statistics tracking
        self.stats = {
            chain: {
                'opportunities_found': 0,
                'trades_executed': 0,
                'total_profit': 0.0,
                'errors': 0,
                'status': 'initializing'
            } for chain in chains
        }

        logger.info(f"Initializing multi-chain arbitrage bot for {len(chains)} chains")

        # Initialize bot for each chain
        for chain in chains:
            try:
                # Create bot instance for this chain
                # Note: CEX should only be enabled for one bot to avoid duplicate trades
                bot = ArbitrageBot(chain=chain, enable_cex=(enable_cex and chain == chains[0]))
                self.chain_bots[chain] = bot
                self.stats[chain]['status'] = 'ready'
                logger.info(f"✓ Initialized bot for {chain} chain")
            except Exception as e:
                logger.error(f"✗ Failed to initialize bot for {chain}: {str(e)}")
                self.stats[chain]['status'] = 'failed'

        if not self.chain_bots:
            raise RuntimeError("Failed to initialize any chain bots")

        logger.info(f"Multi-chain bot ready with {len(self.chain_bots)}/{len(chains)} chains active")

    async def start_chain(self, chain: str):
        """
        Start arbitrage bot for a specific chain

        Args:
            chain: Chain name to start
        """
        bot = self.chain_bots.get(chain)
        if not bot:
            logger.error(f"No bot found for chain: {chain}")
            return

        logger.info(f"🚀 Starting {chain} chain bot...")
        self.stats[chain]['status'] = 'running'

        try:
            bot.running = True

            # Start DEX arbitrage monitoring (always enabled)
            dex_task = bot.check_dex_arbitrage()

            # Start CEX arbitrage if enabled (only for first chain)
            tasks = [dex_task]

            if bot.enable_cex:
                logger.info(f"  - CEX trading enabled for {chain}")
                cex_task = bot.check_cex_arbitrage()
                binance_ws = bot.connect_binance_websocket()
                okx_ws = bot.connect_okx_websocket()
                tasks.extend([cex_task, binance_ws, okx_ws])

            # Run all tasks for this chain
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error in {chain} chain bot: {str(e)}")
            self.stats[chain]['status'] = 'error'
            self.stats[chain]['errors'] += 1
        finally:
            bot.running = False
            self.stats[chain]['status'] = 'stopped'

    async def start_all(self):
        """Start all chain bots in parallel"""
        self.running = True
        logger.info("=" * 60)
        logger.info("🚀 STARTING MULTI-CHAIN ARBITRAGE BOT")
        logger.info("=" * 60)
        logger.info(f"Active chains: {', '.join(self.chain_bots.keys())}")
        logger.info(f"CEX trading: {'enabled' if self.enable_cex else 'disabled'}")
        logger.info("=" * 60)

        # Create tasks for all chains
        tasks = [
            self.start_chain(chain)
            for chain in self.chain_bots.keys()
        ]

        # Add monitoring task
        tasks.append(self.monitor_status())

        # Run all chains in parallel
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            await self.stop_all()

    async def stop_all(self):
        """Stop all chain bots"""
        logger.info("Stopping all chain bots...")
        self.running = False

        for chain, bot in self.chain_bots.items():
            bot.stop()
            self.stats[chain]['status'] = 'stopped'
            logger.info(f"✓ Stopped {chain} chain bot")

        # Print final statistics
        await self.print_summary()

    async def monitor_status(self):
        """Monitor and log status of all chains periodically"""
        while self.running:
            await asyncio.sleep(60)  # Print status every minute

            logger.info("=" * 60)
            logger.info("📊 MULTI-CHAIN STATUS REPORT")
            logger.info("=" * 60)

            for chain, stats in self.stats.items():
                logger.info(
                    f"{chain.upper():12} | "
                    f"Status: {stats['status']:12} | "
                    f"Opportunities: {stats['opportunities_found']:4} | "
                    f"Trades: {stats['trades_executed']:4} | "
                    f"Profit: ${stats['total_profit']:8.2f} | "
                    f"Errors: {stats['errors']:3}"
                )

            logger.info("=" * 60)

    async def print_summary(self):
        """Print final summary statistics"""
        logger.info("=" * 60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 60)

        total_opportunities = sum(s['opportunities_found'] for s in self.stats.values())
        total_trades = sum(s['trades_executed'] for s in self.stats.values())
        total_profit = sum(s['total_profit'] for s in self.stats.values())
        total_errors = sum(s['errors'] for s in self.stats.values())

        logger.info(f"Total Opportunities Found: {total_opportunities}")
        logger.info(f"Total Trades Executed: {total_trades}")
        logger.info(f"Total Profit: ${total_profit:.2f}")
        logger.info(f"Total Errors: {total_errors}")
        logger.info("=" * 60)

        for chain, stats in self.stats.items():
            logger.info(f"\n{chain.upper()} Chain:")
            logger.info(f"  Opportunities: {stats['opportunities_found']}")
            logger.info(f"  Trades: {stats['trades_executed']}")
            logger.info(f"  Profit: ${stats['total_profit']:.2f}")
            logger.info(f"  Errors: {stats['errors']}")

    def get_status(self) -> Dict:
        """Get current status of all chains"""
        return {
            'running': self.running,
            'chains': self.stats,
            'total_opportunities': sum(s['opportunities_found'] for s in self.stats.values()),
            'total_trades': sum(s['trades_executed'] for s in self.stats.values()),
            'total_profit': sum(s['total_profit'] for s in self.stats.values())
        }


async def main():
    """Main entry point for multi-chain bot"""
    import sys

    # Parse command line arguments
    chains = None
    enable_cex = False

    if len(sys.argv) > 1:
        # Allow specifying specific chains
        # Example: python multi_chain_bot.py polygon arbitrum
        chains = sys.argv[1:]

        # Check for --cex flag
        if '--cex' in chains:
            enable_cex = True
            chains.remove('--cex')

    # Create and start multi-chain bot
    bot = MultiChainArbitrageBot(chains=chains, enable_cex=enable_cex)

    try:
        await bot.start_all()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
        await bot.stop_all()


if __name__ == "__main__":
    logger.info("Starting Multi-Chain Arbitrage Bot v2.0.0")
    asyncio.run(main())
