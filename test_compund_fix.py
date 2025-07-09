#!/usr/bin/env python3
# test_compound_fix.py - Verify compound interest is working
"""Test script to verify compound interest is working after the fix"""

import sys
from pathlib import Path

# Add the trading_bot directory to path
sys.path.append(str(Path(__file__).parent / "trading_bot"))

from utils.database_logger import DatabaseLogger
from utils.compound_manager import CompoundManager


def test_compound_fix():
    """Test if compound interest is working correctly"""
    print("🧪 Testing Compound Interest Fix")
    print("=" * 50)
    
    try:
        # Initialize compound manager
        db_logger = DatabaseLogger()
        compound_manager = CompoundManager(db_logger, base_order_size=100.0)
        
        print("1️⃣ Created compound manager")
        print(f"   Base order size: ${compound_manager.base_order_size}")
        print(f"   Initial multiplier: {compound_manager.current_order_multiplier}")
        print(f"   Initial accumulated: ${compound_manager.accumulated_profit}")
        
        # Load state from database
        print("\n2️⃣ Loading state from database...")
        compound_manager.load_state_from_database("trading_bot/data/trading_history.db")
        
        # Check compound status
        compound_info = compound_manager.get_compound_status()
        
        print("\n3️⃣ Compound Status After Loading:")
        print(f"   💰 Order Size: ${compound_info['current_order_size']:.2f}")
        print(f"   📈 Multiplier: {compound_info['order_multiplier']:.3f}x")
        print(f"   💸 Accumulated Profit: ${compound_info['accumulated_profit']:.2f}")
        print(f"   📊 Profit Increase: {compound_info['profit_increase']:.1f}%")
        
        # Test expected values
        expected_order_size = 107.97  # From your force fix
        actual_order_size = compound_info['current_order_size']
        
        print("\n4️⃣ Verification:")
        if abs(actual_order_size - expected_order_size) < 2:
            print("   ✅ COMPOUND IS WORKING!")
            print(f"   ✅ Order size: ${actual_order_size:.2f} (expected ~${expected_order_size:.2f})")
            print("   ✅ Your bot will now use larger orders based on profits!")
        else:
            print("   ❌ Compound still not working")
            print(f"   ❌ Order size: ${actual_order_size:.2f} (expected ~${expected_order_size:.2f})")
            print("   ❌ Still using base $100 orders")
        
        print("\n5️⃣ Database Connection Test:")
        db_path = Path("trading_bot/data/trading_history.db")
        if db_path.exists():
            print(f"   ✅ Database exists: {db_path}")
            
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM trades")
            trade_count = cursor.fetchone()[0]
            conn.close()
            
            print(f"   ✅ Found {trade_count} trades in database")
        else:
            print(f"   ❌ Database not found: {db_path}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_compound_fix()
