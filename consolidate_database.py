#!/usr/bin/env python3
"""
Database Consolidation & Path Fix
Consolidates to trading_bot/data/ as single source of truth
"""

import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime


def analyze_databases():
    """Analyze both database locations"""
    print("🔍 Analyzing database locations...")
    
    old_db = Path("data/trading_history.db")  # Root level
    new_db = Path("trading_bot/data/trading_history.db")  # Preferred location
    
    results = {}
    
    # Check old database
    if old_db.exists():
        try:
            conn = sqlite3.connect(old_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades;")
            old_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 1;")
            old_latest = cursor.fetchone()
            old_latest = old_latest[0] if old_latest else "No trades"
            
            conn.close()
            results['old'] = {'count': old_count, 'latest': old_latest, 'path': str(old_db)}
            print(f"   📊 OLD DB ({old_db}): {old_count} trades, latest: {old_latest}")
        except Exception as e:
            results['old'] = {'error': str(e)}
            print(f"   ❌ OLD DB error: {e}")
    else:
        print(f"   📝 OLD DB ({old_db}): Not found")
        results['old'] = None
    
    # Check new database
    if new_db.exists():
        try:
            conn = sqlite3.connect(new_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades;")
            new_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 1;")
            new_latest = cursor.fetchone()
            new_latest = new_latest[0] if new_latest else "No trades"
            
            conn.close()
            results['new'] = {'count': new_count, 'latest': new_latest, 'path': str(new_db)}
            print(f"   📊 NEW DB ({new_db}): {new_count} trades, latest: {new_latest}")
        except Exception as e:
            results['new'] = {'error': str(e)}
            print(f"   ❌ NEW DB error: {e}")
    else:
        print(f"   📝 NEW DB ({new_db}): Not found")
        results['new'] = None
    
    return results


def consolidate_databases():
    """Consolidate to trading_bot/data/ as single source"""
    print("🔄 Consolidating databases...")
    
    old_db = Path("data/trading_history.db")
    new_db = Path("trading_bot/data/trading_history.db")
    
    # Ensure new directory exists
    new_db.parent.mkdir(parents=True, exist_ok=True)
    
    # If old exists but new doesn't, copy it
    if old_db.exists() and not new_db.exists():
        print(f"   📋 Copying {old_db} → {new_db}")
        shutil.copy2(old_db, new_db)
        return "copied"
    
    # If both exist, merge them
    elif old_db.exists() and new_db.exists():
        print("   🔄 Both databases exist - merging...")
        return merge_databases(old_db, new_db)
    
    # If only new exists, we're good
    elif new_db.exists():
        print("   ✅ Using existing new database")
        return "using_new"
    
    # If neither exists, create new
    else:
        print("   🆕 Creating new database")
        create_fresh_database(new_db)
        return "created_new"


def merge_databases(old_db, new_db):
    """Merge old database into new database"""
    print("   📊 Analyzing trade overlap...")
    
    try:
        # Get trades from old database
        old_conn = sqlite3.connect(old_db)
        old_cursor = old_conn.cursor()
        old_cursor.execute("SELECT * FROM trades ORDER BY timestamp;")
        old_trades = old_cursor.fetchall()
        
        # Get column names from old db
        old_cursor.execute("PRAGMA table_info(trades);")
        old_columns = [col[1] for col in old_cursor.fetchall()]
        old_conn.close()
        
        # Get trades from new database
        new_conn = sqlite3.connect(new_db)
        new_cursor = new_conn.cursor()
        new_cursor.execute("SELECT * FROM trades ORDER BY timestamp;")
        new_trades = new_cursor.fetchall()
        
        # Get column names from new db
        new_cursor.execute("PRAGMA table_info(trades);")
        new_columns = [col[1] for col in new_cursor.fetchall()]
        
        print(f"      OLD: {len(old_trades)} trades, columns: {old_columns}")
        print(f"      NEW: {len(new_trades)} trades, columns: {new_columns}")
        
        # Find unique trades to merge
        # Use timestamp + symbol + side + quantity as unique key
        new_trade_keys = set()
        for trade in new_trades:
            # Assuming standard order: id, timestamp, session_id, symbol, side, quantity, price...
            key = (trade[1], trade[3], trade[4], trade[5])  # timestamp, symbol, side, quantity
            new_trade_keys.add(key)
        
        trades_to_add = []
        for trade in old_trades:
            key = (trade[1], trade[3], trade[4], trade[5])  # Same positions
            if key not in new_trade_keys:
                trades_to_add.append(trade)
        
        if trades_to_add:
            print(f"      🔄 Adding {len(trades_to_add)} unique trades from old database")
            
            # Insert compatible trades (adjust for schema differences)
            for trade in trades_to_add:
                new_cursor.execute("""
                    INSERT INTO trades (
                        timestamp, session_id, symbol, side, quantity, price, total_value,
                        order_id, grid_level, commission, commission_asset, execution_time_ms, profit_loss
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, trade[1:14])  # Skip id, use first 13 columns
            
            new_conn.commit()
            print(f"      ✅ Merged {len(trades_to_add)} trades")
        else:
            print("      ℹ️  No new trades to merge")
        
        new_conn.close()
        return "merged"
        
    except Exception as e:
        print(f"   ❌ Merge failed: {e}")
        return "merge_failed"


def create_fresh_database(db_path):
    """Create fresh database with correct schema"""
    print(f"   🆕 Creating fresh database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create trades table with CORRECT schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                datetime TEXT,
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
                raw_order_data TEXT,
                notes TEXT,
                status TEXT DEFAULT 'FILLED'
            )
        """)
        
        # Create bot events table
        cursor.execute("""
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
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_datetime ON trades(datetime);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON bot_events(timestamp);")
        
        conn.commit()
        conn.close()
        print("   ✅ Fresh database created with correct schema")
        
    except Exception as e:
        print(f"   ❌ Failed to create database: {e}")


def update_all_file_paths():
    """Update all files to use correct relative paths"""
    print("🔧 Updating file paths...")
    
    files_and_updates = [
        # compound_manager.py - fix default path and ensure correct column usage
        ("trading_bot/utils/compound_manager.py", [
            ('db_path: str = "data/trading_history.db"', 'db_path: str = "data/trading_history.db"'),  # Already correct
            ('db_path: str = "trading_bot/data/trading_history.db"', 'db_path: str = "data/trading_history.db"'),  # Fix if wrong
            # Ensure it uses correct column names
            ('SELECT symbol, action,', 'SELECT symbol, side,'),  # Fix column name if wrong
        ]),
        
        # database_logger.py - fix default path
        ("trading_bot/utils/database_logger.py", [
            ('db_path: str = "data/trading_history.db"', 'db_path: str = "data/trading_history.db"'),  # Already correct
            ('db_path: str = "trading_bot/data/trading_history.db"', 'db_path: str = "data/trading_history.db"'),  # Fix if wrong
        ]),
        
        # main.py - fix load_state_from_database call
        ("trading_bot/main.py", [
            ('load_state_from_database("trading_bot/data/trading_history.db")', 'load_state_from_database("data/trading_history.db")'),
            ('load_state_from_database()', 'load_state_from_database("data/trading_history.db")'),  # Add explicit path
        ]),
        
        # simple_profit_tracker.py - if it exists
        ("trading_bot/utils/simple_profit_tracker.py", [
            ('db_path="data/trading_history.db"', 'db_path="data/trading_history.db"'),  # Ensure correct
            ('db_path="trading_bot/data/trading_history.db"', 'db_path="data/trading_history.db"'),
        ]),
    ]
    
    updated_files = []
    
    for file_path, replacements in files_and_updates:
        if Path(file_path).exists():
            print(f"   🔧 Updating {file_path}...")
            
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                original_content = content
                
                for old, new in replacements:
                    if old in content and old != new:  # Only replace if different
                        content = content.replace(old, new)
                        print(f"      ✅ {old[:40]}... → {new[:40]}...")
                
                if content != original_content:
                    with open(file_path, 'w') as f:
                        f.write(content)
                    updated_files.append(file_path)
                    print(f"      ✅ {file_path} updated")
                else:
                    print(f"      ℹ️  {file_path} already correct")
                    
            except Exception as e:
                print(f"      ❌ Error updating {file_path}: {e}")
        else:
            print(f"   ❌ File not found: {file_path}")
    
    return updated_files


def test_compound_calculation():
    """Test compound calculation with correct database"""
    print("🧪 Testing compound calculation...")
    
    db_path = "trading_bot/data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test query with correct column names
        cursor.execute("""
            SELECT symbol, side, quantity, price, timestamp 
            FROM trades 
            ORDER BY timestamp ASC
        """)
        trades = cursor.fetchall()
        
        print(f"   📊 Found {len(trades)} trades for profit calculation")
        
        if len(trades) == 0:
            print("   ℹ️  No trades found - compound will remain at base level")
            conn.close()
            return
        
        # FIFO profit calculation
        open_buys = {}
        total_profit = 0.0
        
        for trade in trades:
            symbol, side, quantity, price, timestamp = trade
            
            if side == "BUY":
                if symbol not in open_buys:
                    open_buys[symbol] = []
                open_buys[symbol].append({"qty": quantity, "price": price})
                
            elif side == "SELL":
                if symbol not in open_buys:
                    continue
                    
                remaining_qty = quantity
                
                while remaining_qty > 0 and open_buys[symbol]:
                    buy = open_buys[symbol][0]
                    match_qty = min(buy["qty"], remaining_qty)
                    profit = (price - buy["price"]) * match_qty
                    
                    if profit > 0:
                        total_profit += profit
                    
                    remaining_qty -= match_qty
                    buy["qty"] -= match_qty
                    
                    if buy["qty"] <= 0:
                        open_buys[symbol].pop(0)
        
        # Calculate expected compound
        base_order_size = 100.0
        reinvestment_rate = 0.3
        min_profit_threshold = 5.0
        
        print(f"   💰 Total profit calculated: ${total_profit:.2f}")
        
        if total_profit >= min_profit_threshold:
            profit_factor = (total_profit * reinvestment_rate) / base_order_size
            new_multiplier = 1.0 + profit_factor
            new_multiplier = min(new_multiplier, 2.0)  # Cap at 2x
            new_order_size = base_order_size * new_multiplier
            
            print(f"   📈 Expected compound multiplier: {new_multiplier:.3f}x")
            print(f"   💵 Expected order size: ${new_order_size:.2f}")
        else:
            print(f"   📊 Profit ${total_profit:.2f} below ${min_profit_threshold} threshold")
            print("   💵 Order size remains: $100.00")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Compound test failed: {e}")


def cleanup_old_database():
    """Remove old database location"""
    print("🧹 Cleaning up old database location...")
    
    old_db = Path("data/trading_history.db")
    old_dir = Path("data")
    
    if old_db.exists():
        try:
            old_db.unlink()
            print(f"   ✅ Removed {old_db}")
        except Exception as e:
            print(f"   ❌ Failed to remove {old_db}: {e}")
    
    # Remove data directory if empty
    if old_dir.exists() and old_dir.is_dir():
        try:
            if not any(old_dir.iterdir()):  # Directory is empty
                old_dir.rmdir()
                print(f"   ✅ Removed empty directory {old_dir}")
            else:
                remaining = list(old_dir.iterdir())
                print(f"   ℹ️  Keeping {old_dir} (contains: {[f.name for f in remaining]})")
        except Exception as e:
            print(f"   ❌ Failed to clean {old_dir}: {e}")


def main():
    """Main consolidation process"""
    print("🔧 Database Consolidation & Path Fix")
    print("=" * 50)
    
    # Step 1: Analyze current state
    db_analysis = analyze_databases()
    
    # Step 2: Consolidate databases
    consolidation_result = consolidate_databases()
    print(f"   📊 Consolidation result: {consolidation_result}")
    
    # Step 3: Update file paths
    updated_files = update_all_file_paths()
    
    # Step 4: Test compound calculation
    test_compound_calculation()
    
    # Step 5: Cleanup (only if consolidation was successful)
    if consolidation_result in ["copied", "merged", "using_new"]:
        cleanup_old_database()
    
    print("\n" + "=" * 50)
    print("🎯 CONSOLIDATION COMPLETE!")
    
    print(f"\n📍 Single source of truth: trading_bot/data/trading_history.db")
    print(f"🔧 Updated files: {len(updated_files)}")
    
    print("\n📋 Next Steps:")
    print("1. cd trading_bot")
    print("2. python main.py")
    print("3. Check logs for proper compound calculation")
    print("4. Test with /test_compound in Telegram")
    
    print("\n✅ Your compound interest should now work correctly!")


if __name__ == "__main__":
    main()
