"""
MEV Attack Detection Module

Detects potential MEV attacks such as:
- Front-running (MEV bot executing transaction before ours)
- Sandwich attacks (MEV bot executes before and after our transaction)
- Transaction reverts (potential attack indicator)
- Abnormal gas prices (sign of MEV competition)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from web3 import Web3
import time
import config


@dataclass
class MEVAttackIndicator:
    """Indicates a potential MEV attack"""
    attack_type: str
    confidence: float  # 0.0 to 1.0
    timestamp: float
    details: Dict
    chain: str


class MEVDetector:
    """Detects MEV attacks"""

    def __init__(self):
        # Attack tracking
        self.suspected_attacks: List[MEVAttackIndicator] = []
        self.attack_history = {}  # Track attacks per chain
        self.transaction_history = {}  # Track our transactions
        self.mempool_cache = {}  # Cache mempool observations

    async def analyze_transaction(
        self,
        w3: Web3,
        chain: str,
        tx_hash: str,
        expected_profit: float
    ) -> Optional[MEVAttackIndicator]:
        """
        Analyze a transaction for MEV attack signs

        Args:
            w3: Web3 instance
            chain: Chain name
            tx_hash: Transaction hash to analyze
            expected_profit: Expected profit for the trade

        Returns:
            MEVAttackIndicator if attack detected
        """
        try:
            # Get transaction receipt
            receipt = w3.eth.get_transaction_receipt(tx_hash)

            if receipt is None:
                logger.debug(f"Transaction {tx_hash} not yet confirmed")
                return None

            # Check for failures
            if receipt['status'] == 0:
                return self._analyze_failed_transaction(
                    w3, chain, tx_hash, receipt, expected_profit
                )

            # Check for abnormal gas prices
            gas_attack = await self._detect_abnormal_gas(
                w3, chain, receipt, expected_profit
            )
            if gas_attack:
                return gas_attack

            # Check for sandwich attack patterns
            sandwich = await self._detect_sandwich_attack(
                w3, chain, receipt
            )
            if sandwich:
                return sandwich

            # Check transaction ordering (front-running signs)
            front_run = await self._detect_front_running(
                w3, chain, receipt
            )
            if front_run:
                return front_run

            return None

        except Exception as e:
            logger.error(f"Error analyzing transaction for MEV: {str(e)}")
            return None

    def _analyze_failed_transaction(
        self,
        w3: Web3,
        chain: str,
        tx_hash: str,
        receipt,
        expected_profit: float
    ) -> Optional[MEVAttackIndicator]:
        """
        Analyze a failed transaction for MEV signs

        Transaction failures can indicate:
        - Front-runner drained liquidity
        - Sandwich attack victim
        - Price moved against us (slippage)
        """
        try:
            tx = w3.eth.get_transaction(tx_hash)

            # Check if transaction was reverted (likely MEV)
            # vs just failed due to slippage
            if receipt['gasUsed'] < tx['gas'] * 0.8:
                # Used much less gas = likely revert (MEV sign)
                confidence = 0.8
                attack_type = "likely_sandwich_victim"
            else:
                # Used most of gas = likely slippage (not MEV)
                confidence = 0.3
                attack_type = "possible_slippage"

            # Log attack indicator
            indicator = MEVAttackIndicator(
                attack_type=attack_type,
                confidence=confidence,
                timestamp=time.time(),
                details={
                    'tx_hash': tx_hash,
                    'gas_used': receipt['gasUsed'],
                    'gas_limit': tx['gas'],
                    'expected_profit': expected_profit
                },
                chain=chain
            )

            self.suspected_attacks.append(indicator)
            logger.warning(
                f"MEV Attack Detected: {attack_type} "
                f"(confidence: {confidence:.0%}) on {chain}"
            )

            return indicator

        except Exception as e:
            logger.error(f"Error analyzing failed transaction: {str(e)}")
            return None

    async def _detect_abnormal_gas(
        self,
        w3: Web3,
        chain: str,
        receipt,
        expected_profit: float
    ) -> Optional[MEVAttackIndicator]:
        """
        Detect if gas price was abnormally high (MEV competition)

        High gas prices relative to profit indicate MEV bot competition.
        """
        try:
            tx = w3.eth.get_transaction(receipt['transactionHash'])

            # Calculate gas cost
            if 'maxFeePerGas' in tx:  # EIP-1559
                gas_price = receipt.get('effectiveGasPrice', tx['maxFeePerGas'])
            else:  # Legacy
                gas_price = tx['gasPrice']

            gas_cost_eth = (receipt['gasUsed'] * gas_price) / 1e18

            # Estimate gas cost in USD (rough)
            eth_price = await self._get_eth_price()
            gas_cost_usd = gas_cost_eth * eth_price

            # If gas cost is > 30% of expected profit, likely MEV competition
            if gas_cost_usd > expected_profit * 0.3:
                indicator = MEVAttackIndicator(
                    attack_type="abnormal_gas_price",
                    confidence=min(1.0, (gas_cost_usd / expected_profit) * 0.5),
                    timestamp=time.time(),
                    details={
                        'gas_price': gas_price,
                        'gas_cost_usd': gas_cost_usd,
                        'expected_profit': expected_profit,
                        'gas_to_profit_ratio': gas_cost_usd / expected_profit if expected_profit > 0 else 0
                    },
                    chain=chain
                )

                logger.warning(
                    f"Abnormal gas detected on {chain}: "
                    f"${gas_cost_usd:.2f} gas cost for ${expected_profit:.2f} profit"
                )

                return indicator

            return None

        except Exception as e:
            logger.debug(f"Error detecting abnormal gas: {str(e)}")
            return None

    async def _detect_sandwich_attack(
        self,
        w3: Web3,
        chain: str,
        receipt
    ) -> Optional[MEVAttackIndicator]:
        """
        Detect sandwich attack pattern

        Sandwich attacks have:
        - Transaction before us (front-run)
        - Our transaction
        - Transaction after us (back-run)
        All in same block
        """
        try:
            block_number = receipt['blockNumber']
            tx_index = receipt['transactionIndex']

            # Get block transactions
            block = w3.eth.get_block(block_number)
            txs_in_block = block['transactions']

            # Check if there are similar-looking transactions before and after
            before_similar = False
            after_similar = False

            # Look at transactions before and after
            if tx_index > 0:
                # Check transaction before
                before_tx_hash = txs_in_block[tx_index - 1]
                before_tx = w3.eth.get_transaction(before_tx_hash)
                if self._looks_like_swap(before_tx):
                    before_similar = True

            if tx_index < len(txs_in_block) - 1:
                # Check transaction after
                after_tx_hash = txs_in_block[tx_index + 1]
                after_tx = w3.eth.get_transaction(after_tx_hash)
                if self._looks_like_swap(after_tx):
                    after_similar = True

            # Sandwich attack = similar tx before and after
            if before_similar and after_similar:
                indicator = MEVAttackIndicator(
                    attack_type="sandwich_attack",
                    confidence=0.9,
                    timestamp=time.time(),
                    details={
                        'block': block_number,
                        'position': tx_index,
                        'before_swap': before_similar,
                        'after_swap': after_similar
                    },
                    chain=chain
                )

                logger.error(f"Sandwich attack detected on {chain}!")
                return indicator

            return None

        except Exception as e:
            logger.debug(f"Error detecting sandwich attack: {str(e)}")
            return None

    async def _detect_front_running(
        self,
        w3: Web3,
        chain: str,
        receipt
    ) -> Optional[MEVAttackIndicator]:
        """
        Detect front-running attack

        Front-running: MEV bot executes transaction before ours
        """
        try:
            block_number = receipt['blockNumber']
            tx_index = receipt['transactionIndex']

            # Get block transactions
            block = w3.eth.get_block(block_number)
            txs_in_block = block['transactions']

            # Check if multiple swaps happened right before ours
            swap_count_before = 0
            for i in range(max(0, tx_index - 3), tx_index):
                prev_tx_hash = txs_in_block[i]
                prev_tx = w3.eth.get_transaction(prev_tx_hash)
                if self._looks_like_swap(prev_tx):
                    swap_count_before += 1

            # If 3+ swaps in 3 blocks before = likely MEV bot
            if swap_count_before >= 3:
                indicator = MEVAttackIndicator(
                    attack_type="front_running",
                    confidence=0.85,
                    timestamp=time.time(),
                    details={
                        'block': block_number,
                        'position': tx_index,
                        'swaps_before': swap_count_before
                    },
                    chain=chain
                )

                logger.warning(f"Front-running detected on {chain}")
                return indicator

            return None

        except Exception as e:
            logger.debug(f"Error detecting front-running: {str(e)}")
            return None

    def _looks_like_swap(self, tx) -> bool:
        """Check if transaction looks like a swap"""
        try:
            # Check function signature
            # Uniswap/Sushiswap swap function selectors
            swap_selectors = [
                '0x38ed1739',  # swapExactTokensForTokens
                '0x4a25d94a',  # swapTokensForExactTokens
                '0x7ff36ab5',  # swapExactETHForTokens
                '0xfb3bdb41',  # swapExactTokensForETH
                '0x414bf389',  # exactInputSingle (Uniswap V3)
                '0x3bba21dc',  # exactInput (Uniswap V3)
            ]

            input_data = tx.get('input', '')
            if input_data and len(input_data) >= 10:
                selector = input_data[:10]
                return selector in swap_selectors

            return False

        except:
            return False

    async def _get_eth_price(self) -> float:
        """Get current ETH price in USD"""
        try:
            # This should be integrated with a price oracle
            # For now, use a rough estimate
            return 2000.0  # Placeholder

        except:
            return 2000.0

    def get_attack_summary(self, chain: Optional[str] = None) -> Dict:
        """Get summary of detected attacks"""
        attacks = self.suspected_attacks
        if chain:
            attacks = [a for a in attacks if a.chain == chain]

        by_type = {}
        for attack in attacks:
            attack_type = attack.attack_type
            if attack_type not in by_type:
                by_type[attack_type] = 0
            by_type[attack_type] += 1

        return {
            'total_detected': len(attacks),
            'by_type': by_type,
            'recent_attacks': attacks[-5:] if attacks else [],
            'chain': chain
        }

    def should_increase_protection(self, chain: str) -> bool:
        """Check if we should increase MEV protection for a chain"""
        attacks = [a for a in self.suspected_attacks if a.chain == chain]

        # If more than 3 attacks in last 10 minutes
        recent_attacks = [
            a for a in attacks
            if (time.time() - a.timestamp) < 600
        ]

        return len(recent_attacks) >= 3

    def record_attack_recovered(self, indicator: MEVAttackIndicator):
        """Record that we recovered from an attack"""
        logger.info(f"Recovered from {indicator.attack_type} on {indicator.chain}")


# Create singleton
mev_detector = MEVDetector()
