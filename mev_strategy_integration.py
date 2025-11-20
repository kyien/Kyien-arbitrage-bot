#!/usr/bin/env python3
"""
MEV Strategy Integration Module

Integrates advanced MEV strategies into the main arbitrage bot.
Provides easy-to-use wrappers for MEV protection and extraction.
"""

import asyncio
from typing import Dict, List, Optional
from loguru import logger
import config
from advanced_mev_strategies import create_mev_strategies, create_cross_chain_mev
from mev_protection import mev_protection, gas_optimizer


class MEVStrategyManager:
    """Manages MEV strategies for the arbitrage bot"""
    
    def __init__(self):
        self.strategies = {}
        self.cross_chain_strategy = None
        self.enabled = True
        
        # Initialize strategies for each chain
        for chain in ['polygon', 'arbitrum', 'optimism', 'bsc']:
            try:
                self.strategies[chain] = create_mev_strategies(chain)
                logger.info(f"✓ MEV strategy initialized for {chain}")
            except Exception as e:
                logger.warning(f"⚠ Failed to initialize MEV strategy for {chain}: {e}")
        
        # Initialize cross-chain strategy
        try:
            self.cross_chain_strategy = create_cross_chain_mev()
            logger.info("✓ Cross-chain MEV strategy initialized")
        except Exception as e:
            logger.warning(f"⚠ Failed to initialize cross-chain MEV: {e}")
    
    async def start_all_strategies(self):
        """Start all MEV strategy monitoring"""
        if not self.enabled:
            logger.warning("MEV strategies are disabled")
            return
        
        logger.info("Starting all MEV strategies...")
        
        tasks = []
        
        # Start chain-specific strategies
        for chain, strategy in self.strategies.items():
            try:
                task = asyncio.create_task(strategy.start_all_strategies())
                tasks.append(task)
                logger.info(f"Started MEV strategies for {chain}")
            except Exception as e:
                logger.error(f"Error starting MEV strategies for {chain}: {e}")
        
        # Start cross-chain strategy
        if self.cross_chain_strategy:
            try:
                task = asyncio.create_task(
                    self.cross_chain_strategy.monitor_cross_chain_opportunities()
                )
                tasks.append(task)
                logger.info("Started cross-chain MEV monitoring")
            except Exception as e:
                logger.error(f"Error starting cross-chain MEV: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("✅ All MEV strategies running")
        else:
            logger.warning("No MEV strategies were started")

    def stop_all_strategies(self):
        """Stop all MEV strategies"""
        logger.info("Stopping MEV strategies...")
        self.enabled = False

    def get_strategy(self, chain: str) -> Optional:
        """Get MEV strategy for specific chain"""
        return self.strategies.get(chain)

    async def execute_with_mev_protection(
        self,
        chain: str,
        trades: List[Dict],
        profit_usd: float
    ) -> Optional[str]:
        """
        Execute trades with advanced MEV protection
        
        Args:
            chain: Blockchain name
            trades: List of trade dictionaries
            profit_usd: Expected profit in USD
            
        Returns:
            Transaction hash if successful
        """
        if not self.enabled:
            logger.warning("MEV protection disabled, executing without protection")
            return await self._execute_without_protection(chain, trades)
        
        strategy = self.get_strategy(chain)
        if not strategy:
            logger.warning(f"No MEV strategy for {chain}, executing without protection")
            return await self._execute_without_protection(chain, trades)
        
        # Execute with batching for MEV protection
        if len(trades) > 1:
            logger.info(f"Executing {len(trades)} trades with batch MEV protection")
            return await strategy.execute_batched_flashswap(trades)
        else:
            logger.info(f"Executing single trade with MEV protection")
            return await strategy._execute_single_trade(trades[0], {})

    async def _execute_without_protection(self, chain: str, trades: List[Dict]) -> Optional[str]:
        """
        Fallback execution without MEV protection
        Used when strategies are disabled or unavailable
        """
        logger.warning(f"Executing {len(trades)} trades without MEV protection on {chain}")
        
        # This would need to integrate with the main bot's execution logic
        # For now, log the attempt and return None
        logger.warning("Fallback execution not implemented - MEV protection is required")
        return None


# Global MEV strategy manager
mev_manager = MEVStrategyManager()


def main():
    """Main entry point for MEV strategy integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MEV Strategy Integration')
    parser.add_argument('--test', action='store_true', help='Run integration tests')
    parser.add_argument('--start', action='store_true', help='Start MEV strategies')
    parser.add_argument('--chain', type=str, default='polygon', help='Chain to test')
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_mev_integration())
    elif args.start:
        asyncio.run(mev_manager.start_all_strategies())
    else:
        print("Use --test to run integration tests or --start to start MEV strategies")


async def test_mev_integration():
    """Test MEV strategy integration"""
    logger.info("Testing MEV strategy integration...")
    
    # Test strategy creation
    manager = MEVStrategyManager()
    
    # Test getting strategy
    polygon_strategy = manager.get_strategy('polygon')
    if polygon_strategy:
        logger.info("✅ Polygon MEV strategy available")
    else:
        logger.error("❌ Polygon MEV strategy not available")
    
    # Test starting strategies (async)
    try:
        await asyncio.wait_for(manager.start_all_strategies(), timeout=5.0)
        logger.info("✅ MEV strategies started successfully")
    except asyncio.TimeoutError:
        logger.info("✅ MEV strategies started (timeout expected in test)")
    except Exception as e:
        logger.error(f"❌ Error starting MEV strategies: {e}")
    
    logger.info("MEV integration test completed")


if __name__ == "__main__":
    main()
