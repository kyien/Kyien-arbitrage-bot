"""
Enhanced Monitoring and Alerting System
Provides comprehensive alerts for arbitrage bot operations
"""

import asyncio
import os
import json
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger
import aiohttp


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert data structure"""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    chain: Optional[str] = None
    tx_hash: Optional[str] = None
    profit: Optional[float] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class AlertManager:
    """
    Manages alerts across multiple channels

    Supports:
    - Telegram notifications
    - Discord webhooks
    - Email alerts
    - Custom webhooks
    """

    def __init__(self):
        """Initialize alert manager"""
        # Telegram configuration
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

        # Discord configuration
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

        # Email configuration (using webhook service like SendGrid, Mailgun)
        self.email_webhook_url = os.getenv('EMAIL_WEBHOOK_URL')
        self.email_to = os.getenv('ALERT_EMAIL_TO')

        # Custom webhook
        self.custom_webhook_url = os.getenv('CUSTOM_WEBHOOK_URL')

        # Alert history (keep last 1000)
        self.alert_history: List[Alert] = []
        self.max_history = 1000

        # Rate limiting (prevent spam)
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_seconds = 60  # 1 minute between similar alerts

        # Statistics
        self.stats = {
            'total_alerts': 0,
            'alerts_by_level': {'info': 0, 'warning': 0, 'critical': 0},
            'alerts_by_channel': {}
        }

        logger.info("AlertManager initialized")
        logger.info(f"  Telegram: {'✅ Configured' if self.telegram_bot_token else '❌ Not configured'}")
        logger.info(f"  Discord: {'✅ Configured' if self.discord_webhook_url else '❌ Not configured'}")
        logger.info(f"  Email: {'✅ Configured' if self.email_webhook_url else '❌ Not configured'}")

    def _should_send_alert(self, alert_key: str) -> bool:
        """Check if alert should be sent (rate limiting)"""
        if alert_key not in self.alert_cooldown:
            return True

        last_sent = self.alert_cooldown[alert_key]
        elapsed = (datetime.now() - last_sent).total_seconds()

        return elapsed >= self.cooldown_seconds

    def _update_cooldown(self, alert_key: str):
        """Update alert cooldown timestamp"""
        self.alert_cooldown[alert_key] = datetime.now()

    async def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        chain: Optional[str] = None,
        tx_hash: Optional[str] = None,
        profit: Optional[float] = None,
        metadata: Optional[Dict] = None,
        channels: Optional[List[AlertChannel]] = None
    ):
        """
        Send alert to configured channels

        Args:
            level: Alert severity level
            title: Alert title
            message: Alert message
            chain: Blockchain chain (if applicable)
            tx_hash: Transaction hash (if applicable)
            profit: Profit amount (if applicable)
            metadata: Additional metadata
            channels: Specific channels to send to (default: all configured)
        """
        # Create alert object
        alert = Alert(
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            chain=chain,
            tx_hash=tx_hash,
            profit=profit,
            metadata=metadata
        )

        # Rate limiting check
        alert_key = f"{title}:{message}"
        if not self._should_send_alert(alert_key):
            logger.debug(f"Alert rate-limited: {title}")
            return

        # Update statistics
        self.stats['total_alerts'] += 1
        self.stats['alerts_by_level'][level.value] += 1

        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)

        # Determine channels
        if channels is None:
            channels = self._get_configured_channels()

        # Send to each channel
        tasks = []
        for channel in channels:
            if channel == AlertChannel.TELEGRAM:
                tasks.append(self._send_telegram(alert))
            elif channel == AlertChannel.DISCORD:
                tasks.append(self._send_discord(alert))
            elif channel == AlertChannel.EMAIL:
                tasks.append(self._send_email(alert))
            elif channel == AlertChannel.WEBHOOK:
                tasks.append(self._send_webhook(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self._update_cooldown(alert_key)

    def _get_configured_channels(self) -> List[AlertChannel]:
        """Get list of configured alert channels"""
        channels = []
        if self.telegram_bot_token and self.telegram_chat_id:
            channels.append(AlertChannel.TELEGRAM)
        if self.discord_webhook_url:
            channels.append(AlertChannel.DISCORD)
        if self.email_webhook_url:
            channels.append(AlertChannel.EMAIL)
        if self.custom_webhook_url:
            channels.append(AlertChannel.WEBHOOK)
        return channels

    async def _send_telegram(self, alert: Alert):
        """Send alert to Telegram"""
        try:
            # Format message
            emoji = {'info': 'ℹ️', 'warning': '⚠️', 'critical': '🚨'}[alert.level.value]

            text = f"{emoji} *{alert.title}*\n\n{alert.message}"

            if alert.chain:
                text += f"\n\n*Chain:* {alert.chain}"
            if alert.tx_hash:
                text += f"\n*TX:* `{alert.tx_hash}`"
            if alert.profit:
                text += f"\n*Profit:* ${alert.profit:.2f}"

            text += f"\n\n🕐 {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"Telegram alert sent: {alert.title}")
                        self.stats['alerts_by_channel']['telegram'] = \
                            self.stats['alerts_by_channel'].get('telegram', 0) + 1
                    else:
                        logger.error(f"Telegram send failed: {response.status}")

        except Exception as e:
            logger.error(f"Error sending Telegram alert: {str(e)}")

    async def _send_discord(self, alert: Alert):
        """Send alert to Discord"""
        try:
            # Color codes
            colors = {'info': 3447003, 'warning': 16776960, 'critical': 15158332}

            # Build embed
            embed = {
                'title': alert.title,
                'description': alert.message,
                'color': colors[alert.level.value],
                'timestamp': alert.timestamp.isoformat(),
                'fields': []
            }

            if alert.chain:
                embed['fields'].append({'name': 'Chain', 'value': alert.chain, 'inline': True})
            if alert.tx_hash:
                embed['fields'].append({'name': 'TX Hash', 'value': f"`{alert.tx_hash[:16]}...`", 'inline': True})
            if alert.profit:
                embed['fields'].append({'name': 'Profit', 'value': f"${alert.profit:.2f}", 'inline': True})

            # Send to Discord webhook
            data = {'embeds': [embed]}

            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=data) as response:
                    if response.status in [200, 204]:
                        logger.debug(f"Discord alert sent: {alert.title}")
                        self.stats['alerts_by_channel']['discord'] = \
                            self.stats['alerts_by_channel'].get('discord', 0) + 1
                    else:
                        logger.error(f"Discord send failed: {response.status}")

        except Exception as e:
            logger.error(f"Error sending Discord alert: {str(e)}")

    async def _send_email(self, alert: Alert):
        """Send alert via email webhook"""
        try:
            # Format email
            subject = f"[{alert.level.value.upper()}] {alert.title}"

            body = f"{alert.message}\n\n"
            if alert.chain:
                body += f"Chain: {alert.chain}\n"
            if alert.tx_hash:
                body += f"Transaction: {alert.tx_hash}\n"
            if alert.profit:
                body += f"Profit: ${alert.profit:.2f}\n"
            body += f"\nTimestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

            # Send via webhook (format depends on email service)
            data = {
                'to': self.email_to,
                'subject': subject,
                'body': body
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.email_webhook_url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"Email alert sent: {alert.title}")
                        self.stats['alerts_by_channel']['email'] = \
                            self.stats['alerts_by_channel'].get('email', 0) + 1
                    else:
                        logger.error(f"Email send failed: {response.status}")

        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")

    async def _send_webhook(self, alert: Alert):
        """Send alert to custom webhook"""
        try:
            # Send full alert data
            data = alert.to_dict()

            async with aiohttp.ClientSession() as session:
                async with session.post(self.custom_webhook_url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"Webhook alert sent: {alert.title}")
                        self.stats['alerts_by_channel']['webhook'] = \
                            self.stats['alerts_by_channel'].get('webhook', 0) + 1
                    else:
                        logger.error(f"Webhook send failed: {response.status}")

        except Exception as e:
            logger.error(f"Error sending webhook alert: {str(e)}")

    async def opportunity_found(self, chain: str, dex1: str, dex2: str, token_pair: str, profit: float):
        """Alert: Arbitrage opportunity found"""
        await self.send_alert(
            level=AlertLevel.INFO,
            title="🎯 Arbitrage Opportunity Found",
            message=f"Found opportunity on {chain}: {token_pair}\n"
                   f"DEX 1: {dex1}\n"
                   f"DEX 2: {dex2}\n"
                   f"Expected Profit: ${profit:.2f}",
            chain=chain,
            profit=profit,
            metadata={'dex1': dex1, 'dex2': dex2, 'token_pair': token_pair}
        )

    async def execution_started(self, chain: str, token_pair: str, expected_profit: float):
        """Alert: Execution started"""
        await self.send_alert(
            level=AlertLevel.INFO,
            title="🚀 Execution Started",
            message=f"Executing arbitrage on {chain}: {token_pair}\n"
                   f"Expected Profit: ${expected_profit:.2f}",
            chain=chain,
            profit=expected_profit
        )

    async def execution_completed(
        self,
        chain: str,
        tx_hash: str,
        token_pair: str,
        actual_profit: float,
        gas_cost: float,
        net_profit: float
    ):
        """Alert: Execution completed successfully"""
        await self.send_alert(
            level=AlertLevel.INFO,
            title="✅ Execution Successful",
            message=f"Arbitrage executed on {chain}: {token_pair}\n"
                   f"Gross Profit: ${actual_profit:.2f}\n"
                   f"Gas Cost: ${gas_cost:.2f}\n"
                   f"Net Profit: ${net_profit:.2f}",
            chain=chain,
            tx_hash=tx_hash,
            profit=net_profit,
            metadata={'gross_profit': actual_profit, 'gas_cost': gas_cost}
        )

    async def execution_failed(self, chain: str, token_pair: str, reason: str, tx_hash: Optional[str] = None):
        """Alert: Execution failed"""
        await self.send_alert(
            level=AlertLevel.WARNING,
            title="❌ Execution Failed",
            message=f"Arbitrage failed on {chain}: {token_pair}\n"
                   f"Reason: {reason}",
            chain=chain,
            tx_hash=tx_hash,
            metadata={'reason': reason}
        )

    async def wallet_balance_update(self, chain: str, token: str, old_balance: float, new_balance: float):
        """Alert: Wallet balance updated"""
        change = new_balance - old_balance
        emoji = "📈" if change > 0 else "📉"

        await self.send_alert(
            level=AlertLevel.INFO,
            title=f"{emoji} Wallet Balance Updated",
            message=f"Balance change on {chain}:\n"
                   f"Token: {token}\n"
                   f"Old: ${old_balance:.2f}\n"
                   f"New: ${new_balance:.2f}\n"
                   f"Change: ${change:+.2f}",
            chain=chain,
            metadata={'token': token, 'old_balance': old_balance, 'new_balance': new_balance, 'change': change}
        )

    async def mev_detected(self, chain: str, tx_hash: str, mev_type: str, estimated_loss: float):
        """Alert: MEV attack detected"""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title="🚨 MEV Attack Detected",
            message=f"MEV detected on {chain}!\n"
                   f"Type: {mev_type}\n"
                   f"Estimated Loss: ${estimated_loss:.2f}\n"
                   f"Transaction: {tx_hash}",
            chain=chain,
            tx_hash=tx_hash,
            metadata={'mev_type': mev_type, 'estimated_loss': estimated_loss}
        )

    async def slippage_alert(self, chain: str, tx_hash: str, expected: float, actual: float, slippage_pct: float):
        """Alert: High slippage detected"""
        await self.send_alert(
            level=AlertLevel.WARNING,
            title="⚠️ High Slippage Detected",
            message=f"High slippage on {chain}:\n"
                   f"Expected: ${expected:.2f}\n"
                   f"Actual: ${actual:.2f}\n"
                   f"Slippage: {slippage_pct:.2f}%",
            chain=chain,
            tx_hash=tx_hash,
            metadata={'expected': expected, 'actual': actual, 'slippage_pct': slippage_pct}
        )

    async def reentrancy_alert(self, chain: str, contract_address: str):
        """Alert: Reentrancy attempt detected"""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title="🚨 Reentrancy Attempt Detected",
            message=f"Reentrancy attack attempted on {chain}!\n"
                   f"Contract: {contract_address}\n"
                   f"Transaction blocked by ReentrancyGuard",
            chain=chain,
            metadata={'contract_address': contract_address}
        )

    async def gas_exhaustion_alert(self, chain: str, current_balance: float, threshold: float):
        """Alert: Gas balance low"""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title="⛽ Gas Balance Low",
            message=f"Gas balance critically low on {chain}!\n"
                   f"Current: ${current_balance:.2f}\n"
                   f"Threshold: ${threshold:.2f}\n"
                   f"Please refill immediately!",
            chain=chain,
            metadata={'current_balance': current_balance, 'threshold': threshold}
        )

    async def bot_started(self, chains: List[str]):
        """Alert: Bot started"""
        await self.send_alert(
            level=AlertLevel.INFO,
            title="🤖 Bot Started",
            message=f"Arbitrage bot started successfully\n"
                   f"Monitoring chains: {', '.join(chains)}",
            metadata={'chains': chains}
        )

    async def bot_stopped(self, reason: str):
        """Alert: Bot stopped"""
        await self.send_alert(
            level=AlertLevel.WARNING,
            title="🛑 Bot Stopped",
            message=f"Arbitrage bot stopped\n"
                   f"Reason: {reason}",
            metadata={'reason': reason}
        )

    async def bot_error(self, error: str, traceback: Optional[str] = None):
        """Alert: Bot error"""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title="💥 Bot Error",
            message=f"Critical error occurred:\n{error}",
            metadata={'error': error, 'traceback': traceback}
        )

    async def health_check_failed(self, component: str, details: str):
        """Alert: Health check failed"""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title="🏥 Health Check Failed",
            message=f"Component health check failed: {component}\n"
                   f"Details: {details}",
            metadata={'component': component, 'details': details}
        )

    def get_stats(self) -> Dict:
        """Get alert statistics"""
        return self.stats.copy()

    def get_recent_alerts(self, count: int = 10) -> List[Dict]:
        """Get recent alerts"""
        recent = self.alert_history[-count:]
        return [alert.to_dict() for alert in recent]


# Global alert manager instance
alert_manager = AlertManager()


async def test_alerts():
    """Test alert system"""
    logger.info("Testing alert system...")

    # Test opportunity found
    await alert_manager.opportunity_found(
        chain='polygon',
        dex1='QuickSwap',
        dex2='SushiSwap',
        token_pair='WETH/USDC',
        profit=15.50
    )

    await asyncio.sleep(2)

    # Test execution completed
    await alert_manager.execution_completed(
        chain='polygon',
        tx_hash='0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        token_pair='WETH/USDC',
        actual_profit=14.80,
        gas_cost=0.50,
        net_profit=14.30
    )

    await asyncio.sleep(2)

    # Test gas exhaustion
    await alert_manager.gas_exhaustion_alert(
        chain='polygon',
        current_balance=5.00,
        threshold=10.00
    )

    await asyncio.sleep(2)

    # Print stats
    stats = alert_manager.get_stats()
    logger.info(f"Alert Stats: {json.dumps(stats, indent=2)}")

    logger.info("Alert test complete!")


if __name__ == "__main__":
    logger.info("Monitoring & Alerting System v1.0.0\n")
    asyncio.run(test_alerts())
