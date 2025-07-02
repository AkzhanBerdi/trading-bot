# trading_bot/utils/telegram_commands.py - COMPLETE VERSION WITH COMPOUNDING
"""Complete Telegram Commands - Essential Bot Control + Compounding"""

import asyncio
import time
from typing import Dict

import requests


class TelegramBotCommands:
    """Complete bot control commands with compounding"""

    def __init__(self, trading_bot, telegram_notifier, db_logger):
        self.trading_bot = trading_bot
        self.telegram_notifier = telegram_notifier
        self.db_logger = db_logger

        # COMPLETE commands - essential bot control + Phase 1 & 2 enhancements
        self.commands = {
            "/start": self.cmd_start,
            "/stop": self.cmd_smart_stop,
            "/resume": self.cmd_smart_resume,
            "/status": self.cmd_simple_status,
            "/risk": self.cmd_risk_status,
            "/reset": self.cmd_reset,
            "/grid": self.cmd_grid_visualization,  # Phase 1: Grid visualization
            "/compound": self.cmd_compound_status,  # Phase 2: Compound interest ✅ FIXED!
            "/help": self.cmd_start,
        }

        self.last_update_id = 0
        self.command_processor_running = False
        self.rate_limit = {}
        self.restart_requested = False

    # =============================================================================
    # ESSENTIAL COMMANDS
    # =============================================================================

    async def cmd_start(self, message):
        """Complete start/help command with compounding info"""
        try:
            uptime = self.get_uptime()
            risk_info = self.trading_bot.risk_manager.get_risk_status()
            compound_info = self.trading_bot.compound_manager.get_compound_status()

            mode_emoji = {
                "NORMAL": "🟢",
                "CONSERVATIVE": "🟡",
                "EMERGENCY_STOP": "🔴",
                "CIRCUIT_BREAKER": "🚨",
            }.get(risk_info["mode"], "❓")

            reply = f"""🤖 **Complete Grid Trading Bot**

**Essential Controls:**
/stop - Stop trading
/resume - Resume trading  
/status - Bot status
/risk - Risk status
/reset - Reset grids

**Advanced Features:**
/grid - Grid visualization
/compound - Compound status

**Current Status:**
• Bot: {"🟢 Running" if self.trading_bot.running else "🔴 Stopped"}  
• Risk: {mode_emoji} {risk_info["mode"]} ({risk_info["daily_pnl"]:+.1f}%)
• Orders: ${compound_info["current_order_size"]:.0f} ({compound_info["profit_increase"]:+.1f}%)
• Uptime: {uptime}

*Compounding active: Profits → Larger orders*
"""
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Error: {str(e)[:100]}")

    async def cmd_smart_stop(self, message):
        """Smart stop with automatic emergency detection"""
        try:
            if not self.trading_bot.running:
                await self.send_reply(message, "ℹ️ Trading is already stopped.")
                return

            # Stop trading
            self.trading_bot.running = False
            self.restart_requested = False

            # Get risk status for smart handling
            risk_info = self.trading_bot.risk_manager.get_risk_status()

            # Smart stop logic
            if risk_info["daily_pnl"] < -1.0:  # Emergency stop for losses
                self.trading_bot.risk_manager.trigger_emergency_stop()
                stop_type = "EMERGENCY"
                icon = "🚨"
                reason = "losses detected"
            else:  # Normal stop
                stop_type = "MANUAL"
                icon = "🛑"
                reason = "manual request"

            # Log to database
            self.db_logger.log_bot_event(
                f"{stop_type}_STOP",
                f"Trading stopped: {reason}",
                "TELEGRAM",
                "WARNING" if stop_type == "EMERGENCY" else "INFO",
                {"stop_type": stop_type, "daily_pnl": risk_info["daily_pnl"]},
                self.trading_bot.session_id,
            )

            await self.send_reply(
                message,
                f"{icon} **Trading Stopped**\n\n"
                f"Reason: {reason}\n"
                f"Daily P&L: {risk_info['daily_pnl']:+.1f}%\n\n"
                f"Use /resume to restart",
            )

        except Exception as e:
            await self.send_reply(message, f"❌ Error stopping: {str(e)[:100]}")

    async def cmd_smart_resume(self, message):
        """Smart resume with risk checking"""
        try:
            if self.trading_bot.running:
                await self.send_reply(message, "ℹ️ Trading is already running.")
                return

            # Check risk status
            risk_info = self.trading_bot.risk_manager.get_risk_status()
            current_mode = risk_info["mode"]

            # Handle different risk states
            if current_mode in ["EMERGENCY_STOP", "CIRCUIT_BREAKER"]:
                # Check if we can auto-resume
                if risk_info["daily_pnl"] > -2.0:  # Conditions improved
                    self.trading_bot.risk_manager.reset_to_normal()
                    await self._do_resume(message, "Risk conditions improved")
                else:
                    # Need manual override
                    await self.send_reply(
                        message,
                        f"⚠️ **Cannot Resume**\n\n"
                        f"Risk mode: {current_mode}\n"
                        f"Daily P&L: {risk_info['daily_pnl']:+.1f}%\n\n"
                        f"Use `/risk override` to force resume",
                    )
            else:
                # Normal resume
                await self._do_resume(message, "Normal resume")

        except Exception as e:
            await self.send_reply(message, f"❌ Error resuming: {str(e)[:100]}")

    async def _do_resume(self, message, reason: str):
        """Actually resume trading - FIXED NoneType error"""
        try:
            self.trading_bot.running = True
            self.restart_requested = True
            self.trading_bot.consecutive_failures = 0

            # Log to database
            self.db_logger.log_bot_event(
                "TRADING_RESUMED",
                f"Trading resumed: {reason}",
                "TELEGRAM",
                "INFO",
                {"reason": reason},
                self.trading_bot.session_id,
            )

            # Get current risk info
            risk_info = self.trading_bot.risk_manager.get_risk_status()

            await self.send_reply(
                message,  # FIXED: was None before
                f"🚀 **Trading Resumed**\n\n"
                f"Reason: {reason}\n"
                f"Risk Mode: {risk_info['mode']}\n"
                f"Daily P&L: {risk_info['daily_pnl']:+.1f}%",
            )

        except Exception as e:
            await self.send_reply(message, f"❌ Resume error: {str(e)[:100]}")

    async def cmd_risk_status(self, message):
        """Risk status with override option"""
        try:
            # Check for override command
            text = message.get("text", "").strip()
            if "override" in text.lower():
                return await self._handle_risk_override(message)

            # Regular risk status
            risk_info = self.trading_bot.risk_manager.get_risk_status()

            mode_emoji = {
                "NORMAL": "🟢",
                "EMERGENCY_STOP": "🔴",
            }.get(risk_info["mode"], "❓")

            reply = f"""🛡️ **Risk Status**
        
**Mode:** {mode_emoji} {risk_info["mode"]}
**Daily P&L:** {risk_info["daily_pnl"]:+.1f}%
**Daily Trades:** {risk_info["daily_trades"]}/{risk_info["risk_limits"]["daily_trade_limit"]}

**Limits:**
• Daily Loss: {risk_info["risk_limits"]["daily_loss_limit"]}%
• Emergency Stop: {risk_info["risk_limits"]["emergency_stop"]}%
"""

            # Add override option if needed
            if risk_info["mode"] == "EMERGENCY_STOP":
                reply += "\n⚠️ Use `/risk override` to force resume"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Risk error: {str(e)[:100]}")

    async def _handle_risk_override(self, message):
        """Handle risk override"""
        try:
            risk_info = self.trading_bot.risk_manager.get_risk_status()
            old_mode = risk_info["mode"]

            # Reset to normal
            self.trading_bot.risk_manager.reset_to_normal()

            # Log override
            self.db_logger.log_bot_event(
                "RISK_OVERRIDE",
                f"Risk override: {old_mode} → NORMAL",
                "TELEGRAM",
                "WARNING",
                {"old_mode": old_mode, "daily_pnl": risk_info["daily_pnl"]},
                self.trading_bot.session_id,
            )

            await self.send_reply(
                message,
                f"⚠️ **Risk Override Applied**\n\n"
                f"{old_mode} → NORMAL\n\n"
                f"Use /resume to restart trading\n"
                f"*Proceed with caution*",
            )

        except Exception as e:
            await self.send_reply(message, f"❌ Override error: {str(e)[:100]}")

    async def cmd_simple_status(self, message):
        """Simple bot status with compound info"""
        try:
            uptime = self.get_uptime()
            failures = getattr(self.trading_bot, "consecutive_failures", 0)
            risk_info = self.trading_bot.risk_manager.get_risk_status()
            compound_info = self.trading_bot.compound_manager.get_compound_status()

            mode_emoji = {
                "NORMAL": "🟢",
                "EMERGENCY_STOP": "🔴",
            }.get(risk_info["mode"], "❓")

            # Grid status
            ada_orders = (
                len(self.trading_bot.ada_grid.filled_orders)
                if hasattr(self.trading_bot, "ada_grid")
                else 0
            )
            avax_orders = (
                len(self.trading_bot.avax_grid.filled_orders)
                if hasattr(self.trading_bot, "avax_grid")
                else 0
            )

            reply = f"""📊 **Bot Status**

**System:**
• Status: {"🟢 Running" if self.trading_bot.running else "🔴 Stopped"}
• Uptime: {uptime}
• Failures: {failures}

**Risk:**
• Mode: {mode_emoji} {risk_info["mode"]}
• Daily P&L: {risk_info["daily_pnl"]:+.1f}%
• Daily Trades: {risk_info["daily_trades"]}/{risk_info["risk_limits"]["daily_trade_limit"]}

**Grids:**
• ADA Orders: {ada_orders}
• AVAX Orders: {avax_orders}
• Active: {"🟢 Yes" if getattr(self.trading_bot, "grid_initialized", False) else "🔴 No"}

**Compounding:**
• Order Size: ${compound_info["current_order_size"]:.0f} (was ${compound_info["base_order_size"]:.0f})
• Multiplier: {compound_info["order_multiplier"]:.2f}x
• Profit Increase: {compound_info["profit_increase"]:+.1f}%

*Check Binance app for portfolio*
"""
            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Status error: {str(e)[:100]}")

    async def cmd_reset(self, message):
        """Reset grid levels with updated compound order sizes"""
        try:
            # Get current prices
            ada_price = self.trading_bot.binance.get_price("ADAUSDT")
            avax_price = self.trading_bot.binance.get_price("AVAXUSDT")

            if not ada_price or not avax_price:
                await self.send_reply(message, "❌ Cannot get current prices")
                return

            # Get current compound order size
            current_order_size = (
                self.trading_bot.compound_manager.get_current_order_size()
            )

            # Update grid traders with new order size FIRST
            self.trading_bot.ada_grid.base_order_size = current_order_size
            self.trading_bot.avax_grid.base_order_size = current_order_size

            # Reset grids with updated order sizes
            self.trading_bot.ada_grid.setup_grid(ada_price)
            self.trading_bot.avax_grid.setup_grid(avax_price)

            # Log to database
            self.db_logger.log_bot_event(
                "GRID_RESET",
                f"Grids reset with compound orders - ADA: ${ada_price:.4f}, AVAX: ${avax_price:.4f}, Order: ${current_order_size:.0f}",
                "TELEGRAM",
                "INFO",
                {
                    "ada_price": ada_price,
                    "avax_price": avax_price,
                    "order_size": current_order_size,
                },
                self.trading_bot.session_id,
            )

            await self.send_reply(
                message,
                f"🔄 **Grids Reset**\n\n"
                f"ADA: ${ada_price:.4f}\n"
                f"AVAX: ${avax_price:.4f}\n"
                f"Order Size: ${current_order_size:.0f}\n\n"
                f"All levels cleared and recreated with compound sizes",
            )

        except Exception as e:
            await self.send_reply(message, f"❌ Reset error: {str(e)[:100]}")

    # =============================================================================
    # PHASE 2: COMPOUND INTEREST COMMAND ✅ COMPLETE!
    # =============================================================================

    async def cmd_compound_status(self, message):
        """Compound interest status and control - Phase 2 complete implementation"""
        try:
            # Check for reset command
            text = message.get("text", "").strip()
            if "reset" in text.lower():
                return await self._handle_compound_reset(message)

            # Get compound status
            compound_info = self.trading_bot.compound_manager.get_compound_status()

            # Build status display
            reply = f"""💰 **Compound Interest Status**

**Current Performance:**
• Order Size: ${compound_info["current_order_size"]:.0f} (base: ${compound_info["base_order_size"]:.0f})
• Multiplier: {compound_info["order_multiplier"]:.3f}x
• Size Increase: {compound_info["profit_increase"]:+.1f}%

**Profit Tracking:**
• Accumulated: ${compound_info["accumulated_profit"]:.2f}
• Reinvestment Rate: {int(compound_info["reinvestment_rate"] * 100)}%
• Max Multiplier: {compound_info["max_multiplier"]:.1f}x

**How It Works:**
• ✅ Bot records profits from sell orders
• ✅ Reinvests {int(compound_info["reinvestment_rate"] * 100)}% into larger order sizes
• ✅ Conservative limits (max {compound_info["max_multiplier"]:.1f}x growth)
• ✅ Automatic - no manual intervention needed

**Growth Trajectory:**
"""

            # Add growth visualization
            base_size = compound_info["base_order_size"]
            current_size = compound_info["current_order_size"]

            if current_size > base_size:
                reply += f"🚀 **GROWING!** Orders {compound_info['profit_increase']:+.1f}% larger\n"
                reply += f"From ${base_size:.0f} → ${current_size:.0f} per trade\n"
            else:
                reply += "📈 **Ready to grow** - accumulating profits...\n"

            # Add reset option
            reply += "\n⚠️ Use `/compound reset` to restart from base size"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(message, f"❌ Compound error: {str(e)[:100]}")

    async def _handle_compound_reset(self, message):
        """Handle compound interest reset"""
        try:
            # Get current status before reset
            old_status = self.trading_bot.compound_manager.get_compound_status()

            # Reset compound manager
            self.trading_bot.compound_manager.reset_compound()

            # Update grid traders to use base order size
            base_size = self.trading_bot.compound_manager.base_order_size
            self.trading_bot.ada_grid.base_order_size = base_size
            self.trading_bot.avax_grid.base_order_size = base_size

            await self.send_reply(
                message,
                f"🔄 **Compound Interest Reset**\n\n"
                f"Old Status:\n"
                f"• Order Size: ${old_status['current_order_size']:.0f}\n"
                f"• Multiplier: {old_status['order_multiplier']:.3f}x\n"
                f"• Accumulated: ${old_status['accumulated_profit']:.2f}\n\n"
                f"New Status:\n"
                f"• Order Size: ${base_size:.0f} (base)\n"
                f"• Multiplier: 1.000x\n"
                f"• Accumulated: $0.00\n\n"
                f"*Compound interest will rebuild from new profits*",
            )

        except Exception as e:
            await self.send_reply(message, f"❌ Compound reset error: {str(e)[:100]}")

    # =============================================================================
    # PHASE 1: GRID VISUALIZATION
    # =============================================================================

    async def cmd_grid_visualization(self, message):
        """Grid visualization - Phase 1 enhancement"""
        try:
            # Get current prices
            ada_price = self.trading_bot.binance.get_price("ADAUSDT")
            avax_price = self.trading_bot.binance.get_price("AVAXUSDT")

            if not ada_price or not avax_price:
                await self.send_reply(message, "❌ Cannot get current prices")
                return

            # Get compound info for context
            compound_info = self.trading_bot.compound_manager.get_compound_status()

            # Build visualization
            reply = "🎯 **Grid Visualization**\n"
            reply += f"*Order Size: ${compound_info['current_order_size']:.0f} ({compound_info['order_multiplier']:.2f}x)*\n\n"

            # ADA Grid
            reply += self._build_grid_display(
                "ADA", ada_price, self.trading_bot.ada_grid
            )
            reply += "\n" + "═" * 25 + "\n\n"

            # AVAX Grid
            reply += self._build_grid_display(
                "AVAX", avax_price, self.trading_bot.avax_grid
            )

            # Add reset guidance
            reply += "\n\n**💡 Reset Guidance:**\n"
            reply += "• If current price is outside grid range\n"
            reply += "• If too many levels above/below current price\n"
            reply += "• Use `/reset` to recreate grids with compound order sizes"

            await self.send_reply(message, reply)

        except Exception as e:
            await self.send_reply(
                message, f"❌ Grid visualization error: {str(e)[:100]}"
            )

    def _build_grid_display(
        self, symbol: str, current_price: float, grid_trader
    ) -> str:
        """Build grid visualization for a symbol"""
        try:
            if not hasattr(grid_trader, "sell_levels") or not hasattr(
                grid_trader, "buy_levels"
            ):
                return f"**{symbol}:** Grid not initialized"

            display = f"**{symbol} Grid (Current: ${current_price:.4f})**\n"
            display += "```\n"

            # Show sell levels (above current price)
            sell_levels = sorted(
                grid_trader.sell_levels, key=lambda x: x["price"], reverse=True
            )
            for level in sell_levels[:6]:  # Show top 6 sell levels
                price = level["price"]
                distance = ((price - current_price) / current_price) * 100
                filled_marker = (
                    "✅"
                    if any(
                        o.get("level") == level["level"] and o.get("side") == "SELL"
                        for o in grid_trader.filled_orders
                    )
                    else "⬜"
                )
                display += f"SELL ${price:.4f} ↑{distance:+5.1f}% {filled_marker}\n"

            # Current price line
            display += "─" * 35 + "\n"
            display += f"NOW  ${current_price:.4f}  ← CURRENT\n"
            display += "─" * 35 + "\n"

            # Show buy levels (below current price)
            buy_levels = sorted(
                grid_trader.buy_levels, key=lambda x: x["price"], reverse=True
            )
            for level in buy_levels[:6]:  # Show top 6 buy levels
                price = level["price"]
                distance = ((price - current_price) / current_price) * 100
                filled_marker = (
                    "✅"
                    if any(
                        o.get("level") == level["level"] and o.get("side") == "BUY"
                        for o in grid_trader.filled_orders
                    )
                    else "⬜"
                )
                display += f"BUY  ${price:.4f} {distance:+5.1f}% {filled_marker}\n"

            display += "```\n"

            # Grid summary
            grid_range_low = (
                grid_trader.buy_levels[-1]["price"]
                if grid_trader.buy_levels
                else current_price
            )
            grid_range_high = (
                grid_trader.sell_levels[-1]["price"]
                if grid_trader.sell_levels
                else current_price
            )

            # Check if current price is within reasonable range
            if current_price < grid_range_low or current_price > grid_range_high:
                display += "⚠️ **OUTSIDE GRID RANGE** - Consider reset\n"
            elif (
                current_price < grid_range_low * 1.1
                or current_price > grid_range_high * 0.9
            ):
                display += "⚠️ **NEAR GRID EDGE** - Monitor for reset\n"
            else:
                display += "✅ **WITHIN GRID RANGE** - Operating normally\n"

            return display

        except Exception as e:
            return f"**{symbol}:** Error displaying grid - {str(e)[:50]}"

    # =============================================================================
    # CORE INFRASTRUCTURE
    # =============================================================================

    async def start_command_processor(self):
        """Start command processor"""
        if not self.telegram_notifier.enabled:
            return

        self.command_processor_running = True
        print("🤖 Complete Telegram commands active (with compounding)")

        while self.command_processor_running:
            try:
                await self.process_updates()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Command processor error: {e}")
                await asyncio.sleep(5)

    def stop_command_processor(self):
        """Stop command processor"""
        self.command_processor_running = False
        print("🛑 Command processor stopped")

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
                print(f"Update processing error: {e}")

    async def handle_update(self, update: Dict):
        """Handle incoming telegram updates"""
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
                await self.send_reply(message, "⏱️ Wait a moment...")
                return

            # Log command
            self.db_logger.log_bot_event(
                "TELEGRAM_COMMAND",
                f"Command: {text}",
                "TELEGRAM",
                "INFO",
                {"command": text},
                self.trading_bot.session_id,
            )

            # Execute command
            for command, handler in self.commands.items():
                if text.startswith(command):
                    print(f"📱 Executing: {command}")
                    try:
                        await handler(message)
                    except Exception as e:
                        print(f"Command error {command}: {e}")
                        await self.send_reply(message, f"❌ Error: {str(e)[:50]}")
                    break
            else:
                if text.startswith("/"):
                    await self.send_reply(message, "❓ Unknown command. Try /help")

        except Exception as e:
            print(f"Update handling error: {e}")

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
        """Send telegram reply"""
        try:
            if not original_message:  # Safety check
                print("⚠️ Cannot send reply - no message object")
                return False

            # Clean text
            cleaned_text = text.replace("_", "\\_")
            if len(cleaned_text) > 4000:
                cleaned_text = cleaned_text[:3950] + "\n\n...(truncated)"

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
                # Retry without markdown
                payload["parse_mode"] = None
                requests.post(url, json=payload, timeout=10)

            return True

        except Exception as e:
            print(f"Reply send error: {e}")
            return False

    def get_uptime(self) -> str:
        """Get bot uptime"""
        try:
            if hasattr(self.trading_bot, "start_time"):
                uptime_seconds = time.time() - self.trading_bot.start_time
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            return "Unknown"
        except:
            return "Unknown"
