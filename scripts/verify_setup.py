"""
Verify Setup Script
Check that everything is ready for deployment
"""

import os
import sys
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    logger.info(f"{status} {description}: {filepath}")
    return exists


def check_env_variable(var_name: str, required: bool = True) -> bool:
    """Check if environment variable is set"""
    try:
        import config
        value = getattr(config, var_name, None)

        if value and value != "":
            logger.info(f"✅ {var_name}: {'*' * 10} (set)")
            return True
        else:
            if required:
                logger.error(f"❌ {var_name}: NOT SET (required!)")
            else:
                logger.warning(f"⚠️  {var_name}: NOT SET (optional)")
            return not required
    except Exception as e:
        logger.error(f"❌ Error checking {var_name}: {str(e)}")
        return False


def verify_setup():
    """Verify complete setup"""
    logger.info("=" * 60)
    logger.info("VERIFYING SETUP FOR ARBITRAGE BOT")
    logger.info("=" * 60)

    all_checks = []

    # ============================================
    # 1. Check Core Files
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("1. CORE FILES")
    logger.info("=" * 60)

    core_files = {
        'config.py': 'Configuration file',
        'arbitrage_bot.py': 'Main bot file',
        'dex_interface.py': 'DEX interface',
        'multi_chain_bot.py': 'Multi-chain orchestrator',
        'contracts/Arbitrage.sol': 'Original contract (vulnerable)',
        'contracts/ArbitrageV2.sol': 'Secure contract (use this!)',
    }

    for filepath, description in core_files.items():
        all_checks.append(check_file_exists(filepath, description))

    # ============================================
    # 2. Check Scripts
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("2. DEPLOYMENT SCRIPTS")
    logger.info("=" * 60)

    scripts = {
        'scripts/deploy_arbitrage_v2.py': 'Deployment script',
        'scripts/whitelist_setup.py': 'Whitelist setup',
        'scripts/test_arbitrage_v2.py': 'Test script',
        'contract_interface_v2.py': 'Contract interface V2',
    }

    for filepath, description in scripts.items():
        all_checks.append(check_file_exists(filepath, description))

    # ============================================
    # 3. Check Documentation
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("3. DOCUMENTATION")
    logger.info("=" * 60)

    docs = {
        'SECURITY_ANALYSIS.md': 'Security audit',
        'SECURITY_IMPLEMENTATION_GUIDE.md': 'Implementation guide',
        'IMPLEMENTATION_QUICK_START.md': 'Quick start guide',
        'FINAL_DEPLOYMENT_GUIDE.md': 'Deployment guide',
        'REQUIRED_VS_OPTIONAL.md': 'Requirements guide',
    }

    for filepath, description in docs.items():
        all_checks.append(check_file_exists(filepath, description))

    # ============================================
    # 4. Check Environment Variables
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("4. ENVIRONMENT VARIABLES")
    logger.info("=" * 60)

    logger.info("\n✅ Required Variables:")
    all_checks.append(check_env_variable('WALLET_ADDRESS', required=True))
    all_checks.append(check_env_variable('PRIVATE_KEY', required=True))
    all_checks.append(check_env_variable('POLYGON_RPC_URL', required=True))

    logger.info("\n⚠️  Optional Variables (for multi-chain):")
    check_env_variable('ARBITRUM_RPC_URL', required=False)
    check_env_variable('OPTIMISM_RPC_URL', required=False)
    check_env_variable('BSC_RPC_URL', required=False)

    logger.info("\n⚠️  Optional Variables (CEX - not needed for DEX-only):")
    check_env_variable('BINANCE_API_KEY', required=False)
    check_env_variable('OKX_API_KEY', required=False)

    # ============================================
    # 5. Check Python Dependencies
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("5. PYTHON DEPENDENCIES")
    logger.info("=" * 60)

    required_packages = [
        'web3',
        'loguru',
        'asyncio',
        'solcx',
        'ccxt',
    ]

    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package}: installed")
            all_checks.append(True)
        except ImportError:
            logger.error(f"❌ {package}: NOT INSTALLED")
            all_checks.append(False)

    # ============================================
    # 6. Check Deployments
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("6. CONTRACT DEPLOYMENTS")
    logger.info("=" * 60)

    if os.path.exists('deployed_contracts_v2.json'):
        logger.info("✅ deployed_contracts_v2.json found")

        import json
        with open('deployed_contracts_v2.json', 'r') as f:
            deployments = json.load(f)

        logger.info(f"\nDeployed chains:")
        for chain, info in deployments.items():
            logger.info(f"  ✅ {chain}: {info['contract_address']}")
    else:
        logger.warning("⚠️  deployed_contracts_v2.json NOT FOUND")
        logger.warning("   Run: python scripts/deploy_arbitrage_v2.py --chain polygon")

    # ============================================
    # Summary
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("SETUP VERIFICATION SUMMARY")
    logger.info("=" * 60)

    passed = sum(all_checks)
    total = len(all_checks)
    success_rate = (passed / total * 100) if total > 0 else 0

    logger.info(f"Checks Passed: {passed}/{total} ({success_rate:.1f}%)")

    if passed == total:
        logger.info("\n🎉 ALL CHECKS PASSED!")
        logger.info("\nYou are ready to deploy ArbitrageV2!")
        logger.info("\nNext steps:")
        logger.info("1. Read: IMPLEMENTATION_QUICK_START.md")
        logger.info("2. Deploy: python scripts/deploy_arbitrage_v2.py --chain polygon")
        logger.info("3. Setup: python scripts/whitelist_setup.py --chain polygon")
        logger.info("4. Test: python scripts/test_arbitrage_v2.py --chain polygon")
        return True
    else:
        logger.error("\n⚠️  SOME CHECKS FAILED!")
        logger.error(f"\nFailed: {total - passed} checks")
        logger.error("\nFix the issues above before deploying.")

        if not check_file_exists('.env', 'Environment file'):
            logger.error("\nMissing .env file!")
            logger.error("Run: cp .env.example .env")
            logger.error("Then edit .env with your configuration")

        return False


if __name__ == "__main__":
    logger.info("Setup Verification Script v2.0.0\n")

    success = verify_setup()

    if not success:
        sys.exit(1)
