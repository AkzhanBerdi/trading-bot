# trading_bot/utils/database_logger.py - MINIMAL VERSION
"""Minimal Database Logger - Only What We Actually Use"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict


class DatabaseLogger:
    """Minimal database logger - only trades and bot events"""

    def __init__(self, db_path: str = "data/trading_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_start = time.time()
        self._init_database()

    def _init_database(self):
        """Initialize minimal database - only essential tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Trades table - KEEP (essential for trade history)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        total_value REAL NOT NULL,
                        order_id TEXT,
                        grid_level INTEGER,
                        commission REAL DEFAULT 0,
                        commission_asset TEXT,
                        execution_time_ms INTEGER,
                        profit_loss REAL DEFAULT 0,
                        raw_order_data TEXT
                    )
                """)

                # Bot events table - KEEP (essential for debugging)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        event_type TEXT NOT NULL,
                        message TEXT,
                        severity TEXT DEFAULT 'INFO',
                        details TEXT
                    )
                """)

                # Essential indexes only
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON bot_events(timestamp)"
                )

                conn.commit()
                print(f"✅ Minimal database initialized: {self.db_path}")

        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            raise

    def log_trade_execution(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_result: Dict,
        grid_level: int = None,
        execution_time_ms: int = None,
        session_id: str = None,
    ) -> int:
        """Log trade execution - SIMPLIFIED"""
        try:
            total_value = quantity * price
            commission = 0
            order_id = ""

            if order_result:
                order_id = str(order_result.get("orderId", ""))
                # Simple commission extraction
                fills = order_result.get("fills", [])
                if fills:
                    commission = sum(float(fill.get("commission", 0)) for fill in fills)

            raw_order_json = json.dumps(order_result) if order_result else None

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO trades (
                        session_id, symbol, side, quantity, price, total_value, 
                        order_id, grid_level, commission, execution_time_ms, raw_order_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        symbol,
                        side,
                        quantity,
                        price,
                        total_value,
                        order_id,
                        grid_level,
                        commission,
                        execution_time_ms,
                        raw_order_json,
                    ),
                )
                trade_id = cursor.lastrowid
                conn.commit()
                return trade_id

        except Exception as e:
            print(f"❌ Failed to log trade: {e}")
            return None

    def log_bot_event(
        self,
        event_type: str,
        message: str,
        category: str = "INFO",  # Accept category for backward compatibility but ignore it
        severity: str = "INFO",
        details: dict = None,
        session_id: str = None,
    ):
        """Log bot events - SIMPLIFIED (accepts category for compatibility)"""
        try:
            # Convert details to string if present
            details_str = None
            if details is not None:
                if isinstance(details, dict):
                    try:
                        details_str = json.dumps(details)
                    except:
                        details_str = str(details)
                else:
                    details_str = str(details)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO bot_events (
                        session_id, event_type, message, severity, details
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(session_id) if session_id else None,
                        str(event_type),
                        str(message),
                        str(severity),
                        details_str,
                    ),
                )
                conn.commit()

        except Exception as e:
            print(
                f"❌ Failed to log event: {e} | event_type: {event_type} | severity: {severity}"
            )

    def get_recent_trades_count(self, hours: int = 24) -> int:
        """Get count of recent trades - MINIMAL INFO ONLY"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM trades 
                    WHERE timestamp >= datetime('now', '-{} hours')
                    """.format(hours)
                )
                result = cursor.fetchone()
                return result[0] if result else 0

        except Exception as e:
            print(f"❌ Failed to get trade count: {e}")
            return 0
