# trading_bot/utils/compound_manager.py - CLEAN VERSION (Correct Path)
"""Simple and Safe Compound Interest Implementation - CLEAN"""

import logging
from pathlib import Path
from typing import Dict


class CompoundManager:
    """Simple compound interest manager - gradually increase order sizes from profits"""

    def __init__(self, db_logger, base_order_size: float = 100.0):
        self.db_logger = db_logger
        self.base_order_size = base_order_size
        self.logger = logging.getLogger(f"{__name__}")

        # Simple compound settings
        self.profit_reinvestment_rate = 0.3  # Reinvest 30% of profits (conservative)
        self.max_order_size_multiplier = 2.0  # Never exceed 2x base order size (safety)
        self.min_profit_threshold = 5.0  # Only compound after $5+ profit

        # Track accumulated profits
        self.accumulated_profit = 0.0
        self.current_order_multiplier = 1.0

        self.logger.info(f"🔄 Compound manager initialized - Base: ${base_order_size}")

    def load_state_from_database(
        self, db_path: str = "trading_bot/data/trading_history.db"
    ):
        """Load compound state from profit data in database"""
        self.logger.info(f"🔄 Loading compound state from {db_path}")

        try:
            import sqlite3

            # Ensure absolute path resolution
            if not Path(db_path).is_absolute():
                abs_db_path = Path.cwd() / db_path
            else:
                abs_db_path = Path(db_path)

            self.logger.info(f"🔄 Using absolute path: {abs_db_path}")
            self.logger.info(f"🔄 Database exists: {abs_db_path.exists()}")

            with sqlite3.connect(str(abs_db_path)) as conn:
                # Get all trades for FIFO calculation
                cursor = conn.execute("""
                    SELECT symbol, side, quantity, price, timestamp 
                    FROM trades 
                    ORDER BY timestamp ASC
                """)

                trades = cursor.fetchall()
                self.logger.info(f"🔄 Found {len(trades)} trades")

                if len(trades) == 0:
                    self.logger.info("🔄 No trades found, using base settings")
                    return

                # FIFO profit calculation
                open_buys = {}
                total_profit = 0.0
                profitable_sells = 0

                for trade in trades:
                    symbol, side, quantity, price, timestamp = trade

                    if side == "BUY":
                        if symbol not in open_buys:
                            open_buys[symbol] = []
                        open_buys[symbol].append({"qty": quantity, "price": price})

                    elif side == "SELL":
                        if symbol not in open_buys or not open_buys[symbol]:
                            continue

                        remaining_qty = quantity
                        sell_profit = 0.0

                        while remaining_qty > 0 and open_buys[symbol]:
                            buy = open_buys[symbol][0]
                            match_qty = min(buy["qty"], remaining_qty)
                            profit = (price - buy["price"]) * match_qty

                            if profit > 0:
                                total_profit += profit
                                sell_profit += profit

                            remaining_qty -= match_qty
                            buy["qty"] -= match_qty

                            if buy["qty"] <= 0:
                                open_buys[symbol].pop(0)

                        if sell_profit > 0:
                            profitable_sells += 1

                self.logger.info(f"🔄 Calculated profit: ${total_profit:.4f}")
                self.logger.info(f"🔄 Profitable sells: {profitable_sells}")

                # Apply compound interest if above threshold
                if total_profit >= self.min_profit_threshold:
                    self.accumulated_profit = total_profit

                    # Calculate new multiplier
                    profit_factor = (
                        total_profit * self.profit_reinvestment_rate
                    ) / self.base_order_size
                    new_multiplier = 1.0 + profit_factor
                    new_multiplier = min(new_multiplier, self.max_order_size_multiplier)

                    self.current_order_multiplier = new_multiplier

                    self.logger.info(f"🔄 Profit factor: {profit_factor:.6f}")
                    self.logger.info(f"🔄 New multiplier: {new_multiplier:.6f}")
                    self.logger.info(
                        f"🔄 New order size: ${self.base_order_size * new_multiplier:.2f}"
                    )

                    self.logger.info(
                        f"✅ Loaded compound state - ${total_profit:.2f} profit, {new_multiplier:.3f}x multiplier"
                    )
                else:
                    self.logger.info(
                        f"📊 Profit ${total_profit:.2f} below ${self.min_profit_threshold:.2f} threshold"
                    )

        except Exception as e:
            self.logger.error(f"❌ Compound loading failed: {e}")
            import traceback

            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.logger.info("📊 Using default compound settings")

    def record_trade_profit(self, symbol: str, side: str, profit: float) -> None:
        """Record profit from a completed trade"""
        try:
            if side == "SELL" and profit > 0:  # Only count actual profits from sells
                self.accumulated_profit += profit

                # Log profit accumulation
                self.db_logger.log_bot_event(
                    "PROFIT_ACCUMULATED",
                    f"Profit added: ${profit:.2f} | Total: ${self.accumulated_profit:.2f}",
                    "INFO",
                    {
                        "symbol": symbol,
                        "profit": profit,
                        "total_accumulated": self.accumulated_profit,
                    },
                )

                # Check if we should update order sizes
                self._update_order_sizes()

                self.logger.info(
                    f"💰 Profit accumulated: ${profit:.2f} (Total: ${self.accumulated_profit:.2f})"
                )

        except Exception as e:
            self.logger.error(f"Error recording profit: {e}")

    def _update_order_sizes(self) -> None:
        """Update order sizes based on accumulated profit"""
        try:
            # Only update if we have significant profit
            if self.accumulated_profit < self.min_profit_threshold:
                return

            # Calculate new multiplier (conservative approach)
            profit_factor = (
                self.accumulated_profit
                * self.profit_reinvestment_rate
                / self.base_order_size
            )
            new_multiplier = 1.0 + profit_factor

            # Apply safety cap
            new_multiplier = min(new_multiplier, self.max_order_size_multiplier)

            # Only update if change is meaningful (avoid tiny adjustments)
            if (
                abs(new_multiplier - self.current_order_multiplier) > 0.05
            ):  # 5% change minimum
                old_multiplier = self.current_order_multiplier
                self.current_order_multiplier = new_multiplier

                # Log compound adjustment
                self.db_logger.log_bot_event(
                    "COMPOUND_ADJUSTMENT",
                    f"Order size multiplier: {old_multiplier:.2f} → {new_multiplier:.2f}",
                    "INFO",
                    {
                        "old_multiplier": old_multiplier,
                        "new_multiplier": new_multiplier,
                        "accumulated_profit": self.accumulated_profit,
                        "new_order_size": self.base_order_size * new_multiplier,
                    },
                )

                self.logger.info(
                    f"🔄 Compound adjustment: {old_multiplier:.2f}x → {new_multiplier:.2f}x"
                )

        except Exception as e:
            self.logger.error(f"Error updating order sizes: {e}")

    def get_current_order_size(self) -> float:
        """Get current order size with compound interest applied"""
        return self.base_order_size * self.current_order_multiplier

    def get_compound_status(self) -> Dict:
        """Get current compound interest status"""
        current_order_size = self.get_current_order_size()

        return {
            "base_order_size": self.base_order_size,
            "current_order_size": round(current_order_size, 2),
            "order_multiplier": round(self.current_order_multiplier, 3),
            "accumulated_profit": round(self.accumulated_profit, 2),
            "reinvestment_rate": self.profit_reinvestment_rate,
            "max_multiplier": self.max_order_size_multiplier,
            "profit_increase": round(
                ((current_order_size - self.base_order_size) / self.base_order_size)
                * 100,
                1,
            ),
        }

    def reset_compound(self) -> None:
        """Reset compound interest (emergency use)"""
        old_profit = self.accumulated_profit
        old_multiplier = self.current_order_multiplier

        self.accumulated_profit = 0.0
        self.current_order_multiplier = 1.0

        # Log reset
        self.db_logger.log_bot_event(
            "COMPOUND_RESET",
            f"Compound reset - Profit: ${old_profit:.2f}, Multiplier: {old_multiplier:.2f}x",
            "WARNING",
            {"old_profit": old_profit, "old_multiplier": old_multiplier},
        )

        self.logger.warning(
            f"🔄 Compound reset - was ${old_profit:.2f} profit, {old_multiplier:.2f}x multiplier"
        )
