#!/usr/bin/env python3
# path_diagnostic.py - Check exactly where the bot is looking for files
"""Diagnostic tool to check path resolution and working directory"""

import os
import sys
from pathlib import Path


def check_working_directory():
    """Check working directory and path resolution"""
    print("📂 Working Directory Diagnostic")
    print("=" * 50)
    
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print(f"Python path: {sys.path}")
    print()
    
    # Test different path resolutions
    test_paths = [
        "data/trading_history.db",
        "./data/trading_history.db", 
        "trading_bot/data/trading_history.db",
        "./trading_bot/data/trading_history.db"
    ]
    
    print("🔍 Path Resolution Test:")
    for test_path in test_paths:
        path = Path(test_path)
        abs_path = path.resolve()
        exists = path.exists()
        
        print(f"  Input: {test_path}")
        print(f"  Resolves to: {abs_path}")
        print(f"  Exists: {exists}")
        
        if exists:
            size = path.stat().st_size
            print(f"  Size: {size} bytes")
        print()


def simulate_bot_path_resolution():
    """Simulate exactly what the bot does for path resolution"""
    print("🤖 Bot Path Resolution Simulation")
    print("=" * 50)
    
    # This is what the compound manager does:
    db_path = "data/trading_history.db"
    
    print(f"1. Bot uses db_path: '{db_path}'")
    
    # Check if absolute
    if not Path(db_path).is_absolute():
        abs_db_path = Path.cwd() / db_path
    else:
        abs_db_path = Path(db_path)
    
    print(f"2. Path.cwd(): {Path.cwd()}")
    print(f"3. Combined path: {abs_db_path}")
    print(f"4. Exists: {abs_db_path.exists()}")
    
    if abs_db_path.exists():
        print(f"5. Size: {abs_db_path.stat().st_size} bytes")
    
    return str(abs_db_path)


def check_from_different_locations():
    """Check what happens when running from different directories"""
    print("\n🏃 Running From Different Locations")
    print("=" * 50)
    
    # Current location
    current_dir = Path.cwd()
    print(f"Currently in: {current_dir}")
    
    # Test running from parent directory
    parent_dir = current_dir.parent
    if parent_dir.exists():
        print(f"\nIf running from parent ({parent_dir}):")
        test_path = parent_dir / "data/trading_history.db"
        print(f"  Would look for: {test_path}")
        print(f"  Exists: {test_path.exists()}")
        
        # Try the path that worked in your force fix
        force_fix_path = parent_dir / "trading_bot/data/trading_history.db"
        print(f"  Force fix path: {force_fix_path}")
        print(f"  Exists: {force_fix_path.exists()}")


def find_all_trading_databases():
    """Find all possible trading database files"""
    print("\n🔎 Finding All Trading Databases")
    print("=" * 50)
    
    # Search from root of project
    start_dir = Path.cwd()
    while start_dir.parent != start_dir and start_dir.name != "trading-bot":
        start_dir = start_dir.parent
        if start_dir.name == "trading-bot":
            break
    
    print(f"Searching from: {start_dir}")
    
    # Find all .db files
    db_files = list(start_dir.rglob("*.db"))
    
    print(f"Found {len(db_files)} database files:")
    for db_file in db_files:
        print(f"  📄 {db_file}")
        try:
            size = db_file.stat().st_size
            print(f"     Size: {size} bytes")
            
            # Quick check if it has trades
            import sqlite3
            conn = sqlite3.connect(str(db_file))
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM trades")
                count = cursor.fetchone()[0]
                print(f"     Trades: {count}")
            except:
                print(f"     Trades: No trades table")
            conn.close()
        except Exception as e:
            print(f"     Error: {e}")
        print()


def main():
    """Run complete path diagnostic"""
    print("🚀 Trading Bot Path Diagnostic")
    print("=" * 70)
    
    check_working_directory()
    bot_path = simulate_bot_path_resolution()
    check_from_different_locations()
    find_all_trading_databases()
    
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Run bot from the correct directory")
    print("2. Use absolute paths in code if needed")
    print("3. Check if database is in different location")
    print(f"4. Bot is currently looking at: {bot_path}")


if __name__ == "__main__":
    main()
