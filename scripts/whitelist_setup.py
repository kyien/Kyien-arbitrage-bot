"""
Whitelist Setup Script
Configure ArbitrageV2 contract with trusted routers and tokens
"""

import asyncio
import json
import os
import sys
from web3 import Web3
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class WhitelistSetup:
    """Setup whitelists for ArbitrageV2 contract"""

    def __init__(self, chain: str):
        self.chain = chain

        # Load deployment info
        deployment_file = 'deployed_contracts_v2.json'
        if not os.path.exists(deployment_file):
            raise Exception(f"Deployment file not found: {deployment_file}")

        with open(deployment_file, 'r') as f:
            deployments = json.load(f)

        if chain not in deployments:
            raise Exception(f"No deployment found for {chain}")

        self.contract_address = deployments[chain]['contract_address']

        # Load ABI
        abi_file = f'deployed_contracts_v2_{chain}_abi.json'
        if not os.path.exists(abi_file):
            raise Exception(f"ABI file not found: {abi_file}")

        with open(abi_file, 'r') as f:
            self.contract_abi = json.load(f)

        # Initialize Web3
        chain_config = config.SUPPORTED_CHAINS.get(chain)
        self.w3 = Web3(Web3.HTTPProvider(chain_config['rpc']))
        self.chain_config = chain_config

        # Create contract instance
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )

        logger.info(f"WhitelistSetup initialized for {chain}")
        logger.info(f"Contract: {self.contract_address}")

    async def whitelist_routers(self):
        """Whitelist all DEX routers for this chain"""
        logger.info(f"Whitelisting routers for {self.chain}...")

        routers = config.DEX_ROUTERS.get(self.chain, {})

        if not routers:
            logger.warning(f"No routers configured for {self.chain}")
            return

        for dex_name, router_address in routers.items():
            await self._whitelist_router(dex_name, router_address)

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
                'from': config.WALLET_ADDRESS,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET_ADDRESS),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_config['chain_id']
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, config.PRIVATE_KEY)
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

        except Exception as e:
            logger.error(f"Error whitelisting {dex_name}: {str(e)}")

    async def whitelist_tokens(self):
        """Whitelist all tokens for this chain"""
        logger.info(f"Whitelisting tokens for {self.chain}...")

        tokens = config.TOKENS_BY_CHAIN.get(self.chain, {})

        if not tokens:
            logger.warning(f"No tokens configured for {self.chain}")
            return

        for token_symbol, token_address in tokens.items():
            await self._whitelist_token(token_symbol, token_address)

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
                'from': config.WALLET_ADDRESS,
                'nonce': self.w3.eth.get_transaction_count(config.WALLET_ADDRESS),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_config['chain_id']
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, config.PRIVATE_KEY)
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

            # Small delay between transactions
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error whitelisting {token_symbol}: {str(e)}")

    async def verify_setup(self):
        """Verify whitelist setup"""
        logger.info("=" * 60)
        logger.info("VERIFYING WHITELIST SETUP")
        logger.info("=" * 60)

        # Check routers
        routers = config.DEX_ROUTERS.get(self.chain, {})
        logger.info(f"\nRouters ({len(routers)}):")
        for dex_name, router_address in routers.items():
            is_whitelisted = await asyncio.to_thread(
                self.contract.functions.whitelistedRouters(router_address).call
            )
            status = "✓" if is_whitelisted else "✗"
            logger.info(f"  {status} {dex_name}: {router_address}")

        # Check tokens
        tokens = config.TOKENS_BY_CHAIN.get(self.chain, {})
        logger.info(f"\nTokens ({len(tokens)}):")
        for token_symbol, token_address in tokens.items():
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
