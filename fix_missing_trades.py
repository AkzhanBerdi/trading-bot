#!/usr/bin/env python3
"""
Trade Reconciliation Script
Adds the missing AVAX trades from your power outage period
"""

import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_trades():
    """Add the 9 missing AVAX trades from the logs"""
    
    # Missing trades from your logs (all successful fills)
    missing_trades = [
        {"time": "2025-07-04 13:01:38", "qty": 5.86, "price": 18.09, "value": 106.03},
        {"time": "2025-07-04 13:02:33", "qty": 5.86, "price": 18.10, "value": 106.07},
        {"time": "2025-07-04 13:02:52", "qty": 5.86, "price": 18.09, "value": 106.01},
        {"time": "2025-07-04 13:03:30", "qty": 5.86, "price": 18.11, "value": 106.12},
        {"time": "2025-07-04 13:04:38", "qty": 5.86, "price": 18.10, "value": 106.07},
        {"time": "2025-07-04 13:05:49", "qty": 5.86, "price": 18.09, "value": 106.01},
        {"time": "2025-07-04 13:06:08", "qty": 5.86, "price": 18.08, "value": 105.95},
        {"time": "2025-07-04 13:06:28", "qty": 5.86, "price": 18.10, "value": 106.07},
        {"time": "2025-07-04 13:07:03", "qty": 5.86, "price": 18.10, "value": 106.07}
    ]
    
    db_path = "data/trading_history.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Ensure trades table exists with correct schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    order_id TEXT,
                    session_id TEXT,
                    grid_level INTEGER,
                    commission REAL DEFAULT 0,
                    execution_time_ms INTEGER
                )
            """)
            
            # Add missing trades
            trades_added = 0
            
            for trade in missing_trades:
                cursor.execute("""
                    INSERT INTO trades 
                    (timestamp, symbol, side, quantity, price, total_value, order_id, session_id)
                    VALUES (?, 'AVAXUSDT', 'BUY', ?, ?, ?, 'RECONCILED', 'POWER_OUTAGE_FIX')
                """, (
                    trade["time"],
                    trade["qty"], 
                    trade["price"],
                    trade["value"]
                ))
                
                trades_added += 1
                logger.info(f"✅ Added: {trade['qty']} AVAX @ ${trade['price']:.2f} ({trade['time']})")
            
            conn.commit()
            
            logger.info(f"🎉 Successfully added {trades_added} missing trades!")
            
            # Verify totals
            cursor.execute("""
                SELECT 
                    COUNT(*) as trade_count,
                    SUM(quantity) as total_avax,
                    SUM(total_value) as total_usd,
                    AVG(price) as avg_price
                FROM trades 
                WHERE symbol = 'AVAXUSDT' AND side = 'BUY'
                AND session_id = 'POWER_OUTAGE_FIX'
            """)
            
            result = cursor.fetchone()
            count, total_avax, total_usd, avg_price = result
            
            logger.info(f"📊 RECONCILIATION SUMMARY:")
            logger.info(f"   Trades added: {count}")
            logger.info(f"   Total AVAX: {total_avax:.2f}")
            logger.info(f"   Total USD: ${total_usd:.2f}")
            logger.info(f"   Average price: ${avg_price:.2f}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Reconciliation failed: {e}")
        return False

def verify_current_position():
    """Check current AVAX position after reconciliation"""
    
    db_path = "data/trading_history.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get total AVAX position
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) as net_avax,
                    SUM(CASE WHEN side = 'BUY' THEN total_value ELSE -total_value END) as net_invested
                FROM trades 
                WHERE symbol = 'AVAXUSDT'
            """)
            
            result = cursor.fetchone()
            net_avax = result[0] if result[0] else 0.0
            net_invested = result[1] if result[1] else 0.0
            
            avg_price = net_invested / net_avax if net_avax > 0 else 0.0
            
            logger.info(f"💰 CURRENT AVAX POSITION:")
            logger.info(f"   Holdings: {net_avax:.2f} AVAX")
            logger.info(f"   Invested: ${net_invested:.2f}")
            logger.info(f"   Avg Price: ${avg_price:.2f}")
            
            # Current market price check (you'd need to add this)
            current_price = 18.15  # Approximate from your logs
            current_value = net_avax * current_price
            unrealized_pnl = current_value - net_invested
            
            logger.info(f"   Current Value: ${current_value:.2f} (@ ${current_price:.2f})")
            logger.info(f"   Unrealized P&L: ${unrealized_pnl:.2f}")
            
            return {
                "avax_qty": net_avax,
                "invested": net_invested,
                "avg_price": avg_price,
                "current_value": current_value,
                "pnl": unrealized_pnl
            }
            
    except Exception as e:
        logger.error(f"❌ Position verification failed: {e}")
        return None

def check_for_duplicates():
    """Check if trades are already in database to avoid duplicates"""
    
    db_path = "data/trading_history.db"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check for existing trades in that time period
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE symbol = 'AVAXUSDT' 
                AND timestamp BETWEEN '2025-07-04 13:01:00' AND '2025-07-04 13:08:00'
            """)
            
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                logger.warning(f"⚠️  Found {existing_count} existing trades in that time period")
                logger.warning("   Reconciliation may create duplicates!")
                return False
            else:
                logger.info("✅ No existing trades found - safe to reconcile")
                return True
                
    except Exception as e:
        logger.error(f"❌ Duplicate check failed: {e}")
        return False

def main():
    """Main reconciliation process"""
    
    logger.info("🔧 TRADE RECONCILIATION STARTED")
    logger.info("=" * 50)
    
    # Step 1: Check for duplicates
    if not check_for_duplicates():
        logger.error("❌ Stopping to prevent duplicates. Check manually first.")
        return
    
    # Step 2: Add missing trades
    if add_missing_trades():
        logger.info("✅ Trades successfully reconciled!")
    else:
        logger.error("❌ Reconciliation failed!")
        return
    
    # Step 3: Verify position
    position = verify_current_position()
    
    logger.info("\n🎯 NEXT STEPS:")
    logger.info("1. Update your SimpleProfitTracker class with missing methods")
    logger.info("2. Test bot with small orders first") 
    logger.info("3. Add position limits to prevent this happening again")
    logger.info("4. Fix telegram notifications")
    
    logger.info("\n✅ Reconciliation complete!")

if __name__ == "__main__":
    main()
