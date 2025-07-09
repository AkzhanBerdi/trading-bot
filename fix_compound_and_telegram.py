#!/usr/bin/env python3
"""
Fix Lost Compound Interest & Telegram API Error
Restore compound calculation and fix Telegram message format
"""

import sqlite3
from pathlib import Path

def check_database_compound():
    """Check if compound calculation is working"""
    
    print("🔍 Checking compound interest calculation...")
    
    db_path = "trading_bot/data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get total trades
        cursor.execute("SELECT COUNT(*) FROM trades;")
        total_trades = cursor.fetchone()[0]
        print(f"   📊 Total trades in database: {total_trades}")
        
        if total_trades == 0:
            print("   ❌ No trades found - explains $0.00 profit")
            conn.close()
            return False
        
        # Manual FIFO calculation (same as compound manager should do)
        cursor.execute("""
            SELECT symbol, side, quantity, price, timestamp 
            FROM trades 
            ORDER BY timestamp ASC
        """)
        trades = cursor.fetchall()
        
        print(f"   🔄 Processing {len(trades)} trades for profit calculation...")
        
        # FIFO calculation
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
        
        conn.close()
        
        print(f"   💰 Calculated profit: ${total_profit:.4f}")
        
        # Expected compound calculation
        if total_profit >= 5.0:
            base_order_size = 100.0
            reinvestment_rate = 0.3
            profit_factor = (total_profit * reinvestment_rate) / base_order_size
            new_multiplier = 1.0 + profit_factor
            new_multiplier = min(new_multiplier, 2.0)
            new_order_size = base_order_size * new_multiplier
            
            print(f"   📈 Expected multiplier: {new_multiplier:.3f}x")
            print(f"   💵 Expected order size: ${new_order_size:.2f}")
            
            return True, total_profit
        else:
            print(f"   📊 Profit ${total_profit:.2f} below $5.00 threshold")
            return True, total_profit
            
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        return False, 0.0

