"""
Multicall Helper for Batching Contract Calls

This module provides a helper for batching multiple contract calls
into a single RPC request using Multicall3, which significantly
reduces latency and improves performance.
"""

from web3 import Web3
import asyncio
from typing import List, Dict, Any
from loguru import logger


class MulticallHelper:
    """Helper for batching multiple contract calls into one RPC request"""

    # Multicall3 is deployed at the same address on all major chains
    MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"

    MULTICALL3_ABI = [
        {
            "inputs": [
                {
                    "components": [
                        {"name": "target", "type": "address"},
                        {"name": "allowFailure", "type": "bool"},
                        {"name": "callData", "type": "bytes"}
                    ],
                    "name": "calls",
                    "type": "tuple[]"
                }
            ],
            "name": "aggregate3",
            "outputs": [
                {
                    "components": [
                        {"name": "success", "type": "bool"},
                        {"name": "returnData", "type": "bytes"}
                    ],
                    "name": "returnData",
                    "type": "tuple[]"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]

    def __init__(self, w3: Web3):
        """
        Initialize Multicall helper

        Args:
            w3: Web3 instance
        """
        self.w3 = w3
        self.multicall = w3.eth.contract(
            address=self.MULTICALL3_ADDRESS,
            abi=self.MULTICALL3_ABI
        )

    async def aggregate_calls(self, calls: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple contract calls in a single RPC request

        Args:
            calls: List of dicts with keys:
                - contract: Web3 contract instance
                - function: Function name
                - args: Function arguments (optional)
                - metadata: Additional metadata for tracking (optional)

        Returns:
            List of decoded results (None for failed calls)

        Example:
            calls = [
                {
                    'contract': router_contract,
                    'function': 'getAmountsOut',
                    'args': [amount_in, [token_a, token_b]],
                    'metadata': {'dex': 'quickswap', 'pair': 'WETH/USDC'}
                },
                {
                    'contract': pair_contract,
                    'function': 'getReserves',
                    'args': [],
                    'metadata': {'pair': 'WETH/USDC'}
                }
            ]
            results = await multicall.aggregate_calls(calls)
        """
        try:
            if not calls:
                return []

            # Build multicall calls
            multicall_calls = []

            for call in calls:
                contract = call['contract']
                function_name = call['function']
                args = call.get('args', [])

                # Encode the function call
                function = contract.get_function_by_name(function_name)
                call_data = function(*args)._encode_transaction_data()

                multicall_calls.append({
                    'target': contract.address,
                    'allowFailure': True,
                    'callData': call_data
                })

            # Execute multicall using asyncio.to_thread
            results = await asyncio.to_thread(
                self.multicall.functions.aggregate3(multicall_calls).call
            )

            # Decode results
            decoded_results = []
            for i, (call, result) in enumerate(zip(calls, results)):
                if result['success']:
                    try:
                        contract = call['contract']
                        function_name = call['function']
                        function = contract.get_function_by_name(function_name)

                        # Decode the return data
                        decoded = function().decode_function_result(result['returnData'])
                        decoded_results.append(decoded[0] if len(decoded) == 1 else decoded)
                    except Exception as decode_error:
                        logger.debug(f"Error decoding result {i}: {str(decode_error)}")
                        decoded_results.append(None)
                else:
                    decoded_results.append(None)

            return decoded_results

        except Exception as e:
            logger.error(f"Error in multicall: {str(e)}")
            return [None] * len(calls)

    async def get_all_dex_prices(self, dex_routers: Dict[str, Any], token_pairs: List[tuple],
                                 amount_in: int = None) -> Dict[str, Dict[tuple, int]]:
        """
        Get prices for multiple token pairs across multiple DEXes in a single call

        Args:
            dex_routers: Dict of {dex_name: router_contract}
            token_pairs: List of (token_in, token_out) tuples
            amount_in: Amount to query (default: 1 ether)

        Returns:
            Dict of {dex_name: {(token_in, token_out): output_amount}}

        Example:
            routers = {
                'quickswap': quickswap_router_contract,
                'sushiswap': sushiswap_router_contract
            }
            pairs = [
                (WETH_ADDRESS, USDC_ADDRESS),
                (WMATIC_ADDRESS, USDC_ADDRESS)
            ]
            prices = await multicall.get_all_dex_prices(routers, pairs)
            # Returns: {
            #     'quickswap': {
            #         (WETH, USDC): 2000000000,
            #         (WMATIC, USDC): 800000
            #     },
            #     'sushiswap': {...}
            # }
        """
        if amount_in is None:
            amount_in = Web3.to_wei(1, 'ether')

        calls = []
        metadata_list = []

        # Build calls for all DEX/pair combinations
        for dex_name, router_contract in dex_routers.items():
            for token_in, token_out in token_pairs:
                calls.append({
                    'contract': router_contract,
                    'function': 'getAmountsOut',
                    'args': [amount_in, [token_in, token_out]]
                })
                metadata_list.append({
                    'dex': dex_name,
                    'pair': (token_in, token_out)
                })

        # Execute all calls
        results = await self.aggregate_calls(calls)

        # Parse results into structured dict
        prices = {}
        for metadata, result in zip(metadata_list, results):
            dex = metadata['dex']
            pair = metadata['pair']

            if dex not in prices:
                prices[dex] = {}

            if result and len(result) > 0:
                # getAmountsOut returns an array, we want the last element
                prices[dex][pair] = result[-1]
            else:
                prices[dex][pair] = None

        return prices

    async def get_all_reserves(self, pair_contracts: List[Any],
                              metadata: List[Dict] = None) -> List[Dict]:
        """
        Get reserves for multiple pairs in a single call

        Args:
            pair_contracts: List of pair contract instances
            metadata: Optional metadata for each pair

        Returns:
            List of dicts with reserve data

        Example:
            pairs = [pair_contract1, pair_contract2, pair_contract3]
            reserves = await multicall.get_all_reserves(pairs)
            # Returns: [
            #     {'reserve0': 1000000, 'reserve1': 2000000, 'timestamp': 1234567890},
            #     {'reserve0': 5000000, 'reserve1': 3000000, 'timestamp': 1234567891},
            #     ...
            # ]
        """
        calls = [
            {
                'contract': pair_contract,
                'function': 'getReserves',
                'args': []
            }
            for pair_contract in pair_contracts
        ]

        results = await self.aggregate_calls(calls)

        # Parse results
        reserves_list = []
        for i, result in enumerate(results):
            if result and len(result) >= 3:
                reserves_list.append({
                    'reserve0': result[0],
                    'reserve1': result[1],
                    'timestamp': result[2],
                    'metadata': metadata[i] if metadata and i < len(metadata) else None
                })
            else:
                reserves_list.append(None)

        return reserves_list


# Example usage
async def example_usage():
    """Example of how to use MulticallHelper"""
    from web3 import Web3
    import config

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(config.POLYGON_RPC_URL))

    # Create multicall helper
    multicall = MulticallHelper(w3)

    # Setup router contracts
    routers = {
        'quickswap': w3.eth.contract(
            address=config.QUICKSWAP_ROUTER,
            abi=config.ROUTER_ABI
        ),
        'sushiswap': w3.eth.contract(
            address=config.SUSHISWAP_ROUTER,
            abi=config.ROUTER_ABI
        )
    }

    # Define token pairs to query
    pairs = [
        (config.TOKENS['WETH'], config.TOKENS['USDC']),
        (config.TOKENS['WMATIC'], config.TOKENS['USDC']),
        (config.TOKENS['WBTC'], config.TOKENS['USDC'])
    ]

    # Get all prices in a single call (instead of 6 separate calls)
    prices = await multicall.get_all_dex_prices(routers, pairs)

    logger.info(f"Retrieved prices for {len(pairs)} pairs across {len(routers)} DEXes")
    logger.info(f"Prices: {prices}")

    return prices


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
