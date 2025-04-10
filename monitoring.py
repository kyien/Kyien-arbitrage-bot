import asyncio
import aiohttp
from loguru import logger
import config
from typing import Dict, List, Any
import time
from dataclasses import dataclass
import json

@dataclass
class AlertConfig:
    min_profit: float
    max_gas_price: int
    health_check_interval: int
    telegram_enabled: bool
    discord_enabled: bool

class MonitoringSystem:
    def __init__(self):
        self.alert_config = AlertConfig(
            min_profit=config.ALERT_MIN_PROFIT,
            max_gas_price=config.MAX_GAS_PRICE_GWEI,
            health_check_interval=config.HEALTH_CHECK_INTERVAL,
            telegram_enabled=bool(config.TELEGRAM_BOT_TOKEN),
            discord_enabled=bool(config.DISCORD_WEBHOOK_URL)
        )
        
        self.metrics = {
            'trades': [],
            'profits': [],
            'errors': [],
            'gas_prices': {},
            'system_health': {}
        }

    async def start_monitoring(self):
        """Start all monitoring tasks"""
        tasks = [
            self.monitor_system_health(),
            self.monitor_gas_prices(),
            self.monitor_profit_opportunities(),
            self.monitor_error_rates()
        ]
        await asyncio.gather(*tasks)

    async def monitor_system_health(self):
        """Monitor system health metrics"""
        while True:
            try:
                # Check various system components
                health_metrics = {
                    'websocket_connections': await self._check_websocket_status(),
                    'chain_connections': await self._check_chain_connections(),
                    'api_rate_limits': await self._check_api_rate_limits(),
                    'memory_usage': self._get_memory_usage(),
                    'error_rate': self._calculate_error_rate()
                }
                
                self.metrics['system_health'] = health_metrics
                
                # Check for critical issues
                await self._check_health_alerts(health_metrics)
                
                await asyncio.sleep(self.alert_config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in system health monitoring: {str(e)}")
                await self.send_alert(f"System health monitoring error: {str(e)}", "error")
                await asyncio.sleep(10)

    async def monitor_gas_prices(self):
        """Monitor gas prices across different chains"""
        while True:
            try:
                for chain in ['polygon', 'arbitrum', 'optimism', 'bsc']:
                    gas_price = await self._get_gas_price(chain)
                    self.metrics['gas_prices'][chain] = gas_price
                    
                    if gas_price > self.alert_config.max_gas_price:
                        await self.send_alert(
                            f"High gas price on {chain}: {gas_price} gwei",
                            "warning"
                        )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in gas price monitoring: {str(e)}")
                await asyncio.sleep(5)

    async def monitor_profit_opportunities(self):
        """Monitor and alert on profitable opportunities"""
        while True:
            try:
                for trade in self.metrics['trades'][-100:]:  # Look at last 100 trades
                    if trade['profit'] > self.alert_config.min_profit:
                        await self.send_alert(
                            f"High profit opportunity: {trade['profit']}% on {trade['pair']}",
                            "opportunity"
                        )
                
                await asyncio.sleep(1)  # Check frequently
                
            except Exception as e:
                logger.error(f"Error in profit monitoring: {str(e)}")
                await asyncio.sleep(5)

    async def monitor_error_rates(self):
        """Monitor error rates and alert if too high"""
        while True:
            try:
                error_rate = self._calculate_error_rate()
                
                if error_rate > 0.1:  # More than 10% error rate
                    await self.send_alert(
                        f"High error rate detected: {error_rate*100}%",
                        "error"
                    )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in error rate monitoring: {str(e)}")
                await asyncio.sleep(5)

    async def send_alert(self, message: str, level: str):
        """Send alert through configured channels"""
        try:
            if self.alert_config.telegram_enabled:
                await self._send_telegram_alert(message, level)
            
            if self.alert_config.discord_enabled:
                await self._send_discord_alert(message, level)
            
            logger.log(level.upper(), message)
            
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")

    async def _send_telegram_alert(self, message: str, level: str):
        """Send alert via Telegram"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
                data = {
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": f"[{level.upper()}] {message}",
                    "parse_mode": "Markdown"
                }
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        logger.error(f"Telegram API error: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {str(e)}")

    async def _send_discord_alert(self, message: str, level: str):
        """Send alert via Discord webhook"""
        try:
            async with aiohttp.ClientSession() as session:
                embed = {
                    "title": f"Arbitrage Alert - {level.upper()}",
                    "description": message,
                    "color": self._get_discord_color(level)
                }
                
                data = {
                    "embeds": [embed]
                }
                
                async with session.post(config.DISCORD_WEBHOOK_URL, json=data) as response:
                    if response.status != 204:
                        logger.error(f"Discord API error: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Error sending Discord alert: {str(e)}")

    def _get_discord_color(self, level: str) -> int:
        """Get Discord embed color based on alert level"""
        colors = {
            "error": 0xFF0000,    # Red
            "warning": 0xFFA500,  # Orange
            "info": 0x00FF00,     # Green
            "opportunity": 0x00FF00  # Green
        }
        return colors.get(level.lower(), 0x808080)  # Default gray

    def _calculate_error_rate(self) -> float:
        """Calculate error rate from recent operations"""
        recent_errors = len([e for e in self.metrics['errors'] 
                           if time.time() - e['timestamp'] < 3600])
        recent_trades = len([t for t in self.metrics['trades'] 
                           if time.time() - t['timestamp'] < 3600])
        
        if recent_trades == 0:
            return 0.0
            
        return recent_errors / (recent_trades + recent_errors)

    async def _check_websocket_status(self) -> Dict[str, bool]:
        """Check status of websocket connections"""
        # Implementation depends on websocket management system
        pass

    async def _check_chain_connections(self) -> Dict[str, bool]:
        """Check connections to different blockchain networks"""
        # Implementation depends on chain connection management
        pass

    async def _check_api_rate_limits(self) -> Dict[str, float]:
        """Check current API rate limit status"""
        # Implementation depends on exchange API management
        pass

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        # Implementation depends on system monitoring requirements
        pass

    async def _get_gas_price(self, chain: str) -> float:
        """Get current gas price for specified chain"""
        # Implementation depends on chain connection management
        pass

    async def log_trade(self, trade_data: Dict[str, Any]):
        """Log a trade for monitoring"""
        trade_data['timestamp'] = time.time()
        self.metrics['trades'].append(trade_data)
        
        # Keep only recent trades
        self.metrics['trades'] = [t for t in self.metrics['trades'] 
                                if time.time() - t['timestamp'] < 86400]  # Last 24h

    async def log_error(self, error_data: Dict[str, Any]):
        """Log an error for monitoring"""
        error_data['timestamp'] = time.time()
        self.metrics['errors'].append(error_data)
        
        # Keep only recent errors
        self.metrics['errors'] = [e for e in self.metrics['errors'] 
                                if time.time() - e['timestamp'] < 86400]  # Last 24h
