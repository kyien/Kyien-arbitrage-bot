"""
Volatility Detector for Arbitrage Bot

This module monitors market volatility and triggers arbitrage bot activity
during high-volatility periods when arbitrage opportunities are more likely.

High volatility = More price discrepancies = More arbitrage opportunities
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass
import numpy as np
from loguru import logger
import config


@dataclass
class VolatilityMetrics:
    """Container for volatility metrics"""
    current_volatility: float  # Current volatility percentage
    avg_volatility_1h: float   # 1-hour average volatility
    avg_volatility_24h: float  # 24-hour average volatility
    volatility_trend: str      # "increasing", "decreasing", "stable"
    is_high_volatility: bool   # Whether volatility exceeds threshold
    price_change_rate: float   # Rate of price change per minute


class VolatilityDetector:
    """
    Detect market volatility and trigger bot activity during high-volatility periods

    Uses multiple indicators:
    - Price standard deviation
    - Rate of price change
    - Volume spikes
    - Moving average crossovers
    """

    def __init__(
        self,
        high_volatility_threshold: float = 2.0,  # 2% volatility is "high"
        window_size_1h: int = 60,                # 60 data points for 1 hour
        window_size_24h: int = 1440,             # 1440 data points for 24 hours
        check_interval: int = 60                 # Check every 60 seconds
    ):
        """
        Initialize volatility detector

        Args:
            high_volatility_threshold: Volatility % threshold for "high" volatility
            window_size_1h: Number of samples for 1-hour calculations
            window_size_24h: Number of samples for 24-hour calculations
            check_interval: Seconds between volatility checks
        """
        self.high_volatility_threshold = high_volatility_threshold
        self.window_size_1h = window_size_1h
        self.window_size_24h = window_size_24h
        self.check_interval = check_interval

        # Price history storage
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        self.timestamp_history: Dict[str, deque] = {}

        # Volatility state
        self.current_metrics: Dict[str, VolatilityMetrics] = {}
        self.volatility_callbacks = []

        # State tracking
        self.is_high_volatility_mode = False
        self.high_volatility_start_time = None

        logger.info("Volatility Detector initialized")

    def add_price_data(self, symbol: str, price: float, volume: float = 0):
        """
        Add price and volume data for volatility calculation

        Args:
            symbol: Trading pair symbol (e.g., "ETH/USDT")
            price: Current price
            volume: Current volume
        """
        # Initialize history if needed
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.window_size_24h)
            self.volume_history[symbol] = deque(maxlen=self.window_size_24h)
            self.timestamp_history[symbol] = deque(maxlen=self.window_size_24h)

        # Add data
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        self.timestamp_history[symbol].append(time.time())

    def calculate_volatility(self, symbol: str) -> Optional[VolatilityMetrics]:
        """
        Calculate comprehensive volatility metrics for a symbol

        Args:
            symbol: Trading pair symbol

        Returns:
            VolatilityMetrics object or None if insufficient data
        """
        if symbol not in self.price_history:
            return None

        prices = list(self.price_history[symbol])

        if len(prices) < 10:
            logger.debug(f"Insufficient data for {symbol}: {len(prices)} samples")
            return None

        try:
            # Convert to numpy arrays
            prices_array = np.array(prices)

            # Calculate current volatility (standard deviation of returns)
            returns = np.diff(prices_array) / prices_array[:-1] * 100
            current_volatility = np.std(returns) if len(returns) > 0 else 0

            # Calculate 1-hour average volatility
            if len(prices) >= self.window_size_1h:
                prices_1h = prices_array[-self.window_size_1h:]
                returns_1h = np.diff(prices_1h) / prices_1h[:-1] * 100
                avg_volatility_1h = np.std(returns_1h)
            else:
                avg_volatility_1h = current_volatility

            # Calculate 24-hour average volatility
            if len(prices) >= self.window_size_24h:
                returns_24h = np.diff(prices_array) / prices_array[:-1] * 100
                avg_volatility_24h = np.std(returns_24h)
            else:
                avg_volatility_24h = current_volatility

            # Determine volatility trend
            if avg_volatility_1h > avg_volatility_24h * 1.2:
                volatility_trend = "increasing"
            elif avg_volatility_1h < avg_volatility_24h * 0.8:
                volatility_trend = "decreasing"
            else:
                volatility_trend = "stable"

            # Calculate price change rate (per minute)
            if len(self.timestamp_history[symbol]) >= 2:
                time_diff = self.timestamp_history[symbol][-1] - self.timestamp_history[symbol][0]
                price_diff = prices[-1] - prices[0]
                price_change_rate = (price_diff / prices[0] * 100) / (time_diff / 60) if time_diff > 0 else 0
            else:
                price_change_rate = 0

            # Determine if high volatility
            is_high_volatility = current_volatility > self.high_volatility_threshold

            metrics = VolatilityMetrics(
                current_volatility=current_volatility,
                avg_volatility_1h=avg_volatility_1h,
                avg_volatility_24h=avg_volatility_24h,
                volatility_trend=volatility_trend,
                is_high_volatility=is_high_volatility,
                price_change_rate=price_change_rate
            )

            self.current_metrics[symbol] = metrics

            return metrics

        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {str(e)}")
            return None

    def is_high_volatility_period(self, symbols: List[str] = None) -> bool:
        """
        Check if we're in a high volatility period across multiple symbols

        Args:
            symbols: List of symbols to check (None = check all)

        Returns:
            True if high volatility detected
        """
        if symbols is None:
            symbols = list(self.current_metrics.keys())

        if not symbols:
            return False

        # Count how many symbols have high volatility
        high_vol_count = sum(
            1 for symbol in symbols
            if symbol in self.current_metrics
            and self.current_metrics[symbol].is_high_volatility
        )

        # Consider high volatility if >50% of symbols show high volatility
        threshold = len(symbols) * 0.5

        is_high_vol = high_vol_count >= threshold

        # Update state
        if is_high_vol and not self.is_high_volatility_mode:
            self.is_high_volatility_mode = True
            self.high_volatility_start_time = time.time()
            logger.warning(f"🔥 HIGH VOLATILITY DETECTED: {high_vol_count}/{len(symbols)} symbols")
            self._trigger_callbacks("high_volatility_start")

        elif not is_high_vol and self.is_high_volatility_mode:
            self.is_high_volatility_mode = False
            duration = time.time() - self.high_volatility_start_time if self.high_volatility_start_time else 0
            logger.info(f"📉 Volatility normalized (duration: {duration:.0f}s)")
            self._trigger_callbacks("high_volatility_end")

        return is_high_vol

    def get_volatility_score(self, symbols: List[str] = None) -> float:
        """
        Get overall volatility score (0-100)

        Args:
            symbols: List of symbols to check

        Returns:
            Volatility score (0-100, where 100 = extremely volatile)
        """
        if symbols is None:
            symbols = list(self.current_metrics.keys())

        if not symbols:
            return 0

        # Get average volatility across all symbols
        volatilities = [
            self.current_metrics[symbol].current_volatility
            for symbol in symbols
            if symbol in self.current_metrics
        ]

        if not volatilities:
            return 0

        avg_volatility = np.mean(volatilities)

        # Normalize to 0-100 scale (assume 10% volatility = 100 score)
        score = min(100, (avg_volatility / 10.0) * 100)

        return score

    def register_callback(self, callback):
        """
        Register a callback to be called when volatility changes

        Args:
            callback: Function to call with event type
        """
        self.volatility_callbacks.append(callback)

    def _trigger_callbacks(self, event_type: str):
        """Trigger all registered callbacks"""
        for callback in self.volatility_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event_type))
                else:
                    callback(event_type)
            except Exception as e:
                logger.error(f"Error in volatility callback: {str(e)}")

    def get_status(self) -> Dict:
        """Get current volatility status"""
        return {
            'is_high_volatility': self.is_high_volatility_mode,
            'high_volatility_duration': (
                time.time() - self.high_volatility_start_time
                if self.high_volatility_start_time else 0
            ),
            'volatility_score': self.get_volatility_score(),
            'monitored_symbols': len(self.current_metrics),
            'metrics': {
                symbol: {
                    'current': f"{metrics.current_volatility:.2f}%",
                    'trend': metrics.volatility_trend,
                    'is_high': metrics.is_high_volatility
                }
                for symbol, metrics in self.current_metrics.items()
            }
        }

    async def monitor_loop(self, price_fetcher, symbols: List[str]):
        """
        Continuous monitoring loop

        Args:
            price_fetcher: Async function that returns price data
            symbols: List of symbols to monitor
        """
        logger.info(f"Starting volatility monitoring for {len(symbols)} symbols")

        while True:
            try:
                # Fetch current prices
                prices = await price_fetcher(symbols)

                # Update price history
                for symbol, price_data in prices.items():
                    if price_data:
                        self.add_price_data(
                            symbol,
                            price_data.get('price', 0),
                            price_data.get('volume', 0)
                        )

                # Calculate volatility for all symbols
                for symbol in symbols:
                    metrics = self.calculate_volatility(symbol)
                    if metrics:
                        logger.debug(
                            f"{symbol}: Volatility={metrics.current_volatility:.2f}% "
                            f"Trend={metrics.volatility_trend}"
                        )

                # Check if high volatility period
                is_high_vol = self.is_high_volatility_period(symbols)

                if is_high_vol:
                    logger.warning(
                        f"🔥 High volatility mode active "
                        f"(score: {self.get_volatility_score():.1f}/100)"
                    )

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in volatility monitoring loop: {str(e)}")
                await asyncio.sleep(self.check_interval)


# Integration with arbitrage bot
class VolatilityTriggeredBot:
    """Wrapper to enable/disable bot based on volatility"""

    def __init__(self, arbitrage_bot, volatility_detector: VolatilityDetector):
        self.bot = arbitrage_bot
        self.detector = volatility_detector
        self.normal_mode_sleep = 1.0      # Sleep 1s in normal volatility
        self.high_vol_mode_sleep = 0.01   # Sleep 10ms in high volatility

    async def adaptive_trading_loop(self):
        """Trading loop that adapts to volatility"""
        while True:
            try:
                # Check current volatility state
                is_high_vol = self.detector.is_high_volatility_mode
                volatility_score = self.detector.get_volatility_score()

                if is_high_vol:
                    # High volatility - aggressive scanning
                    logger.info(f"⚡ High volatility mode: {volatility_score:.1f}/100")
                    await self.bot.check_dex_arbitrage()
                    await asyncio.sleep(self.high_vol_mode_sleep)
                else:
                    # Normal volatility - conservative scanning
                    await self.bot.check_dex_arbitrage()
                    await asyncio.sleep(self.normal_mode_sleep)

            except Exception as e:
                logger.error(f"Error in adaptive trading loop: {str(e)}")
                await asyncio.sleep(1)


# Example usage
async def example_usage():
    """Example of how to use VolatilityDetector"""

    # Create detector
    detector = VolatilityDetector(
        high_volatility_threshold=2.0,  # 2% is high
        check_interval=60               # Check every minute
    )

    # Simulate adding price data
    symbols = ['ETH/USDT', 'BTC/USDT']

    for i in range(100):
        for symbol in symbols:
            # Simulate price with some volatility
            base_price = 2000 if 'ETH' in symbol else 50000
            volatility = np.random.normal(0, 20)  # Simulate volatility
            price = base_price + volatility
            volume = np.random.uniform(1000, 10000)

            detector.add_price_data(symbol, price, volume)

        await asyncio.sleep(0.1)

    # Calculate volatility
    for symbol in symbols:
        metrics = detector.calculate_volatility(symbol)
        if metrics:
            logger.info(f"\n{symbol} Volatility Metrics:")
            logger.info(f"  Current: {metrics.current_volatility:.2f}%")
            logger.info(f"  1h Avg: {metrics.avg_volatility_1h:.2f}%")
            logger.info(f"  24h Avg: {metrics.avg_volatility_24h:.2f}%")
            logger.info(f"  Trend: {metrics.volatility_trend}")
            logger.info(f"  High Volatility: {metrics.is_high_volatility}")

    # Check overall state
    status = detector.get_status()
    logger.info(f"\nOverall Status: {status}")


if __name__ == "__main__":
    asyncio.run(example_usage())
