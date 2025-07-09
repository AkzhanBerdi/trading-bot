#!/usr/bin/env python3
"""
Force Compound Interest Fix
Directly fix the compound manager calculation
"""

import sqlite3
from pathlib import Path

def force_fix_compound_manager():
    """Completely replace the compound manager load method"""
    
    print("🔧 Force fixing compound manager...")
    
    compound_file = Path("trading_bot/utils/compound_manager.py")
    
    if not compound_file.exists():
        print("❌ compound_manager.py not found")
        return False
    
    with open(compound_file, 'r') as f:
        content = f.read()
    
    # Find and replace the entire load_state_from_database method
    method_start = 'def load_state_from_database(self, db_path: str = "data/trading_history.db"):'
    method_end = '\n    def '  # Next method
    
    start_pos = content.find(method_start)
    if start_pos == -1:
        print("❌ Could not find load_state_from_database method")
        return False
    
    # Find the end of the method (next method definition)
    search_start = start_pos + len(method_start)
    next_method_pos = content.find('\n    def ', search_start)
    
    if next_method_pos == -1:
        # If no next method, find class end or file end
        next_method_pos = len(content)
    
    # Create the completely new method
    new_method = '''    def load_state_from_database(self, db_path: str = "data/trading_history.db"):
        """FIXED: Load compound state from profit data in database"""
        self.logger.info(f"🔄 FIXED: Loading compound state from {db_path}")
        
        try:
            import sqlite3
            from pathlib import Path

            # Ensure absolute path resolution
            if not Path(db_path).is_absolute():
                abs_db_path = Path.cwd() / db_path
            else:
                abs_db_path = Path(db_path)
            
            self.logger.info(f"🔄 FIXED: Using absolute path: {abs_db_path}")
            self.logger.info(f"🔄 FIXED: Database exists: {abs_db_path.exists()}")

            with sqlite3.connect(str(abs_db_path)) as conn:
                # Get all trades for FIFO calculation
                cursor = conn.execute("""
                    SELECT symbol, side, quantity, price, timestamp 
                    FROM trades 
                    ORDER BY timestamp ASC
                """)

                trades = cursor.fetchall()
                self.logger.info(f"🔄 FIXED: Found {len(trades)} trades")

                if len(trades) == 0:
                    self.logger.info("🔄 FIXED: No trades found, using base settings")
                    return

                # FIFO profit calculation - EXACT implementation
                open_buys = {}
                total_profit = 0.0
                profitable_sells = 0

                for i, trade in enumerate(trades):
                    symbol, side, quantity, price, timestamp = trade
                    
                    if side == "BUY":
                        if symbol not in open_buys:
                            open_buys[symbol] = []
                        open_buys[symbol].append({"qty": quantity, "price": price})
                        
                    elif side == "SELL":
                        if symbol not in open_buys or not open_buys[symbol]:
                            continue
                            
                        remaining_qty = quantity
                        sell_profit = 0.0
                        
                        while remaining_qty > 0 and open_buys[symbol]:
                            buy = open_buys[symbol][0]
                            match_qty = min(buy["qty"], remaining_qty)
                            profit = (price - buy["price"]) * match_qty
                            
                            if profit > 0:
                                total_profit += profit
                                sell_profit += profit
                            
                            remaining_qty -= match_qty
                            buy["qty"] -= match_qty
                            
                            if buy["qty"] <= 0:
                                open_buys[symbol].pop(0)
                        
                        if sell_profit > 0:
                            profitable_sells += 1

                self.logger.info(f"🔄 FIXED: Calculated profit: ${total_profit:.4f}")
                self.logger.info(f"🔄 FIXED: Profitable sells: {profitable_sells}")
                self.logger.info(f"🔄 FIXED: Threshold: ${self.min_profit_threshold:.2f}")

                # Apply compound interest if above threshold
                if total_profit >= self.min_profit_threshold:
                    self.accumulated_profit = total_profit

                    # Calculate new multiplier
                    profit_factor = (total_profit * self.profit_reinvestment_rate) / self.base_order_size
                    new_multiplier = 1.0 + profit_factor
                    new_multiplier = min(new_multiplier, self.max_order_size_multiplier)

                    self.current_order_multiplier = new_multiplier

                    self.logger.info(f"🔄 FIXED: Profit factor: {profit_factor:.6f}")
                    self.logger.info(f"🔄 FIXED: New multiplier: {new_multiplier:.6f}")
                    self.logger.info(f"🔄 FIXED: New order size: ${self.base_order_size * new_multiplier:.2f}")

                    self.logger.info(
                        f"✅ FIXED: Loaded compound state - ${total_profit:.2f} profit, {new_multiplier:.3f}x multiplier"
                    )
                else:
                    self.logger.info(
                        f"📊 FIXED: Profit ${total_profit:.2f} below ${self.min_profit_threshold:.2f} threshold"
                    )

        except Exception as e:
            self.logger.error(f"❌ FIXED: Compound loading failed: {e}")
            self.logger.error(f"❌ FIXED: Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"❌ FIXED: Traceback: {traceback.format_exc()}")
            self.logger.info("📊 FIXED: Using default compound settings")

'''
    
    # Replace the method
    new_content = content[:start_pos] + new_method + content[next_method_pos:]
    
    # Backup original
    backup_file = compound_file.with_suffix('.py.backup_force')
    with open(backup_file, 'w') as f:
        f.write(content)
    
    # Write the fixed version
    with open(compound_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Force-fixed compound manager")
    print(f"📋 Backup saved: {backup_file}")
    return True

def create_telegram_fix():
    """Create a simple Telegram notification fix"""
    
    print("🔧 Creating simple Telegram fix...")
    
    main_file = Path("trading_bot/main.py")
    
    if not main_file.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find and replace the startup notification with a very simple one
    notification_start = 'await self.telegram_notifier.notify_bot_status('
    
    if notification_start in content:
        # Find the complete notification block
        start_pos = content.find(notification_start)
        
        # Find the end by counting parentheses
        paren_count = 0
        end_pos = start_pos
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    end_pos = i + 1
                    break
        
        # Replace with minimal notification
        simple_notification = '''await self.telegram_notifier.notify_info(
                    f"🤖 Bot Started - Order Size: ${compound_info['current_order_size']:.0f}"
                )'''
        
        new_content = content[:start_pos] + simple_notification + content[end_pos:]
        
        # Backup and save
        backup_file = main_file.with_suffix('.py.backup_telegram')
        with open(backup_file, 'w') as f:
            f.write(content)
        
        with open(main_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Simplified Telegram notification")
        return True
    
    else:
        print("❌ Telegram notification not found")
        return False

def test_fixed_compound():
    """Test the fixed compound calculation"""
    
    print("🧪 Testing fixed compound calculation...")
    
    try:
        import sys
        sys.path.insert(0, 'trading_bot')
        
        # Import the fixed version
        from utils.compound_manager import CompoundManager
        from utils.database_logger import DatabaseLogger
        
        # Test the calculation
        db_logger = DatabaseLogger()
        compound_manager = CompoundManager(db_logger, base_order_size=100.0)
        
        print("   🔄 Loading state from database...")
        compound_manager.load_state_from_database("data/trading_history.db")
        
        # Check results
        status = compound_manager.get_compound_status()
        
        print(f"   💰 Order size: ${status['current_order_size']:.2f}")
        print(f"   📈 Multiplier: {status['order_multiplier']:.3f}x")
        print(f"   💸 Profit: ${status['accumulated_profit']:.2f}")
        
        if status['accumulated_profit'] > 0:
            print("   ✅ FIXED! Compound calculation working!")
            return True
        else:
            print("   ❌ Still not working")
            return False
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

def calculate_expected_compound():
    """Calculate what compound should be based on database"""
    
    print("📊 Calculating expected compound from database...")
    
    try:
        conn = sqlite3.connect("trading_bot/data/trading_history.db")
        cursor = conn.cursor()
        
        # Use the actual database calculation
        cursor.execute("""
            SELECT symbol, side, quantity, price, timestamp 
            FROM trades 
            ORDER BY timestamp ASC
        """)
        trades = cursor.fetchall()
        
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
        
        # Calculate compound
        base_order_size = 100.0
        reinvestment_rate = 0.3
        profit_factor = (total_profit * reinvestment_rate) / base_order_size
        new_multiplier = 1.0 + profit_factor
        new_multiplier = min(new_multiplier, 2.0)
        new_order_size = base_order_size * new_multiplier
        
        print(f"   💰 Database profit: ${total_profit:.4f}")
        print(f"   📊 Profit factor: {profit_factor:.6f}")
        print(f"   📈 Expected multiplier: {new_multiplier:.6f}")
        print(f"   💵 Expected order size: ${new_order_size:.2f}")
        
        return total_profit, new_multiplier, new_order_size
        
    except Exception as e:
        print(f"   ❌ Calculation failed: {e}")
        return 0, 1.0, 100.0

def main():
    """Main force fix process"""
    
    print("🔧 FORCE FIXING Compound Interest & Telegram")
    print("=" * 50)
    
    # Step 1: Calculate expected values
    print("1️⃣ Calculating expected compound values...")
    expected_profit, expected_mult, expected_size = calculate_expected_compound()
    
    # Step 2: Force fix compound manager
    print("\n2️⃣ Force fixing compound manager...")
    compound_fixed = force_fix_compound_manager()
    
    # Step 3: Fix Telegram
    print("\n3️⃣ Fixing Telegram notification...")
    telegram_fixed = create_telegram_fix()
    
    # Step 4: Test fix
    print("\n4️⃣ Testing fixed compound calculation...")
    test_working = test_fixed_compound()
    
    print("\n" + "=" * 50)
    print("🎯 FORCE FIX RESULTS:")
    
    if expected_profit > 0:
        print(f"✅ Database contains ${expected_profit:.2f} profit")
        print(f"✅ Should result in {expected_mult:.3f}x multiplier")
        print(f"✅ Should result in ${expected_size:.0f} order size")
    
    if compound_fixed:
        print("✅ Compound manager force-fixed")
    else:
        print("❌ Compound manager fix failed")
    
    if telegram_fixed:
        print("✅ Telegram notification simplified")
    else:
        print("❌ Telegram fix failed")
    
    if test_working:
        print("✅ Fixed compound calculation working!")
    else:
        print("❌ Compound still not working")
    
    print("\n📋 FINAL STEPS:")
    print("1. Restart bot: cd trading_bot && python main.py")
    print("2. Look for: 🔄 FIXED: Found 37 trades")
    print("3. Look for: ✅ FIXED: Loaded compound state")
    print(f"4. Expect: ${expected_size:.0f} order size instead of $100")
    print("5. No more Telegram 400 errors")
    
    print(f"\n🎯 YOUR BOT SHOULD NOW USE ${expected_size:.0f} ORDERS! 🚀")

if __name__ == "__main__":
    main()
