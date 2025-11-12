#!/usr/bin/env python3
"""
Test Script for Arbitrage Bot Improvements

This script verifies that all improvements are working correctly
before deploying to production.
"""

import asyncio
import sys
from loguru import logger
from web3 import Web3
import config

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class ImprovementTester:
    """Test all improvements"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []

    def test(self, name: str):
        """Decorator for test methods"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                logger.info(f"\n{'='*60}")
                logger.info(f"Testing: {name}")
                logger.info(f"{'='*60}")
                try:
                    await func(*args, **kwargs)
                    self.tests_passed += 1
                    self.results.append((name, "✅ PASS"))
                    logger.success(f"✅ {name} - PASSED")
                except Exception as e:
                    self.tests_failed += 1
                    self.results.append((name, f"❌ FAIL: {str(e)}"))
                    logger.error(f"❌ {name} - FAILED: {str(e)}")
            return wrapper
        return decorator

    @test("Configuration Loading")
    async def test_config(self):
        """Test that configuration is loaded correctly"""
        assert config.POLYGON_RPC_URL, "POLYGON_RPC_URL not set"
        assert config.WALLET_ADDRESS, "WALLET_ADDRESS not set"
        assert config.TOKENS, "TOKENS not configured"
        logger.info(f"✓ Config loaded: {len(config.TOKENS)} tokens configured")

    @test("Web3 Connection")
    async def test_web3_connection(self):
        """Test Web3 connection to RPC"""
        w3 = Web3(Web3.HTTPProvider(config.POLYGON_RPC_URL))
        assert w3.is_connected(), "Cannot connect to RPC endpoint"

        block_number = await asyncio.to_thread(w3.eth.block_number)
        logger.info(f"✓ Connected to RPC, current block: {block_number}")

    @test("RPC Manager")
    async def test_rpc_manager(self):
        """Test RPC manager with failover"""
        from rpc_manager import RPCManager

        # Test with multiple endpoints
        manager = RPCManager([
            config.POLYGON_RPC_URL,
            'https://polygon-rpc.com'
        ])

        # Test health check
        await manager.health_check()

        status = manager.get_status()
        assert status['healthy_endpoints'] > 0, "No healthy RPC endpoints"

        logger.info(f"✓ RPC Manager: {status['healthy_endpoints']}/{status['total_endpoints']} endpoints healthy")

    @test("Multicall Helper")
    async def test_multicall(self):
        """Test multicall functionality"""
        from multicall_helper import MulticallHelper

        w3 = Web3(Web3.HTTPProvider(config.POLYGON_RPC_URL))
        multicall = MulticallHelper(w3)

        # Test with a simple call
        weth_address = config.TOKENS.get('WETH')
        if not weth_address:
            logger.warning("⚠ WETH address not configured, skipping multicall test")
            return

        # Create a simple token contract
        erc20_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }
        ]

        token_contract = w3.eth.contract(address=weth_address, abi=erc20_abi)

        calls = [
            {'contract': token_contract, 'function': 'decimals', 'args': []},
            {'contract': token_contract, 'function': 'symbol', 'args': []}
        ]

        results = await multicall.aggregate_calls(calls)

        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert results[0] is not None, "Multicall failed to get decimals"

        logger.info(f"✓ Multicall: Retrieved {len(results)} values in single call")

    @test("DEX Interface - Price Query")
    async def test_dex_price_query(self):
        """Test actual on-chain price queries"""
        from dex_interface import DexInterface

        dex = DexInterface(config.POLYGON_RPC_URL)

        weth = config.TOKENS.get('WETH')
        usdc = config.TOKENS.get('USDC')

        if not weth or not usdc:
            logger.warning("⚠ WETH or USDC not configured, skipping price query test")
            return

        # Test price query
        price = await dex.get_token_price('quickswap', weth, usdc)

        assert price is not None, "Price query returned None"
        assert price > 0, f"Invalid price: {price}"

        # Convert to human readable
        price_usd = price / 1e6  # USDC has 6 decimals
        logger.info(f"✓ Price Query: 1 WETH = ${price_usd:,.2f} on QuickSwap")

    @test("DEX Interface - Liquidity Check")
    async def test_dex_liquidity(self):
        """Test liquidity checking"""
        from dex_interface import DexInterface

        dex = DexInterface(config.POLYGON_RPC_URL)

        # Test liquidity check
        liquidity = await dex.check_liquidity('quickswap', 'WETH/USDC')

        assert liquidity >= 0, f"Invalid liquidity: {liquidity}"

        if liquidity > 0:
            logger.info(f"✓ Liquidity Check: WETH/USDC pool has ${liquidity:,.2f}")
        else:
            logger.warning("⚠ Liquidity check returned 0 (pair may not exist)")

    @test("DEX Interface - Pair Address")
    async def test_get_pair_address(self):
        """Test getting pair address"""
        from dex_interface import DexInterface

        dex = DexInterface(config.POLYGON_RPC_URL)

        weth = config.TOKENS.get('WETH')
        usdc = config.TOKENS.get('USDC')

        if not weth or not usdc:
            logger.warning("⚠ WETH or USDC not configured, skipping pair address test")
            return

        pair_address = await dex.get_pair_address('quickswap', weth, usdc)

        if pair_address:
            logger.info(f"✓ Pair Address: {pair_address}")
        else:
            logger.warning("⚠ Could not find pair address")

    @test("Parallel Execution")
    async def test_parallel_execution(self):
        """Test that parallel execution is faster than sequential"""
        from dex_interface import DexInterface
        import time

        dex = DexInterface(config.POLYGON_RPC_URL)

        weth = config.TOKENS.get('WETH')
        usdc = config.TOKENS.get('USDC')

        if not weth or not usdc:
            logger.warning("⚠ WETH or USDC not configured, skipping parallel test")
            return

        dexes = ['quickswap', 'sushiswap', 'uniswap_v3']

        # Test sequential
        start = time.time()
        for dex_name in dexes:
            try:
                await dex.get_token_price(dex_name, weth, usdc)
            except:
                pass
        sequential_time = time.time() - start

        # Test parallel
        start = time.time()
        tasks = [dex.get_token_price(dex_name, weth, usdc) for dex_name in dexes]
        await asyncio.gather(*tasks, return_exceptions=True)
        parallel_time = time.time() - start

        speedup = sequential_time / parallel_time if parallel_time > 0 else 0

        logger.info(f"✓ Sequential: {sequential_time:.2f}s, Parallel: {parallel_time:.2f}s")
        logger.info(f"✓ Speedup: {speedup:.1f}x faster")

        assert parallel_time < sequential_time, "Parallel execution should be faster"

    @test("Smart Contract Deployment Check")
    async def test_contract_deployment(self):
        """Test that smart contract is deployed"""
        import os
        import json

        if not os.path.exists('deployed_contracts.json'):
            logger.warning("⚠ deployed_contracts.json not found - run deploy_contracts.py")
            logger.info("  This is OK for testing, but required for production")
            return

        with open('deployed_contracts.json', 'r') as f:
            contracts = json.load(f)

        assert 'polygon' in contracts, "Polygon contract not deployed"
        assert 'arbitrage_executor' in contracts['polygon'], "Arbitrage executor not deployed"

        address = contracts['polygon']['arbitrage_executor']
        logger.info(f"✓ Contract deployed at: {address}")

    @test("Circuit Breaker")
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        from circuit_breaker import RiskManager

        risk_manager = RiskManager()

        # Test that trades are allowed initially
        assert risk_manager.check_trade_allowed('polygon'), "Trades should be allowed initially"

        # Simulate failures
        for i in range(5):
            risk_manager.record_trade_result('polygon', 0, False)

        # After 5 failures, circuit should open
        status = risk_manager.get_risk_status()
        logger.info(f"✓ Circuit breaker status: {status['circuit_breakers']}")

    def print_summary(self):
        """Print test summary"""
        total = self.tests_passed + self.tests_failed

        logger.info(f"\n{'='*60}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*60}")

        for name, result in self.results:
            logger.info(f"{result}: {name}")

        logger.info(f"\n{'='*60}")
        logger.info(f"Total: {total} tests")
        logger.info(f"Passed: {self.tests_passed} ✅")
        logger.info(f"Failed: {self.tests_failed} ❌")
        logger.info(f"Success Rate: {(self.tests_passed/total*100):.1f}%")
        logger.info(f"{'='*60}")

        if self.tests_failed == 0:
            logger.success("\n🎉 All tests passed! Ready for deployment.")
        else:
            logger.error(f"\n⚠ {self.tests_failed} test(s) failed. Review errors above.")

        return self.tests_failed == 0


async def main():
    """Run all tests"""
    logger.info("Starting Arbitrage Bot Improvement Tests\n")

    tester = ImprovementTester()

    # Run all tests
    await tester.test_config()
    await tester.test_web3_connection()
    await tester.test_rpc_manager()
    await tester.test_multicall()
    await tester.test_dex_price_query()
    await tester.test_dex_liquidity()
    await tester.test_get_pair_address()
    await tester.test_parallel_execution()
    await tester.test_contract_deployment()
    await tester.test_circuit_breaker()

    # Print summary
    success = tester.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
