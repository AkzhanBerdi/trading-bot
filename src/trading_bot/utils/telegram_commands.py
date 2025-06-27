# utils/telegram_commands.py
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict

import requests


class TelegramBotCommands:
    """Advanced Telegram bot command handler with rich features"""

    def __init__(self, trading_bot, telegram_notifier, trade_logger):
        self.trading_bot = trading_bot
        self.telegram_notifier = telegram_notifier
        self.trade_logger = trade_logger
        self.logger = logging.getLogger(__name__)

        # Enhanced command handlers
        self.commands = {
            "/start": self.cmd_start,
            "/stop": self.cmd_stop_bot,
            "/resume": self.cmd_start_bot,  # ← CHANGE FROM '/start_bot' TO '/resume'
            "/status": self.cmd_status,
            "/trades": self.cmd_recent_trades,
            "/portfolio": self.cmd_portfolio,
            "/balance": self.cmd_balance,
            "/stats": self.cmd_stats,
            "/grid": self.cmd_grid_status,
            "/health": self.cmd_health_check,
            "/reset": self.cmd_reset,
            "/help": self.cmd_help,
            "/performance": self.cmd_performance,
            "/errors": self.cmd_recent_errors,
        }

        self.last_update_id = 0
        self.command_processor_running = False
        self.command_history = []
        self.rate_limit = {}  # Rate limiting per command
        self.restart_requested = False  # Add this line

    async def start_command_processor(self):
        """Start enhanced command processor with rate limiting"""
        if not self.telegram_notifier.enabled:
            self.logger.warning("Telegram not enabled, skipping command processor")
            return

        self.command_processor_running = True
        self.logger.info("🤖 Enhanced Telegram command processor started")

        while self.command_processor_running:
            try:
                await self.process_updates()
                await asyncio.sleep(1)  # Faster polling for responsiveness
            except Exception as e:
                self.logger.error(f"Error in command processor: {e}")
                await asyncio.sleep(5)

    def stop_command_processor(self):
        """Stop command processor"""
        self.command_processor_running = False
        self.logger.info("🛑 Telegram command processor stopped")

    async def process_updates(self):
        """Process telegram updates with enhanced error handling"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_notifier.bot_token}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 2,
                "allowed_updates": ["message"],
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data["ok"] and data["result"]:
                    for update in data["result"]:
                        await self.handle_update(update)
                        self.last_update_id = update["update_id"]

        except Exception as e:
            if "timeout" not in str(e).lower():
                self.logger.error(f"Error processing updates: {e}")

    async def handle_update(self, update: Dict):
        """Enhanced update handler with command history and rate limiting"""
        try:
            if "message" not in update:
                return

            message = update["message"]

            # Security: Only process from configured chat
            if str(message["chat"]["id"]) != str(self.telegram_notifier.chat_id):
                return

            if "text" not in message:
                return

            text = message["text"].strip()
            user_id = message["from"]["id"]

            # Rate limiting check
            if self._is_rate_limited(user_id, text):
                await self.send_reply(
                    message, "⏱️ Please wait before sending another command."
                )
                return

            # Log command
            self.command_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "command": text,
                    "message_id": message["message_id"],
                }
            )

            # Find and execute command
            for command, handler in self.commands.items():
                if text.startswith(command):
                    self.logger.info(
                        f"📱 Executing command: {command} from user {user_id}"
                    )
                    try:
                        await handler(message)
                    except Exception as e:
                        self.logger.error(f"Error executing command {command}: {e}")
                        await self.send_reply(
                            message, f"❌ Error executing command: {str(e)[:100]}"
                        )
                    break
            else:
                # Unknown command
                if text.startswith("/"):
                    await self.send_reply(
                        message,
                        "❓ Unknown command. Send /help for available commands.",
                    )

        except Exception as e:
            self.logger.error(f"Error handling update: {e}")

    def _is_rate_limited(self, user_id: int, command: str) -> bool:
        """Check if user is rate limited"""
        now = time.time()
        key = f"{user_id}_{command}"

        if key in self.rate_limit:
            if now - self.rate_limit[key] < 2:  # 2 second rate limit
                return True

        self.rate_limit[key] = now
        return False

    async def send_reply(
        self, original_message: Dict, text: str, parse_mode: str = "Markdown"
    ):
        """Enhanced reply with safe formatting and error handling"""
        try:
            # Clean the text to avoid formatting issues
            # Remove problematic characters and ensure proper encoding
            cleaned_text = text.replace("\\n", "\n")  # Fix escaped newlines
            cleaned_text = cleaned_text.replace(
                "_", "\\_"
            )  # Escape underscores for markdown

            # Limit message length (Telegram limit is 4096)
            if len(cleaned_text) > 4000:
                cleaned_text = cleaned_text[:3950] + "\n\n... (message truncated)"

            url = f"https://api.telegram.org/bot{self.telegram_notifier.bot_token}/sendMessage"
            payload = {
                "chat_id": original_message["chat"]["id"],
                "text": cleaned_text,
                "parse_mode": parse_mode,
                "reply_to_message_id": original_message["message_id"],
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                return True
            else:
                # Try without markdown if it fails
                self.logger.warning(
                    f"Markdown failed ({response.status_code}), trying plain text"
                )
                payload["parse_mode"] = None
                response2 = requests.post(url, json=payload, timeout=10)

                if response2.status_code != 200:
                    self.logger.error(
                        f"Failed to send reply: {response2.status_code} - {response2.text}"
                    )
                    return False
                return True

        except Exception as e:
            self.logger.error(f"Error sending reply: {e}")
            return False

    # =============================================================================
    # COMMAND HANDLERS
    # =============================================================================

    async def cmd_start(self, message):
        """Enhanced start command with RESUME instead of start_bot"""
        uptime = self.get_uptime()

        try:
            stats = self.trade_logger.get_trading_statistics(1)
        except:
            stats = {"total_trades": 0}

        # Get portfolio value safely
        portfolio_text = "Loading..."
        try:
            portfolio, total_value = await self.trading_bot.get_portfolio_status()
            portfolio_text = f"${total_value:.2f}"
        except:
            pass

        reply = f"""🤖 *Advanced Trading Bot Dashboard*

    *🎛️ Bot Control:*
    /resume - Start trading
    /stop - Stop trading
    /status - Detailed status
    /health - System health check

    *📊 Information:*
    /portfolio - Portfolio summary
    /balance - Account balances
    /trades - Recent trades
    /stats - Trading statistics
    /grid - Grid trading status
    /performance - Performance metrics

    *🔧 Management:*
    /reset - Reset grid state
    /errors - Recent errors
    /help - This help menu

    *📈 Current Status:*
    Bot: {"🟢 Running" if self.trading_bot.running else "🔴 Stopped"}
    Uptime: {uptime}
    Today's Trades: {stats.get("total_trades", 0)}
    Portfolio: {portfolio_text}
    """

        await self.send_reply(message, reply)

    # CHANGE 3: Stop Command Message
    async def cmd_stop_bot(self, message):
        """Handle /stop command with RESUME reference"""
        try:
            if self.trading_bot.running:
                self.trading_bot.running = False
                self.restart_requested = False

                try:
                    self.trade_logger.log_bot_event(
                        "PAUSE",
                        "Trading paused via Telegram command",
                        "TELEGRAM",
                        "INFO",
                    )
                except Exception as log_error:
                    self.logger.warning(f"Failed to log pause event: {log_error}")

                await self.send_reply(
                    message,
                    "🛑 *Trading paused*\n\nBot is still running but not trading.\nSend /resume to restart trading.",
                )
            else:
                await self.send_reply(message, "ℹ️ Trading is already paused.")
        except Exception as e:
            self.logger.error(f"Error in cmd_stop_bot: {e}")
            await self.send_reply(message, "❌ Error pausing trading")

    # CHANGE 4: Keep the method name but update the docstring
    async def cmd_start_bot(self, message):
        """Handle /resume command - Resume trading"""
        self.logger.info("🔄 Processing resume command")

        try:
            if not self.trading_bot.running:
                self.trading_bot.running = True
                self.restart_requested = True
                self.trading_bot.consecutive_failures = 0

                try:
                    self.trade_logger.log_bot_event(
                        "RESUME",
                        "Trading resumed via Telegram /resume command",
                        "TELEGRAM",
                        "INFO",
                    )
                except Exception as log_error:
                    self.logger.warning(f"Failed to log resume event: {log_error}")

                await self.send_reply(
                    message,
                    "🚀 *Trading resumed*\n\nBot is now actively monitoring and trading.",
                )
            else:
                await self.send_reply(message, "ℹ️ Trading is already active.")
        except Exception as e:
            self.logger.error(f"Error in cmd_start_bot: {e}")
            await self.send_reply(message, "❌ Error resuming trading")

    async def cmd_status(self, message):
        """Comprehensive status report"""
        try:
            status = "🟢 Running" if self.trading_bot.running else "🔴 Stopped"
            uptime = self.get_uptime()

            # Get recent stats
            stats_1d = self.trade_logger.get_trading_statistics(1)

            # Get grid status
            ada_filled = (
                len(self.trading_bot.ada_grid.filled_orders)
                if hasattr(self.trading_bot, "ada_grid")
                else 0
            )
            avax_filled = (
                len(self.trading_bot.avax_grid.filled_orders)
                if hasattr(self.trading_bot, "avax_grid")
                else 0
            )

            # System health
            health_status = "🟢 Healthy"
            if hasattr(self.trading_bot, "consecutive_failures"):
                if self.trading_bot.consecutive_failures > 2:
                    health_status = "⚠️ Warning"
                elif self.trading_bot.consecutive_failures >= 5:
                    health_status = "🔴 Critical"

            reply = f"""📊 *Comprehensive Bot Status*

