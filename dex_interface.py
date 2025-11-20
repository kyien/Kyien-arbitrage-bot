from web3 import Web3
from decouple import config
# import json
import aiohttp
import asyncio
from loguru import logger

class DexInterface:
    def __init__(self, web3_provider):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.ws_provider = config.POLYGON_WSS_URL
        self.tokens = config.TOKENS
        self.routers = {
            'quickswap': config.QUICKSWAP_ROUTER,
            'sushiswap': config.SUSHISWAP_ROUTER,
            'uniswap_v3': config.UNISWAP_V3_ROUTER
        }
        
    async def get_token_price(self, dex_name, token_address, base_token_address, amount_in=None):
        """Get actual token price from DEX router"""
        try:
            if amount_in is None:
                amount_in = Web3.to_wei(1, 'ether')

            router_address = self.routers[dex_name]
            router_contract = self.w3.eth.contract(
                address=router_address,
                abi=config.ROUTER_ABI
            )

            path = [token_address, base_token_address]

            # Get amounts out from router using asyncio.to_thread for non-blocking calls
            amounts = await asyncio.to_thread(
                router_contract.functions.getAmountsOut(amount_in, path).call
            )

            # Return the output amount (last element)
            return amounts[-1] if amounts else None

        except Exception as e:
            logger.error(f"Error getting price from {dex_name}: {str(e)}")
            return None

    async def _get_amount_out(self, router_address, amount_in, path):
        """Get amount out for a given amount in and path"""
        try:
            router_contract = self.w3.eth.contract(
                address=router_address,
                abi=config.ROUTER_ABI
            )

            # Use asyncio.to_thread to avoid blocking
            amounts = await asyncio.to_thread(
                router_contract.functions.getAmountsOut(amount_in, path).call
            )

            return amounts[-1] if amounts else None

        except Exception as e:
            logger.error(f"Error in _get_amount_out: {str(e)}")
            return None

    async def execute_swap(self, dex_name, token_in, token_out, amount_in):
        """Execute a swap on the specified DEX"""
        try:
            router_address = self.routers[dex_name]
            # Implementation will vary based on DEX
            # This is a simplified example
            # Fix warning: "async def" function is never awaited
            await asyncio.sleep(0)

            tx = await self._swap_exact_tokens_for_tokens(
                router_address,
                amount_in,
                0,  # min amount out (needs to be calculated with slippage)
                [self.tokens[token_in], self.tokens[token_out]],
                config.GAS_LIMIT
            )
            return tx
        except Exception as e:
            logger.error(f"Error executing swap on {dex_name}: {str(e)}")
            return None

    async def _swap_exact_tokens_for_tokens(self, router_address, amount_in, amount_out_min, path, gas_limit):
        """
        Execute a token swap with exact input amount
        
        Args:
            router_address (str): Address of the DEX router contract
            amount_in (int): Exact amount of input tokens
            amount_out_min (int): Minimum amount of output tokens to receive
            path (list): List of token addresses representing the swap path
            gas_limit (int): Gas limit for the transaction
            
        Returns:
            dict: Transaction receipt
        """
        try:
            # Create contract instance
            router_abi = config.ROUTER_ABI  # Make sure this is defined in your config
            router_contract = self.w3.eth.contract(
                address=router_address,
                abi=router_abi
            )
            
            # Get deadline (usually current time + some minutes)
            deadline = self.w3.eth.get_block('latest')['timestamp'] + 300  # 5 minutes
            
            # Build the swap transaction
            swap_txn = router_contract.functions.swapExactTokensForTokens(
                amount_in,
                amount_out_min,
                path,
                config.WALLET_ADDRESS,  # Make sure this is defined in your config
                deadline
            ).build_transaction({
                'from': config.WALLET_ADDRESS,
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET_ADDRESS),
            })
            
            # Sign and send the transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                swap_txn,
                config.PRIVATE_KEY  # Make sure this is defined in your config
            )
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_receipt
            
        except Exception as e:
            logger.error(f"Error in _swap_exact_tokens_for_tokens: {str(e)}")
            raise

    async def monitor_dex_prices(self):
        """Monitor DEX prices using websocket"""
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.ws_provider) as ws:
                # Subscribe to relevant events
                # Implementation will vary based on DEX
                while True:
                    try:
                        msg = await ws.receive_json()
                        # Process price updates
                        await self._handle_price_update(msg)
                    except Exception as e:
                        logger.error(f"Error in DEX price monitoring: {str(e)}")
                        await asyncio.sleep(1)

    async def _handle_price_update(self, msg):
        """Handle incoming price updates"""
        # Implementation will vary based on DEX
        pass

    def calculate_price_impact(self, amount_in, reserve_in, reserve_out):
        """Calculate price impact of a trade"""
        amount_with_fee = amount_in * 997  # 0.3% fee
        numerator = amount_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_with_fee
        amount_out = numerator / denominator
        
        # Calculate price impact
        price_impact = (amount_out / reserve_out) * 100
        return price_impact

    async def check_liquidity(self, dex_name, token_pair):
        """Check actual liquidity from pair contract"""
        try:
            token_in, token_out = token_pair.split('/')
            token_in_addr = config.TOKENS.get(token_in)
            token_out_addr = config.TOKENS.get(token_out)

            if not token_in_addr or not token_out_addr:
                logger.warning(f"Token addresses not found for {token_pair}")
                return 0

            # Get pair address
            factory_address = self._get_factory_address(dex_name)
            if not factory_address:
                return 0

            factory_abi = [
                {
                    "constant": True,
                    "inputs": [
                        {"name": "tokenA", "type": "address"},
                        {"name": "tokenB", "type": "address"}
                    ],
                    "name": "getPair",
                    "outputs": [{"name": "pair", "type": "address"}],
                    "type": "function"
                }
            ]

            factory = self.w3.eth.contract(address=factory_address, abi=factory_abi)
            pair_address = await asyncio.to_thread(
                factory.functions.getPair(token_in_addr, token_out_addr).call
            )

            if pair_address == '0x0000000000000000000000000000000000000000':
                logger.debug(f"No pair found for {token_pair} on {dex_name}")
                return 0

            # Get reserves from pair
            pair_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "reserve0", "type": "uint112"},
                        {"name": "reserve1", "type": "uint112"},
                        {"name": "blockTimestampLast", "type": "uint32"}
                    ],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "type": "function"
                }
            ]

            pair_contract = self.w3.eth.contract(address=pair_address, abi=pair_abi)
            reserves = await asyncio.to_thread(pair_contract.functions.getReserves().call)

            # Calculate liquidity in USD (simplified - assumes USDC/USDT as one of the tokens)
            reserve0, reserve1, _ = reserves

            # Get token0 and token1 to determine which reserve is which
            token0 = await asyncio.to_thread(pair_contract.functions.token0().call)

            # Determine which reserve corresponds to the stablecoin
            if token0.lower() == token_in_addr.lower():
                # Check if token_out is a stablecoin
                if token_out in ['USDC', 'USDT']:
                    liquidity_usd = reserve1 / 1e6  # Assuming 6 decimals for stablecoins
                else:
                    liquidity_usd = reserve0 / 1e18  # Assuming 18 decimals
            else:
                if token_in in ['USDC', 'USDT']:
                    liquidity_usd = reserve0 / 1e6
                else:
                    liquidity_usd = reserve1 / 1e18

            return liquidity_usd * 2  # Total liquidity is both reserves

        except Exception as e:
            logger.error(f"Error checking liquidity on {dex_name}: {str(e)}")
            return 0

    def _get_factory_address(self, dex_name):
        """Get factory address for DEX"""
        factories = {
            'quickswap': '0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32',
            'sushiswap': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4',
            'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984'
        }
        return factories.get(dex_name)

    async def get_volume(self, dex_name, token_pair):
        """Get 24h trading volume (simplified implementation)"""
        try:
            # For production: integrate with TheGraph API or on-chain events
            # For now, estimate based on liquidity
            liquidity = await self.check_liquidity(dex_name, token_pair)
            # Rough estimate: daily volume is typically 0.5-2x liquidity
            estimated_volume = liquidity * 1.0
            return estimated_volume
        except Exception as e:
            logger.error(f"Error getting volume from {dex_name}: {str(e)}")
            return 100000  # Default fallback

    async def get_pair_address(self, dex_name, token_in_address, token_out_address):
        """Get pair address for two tokens on a DEX"""
        try:
            factory_address = self._get_factory_address(dex_name)
            if not factory_address:
                return None

            factory_abi = [
                {
                    "constant": True,
                    "inputs": [
                        {"name": "tokenA", "type": "address"},
                        {"name": "tokenB", "type": "address"}
                    ],
                    "name": "getPair",
                    "outputs": [{"name": "pair", "type": "address"}],
                    "type": "function"
                }
            ]

            factory = self.w3.eth.contract(address=factory_address, abi=factory_abi)
            pair_address = await asyncio.to_thread(
                factory.functions.getPair(token_in_address, token_out_address).call
            )

            if pair_address == '0x0000000000000000000000000000000000000000':
                return None

            return pair_address

        except Exception as e:
            logger.error(f"Error getting pair address: {str(e)}")
            return None
