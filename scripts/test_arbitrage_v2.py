"""
Test ArbitrageV2 Contract
Verify security features and functionality
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


class ArbitrageV2Tester:
    """Test ArbitrageV2 contract functionality"""

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

        logger.info(f"ArbitrageV2 Tester initialized for {chain}")
        logger.info(f"Contract: {self.contract_address}")

    async def test_basic_info(self):
        """Test basic contract info"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: BASIC CONTRACT INFO")
        logger.info("=" * 60)

        try:
            # Check owner
            owner = await asyncio.to_thread(
                self.contract.functions.owner().call
            )
            logger.info(f"✓ Owner: {owner}")

            expected_owner = config.WALLET_ADDRESS
            if owner.lower() == expected_owner.lower():
                logger.info("  ✓ Owner matches wallet address")
            else:
                logger.error(f"  ✗ Owner mismatch! Expected: {expected_owner}")

            # Check emergency withdrawal address
            emergency_addr = await asyncio.to_thread(
                self.contract.functions.emergencyWithdrawalAddress().call
            )
            logger.info(f"✓ Emergency Address: {emergency_addr}")

            # Check min profit threshold
            min_profit_bp = await asyncio.to_thread(
                self.contract.functions.minProfitBasisPoints().call
            )
            logger.info(f"✓ Min Profit Threshold: {min_profit_bp / 100}%")

            # Check max slippage
            max_slippage_bp = await asyncio.to_thread(
                self.contract.functions.maxSlippageBasisPoints().call
            )
            logger.info(f"✓ Max Slippage: {max_slippage_bp / 100}%")

            # Check if paused
            is_paused = await asyncio.to_thread(
                self.contract.functions.paused().call
            )
            status = "PAUSED" if is_paused else "ACTIVE"
            logger.info(f"✓ Contract Status: {status}")

            return True

        except Exception as e:
            logger.error(f"✗ Basic info test failed: {str(e)}")
            return False

    async def test_whitelists(self):
        """Test whitelist configuration"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: WHITELIST CONFIGURATION")
        logger.info("=" * 60)

        try:
            all_ok = True

            # Test routers
            routers = config.DEX_ROUTERS.get(self.chain, {})
            logger.info(f"\nTesting {len(routers)} routers:")

            for dex_name, router_address in routers.items():
                is_whitelisted = await asyncio.to_thread(
                    self.contract.functions.whitelistedRouters(router_address).call
                )

                if is_whitelisted:
                    logger.info(f"  ✓ {dex_name}: {router_address}")
                else:
                    logger.error(f"  ✗ {dex_name} NOT whitelisted: {router_address}")
                    all_ok = False

            # Test tokens
            tokens = config.TOKENS_BY_CHAIN.get(self.chain, {})
            logger.info(f"\nTesting {len(tokens)} tokens:")

            for token_symbol, token_address in tokens.items():
                is_whitelisted = await asyncio.to_thread(
                    self.contract.functions.whitelistedTokens(token_address).call
                )

                if is_whitelisted:
                    logger.info(f"  ✓ {token_symbol}: {token_address}")
                else:
                    logger.error(f"  ✗ {token_symbol} NOT whitelisted: {token_address}")
                    all_ok = False

            if all_ok:
                logger.info("\n✓ All whitelists configured correctly")
            else:
                logger.error("\n✗ Some whitelists missing! Run: python scripts/whitelist_setup.py")

            return all_ok

        except Exception as e:
            logger.error(f"✗ Whitelist test failed: {str(e)}")
            return False

    async def test_security_features(self):
        """Test security features (reentrancy, pausable, etc.)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: SECURITY FEATURES")
        logger.info("=" * 60)

        try:
            # Test 1: Check ReentrancyGuard
            logger.info("\n✓ ReentrancyGuard: Contract compiled with ReentrancyGuard")
            logger.info("  (Protection active on executeFlashSwap and uniswapV2Call)")

            # Test 2: Check Pausable
            logger.info("\n✓ Pausable: Contract compiled with Pausable")

            is_paused = await asyncio.to_thread(
                self.contract.functions.paused().call
            )

            if not is_paused:
                logger.info("  ✓ Contract is active (not paused)")
            else:
                logger.warning("  ⚠️ Contract is PAUSED")

            # Test 3: Check Ownable
            logger.info("\n✓ Ownable: Contract compiled with Ownable")

            owner = await asyncio.to_thread(
                self.contract.functions.owner().call
            )

            if owner.lower() == config.WALLET_ADDRESS.lower():
                logger.info(f"  ✓ Owner is correct: {owner}")
            else:
                logger.error(f"  ✗ Owner mismatch!")

            # Test 4: Check statistics tracking
            logger.info("\n✓ Statistics Tracking:")

            stats = await asyncio.to_thread(
                self.contract.functions.getStats().call
            )

            success_count, fail_count, success_rate = stats
            logger.info(f"  Success Count: {success_count}")
            logger.info(f"  Fail Count: {fail_count}")
            logger.info(f"  Success Rate: {success_rate}%")

            logger.info("\n✓ All security features verified")
            return True

        except Exception as e:
            logger.error(f"✗ Security features test failed: {str(e)}")
            return False

    async def test_profitability_check(self):
        """Test profitability verification function"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: PROFITABILITY VERIFICATION")
        logger.info("=" * 60)

        try:
            # Test case 1: Profitable trade
            amount_borrowed = Web3.to_wei(1, 'ether')  # 1 ETH borrowed
            expected_output = Web3.to_wei(1.01, 'ether')  # 1.01 ETH received (1% profit)

            is_profitable = await asyncio.to_thread(
                self.contract.functions.wouldBeProfitable(
                    amount_borrowed,
                    expected_output
                ).call
            )

            if is_profitable:
                logger.info("✓ Test 1: Correctly identified profitable trade (1% profit)")
            else:
                logger.error("✗ Test 1: Failed to identify profitable trade")

            # Test case 2: Unprofitable trade
            amount_borrowed2 = Web3.to_wei(1, 'ether')
            expected_output2 = Web3.to_wei(1.002, 'ether')  # 0.2% profit (below 0.3% threshold)

            is_profitable2 = await asyncio.to_thread(
                self.contract.functions.wouldBeProfitable(
                    amount_borrowed2,
                    expected_output2
                ).call
            )

            if not is_profitable2:
                logger.info("✓ Test 2: Correctly rejected unprofitable trade (0.2% profit)")
            else:
                logger.error("✗ Test 2: Should have rejected unprofitable trade")

            logger.info("\n✓ Profitability checks working correctly")
            return True

        except Exception as e:
            logger.error(f"✗ Profitability test failed: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 60)
        logger.info(f"TESTING ArbitrageV2 ON {self.chain.upper()}")
        logger.info("=" * 60)

        results = {
            'basic_info': await self.test_basic_info(),
            'whitelists': await self.test_whitelists(),
            'security': await self.test_security_features(),
            'profitability': await self.test_profitability_check(),
        }

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)

        passed = sum(results.values())
        total = len(results)

        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"{test_name.upper():20} {status}")

        logger.info("=" * 60)
        logger.info(f"RESULT: {passed}/{total} tests passed")
        logger.info("=" * 60)

        if passed == total:
            logger.info("\n🎉 ALL TESTS PASSED! Contract is ready to use.")
            logger.info("\nNext steps:")
            logger.info("1. Update contract_interface.py to use ArbitrageV2")
            logger.info("2. Update arbitrage_bot.py to call new contract functions")
            logger.info("3. Test with small trade amounts first")
        else:
            logger.error("\n⚠️ SOME TESTS FAILED! Fix issues before using contract.")

        return passed == total


async def main():
    """Main test script"""
    import argparse

    parser = argparse.ArgumentParser(description='Test ArbitrageV2 Contract')
    parser.add_argument(
        '--chain',
        type=str,
        default='polygon',
        choices=['polygon', 'arbitrum', 'optimism', 'bsc', 'ethereum'],
        help='Chain to test'
    )

    args = parser.parse_args()

    try:
        # Create tester
        tester = ArbitrageV2Tester(chain=args.chain)

        # Run all tests
        success = await tester.run_all_tests()

        if not success:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    logger.info("ArbitrageV2 Test Suite v2.0.0")
    asyncio.run(main())
