# Step 4: Simple Performance Dashboard
# Add to your trading_bot/utils/performance_dashboard.py (new file)

from datetime import datetime

import pytz


class PerformanceDashboard:
    def __init__(self, profit_tracker, compound_manager, telegram_notifier, db_logger):
        self.profit_tracker = profit_tracker
        self.compound_manager = compound_manager
        self.telegram_notifier = telegram_notifier
        self.db_logger = db_logger
        self.last_summary_date = None

    async def generate_daily_summary(self):
        """Generate and send daily performance summary"""
        try:
            # Get 24h stats
            stats = self.profit_tracker.get_recent_stats(24)
            compound_info = self.compound_manager.get_compound_status()

            # Get positions
            ada_pos = self.profit_tracker.get_position("ADAUSDT")
            avax_pos = self.profit_tracker.get_position("AVAXUSDT")

            # Calculate performance metrics
            profit_24h = stats.get("recent_profit", 0)
            trades_24h = stats.get("recent_trades", 0)

            summary = f"""
📊 **Daily Trading Summary**

**Performance (24h):**
• Trades: {trades_24h}
• Profit: ${profit_24h:.2f}
• Order Size: ${compound_info["current_order_size"]:.0f} ({compound_info["order_multiplier"]:.2f}x)

**Positions:**
• ADA: {ada_pos.get("quantity", 0):.0f} tokens (${ada_pos.get("total_invested", 0):.0f})
• AVAX: {avax_pos.get("quantity", 0):.1f} tokens (${avax_pos.get("total_invested", 0):.0f})

**Compound Status:**
• Accumulated Profit: ${compound_info["accumulated_profit"]:.2f}
• Growth Rate: {compound_info["profit_increase"]:+.1f}%

**Status:** {"🟢 Active" if self._bot_is_running() else "🔴 Stopped"}
            """

            await self.telegram_notifier.notify_info(summary.strip())

            # Log summary generation
            self.db_logger.log_bot_event(
                "DAILY_SUMMARY",
                f"Daily summary sent - Profit: ${profit_24h:.2f}, Trades: {trades_24h}",
                "INFO",
            )

        except Exception as e:
            print(f"Daily summary failed: {e}")

    def should_send_daily_summary(self) -> bool:
        """Check if it's time for daily summary (9 AM UTC)"""
        now = datetime.now(pytz.UTC)

        # Check if we already sent today's summary
        if self.last_summary_date == now.date():
            return False

        # Check if it's around 9 AM UTC (within 15 minutes)
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        time_diff = abs((now - target_time).total_seconds())

        if time_diff < 900:  # Within 15 minutes
            self.last_summary_date = now.date()
            return True

        return False

    def _bot_is_running(self) -> bool:
        """Check if bot is currently running (implement based on your bot structure)"""
        # This should check your bot's running status
        # You'll need to connect this to your main bot's running flag
        return True  # Placeholder

    async def get_quick_stats(self) -> dict:
        """Get quick performance stats for status commands"""
        try:
            stats_24h = self.profit_tracker.get_recent_stats(24)
            stats_7d = self.profit_tracker.get_recent_stats(24 * 7)
            compound_info = self.compound_manager.get_compound_status()

            return {
                "profit_24h": stats_24h.get("recent_profit", 0),
                "trades_24h": stats_24h.get("recent_trades", 0),
                "profit_7d": stats_7d.get("recent_profit", 0),
                "trades_7d": stats_7d.get("recent_trades", 0),
                "order_size": compound_info["current_order_size"],
                "growth_multiplier": compound_info["order_multiplier"],
            }
        except Exception:
            return {}
