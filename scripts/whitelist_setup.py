"""
Whitelist Setup Script
Configure ArbitrageV2 contract with trusted routers and tokens
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from web3 import Web3
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class WhitelistSetup:
    """Setup whitelists for ArbitrageV2 contract"""

    def __init__(self, chain: str):
        self.chain = chain

        # Get absolute paths from current directory to avoid Docker mount issues
        base_dir = Path(__file__).parent.parent
        self.deployment_file = (base_dir / 'deployed_contracts_v2.json').resolve()
        self.abi_file = (base_dir / f'deployed_contracts_v2_{chain}_abi.json').resolve()

        # Validate deployment file exists and is a file (not directory)
        self._validate_deployment_file()

        # Load ABI
        self.contract_abi = self._load_abi()

        # Initialize Web3
        chain_config = config.SUPPORTED_CHAINS.get(chain)
        if not chain_config:
            raise ValueError(f"Unsupported chain: {chain}")
        
        self.w3 = Web3(Web3.HTTPProvider(chain_config['rpc']))
        self.chain_config = chain_config

        # CRITICAL: Convert wallet address to checksum format
        self.wallet_address = Web3.to_checksum_address(config.WALLET_ADDRESS)
        self.private_key = config.PRIVATE_KEY

        # Load deployment info
        self.deployed_contracts = self._load_deployments()
        self.contract_address = self.deployed_contracts[chain]['contract_address']
        self.contract_address = Web3.to_checksum_address(self.contract_address)

        # Create contract instance
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )

        logger.info(f"WhitelistSetup initialized for {chain}")
        logger.info(f"Contract: {self.contract_address}")

    def _validate_deployment_file(self):
        """Ensure deployment file exists and is valid"""
        if not self.deployment_file.exists():
            raise FileNotFoundError(
                f"Deployment file not found: {self.deployment_file}\n"
                f"Run deploy_arbitrage_v2.py first!"
            )
        
        # CRITICAL: Check if it's a directory (common Docker mount issue)
        if self.deployment_file.is_dir():
            raise IsADirectoryError(
                f"CRITICAL ERROR: {self.deployment_file} is a directory!\n"
                f"Remove it and create a proper JSON file."
            )

    def _load_deployments(self) -> dict:
        """Load existing contract deployments with validation"""
        try:
            with open(self.deployment_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    logger.warning(f"{self.deployment_file} is empty")
                    return {}
                data = json.loads(content)
                
                # Validate chain data exists
                if self.chain not in data:
                    raise KeyError(f"No deployment found for {self.chain}")
                
                # Validate required fields
                required_fields = ['contract_address', 'tx_hash', 'chain_id']
                for field in required_fields:
                    if field not in data[self.chain]:
                        raise KeyError(f"Missing required field '{field}' for {self.chain}")
                
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.deployment_file}: {str(e)}")
            raise

    def _load_abi(self) -> list:
        """Load ABI file with validation"""
        if not self.abi_file.exists():
            raise FileNotFoundError(
                f"ABI file not found: {self.abi_file}\n"
                f"This should be created during deployment!"
            )
        
        # CRITICAL: Check if it's a directory
        if self.abi_file.is_dir():
            raise IsADirectoryError(
                f"CRITICAL ERROR: {self.abi_file} is a directory!\n"
                f"Remove it and create a proper JSON file."
            )
        
        try:
            with open(self.abi_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.abi_file}: {str(e)}")
            raise

    async def whitelist_routers(self):
        """Whitelist all DEX routers for this chain"""
        logger.info(f"Whitelisting routers for {self.chain}...")
        
        # CRITICAL: Validate config exists
        if not hasattr(config, 'DEX_ROUTERS'):
            raise AttributeError("config.py missing DEX_ROUTERS dictionary")
        
        routers = config.DEX_ROUTERS.get(self.chain, {})
        if not routers:
            logger.warning(f"No routers configured for {self.chain}")
            return

        for dex_name, router_address in routers.items():
            # Validate router address format
            try:
                router_address = Web3.to_checksum_address(router_address)
                await self._whitelist_router(dex_name, router_address)
            except Exception as e:
                logger.error(f"Invalid router address {router_address}: {str(e)}")

        logger.info(f"✓ All routers whitelisted for {self.chain}")

    async def _whitelist_router(self, dex_name: str, router_address: str):
        """Whitelist a single router"""
        try:
            logger.info(f"Whitelisting {dex_name}: {router_address}")

            # Check if already whitelisted
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedRouters(router_address).call
            )

            if is_whitelisted:
                logger.info(f"  ✓ {dex_name} already whitelisted")
                return

            # Build transaction
            tx = self.contract.functions.whitelistRouter(
                router_address,
                True
            ).build_transaction({
                'from': self.wallet_address,  # Use checksum address
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_config['chain_id']
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            logger.info(f"  Transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = await asyncio.to_thread(
                self.w3.eth.wait_for_transaction_receipt,
                tx_hash,
                timeout=120
            )

            if receipt.status == 1:
                logger.info(f"  ✓ {dex_name} whitelisted successfully")
            else:
                logger.error(f"  ✗ Failed to whitelist {dex_name}")
                # Log more details
                logger.error(f"    Gas used: {receipt.gasUsed}")
                logger.error(f"    Cumulative gas used: {receipt.cumulativeGasUsed}")

        except Exception as e:
            logger.error(f"Error whitelisting {dex_name}: {str(e)}")
            # Log full traceback for debugging
            import traceback
            logger.error(traceback.format_exc())

    async def whitelist_tokens(self):
        """Whitelist all tokens for this chain"""
        logger.info(f"Whitelisting tokens for {self.chain}...")
        
        # CRITICAL: Validate config exists
        if not hasattr(config, 'TOKENS_BY_CHAIN'):
            raise AttributeError("config.py missing TOKENS_BY_CHAIN dictionary")
        
        tokens = config.TOKENS_BY_CHAIN.get(self.chain, {})
        if not tokens:
            logger.warning(f"No tokens configured for {self.chain}")
            return

        for token_symbol, token_address in tokens.items():
            # Validate token address format
            try:
                token_address = Web3.to_checksum_address(token_address)
                await self._whitelist_token(token_symbol, token_address)
            except Exception as e:
                logger.error(f"Invalid token address {token_address}: {str(e)}")

        logger.info(f"✓ All tokens whitelisted for {self.chain}")

    async def _whitelist_token(self, token_symbol: str, token_address: str):
        """Whitelist a single token"""
        try:
            logger.info(f"Whitelisting {token_symbol}: {token_address}")

            # Check if already whitelisted
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedTokens(token_address).call
            )

            if is_whitelisted:
                logger.info(f"  ✓ {token_symbol} already whitelisted")
                return

            # Build transaction
            tx = self.contract.functions.whitelistToken(
                token_address,
                True
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_config['chain_id']
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            logger.info(f"  Transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = await asyncio.to_thread(
                self.w3.eth.wait_for_transaction_receipt,
                tx_hash,
                timeout=120
            )

            if receipt.status == 1:
                logger.info(f"  ✓ {token_symbol} whitelisted successfully")
            else:
                logger.error(f"  ✗ Failed to whitelist {token_symbol}")
                logger.error(f"    Gas used: {receipt.gasUsed}")

            # Small delay between transactions to avoid rate limits
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error whitelisting {token_symbol}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    async def verify_setup(self):
        """Verify whitelist setup"""
        logger.info("=" * 60)
        logger.info("VERIFYING WHITELIST SETUP")
        logger.info("=" * 60)

        # Check routers
        routers = config.DEX_ROUTERS.get(self.chain, {})
        logger.info(f"\nRouters ({len(routers)}):")
        for dex_name, router_address in routers.items():
            router_address = Web3.to_checksum_address(router_address)
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedRouters(router_address).call
            )
            status = "✓" if is_whitelisted else "✗"
            logger.info(f"  {status} {dex_name}: {router_address}")

        # Check tokens
        tokens = config.TOKENS_BY_CHAIN.get(self.chain, {})
        logger.info(f"\nTokens ({len(tokens)}):")
        for token_symbol, token_address in tokens.items():
            token_address = Web3.to_checksum_address(token_address)
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedTokens(token_address).call
            )
            status = "✓" if is_whitelisted else "✗"
            logger.info(f"  {status} {token_symbol}: {token_address}")

        logger.info("=" * 60)

    async def setup_all(self):
        """Run complete setup"""
        logger.info("=" * 60)
        logger.info(f"SETTING UP WHITELISTS FOR {self.chain.upper()}")
        logger.info("=" * 60)

        # Pre-flight checks
        if not self.w3.is_connected():
            raise Exception(f"Failed to connect to {self.chain} RPC")

        logger.info(f"✓ Connected to {self.chain}")
        logger.info(f"✓ Contract: {self.contract_address}")
        logger.info(f"✓ Wallet: {self.wallet_address}")

        # Whitelist routers
        await self.whitelist_routers()

        # Small delay
        await asyncio.sleep(5)

        # Whitelist tokens
        await self.whitelist_tokens()

        # Verify
        await asyncio.sleep(5)
        await self.verify_setup()

        logger.info("\n✓ Whitelist setup complete!")


async def main():
    """Main setup script"""
    import argparse

    parser = argparse.ArgumentParser(description='Setup ArbitrageV2 Whitelists')
    parser.add_argument(
        '--chain',
        type=str,
        default='polygon',
        choices=['polygon', 'arbitrum', 'optimism', 'bsc', 'ethereum'],
        help='Chain to setup'
    )
    parser.add_argument(
        '--routers-only',
        action='store_true',
        help='Only whitelist routers'
    )
    parser.add_argument(
        '--tokens-only',
        action='store_true',
        help='Only whitelist tokens'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify whitelists'
    )

    args = parser.parse_args()

    try:
        # Create setup instance
        setup = WhitelistSetup(chain=args.chain)

        if args.verify_only:
            await setup.verify_setup()
        elif args.routers_only:
            await setup.whitelist_routers()
            await asyncio.sleep(5)
            await setup.verify_setup()
        elif args.tokens_only:
            await setup.whitelist_tokens()
            await asyncio.sleep(5)
            await setup.verify_setup()
        else:
            await setup.setup_all()

        logger.info("\n" + "=" * 60)
        logger.info("NEXT STEPS:")
        logger.info("=" * 60)
        logger.info(f"1. Test the contract:")
        logger.info(f"   python scripts/test_arbitrage_v2.py --chain {args.chain}")
        logger.info(f"")
        logger.info(f"2. Update bot to use new contract")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    logger.info("ArbitrageV2 Whitelist Setup v2.0.0")
    asyncio.run(main())
