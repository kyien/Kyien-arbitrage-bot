import asyncio
import ccxt.async_support as ccxt
from web3 import Web3
from loguru import logger
import config
import time
from decimal import Decimal
import websockets
import json
import numpy as np
from dex_interface import DexInterface
from flashloan import FlashloanExecutor
from contract_interface import ContractInterface
from cross_chain import CrossChainManager
from advanced_strategies import AdvancedStrategyManager
from monitoring import MonitoringSystem

class ArbitrageBot:
    def __init__(self):
        # Initialize CEX exchanges
        self.binance = ccxt.binance({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_SECRET_KEY,
            'enableRateLimit': True
        })
        
        self.okx = ccxt.okx({
            'apiKey': config.OKX_API_KEY,
            'secret': config.OKX_SECRET_KEY,
            'enableRateLimit': True
        })
        
        # Initialize Web3 and DEX interfaces
        self.w3 = Web3(Web3.HTTPProvider(config.POLYGON_RPC_URL))
        self.dex = DexInterface(config.POLYGON_RPC_URL)
        self.flashloan = FlashloanExecutor(config.POLYGON_RPC_URL)
        
        # Initialize new components
        self.contract_interface = ContractInterface()
        self.cross_chain = CrossChainManager()
        self.strategy = AdvancedStrategyManager()
        self.monitoring = MonitoringSystem()
        
        # Price storage
        self.prices = {
            'binance': {},
            'okx': {},
            'quickswap': {},
            'sushiswap': {},
            'uniswap_v3': {}
        }
        
        # Moving averages for price analysis
        self.price_history = {}
        self.running = False
        logger.info("Arbitrage bot initialized")

    async def connect_binance_websocket(self):
        """Connect to Binance websocket for real-time price updates"""
        async with websockets.connect(config.BINANCE_WSS_URL) as ws:
            # Subscribe to ticker streams for all pairs
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": [f"{pair.lower()}@ticker" for pair in config.TRADING_PAIRS['CEX']],
                "id": 1
            }
            await ws.send(json.dumps(subscribe_message))
            
            while self.running:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    if 'data' in data:
                        await self._handle_binance_price_update(data['data'])
                except Exception as e:
                    logger.error(f"Binance websocket error: {str(e)}")
                    await asyncio.sleep(1)

    async def connect_okx_websocket(self):
        """Connect to OKX websocket for real-time price updates"""
        async with websockets.connect(config.OKX_WSS_URL) as ws:
            # Subscribe to ticker streams
            subscribe_message = {
                "op": "subscribe",
                "args": [{"channel": "tickers", "instId": pair} for pair in config.TRADING_PAIRS['CEX']]
            }
            await ws.send(json.dumps(subscribe_message))
            
            while self.running:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    if 'data' in data:
                        await self._handle_okx_price_update(data['data'])
                except Exception as e:
                    logger.error(f"OKX websocket error: {str(e)}")
                    await asyncio.sleep(1)

    async def _handle_binance_price_update(self, data):
        """Handle Binance price updates"""
        symbol = data['s']
        self.prices['binance'][symbol] = {
            'bid': float(data['b']),
            'ask': float(data['a'])
        }
        await self._update_price_history('binance', symbol)

    async def _handle_okx_price_update(self, data):
        """Handle OKX price updates"""
        symbol = data['instId']
        self.prices['okx'][symbol] = {
            'bid': float(data['bidPx']),
            'ask': float(data['askPx'])
        }
        await self._update_price_history('okx', symbol)

    async def _update_price_history(self, exchange, symbol):
        """Update price history for moving averages"""
        key = f"{exchange}_{symbol}"
        if key not in self.price_history:
            self.price_history[key] = []
        
        price = (self.prices[exchange][symbol]['bid'] + self.prices[exchange][symbol]['ask']) / 2
        self.price_history[key].append(price)
        
        # Keep only recent prices for MA calculation
        max_period = max(config.MOVING_AVERAGE_PERIODS)
        if len(self.price_history[key]) > max_period:
            self.price_history[key].pop(0)

    def calculate_moving_averages(self, exchange, symbol):
        """Calculate moving averages for price analysis"""
        key = f"{exchange}_{symbol}"
        if key not in self.price_history:
            return {}
        
        mas = {}
        prices = np.array(self.price_history[key])
        for period in config.MOVING_AVERAGE_PERIODS:
            if len(prices) >= period:
                mas[period] = np.mean(prices[-period:])
        return mas

    async def check_dex_arbitrage(self):
        """Check for arbitrage opportunities between DEXes using parallel queries"""
        while self.running:
            try:
                for pair in config.TRADING_PAIRS['DEX']:
                    token_in, token_out = pair.split('/')

                    # Get prices from all DEXes in parallel
                    dex_names = ['quickswap', 'sushiswap', 'uniswap_v3']

                    # Create all tasks at once for parallel execution
                    price_tasks = [
                        self.dex.get_token_price(
                            dex,
                            config.TOKENS[token_in],
                            config.TOKENS[token_out]
                        ) for dex in dex_names
                    ]

                    volume_tasks = [
                        self.dex.get_volume(dex, pair) for dex in dex_names
                    ]

                    liquidity_tasks = [
                        self.dex.check_liquidity(dex, pair) for dex in dex_names
                    ]

                    # Execute all queries in parallel using asyncio.gather
                    results = await asyncio.gather(
                        *price_tasks,
                        *volume_tasks,
                        *liquidity_tasks,
                        return_exceptions=True
                    )

                    # Parse results
                    num_dexs = len(dex_names)
                    prices = dict(zip(dex_names, results[:num_dexs]))
                    volumes = dict(zip(dex_names, results[num_dexs:num_dexs*2]))
                    liquidity = dict(zip(dex_names, results[num_dexs*2:]))

                    # Filter out None values and exceptions (failed queries)
                    prices = {k: v for k, v in prices.items() if v is not None and not isinstance(v, Exception)}
                    volumes = {k: v for k, v in volumes.items() if v is not None and not isinstance(v, Exception)}
                    liquidity = {k: v for k, v in liquidity.items() if v is not None and not isinstance(v, Exception)}

                    # Process arbitrage opportunities
                    await self._process_arbitrage_opportunities(
                        pair, token_in, token_out, prices, volumes, liquidity
                    )

                # CRITICAL: Reduce sleep time dramatically for faster opportunity detection
                await asyncio.sleep(0.01)  # 10ms instead of 100ms = 10x faster

            except Exception as e:
                logger.error(f"Error in DEX arbitrage check: {str(e)}")
                await self.monitoring.log_error({
                    "source": "dex_arbitrage",
                    "error": str(e)
                })
                await asyncio.sleep(1)

    async def _process_arbitrage_opportunities(self, pair, token_in, token_out, prices, volumes, liquidity):
        """Process arbitrage opportunities for a given pair"""
        # Find best opportunities
        for dex1 in prices:
            for dex2 in prices:
                if dex1 != dex2:
                    # Calculate profit percentage
                    profit_pct = (prices[dex2] - prices[dex1]) / prices[dex1] * 100

                    if profit_pct > config.MIN_PROFIT_THRESHOLD:
                        # Check if liquidity is sufficient
                        if liquidity.get(dex1, 0) < config.MIN_LIQUIDITY_THRESHOLD:
                            logger.debug(f"Insufficient liquidity on {dex1} for {pair}")
                            continue

                        # Analyze market conditions
                        market_condition = self.strategy.analyze_market_conditions(
                            pair,
                            list(prices.values()),
                            list(volumes.values()),
                            list(liquidity.values())
                        )

                        if not market_condition:
                            logger.debug(f"Could not analyze market conditions for {pair}")
                            continue

                        # Determine if we should execute the trade
                        should_execute, reason = self.strategy.should_execute_trade(
                            market_condition,
                            profit_pct
                        )

                        if should_execute:
                            # Calculate optimal position size
                            optimal_amount = self.strategy.calculate_optimal_position_size(
                                market_condition,
                                config.MAX_POSITION_SIZE
                            )

                            # Simulate trade first to verify profitability
                            is_profitable = await self._simulate_and_verify_trade(
                                'polygon',
                                dex1,
                                dex2,
                                token_in,
                                token_out,
                                optimal_amount,
                                prices,
                                profit_pct
                            )

                            if is_profitable:
                                # Execute arbitrage using flashswap with retry logic
                                await self.execute_dex_flashswap_with_retry(
                                    'polygon',
                                    dex1,
                                    dex2,
                                    token_in,
                                    token_out,
                                    optimal_amount,
                                    prices
                                )
                            else:
                                logger.debug(f"Trade not profitable after gas costs for {pair}")
                        else:
                            logger.debug(f"Skipping {pair} opportunity: {reason}")

    async def execute_dex_flashswap(self, chain, dex1, dex2, token_in, token_out, amount, prices):
        """Execute arbitrage between DEXes using flashswap"""
        try:
            # Get token addresses
            token_in_address = config.TOKENS[token_in]
            token_out_address = config.TOKENS[token_out]
            
            # Get the pair address for the flashswap (depends on DEX implementation)
            pair_address = await self.dex.get_pair_address(dex1, token_in_address, token_out_address)
            
            if not pair_address:
                logger.error(f"Could not find pair address for {token_in}/{token_out} on {dex1}")
                return
            
            # Execute flashswap using smart contract
            tx_hash = await self.contract_interface.execute_flashswap(
                chain,
                pair_address,
                token_in_address,
                amount,
                dex2,  # Target DEX for the arbitrage
                token_in_address,
                token_out_address
            )
            
            if tx_hash:
                logger.info(f"Successfully executed DEX flashswap arbitrage: {tx_hash}")
                
                # Log the trade for monitoring
                await self.monitoring.log_trade({
                    "type": "dex_flashswap",
                    "chain": chain,
                    "token_in": token_in,
                    "token_out": token_out,
                    "source_dex": dex1,
                    "target_dex": dex2,
                    "amount": amount,
                    "profit": (prices[dex2] - prices[dex1]) * amount,
                    "tx_hash": tx_hash
                })
                
                # Send alert for successful trade
                await self.monitoring.send_alert(
                    f"DEX Flashswap: {token_in} -> {token_out} from {dex1} to {dex2}. Profit: {(prices[dex2] - prices[dex1]) * amount}",
                    "info"
                )
            
        except Exception as e:
            logger.error(f"Error executing DEX flashswap: {str(e)}")
            await self.monitoring.log_error({
                "source": "dex_flashswap",
                "error": str(e)
            })

    async def check_cross_chain_opportunities(self):
        """Check for cross-chain arbitrage opportunities"""
        while self.running:
            try:
                for token in ["WETH", "USDC", "WBTC"]:
                    # Find cross-chain opportunities
                    opportunities = await self.cross_chain.check_cross_chain_opportunities(token)
                    
                    for opportunity in opportunities:
                        # Analyze market conditions for the chains involved
                        market_conditions = await self._analyze_cross_chain_market(
                            opportunity['source_chain'],
                            opportunity['target_chain'],
                            token
                        )
                        
                        # Determine if we should execute the cross-chain arbitrage
                        should_execute, reason = self.strategy.should_execute_trade(
                            market_conditions,
                            opportunity['profit']
                        )
                        
                        if should_execute:
                            # Execute the cross-chain arbitrage
                            success = await self.cross_chain.execute_cross_chain_arbitrage(opportunity)
                            
                            if success:
                                logger.info(f"Successfully executed cross-chain arbitrage: {opportunity}")
                                
                                # Log the trade for monitoring
                                await self.monitoring.log_trade({
                                    "type": "cross_chain",
                                    "source_chain": opportunity['source_chain'],
                                    "target_chain": opportunity['target_chain'],
                                    "token": token,
                                    "bridge": opportunity['bridge'],
                                    "profit": opportunity['profit'],
                                    "path": opportunity['path']
                                })
                                
                                # Send alert for successful trade
                                await self.monitoring.send_alert(
                                    f"Cross-Chain: {token} from {opportunity['source_chain']} to {opportunity['target_chain']}. Profit: {opportunity['profit']}",
                                    "info"
                                )
                        else:
                            logger.info(f"Skipping cross-chain opportunity due to market conditions: {reason}")
                
                await asyncio.sleep(5)  # Longer delay for cross-chain checks
            except Exception as e:
                logger.error(f"Error in cross-chain arbitrage check: {str(e)}")
                await self.monitoring.log_error({
                    "source": "cross_chain_arbitrage",
                    "error": str(e)
                })
                await asyncio.sleep(5)

    async def _analyze_cross_chain_market(self, source_chain, target_chain, token):
        """Analyze market conditions for cross-chain arbitrage"""
        # This would be a simplified version of the advanced strategy analysis
        # Actual implementation would need to gather data from both chains
        pass

    async def check_cex_arbitrage(self):
        """Check for arbitrage opportunities between centralized exchanges"""
        while self.running:
            try:
                for pair in config.TRADING_PAIRS['CEX']:
                    if pair in self.prices['binance'] and pair in self.prices['okx']:
                        # Calculate potential profits
                        profit1 = (self.prices['okx'][pair]['bid'] - self.prices['binance'][pair]['ask']) / self.prices['binance'][pair]['ask'] * 100
                        profit2 = (self.prices['binance'][pair]['bid'] - self.prices['okx'][pair]['ask']) / self.prices['okx'][pair]['ask'] * 100
                        
                        # Check moving averages for trend confirmation
                        binance_mas = self.calculate_moving_averages('binance', pair)
                        okx_mas = self.calculate_moving_averages('okx', pair)
                        
                        # Use advanced strategy for CEX trades as well
                        market_condition = await self._analyze_cex_market_condition(pair)
                        
                        if profit1 > config.MIN_PROFIT_THRESHOLD:
                            should_execute, reason = self.strategy.should_execute_trade(
                                market_condition,
                                profit1
                            )
                            
                            if should_execute and self._confirm_trend(binance_mas, okx_mas):
                                # Calculate optimal position size
                                optimal_amount = self.strategy.calculate_optimal_position_size(
                                    market_condition,
                                    config.MAX_POSITION_SIZE
                                )
                                
                                await self.execute_cex_arbitrage(pair, "binance", "okx", 
                                                          self.prices['binance'][pair]['ask'],
                                                          self.prices['okx'][pair]['bid'],
                                                          optimal_amount)
                        
                        elif profit2 > config.MIN_PROFIT_THRESHOLD:
                            should_execute, reason = self.strategy.should_execute_trade(
                                market_condition,
                                profit2
                            )
                            
                            if should_execute and self._confirm_trend(okx_mas, binance_mas):
                                # Calculate optimal position size
                                optimal_amount = self.strategy.calculate_optimal_position_size(
                                    market_condition,
                                    config.MAX_POSITION_SIZE
                                )
                                
                                await self.execute_cex_arbitrage(pair, "okx", "binance",
                                                          self.prices['okx'][pair]['ask'],
                                                          self.prices['binance'][pair]['bid'],
                                                          optimal_amount)
                
                await asyncio.sleep(0.1)  # Small delay to prevent CPU overload
            except Exception as e:
                logger.error(f"Error in CEX arbitrage check: {str(e)}")
                await self.monitoring.log_error({
                    "source": "cex_arbitrage",
                    "error": str(e)
                })
                await asyncio.sleep(1)

    async def _analyze_cex_market_condition(self, pair):
        """Analyze market conditions for CEX arbitrage"""
        # Gather data for the strategy analysis
        # This is a placeholder for actual implementation
        pass

    def _confirm_trend(self, mas_1, mas_2):
        """Confirm trend using moving averages"""
        if not mas_1 or not mas_2:
            return False
            
        # Check if short-term MA is above longer-term MAs
        return all(mas_1[shorter] >= mas_1[longer] for shorter, longer in zip(config.MOVING_AVERAGE_PERIODS[:-1], config.MOVING_AVERAGE_PERIODS[1:]))

    async def execute_cex_arbitrage(self, symbol, buy_exchange, sell_exchange, buy_price, sell_price, amount=None):
        """Execute the arbitrage trade between centralized exchanges"""
        try:
            # Calculate trade amount if not provided
            if amount is None:
                amount = min(
                    config.MAX_TRADE_AMOUNT / buy_price,
                    config.MAX_TRADE_AMOUNT / sell_price
                )
            
            # Execute trades
            buy_exchange_instance = getattr(self, buy_exchange)
            sell_exchange_instance = getattr(self, sell_exchange)
            
            # Place market buy order
            buy_order = await buy_exchange_instance.create_market_buy_order(symbol, amount)
            logger.info(f"Buy order executed on {buy_exchange}: {buy_order}")
            
            # Place market sell order
            sell_order = await sell_exchange_instance.create_market_sell_order(symbol, amount)
            logger.info(f"Sell order executed on {sell_exchange}: {sell_order}")
            
            # Calculate actual profit
            actual_profit = (sell_order['price'] - buy_order['price']) * amount
            
            # Log the trade for monitoring
            await self.monitoring.log_trade({
                "type": "cex_arbitrage",
                "symbol": symbol,
                "buy_exchange": buy_exchange,
                "sell_exchange": sell_exchange,
                "amount": amount,
                "buy_price": buy_order['price'],
                "sell_price": sell_order['price'],
                "profit": actual_profit
            })
            
            # Send alert for successful trade
            await self.monitoring.send_alert(
                f"CEX Arbitrage: {symbol} from {buy_exchange} to {sell_exchange}. Profit: {actual_profit}",
                "info"
            )
            
        except Exception as e:
            logger.error(f"Error executing CEX arbitrage: {str(e)}")
            await self.monitoring.log_error({
                "source": "cex_arbitrage",
                "error": str(e)
            })

    async def withdraw_profits(self):
        """Periodically withdraw profits from contracts"""
        while self.running:
            try:
                # Loop through chains and tokens to withdraw profits
                for chain in ['polygon', 'arbitrum', 'optimism', 'bsc']:
                    for token in config.TOKENS.values():
                        await self.contract_interface.withdraw_profits(chain, token)
                
                # Wait for next withdrawal cycle (once a day)
                await asyncio.sleep(86400)  # 24 hours
            except Exception as e:
                logger.error(f"Error withdrawing profits: {str(e)}")
                await asyncio.sleep(3600)  # Retry after an hour

    async def monitor_markets(self):
        """Main monitoring loop"""
        self.running = True
        try:
            # Start websocket connections
            ws_tasks = [
                self.connect_binance_websocket(),
                self.connect_okx_websocket(),
                self.dex.monitor_dex_prices()
            ]
            
            # Start market monitoring
            monitor_tasks = [
                self.check_cex_arbitrage(),
                self.check_dex_arbitrage(),
                self.check_cross_chain_opportunities(),
                self.withdraw_profits(),
                self.monitoring.start_monitoring()
            ]
            
            # Combine all tasks
            tasks = ws_tasks + monitor_tasks
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in market monitoring: {str(e)}")
            await asyncio.sleep(5)

    async def _simulate_and_verify_trade(self, chain, dex1, dex2, token_in, token_out,
                                         amount, prices, profit_pct) -> bool:
        """Simulate trade execution and verify profitability after gas costs"""
        try:
            w3 = self.w3

            # Get token addresses
            token_in_address = config.TOKENS[token_in]
            token_out_address = config.TOKENS[token_out]

            # Get pair address for flashswap
            pair_address = await self.dex.get_pair_address(
                dex1, token_in_address, token_out_address
            )

            if not pair_address:
                logger.debug(f"No pair found for {token_in}/{token_out} on {dex1}")
                return False

            # Get the arbitrage contract
            contract = self.contract_interface.contracts.get(chain, {}).get('arbitrage_executor')
            if not contract:
                logger.error("Arbitrage contract not deployed")
                return False

            # Encode callback data
            target_router = self.dex.routers[dex2]
            callback_data = w3.codec.encode_abi(
                ['address', 'address', 'address'],
                [target_router, token_in_address, token_out_address]
            )

            # Simulate the transaction using eth_call
            try:
                amount_wei = Web3.to_wei(amount, 'ether')

                # Try to call the function to see if it would succeed
                await asyncio.to_thread(
                    contract.functions.executeFlashSwap(
                        pair_address,
                        token_in_address,
                        amount_wei,
                        callback_data
                    ).call,
                    {'from': config.WALLET_ADDRESS}
                )

                logger.info(f"✓ Trade simulation successful for {token_in}/{token_out}")

            except Exception as sim_error:
                logger.warning(f"✗ Trade simulation failed for {token_in}/{token_out}: {str(sim_error)}")
                return False

            # Estimate gas cost
            try:
                gas_estimate = await asyncio.to_thread(
                    contract.functions.executeFlashSwap(
                        pair_address,
                        token_in_address,
                        amount_wei,
                        callback_data
                    ).estimate_gas,
                    {'from': config.WALLET_ADDRESS}
                )

                # Get gas price
                gas_price = w3.eth.gas_price
                gas_cost_wei = gas_estimate * gas_price
                gas_cost_eth = Web3.from_wei(gas_cost_wei, 'ether')

                # Estimate gas cost in USD (assuming MATIC price ~ $0.80)
                gas_cost_usd = float(gas_cost_eth) * 0.80

                # Calculate expected profit
                profit_usd = amount * (profit_pct / 100)

                # Verify profitability after gas
                net_profit = profit_usd - gas_cost_usd

                if net_profit > config.MIN_PROFIT_THRESHOLD:
                    logger.info(
                        f"✓ Trade profitable: ${net_profit:.2f} "
                        f"(Gross: ${profit_usd:.2f}, Gas: ${gas_cost_usd:.2f})"
                    )
                    return True
                else:
                    logger.debug(
                        f"✗ Trade unprofitable after gas: ${net_profit:.2f} "
                        f"(Gas: ${gas_cost_usd:.2f} exceeds profit: ${profit_usd:.2f})"
                    )
                    return False

            except Exception as gas_error:
                logger.error(f"Error estimating gas: {str(gas_error)}")
                # If we can't estimate gas, be conservative and skip
                return False

        except Exception as e:
            logger.error(f"Error simulating trade: {str(e)}")
            return False

    async def execute_dex_flashswap_with_retry(self, chain, dex1, dex2, token_in,
                                               token_out, amount, prices, max_retries=3):
        """Execute flashswap with retry logic and circuit breaker protection"""
        for attempt in range(max_retries):
            try:
                # Check circuit breaker before attempting
                from circuit_breaker import risk_manager

                if not risk_manager.check_trade_allowed(chain):
                    logger.warning(f"Trade blocked by risk manager for {chain}")
                    return None

                result = await self.execute_dex_flashswap(
                    chain, dex1, dex2, token_in, token_out, amount, prices
                )

                if result:
                    # Record success
                    profit_estimate = amount * ((prices[dex2] - prices[dex1]) / prices[dex1])
                    risk_manager.record_trade_result(chain, profit_estimate, True)

                    logger.info(f"✓ Flashswap executed successfully on attempt {attempt + 1}")
                    return result
                else:
                    # Record failure
                    risk_manager.record_trade_result(chain, 0, False)

                    if attempt < max_retries - 1:
                        # Exponential backoff
                        wait_time = (2 ** attempt) * 0.1  # 0.1s, 0.2s, 0.4s
                        logger.info(f"Retry attempt {attempt + 2} after {wait_time}s")
                        await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")

                # Record failure
                from circuit_breaker import risk_manager
                risk_manager.record_trade_result(chain, 0, False)

                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1
                    logger.info(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)

        logger.error(f"All {max_retries} retry attempts failed for {chain}")
        return None

    async def start(self):
        """Start the arbitrage bot"""
        logger.info("Starting arbitrage bot...")
        await self.monitor_markets()

    def stop(self):
        """Stop the arbitrage bot"""
        self.running = False
        logger.info("Stopping arbitrage bot...")

if __name__ == "__main__":
    bot = ArbitrageBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        bot.stop()
