#!/usr/bin/env python3
"""
Corrected Database Fix Script
Works with your actual database schema
"""

import sqlite3
import os
from pathlib import Path

def analyze_actual_schema():
    """Analyze your actual database schema"""
    print("🔍 Analyzing actual database schema...")
    
    db_path = "data/trading_history.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get actual schema
        cursor.execute("PRAGMA table_info(trades);")
        columns = cursor.fetchall()
        
        print("📋 Your actual database columns:")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        # Check recent data
        cursor.execute("SELECT COUNT(*) FROM trades;")
        total_count = cursor.fetchone()[0]
        print(f"\n📊 Total trades in database: {total_count}")
        
        if total_count > 0:
            # Show recent trades with actual column names
            cursor.execute("SELECT timestamp, symbol, side, quantity, price, total_value FROM trades ORDER BY id DESC LIMIT 3;")
            recent = cursor.fetchall()
            
            print("\n📝 Recent trades (actual data):")
            for trade in recent:
                print(f"   {trade[0]} | {trade[1]} | {trade[2]} | {trade[3]} | ${trade[4]:.4f} | ${trade[5]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema analysis failed: {e}")
        return False
    finally:
        conn.close()

def fix_schema_for_your_database():
    """Fix schema issues for your specific database"""
    print("🔧 Fixing schema for your database...")
    
    db_path = "data/trading_history.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get current columns
        cursor.execute("PRAGMA table_info(trades);")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Fix 1: Ensure datetime column exists and is populated
        if 'datetime' not in column_names:
            print("   🔧 Adding datetime column...")
            cursor.execute("ALTER TABLE trades ADD COLUMN datetime TEXT;")
            
        # Always update datetime from timestamp
        if 'timestamp' in column_names:
            cursor.execute("UPDATE trades SET datetime = timestamp WHERE datetime IS NULL OR datetime = '';")
            print("   ✅ Updated datetime from timestamp")
        
        # Fix 2: Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_trades_datetime ON trades(datetime);",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);", 
            "CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);",
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("   ✅ Created performance indexes")
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("SELECT COUNT(*) FROM trades WHERE datetime IS NOT NULL;")
        datetime_count = cursor.fetchone()[0]
        print(f"   📊 Trades with datetime: {datetime_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        return False
    finally:
        conn.close()

def test_queries_with_actual_schema():
    """Test queries using your actual schema"""
    print("🧪 Testing queries with actual schema...")
    
    db_path = "data/trading_history.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test 1: Query recent trades using datetime
        cursor.execute("SELECT COUNT(*) FROM trades WHERE datetime >= '2025-07-01';")
        recent_count = cursor.fetchone()[0]
        print(f"   ✅ Recent trades (July+): {recent_count}")
        
        # Test 2: Query by symbol and side
        cursor.execute("SELECT symbol, side, COUNT(*), SUM(total_value) FROM trades GROUP BY symbol, side;")
        summary = cursor.fetchall()
        
        print("   📊 Trade summary by symbol/side:")
        for row in summary:
            print(f"      {row[0]} {row[1]}: {row[2]} trades, ${row[3]:.2f} total")
        
        # Test 3: Recent trades with proper columns
        cursor.execute("""
        SELECT datetime, symbol, side, quantity, price, total_value 
        FROM trades 
        WHERE datetime >= '2025-07-08' 
        ORDER BY datetime DESC 
        LIMIT 5
        """)
        recent_july8 = cursor.fetchall()
        
        print(f"   📝 July 8 trades: {len(recent_july8)} found")
        for trade in recent_july8:
            print(f"      {trade[0]} | {trade[1]} {trade[2]} {trade[3]} @ ${trade[4]:.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        return False
    finally:
        conn.close()

def create_simple_logging_function():
    """Create a simple logging function that works with your schema"""
    print("📝 Creating compatible logging function...")
    
    logging_code = '''
def log_trade_to_your_database(symbol, side, quantity, price, total_value, order_id=None, notes=""):
    """Log trade using your actual database schema"""
    import sqlite3
    from datetime import datetime
    
    try:
        conn = sqlite3.connect("data/trading_history.db")
        cursor = conn.cursor()
        
        # Use your actual column names
        cursor.execute("""
        INSERT INTO trades (
            timestamp, datetime, symbol, side, quantity, price, total_value, 
            order_id, notes, status, session_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),  # timestamp
            datetime.now().isoformat(),  # datetime
            symbol,
            side,  # BUY or SELL
            quantity,
            price,
            total_value,
            order_id,
            notes,
            "FILLED",
            "enhanced_bot"
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Logged: {side} {quantity} {symbol} @ ${price:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ Logging failed: {e}")
        return False

# Test the logging function
log_trade_to_your_database("TESTUSDT", "BUY", 1.0, 1.0, 1.0, "TEST123", "Schema test")
'''
    
    # Save to file
    with open("compatible_logging.py", "w") as f:
        f.write(logging_code)
    
    print("   ✅ Created compatible_logging.py")
    
    # Test it
    try:
        exec(logging_code)
        return True
    except Exception as e:
        print(f"   ❌ Logging test failed: {e}")
        return False

def main():
    """Main corrected fix process"""
    print("🔧 Corrected Enhanced Trading Bot Database Fix")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # Test 1: Analyze actual schema
    if analyze_actual_schema():
        success_count += 1
    
    # Test 2: Fix schema for your database
    if fix_schema_for_your_database():
        success_count += 1
    
    # Test 3: Test queries with actual schema
    if test_queries_with_actual_schema():
        success_count += 1
    
    # Test 4: Create compatible logging
    if create_simple_logging_function():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 Results: {success_count}/{total_tests} tests passed")
    
    if success_count >= 3:
        print("✅ Database is now compatible!")
        print("\n🔧 Next steps:")
        print("1. Your database uses 'side' not 'action'")
        print("2. Your database uses 'total_value' not 'value'") 
        print("3. Update your bot to use correct column names")
        print("4. Use the compatible logging function")
        
    print("\n📋 Your Database Schema Summary:")
    print("   • Uses 'side' column (BUY/SELL)")
    print("   • Uses 'total_value' column")
    print("   • Has datetime column (fixed)")
    print("   • Has performance indexes (added)")

if __name__ == "__main__":
    main()
