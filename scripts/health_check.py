#!/usr/bin/env python3
"""
Health Check Script for Arbitrage Bot
Monitors bot health and returns exit code for Docker/systemd health checks
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Health checker for arbitrage bot

    Checks:
    - Heartbeat file (bot is running)
    - RPC connectivity
    - Gas balance
    - Memory usage
    - Disk space
    - Log file growth (bot is active)
    """

    def __init__(self):
        """Initialize health checker"""
        self.health_file = Path("/tmp/arbitrage-bot-health.json")
        self.log_dir = Path(os.getenv('LOG_DIR', '/var/log/arbitrage-bot'))
        self.heartbeat_timeout = 300  # 5 minutes
        self.min_gas_balance = float(os.getenv('MIN_GAS_BALANCE_USD', '10'))
        self.max_memory_percent = 90
        self.min_disk_space_gb = 5

        self.checks = {
            'heartbeat': False,
            'rpc_connectivity': False,
            'gas_balance': False,
            'memory': False,
            'disk_space': False,
            'log_activity': False
        }

    def check_heartbeat(self) -> bool:
        """
        Check if bot heartbeat is recent

        Returns:
            True if heartbeat is within timeout period
        """
        try:
            if not self.health_file.exists():
                if LOGURU_AVAILABLE:
                    logger.warning("Health file not found - bot may not be running")
                return False

            with open(self.health_file, 'r') as f:
                health_data = json.load(f)

            last_heartbeat = datetime.fromisoformat(health_data.get('last_heartbeat', '1970-01-01'))
            age_seconds = (datetime.now() - last_heartbeat).total_seconds()

            if age_seconds > self.heartbeat_timeout:
                if LOGURU_AVAILABLE:
                    logger.error(f"Heartbeat too old: {age_seconds:.0f}s (max: {self.heartbeat_timeout}s)")
                return False

            return True

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Heartbeat check failed: {str(e)}")
            return False

    def check_rpc_connectivity(self) -> bool:
        """
        Check RPC connectivity

        Returns:
            True if at least one RPC is reachable
        """
        try:
            if not self.health_file.exists():
                return False

            with open(self.health_file, 'r') as f:
                health_data = json.load(f)

            rpc_status = health_data.get('rpc_status', {})

            # At least one chain RPC should be connected
            connected = any(status == 'connected' for status in rpc_status.values())

            if not connected and LOGURU_AVAILABLE:
                logger.error("No RPC endpoints connected")

            return connected

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"RPC check failed: {str(e)}")
            return False

    def check_gas_balance(self) -> bool:
        """
        Check gas balance on all chains

        Returns:
            True if all active chains have sufficient gas
        """
        try:
            if not self.health_file.exists():
                return False

            with open(self.health_file, 'r') as f:
                health_data = json.load(f)

            gas_balances = health_data.get('gas_balances', {})

            if not gas_balances:
                # No gas balance data yet
                return True

            # Check each chain
            low_balance_chains = []
            for chain, balance_usd in gas_balances.items():
                if balance_usd < self.min_gas_balance:
                    low_balance_chains.append(f"{chain}: ${balance_usd:.2f}")

            if low_balance_chains:
                if LOGURU_AVAILABLE:
                    logger.error(f"Low gas balance: {', '.join(low_balance_chains)}")
                return False

            return True

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Gas balance check failed: {str(e)}")
            return True  # Don't fail health check on gas balance error

    def check_memory_usage(self) -> bool:
        """
        Check memory usage

        Returns:
            True if memory usage is acceptable
        """
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent > self.max_memory_percent:
                if LOGURU_AVAILABLE:
                    logger.error(f"High memory usage: {memory_percent:.1f}%")
                return False

            return True

        except ImportError:
            # psutil not available, skip check
            return True
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Memory check failed: {str(e)}")
            return True

    def check_disk_space(self) -> bool:
        """
        Check available disk space

        Returns:
            True if sufficient disk space available
        """
        try:
            import psutil

            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)

            if free_gb < self.min_disk_space_gb:
                if LOGURU_AVAILABLE:
                    logger.error(f"Low disk space: {free_gb:.1f}GB")
                return False

            return True

        except ImportError:
            # psutil not available, skip check
            return True
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Disk space check failed: {str(e)}")
            return True

    def check_log_activity(self) -> bool:
        """
        Check if log files are being written to (bot is active)

        Returns:
            True if recent log activity detected
        """
        try:
            if not self.log_dir.exists():
                return True  # Log dir not created yet

            bot_log = self.log_dir / 'bot.log'

            if not bot_log.exists():
                return True  # Log file not created yet

            # Check if log was modified in last 10 minutes
            last_modified = datetime.fromtimestamp(bot_log.stat().st_mtime)
            age_seconds = (datetime.now() - last_modified).total_seconds()

            if age_seconds > 600:  # 10 minutes
                if LOGURU_AVAILABLE:
                    logger.warning(f"Log file not updated in {age_seconds:.0f}s")
                return False

            return True

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Log activity check failed: {str(e)}")
            return True

    def run_all_checks(self) -> dict:
        """
        Run all health checks

        Returns:
            Dictionary with check results
        """
        self.checks['heartbeat'] = self.check_heartbeat()
        self.checks['rpc_connectivity'] = self.check_rpc_connectivity()
        self.checks['gas_balance'] = self.check_gas_balance()
        self.checks['memory'] = self.check_memory_usage()
        self.checks['disk_space'] = self.check_disk_space()
        self.checks['log_activity'] = self.check_log_activity()

        return self.checks

    def is_healthy(self) -> bool:
        """
        Check if bot is healthy

        Returns:
            True if all critical checks pass
        """
        results = self.run_all_checks()

        # Critical checks (must pass)
        critical_checks = ['heartbeat', 'rpc_connectivity', 'disk_space']

        for check in critical_checks:
            if not results.get(check, False):
                return False

        return True

    def get_health_summary(self) -> dict:
        """
        Get health summary

        Returns:
            Dictionary with health summary
        """
        is_healthy = self.is_healthy()

        return {
            'healthy': is_healthy,
            'timestamp': datetime.now().isoformat(),
            'checks': self.checks,
            'passed': sum(1 for v in self.checks.values() if v),
            'total': len(self.checks)
        }


