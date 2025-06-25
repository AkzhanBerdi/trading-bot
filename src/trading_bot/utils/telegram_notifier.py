# src/trading_bot/utils/telegram_notifier.py
import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Optional, Any
import requests
from enum import Enum

class NotificationType(Enum):
    """Types of notifications"""
    TRADE_ATTEMPT = "🎯"
    TRADE_SUCCESS = "✅"
    TRADE_ERROR = "❌"
    BOT_START = "🚀"
    BOT_STOP = "🛑"
    BOT_ERROR = "💥"
    PORTFOLIO_UPDATE = "💰"
    GRID_RESET = "🔄"
    SIGNAL_DETECTED = "⚡"
    WARNING = "⚠️"
    INFO = "ℹ️"

class TelegramNotifier:
    """Telegram notification system for trading bot"""
    
    def __init__(self):
        """Initialize Telegram notifier - NO ASYNC CALLS HERE"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        # Notification settings
        self.max_message_length = 4096  # Telegram limit
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        
        # Rate limiting to avoid spam
        self.last_notification_time = {}
        self.min_interval_seconds = {
            NotificationType.TRADE_ATTEMPT: 0,  # No limit
            NotificationType.TRADE_SUCCESS: 0,  # No limit
            NotificationType.TRADE_ERROR: 0,   # No limit
            NotificationType.PORTFOLIO_UPDATE: 300,  # 5 minutes
            NotificationType.WARNING: 60,      # 1 minute
            NotificationType.INFO: 30,         # 30 seconds
        }
        
        self.logger = logging.getLogger(__name__)
        self.connection_tested = False  # Track if we've tested connection
        
        if self.enabled:
            self.logger.info("✅ Telegram notifier initialized")
            # Don't test connection here - will be done when first message is sent
        else:
            self.logger.warning("⚠️ Telegram notifier disabled - missing credentials")
    
    async def test_connection(self) -> bool:
        """Test Telegram bot connection - only called when event loop is running"""
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                bot_name = bot_info.get('result', {}).get('username', 'Unknown')
                self.connection_tested = True
                self.logger.info(f"✅ Telegram bot connected: @{bot_name}")
                return True
            else:
                self.logger.error(f"Telegram test failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Telegram connection test error: {e}")
            return False
    
    def _should_send_notification(self, notification_type: NotificationType) -> bool:
        """Check if notification should be sent based on rate limiting"""
        if not self.enabled:
            return False
        
        min_interval = self.min_interval_seconds.get(notification_type, 0)
        if min_interval == 0:
            return True
        
        last_time = self.last_notification_time.get(notification_type)
        if last_time is None:
            return True
        
        time_since_last = (datetime.now() - last_time).total_seconds()
        return time_since_last >= min_interval
    
    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """Send a notification to Telegram"""
        
        if not force and not self._should_send_notification(notification_type):
            self.logger.debug(f"Skipping {notification_type.name} notification due to rate limiting")
            return False
        
        # Test connection on first use (not during init)
        if not self.connection_tested:
            await self.test_connection()
        
        try:
            # Format the message
            emoji = notification_type.value
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            formatted_message = f"{emoji} *{title}*\n"
            formatted_message += f"🕐 {timestamp}\n\n"
            formatted_message += message
            
            # Add extra data if provided
            if extra_data:
                formatted_message += "\n\n📊 *Details:*\n"
                for key, value in extra_data.items():
                    formatted_message += f"• {key}: `{value}`\n"
            
            # Truncate if too long
            if len(formatted_message) > self.max_message_length:
                formatted_message = formatted_message[:self.max_message_length-50] + "...\n\n*Message truncated*"
            
            # Send the message
            success = await self._send_telegram_message(formatted_message)
            
            if success:
                self.last_notification_time[notification_type] = datetime.now()
                self.logger.debug(f"Sent {notification_type.name} notification")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False
    
    async def _send_telegram_message(self, message: str) -> bool:
        """Send message to Telegram with retry logic"""
        if not self.enabled:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    return True
                else:
                    error_data = response.json() if response.content else {}
                    self.logger.warning(f"Telegram API error (attempt {attempt + 1}): {response.status_code} - {error_data}")
                    
                    # Don't retry on certain errors
                    if response.status_code in [400, 401, 403]:
                        break
                        
            except Exception as e:
                self.logger.warning(f"Telegram send error (attempt {attempt + 1}): {e}")
            
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return False
    
    # Convenience methods for different types of notifications
    
    async def notify_trade_attempt(self, symbol: str, action: str, price: float, quantity: float, level: int = None):
        """Notify when a trade is attempted"""
        title = f"{action} Order Placed"
        message = f"💹 *{symbol}* {action}\n"
        message += f"💵 Price: `${price:.4f}`\n"
        message += f"📦 Quantity: `{quantity:.6f}`\n"
        message += f"💰 Value: `${price * quantity:.2f}`"
        
        if level:
            message += f"\n🎯 Grid Level: `{level}`"
        
        await self.send_notification(NotificationType.TRADE_ATTEMPT, title, message)
    
    async def notify_trade_success(self, symbol: str, action: str, price: float, quantity: float, 
                                 order_id: str = None, profit: float = None):
        """Notify when a trade is successful"""
        title = f"{action} Order Filled! 🎉"
        message = f"💹 *{symbol}* {action} EXECUTED\n"
        message += f"💵 Fill Price: `${price:.4f}`\n"
        message += f"📦 Quantity: `{quantity:.6f}`\n"
        message += f"💰 Total: `${price * quantity:.2f}`"
        
        if profit is not None:
            profit_emoji = "📈" if profit > 0 else "📉"
            message += f"\n{profit_emoji} P&L: `${profit:.2f}`"
        
        extra_data = {}
        if order_id:
            extra_data["Order ID"] = order_id
        
        await self.send_notification(NotificationType.TRADE_SUCCESS, title, message, extra_data)
    
    async def notify_trade_error(self, symbol: str, action: str, error_message: str, 
                               price: float = None, quantity: float = None):
        """Notify when a trade fails"""
        title = f"{action} Order Failed"
        message = f"💹 *{symbol}* {action} FAILED\n"
        message += f"🚨 Error: `{error_message}`"
        
        if price and quantity:
            message += f"\n💵 Attempted Price: `${price:.4f}`\n"
            message += f"📦 Attempted Quantity: `{quantity:.6f}`"
        
        await self.send_notification(NotificationType.TRADE_ERROR, title, message)
    
    async def notify_portfolio_update(self, total_value: float, daily_change: float = None, 
                                    top_assets: Dict[str, float] = None):
        """Notify portfolio status"""
        title = "Portfolio Update"
        message = f"💰 Total Value: `${total_value:.2f}`"
        
        if daily_change is not None:
            change_emoji = "📈" if daily_change >= 0 else "📉"
            message += f"\n{change_emoji} 24h Change: `${daily_change:+.2f}` ({daily_change/total_value*100:+.1f}%)"
        
        if top_assets:
            message += "\n\n🏆 *Top Holdings:*"
            for asset, value in list(top_assets.items())[:5]:
                percentage = (value / total_value) * 100
                message += f"\n• {asset}: `${value:.2f}` ({percentage:.1f}%)"
        
        await self.send_notification(NotificationType.PORTFOLIO_UPDATE, title, message)
    
    async def notify_grid_reset(self, symbol: str, old_price: float, new_price: float, reason: str):
        """Notify when grid is reset"""
        title = f"Grid Reset: {symbol}"
        change_percent = ((new_price - old_price) / old_price) * 100
        change_emoji = "📈" if change_percent >= 0 else "📉"
        
        message = f"🔄 *{symbol}* Grid Reconfigured\n"
        message += f"📊 Old Center: `${old_price:.4f}`\n"
        message += f"📊 New Center: `${new_price:.4f}`\n"
        message += f"{change_emoji} Change: `{change_percent:+.1f}%`\n"
        message += f"💡 Reason: {reason}"
        
        await self.send_notification(NotificationType.GRID_RESET, title, message)
    
    async def notify_signal_detected(self, symbol: str, signal_type: str, strength: float, reasons: list):
        """Notify when trading signal is detected"""
        title = f"Signal Detected: {symbol}"
        strength_emoji = "🔥" if strength > 0.8 else "⚡" if strength > 0.6 else "💡"
        
        message = f"{strength_emoji} *{signal_type}* Signal\n"
        message += f"💹 Asset: `{symbol}`\n"
        message += f"💪 Strength: `{strength:.1%}`\n"
        message += f"🔍 Reasons:\n"
        
        for reason in reasons[:5]:  # Limit to 5 reasons
            message += f"• {reason}\n"
        
        await self.send_notification(NotificationType.SIGNAL_DETECTED, title, message)
    
    async def notify_bot_status(self, status: str, details: str = None):
        """Notify bot status changes"""
        if status.lower() in ['start', 'started', 'startup']:
            notification_type = NotificationType.BOT_START
            title = "🚀 Trading Bot Started"
        elif status.lower() in ['stop', 'stopped', 'shutdown']:
            notification_type = NotificationType.BOT_STOP
            title = "🛑 Trading Bot Stopped"
        elif status.lower() in ['error', 'crash', 'exception']:
            notification_type = NotificationType.BOT_ERROR
            title = "💥 Trading Bot Error"
        else:
            notification_type = NotificationType.INFO
            title = f"Bot Status: {status}"
        
        message = details if details else f"Status changed to: {status}"
        await self.send_notification(notification_type, title, message, force=True)
    
    async def notify_warning(self, warning_message: str, details: Dict[str, Any] = None):
        """Send warning notification"""
        await self.send_notification(
            NotificationType.WARNING,
            "Warning",
            warning_message,
            details
        )
    
    async def notify_info(self, info_message: str, details: Dict[str, Any] = None):
        """Send info notification"""
        await self.send_notification(
            NotificationType.INFO,
            "Information",
            info_message,
            details
        )
    
    def disable(self):
        """Disable notifications"""
        self.enabled = False
        self.logger.info("📴 Telegram notifications disabled")
    
    def enable(self):
        """Enable notifications"""
        if self.bot_token and self.chat_id:
            self.enabled = True
            self.connection_tested = False  # Reset connection test
            self.logger.info("📱 Telegram notifications enabled")
        else:
            self.logger.error("Cannot enable notifications - missing credentials")

# Global notifier instance - NO ASYNC CALLS DURING IMPORT
telegram_notifier = TelegramNotifier()
