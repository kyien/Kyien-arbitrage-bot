"""
Deploy ArbitrageV2 Contract (Secure Version)
Deploys the hardened contract with reentrancy protection
"""

import asyncio
import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from loguru import logger
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class ArbitrageV2Deployer:
    """Deploy ArbitrageV2 contract with security features"""

    def __init__(self, chain: str = 'polygon'):
        self.chain = chain
        self.deployment_file = '/app/deployed_contracts_v2.json'

        # Get chain configuration
        chain_config = config.SUPPORTED_CHAINS.get(chain)
        if not chain_config:
            raise ValueError(f"Unsupported chain: {chain}")

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(chain_config['rpc']))
        self.chain_config = chain_config

        # Load existing deployments
        self.deployed_contracts = self._load_deployments()

        logger.info(f"ArbitrageV2 Deployer initialized for {chain}")

    def _load_deployments(self) -> dict:
        """Load existing contract deployments"""
        if os.path.exists(self.deployment_file):
            if os.path.isdir(self.deployment_file):
                logger.error(f"CRITICAL ERROR: {self.deployment_file} is a directory, not a file!")
                logger.error("Please remove the directory and create an empty JSON file instead.")
                sys.exit(1)
            
            try:
                with open(self.deployment_file, 'r') as f:
                    content = f.read().strip()
                    if not content:  # File is empty
                        logger.warning(f"{self.deployment_file} is empty, initializing with empty object")
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {self.deployment_file}: {str(e)}")
                logger.error("Please fix the JSON file or delete it to start fresh")
                sys.exit(1)
        
        logger.info(f"{self.deployment_file} not found, starting fresh")
        return {}

    def _save_deployment(self, chain: str, contract_address: str, tx_hash: str):
        """Save deployment info"""
        self.deployed_contracts[chain] = {
            'contract_address': contract_address,
            'tx_hash': tx_hash,
            'deployer': config.WALLET_ADDRESS,
            'chain_id': self.chain_config['chain_id'],
            'timestamp': int(asyncio.get_event_loop().time())
        }

        with open(self.deployment_file, 'w') as f:
            json.dump(self.deployed_contracts, f, indent=2)

        logger.info(f"Deployment saved to {self.deployment_file}")

    def compile_contract(self) -> dict:
        """Compile ArbitrageV2.sol"""
        logger.info("Compiling ArbitrageV2.sol...")

        try:
            # Install Solidity compiler
            install_solc('0.8.17')

            # Read contract source
            contract_path = '/app/contracts/ArbitrageV2.sol'
            with open(contract_path, 'r') as file:
                contract_source = file.read()

            # Get node_modules path
            node_modules_path = '/app/node_modules'
            
            logger.info(f"Node modules path: {node_modules_path}")
            logger.info(f"OpenZeppelin exists: {os.path.exists(os.path.join(node_modules_path, '@openzeppelin'))}")
            logger.info(f"Uniswap exists: {os.path.exists(os.path.join(node_modules_path, '@uniswap'))}")

            if not os.path.exists(node_modules_path):
                logger.error(f"CRITICAL: node_modules not found at {node_modules_path}")
                logger.error("Directory contents of /app:")
                logger.error(os.listdir('/app'))
                raise FileNotFoundError("node_modules directory is missing")

            # Compile with proper import remappings
            compiled_sol = compile_standard(
                {
                    "language": "Solidity",
                    "sources": {
                        "ArbitrageV2.sol": {
                            "content": contract_source
                        }
                    },
                    "settings": {
                        "optimizer": {
                            "enabled": True,
                            "runs": 200
                        },
                        # CRITICAL: Remappings tell solc where to find imports
                        "remappings": [
                            f"@openzeppelin/={node_modules_path}/@openzeppelin/",
                            f"@uniswap/={node_modules_path}/@uniswap/"
                        ],
                        "outputSelection": {
                            "*": {
                                "*": ["abi", "metadata", "evm.bytecode", "evm.bytecode.sourceMap"]
                            }
                        }
                    }
                },
                solc_version='0.8.17',
                allow_paths=[node_modules_path, '/app/contracts']
            )

            # Extract contract data
            contract_interface = compiled_sol['contracts']['ArbitrageV2.sol']['ArbitrageExecutorV2']
            abi = contract_interface['abi']
            bytecode = contract_interface['evm']['bytecode']['object']

            logger.info("✓ Contract compiled successfully")

            return {
                'abi': abi,
                'bytecode': bytecode
            }

        except Exception as e:
            logger.error(f"Compilation failed: {str(e)}")
            raise

    async def deploy(self, emergency_address: str = None) -> str:
        """
        Deploy ArbitrageV2 contract

        Args:
            emergency_address: Emergency withdrawal address (defaults to wallet address)

        Returns:
            Contract address
        """
        try:
            # Check if already deployed
            if self.chain in self.deployed_contracts:
                logger.warning(f"Contract already deployed on {self.chain}")
                existing = self.deployed_contracts[self.chain]['contract_address']
                logger.info(f"Existing contract: {existing}")

                response = input("Deploy new contract anyway? (yes/no): ")
                if response.lower() != 'yes':
                    return existing

            # Check connection
            if not self.w3.is_connected():
                raise Exception(f"Failed to connect to {self.chain} RPC")

            logger.info(f"✓ Connected to {self.chain}")

            # Check balance
            balance = self.w3.eth.get_balance(config.WALLET_ADDRESS)
            balance_eth = self.w3.from_wei(balance, 'ether')

            logger.info(f"✓ Wallet: {config.WALLET_ADDRESS}")
            logger.info(f"✓ Balance: {balance_eth:.4f} {self.chain_config['native_token']}")

            if balance == 0:
                raise Exception("Insufficient balance for deployment")

            # Compile contract
            contract_data = self.compile_contract()

            # Create contract instance
            contract = self.w3.eth.contract(
                abi=contract_data['abi'],
                bytecode=contract_data['bytecode']
            )

            # Use wallet address as emergency address if not provided
            if emergency_address is None:
                emergency_address = config.WALLET_ADDRESS

            logger.info(f"Emergency withdrawal address: {emergency_address}")

            # Estimate gas
            try:
                gas_estimate = contract.constructor(emergency_address).estimate_gas({
                    'from': config.WALLET_ADDRESS
                })
                logger.info(f"Estimated gas: {gas_estimate}")
            except Exception as e:
                logger.warning(f"Gas estimation failed: {str(e)}, using default")
                gas_estimate = 3000000

            # Get gas price
            gas_price = self.w3.eth.gas_price

            # Calculate deployment cost
            deployment_cost = self.w3.from_wei(gas_estimate * gas_price, 'ether')
            logger.info(f"Estimated cost: {deployment_cost:.6f} {self.chain_config['native_token']}")

            # Confirm deployment
            response = input("Proceed with deployment? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Deployment cancelled")
                return None

            # Build transaction
            transaction = contract.constructor(emergency_address).build_transaction({
                'from': config.WALLET_ADDRESS,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET_ADDRESS),
                'gas': gas_estimate,
                'gasPrice': gas_price,
                'chainId': self.chain_config['chain_id']
            })

            logger.info("Signing transaction...")

            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=config.PRIVATE_KEY
            )

            logger.info("Sending transaction...")

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            logger.info(f"Transaction sent: {tx_hash.hex()}")
            logger.info("Waiting for confirmation...")

            # Wait for receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if tx_receipt.status == 1:
                contract_address = tx_receipt.contractAddress

                logger.info("=" * 60)
                logger.info("✓ CONTRACT DEPLOYED SUCCESSFULLY!")
                logger.info("=" * 60)
                logger.info(f"Contract Address: {contract_address}")
                logger.info(f"Transaction Hash: {tx_hash.hex()}")
                logger.info(f"Block Number: {tx_receipt.blockNumber}")
                logger.info(f"Gas Used: {tx_receipt.gasUsed}")
                logger.info("=" * 60)

                # Save deployment
                self._save_deployment(self.chain, contract_address, tx_hash.hex())

                # Save ABI
                abi_file = f'deployed_contracts_v2_{self.chain}_abi.json'
                with open(abi_file, 'w') as f:
                    json.dump(contract_data['abi'], f, indent=2)
                logger.info(f"ABI saved to {abi_file}")

                return contract_address

            else:
                logger.error(f"Deployment failed! Status: {tx_receipt.status}")
                return None

        except Exception as e:
            logger.error(f"Deployment error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None


async def main():
    """Main deployment script"""
    import argparse

    parser = argparse.ArgumentParser(description='Deploy ArbitrageV2 Contract')
    parser.add_argument(
        '--chain',
        type=str,
        default='polygon',
        choices=['polygon', 'arbitrum', 'optimism', 'bsc', 'ethereum'],
        help='Chain to deploy to'
    )
    parser.add_argument(
        '--emergency-address',
        type=str,
        default=None,
        help='Emergency withdrawal address (defaults to wallet address)'
    )

    args = parser.parse_args()

    # Create deployer
    deployer = ArbitrageV2Deployer(chain=args.chain)

    # Deploy contract
    contract_address = await deployer.deploy(emergency_address=args.emergency_address)

    if contract_address:
        logger.info("\n" + "=" * 60)
        logger.info("NEXT STEPS:")
        logger.info("=" * 60)
        logger.info(f"1. Whitelist DEX routers:")
        logger.info(f"   python scripts/whitelist_setup.py --chain {args.chain}")
        logger.info(f"")
        logger.info(f"2. Test the contract:")
        logger.info(f"   python scripts/test_arbitrage_v2.py --chain {args.chain}")
        logger.info(f"")
        logger.info(f"3. Update bot to use ArbitrageV2:")
        logger.info(f"   Update contract_interface.py")
        logger.info("=" * 60)
    else:
        logger.error("Deployment failed!")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("ArbitrageV2 Deployment Script v2.0.0")
    asyncio.run(main())
