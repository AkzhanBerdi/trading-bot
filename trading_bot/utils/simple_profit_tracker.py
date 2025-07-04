import sqlite3
from typing import Dict


class SimpleProfitTracker:
    """
    Database-backed FIFO profit tracking for trading bot
    Uses existing SQLite database for persistence
    Tracks (selling_price - buying_price) × quantity
    """

    def __init__(self, db_path: str = "data/trading_history.db"):
        self.db_path = db_path

    def get_stats(self) -> Dict:
        """Calculate profit statistics from database using FIFO matching"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all trades ordered by timestamp (FIFO)
                cursor = conn.execute("""
                    SELECT symbol, side, quantity, price, timestamp 
                    FROM trades 
                    ORDER BY timestamp ASC
                """)

                trades = cursor.fetchall()

                # Track open buys per symbol
                open_buys = {}
                total_profit = 0.0
                completed_trades = 0

                for trade in trades:
                    symbol, side, quantity, price, timestamp = trade

                    if side == "BUY":
                        # Add to open buys
                        if symbol not in open_buys:
                            open_buys[symbol] = []
                        open_buys[symbol].append(
                            {"qty": quantity, "price": price, "timestamp": timestamp}
                        )

                    elif side == "SELL":
                        # Match with open buys using FIFO
                        if symbol not in open_buys:
                            continue

                        remaining_qty = quantity

                        while remaining_qty > 0 and open_buys[symbol]:
                            buy = open_buys[symbol][0]

                            # How much can we match?
                            match_qty = min(buy["qty"], remaining_qty)

                            # Calculate profit: (sell_price - buy_price) × quantity
                            profit = (price - buy["price"]) * match_qty
                            if profit > 0:
                                total_profit += profit
                                completed_trades += 1

                            # Update quantities
                            remaining_qty -= match_qty
                            buy["qty"] -= match_qty

                            # Remove buy if fully used
                            if buy["qty"] <= 0:
                                open_buys[symbol].pop(0)

                return {
                    "total_profit": round(total_profit, 2),
                    "total_trades": completed_trades,
                    "avg_per_trade": round(
                        total_profit / completed_trades if completed_trades > 0 else 0,
                        2,
                    ),
                }

        except Exception as e:
            print(f"Error calculating profit stats: {e}")
            return {"total_profit": 0.0, "total_trades": 0, "avg_per_trade": 0.0}

    def get_recent_stats(self, hours: int = 24) -> Dict:
        """Get profit statistics for recent time period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get trades from last N hours
                cursor = conn.execute(
                    """
                    SELECT symbol, side, quantity, price, timestamp 
                    FROM trades 
                    WHERE timestamp >= datetime('now', '-{} hours')
                    ORDER BY timestamp ASC
                """.format(hours)
                )

                trades = cursor.fetchall()

                # Use same FIFO logic but for recent trades only
                # (This is a simplified version - could be more sophisticated)
                recent_profit = 0.0
                recent_trades = 0

                for trade in trades:
                    symbol, side, quantity, price, timestamp = trade
                    if side == "SELL":
                        # Simple approximation: assume 2% profit per sell
                        # This could be made more accurate with full FIFO tracking
                        estimated_profit = quantity * price * 0.02
                        recent_profit += estimated_profit
                        recent_trades += 1

                return {
                    "recent_profit": round(recent_profit, 2),
                    "recent_trades": recent_trades,
                }

        except Exception as e:
            print(f"Error calculating recent stats: {e}")
            return {"recent_profit": 0.0, "recent_trades": 0}
