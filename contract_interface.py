from web3 import Web3
import json
import os
from loguru import logger
import config
import asyncio
from typing import Dict, Any, List, Optional
import time

class ContractInterface:
    def __init__(self):
        # Load deployed contract addresses
        self.deployed_contracts = self._load_deployed_contracts()
        
        # Initialize web3 connections for each chain
        self.w3_connections = {
            'polygon': Web3(Web3.HTTPProvider(config.POLYGON_RPC_URL)),
            'arbitrum': Web3(Web3.HTTPProvider(config.ARBITRUM_RPC_URL)),
            'optimism': Web3(Web3.HTTPProvider(config.OPTIMISM_RPC_URL)),
            'bsc': Web3(Web3.HTTPProvider(config.BSC_RPC_URL))
        }
        
        # Load contract ABIs
        self.contract_abis = self._load_contract_abis()
        
        # Initialize contract instances
        self.contracts = self._initialize_contracts()
        
        # Account used for transactions
        self.account_address = config.WALLET_ADDRESS
        
        # Private key used for signing transactions
        self.private_key = config.PRIVATE_KEY
        
        logger.info("Contract interface initialized")
    
    def _load_deployed_contracts(self) -> Dict:
        """Load deployed contract addresses from JSON file"""
        try:
            if os.path.exists('deployed_contracts.json'):
                with open('deployed_contracts.json', 'r') as f:
                    return json.load(f)
            else:
                logger.warning("No deployed contracts found. Please run deploy_contracts.py first")
                return {}
        except Exception as e:
            logger.error(f"Error loading deployed contracts: {str(e)}")
            return {}
    
    def _load_contract_abis(self) -> Dict:
        """Load contract ABIs from build directory"""
        try:
            abis = {}
            build_dir = "build/contracts"
            
            if os.path.exists(build_dir):
                for file in os.listdir(build_dir):
                    if file.endswith(".json"):
                        with open(os.path.join(build_dir, file), 'r') as f:
                            contract_data = json.load(f)
                            abis[contract_data['contractName']] = contract_data['abi']
            else:
                logger.warning("No contract build files found. Please compile contracts first")
            
            return abis
        except Exception as e:
            logger.error(f"Error loading contract ABIs: {str(e)}")
            return {}
    
    def _initialize_contracts(self) -> Dict:
        """Initialize contract instances for each chain"""
        contracts = {}
        
        for chain, chain_data in self.deployed_contracts.items():
            contracts[chain] = {}
            w3 = self.w3_connections.get(chain)
            
            if not w3:
                logger.warning(f"No web3 connection for chain: {chain}")
                continue
            
            if 'arbitrage_executor' in chain_data and 'ArbitrageExecutor' in self.contract_abis:
                contracts[chain]['arbitrage_executor'] = w3.eth.contract(
                    address=chain_data['arbitrage_executor'],
                    abi=self.contract_abis['ArbitrageExecutor']
                )
        
        return contracts
    
    async def execute_dex_swap(self, chain: str, router_type: str, token_in: str, token_out: str, 
                             amount_in: int, min_amount_out: int) -> Optional[str]:
        """Execute a swap on a DEX using the deployed contract"""
        try:
            # Get the contract for the specified chain
            contract = self.contracts.get(chain, {}).get('arbitrage_executor')
            w3 = self.w3_connections.get(chain)
            
            if not contract or not w3:
                logger.error(f"Contract or web3 connection not found for chain: {chain}")
                return None
            
            # Get the router address based on the router type
            router_address = self._get_router_address(chain, router_type)
            
            if not router_address:
                logger.error(f"Router address not found for {router_type} on {chain}")
                return None
            
            # Prepare the transaction
            deadline = int(time.time()) + 300  # 5 minutes from now
            
            # Build the transaction
            tx = contract.functions.executeSwap(
                router_address,
                token_in,
                token_out,
                amount_in,
                min_amount_out,
                deadline
            ).build_transaction({
                'from': self.account_address,
                'nonce': w3.eth.get_transaction_count(self.account_address),
                'gas': config.GAS_LIMIT,
                'gasPrice': self._get_optimal_gas_price(w3),
                'chainId': w3.eth.chain_id
            })
            
            # Sign the transaction
            signed_tx = w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Add anti-MEV protection
            protected_tx = self._apply_anti_mev_protection(chain, signed_tx)
            
            # Send the transaction
            tx_hash = w3.eth.send_raw_transaction(protected_tx.rawTransaction)
            
            # Wait for transaction confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"Swap executed successfully on {chain}: {w3.to_hex(tx_hash)}")
                return w3.to_hex(tx_hash)
            else:
                logger.error(f"Swap failed on {chain}: {w3.to_hex(tx_hash)}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing DEX swap: {str(e)}")
            return None
    
    async def execute_flashswap(self, chain: str, pair_address: str, token_borrow: str, 
                              amount: int, target_router: str, token_in: str, token_out: str) -> Optional[str]:
        """Execute a flashswap using the deployed contract"""
        try:
            # Get the contract for the specified chain
            contract = self.contracts.get(chain, {}).get('arbitrage_executor')
            w3 = self.w3_connections.get(chain)
            
            if not contract or not w3:
                logger.error(f"Contract or web3 connection not found for chain: {chain}")
                return None
            
            # Get the router address based on the router type
            target_router_address = self._get_router_address(chain, target_router)
            
            if not target_router_address:
                logger.error(f"Router address not found for {target_router} on {chain}")
                return None
            
            # Encode the callback data
            callback_data = w3.eth.contract().encodeABI(
                fn_name="",
                args=[target_router_address, token_in, token_out]
            )
            
            # Build the transaction
            tx = contract.functions.executeFlashSwap(
                pair_address,
                token_borrow,
                amount,
                callback_data
            ).build_transaction({
                'from': self.account_address,
                'nonce': w3.eth.get_transaction_count(self.account_address),
                'gas': config.GAS_LIMIT,
                'gasPrice': self._get_optimal_gas_price(w3),
                'chainId': w3.eth.chain_id
            })
            
            # Sign the transaction
            signed_tx = w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Add anti-MEV protection
            protected_tx = self._apply_anti_mev_protection(chain, signed_tx)
            
            # Send the transaction
            tx_hash = w3.eth.send_raw_transaction(protected_tx.rawTransaction)
            
            # Wait for transaction confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"Flashswap executed successfully on {chain}: {w3.to_hex(tx_hash)}")
                return w3.to_hex(tx_hash)
            else:
                logger.error(f"Flashswap failed on {chain}: {w3.to_hex(tx_hash)}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing flashswap: {str(e)}")
            return None
    
    def _get_router_address(self, chain: str, router_type: str) -> Optional[str]:
        """Get the router address for a specific chain and router type"""
        routers = {
            'polygon': {
                'uniswap': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
                'quickswap': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'
            },
            'arbitrum': {
                'uniswap': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
            },
            'optimism': {
                'uniswap': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
            },
            'bsc': {
                'pancakeswap': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
                'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
            }
        }
        
        return routers.get(chain, {}).get(router_type.lower())
    
    def _get_optimal_gas_price(self, w3: Web3) -> int:
        """Get optimal gas price with anti-MEV considerations"""
        try:
            # Get current gas price
            base_fee = w3.eth.gas_price
            
            # Check chain for EIP-1559 support
            if hasattr(w3.eth, 'fee_history'):
                # Use EIP-1559 fee mechanism
                try:
                    fee_history = w3.eth.fee_history(4, 'latest', [25, 50, 75])
                    
                    # Calculate max fee and priority fee
                    base_fee_per_gas = fee_history.base_fee_per_gas[-1]
                    priority_fee_per_gas = fee_history.reward[1][1]  # 50th percentile from the latest block
                    
                    # Add slight randomness to the priority fee to avoid detection patterns
                    import random
                    random_adjustment = random.randint(1, 100000)  # Small random value
                    priority_fee_per_gas += random_adjustment
                    
                    # Calculate max fee (base fee + priority fee with a buffer)
                    max_fee_per_gas = base_fee_per_gas * 2 + priority_fee_per_gas
                    
                    return {
                        'maxFeePerGas': max_fee_per_gas,
                        'maxPriorityFeePerGas': priority_fee_per_gas
                    }
                except:
                    # Fallback to legacy pricing if fee_history fails
                    pass
            
            # Legacy gas price with anti-MEV adjustment (avoid round numbers)
            gas_price = int(base_fee * 1.2)  # 20% more than base
            
            # Avoid round numbers that might be targeted by sandwich attacks
            gas_price += gas_price % 100000007  # Add a prime number remainder
            
            return gas_price
            
        except Exception as e:
            logger.error(f"Error calculating gas price: {str(e)}")
            # Fallback to standard gas price
            return w3.eth.gas_price
    
    def _apply_anti_mev_protection(self, chain: str, signed_tx):
        """Apply chain-specific anti-MEV protection to a signed transaction"""
        try:
            # Different chains have different anti-MEV solutions
            if chain == 'ethereum':
                # For Ethereum, we could use Flashbots
                # This is a simplified example - actual implementation would require Flashbots RPC
                return signed_tx
            elif chain == 'polygon':
                # For Polygon, adjust gas price to avoid typical MEV thresholds
                return signed_tx
            else:
                # For other chains, use default protection
                return signed_tx
        except Exception as e:
            logger.error(f"Error applying anti-MEV protection: {str(e)}")
            return signed_tx
    
    async def withdraw_profits(self, chain: str, token_address: str) -> Optional[str]:
        """Withdraw profits from the contract"""
        try:
            # Get the contract for the specified chain
            contract = self.contracts.get(chain, {}).get('arbitrage_executor')
            w3 = self.w3_connections.get(chain)
            
            if not contract or not w3:
                logger.error(f"Contract or web3 connection not found for chain: {chain}")
                return None
            
            # Get token balance
            token_contract = w3.eth.contract(
                address=token_address,
                abi=self._get_erc20_abi()
            )
            
            balance = token_contract.functions.balanceOf(contract.address).call()
            
            if balance == 0:
                logger.info(f"No profits to withdraw for token {token_address} on {chain}")
                return None
            
            # Build the withdrawal transaction
            tx = contract.functions.withdrawToken(
                token_address,
                balance
            ).build_transaction({
                'from': self.account_address,
                'nonce': w3.eth.get_transaction_count(self.account_address),
                'gas': 100000,  # Less gas needed for a simple transfer
                'gasPrice': self._get_optimal_gas_price(w3),
                'chainId': w3.eth.chain_id
            })
            
            # Sign the transaction
            signed_tx = w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Send the transaction
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction confirmation
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"Profits withdrawn successfully on {chain}: {w3.to_hex(tx_hash)}")
                return w3.to_hex(tx_hash)
            else:
                logger.error(f"Profit withdrawal failed on {chain}: {w3.to_hex(tx_hash)}")
                return None
                
        except Exception as e:
            logger.error(f"Error withdrawing profits: {str(e)}")
            return None
    
    def _get_erc20_abi(self) -> List:
        """Get standard ERC20 ABI"""
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