*🤖 System Status:*
Status: {status}
Health: {health_status}
Uptime: {uptime}

*📈 Trading Activity (24h):*
• Trades Executed: {stats_1d.get("total_trades", 0)}
• Volume Traded: ${stats_1d.get("total_volume", 0):.2f}
• Commission Paid: ${stats_1d.get("total_commission", 0):.4f}

*📊 Grid Status:*
• ADA Grid: {ada_filled} orders filled
• AVAX Grid: {avax_filled} orders filled
• Grid Health: {"🟢 Active" if getattr(self.trading_bot, "grid_initialized", False) else "🔴 Inactive"}
"""

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting status: {str(e)[:100]}")

    async def cmd_recent_trades(self, message):
        """Enhanced recent trades - FIXED formatting"""
        try:
            trades = self.trade_logger.get_recent_trades(8, 48)  # Last 8 trades in 48h

            if not trades:
                await self.send_reply(
                    message, "📈 No recent trades found in the last 48 hours."
                )
                return

            reply = "📈 *Recent Trading Activity:*\n\n"

            for trade in trades:
                timestamp = trade["timestamp"][:16]
                side_emoji = "🟢" if trade["side"] == "BUY" else "🔴"

                # Format trade details
                symbol = trade["symbol"]
                quantity = trade["quantity"]
                price = trade["price"]
                value = trade["total_value"]
                level = trade.get("grid_level", "N/A")

                reply += f"{side_emoji} *{symbol}* {trade['side']}\n"
                reply += f"   📦 Qty: `{quantity:.6f}` @ `${price:.6f}`\n"
                reply += f"   💰 Value: `${value:.2f}` | Level: `{level}`\n"
                reply += f"   🕐 {timestamp}\n\n"

            # Add summary
            total_volume = sum(trade["total_value"] for trade in trades)
            buy_count = len([t for t in trades if t["side"] == "BUY"])
            sell_count = len([t for t in trades if t["side"] == "SELL"])

            reply += "*📊 Summary:*\n"
            reply += f"Total Volume: `${total_volume:.2f}`\n"
            reply += f"Buy/Sell: `{buy_count}/{sell_count}` orders"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting trades: {str(e)[:100]}")

    async def cmd_portfolio(self, message):
        """Handle /portfolio command - FIXED formatting"""
        try:
            portfolio, total_value = await self.trading_bot.get_portfolio_status()

            reply = "💰 *Portfolio Summary*\n\n"
            reply += f"Total Value: `${total_value:.2f}`\n\n"

            if portfolio:
                for asset, data in portfolio.items():
                    balance = data.get("balance", 0)
                    value = data.get("value", 0)
                    if balance > 0:
                        percentage = (
                            (value / total_value * 100) if total_value > 0 else 0
                        )
                        reply += f"• {asset}: `{balance:.6f}` (${value:.2f} - {percentage:.1f}%)\n"
            else:
                reply += "No portfolio data available."

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting portfolio: {str(e)[:100]}"
            )

    async def cmd_balance(self, message):
        """Handle /balance command - FIXED formatting"""
        try:
            balances = self.trading_bot.binance.get_account_balance()

            reply = "💳 *Account Balances:*\n\n"

            if balances:
                for balance in balances:
                    if balance["total"] > 0.001:  # Only show significant balances
                        reply += f"• {balance['asset']}: `{balance['free']:.6f}`\n"
                        if balance["locked"] > 0:
                            reply += f"  (Locked: `{balance['locked']:.6f}`)\n"
            else:
                reply = "No balance data available."

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting balances: {str(e)[:100]}")

    async def cmd_stats(self, message):
        """Handle /stats command - Show trading statistics"""
        try:
            stats_1d = self.trade_logger.get_trading_statistics(1)
            stats_7d = self.trade_logger.get_trading_statistics(7)

            reply = f"""📊 *Trading Statistics*

