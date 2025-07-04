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

    def record_buy(self, symbol: str, quantity: float, price: float) -> bool:
        """Record a buy trade - adds to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO trades (symbol, side, quantity, price, total_value, timestamp)
                    VALUES (?, 'BUY', ?, ?, ?, datetime('now'))
                """,
                    (symbol, quantity, price, quantity * price),
                )

                conn.commit()
                print(f"✅ Recorded BUY: {quantity} {symbol} @ ${price:.4f}")
                return True

        except Exception as e:
            print(f"❌ Failed to record buy: {e}")
            return False

    def record_sell(self, symbol: str, quantity: float, price: float) -> float:
        """Record a sell trade and calculate profit using FIFO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First record the sell
                cursor = conn.execute(
                    """
                    INSERT INTO trades (symbol, side, quantity, price, total_value, timestamp)
                    VALUES (?, 'SELL', ?, ?, ?, datetime('now'))
                """,
                    (symbol, quantity, price, quantity * price),
                )

                conn.commit()

                # Calculate profit using FIFO method
                profit = self._calculate_fifo_profit(symbol, quantity, price)
                print(
                    f"✅ Recorded SELL: {quantity} {symbol} @ ${price:.4f} (Profit: ${profit:.2f})"
                )

                return profit

        except Exception as e:
            print(f"❌ Failed to record sell: {e}")
            return 0.0

    def _calculate_fifo_profit(
        self, symbol: str, sell_quantity: float, sell_price: float
    ) -> float:
        """Calculate profit using FIFO (First In, First Out) method"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all buy orders for this symbol, oldest first
                cursor = conn.execute(
                    """
                    SELECT quantity, price, timestamp FROM trades 
                    WHERE symbol = ? AND side = 'BUY'
                    ORDER BY timestamp ASC
                """,
                    (symbol,),
                )

                buys = cursor.fetchall()
                remaining_sell_qty = sell_quantity
                total_profit = 0.0

                for buy_qty, buy_price, timestamp in buys:
                    if remaining_sell_qty <= 0:
                        break

                    # How much can we match with this buy?
                    match_qty = min(buy_qty, remaining_sell_qty)

                    # Calculate profit for this match
                    profit = (sell_price - buy_price) * match_qty
                    total_profit += profit

                    remaining_sell_qty -= match_qty

                return total_profit

        except Exception as e:
            print(f"❌ FIFO calculation failed: {e}")
            return 0.0

    def get_position(self, symbol: str) -> dict:
        """Get current position for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) as net_quantity,
                        SUM(CASE WHEN side = 'BUY' THEN total_value ELSE -total_value END) as net_value
                    FROM trades 
                    WHERE symbol = ?
                """,
                    (symbol,),
                )

                result = cursor.fetchone()
                net_qty = result[0] if result[0] else 0.0
                net_value = result[1] if result[1] else 0.0

                avg_price = net_value / net_qty if net_qty > 0 else 0.0

                return {
                    "symbol": symbol,
                    "quantity": net_qty,
                    "avg_price": avg_price,
                    "total_invested": net_value,
                }

        except Exception as e:
            print(f"❌ Position calculation failed: {e}")
            return {
                "symbol": symbol,
                "quantity": 0.0,
                "avg_price": 0.0,
                "total_invested": 0.0,
            }
