# utils/telegram_commands.py
import asyncio
import time
from datetime import datetime
from typing import Dict

import requests


class TelegramBotCommands:
    """Database Telegram bot command handler"""

    def __init__(self, trading_bot, telegram_notifier, db_logger):
        self.trading_bot = trading_bot
        self.telegram_notifier = telegram_notifier
        self.db_logger = db_logger

        # Command handlers
        self.commands = {
            "/start": self.cmd_start,
            "/stop": self.cmd_stop_bot,
            "/resume": self.cmd_resume_bot,
            "/status": self.cmd_status,
            "/trades": self.cmd_recent_trades,
            "/portfolio": self.cmd_portfolio,
            "/balance": self.cmd_balance,
            "/stats": self.cmd_stats,
            "/health": self.cmd_health_check,
            "/reset": self.cmd_reset,
            "/help": self.cmd_help,
            "/performance": self.cmd_performance,
            "/events": self.cmd_recent_events,
            "/db": self.cmd_database_stats,
        }

        self.last_update_id = 0
        self.command_processor_running = False
        self.command_history = []
        self.rate_limit = {}
        self.restart_requested = False

    async def start_command_processor(self):
        """Start command processor"""
        if not self.telegram_notifier.enabled:
            return

        self.command_processor_running = True
        print("🤖 Database Telegram command processor started")

        while self.command_processor_running:
            try:
                await self.process_updates()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error in command processor: {e}")
                await asyncio.sleep(5)

    def stop_command_processor(self):
        """Stop command processor"""
        self.command_processor_running = False
        print("🛑 Telegram command processor stopped")

    async def process_updates(self):
        """Process telegram updates"""
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
                print(f"Error processing updates: {e}")

    async def handle_update(self, update: Dict):
        """Handle incoming update"""
        try:
            if "message" not in update:
                return

            message = update["message"]

            # Security check
            if str(message["chat"]["id"]) != str(self.telegram_notifier.chat_id):
                return

            if "text" not in message:
                return

            text = message["text"].strip()
            user_id = message["from"]["id"]

            # Rate limiting
            if self._is_rate_limited(user_id, text):
                await self.send_reply(
                    message, "⏱️ Please wait before sending another command."
                )
                return

            # Log command to database
            self.db_logger.log_bot_event(
                "TELEGRAM_COMMAND",
                f"Command received: {text}",
                "TELEGRAM",
                "INFO",
                {"user_id": user_id, "command": text},
                self.trading_bot.session_id,
            )

            # Execute command
            for command, handler in self.commands.items():
                if text.startswith(command):
                    print(f"📱 Executing command: {command}")
                    try:
                        await handler(message)
                    except Exception as e:
                        print(f"Error executing command {command}: {e}")
                        await self.send_reply(message, f"❌ Error: {str(e)[:100]}")
                    break
            else:
                if text.startswith("/"):
                    await self.send_reply(
                        message,
                        "❓ Unknown command. Send /help for available commands.",
                    )

        except Exception as e:
            print(f"Error handling update: {e}")

    def _is_rate_limited(self, user_id: int, command: str) -> bool:
        """Simple rate limiting"""
        now = time.time()
        key = f"{user_id}_{command}"

        if key in self.rate_limit:
            if now - self.rate_limit[key] < 2:
                return True

        self.rate_limit[key] = now
        return False

    async def send_reply(
        self, original_message: Dict, text: str, parse_mode: str = "Markdown"
    ):
        """Send reply to Telegram"""
        try:
            cleaned_text = text.replace("_", "\\_")

            if len(cleaned_text) > 4000:
                cleaned_text = cleaned_text[:3950] + "\n\n... (truncated)"

            url = f"https://api.telegram.org/bot{self.telegram_notifier.bot_token}/sendMessage"
            payload = {
                "chat_id": original_message["chat"]["id"],
                "text": cleaned_text,
                "parse_mode": parse_mode,
                "reply_to_message_id": original_message["message_id"],
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code != 200:
                # Try without markdown
                payload["parse_mode"] = None
                requests.post(url, json=payload, timeout=10)

            return True

        except Exception as e:
            print(f"Error sending reply: {e}")
            return False

    # =============================================================================
    # COMMAND HANDLERS
    # =============================================================================

    async def cmd_start(self, message):
        """Enhanced start command"""
        uptime = self.get_uptime()

        # Get stats from database
        stats = self.db_logger.get_trading_statistics(1)

        # Get portfolio value
        portfolio_text = "Loading..."
        try:
            portfolio, total_value = await self.trading_bot.get_portfolio_status()
            portfolio_text = f"${total_value:.2f}"
        except:
            pass

        reply = f"""🤖 *Database Trading Bot*

*🎛️ Bot Control:*
/resume - Start trading
/stop - Stop trading  
/status - Bot status
/health - System health

*📊 Data & Analytics:*
/portfolio - Portfolio summary
/balance - Account balances
/trades - Recent trades
/stats - Trading statistics
/performance - Performance metrics
/events - Recent events

*🔧 Management:*
/reset - Reset grids
/db - Database statistics
/help - This help menu

*📈 Current Status:*
Bot: {"🟢 Running" if self.trading_bot.running else "🔴 Stopped"}
Uptime: {uptime}
Today's Trades: {stats.get("total_trades", 0)}
Portfolio: {portfolio_text}

*🗄️ All data stored in SQLite database*
"""
        await self.send_reply(message, reply)

    async def cmd_stop_bot(self, message):
        """Stop trading"""
        try:
            if self.trading_bot.running:
                self.trading_bot.running = False
                self.restart_requested = False

                # Log to database
                self.db_logger.log_bot_event(
                    "TRADING_PAUSED",
                    "Trading paused via Telegram /stop command",
                    "TELEGRAM",
                    "INFO",
                    {},
                    self.trading_bot.session_id,
                )

                await self.send_reply(
                    message,
                    "🛑 *Trading Paused*\n\nBot is still running but not trading.\nSend /resume to restart trading.",
                )
            else:
                await self.send_reply(message, "ℹ️ Trading is already paused.")
        except Exception:
            await self.send_reply(message, "❌ Error pausing trading")

    async def cmd_resume_bot(self, message):
        """Resume trading"""
        try:
            if not self.trading_bot.running:
                self.trading_bot.running = True
                self.restart_requested = True
                self.trading_bot.consecutive_failures = 0

                # Log to database
                self.db_logger.log_bot_event(
                    "TRADING_RESUMED",
                    "Trading resumed via Telegram /resume command",
                    "TELEGRAM",
                    "INFO",
                    {},
                    self.trading_bot.session_id,
                )

                await self.send_reply(
                    message,
                    "🚀 *Trading Resumed*\n\nBot is now actively monitoring and trading.",
                )
            else:
                await self.send_reply(message, "ℹ️ Trading is already active.")
        except Exception:
            await self.send_reply(message, "❌ Error resuming trading")

    async def cmd_status(self, message):
        """Get bot status from database"""
        try:
            status = "🟢 Running" if self.trading_bot.running else "🔴 Stopped"
            uptime = self.get_uptime()

            # Get stats from database
            stats_1d = self.db_logger.get_trading_statistics(1)

            # Get grid status from memory
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
            failures = getattr(self.trading_bot, "consecutive_failures", 0)
            if failures > 2:
                health_status = "⚠️ Warning"
            elif failures >= 5:
                health_status = "🔴 Critical"

            reply = f"""📊 *Bot Status (Database-Only)*

*🤖 System:*
Status: {status}
Health: {health_status}
Uptime: {uptime}
Failures: {failures}

*📈 Trading (24h):*
• Trades: {stats_1d.get("total_trades", 0)}
• Volume: ${stats_1d.get("total_volume", 0):.2f}
• Commission: ${stats_1d.get("total_commission", 0):.4f}

*📊 Grid Status:*
• ADA Orders: {ada_filled}
• AVAX Orders: {avax_filled}
• Grid Active: {"🟢 Yes" if getattr(self.trading_bot, "grid_initialized", False) else "🔴 No"}

*🗄️ Data Source: SQLite Database*
"""
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting status: {str(e)[:100]}")

    async def cmd_recent_trades(self, message):
        """Get recent trades from database"""
        try:
            trades = self.db_logger.get_recent_trades(8, 48)

            if not trades:
                await self.send_reply(message, "📈 No recent trades in database.")
                return

            reply = "📈 *Recent Trades (from Database):*\n\n"

            for trade in trades:
                timestamp = trade["timestamp"][:16] if trade["timestamp"] else "Unknown"
                side_emoji = "🟢" if trade["side"] == "BUY" else "🔴"

                symbol = trade["symbol"]
                quantity = trade["quantity"]
                price = trade["price"]
                value = trade["total_value"]
                level = trade.get("grid_level", "N/A")

                reply += f"{side_emoji} *{symbol}* {trade['side']}\n"
                reply += f"   📦 Qty: `{quantity:.6f}` @ `${price:.6f}`\n"
                reply += f"   💰 Value: `${value:.2f}` | Level: `{level}`\n"
                reply += f"   🕐 {timestamp}\n\n"

            # Summary
            total_volume = sum(trade["total_value"] for trade in trades)
            buy_count = len([t for t in trades if t["side"] == "BUY"])
            sell_count = len([t for t in trades if t["side"] == "SELL"])

            reply += "*📊 Summary:*\n"
            reply += f"Total Volume: `${total_volume:.2f}`\n"
            reply += f"Buy/Sell: `{buy_count}/{sell_count}`"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting trades: {str(e)[:100]}")

    async def cmd_portfolio(self, message):
        """Get portfolio from live API and database history"""
        try:
            portfolio, total_value = await self.trading_bot.get_portfolio_status()

            reply = "💰 *Portfolio Summary*\n\n"
            reply += f"Total Value: `${total_value:.2f}`\n\n"

            if portfolio:
                reply += "*💎 Holdings:*\n"
                for asset, data in portfolio.items():
                    quantity = data.get("quantity", 0)
                    value = data.get("usd_value", 0)
                    if quantity > 0:
                        percentage = (
                            (value / total_value * 100) if total_value > 0 else 0
                        )
                        reply += f"• {asset}: `{quantity:.6f}` (${value:.2f} - {percentage:.1f}%)\n"

            # Get recent portfolio history from database
            history = self.db_logger.get_portfolio_history(7)
            if history:
                reply += "\n*📈 Recent History:*\n"
                reply += f"Records in database: {len(history)}\n"
                if len(history) > 1:
                    oldest = history[-1]["total_value"]
                    change = total_value - oldest
                    change_pct = (change / oldest * 100) if oldest > 0 else 0
                    reply += f"7-day change: `${change:+.2f}` ({change_pct:+.1f}%)"

            reply += "\n\n*🗄️ Data from: Live API + Database History*"
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting portfolio: {str(e)[:100]}"
            )

    async def cmd_balance(self, message):
        """Get account balances"""
        try:
            balances = self.trading_bot.binance.get_account_balance()

            reply = "💳 *Account Balances:*\n\n"

            if balances:
                for balance in balances:
                    if balance["total"] > 0.001:
                        reply += f"• {balance['asset']}: `{balance['free']:.6f}`\n"
                        if balance["locked"] > 0:
                            reply += f"  (Locked: `{balance['locked']:.6f}`)\n"
            else:
                reply = "No balance data available."

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting balances: {str(e)[:100]}")

    async def cmd_stats(self, message):
        """Get trading statistics"""
        try:
            stats_1d = self.db_logger.get_trading_statistics(1)
            stats_7d = self.db_logger.get_trading_statistics(7)

            reply = f"""📊 *Trading Statistics*

*Last 24 Hours:*
• Trades: {stats_1d.get("total_trades", 0)}
• Volume: ${stats_1d.get("total_volume", 0):.2f}
• Commission: ${stats_1d.get("total_commission", 0):.4f}
• Avg Trade: ${stats_1d.get("avg_trade_size", 0):.2f}

*Last 7 Days:*
• Trades: {stats_7d.get("total_trades", 0)}
• Volume: ${stats_7d.get("total_volume", 0):.2f}
• Commission: ${stats_7d.get("total_commission", 0):.4f}
• Symbols: {stats_7d.get("symbols_traded", 0)}
• Avg Trade: ${stats_7d.get("avg_trade_size", 0):.2f}
• Commission Rate: {stats_7d.get("commission_rate", 0):.3f}%
"""

            if stats_7d.get("avg_execution_time"):
                reply += f"• Avg Execution: {stats_7d['avg_execution_time']:.0f}ms"

            reply += "\n\n*🗄️ Source: SQLite*"
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting statistics: {str(e)[:100]}"
            )

    async def cmd_health_check(self, message):
        """System health check"""
        try:
            health_report = "🏥 *System Health Check*\n\n"

            # API Health
            try:
                api_healthy = self.trading_bot.binance.test_connection()
                health_report += (
                    f"🌐 API: {'🟢 Healthy' if api_healthy else '🔴 Issues'}\n"
                )
            except:
                health_report += "🌐 API: ❓ Unknown\n"

            # Database Health
            try:
                db_stats = self.db_logger.get_database_stats()
                trades_count = db_stats.get("trades_count", 0)
                db_size = db_stats.get("database_size_mb", 0)
                health_report += (
                    f"💾 Database: 🟢 Healthy ({trades_count} trades, {db_size}MB)\n"
                )
            except:
                health_report += "💾 Database: 🔴 Issues\n"

            # Grid Health
            grid_healthy = getattr(self.trading_bot, "grid_initialized", False)
            health_report += (
                f"🎯 Grid: {'🟢 Active' if grid_healthy else '🔴 Inactive'}\n"
            )

            # Error Status
            failures = getattr(self.trading_bot, "consecutive_failures", 0)
            if failures == 0:
                health_report += "⚡ Errors: 🟢 No recent failures\n"
            elif failures < 3:
                health_report += f"⚡ Errors: ⚠️ {failures} recent failures\n"
            else:
                health_report += f"⚡ Errors: 🔴 {failures} consecutive failures\n"

            health_report += f"\n*🕐 Last Check:* {datetime.now().strftime('%H:%M:%S')}"
            await self.send_reply(message, health_report)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error performing health check: {str(e)[:100]}"
            )

    async def cmd_performance(self, message):
        """Get performance summary"""
        try:
            performance = self.db_logger.get_performance_summary()

            today = performance.get("today", {})
            week = performance.get("week", {})
            uptime = performance.get("session_uptime", 0)

            reply = f"""📈 *Performance*

*🕐 Session:*
• Uptime: {uptime / 3600:.1f} hours

*📊 Today:*
• Trades: {today.get("total_trades", 0)}
• Volume: ${today.get("total_volume", 0):.2f}
• Commission: ${today.get("total_commission", 0):.4f}

*📈 This Week:*
• Trades: {week.get("total_trades", 0)}
• Volume: ${week.get("total_volume", 0):.2f}
• Avg Trade: ${week.get("avg_trade_size", 0):.2f}
• Commission Rate: {week.get("commission_rate", 0):.3f}%
"""

            recent_trades = performance.get("recent_trades", [])
            if recent_trades:
                last_trade = recent_trades[0]
                side_emoji = "🟢" if last_trade["side"] == "BUY" else "🔴"
                reply += f"\n*🎯 Last Trade:*\n{side_emoji} {last_trade['symbol']} ${last_trade['total_value']:.2f}"

            reply += "\n\n*🗄️ Data from SQLite*"
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting performance: {str(e)[:100]}"
            )

    async def cmd_recent_events(self, message):
        """Get recent events"""
        try:
            events = self.db_logger.get_recent_events(10)

            if not events:
                await self.send_reply(message, "📋 No recent events.")
                return

            reply = "📋 *Recent Events:*\n\n"

            for event in events:
                timestamp = event["timestamp"][:16] if event["timestamp"] else "Unknown"
                event_type = event["event_type"]
                severity = event["severity"]
                message_text = (
                    event["message"][:50] + "..."
                    if len(event["message"]) > 50
                    else event["message"]
                )

                # Severity emojis
                severity_emoji = {
                    "CRITICAL": "🚨",
                    "ERROR": "❌",
                    "WARNING": "⚠️",
                    "INFO": "ℹ️",
                    "DEBUG": "🔍",
                }.get(severity, "📝")

                reply += f"{severity_emoji} *{event_type}*\n"
                reply += f"   {message_text}\n"
                reply += f"   🕐 {timestamp}\n\n"

            reply += "*🗄️ Source: SQLite*"
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error getting events: {str(e)[:100]}")

    async def cmd_database_stats(self, message):
        """Get database statistics"""
        try:
            stats = self.db_logger.get_database_stats()

            if not stats:
                await self.send_reply(message, "❌ Could not get database statistics.")
                return

            reply = f"""🗄️ *Database Statistics*

*📊 Record Counts:*
• Trades: {stats.get("trades_count", 0):,}
• Portfolio Snapshots: {stats.get("portfolio_snapshots_count", 0):,}
• Bot Events: {stats.get("bot_events_count", 0):,}
• Performance Metrics: {stats.get("performance_metrics_count", 0):,}

*💾 Storage:*
• Database Size: {stats.get("database_size_mb", 0):.2f} MB
• Trades (24h): {stats.get("trades_last_24h", 0)}

*🎯 Single Source of Truth*
All data stored in SQLite
"""

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Error getting database stats: {str(e)[:100]}"
            )

    async def cmd_reset(self, message):
        """Reset grids"""
        try:
            ada_price = self.trading_bot.binance.get_price("ADAUSDT")
            avax_price = self.trading_bot.binance.get_price("AVAXUSDT")

            if ada_price and avax_price:
                # Reset grids
                self.trading_bot.ada_grid.setup_grid(ada_price)
                self.trading_bot.avax_grid.setup_grid(avax_price)

                # Log to database
                self.db_logger.log_bot_event(
                    "GRID_RESET",
                    f"Grids reset via Telegram - ADA: ${ada_price:.4f}, AVAX: ${avax_price:.4f}",
                    "TELEGRAM",
                    "INFO",
                    {"ada_price": ada_price, "avax_price": avax_price},
                    self.trading_bot.session_id,
                )

                await self.send_reply(
                    message,
                    f"🔄 *Grids Reset*\n\n"
                    f"ADA: Fresh grid at ${ada_price:.4f}\n"
                    f"AVAX: Fresh grid at ${avax_price:.4f}\n"
                    f"All levels cleared and recreated\n\n"
                    f"*Reset logged to database*",
                )
            else:
                await self.send_reply(
                    message, "❌ Could not get current prices for reset"
                )

        except Exception as e:
            await self.send_reply(message, f"❌ Error resetting grids: {str(e)[:100]}")

    async def cmd_help(self, message):
        """Show help"""
        await self.cmd_start(message)

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
