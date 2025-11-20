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
from contract_interface_v2 import ContractInterfaceV2
from cross_chain import CrossChainManager
from advanced_strategies import AdvancedStrategyManager
from monitoring_alerts import alert_manager, AlertLevel
from logging_config import setup_logging, log_trade, log_performance
from scripts.health_check import update_heartbeat
from mev_strategy_integration import mev_manager
from volatility_detector import VolatilityDetector

class ArbitrageBot:
    def __init__(self, chain='polygon', enable_cex=False):
        """
        Initialize Arbitrage Bot for a specific chain

        Args:
            chain: Chain to operate on ('polygon', 'arbitrum', 'optimism', 'bsc', 'ethereum')
            enable_cex: Whether to enable CEX trading (requires API keys and capital)
        """
        self.chain = chain
        self.enable_cex = enable_cex

        # Get chain configuration
        chain_config = config.SUPPORTED_CHAINS.get(chain)
        if not chain_config:
            raise ValueError(f"Unsupported chain: {chain}")

        # Initialize CEX exchanges (only if enabled)
        if enable_cex:
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
        else:
            self.binance = None
            self.okx = None

        # Get RPC URL for this chain
        rpc_url = chain_config['rpc']

        # Initialize Web3 and DEX interfaces for this chain
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.dex = DexInterface(rpc_url, chain=chain)
        self.flashloan = FlashloanExecutor(rpc_url)

        # Initialize MEV strategy manager
        self.mev_manager = mev_manager
        
        # Initialize contract interface with error handling
        try:
            self.contract_interface = ContractInterfaceV2(chain=chain)
            logger.info(f"✓ ContractInterfaceV2 initialized for {chain}")
        except Exception as e:
            logger.warning(f"⚠ ContractInterfaceV2 not initialized: {str(e)}")
            logger.warning("  Run: python scripts/deploy_arbitrage_v2.py --chain polygon")
            self.contract_interface = None
            
        self.cross_chain = CrossChainManager()
        self.strategy = AdvancedStrategyManager()
        
        # Initialize volatility detector
        self.volatility_detector = VolatilityDetector(
            high_volatility_threshold=2.0,
            check_interval=30
        )
        
        # Monitoring is now handled by alert_manager (imported globally)

        # Get DEX names for this chain
        self.dex_names = list(config.DEX_ROUTERS.get(chain, {}).keys())

        # Get tokens for this chain
        self.tokens = config.TOKENS_BY_CHAIN.get(chain, {})

        # Price storage (dynamically create based on available DEXes)
        self.prices = {dex: {} for dex in self.dex_names}
        if enable_cex:
            self.prices['binance'] = {}
            self.prices['okx'] = {}

        # Moving averages for price analysis
        self.price_history = {}
        self.running = False

        logger.info(f"Arbitrage bot initialized for {chain} chain")
        logger.info(f"  - Available DEXes: {', '.join(self.dex_names)}")
        logger.info(f"  - Available tokens: {', '.join(self.tokens.keys())}")
        logger.info(f"  - CEX trading: {'enabled' if enable_cex else 'disabled'}")

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

                    # Skip if tokens not available on this chain
                    if token_in not in self.tokens or token_out not in self.tokens:
                        continue

                    # Use DEXes available on this chain
                    dex_names = self.dex_names

                    # Create all tasks at once for parallel execution
                    price_tasks = [
                        self.dex.get_token_price(
                            dex,
                            self.tokens[token_in],
                            self.tokens[token_out]
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

                    # Update volatility detector with price data
                    for dex in prices:
                        if prices[dex]:
                            await self.volatility_detector.add_price_data(
                                f"{token_in}/{token_out}-{dex}",
                                prices[dex],
                                volumes.get(dex, 0)
                            )

                    # Process arbitrage opportunities
                    await self._process_arbitrage_opportunities(
                        pair, token_in, token_out, prices, volumes, liquidity
                    )

                # CRITICAL: Reduce sleep time dramatically for faster opportunity detection
                await asyncio.sleep(0.01)  # 10ms instead of 100ms = 10x faster

            except Exception as e:
                logger.error(f"Error in DEX arbitrage check on {self.chain}: {str(e)}")
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

                            # Build trade for MEV-protected execution
                            trade = {
                                'pair_address': await self.dex.get_pair_address(dex1, token_in, token_out),
                                'token_in': self.tokens[token_in],
                                'token_out': self.tokens[token_out],
                                'amount': optimal_amount,
                                'target_router': config.DEX_ROUTERS[self.chain][dex2],
                                'min_profit': int(optimal_amount * 0.01 * 10**18),  # 1% minimum
                                'profit_usd': optimal_amount * profit_pct / 100
                            }

                            # Send opportunity alert
                            if trade['profit_usd'] > 10.0:  # Alert only for $10+ opportunities
                                await alert_manager.opportunity_found(
                                    chain=self.chain,
                                    dex1=dex1,
                                    dex2=dex2,
                                    token_pair=pair,
                                    profit=trade['profit_usd']
                                )

                            if trade['profit_usd'] > config.MIN_PROFIT_THRESHOLD:
                                # Execute with MEV protection
                                await alert_manager.execution_started(
                                    chain=self.chain,
                                    token_pair=pair,
                                    expected_profit=trade['profit_usd']
                                )
                                
                                result = await self.mev_manager.execute_with_mev_protection(
                                    chain=self.chain,
                                    trades=[trade],
                                    profit_usd=trade['profit_usd']
                                )
                                
                                if result:
                                    await alert_manager.execution_completed(
                                        chain=self.chain,
                                        tx_hash=result,
                                        token_pair=pair,
                                        actual_profit=trade['profit_usd'],
                                        gas_cost=0.5,  # Estimate
                                        net_profit=trade['profit_usd'] - 0.5
                                    )
                                else:
                                    await alert_manager.execution_failed(
                                        chain=self.chain,
                                        token_pair=pair,
                                        reason="MEV protection execution failed"
                                    )

    async def execute_dex_flashswap(self, chain, dex1, dex2, token_in, token_out, amount, prices):
        """Execute arbitrage between DEXes using flashswap"""
        try:
            # Get token addresses
            token_in_address = self.tokens[token_in]
            token_out_address = self.tokens[token_out]
            
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
                log_trade({
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
                alert_manager.send_alert(
                    f"DEX Flashswap: {token_in} -> {token_out} from {dex1} to {dex2}. Profit: {(prices[dex2] - prices[dex1]) * amount}",
                    "info"
                )
            
        except Exception as e:
            logger.error(f"Error executing DEX flashswap: {str(e)}")

    async def _monitor_gas_levels(self):
        """Monitor gas token balances and alert when low"""
        gas_thresholds = {
            'polygon': 10.0,    # 10 MATIC
            'arbitrum': 0.01,   # 0.01 ETH
            'optimism': 0.01,   # 0.01 ETH
            'bsc': 0.05         # 0.05 BNB
        }
        
        while self.running:
            try:
                for chain in ['polygon', 'arbitrum', 'optimism', 'bsc']:
                    if not self.w3.is_connected():
                        continue
                    
                    # Get native token balance
                    balance = self.w3.eth.get_balance(config.WALLET_ADDRESS)
                    balance_eth = balance / 10**18
                    
                    threshold = gas_thresholds.get(chain, 10.0)
                    
                    if balance_eth < threshold:
                        await alert_manager.gas_exhaustion_alert(
                            chain=chain,
                            current_balance=balance_eth,
                            threshold=threshold
                        )
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring gas levels: {e}")
                await asyncio.sleep(300)

    async def _monitor_volatility(self):
        """Monitor volatility and send alerts"""
        while self.running:
            try:
                # Calculate volatility for all monitored pairs
                for pair in config.TRADING_PAIRS['DEX']:
                    metrics = self.volatility_detector.calculate_volatility(pair)
                    
                    if metrics and metrics.is_high_volatility:
                        await alert_manager.send_alert(
                            level=AlertLevel.WARNING,
                            title="🔥 High Volatility Detected",
                            message=f"High volatility on {pair}: {metrics.current_volatility:.2f}%",
                            chain=self.chain,
                            metadata={
                                'volatility': metrics.current_volatility,
                                'trend': metrics.volatility_trend
                            }
                        )
                
                # Check if high volatility period
                is_high_vol = self.volatility_detector.is_high_volatility_period()
                if is_high_vol:
                    status = self.volatility_detector.get_status()
                    await alert_manager.send_alert(
                        level=AlertLevel.INFO,
                        title="📊 Volatility Mode Active",
                        message=f"High volatility mode active. Score: {status['volatility_score']:.1f}/100\n"
                               f"Duration: {status['high_volatility_duration']:.0f}s",
                        chain=self.chain
                    )
                        
                await asyncio.sleep(self.volatility_detector.check_interval)
                
            except Exception as e:
                logger.error(f"Error in volatility monitoring: {e}")
                await asyncio.sleep(30)

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
            # Start MEV strategies
            asyncio.create_task(self.mev_manager.start_all_strategies())
            
            # Start volatility monitoring
            asyncio.create_task(self._monitor_volatility())
            
            # Start gas level monitoring
            asyncio.create_task(self._monitor_gas_levels())
            
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
                self.withdraw_profits()
            ]
            
            # Combine all tasks
            tasks = ws_tasks + monitor_tasks
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in market monitoring: {str(e)}")
            await asyncio.sleep(5)

    async def start(self):
        """Start the arbitrage bot"""
        logger.info("Starting arbitrage bot...")
        await alert_manager.bot_started(chains=[self.chain])
        await self.monitor_markets()

    def stop(self):
        """Stop the arbitrage bot"""
        self.running = False
        asyncio.create_task(alert_manager.bot_stopped(reason="User initiated stop"))
        logger.info("Stopping arbitrage bot...")

if __name__ == "__main__":
    bot = ArbitrageBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        bot.stop()
    except Exception as e:
        asyncio.run(alert_manager.bot_error(error=str(e)))
        raise