*Last 24 Hours:*
• Trades: {stats_1d.get("total_trades", 0)}
• Volume: ${stats_1d.get("total_volume", 0):.2f}
• Commission: ${stats_1d.get("total_commission", 0):.4f}

*Last 7 Days:*
• Trades: {stats_7d.get("total_trades", 0)}
• Volume: ${stats_7d.get("total_volume", 0):.2f}
• Commission: ${stats_7d.get("total_commission", 0):.4f}
• Symbols Traded: {stats_7d.get("symbols_traded", 0)}
• Avg Trade Size: ${stats_7d.get("avg_trade_size", 0):.2f}
"""

            if stats_7d.get("avg_execution_time"):
                reply += f"• Avg Execution: {stats_7d['avg_execution_time']:.0f}ms"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting statistics: {str(e)[:100]}"
            )

    async def cmd_grid_status(self, message):
        """Detailed grid trading status - FIXED formatting"""
        try:
            reply = "🎯 *Grid Trading Status*\n\n"

            # ADA Grid
            if hasattr(self.trading_bot, "ada_grid"):
                ada_grid = self.trading_bot.ada_grid
                ada_filled = len(ada_grid.filled_orders)
                ada_buy_filled = len(
                    [o for o in ada_grid.filled_orders if o.get("side") == "BUY"]
                )
                ada_sell_filled = len(
                    [o for o in ada_grid.filled_orders if o.get("side") == "SELL"]
                )
                ada_volume = sum(
                    o.get("total_value", 0) for o in ada_grid.filled_orders
                )

                reply += "*💎 ADA Grid:*\n"
                reply += f"• Total Orders: `{ada_filled}/{getattr(ada_grid, 'num_grids', 8) * 2}`\n"
                reply += f"• Buy/Sell: `{ada_buy_filled}/{ada_sell_filled}`\n"
                reply += f"• Volume: `${ada_volume:.2f}`\n"
                reply += (
                    f"• Grid Size: `{getattr(ada_grid, 'grid_size', 0) * 100:.1f}%`\n\n"
                )

            # AVAX Grid
            if hasattr(self.trading_bot, "avax_grid"):
                avax_grid = self.trading_bot.avax_grid
                avax_filled = len(avax_grid.filled_orders)
                avax_buy_filled = len(
                    [o for o in avax_grid.filled_orders if o.get("side") == "BUY"]
                )
                avax_sell_filled = len(
                    [o for o in avax_grid.filled_orders if o.get("side") == "SELL"]
                )
                avax_volume = sum(
                    o.get("total_value", 0) for o in avax_grid.filled_orders
                )

                reply += "*🔺 AVAX Grid:*\n"
                reply += f"• Total Orders: `{avax_filled}/{getattr(avax_grid, 'num_grids', 8) * 2}`\n"
                reply += f"• Buy/Sell: `{avax_buy_filled}/{avax_sell_filled}`\n"
                reply += f"• Volume: `${avax_volume:.2f}`\n"
                reply += f"• Grid Size: `{getattr(avax_grid, 'grid_size', 0) * 100:.1f}%`\n\n"

            # Recent grid activity
            recent_trades = self.trade_logger.get_recent_trades(3, 24)
            if recent_trades:
                reply += "*🎯 Recent Grid Activity:*\n"
                for trade in recent_trades:
                    side_emoji = "🟢" if trade["side"] == "BUY" else "🔴"
                    reply += f"{side_emoji} {trade['symbol']} Level {trade.get('grid_level', '?')}\n"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting grid status: {str(e)[:100]}"
            )

    async def cmd_health_check(self, message):
        """System health check - FIXED formatting"""
        try:
            health_report = "🏥 *System Health Check*\n\n"

            # API Health
            try:
                api_healthy = (
                    await self.trading_bot.check_api_health()
                    if hasattr(self.trading_bot, "check_api_health")
                    else True
                )
                health_report += f"🌐 API Connection: {'🟢 Healthy' if api_healthy else '🔴 Issues'}\n"
            except:
                health_report += "🌐 API Connection: ❓ Unknown\n"

            # Database Health
            try:
                db_healthy = True  # Simple check - if we can query recent trades
                self.trade_logger.get_recent_trades(1)
                health_report += (
                    f"💾 Database: {'🟢 Healthy' if db_healthy else '🔴 Issues'}\n"
                )
            except:
                health_report += "💾 Database: 🔴 Issues\n"

            # Grid Health
            grid_healthy = getattr(self.trading_bot, "grid_initialized", False)
            health_report += (
                f"🎯 Grid System: {'🟢 Active' if grid_healthy else '🔴 Inactive'}\n"
            )

            # Error Count
            consecutive_failures = getattr(self.trading_bot, "consecutive_failures", 0)
            if consecutive_failures == 0:
                health_report += "⚡ Error Status: 🟢 No recent failures\n"
            elif consecutive_failures < 3:
                health_report += (
                    f"⚡ Error Status: ⚠️ {consecutive_failures} recent failures\n"
                )
            else:
                health_report += (
                    f"⚡ Error Status: 🔴 {consecutive_failures} consecutive failures\n"
                )

            health_report += (
                f"\n*🕐 Last Updated:* {datetime.now().strftime('%H:%M:%S')}"
            )

            await self.send_reply(message, health_report)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error performing health check: {str(e)[:100]}"
            )

    async def cmd_performance(self, message):
        """Handle /performance command - Show performance metrics"""
        try:
            performance = self.trade_logger.get_performance_summary()

            today = performance.get("today", {})
            week = performance.get("week", {})
            recent_trades = performance.get("recent_trades", [])
            uptime = performance.get("session_uptime", 0)

            reply = f"""📈 *Performance Summary*