def update_heartbeat(
    rpc_status: dict = None,
    gas_balances: dict = None,
    trade_count: int = 0,
    error_count: int = 0
):
    """
    Update heartbeat file (called by bot)

    Args:
        rpc_status: Dictionary of RPC statuses by chain
        gas_balances: Dictionary of gas balances by chain (in USD)
        trade_count: Number of trades executed
        error_count: Number of errors encountered
    """
    health_file = Path("/tmp/arbitrage-bot-health.json")

    health_data = {
        'last_heartbeat': datetime.now().isoformat(),
        'rpc_status': rpc_status or {},
        'gas_balances': gas_balances or {},
        'trade_count': trade_count,
        'error_count': error_count,
        'pid': os.getpid()
    }

    try:
        with open(health_file, 'w') as f:
            json.dump(health_data, f, indent=2)
    except Exception as e:
        if LOGURU_AVAILABLE:
            logger.error(f"Failed to update heartbeat: {str(e)}")


def main():
    """
    Main health check function

    Exit codes:
    0 = Healthy
    1 = Unhealthy
    """
    checker = HealthChecker()

    summary = checker.get_health_summary()

    # Print summary
    print(f"Health Status: {'✅ HEALTHY' if summary['healthy'] else '❌ UNHEALTHY'}")
    print(f"Checks Passed: {summary['passed']}/{summary['total']}")
    print("\nCheck Results:")
    for check_name, passed in summary['checks'].items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check_name}: {status}")

    # Exit with appropriate code
    sys.exit(0 if summary['healthy'] else 1)


if __name__ == "__main__":
    main()
