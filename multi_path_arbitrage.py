"""
Multi-Path Arbitrage Detection Module

This module detects arbitrage opportunities across multiple trading paths,
not just direct token pairs. Examples:
- Path 1: USDT -> WETH -> WMATIC -> USDT (3-hop)
- Path 2: WETH -> WBTC -> USDC -> WETH (3-hop)

This significantly increases the number of arbitrage opportunities.
"""

import asyncio
from typing import Dict, List, Tuple, Optional
from itertools import permutations, combinations
from loguru import logger
from web3 import Web3
import config
from mev_protection import mev_protection, gas_optimizer


class MultiPathArbitrageDetector:
    """Detect and execute multi-path arbitrage opportunities"""

    def __init__(self):
        # Available tokens for paths
        self.token_pool = {
            'polygon': list(config.TOKENS.values()),
            'arbitrum': list(config.TOKENS.values()),
            'optimism': list(config.TOKENS.values()),
            'bsc': list(config.TOKENS.values()),
        }

        # DEXs available on each chain
        self.dexs_per_chain = {
            'polygon': ['quickswap', 'sushiswap', 'uniswap_v3'],
            'arbitrum': ['uniswap_v3', 'sushiswap'],
            'optimism': ['uniswap_v3', 'sushiswap'],
            'bsc': ['pancakeswap', 'sushiswap'],
        }

        # Cache for path prices (TTL: 5 seconds)
        self.price_cache = {}
        self.cache_timestamp = {}
        self.cache_ttl = 5

        # Track profitable paths
        self.profitable_paths = []

    async def find_all_arbitrage_paths(
        self,
        chain: str,
        max_hops: int = 3,
        min_profit_threshold: float = config.MIN_PROFIT_THRESHOLD
    ) -> List[Dict]:
        """
        Find all arbitrage opportunities across multiple paths

        Args:
            chain: Blockchain name (polygon, arbitrum, etc.)
            max_hops: Maximum number of hops in a path (2-4)
            min_profit_threshold: Minimum profit % to consider

        Returns:
            List of profitable paths
        """
        opportunities = []

        try:
            # Start with 2-hop paths (fastest to calculate)
            logger.info(f"Scanning 2-hop paths on {chain}...")
            two_hop = await self._find_paths_with_length(
                chain, 2, min_profit_threshold
            )
            opportunities.extend(two_hop)

            # Then 3-hop paths (more opportunities)
            if max_hops >= 3:
                logger.info(f"Scanning 3-hop paths on {chain}...")
                three_hop = await self._find_paths_with_length(
                    chain, 3, min_profit_threshold
                )
                opportunities.extend(three_hop)

            # Finally 4-hop paths (most opportunities but slower)
            if max_hops >= 4:
                logger.info(f"Scanning 4-hop paths on {chain}...")
                four_hop = await self._find_paths_with_length(
                    chain, 4, min_profit_threshold
                )
                opportunities.extend(four_hop)

            # Sort by profit (highest first)
            opportunities.sort(
                key=lambda x: x['profit_percentage'],
                reverse=True
            )

            logger.info(
                f"Found {len(opportunities)} profitable paths on {chain}: "
                f"{[p['profit_percentage'] for p in opportunities[:5]]}"
            )

            return opportunities

        except Exception as e:
            logger.error(f"Error finding arbitrage paths: {str(e)}")
            return []

    async def _find_paths_with_length(
        self,
        chain: str,
        path_length: int,
        min_profit_threshold: float
    ) -> List[Dict]:
        """Find profitable paths of specific length"""
        paths = []
        tokens = self.token_pool.get(chain, [])

        if len(tokens) < path_length:
            return paths

        # Generate all permutations of tokens for this path length
        # For efficiency, limit to top 10 liquidity tokens
        top_tokens = await self._get_top_liquidity_tokens(chain)

        # Generate combinations (start token must appear at start and end)
        for start_token in top_tokens:
            # Get permutations of other tokens
            other_tokens = [t for t in top_tokens if t != start_token]

            # For paths of length n, we need n-1 intermediate tokens
            for intermediate_tokens in combinations(other_tokens, path_length - 1):
                # Try all permutations of intermediate tokens
                for perm in permutations(intermediate_tokens):
                    path = [start_token] + list(perm) + [start_token]

                    # Calculate profit for this path
                    profit = await self._calculate_path_profit(
                        chain, path
                    )

                    if profit and profit['profit_percentage'] >= min_profit_threshold:
                        paths.append({
                            'path': path,
                            'path_length': path_length,
                            'profit_percentage': profit['profit_percentage'],
                            'profit_amount': profit['profit_amount'],
                            'chain': chain,
                            'input_amount': profit['input_amount'],
                            'output_amount': profit['output_amount']
                        })

        return paths

    async def _get_top_liquidity_tokens(self, chain: str) -> List[str]:
        """Get tokens with highest liquidity on a chain"""
        # This should integrate with actual DEX data
        # For now, return a prioritized list
        tokens_by_priority = {
            'polygon': [
                config.TOKENS.get('USDT'),
                config.TOKENS.get('USDC'),
                config.TOKENS.get('WETH'),
                config.TOKENS.get('WMATIC'),
                config.TOKENS.get('WBTC'),
            ],
            'arbitrum': [
                config.TOKENS.get('USDT'),
                config.TOKENS.get('USDC'),
                config.TOKENS.get('WETH'),
                config.TOKENS.get('WBTC'),
            ],
            'optimism': [
                config.TOKENS.get('USDT'),
                config.TOKENS.get('USDC'),
                config.TOKENS.get('WETH'),
                config.TOKENS.get('WBTC'),
            ],
            'bsc': [
                config.TOKENS.get('USDT'),
                config.TOKENS.get('USDC'),
                config.TOKENS.get('WETH'),
                config.TOKENS.get('WBTC'),
            ],
        }

        tokens = tokens_by_priority.get(chain, [])
        return [t for t in tokens if t is not None]

    async def _calculate_path_profit(
        self,
        chain: str,
        path: List[str],
        input_amount: float = 1000  # 1000 USDT equivalent
    ) -> Optional[Dict]:
        """
        Calculate profit for a trading path

        Args:
            chain: Blockchain name
            path: List of token addresses in the path
            input_amount: Input amount in USD

        Returns:
            Dict with profit info or None if path is not profitable
        """
        try:
            # Check cache first
            path_key = f"{chain}:{'->'.join(path)}"
            if self._is_cache_valid(path_key):
                return self.price_cache.get(path_key)

            # Calculate output amount through the path
            current_amount = input_amount
            dexs = self.dexs_per_chain.get(chain, [])

            for i in range(len(path) - 1):
                token_in = path[i]
                token_out = path[i + 1]

                # Select DEX (rotate through available DEXs)
                dex = dexs[i % len(dexs)]

                # Get output amount (simplified - should call actual DEX)
                output = await self._get_swap_output(
                    chain, dex, token_in, token_out, current_amount
                )

                if output is None or output <= 0:
                    return None  # Path is not viable

                current_amount = output

            # Calculate profit
            profit_amount = current_amount - input_amount
            profit_percentage = (profit_amount / input_amount) * 100

            # Cache the result
            result = {
                'profit_amount': profit_amount,
                'profit_percentage': profit_percentage,
                'input_amount': input_amount,
                'output_amount': current_amount
            }

            self.price_cache[path_key] = result
            self.cache_timestamp[path_key] = asyncio.get_event_loop().time()

            return result

        except Exception as e:
            logger.debug(f"Error calculating path profit: {str(e)}")
            return None

    async def _get_swap_output(
        self,
        chain: str,
        dex: str,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> Optional[float]:
        """
        Get output amount for a swap (placeholder - should integrate with actual DEX)

        Returns:
            Output amount or None if swap is not possible
        """
        try:
            # This is a simplified placeholder
            # In production, this should call the actual DEX router contract
            # Using getAmountsOut or similar methods

            # For now, return approximate values based on historical spreads
            # This should be replaced with actual contract calls

            # Typical slippage on DEXs is 0.3-0.5% per swap
            slippage = 0.003  # 0.3%
            output = amount_in * (1 - slippage)

            return output

        except Exception as e:
            logger.debug(f"Error getting swap output: {str(e)}")
            return None

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache_timestamp:
            return False

        current_time = asyncio.get_event_loop().time()
        cache_age = current_time - self.cache_timestamp[cache_key]

        return cache_age < self.cache_ttl

    async def execute_multi_path_arbitrage(
        self,
        opportunity: Dict,
        w3: Web3
    ) -> bool:
        """
        Execute a multi-path arbitrage opportunity

        Args:
            opportunity: Path opportunity to execute
            w3: Web3 instance

        Returns:
            True if successful, False otherwise
        """
        try:
            path = opportunity['path']
            chain = opportunity['chain']

            logger.info(
                f"Executing {len(path)-1}-hop arbitrage on {chain}: "
                f"Profit: {opportunity['profit_percentage']:.2f}%"
            )

            # Execute swaps along the path
            current_amount = opportunity['input_amount']
            dexs = self.dexs_per_chain.get(chain, [])

            for i in range(len(path) - 1):
                token_in = path[i]
                token_out = path[i + 1]
                dex = dexs[i % len(dexs)]

                # Execute swap
                tx_hash = await self._execute_swap(
                    w3, chain, dex, token_in, token_out, current_amount
                )

                if not tx_hash:
                    logger.error(f"Failed to execute swap {i+1} on path")
                    return False

                # Get actual output amount
                # (In production, parse the transaction receipt)
                current_amount = opportunity['output_amount']

            logger.info(
                f"Successfully executed multi-path arbitrage. "
                f"Profit: ${opportunity['profit_amount']:.2f}"
            )

            return True

        except Exception as e:
            logger.error(f"Error executing multi-path arbitrage: {str(e)}")
            return False

    async def _execute_swap(
        self,
        w3: Web3,
        chain: str,
        dex: str,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> Optional[str]:
        """Execute a single swap in the path"""
        try:
            # This should call the actual DEX router contract
            # Implementation depends on specific DEX

            # Get optimal gas price
            gas_price = mev_protection.calculate_optimal_gas_price(
                w3, chain, urgency='normal'
            )

            # Execute swap (placeholder)
            # In production, build and send actual transaction
            logger.debug(f"Executing {dex} swap: {amount_in} {token_in} -> {token_out}")

            return "0x" + "0" * 64  # Placeholder transaction hash

        except Exception as e:
            logger.error(f"Error executing swap: {str(e)}")
            return None

    async def monitor_multi_path_opportunities(self, chain: str):
        """Continuously monitor for multi-path arbitrage opportunities"""
        while True:
            try:
                # Find opportunities
                opportunities = await self.find_all_arbitrage_paths(
                    chain,
                    max_hops=3,
                    min_profit_threshold=config.MIN_PROFIT_THRESHOLD
                )

                # Log top opportunities
                if opportunities:
                    logger.info(
                        f"Top 3 opportunities on {chain}: "
                        f"{[(o['path_length'], f\"{o['profit_percentage']:.2f}%\") for o in opportunities[:3]]}"
                    )

                # Wait before next scan
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(5)


# Create singleton instance
multi_path_detector = MultiPathArbitrageDetector()
