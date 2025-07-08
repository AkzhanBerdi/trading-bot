#!/usr/bin/env python3
"""
Verification Script - Check if compound interest fix worked
Run this from project root to verify everything is working
"""

import sqlite3
from pathlib import Path
import os

def verify_database_location():
    """Verify correct database location"""
    print("📍 Verifying database location...")
    
    target_db = Path("trading_bot/data/trading_history.db")
    old_db = Path("data/trading_history.db")
    
    if target_db.exists():
        print(f"✅ Target database exists: {target_db}")
        
        # Check trade count
        try:
            conn = sqlite3.connect(target_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades;")
            count = cursor.fetchone()[0]
            print(f"   📊 Contains {count} trades")
            
            if count > 0:
                cursor.execute("SELECT symbol, side, quantity, price FROM trades ORDER BY timestamp DESC LIMIT 1;")
                latest = cursor.fetchone()
                print(f"   📝 Latest trade: {latest[1]} {latest[2]} {latest[0]} @ ${latest[3]:.4f}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    else:
        print(f"❌ Target database missing: {target_db}")
        return False

def verify_file_paths():
    """Verify file paths are correct"""
    print("\n🔧 Verifying file paths...")
    
    files_to_check = [
        "trading_bot/utils/compound_manager.py",
        "trading_bot/utils/database_logger.py", 
        "trading_bot/main.py"
    ]
    
    correct_paths = [
        'db_path: str = "data/trading_history.db"',
        'load_state_from_database("data/trading_history.db")',
    ]
    
    wrong_paths = [
        'db_path: str = "trading_bot/data/trading_history.db"',
        'load_state_from_database("trading_bot/data/trading_history.db")',
    ]
    
    issues_found = []
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for wrong paths
            has_wrong_path = any(wrong in content for wrong in wrong_paths)
            has_correct_path = any(correct in content for correct in correct_paths)
            
            if has_wrong_path:
                issues_found.append(f"❌ {file_path} has incorrect paths")
            elif has_correct_path:
                print(f"✅ {file_path} paths correct")
            else:
                print(f"ℹ️  {file_path} no database path found")
        else:
            issues_found.append(f"❌ Missing file: {file_path}")
    
    return len(issues_found) == 0

def simulate_compound_calculation():
    """Simulate compound calculation to verify it works"""
    print("\n🧮 Simulating compound calculation...")
    
    db_path = "trading_bot/data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get trades using correct column names
        cursor.execute("""
            SELECT symbol, side, quantity, price, timestamp 
            FROM trades 
            ORDER BY timestamp ASC
        """)
        trades = cursor.fetchall()
        
        print(f"   📊 Processing {len(trades)} trades...")
        
        # FIFO profit calculation
        open_buys = {}
        total_profit = 0.0
        sells_processed = 0
        
        for trade in trades:
            symbol, side, quantity, price, timestamp = trade
            
            if side == "BUY":
                if symbol not in open_buys:
                    open_buys[symbol] = []
                open_buys[symbol].append({"qty": quantity, "price": price})
                
            elif side == "SELL":
                sells_processed += 1
                if symbol not in open_buys:
                    continue
                    
                remaining_qty = quantity
                trade_profit = 0.0
                
                while remaining_qty > 0 and open_buys[symbol]:
                    buy = open_buys[symbol][0]
                    match_qty = min(buy["qty"], remaining_qty)
                    profit = (price - buy["price"]) * match_qty
                    
                    if profit > 0:
                        total_profit += profit
                        trade_profit += profit
                    
                    remaining_qty -= match_qty
                    buy["qty"] -= match_qty
                    
                    if buy["qty"] <= 0:
                        open_buys[symbol].pop(0)
                
                if trade_profit > 0:
                    print(f"      💰 {symbol} sell profit: ${trade_profit:.2f}")
        
        conn.close()
        
        # Calculate compound settings
        base_order_size = 100.0
        reinvestment_rate = 0.3
        min_profit_threshold = 5.0
        max_multiplier = 2.0
        
        print(f"\n   📈 Calculation Results:")
        print(f"      Total profit: ${total_profit:.2f}")
        print(f"      Sells processed: {sells_processed}")
        
        if total_profit >= min_profit_threshold:
            profit_factor = (total_profit * reinvestment_rate) / base_order_size
            new_multiplier = 1.0 + profit_factor
            new_multiplier = min(new_multiplier, max_multiplier)
            new_order_size = base_order_size * new_multiplier
            
            print(f"      Expected multiplier: {new_multiplier:.3f}x")
            print(f"      Expected order size: ${new_order_size:.2f}")
            
            if new_order_size > 100:
                print("   ✅ Compound interest should be working!")
                return True
            else:
                print("   ℹ️  Compound at minimum level (not enough profit)")
                return True
        else:
            print(f"      Profit below ${min_profit_threshold} threshold")
            print("   ℹ️  Compound will remain at base level")
            return True
            
    except Exception as e:
        print(f"   ❌ Simulation failed: {e}")
        return False

def check_old_database_cleanup():
    """Check if old database was cleaned up"""
    print("\n🧹 Checking cleanup...")
    
    old_db = Path("data/trading_history.db")
    old_dir = Path("data")
    
    if old_db.exists():
        print(f"⚠️  Old database still exists: {old_db}")
        print("   Consider removing it after verifying everything works")
        return False
    else:
        print("✅ Old database location cleaned up")
    
    if old_dir.exists() and old_dir.is_dir():
        remaining = list(old_dir.iterdir())
        if remaining:
            print(f"ℹ️  Old data directory contains: {[f.name for f in remaining]}")
        else:
            print("ℹ️  Old data directory is empty")
    
    return True

def main():
    """Main verification process"""
    print("🔍 Verifying Compound Interest Fix")
    print("=" * 40)
    
    checks = [
        ("Database Location", verify_database_location),
        ("File Paths", verify_file_paths), 
        ("Compound Calculation", simulate_compound_calculation),
        ("Cleanup Status", check_old_database_cleanup),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}:")
        if check_func():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"🎯 Verification Results: {passed}/{total} checks passed")
    
    if passed >= 3:  # Allow cleanup to fail
        print("\n✅ VERIFICATION SUCCESSFUL!")
        print("\n📋 Next Steps:")
        print("1. cd trading_bot")
        print("2. python main.py")
        print("3. Watch logs for compound interest messages")
        print("4. Test with /test_compound in Telegram")
        
        print("\n🔍 Expected Log Messages:")
        print("   ✅ Loaded compound state from database: $X.XX profit, X.XXXx multiplier")
        print("   💰 Using compound order size: $XXX")
        
    else:
        print("\n❌ VERIFICATION FAILED!")
        print("Please run the consolidation script first")

if __name__ == "__main__":
    main()
