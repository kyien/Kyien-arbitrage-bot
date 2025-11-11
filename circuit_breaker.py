"""
Circuit Breaker Module for Risk Management

Implements circuit breaker pattern to prevent catastrophic losses:
- Stops trading after consecutive failures
- Auto-recovery with gradual operation resumption
- Drawdown limits and recovery tracking
- Per-chain circuit breakers
"""

import time
from typing import Optional, Dict
from enum import Enum
from loguru import logger
import config


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Trading halted
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for preventing catastrophic losses

    States:
    - CLOSED: Normal operation
    - OPEN: Trading disabled (after failure threshold)
    - HALF_OPEN: Limited testing (gradual recovery)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,  # 5 minutes
        half_open_max_trades: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_trades = half_open_max_trades

        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.consecutive_failures = 0
        self.last_state_change = time.time()

        # Per-chain tracking
        self.chain_states: Dict[str, Dict] = {}

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result if successful

        Raises:
            Exception if circuit is open
        """
        # Check if circuit should transition to half-open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_trades = 0
                logger.warning("Circuit breaker: HALF_OPEN state, attempting recovery")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. "
                    f"Recovery in {self.recovery_timeout - (time.time() - self.last_failure_time):.0f}s"
                )

        # In half-open state, limit number of operations
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_trades >= self.half_open_max_trades:
                raise Exception(
                    f"Circuit breaker: HALF_OPEN state limit reached "
                    f"({self.half_open_trades}/{self.half_open_max_trades})"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    async def call_async(self, func, *args, **kwargs):
        """Async version of call"""
        # Check recovery
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_trades = 0
                logger.warning("Circuit breaker: HALF_OPEN state, attempting recovery")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. "
                    f"Recovery in {self.recovery_timeout - (time.time() - self.last_failure_time):.0f}s"
                )

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_trades >= self.half_open_max_trades:
                raise Exception(
                    f"Circuit breaker: HALF_OPEN state limit reached "
                    f"({self.half_open_trades}/{self.half_open_max_trades})"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_trades += 1
            # After successful half-open trades, close the circuit
            if self.half_open_trades >= self.half_open_max_trades:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker: Recovered to CLOSED state")
        else:
            self.failure_count = 0
            self.consecutive_failures = 0

    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker: Failure {self.failure_count}/{self.failure_threshold}"
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker: OPEN state activated after "
                f"{self.consecutive_failures} consecutive failures"
            )

        # If in half-open, go back to open
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.failure_count = 1  # Reset but stay in open
            logger.error("Circuit breaker: Failed in HALF_OPEN state, returning to OPEN")

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.recovery_timeout

    def get_state(self) -> Dict:
        """Get current state information"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'consecutive_failures': self.consecutive_failures,
            'last_failure': self.last_failure_time,
            'is_open': self.state == CircuitState.OPEN,
            'is_half_open': self.state == CircuitState.HALF_OPEN
        }

    def reset(self):
        """Manually reset the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.consecutive_failures = 0
        self.last_failure_time = None
        logger.info("Circuit breaker: Manually reset to CLOSED state")


class PerChainCircuitBreaker:
    """Manages circuit breakers for multiple chains"""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, chain: str) -> CircuitBreaker:
        """Get or create circuit breaker for a chain"""
        if chain not in self.breakers:
            self.breakers[chain] = CircuitBreaker()
        return self.breakers[chain]

    def is_chain_trading(self, chain: str) -> bool:
        """Check if trading is allowed on a chain"""
        breaker = self.get_breaker(chain)
        return breaker.state != CircuitState.OPEN

    def record_failure(self, chain: str):
        """Record a failure for a chain"""
        breaker = self.get_breaker(chain)
        try:
            # Simulate a failure
            raise Exception("Recorded failure")
        except:
            breaker._on_failure()

    def record_success(self, chain: str):
        """Record a success for a chain"""
        breaker = self.get_breaker(chain)
        breaker._on_success()

    def get_all_states(self) -> Dict:
        """Get states of all chain breakers"""
        return {
            chain: breaker.get_state()
            for chain, breaker in self.breakers.items()
        }

    def reset_chain(self, chain: str):
        """Reset a specific chain's circuit breaker"""
        if chain in self.breakers:
            self.breakers[chain].reset()
            logger.info(f"Circuit breaker reset for chain: {chain}")


class DrawdownManager:
    """Manages maximum drawdown limits"""

    def __init__(self, max_daily_loss: float = 100.0):  # $100 USD
        self.max_daily_loss = max_daily_loss
        self.daily_loss = 0.0
        self.daily_start_time = time.time()
        self.daily_profit = 0.0

    def record_trade(self, profit: float):
        """Record a trade result"""
        # Reset daily tracking if new day
        if self._is_new_day():
            self.daily_loss = 0.0
            self.daily_profit = 0.0
            self.daily_start_time = time.time()

        if profit < 0:
            self.daily_loss += abs(profit)
        else:
            self.daily_profit += profit

    def is_within_limits(self) -> bool:
        """Check if drawdown is within acceptable limits"""
        return self.daily_loss <= self.max_daily_loss

    def get_remaining_loss_budget(self) -> float:
        """Get remaining loss budget for the day"""
        return self.max_daily_loss - self.daily_loss

    def _is_new_day(self) -> bool:
        """Check if it's a new day since last reset"""
        return (time.time() - self.daily_start_time) >= 86400  # 24 hours

    def get_status(self) -> Dict:
        """Get drawdown status"""
        return {
            'daily_loss': self.daily_loss,
            'daily_profit': self.daily_profit,
            'net_daily': self.daily_profit - self.daily_loss,
            'max_loss_allowed': self.max_daily_loss,
            'remaining_budget': self.get_remaining_loss_budget(),
            'within_limits': self.is_within_limits()
        }


class RiskManager:
    """Overall risk management system"""

    def __init__(self):
        self.circuit_breaker = PerChainCircuitBreaker()
        self.drawdown_manager = DrawdownManager(
            max_daily_loss=float(config.MAX_POSITION_SIZE * 0.1)  # 10% of max position
        )

    def check_trade_allowed(self, chain: str) -> bool:
        """Check if a trade is allowed on a chain"""
        # Check circuit breaker
        if not self.circuit_breaker.is_chain_trading(chain):
            logger.warning(f"Trade blocked by circuit breaker on {chain}")
            return False

        # Check drawdown limits
        if not self.drawdown_manager.is_within_limits():
            logger.warning("Trade blocked by daily drawdown limit")
            return False

        return True

    def record_trade_result(self, chain: str, profit: float, success: bool):
        """Record trade result for risk tracking"""
        if success:
            self.circuit_breaker.record_success(chain)
        else:
            self.circuit_breaker.record_failure(chain)

        self.drawdown_manager.record_trade(profit)

    def get_risk_status(self) -> Dict:
        """Get overall risk management status"""
        return {
            'circuit_breakers': self.circuit_breaker.get_all_states(),
            'drawdown': self.drawdown_manager.get_status()
        }


# Create singleton instances
circuit_breaker = PerChainCircuitBreaker()
drawdown_manager = DrawdownManager()
risk_manager = RiskManager()
