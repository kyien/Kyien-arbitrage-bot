import numpy as np
from typing import Dict, List, Tuple
import pandas as pd
from loguru import logger
import config
import talib
from dataclasses import dataclass

@dataclass
class MarketCondition:
    volatility: float
    trend: str
    volume: float
    liquidity: float
    rsi: float
    bollinger_position: str

class AdvancedStrategyManager:
    def __init__(self):
        self.price_history = {}
        self.volume_history = {}
        self.liquidity_history = {}

    def analyze_market_conditions(self, symbol: str, prices: List[float], 
                                volumes: List[float], liquidity: List[float]) -> MarketCondition:
        """Analyze market conditions using multiple indicators"""
        try:
            prices_array = np.array(prices)
            volumes_array = np.array(volumes)
            
            # Calculate volatility
            volatility = np.std(prices_array) / np.mean(prices_array)
            
            # Determine trend using multiple timeframes
            trends = self._analyze_trends(prices_array)
            
            # Calculate RSI
            rsi = talib.RSI(prices_array)[-1]
            
            # Calculate Bollinger Bands
            upper, middle, lower = talib.BBANDS(
                prices_array,
                timeperiod=config.BOLLINGER_PERIOD,
                nbdevup=config.BOLLINGER_STD,
                nbdevdn=config.BOLLINGER_STD
            )
            
            current_price = prices_array[-1]
            if current_price > upper[-1]:
                bollinger_position = "above"
            elif current_price < lower[-1]:
                bollinger_position = "below"
            else:
                bollinger_position = "inside"
            
            return MarketCondition(
                volatility=volatility,
                trend=trends['primary'],
                volume=volumes_array[-1],
                liquidity=liquidity[-1],
                rsi=rsi,
                bollinger_position=bollinger_position
            )
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return None

    def calculate_optimal_position_size(self, market_condition: MarketCondition, 
                                     max_position: float) -> float:
        """Calculate optimal position size based on market conditions"""
        try:
            # Base score on market conditions
            volatility_score = self._normalize_volatility(market_condition.volatility)
            trend_score = self._get_trend_score(market_condition.trend)
            volume_score = self._normalize_volume(market_condition.volume)
            liquidity_score = self._normalize_liquidity(market_condition.liquidity)
            
            # Weight the factors
            weighted_score = (
                volatility_score * config.VOLATILITY_WEIGHT +
                trend_score * 0.2 +
                volume_score * config.VOLUME_WEIGHT +
                liquidity_score * config.LIQUIDITY_WEIGHT
            )
            
            # Adjust for RSI extremes
            if market_condition.rsi < config.RSI_OVERSOLD:
                weighted_score *= 1.2  # Increase position size for oversold conditions
            elif market_condition.rsi > config.RSI_OVERBOUGHT:
                weighted_score *= 0.8  # Decrease position size for overbought conditions
            
            # Calculate final position size
            position_size = max_position * weighted_score
            
            # Ensure within limits
            return min(position_size, config.MAX_POSITION_SIZE)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return config.MAX_TRADE_AMOUNT

    def should_execute_trade(self, market_condition: MarketCondition, 
                           profit_potential: float) -> Tuple[bool, str]:
        """Determine if a trade should be executed based on conditions"""
        try:
            reasons = []
            
            # Check if profit meets minimum threshold
            if profit_potential < config.MIN_PROFIT_THRESHOLD:
                return False, "Insufficient profit potential"
            
            # Check market conditions
            if market_condition.volatility > 0.05:  # 5% volatility threshold
                reasons.append("High volatility")
            
            if market_condition.rsi > config.RSI_OVERBOUGHT:
                reasons.append("Overbought conditions")
            elif market_condition.rsi < config.RSI_OVERSOLD:
                reasons.append("Oversold conditions")
            
            if market_condition.bollinger_position == "above":
                reasons.append("Price above Bollinger Bands")
            
            # Make decision based on combined factors
            if len(reasons) >= 2:  # If multiple warning signs
                return False, f"Multiple risk factors: {', '.join(reasons)}"
            
            return True, "Conditions favorable for trade"
            
        except Exception as e:
            logger.error(f"Error in trade execution decision: {str(e)}")
            return False, f"Error in analysis: {str(e)}"

    def _analyze_trends(self, prices: np.ndarray) -> Dict[str, str]:
        """Analyze trends across multiple timeframes"""
        try:
            # Calculate EMAs for different timeframes
            ema9 = talib.EMA(prices, timeperiod=9)
            ema21 = talib.EMA(prices, timeperiod=21)
            ema55 = talib.EMA(prices, timeperiod=55)
            
            # Determine trends
            short_trend = "bullish" if ema9[-1] > ema21[-1] else "bearish"
            long_trend = "bullish" if ema21[-1] > ema55[-1] else "bearish"
            
            # Combine trends
            if short_trend == long_trend:
                primary_trend = short_trend
            else:
                primary_trend = "sideways"
            
            return {
                "primary": primary_trend,
                "short": short_trend,
                "long": long_trend
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {"primary": "unknown", "short": "unknown", "long": "unknown"}

    def _normalize_volatility(self, volatility: float) -> float:
        """Normalize volatility to a score between 0 and 1"""
        # Higher volatility = lower score
        return max(0, 1 - (volatility / 0.1))  # 10% volatility = 0 score

    def _get_trend_score(self, trend: str) -> float:
        """Convert trend to a numeric score"""
        return {"bullish": 1.0, "sideways": 0.5, "bearish": 0.0}.get(trend, 0.5)

    def _normalize_volume(self, volume: float) -> float:
        """Normalize volume to a score between 0 and 1"""
        # Compare to moving average
        return min(1.0, volume / np.mean(self.volume_history.get(symbol, [volume])))

    def _normalize_liquidity(self, liquidity: float) -> float:
        """Normalize liquidity to a score between 0 and 1"""
        return min(1.0, liquidity / config.MIN_LIQUIDITY_THRESHOLD)
