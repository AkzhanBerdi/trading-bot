#!/usr/bin/env python3
# database_diagnostic.py - Find out what's wrong with the database
"""Diagnostic tool to check database structure and content"""

import sqlite3
import os
from pathlib import Path


def check_database_paths():
    """Check all possible database locations"""
    print("🔍 Checking Database Locations")
    print("=" * 50)
    
    possible_paths = [
        "data/trading_history.db",
        "trading_bot/data/trading_history.db", 
        "/home/aberdeev/crypto-trading/trading-bot/data/trading_history.db",
        "/home/aberdeev/crypto-trading/trading-bot/trading_bot/data/trading_history.db"
    ]
    
    found_databases = []
    
    for path_str in possible_paths:
        path = Path(path_str)
        abs_path = path.resolve()
        
        print(f"📁 Checking: {path_str}")
        print(f"   Absolute: {abs_path}")
        print(f"   Exists: {path.exists()}")
        
        if path.exists():
            found_databases.append(str(abs_path))
            try:
                size = path.stat().st_size
                print(f"   Size: {size} bytes")
                
                # Quick check for tables
                conn = sqlite3.connect(str(path))
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                print(f"   Tables: {tables}")
                
                if 'trades' in tables:
                    cursor = conn.execute("SELECT COUNT(*) FROM trades")
                    count = cursor.fetchone()[0]
                    print(f"   Trades count: {count}")
                
                conn.close()
                
            except Exception as e:
                print(f"   Error reading: {e}")
        
        print()
    
    return found_databases


def analyze_database(db_path):
    """Deep analysis of database content"""
    print(f"🔬 Analyzing Database: {db_path}")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Check schema
        print("1️⃣ Table Schemas:")
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        for row in cursor.fetchall():
            if row[0]:
                print(f"   {row[0]}")
        print()
        
        # Check trades table specifically
        print("2️⃣ Trades Table Analysis:")
        try:
            # Get column info
            cursor = conn.execute("PRAGMA table_info(trades)")
            columns = cursor.fetchall()
            print("   Columns:")
            for col in columns:
                print(f"     {col[1]} ({col[2]})")
            
            # Count trades
            cursor = conn.execute("SELECT COUNT(*) FROM trades")
            count = cursor.fetchone()[0]
            print(f"   Total trades: {count}")
            
            if count > 0:
                print("\n   Sample trades:")
                cursor = conn.execute("SELECT * FROM trades LIMIT 5")
                rows = cursor.fetchall()
                for i, row in enumerate(rows):
                    print(f"     Trade {i+1}: {row}")
                
                # Check what columns actually exist
                print("\n   Column test - SELECT symbol, side, quantity, price, timestamp:")
                try:
                    cursor = conn.execute("SELECT symbol, side, quantity, price, timestamp FROM trades LIMIT 1")
                    row = cursor.fetchone()
                    print(f"     ✅ SUCCESS: {row}")
                except Exception as e:
                    print(f"     ❌ FAILED: {e}")
                    
                    # Try alternative column names
                    print("\n   Trying alternative column combinations:")
                    alternatives = [
                        "SELECT symbol, side, quantity, price, datetime FROM trades LIMIT 1",
                        "SELECT symbol, side, quantity, price, id FROM trades LIMIT 1",
                        "SELECT * FROM trades LIMIT 1"
                    ]
                    
                    for alt in alternatives:
                        try:
                            cursor = conn.execute(alt)
                            row = cursor.fetchone()
                            print(f"     ✅ {alt}: {row}")
                            break
                        except Exception as e2:
                            print(f"     ❌ {alt}: {e2}")
            
        except Exception as e:
            print(f"   ❌ Trades table error: {e}")
        
        # Check bot_events
        print("\n3️⃣ Bot Events:")
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM bot_events")
            count = cursor.fetchone()[0]
            print(f"   Total events: {count}")
            
            if count > 0:
                cursor = conn.execute("SELECT event_type, COUNT(*) FROM bot_events GROUP BY event_type")
                events = cursor.fetchall()
                for event_type, count in events:
                    print(f"     {event_type}: {count}")
        except Exception as e:
            print(f"   ❌ Bot events error: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database analysis failed: {e}")


def test_compound_query():
    """Test the exact query compound manager uses"""
    print("\n🧪 Testing Compound Manager Query")
    print("=" * 50)
    
    db_path = "/home/aberdeev/crypto-trading/trading-bot/data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        
        # This is the EXACT query from compound manager
        query = """
            SELECT symbol, side, quantity, price, timestamp 
            FROM trades 
            ORDER BY timestamp ASC
        """
        
        print(f"Query: {query}")
        
        cursor = conn.execute(query)
        trades = cursor.fetchall()
        
        print(f"Result: {len(trades)} trades found")
        
        if len(trades) > 0:
            print("Sample trades:")
            for i, trade in enumerate(trades[:5]):
                print(f"  {i+1}: {trade}")
        else:
            print("❌ No trades returned by compound query!")
            
            # Check if trades exist at all
            cursor = conn.execute("SELECT COUNT(*) FROM trades")
            total = cursor.fetchone()[0]
            print(f"Total trades in table: {total}")
            
            if total > 0:
                print("❌ Trades exist but query isn't finding them!")
                
                # Show actual column names
                cursor = conn.execute("PRAGMA table_info(trades)")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"Actual columns: {columns}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Query test failed: {e}")


def main():
    """Run complete database diagnostic"""
    print("🚀 Trading Bot Database Diagnostic Tool")
    print("=" * 70)
    
    # Check current directory
    print(f"📂 Current directory: {os.getcwd()}")
    print()
    
    # Find all databases
    found_dbs = check_database_paths()
    
    if not found_dbs:
        print("❌ No databases found!")
        return
    
    # Analyze each database
    for db_path in found_dbs:
        analyze_database(db_path)
        print()
    
    # Test compound query specifically
    test_compound_query()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Check if trades are in a different table")
    print("2. Check if column names are different") 
    print("3. Check if database path is wrong in code")
    print("4. Look for backup databases")


if __name__ == "__main__":
    main()