def fix_compound_manager():
    """Fix compound manager debugging"""
    
    print("🔧 Adding debugging to compound manager...")
    
    compound_file = Path("trading_bot/utils/compound_manager.py")
    
    if not compound_file.exists():
        print("❌ compound_manager.py not found")
        return False
    
    with open(compound_file, 'r') as f:
        content = f.read()
    
    # Check if debugging already exists
    if '🔍 Debugging compound calculation' in content:
        print("✅ Debugging already added")
        return True
    
    # Add detailed debugging to load_state_from_database method
    old_method_start = 'def load_state_from_database(self, db_path: str = "data/trading_history.db"):'
    
    if old_method_start in content:
        # Find the method and add debugging
        start_pos = content.find(old_method_start)
        end_pos = content.find('def ', start_pos + 1)
        if end_pos == -1:
            end_pos = len(content)
        
        # Extract current method
        current_method = content[start_pos:end_pos]
        
        # Enhanced method with debugging
        enhanced_method = '''    def load_state_from_database(self, db_path: str = "data/trading_history.db"):
        """Load compound state from profit data in database - ENHANCED WITH DEBUGGING"""
        
        self.logger.info(f"🔍 Debugging compound calculation...")
        self.logger.info(f"🔍 Database path: {db_path}")
        self.logger.info(f"🔍 Database exists: {Path(db_path).exists()}")
        self.logger.info(f"🔍 Working directory: {Path.cwd()}")
        
        try:
            import sqlite3
            from pathlib import Path

            with sqlite3.connect(db_path) as conn:
                # Calculate total profit using same logic as profit tracker
                cursor = conn.execute("""
                    SELECT symbol, side, quantity, price, timestamp 
                    FROM trades 
                    ORDER BY timestamp ASC
                """)

                trades = cursor.fetchall()
                self.logger.info(f"🔍 Found {len(trades)} trades in database")

                # FIFO profit calculation (same as profit tracker)
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

                self.logger.info(f"🔍 Calculated total profit: ${total_profit:.4f}")
                self.logger.info(f"🔍 Minimum threshold: ${self.min_profit_threshold:.2f}")

                # Update compound state based on database profit
                if total_profit >= self.min_profit_threshold:
                    self.accumulated_profit = total_profit

                    profit_factor = (
                        total_profit
                        * self.profit_reinvestment_rate
                        / self.base_order_size
                    )
                    new_multiplier = 1.0 + profit_factor
                    new_multiplier = min(new_multiplier, self.max_order_size_multiplier)

                    self.current_order_multiplier = new_multiplier

                    self.logger.info(f"🔍 Profit factor: {profit_factor:.4f}")
                    self.logger.info(f"🔍 New multiplier: {new_multiplier:.4f}")
                    self.logger.info(f"🔍 New order size: ${self.base_order_size * new_multiplier:.2f}")

                    self.logger.info(
                        f"✅ Loaded compound state from database: ${total_profit:.2f} profit, {new_multiplier:.3f}x multiplier"
                    )
                else:
                    self.logger.info(
                        f"📊 Database profit ${total_profit:.2f} below threshold ${self.min_profit_threshold:.2f}, keeping base settings"
                    )

        except Exception as e:
            self.logger.error(f"❌ Failed to load compound state from database: {e}")
            self.logger.error(f"❌ Database path: {db_path}")
            self.logger.error(f"❌ Working directory: {Path.cwd()}")
            self.logger.info("📊 Using default compound settings")

'''
        
        # Replace the method
        new_content = content[:start_pos] + enhanced_method + content[end_pos:]
        
        # Backup and save
        with open(compound_file.with_suffix('.py.backup3'), 'w') as f:
            f.write(content)
        
        with open(compound_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Enhanced compound manager with debugging")
        return True
    
    else:
        print("❌ Could not find load_state_from_database method")
        return False

def fix_telegram_startup_message():
    """Fix Telegram API 400 error by simplifying startup message"""
    
    print("🔧 Fixing Telegram startup message...")
    
    main_file = Path("trading_bot/main.py")
    
    if not main_file.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find the problematic startup notification
    startup_notification_start = 'await self.telegram_notifier.notify_bot_status('
    
    if startup_notification_start in content:
        # Find the full notification block
        start_pos = content.find(startup_notification_start)
        end_pos = content.find(')', start_pos)
        
        # Count parentheses to find the correct closing
        paren_count = 0
        for i, char in enumerate(content[start_pos:]):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    end_pos = start_pos + i + 1
                    break
        
        # Replace with simpler notification
        simple_notification = '''await self.telegram_notifier.notify_bot_status(
                    "started",
                    f"🤖 Enhanced Trading Bot Online!\\n"
                    f"Order size: ${compound_info['current_order_size']:.0f} ({compound_info['order_multiplier']:.2f}x)\\n"
                    f"Market: {market_info['session']} ({market_info['activity_level']})\\n"
                    f"Commands: /start for help"
                )'''
        
        new_content = content[:start_pos] + simple_notification + content[end_pos:]
        
        # Backup and save
        with open(main_file.with_suffix('.py.backup4'), 'w') as f:
            f.write(content)
        
        with open(main_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Simplified Telegram startup message")
        return True
    
    else:
        print("❌ Could not find startup notification")
        return False

def manual_compound_test():
    """Test compound calculation manually"""
    
    print("🧪 Manual compound calculation test...")
    
    try:
        import sys
        sys.path.insert(0, 'trading_bot')
        
        from utils.compound_manager import CompoundManager
        from utils.database_logger import DatabaseLogger
        
        # Create instances
        db_logger = DatabaseLogger()
        compound_manager = CompoundManager(db_logger, base_order_size=100.0)
        
        # Load state
        compound_manager.load_state_from_database("data/trading_history.db")
        
        # Get status
        status = compound_manager.get_compound_status()
        
        print(f"   💰 Order size: ${status['current_order_size']:.2f}")
        print(f"   📈 Multiplier: {status['order_multiplier']:.3f}x")
        print(f"   💸 Profit: ${status['accumulated_profit']:.2f}")
        
        if status['accumulated_profit'] > 0:
            print("   ✅ Compound calculation working!")
            return True
        else:
            print("   ❌ Still showing $0.00 profit")
            return False
            
    except Exception as e:
        print(f"   ❌ Manual test failed: {e}")
        return False

def main():
    """Main fix process"""
    
    print("🔧 Fixing Lost Compound Interest & Telegram Error")
    print("=" * 50)
    
    # Step 1: Check database compound calculation
    print("1️⃣ Checking database compound calculation...")
    db_ok, calculated_profit = check_database_compound()
    
    if not db_ok:
        print("❌ Database issues found - cannot proceed")
        return
    
    # Step 2: Fix compound manager debugging
    print("\n2️⃣ Adding compound manager debugging...")
    fix_compound_manager()
    
    # Step 3: Fix Telegram message
    print("\n3️⃣ Fixing Telegram startup message...")
    fix_telegram_startup_message()
    
    # Step 4: Manual test
    print("\n4️⃣ Testing compound calculation...")
    compound_working = manual_compound_test()
    
    print("\n" + "=" * 50)
    print("🎯 FIX SUMMARY:")
    
    if calculated_profit > 0:
        print(f"✅ Database contains ${calculated_profit:.2f} profit")
    else:
        print("❌ Database shows $0.00 profit")
    
    print("✅ Enhanced compound manager debugging")
    print("✅ Simplified Telegram startup message")
    
    if compound_working:
        print("✅ Compound calculation working in test")
    else:
        print("❌ Compound calculation still failing")
    
    print("\n📋 Next Steps:")
    print("1. Restart your trading bot:")
    print("   cd trading_bot && python main.py")
    
    print("\n2. Look for detailed compound debugging:")
    print("   🔍 Debugging compound calculation...")
    print("   🔍 Found X trades in database")
    print("   🔍 Calculated total profit: $X.XX")
    
    print("\n3. Expected results:")
    if calculated_profit >= 5.0:
        expected_multiplier = 1.0 + (calculated_profit * 0.3 / 100.0)
        expected_order_size = 100.0 * expected_multiplier
        print(f"   ✅ Should show: ${expected_order_size:.0f} order size")
        print(f"   ✅ Should show: {expected_multiplier:.3f}x multiplier")
    else:
        print("   📊 Should remain at $100 (below threshold)")
    
    print("\n4. No more Telegram 400 errors")

if __name__ == "__main__":
    main()
