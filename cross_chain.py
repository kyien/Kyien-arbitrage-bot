from web3 import Web3
import asyncio
from loguru import logger
import config
from typing import Dict, List, Tuple
import json

class CrossChainManager:
    def __init__(self):
        # Initialize connections to different chains
        self.chains = {
            'polygon': Web3(Web3.HTTPProvider(config.POLYGON_RPC_URL)),
            'arbitrum': Web3(Web3.HTTPProvider(config.ARBITRUM_RPC_URL)),
            'optimism': Web3(Web3.HTTPProvider(config.OPTIMISM_RPC_URL)),
            'bsc': Web3(Web3.HTTPProvider(config.BSC_RPC_URL))
        }
        
        self.bridges = {
            'across': config.ACROSS_ROUTER,
            'socket': config.SOCKET_ROUTER,
            'stargate': config.STARGATE_ROUTER,
            'layerzero': config.LAYERZERO_ENDPOINT
        }
        
    async def check_cross_chain_opportunities(self, token: str) -> List[Dict]:
        """Find arbitrage opportunities across different chains"""
        opportunities = []
        
        # Get prices from all chains
        prices = await self._get_prices_across_chains(token)
        
        # Check bridge fees and gas costs
        bridge_fees = await self._get_bridge_fees(token)
        gas_costs = await self._get_gas_costs()
        
        # Find profitable paths
        for source_chain in prices:
            for target_chain in prices:
                if source_chain != target_chain:
                    for bridge in self.bridges:
                        profit = await self._calculate_cross_chain_profit(
                            token,
                            source_chain,
                            target_chain,
                            prices[source_chain],
                            prices[target_chain],
                            bridge_fees[bridge],
                            gas_costs
                        )
                        
                        if profit['profitable']:
                            opportunities.append({
                                'source_chain': source_chain,
                                'target_chain': target_chain,
                                'bridge': bridge,
                                'profit': profit['amount'],
                                'path': profit['path']
                            })
        
        return opportunities

    async def execute_cross_chain_arbitrage(self, opportunity: Dict) -> bool:
        """Execute a cross-chain arbitrage opportunity"""
        try:
            # 1. Buy token on source chain
            source_tx = await self._execute_dex_trade(
                opportunity['source_chain'],
                opportunity['path']['source_dex'],
                opportunity['path']['amount'],
                'buy'
            )
            
            if not source_tx:
                return False
                
            # 2. Bridge tokens to target chain
            bridge_tx = await self._bridge_tokens(
                opportunity['bridge'],
                opportunity['source_chain'],
                opportunity['target_chain'],
                opportunity['path']['amount']
            )
            
            if not bridge_tx:
                return False
            
            # 3. Wait for bridge completion
            await self._wait_for_bridge_completion(bridge_tx)
            
            # 4. Sell token on target chain
            target_tx = await self._execute_dex_trade(
                opportunity['target_chain'],
                opportunity['path']['target_dex'],
                opportunity['path']['amount'],
                'sell'
            )
            
            return bool(target_tx)
            
        except Exception as e:
            logger.error(f"Error in cross-chain arbitrage: {str(e)}")
            return False

    async def _get_prices_across_chains(self, token: str) -> Dict:
        """Get token prices across all chains and DEXes"""
        prices = {}
        tasks = []
        
        for chain in self.chains:
            prices[chain] = {}
            for dex in self._get_dexes_for_chain(chain):
                task = self._get_price_on_dex(chain, dex, token)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return self._process_price_results(results)

    async def _get_bridge_fees(self, token: str) -> Dict:
        """Get fees for different bridge protocols"""
        fees = {}
        for bridge in self.bridges:
            fees[bridge] = await self._query_bridge_fee(bridge, token)
        return fees

    async def _get_gas_costs(self) -> Dict:
        """Get gas costs for different chains"""
        gas_costs = {}
        for chain in self.chains:
            gas_costs[chain] = await self._estimate_gas_cost(chain)
        return gas_costs

    async def _calculate_cross_chain_profit(
        self, token: str, source_chain: str, target_chain: str,
        source_price: float, target_price: float,
        bridge_fee: float, gas_costs: Dict
    ) -> Dict:
        """Calculate potential profit for cross-chain arbitrage"""
        try:
            # Calculate optimal amount
            amount = self._calculate_optimal_amount(
                source_price,
                target_price,
                bridge_fee,
                gas_costs[source_chain],
                gas_costs[target_chain]
            )
            
            # Calculate total costs
            total_cost = (
                amount * source_price +  # Cost of buying tokens
                bridge_fee +             # Bridge fee
                gas_costs[source_chain] + # Source chain gas
                gas_costs[target_chain]   # Target chain gas
            )
            
            # Calculate revenue
            revenue = amount * target_price
            
            # Calculate profit
            profit = revenue - total_cost
            
            return {
                'profitable': profit > config.MIN_PROFIT_THRESHOLD,
                'amount': profit,
                'path': {
                    'amount': amount,
                    'source_dex': self._get_best_dex(source_chain, token, 'buy'),
                    'target_dex': self._get_best_dex(target_chain, token, 'sell')
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating cross-chain profit: {str(e)}")
            return {'profitable': False, 'amount': 0, 'path': None}

    def _get_dexes_for_chain(self, chain: str) -> List[str]:
        """Get list of DEXes available on a specific chain"""
        dex_mapping = {
            'polygon': ['quickswap', 'sushiswap', 'uniswap_v3', 'curve'],
            'arbitrum': ['sushiswap', 'uniswap_v3', 'curve', 'balancer'],
            'optimism': ['uniswap_v3', 'curve', 'velodrome'],
            'bsc': ['pancakeswap', 'sushiswap', 'curve']
        }
        return dex_mapping.get(chain, [])
