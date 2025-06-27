# utils/enhanced_trade_logger.py
import sqlite3
import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import os

class EnhancedTradeLogger:
    """Comprehensive SQLite-based trade logging and analytics system"""
    
    def __init__(self, db_path: str = "data/trading_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.init_database()
        
        # Performance tracking
        self.session_start = time.time()
        self.last_health_check = 0
    
    def init_database(self):
        """Initialize comprehensive database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enhanced trades table
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
                        strategy TEXT DEFAULT 'GRID',
                        status TEXT DEFAULT 'FILLED',
                        commission REAL DEFAULT 0,
                        commission_asset TEXT,
                        profit_loss REAL DEFAULT 0,
                        execution_time_ms INTEGER,
                        notes TEXT,
                        raw_order_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Portfolio snapshots
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        total_value REAL NOT NULL,
                        total_pnl REAL DEFAULT 0,
                        daily_change REAL DEFAULT 0,
                        assets TEXT,  -- JSON string of all assets
                        balances TEXT,  -- JSON string of balances
                        notes TEXT
                    )
                """)
                
                # Bot events and health
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        event_type TEXT NOT NULL,
                        event_category TEXT,  -- START/STOP/ERROR/TRADE/HEALTH
                        message TEXT,
                        details TEXT,  -- JSON string
                        severity TEXT DEFAULT 'INFO'  -- INFO/WARNING/ERROR/CRITICAL
                    )
                """)
                
                # Grid states
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS grid_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        symbol TEXT NOT NULL,
                        grid_config TEXT,  -- JSON
                        filled_orders TEXT,  -- JSON
                        active_levels TEXT,  -- JSON
                        total_orders INTEGER DEFAULT 0,
                        total_volume REAL DEFAULT 0,
                        unrealized_pnl REAL DEFAULT 0
                    )
                """)
                
                # Performance metrics
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        metric_type TEXT,  -- DAILY/WEEKLY/MONTHLY
                        total_trades INTEGER,
                        total_volume REAL,
                        total_pnl REAL,
                        win_rate REAL,
                        avg_trade_pnl REAL,
                        max_drawdown REAL,
                        sharpe_ratio REAL,
                        details TEXT  -- JSON
                    )
                """)
                
                # Create indexes for performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
                    "CREATE INDEX IF NOT EXISTS idx_trades_session ON trades(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp ON portfolio_snapshots(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON bot_events(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_events_type ON bot_events(event_type)",
                ]
                
                for index in indexes:
                    conn.execute(index)
                
                conn.commit()
                self.logger.info(f"✅ Enhanced database initialized: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def generate_session_id(self):
        """Generate unique session ID"""
        return f"session_{int(time.time())}_{os.getpid()}"
    
    def log_trade_execution(self, symbol: str, side: str, quantity: float, price: float, 
                          order_result: Dict, grid_level: int = None, 
                          execution_time_ms: int = None, session_id: str = None) -> int:
        """Log comprehensive trade execution details"""
        try:
            # Calculate values
            total_value = quantity * price
            commission = 0
            commission_asset = ""
            order_id = ""
            
            if order_result:
                order_id = str(order_result.get("orderId", ""))
                
                # Extract commission from fills
                fills = order_result.get("fills", [])
                if fills:
                    commission = sum(float(fill.get("commission", 0)) for fill in fills)
                    commission_asset = fills[0].get("commissionAsset", "") if fills else ""
            
            raw_order_json = json.dumps(order_result) if order_result else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO trades (
                        session_id, symbol, side, quantity, price, total_value, 
                        order_id, grid_level, commission, commission_asset,
                        execution_time_ms, raw_order_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id or self.generate_session_id(),
                    symbol, side, quantity, price, total_value,
                    order_id, grid_level, commission, commission_asset,
                    execution_time_ms, raw_order_json
                ))
                
                trade_id = cursor.lastrowid
                conn.commit()
                
                # Log to file as well for immediate visibility
                self.logger.info(
                    f"🎯 TRADE EXECUTED: {side} {quantity:.6f} {symbol} @ ${price:.6f} "
                    f"(${total_value:.2f}) [ID: {trade_id}] [Level: {grid_level}] [Order: {order_id}]"
                )
                
                return trade_id
                
        except Exception as e:
            self.logger.error(f"❌ Failed to log trade execution: {e}")
            return None
    
    def log_portfolio_snapshot(self, total_value: float, assets: Dict, 
                             session_id: str = None, notes: str = None):
        """Log detailed portfolio snapshot"""
        try:
            assets_json = json.dumps(assets)
            
            # Calculate daily change if we have previous snapshot
            daily_change = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT total_value FROM portfolio_snapshots 
                    WHERE timestamp >= datetime('now', '-1 day')
                    ORDER BY timestamp DESC LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    prev_value = result[0]
                    daily_change = total_value - prev_value
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO portfolio_snapshots (
                        session_id, total_value, daily_change, assets, notes
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id or self.generate_session_id(),
                    total_value, daily_change, assets_json, notes
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"❌ Failed to log portfolio snapshot: {e}")
    
    def log_bot_event(self, event_type: str, message: str, 
                     category: str = "INFO", severity: str = "INFO",
                     details: Dict = None, session_id: str = None):
        """Log bot events with categorization"""
        try:
            details_json = json.dumps(details) if details else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO bot_events (
                        session_id, event_type, event_category, message, details, severity
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id or self.generate_session_id(),
                    event_type, category, message, details_json, severity
                ))
                conn.commit()
                
                # Also log to file based on severity
                if severity == "CRITICAL":
                    self.logger.critical(f"🚨 {message}")
                elif severity == "ERROR":
                    self.logger.error(f"❌ {message}")
                elif severity == "WARNING":
                    self.logger.warning(f"⚠️ {message}")
                else:
                    self.logger.info(f"ℹ️ {message}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to log bot event: {e}")
    
    def save_grid_state(self, symbol: str, grid_config: Dict, filled_orders: List,
                       session_id: str = None):
        """Save current grid state"""
        try:
            total_orders = len(filled_orders)
            total_volume = sum(order.get('total_value', 0) for order in filled_orders)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO grid_states (
                        session_id, symbol, grid_config, filled_orders, 
                        total_orders, total_volume
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id or self.generate_session_id(),
                    symbol, json.dumps(grid_config), json.dumps(filled_orders),
                    total_orders, total_volume
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"❌ Failed to save grid state: {e}")
    
    def get_recent_trades(self, limit: int = 10, hours: int = 24) -> List[Dict]:
        """Get recent trades with enhanced details"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT 
                        id, timestamp, symbol, side, quantity, price, total_value,
                        order_id, grid_level, commission, commission_asset,
                        profit_loss, execution_time_ms
                    FROM trades 
                    WHERE timestamp >= datetime('now', '-{} hours')
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """.format(hours), (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get recent trades: {e}")
            return []
    
    def get_trading_statistics(self, days: int = 7) -> Dict:
        """Get comprehensive trading statistics - FIXED"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Use row_factory to get proper dict results
                conn.row_factory = sqlite3.Row
                
                # Basic stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
                        SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
                        SUM(total_value) as total_volume,
                        SUM(commission) as total_commission,
                        AVG(execution_time_ms) as avg_execution_time,
                        COUNT(DISTINCT symbol) as symbols_traded
                    FROM trades 
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days))
                
                row = cursor.fetchone()
                if row:
                    stats = dict(row)
                    # Handle None values
                    for key, value in stats.items():
                        if value is None:
                            stats[key] = 0
                else:
                    stats = {
                        'total_trades': 0,
                        'buy_trades': 0,
                        'sell_trades': 0,
                        'total_volume': 0,
                        'total_commission': 0,
                        'avg_execution_time': 0,
                        'symbols_traded': 0
                    }
                
                # Calculate additional metrics
                if stats.get('total_trades', 0) > 0:
                    stats['avg_trade_size'] = stats.get('total_volume', 0) / stats['total_trades']
                    if stats.get('total_volume', 0) > 0:
                        stats['commission_rate'] = (stats.get('total_commission', 0) / stats.get('total_volume', 1)) * 100
                    else:
                        stats['commission_rate'] = 0
                else:
                    stats['avg_trade_size'] = 0
                    stats['commission_rate'] = 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get trading statistics: {e}")
            # Return default stats on error
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_volume': 0,
                'total_commission': 0,
                'avg_execution_time': 0,
                'symbols_traded': 0,
                'avg_trade_size': 0,
                'commission_rate': 0
            }
    
    def get_performance_summary(self) -> Dict:
        """Get real-time performance summary"""
        try:
            stats_1d = self.get_trading_statistics(1)
            stats_7d = self.get_trading_statistics(7)
            recent_trades = self.get_recent_trades(5, 24)
            
            return {
                'today': stats_1d,
                'week': stats_7d,
                'recent_trades': recent_trades,
                'session_uptime': time.time() - self.session_start
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get performance summary: {e}")
            return {}
