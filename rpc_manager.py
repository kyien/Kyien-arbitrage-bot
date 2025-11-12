"""
RPC Manager with Failover Support

This module manages multiple RPC endpoints with automatic failover
when endpoints become unavailable or slow. This ensures high availability
and optimal performance.
"""

from web3 import Web3
import asyncio
import time
from typing import List, Dict, Optional
from loguru import logger
from collections import deque


class RPCEndpoint:
    """Represents a single RPC endpoint with performance tracking"""

    def __init__(self, url: str, priority: int = 0):
        """
        Initialize RPC endpoint

        Args:
            url: RPC endpoint URL
            priority: Priority level (lower = higher priority)
        """
        self.url = url
        self.priority = priority
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.avg_latency_ms = 0
        self.latency_samples = deque(maxlen=10)  # Keep last 10 samples
        self.is_healthy = True

    def record_success(self, latency_ms: float):
        """Record a successful request"""
        self.success_count += 1
        self.last_success_time = time.time()
        self.latency_samples.append(latency_ms)
        self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)

        # Gradually reduce failure count on success
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)

        # Mark as healthy after 3 consecutive successes
        if self.success_count >= 3:
            self.is_healthy = True

    def record_failure(self):
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        # Mark as unhealthy after 3 consecutive failures
        if self.failure_count >= 3:
            self.is_healthy = False
            logger.warning(
                f"RPC endpoint marked unhealthy: {self.url} "
                f"(failures: {self.failure_count})"
            )

    def should_retry(self, cooldown_seconds: int = 60) -> bool:
        """Check if endpoint should be retried after cooldown period"""
        if self.is_healthy:
            return True

        if self.last_failure_time is None:
            return True

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= cooldown_seconds

    def get_status(self) -> Dict:
        """Get endpoint status"""
        return {
            'url': self.url,
            'priority': self.priority,
            'is_healthy': self.is_healthy,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'avg_latency_ms': round(self.avg_latency_ms, 2),
            'last_failure': self.last_failure_time,
            'last_success': self.last_success_time
        }


class RPCManager:
    """Manage multiple RPC endpoints with automatic failover"""

    def __init__(self, endpoints: List[str], priority_order: List[int] = None):
        """
        Initialize RPC Manager

        Args:
            endpoints: List of RPC endpoint URLs
            priority_order: Optional list of priorities (lower = higher priority)

        Example:
            # Primary endpoint has priority 0, backup has priority 1
            manager = RPCManager(
                endpoints=[
                    'https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY',
                    'https://polygon-rpc.com'
                ],
                priority_order=[0, 1]
            )
        """
        if priority_order is None:
            priority_order = list(range(len(endpoints)))

        self.endpoints = [
            RPCEndpoint(url, priority)
            for url, priority in zip(endpoints, priority_order)
        ]

        # Sort by priority
        self.endpoints.sort(key=lambda x: x.priority)

        self.current_endpoint = self.endpoints[0] if self.endpoints else None
        self.w3_cache: Dict[str, Web3] = {}

        logger.info(f"Initialized RPC Manager with {len(self.endpoints)} endpoints")

    def get_web3(self, endpoint: RPCEndpoint = None) -> Web3:
        """
        Get Web3 instance for an endpoint

        Args:
            endpoint: Specific endpoint to use (default: current)

        Returns:
            Web3 instance
        """
        if endpoint is None:
            endpoint = self.current_endpoint

        if endpoint is None:
            raise Exception("No RPC endpoints available")

        # Use cached Web3 instance if available
        if endpoint.url not in self.w3_cache:
            if endpoint.url.startswith('ws'):
                provider = Web3.WebsocketProvider(endpoint.url)
            else:
                provider = Web3.HTTPProvider(endpoint.url)

            self.w3_cache[endpoint.url] = Web3(provider)
            logger.info(f"Created new Web3 instance for {endpoint.url}")

        return self.w3_cache[endpoint.url]

    async def execute_with_fallback(self, func, *args, **kwargs):
        """
        Execute a function with automatic fallback to backup endpoints

        Args:
            func: Function to execute (should be a Web3 method)
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception if all endpoints fail

        Example:
            result = await rpc_manager.execute_with_fallback(
                w3.eth.get_block, 'latest'
            )
        """
        last_error = None

        for endpoint in self.endpoints:
            # Skip unhealthy endpoints unless they've cooled down
            if not endpoint.should_retry():
                logger.debug(f"Skipping unhealthy endpoint: {endpoint.url}")
                continue

            try:
                w3 = self.get_web3(endpoint)

                # Measure latency
                start_time = time.time()

                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await asyncio.to_thread(func, *args, **kwargs)

                latency_ms = (time.time() - start_time) * 1000

                # Record success
                endpoint.record_success(latency_ms)

                # Update current endpoint if this is better
                if endpoint != self.current_endpoint:
                    if endpoint.priority < self.current_endpoint.priority:
                        logger.info(f"Switched to higher priority endpoint: {endpoint.url}")
                        self.current_endpoint = endpoint

                return result

            except Exception as e:
                logger.warning(f"RPC call failed on {endpoint.url}: {str(e)}")
                endpoint.record_failure()
                last_error = e

                # Try next endpoint
                continue

        # All endpoints failed
        raise Exception(f"All RPC endpoints failed. Last error: {str(last_error)}")

    def rotate_to_next_healthy(self):
        """Manually rotate to the next healthy endpoint"""
        current_index = self.endpoints.index(self.current_endpoint)

        for i in range(1, len(self.endpoints)):
            next_index = (current_index + i) % len(self.endpoints)
            next_endpoint = self.endpoints[next_index]

            if next_endpoint.is_healthy:
                logger.info(f"Manually rotated to: {next_endpoint.url}")
                self.current_endpoint = next_endpoint
                return True

        logger.warning("No healthy endpoints available for rotation")
        return False

    def get_status(self) -> Dict:
        """Get status of all endpoints"""
        return {
            'current_endpoint': self.current_endpoint.url if self.current_endpoint else None,
            'endpoints': [ep.get_status() for ep in self.endpoints],
            'total_endpoints': len(self.endpoints),
            'healthy_endpoints': sum(1 for ep in self.endpoints if ep.is_healthy)
        }

    def get_best_endpoint(self) -> Optional[RPCEndpoint]:
        """Get the best available endpoint based on health and latency"""
        healthy_endpoints = [ep for ep in self.endpoints if ep.is_healthy]

        if not healthy_endpoints:
            # Return first endpoint that can be retried
            for ep in self.endpoints:
                if ep.should_retry():
                    return ep
            return None

        # Sort by priority first, then by latency
        healthy_endpoints.sort(key=lambda ep: (ep.priority, ep.avg_latency_ms))

        return healthy_endpoints[0]

    async def health_check(self):
        """Perform health check on all endpoints"""
        logger.info("Performing health check on all RPC endpoints...")

        for endpoint in self.endpoints:
            try:
                w3 = self.get_web3(endpoint)

                start_time = time.time()
                block_number = await asyncio.to_thread(w3.eth.block_number)
                latency_ms = (time.time() - start_time) * 1000

                endpoint.record_success(latency_ms)

                logger.info(
                    f"✓ {endpoint.url} - Healthy "
                    f"(Block: {block_number}, Latency: {latency_ms:.0f}ms)"
                )

            except Exception as e:
                endpoint.record_failure()
                logger.warning(f"✗ {endpoint.url} - Unhealthy: {str(e)}")

        # Update current endpoint to the best available
        best_endpoint = self.get_best_endpoint()
        if best_endpoint and best_endpoint != self.current_endpoint:
            logger.info(f"Switching to best endpoint: {best_endpoint.url}")
            self.current_endpoint = best_endpoint