*🕐 Session Info:*
• Uptime: {uptime / 3600:.1f} hours

*📊 Today's Performance:*
• Trades: {today.get("total_trades", 0)}
• Volume: ${today.get("total_volume", 0):.2f}
• Commission Rate: {today.get("commission_rate", 0):.3f}%

*📈 Weekly Performance:*
• Total Trades: {week.get("total_trades", 0)}
• Total Volume: ${week.get("total_volume", 0):.2f}
• Average Trade: ${week.get("avg_trade_size", 0):.2f}
"""

            if recent_trades:
                reply += "\\n*🎯 Last Trade:*\\n"
                last_trade = recent_trades[0]
                side_emoji = "🟢" if last_trade["side"] == "BUY" else "🔴"
                reply += f"{side_emoji} {last_trade['symbol']} ${last_trade['total_value']:.2f}"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting performance: {str(e)[:100]}"
            )

    async def cmd_reset(self, message):
        """Handle /reset command with proper confirmation"""
        try:
            text = message["text"].strip()

            if text == "/reset confirm":
                # Actually perform the reset
                try:
                    # Clear ADA grid state
                    if hasattr(self.trading_bot, "ada_grid_persistence"):
                        self.trading_bot.ada_grid_persistence.clear_state()
                        self.trading_bot.ada_grid.filled_orders = []

                    # Clear AVAX grid state
                    if hasattr(self.trading_bot, "avax_grid_persistence"):
                        self.trading_bot.avax_grid_persistence.clear_state()
                        self.trading_bot.avax_grid.filled_orders = []

                    # Reset grid initialization flag
                    self.trading_bot.grid_initialized = False

                    # Log the reset
                    self.trade_logger.log_bot_event(
                        "GRID_RESET",
                        "Grid state reset via Telegram command",
                        "TELEGRAM",
                        "INFO",
                    )

                    await self.send_reply(
                        message,
                        "✅ *Grid state reset complete!*\n\n"
                        "• All filled orders cleared\n"
                        "• Grid levels reset\n"
                        "• Fresh grids will be created on next cycle\n\n"
                        "Trading continues with clean state.",
                    )

                except Exception as e:
                    await self.send_reply(
                        message, f"❌ Error during reset: {str(e)[:100]}"
                    )

            else:
                # Show confirmation message
                reply = "⚠️ *Grid State Reset*\n\n"
                reply += "This will clear all saved grid states and restart with fresh grids.\n\n"
                reply += "**WARNING:** This will:\n"
                reply += "• Clear all filled order history\n"
                reply += "• Reset grid levels\n"
                reply += "• Lose current position tracking\n\n"
                reply += (
                    "Send `/reset confirm` to proceed or any other message to cancel."
                )

                await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error in reset: {str(e)[:100]}")

    async def cmd_recent_errors(self, message):
        """Handle /errors command - Show recent errors"""
        try:
            failures = getattr(self.trading_bot, "consecutive_failures", 0)

            reply = f"""🔍 *Error Status*

*Current Status:*
• Consecutive Failures: {failures}
• Health Status: {"🟢 Healthy" if failures == 0 else "⚠️ Issues" if failures < 3 else "🔴 Critical"}

*Recent Issues:*
"""

            if failures == 0:
                reply += "✅ No recent failures detected"
            else:
                reply += f"⚠️ {failures} consecutive failures\\n"
                reply += "Check logs for detailed error information"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting error status: {str(e)[:100]}"
            )

    async def cmd_help(self, message):
        """Handle /help command - Show help information"""
        await self.cmd_start(message)  # Redirect to start command which shows help

    def get_uptime(self) -> str:
        """Get formatted uptime"""
        try:
            if hasattr(self.trading_bot, "start_time"):
                uptime_seconds = time.time() - self.trading_bot.start_time
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                if hours > 0:
                    return f"{hours}h {minutes}m"
                else:
                    return f"{minutes}m"
            return "Unknown"
        except:
            return "Unknown"
