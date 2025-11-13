"""
Contract Interface V2
Interface for ArbitrageV2 contracts with enhanced security features
"""

import asyncio
import json
import os
from web3 import Web3
from loguru import logger
from typing import Optional, Dict
import config


class ContractInterfaceV2:
    """
    Interface for ArbitrageV2 smart contracts

    Features:
    - Reentrancy protection
    - Slippage protection
    - Deadline checks
    - Profitability verification
    - Whitelist management
    """

    def __init__(self, chain: str = 'polygon'):
        """
        Initialize contract interface for a specific chain

        Args:
            chain: Chain name (polygon, arbitrum, optimism, bsc)
        """
        self.chain = chain

        # Load deployment info
        deployment_file = 'deployed_contracts_v2.json'
        if not os.path.exists(deployment_file):
            raise Exception(
                f"ArbitrageV2 not deployed yet! "
                f"Run: python scripts/deploy_arbitrage_v2.py --chain {chain}"
            )

        with open(deployment_file, 'r') as f:
            deployments = json.load(f)

        if chain not in deployments:
            raise Exception(
                f"ArbitrageV2 not deployed to {chain}! "
                f"Run: python scripts/deploy_arbitrage_v2.py --chain {chain}"
            )

        self.contract_address = deployments[chain]['contract_address']
        self.tx_hash = deployments[chain].get('tx_hash')

        # Load ABI
        abi_file = f'deployed_contracts_v2_{chain}_abi.json'
        if not os.path.exists(abi_file):
            raise Exception(f"ABI file not found: {abi_file}")

        with open(abi_file, 'r') as f:
            self.contract_abi = json.load(f)

        # Get chain configuration
        chain_config = config.SUPPORTED_CHAINS.get(chain)
        if not chain_config:
            raise ValueError(f"Unsupported chain: {chain}")

        self.chain_config = chain_config

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(chain_config['rpc']))

        if not self.w3.is_connected():
            raise Exception(f"Failed to connect to {chain} RPC")

        # Create contract instance
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )

        logger.info(f"ContractInterfaceV2 initialized for {chain}")
        logger.info(f"  Contract: {self.contract_address}")
        logger.info(f"  Chain ID: {chain_config['chain_id']}")

    async def execute_flashswap(
        self,
        pair_address: str,
        token_borrow: str,
        amount: int,
        target_router: str,
        token_out: str,
        min_profit: int,
        deadline: int = None
    ) -> Optional[str]:
        """
        Execute flash swap arbitrage with ArbitrageV2

        Args:
            pair_address: Uniswap V2 pair address to borrow from
            token_borrow: Token to borrow
            amount: Amount to borrow (in wei)
            target_router: Router to execute arbitrage on
            token_out: Output token
            min_profit: Minimum profit required (in wei)
            deadline: Transaction deadline (defaults to current time + 5 minutes)

        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            # Set deadline if not provided (5 minutes from now)
            if deadline is None:
                current_block = self.w3.eth.get_block('latest')
                deadline = current_block['timestamp'] + 300  # 5 minutes

            logger.info(
                f"Executing flashswap on {self.chain}:\n"
                f"  Pair: {pair_address}\n"
                f"  Token Borrow: {token_borrow}\n"
                f"  Amount: {Web3.from_wei(amount, 'ether'):.6f}\n"
                f"  Target Router: {target_router}\n"
                f"  Min Profit: {Web3.from_wei(min_profit, 'ether'):.6f}\n"
                f"  Deadline: {deadline}"
            )

            # Build transaction
            tx = self.contract.functions.executeFlashSwap(
                pair_address,
                token_borrow,
                amount,
                target_router,
                token_out,
                min_profit,
                deadline
            ).build_transaction({
                'from': config.WALLET_ADDRESS,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET_ADDRESS),
                'gas': 500000,  # Conservative gas limit
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_config['chain_id']
            })

            logger.debug("Signing transaction...")

            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=config.PRIVATE_KEY
            )

            logger.debug("Sending transaction...")

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            logger.info(f"Transaction sent: {tx_hash.hex()}")
            logger.info("Waiting for confirmation...")

            # Wait for receipt
            receipt = await asyncio.to_thread(
                self.w3.eth.wait_for_transaction_receipt,
                tx_hash,
                timeout=120
            )

            if receipt.status == 1:
                logger.info(f"✅ Flash swap successful!")
                logger.info(f"  Block: {receipt.blockNumber}")
                logger.info(f"  Gas Used: {receipt.gasUsed}")
                return tx_hash.hex()
            else:
                logger.error(f"❌ Flash swap failed (status: {receipt.status})")
                return None

        except Exception as e:
            logger.error(f"Error executing flashswap: {str(e)}")
            return None

    async def check_profitability(
        self,
        amount_borrowed: int,
        expected_output: int
    ) -> bool:
        """
        Check if a trade would be profitable

        Args:
            amount_borrowed: Amount to borrow (in wei)
            expected_output: Expected output amount (in wei)

        Returns:
            True if profitable, False otherwise
        """
        try:
            is_profitable = await asyncio.to_thread(
                self.contract.functions.wouldBeProfitable(
                    amount_borrowed,
                    expected_output
                ).call
            )

            return is_profitable

        except Exception as e:
            logger.error(f"Error checking profitability: {str(e)}")
            return False

    async def get_contract_stats(self) -> Dict:
        """
        Get contract statistics

        Returns:
            Dict with success_count, fail_count, success_rate
        """
        try:
            stats = await asyncio.to_thread(
                self.contract.functions.getStats().call
            )

            success_count, fail_count, success_rate = stats

            return {
                'success_count': success_count,
                'fail_count': fail_count,
                'success_rate': success_rate,
                'total_trades': success_count + fail_count
            }

        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {
                'success_count': 0,
                'fail_count': 0,
                'success_rate': 0,
                'total_trades': 0
            }

    async def get_min_profit_threshold(self) -> float:
        """Get minimum profit threshold (as percentage)"""
        try:
            min_profit_bp = await asyncio.to_thread(
                self.contract.functions.minProfitBasisPoints().call
            )
            return min_profit_bp / 100  # Convert basis points to percentage

        except Exception as e:
            logger.error(f"Error getting min profit: {str(e)}")
            return 0.3  # Default

    async def get_max_slippage(self) -> float:
        """Get maximum slippage tolerance (as percentage)"""
        try:
            max_slippage_bp = await asyncio.to_thread(
                self.contract.functions.maxSlippageBasisPoints().call
            )
            return max_slippage_bp / 100  # Convert basis points to percentage

        except Exception as e:
            logger.error(f"Error getting max slippage: {str(e)}")
            return 1.0  # Default

    async def is_router_whitelisted(self, router_address: str) -> bool:
        """Check if a router is whitelisted"""
        try:
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedRouters(router_address).call
            )
            return is_whitelisted

        except Exception as e:
            logger.error(f"Error checking router whitelist: {str(e)}")
            return False

    async def is_token_whitelisted(self, token_address: str) -> bool:
        """Check if a token is whitelisted"""
        try:
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedTokens(token_address).call
            )
            return is_whitelisted

        except Exception as e:
            logger.error(f"Error checking token whitelist: {str(e)}")
            return False

    async def is_paused(self) -> bool:
        """Check if contract is paused"""
        try:
            paused = await asyncio.to_thread(
                self.contract.functions.paused().call
            )
            return paused

        except Exception as e:
            logger.error(f"Error checking pause status: {str(e)}")
            return True  # Assume paused if error

    async def get_owner(self) -> str:
        """Get contract owner address"""
        try:
            owner = await asyncio.to_thread(
                self.contract.functions.owner().call
            )
            return owner

        except Exception as e:
            logger.error(f"Error getting owner: {str(e)}")
            return ""

    async def withdraw_profits(self, token_address: str, amount: int) -> Optional[str]:
        """
        Withdraw profits from contract

        Args:
            token_address: Token to withdraw
            amount: Amount to withdraw (in wei)

        Returns:
            Transaction hash if successful
        """
        try:
            logger.info(
                f"Withdrawing profits from {self.chain}:\n"
                f"  Token: {token_address}\n"
                f"  Amount: {Web3.from_wei(amount, 'ether'):.6f}"
            )

            # Build transaction
            tx = self.contract.functions.withdrawProfit(
                token_address,
                amount
            ).build_transaction({
                'from': config.WALLET_ADDRESS,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET_ADDRESS),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_config['chain_id']
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, config.PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            logger.info(f"Withdrawal transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = await asyncio.to_thread(
                self.w3.eth.wait_for_transaction_receipt,
                tx_hash,
                timeout=120
            )

            if receipt.status == 1:
                logger.info("✅ Withdrawal successful!")
                return tx_hash.hex()
            else:
                logger.error("❌ Withdrawal failed")
                return None

        except Exception as e:
            logger.error(f"Error withdrawing profits: {str(e)}")
            return None

    def get_contract_info(self) -> Dict:
        """Get contract information"""
        return {
            'chain': self.chain,
            'address': self.contract_address,
            'deployment_tx': self.tx_hash,
            'chain_id': self.chain_config['chain_id'],
            'native_token': self.chain_config['native_token']
        }


async def test_interface():
    """Test ContractInterfaceV2"""
    logger.info("Testing ContractInterfaceV2...")

    try:
        # Initialize interface
        interface = ContractInterfaceV2(chain='polygon')

        # Get contract info
        info = interface.get_contract_info()
        logger.info(f"Contract Info: {json.dumps(info, indent=2)}")

        # Get stats
        stats = await interface.get_contract_stats()
        logger.info(f"Contract Stats: {json.dumps(stats, indent=2)}")

        # Get thresholds
        min_profit = await interface.get_min_profit_threshold()
        max_slippage = await interface.get_max_slippage()
        logger.info(f"Min Profit: {min_profit}%")
        logger.info(f"Max Slippage: {max_slippage}%")

        # Check owner
        owner = await interface.get_owner()
        logger.info(f"Owner: {owner}")

        # Check pause status
        paused = await interface.is_paused()
        logger.info(f"Paused: {paused}")

        logger.info("✅ Interface test complete!")

    except Exception as e:
        logger.error(f"Interface test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    logger.info("ContractInterfaceV2 Module")
    asyncio.run(test_interface())