# Example usage and configuration
class ChainRPCManager:
    """Manage RPC endpoints for multiple chains"""

    def __init__(self):
        """Initialize RPC managers for all supported chains"""
        import config

        self.managers = {}

        # Polygon RPC endpoints (prioritized)
        polygon_endpoints = [
            config.POLYGON_RPC_URL,
            'https://polygon-rpc.com',
            'https://rpc-mainnet.matic.network',
            'https://rpc-mainnet.maticvigil.com'
        ]
        self.managers['polygon'] = RPCManager(
            [ep for ep in polygon_endpoints if ep],
            priority_order=[0, 1, 2, 3]
        )

        # Arbitrum RPC endpoints
        arbitrum_endpoints = [
            config.ARBITRUM_RPC_URL,
            'https://arb1.arbitrum.io/rpc',
            'https://arbitrum-mainnet.infura.io/v3/YOUR_KEY'
        ]
        self.managers['arbitrum'] = RPCManager(
            [ep for ep in arbitrum_endpoints if ep],
            priority_order=[0, 1, 2]
        )

        # Add more chains as needed

        logger.info(f"Initialized RPC managers for {len(self.managers)} chains")

    def get_manager(self, chain: str) -> RPCManager:
        """Get RPC manager for a specific chain"""
        if chain not in self.managers:
            raise Exception(f"No RPC manager for chain: {chain}")

        return self.managers[chain]

    def get_web3(self, chain: str) -> Web3:
        """Get Web3 instance for a chain"""
        manager = self.get_manager(chain)
        return manager.get_web3()

    async def health_check_all(self):
        """Perform health check on all chains"""
        logger.info("Performing health check on all chains...")

        tasks = [
            manager.health_check()
            for manager in self.managers.values()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Health check completed")

    def get_status_all(self) -> Dict:
        """Get status of all RPC managers"""
        return {
            chain: manager.get_status()
            for chain, manager in self.managers.items()
        }


# Example usage
async def example_usage():
    """Example of how to use RPCManager"""
    import config

    # Create RPC manager with multiple endpoints
    manager = RPCManager(
        endpoints=[
            config.POLYGON_RPC_URL,
            'https://polygon-rpc.com',
            'https://rpc-mainnet.matic.network'
        ],
        priority_order=[0, 1, 2]  # First endpoint has highest priority
    )

    # Perform health check
    await manager.health_check()

    # Execute a call with automatic failover
    try:
        w3 = manager.get_web3()
        block_number = await manager.execute_with_fallback(
            w3.eth.get_block_number
        )
        logger.info(f"Current block number: {block_number}")

        # Get status
        status = manager.get_status()
        logger.info(f"RPC Manager Status: {status}")

    except Exception as e:
        logger.error(f"All RPC endpoints failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(example_usage())
