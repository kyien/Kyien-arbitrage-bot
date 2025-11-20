"""
Mempool Monitor for Front-Running Opportunities

This module monitors the mempool (pending transactions) for large swaps
and other opportunities that create arbitrage possibilities.

⚠️ IMPORTANT ETHICAL NOTE:
This tool is for DEFENSIVE front-running (protecting your own trades)
and BACKRUNNING (executing after a large trade). Traditional sandwich
attacks can be predatory and may be illegal in some jurisdictions.

Use responsibly and ethically!
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from web3 import Web3
from eth_abi import decode
from loguru import logger
import config


@dataclass
class PendingSwap:
    """Information about a pending swap transaction"""
    tx_hash: str
    from_address: str
    to_address: str  # Router address
    token_in: str
    token_out: str
    amount_in: int
    estimated_amount_out: int
    gas_price: int
    timestamp: float
    dex: str
    opportunity_type: str  # "large_swap", "create_imbalance", "arbitrage_setup"


class MempoolMonitor:
    """
    Monitor mempool for arbitrage opportunities

    Strategies:
    1. Backrunning: Execute arbitrage AFTER a large swap completes
    2. Defensive: Protect your own trades from being front-run
    3. Opportunity Detection: Identify swaps that create price imbalances
    """

    def __init__(
        self,
        w3: Web3,
        min_swap_size_usd: float = 50000,  # Only track swaps > $50k
        opportunity_callback: Optional[Callable] = None
    ):
        """
        Initialize mempool monitor

        Args:
            w3: Web3 instance with WebSocket provider
            min_swap_size_usd: Minimum swap size to track (in USD)
            opportunity_callback: Function to call when opportunity detected
        """
        self.w3 = w3
        self.min_swap_size_usd = min_swap_size_usd
        self.opportunity_callback = opportunity_callback

        # Track pending swaps
        self.pending_swaps: Dict[str, PendingSwap] = {}
        self.processed_txs: set = set()

        # DEX router signatures
        self.swap_signatures = {
            # Uniswap V2 style
            '0x38ed1739': 'swapExactTokensForTokens',
            '0x8803dbee': 'swapTokensForExactTokens',
            '0x7ff36ab5': 'swapExactETHForTokens',
            '0x18cbafe5': 'swapExactTokensForETH',

            # Uniswap V3
            '0x414bf389': 'exactInputSingle',
            '0xc04b8d59': 'exactInput',
            '0xdb3e2198': 'exactOutputSingle',
            '0x09b81346': 'exactOutput',
        }

        # Known DEX routers
        self.dex_routers = self._get_all_dex_routers()

        logger.info(f"Mempool Monitor initialized (min swap: ${min_swap_size_usd:,.0f})")

    def _get_all_dex_routers(self) -> Dict[str, str]:
        """Get all DEX router addresses from config"""
        routers = {}

        for chain, chain_routers in config.DEX_ROUTERS.items():
            for dex_name, router_address in chain_routers.items():
                key = f"{chain}_{dex_name}"
                routers[router_address.lower()] = key

        return routers

    async def start_monitoring(self):
        """Start monitoring mempool"""
        logger.info("Starting mempool monitoring...")

        try:
            # Subscribe to pending transactions
            async def handle_pending_tx(tx_hash):
                await self.process_pending_transaction(tx_hash)

            # Create subscription filter
            pending_tx_filter = await self.w3.eth.filter('pending')

            while True:
                try:
                    # Get new pending transactions
                    for tx_hash in await pending_tx_filter.get_new_entries():
                        asyncio.create_task(self.process_pending_transaction(tx_hash))

                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error in mempool monitoring loop: {str(e)}")
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Failed to start mempool monitoring: {str(e)}")

    async def process_pending_transaction(self, tx_hash: str):
        """
        Process a pending transaction to detect opportunities

        Args:
            tx_hash: Transaction hash
        """
        try:
            # Skip if already processed
            if tx_hash in self.processed_txs:
                return

            self.processed_txs.add(tx_hash)

            # Fetch transaction details
            tx = await asyncio.to_thread(self.w3.eth.get_transaction, tx_hash)

            if not tx or not tx.get('to'):
                return

            # Check if it's a DEX transaction
            to_address = tx['to'].lower()

            if to_address not in self.dex_routers:
                return  # Not a DEX transaction

            # Parse the transaction
            swap_info = await self._parse_swap_transaction(tx, to_address)

            if not swap_info:
                return

            # Check if swap is large enough
            if not self._is_significant_swap(swap_info):
                return

            # Log the opportunity
            logger.warning(
                f"🎯 Large Swap Detected: "
                f"{swap_info.dex} "
                f"${swap_info.amount_in / 1e6:,.0f} "
                f"Gas: {swap_info.gas_price / 1e9:.1f} gwei"
            )

            # Store pending swap
            self.pending_swaps[tx_hash] = swap_info

            # Trigger callback if provided
            if self.opportunity_callback:
                await self.opportunity_callback(swap_info)

        except Exception as e:
            logger.debug(f"Error processing tx {tx_hash}: {str(e)}")

    async def _parse_swap_transaction(self, tx: Dict, router_address: str) -> Optional[PendingSwap]:
        """
        Parse swap transaction details

        Args:
            tx: Transaction dict
            router_address: DEX router address

        Returns:
            PendingSwap object or None
        """
        try:
            # Get function signature
            input_data = tx.get('input', '0x')

            if len(input_data) < 10:
                return None

            func_sig = input_data[:10]

            if func_sig not in self.swap_signatures:
                return None

            func_name = self.swap_signatures[func_sig]
            dex_name = self.dex_routers.get(router_address, 'unknown')

            # Parse based on function type
            if func_name == 'swapExactTokensForTokens':
                # Decode parameters: amountIn, amountOutMin, path, to, deadline
                params = decode(
                    ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                    bytes.fromhex(input_data[10:])
                )

                amount_in = params[0]
                amount_out_min = params[1]
                path = params[2]

                if len(path) >= 2:
                    token_in = path[0]
                    token_out = path[-1]
                else:
                    return None

            elif func_name == 'exactInputSingle':
                # Uniswap V3 single hop
                # Decode struct: tokenIn, tokenOut, fee, recipient, deadline, amountIn, amountOutMinimum, sqrtPriceLimitX96
                params = decode(
                    ['address', 'address', 'uint24', 'address', 'uint256', 'uint256', 'uint256', 'uint160'],
                    bytes.fromhex(input_data[10:])
                )

                token_in = params[0]
                token_out = params[1]
                amount_in = params[5]
                amount_out_min = params[6]

            else:
                # For other swap types, try generic parsing
                logger.debug(f"Unsupported swap function: {func_name}")
                return None

            # Create PendingSwap object
            swap = PendingSwap(
                tx_hash=tx['hash'].hex(),
                from_address=tx['from'],
                to_address=router_address,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                estimated_amount_out=amount_out_min,
                gas_price=tx.get('gasPrice', 0),
                timestamp=time.time(),
                dex=dex_name,
                opportunity_type='large_swap'
            )

            return swap

        except Exception as e:
            logger.debug(f"Error parsing swap: {str(e)}")
            return None

    def _is_significant_swap(self, swap: PendingSwap) -> bool:
        """
        Check if swap is significant enough to create arbitrage opportunity

        Args:
            swap: PendingSwap object

        Returns:
            True if swap is significant
        """
        # Estimate USD value (rough approximation)
        # This should be improved with actual price feeds

        # For now, assume stablecoin pairs
        stablecoins = ['usdc', 'usdt', 'dai', 'busd']

        # Check if token_in or token_out is a stablecoin
        token_in_lower = swap.token_in.lower()
        token_out_lower = swap.token_out.lower()

        # If involving stablecoin, use amount_in as USD value
        if any(stable in str(token_in_lower) for stable in stablecoins):
            usd_value = swap.amount_in / 1e6  # Assuming 6 decimals
        elif any(stable in str(token_out_lower) for stable in stablecoins):
            usd_value = swap.estimated_amount_out / 1e6
        else:
            # For non-stablecoin pairs, we'd need price feed
            # For now, use a heuristic based on amount
            usd_value = swap.amount_in / 1e18 * 2000  # Rough estimate

        return usd_value >= self.min_swap_size_usd

    async def watch_transaction_confirmation(self, tx_hash: str, max_wait: int = 30) -> bool:
        """
        Watch for transaction confirmation

        Args:
            tx_hash: Transaction hash to watch
            max_wait: Maximum seconds to wait

        Returns:
            True if confirmed successfully
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                receipt = await asyncio.to_thread(
                    self.w3.eth.get_transaction_receipt,
                    tx_hash
                )

                if receipt:
                    if receipt.status == 1:
                        logger.info(f"✅ Transaction confirmed: {tx_hash}")
                        return True
                    else:
                        logger.warning(f"❌ Transaction failed: {tx_hash}")
                        return False

            except Exception:
                pass

            await asyncio.sleep(0.5)

        logger.warning(f"⏰ Transaction not confirmed within {max_wait}s: {tx_hash}")
        return False

    def get_pending_opportunities(self) -> List[PendingSwap]:
        """Get list of current pending opportunities"""
        # Clean up old pending swaps (>60 seconds old)
        current_time = time.time()
        self.pending_swaps = {
            tx_hash: swap
            for tx_hash, swap in self.pending_swaps.items()
            if current_time - swap.timestamp < 60
        }

        return list(self.pending_swaps.values())

    def get_status(self) -> Dict:
        """Get mempool monitor status"""
        return {
            'pending_opportunities': len(self.pending_swaps),
            'total_transactions_processed': len(self.processed_txs),
            'monitored_routers': len(self.dex_routers),
            'min_swap_size_usd': self.min_swap_size_usd
        }


