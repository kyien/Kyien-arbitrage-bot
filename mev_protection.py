"""
MEV Protection and Gas Optimization Module

This module provides advanced MEV protection and gas optimization strategies
for the arbitrage bot to maximize profitability and protect against front-running.
"""

import random
import time
import asyncio
from typing import Dict, Optional, Tuple
from web3 import Web3
from loguru import logger
import config


class MEVProtection:
    """Advanced MEV protection strategies"""
    
    def __init__(self):
        self.transaction_timings = {}  # Track transaction timing patterns
        self.failed_tx_count = {}  # Track failed transactions per chain
        self.last_tx_time = {}  # Track last transaction time per chain
        
    def calculate_optimal_gas_price(
        self, 
        w3: Web3, 
        chain: str,
        urgency: str = 'normal'
    ) -> Dict:
        """
        Calculate optimal gas price with MEV protection
        
        Args:
            w3: Web3 instance
            chain: Chain name
            urgency: 'low', 'normal', 'high', 'critical'
            
        Returns:
            Dict with gas price parameters
        """
        try:
            # Get current block information
            latest_block = w3.eth.get_block('latest')
            
            # Check if chain supports EIP-1559
            if latest_block.get('baseFeePerGas') is not None:
                return self._get_eip1559_gas_price(w3, chain, urgency)
            else:
                return self._get_legacy_gas_price(w3, chain, urgency)
                
        except Exception as e:
            logger.error(f"Error calculating gas price: {str(e)}")
            return {'gasPrice': w3.eth.gas_price}
    
    def _get_eip1559_gas_price(
        self, 
        w3: Web3, 
        chain: str,
        urgency: str
    ) -> Dict:
        """Get EIP-1559 gas price with MEV protection"""
        try:
            # Get fee history (last 4 blocks)
            fee_history = w3.eth.fee_history(4, 'latest', [25, 50, 75])
            
            if not fee_history or not fee_history.get('baseFeePerGas'):
                return self._get_legacy_gas_price(w3, chain, urgency)
            
            # Get latest base fee
            base_fee_per_gas = fee_history['baseFeePerGas'][-1]
            
            # Get priority fee percentiles
            rewards = fee_history.get('reward', [])
            if rewards and len(rewards) > 0:
                # Use 50th percentile as base, but adjust based on urgency
                priority_fee_percentiles = rewards[-1]  # Latest block rewards
                
                base_priority_fee = priority_fee_percentiles[1]  # 50th percentile
                
                # Adjust based on urgency
                urgency_multipliers = {
                    'low': 0.8,
                    'normal': 1.0,
                    'high': 1.5,
                    'critical': 2.0
                }
                
                multiplier = urgency_multipliers.get(urgency, 1.0)
                priority_fee_per_gas = int(base_priority_fee * multiplier)
                
                # Add randomness to avoid detection patterns
                # Use small random adjustments (1-5% of priority fee)
                random_adjustment = random.randint(
                    int(priority_fee_per_gas * 0.01),
                    int(priority_fee_per_gas * 0.05)
                )
                priority_fee_per_gas += random_adjustment
                
            else:
                # Fallback if no reward data
                priority_fee_per_gas = int(base_fee_per_gas * 0.05)  # 5% of base fee
            
            # Calculate max fee per gas
            # Base fee can increase by up to 12.5% per block (EIP-1559 spec)
            # Use 2x base fee for safety, plus priority fee
            max_fee_per_gas = int(base_fee_per_gas * 2.5) + priority_fee_per_gas
            
            # Add small non-round number to avoid MEV bot detection
            # MEV bots often target round numbers
            if priority_fee_per_gas % 1000000 == 0:  # If it's a round number
                priority_fee_per_gas += random.randint(12345, 98765)
            
            return {
                'maxFeePerGas': max_fee_per_gas,
                'maxPriorityFeePerGas': priority_fee_per_gas,
                'type': '0x2'  # EIP-1559 transaction type
            }
            
        except Exception as e:
            logger.error(f"Error in EIP-1559 gas calculation: {str(e)}")
            return self._get_legacy_gas_price(w3, chain, urgency)
    
    def _get_legacy_gas_price(
        self, 
        w3: Web3, 
        chain: str,
        urgency: str
    ) -> Dict:
        """Get legacy gas price with MEV protection"""
        try:
            base_gas_price = w3.eth.gas_price
            
            # Adjust based on urgency
            urgency_multipliers = {
                'low': 0.95,
                'normal': 1.0,
                'high': 1.15,
                'critical': 1.3
            }
            
            multiplier = urgency_multipliers.get(urgency, 1.0)
            gas_price = int(base_gas_price * multiplier)
            
            # Add randomness (1-3% of gas price)
            random_adjustment = random.randint(
                int(gas_price * 0.01),
                int(gas_price * 0.03)
            )
            gas_price += random_adjustment
            
            # Avoid round numbers that MEV bots target
            # Round numbers are often targeted by sandwich attacks
            if gas_price % 1000000000 == 0:  # If it's a round number (1 Gwei)
                gas_price += random.randint(10000000, 50000000)  # Add 0.01-0.05 Gwei
            
            # Use prime number remainder to avoid patterns
            # This makes it harder for MEV bots to predict
            prime_remainder = gas_price % 100000007
            if prime_remainder < 100000:  # If remainder is too small
                gas_price += random.randint(100000, 1000000)
            
            return {'gasPrice': gas_price}
            
        except Exception as e:
            logger.error(f"Error in legacy gas calculation: {str(e)}")
            return {'gasPrice': w3.eth.gas_price}
    
    def add_timing_randomization(self, chain: str, base_delay: float = 0.1) -> float:
        """
        Add random delay to avoid timing-based MEV attacks
        
        Args:
            chain: Chain name
            base_delay: Base delay in seconds
            
        Returns:
            Randomized delay in seconds
        """
        # Check if we've been sending transactions too quickly
        last_tx_time = self.last_tx_time.get(chain, 0)
        time_since_last = time.time() - last_tx_time
        
        # If sending too quickly, add more delay
        if time_since_last < 1.0:
            base_delay *= 2
        
        # Add random delay (0.1 to 0.5 seconds)
        random_delay = random.uniform(base_delay, base_delay * 2)
        
        # Add extra delay if we've had recent failures (might be MEV-related)
        failed_count = self.failed_tx_count.get(chain, 0)
        if failed_count > 2:
            random_delay += random.uniform(0.5, 1.5)
        
        return random_delay
    
    def should_use_private_pool(self, chain: str, profit_amount: float) -> bool:
        """
        Determine if transaction should use private transaction pool
        
        Args:
            chain: Chain name
            profit_amount: Expected profit amount
            
        Returns:
            True if should use private pool
        """
        # Use private pools for high-value transactions
        if profit_amount > 100:  # $100+ profit
            return True
        
        # Use private pools if we've had recent MEV attacks
        failed_count = self.failed_tx_count.get(chain, 0)
        if failed_count > 3:
            return True
        
        return False
    
    def get_flashbots_endpoint(self, chain: str) -> Optional[str]:
        """Get Flashbots RPC endpoint for chain"""
        flashbots_endpoints = {
            'ethereum': 'https://relay.flashbots.net',
            'mainnet': 'https://relay.flashbots.net',
        }
        return flashbots_endpoints.get(chain.lower())
    
    def record_transaction(self, chain: str, success: bool):
        """Record transaction for pattern analysis"""
        self.last_tx_time[chain] = time.time()
        
        if not success:
            self.failed_tx_count[chain] = self.failed_tx_count.get(chain, 0) + 1
        else:
            # Reset failure count after successful transaction
            self.failed_tx_count[chain] = 0


class GasOptimizer:
    """Gas optimization strategies"""
    
    def __init__(self):
        self.gas_price_cache = {}  # Cache gas prices
        self.cache_ttl = 30  # Cache TTL in seconds
        self.last_update = {}  # Last cache update time
    
    def get_optimized_gas_limit(
        self,
        w3: Web3,
        contract_function,
        tx_params: Dict,
        safety_multiplier: float = 1.2
    ) -> int:
        """
        Get optimized gas limit with safety margin
        
        Args:
            w3: Web3 instance
            contract_function: Contract function to estimate
            tx_params: Transaction parameters
            safety_multiplier: Safety multiplier for gas limit
            
        Returns:
            Optimized gas limit
        """
        try:
            # Estimate gas
            estimated_gas = contract_function.estimate_gas(tx_params)
            
            # Apply safety multiplier
            optimized_gas = int(estimated_gas * safety_multiplier)
            
            # Cap at maximum reasonable gas limit
            max_gas = config.GAS_LIMIT
            return min(optimized_gas, max_gas)
            
        except Exception as e:
            logger.warning(f"Gas estimation failed: {str(e)}, using default")
            return config.GAS_LIMIT
    
    def optimize_gas_price_for_profit(
        self,
        gas_price: Dict,
        expected_profit: float,
        gas_limit: int
    ) -> Dict:
        """
        Optimize gas price based on expected profit
        
        Args:
            gas_price: Current gas price dict
            expected_profit: Expected profit in USD
            gas_limit: Gas limit for transaction
            
        Returns:
            Optimized gas price dict
        """
        try:
            # Estimate gas cost in ETH
            if 'maxFeePerGas' in gas_price:
                # EIP-1559 transaction
                max_fee = gas_price['maxFeePerGas']
                gas_cost_wei = max_fee * gas_limit
            else:
                # Legacy transaction
                gas_cost_wei = gas_price['gasPrice'] * gas_limit
            
            # Convert to USD (rough estimate, should use oracle in production)
            # Assume 1 ETH = $2000 (this should be dynamic)
            eth_price_usd = 2000
            gas_cost_usd = (gas_cost_wei / 1e18) * eth_price_usd
            
            # If gas cost is too high relative to profit, reduce gas price
            if gas_cost_usd > expected_profit * 0.3:  # More than 30% of profit
                logger.warning(
                    f"Gas cost ({gas_cost_usd:.2f} USD) is high relative to profit "
                    f"({expected_profit:.2f} USD)"
                )
                
                # Reduce gas price by 10% if still profitable
                if gas_cost_usd < expected_profit * 0.9:
                    if 'maxFeePerGas' in gas_price:
                        gas_price['maxFeePerGas'] = int(gas_price['maxFeePerGas'] * 0.9)
                        gas_price['maxPriorityFeePerGas'] = int(
                            gas_price['maxPriorityFeePerGas'] * 0.9
                        )
                    else:
                        gas_price['gasPrice'] = int(gas_price['gasPrice'] * 0.9)
            
            return gas_price
            
        except Exception as e:
            logger.error(f"Error optimizing gas for profit: {str(e)}")
            return gas_price
    
    def get_cached_gas_price(self, chain: str) -> Optional[Dict]:
        """Get cached gas price if still valid"""
        if chain not in self.gas_price_cache:
            return None
        
        last_update = self.last_update.get(chain, 0)
        if time.time() - last_update > self.cache_ttl:
            return None
        
        return self.gas_price_cache[chain]
    
    def cache_gas_price(self, chain: str, gas_price: Dict):
        """Cache gas price"""
        self.gas_price_cache[chain] = gas_price
        self.last_update[chain] = time.time()
    
    def calculate_optimal_deadline(self, w3: Web3, buffer_seconds: int = 300) -> int:
        """
        Calculate optimal transaction deadline
        
        Args:
            w3: Web3 instance
            buffer_seconds: Buffer time in seconds
            
        Returns:
            Deadline timestamp
        """
        current_block = w3.eth.get_block('latest')
        current_time = current_block['timestamp']
        
        # Add buffer for transaction inclusion
        deadline = current_time + buffer_seconds
        
        return deadline
    
    def optimize_slippage_tolerance(
        self,
        expected_price: float,
        liquidity: float,
        trade_size: float
    ) -> float:
        """
        Optimize slippage tolerance based on market conditions
        
        Args:
            expected_price: Expected execution price
            liquidity: Available liquidity
            trade_size: Size of trade
            
        Returns:
            Optimal slippage tolerance (as percentage)
        """
        # Calculate price impact
        price_impact = (trade_size / liquidity) * 100
        
        # Base slippage tolerance
        base_slippage = config.SLIPPAGE_TOLERANCE
        
        # Adjust based on price impact
        if price_impact > 1.0:  # High price impact
            optimal_slippage = base_slippage * 1.5
        elif price_impact < 0.1:  # Low price impact
            optimal_slippage = base_slippage * 0.8
        else:
            optimal_slippage = base_slippage
        
        # Cap at reasonable maximum
        return min(optimal_slippage, 5.0)  # Max 5% slippage


# Create singleton instances
mev_protection = MEVProtection()
gas_optimizer = GasOptimizer()