class BackrunStrategy:
    """
    Strategy for backrunning large swaps

    Backrunning is LEGAL and ETHICAL - you execute AFTER the trade
    to capture arbitrage created by price movement.
    """

    def __init__(self, arbitrage_bot, mempool_monitor: MempoolMonitor):
        """
        Initialize backrun strategy

        Args:
            arbitrage_bot: Arbitrage bot instance
            mempool_monitor: Mempool monitor instance
        """
        self.bot = arbitrage_bot
        self.monitor = mempool_monitor

    async def execute_backrun(self, swap: PendingSwap):
        """
        Execute backrun strategy

        1. Wait for large swap to confirm
        2. Check for resulting arbitrage opportunity
        3. Execute if profitable

        Args:
            swap: Pending swap to backrun
        """
        logger.info(f"🎯 Preparing backrun for swap: {swap.tx_hash}")

        # Wait for transaction to confirm
        confirmed = await self.monitor.watch_transaction_confirmation(swap.tx_hash)

        if not confirmed:
            logger.warning(f"Swap failed or not confirmed: {swap.tx_hash}")
            return

        # Now check for arbitrage opportunity created by this swap
        logger.info(f"✅ Swap confirmed, checking for arbitrage...")

        # The large swap likely moved the price on one DEX
        # Check if there's now an arbitrage opportunity

        # Extract token pair
        token_in_symbol = self._get_token_symbol(swap.token_in)
        token_out_symbol = self._get_token_symbol(swap.token_out)

        if not token_in_symbol or not token_out_symbol:
            return

        pair = f"{token_in_symbol}/{token_out_symbol}"

        # Trigger immediate arbitrage check for this pair
        logger.info(f"🔍 Checking arbitrage for {pair} after large swap")

        # This would trigger your existing arbitrage logic
        # focusing on this specific pair

    def _get_token_symbol(self, token_address: str) -> Optional[str]:
        """Get token symbol from address"""
        # Map addresses back to symbols
        for chain, tokens in config.TOKENS_BY_CHAIN.items():
            for symbol, address in tokens.items():
                if address.lower() == token_address.lower():
                    return symbol
        return None


# Example usage
async def example_usage():
    """Example of how to use MempoolMonitor"""

    # Initialize Web3 with WebSocket provider
    w3 = Web3(Web3.WebsocketProvider(config.POLYGON_WSS_URL))

    # Create callback for opportunities
    async def handle_opportunity(swap: PendingSwap):
        logger.warning(
            f"\n🚨 OPPORTUNITY DETECTED 🚨\n"
            f"  DEX: {swap.dex}\n"
            f"  Amount: ${swap.amount_in / 1e6:,.0f}\n"
            f"  Gas Price: {swap.gas_price / 1e9:.1f} gwei\n"
            f"  TX: {swap.tx_hash}\n"
        )

    # Create monitor
    monitor = MempoolMonitor(
        w3=w3,
        min_swap_size_usd=50000,
        opportunity_callback=handle_opportunity
    )

    # Start monitoring
    await monitor.start_monitoring()


if __name__ == "__main__":
    logger.info("Starting Mempool Monitor example...")
    asyncio.run(example_usage())
