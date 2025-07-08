#!/usr/bin/env python3
"""
Fix Compound Manager Database Path
Replace the load_state_from_database method with working version
"""

import os
from pathlib import Path

def create_fixed_compound_manager():
    """Create fixed compound manager with correct database handling"""
    
    compound_manager_fix = '''    def load_state_from_database(self, db_path: str = "data/trading_history.db"):
        """Load compound state from profit data in database - FIXED VERSION"""
        
        # Debug: Show exactly what path we're using
        abs_path = Path(db_path).resolve()
        self.logger.info(f"🔍 Compound manager loading from: {db_path}")
        self.logger.info(f"🔍 Absolute path: {abs_path}")
        self.logger.info(f"🔍 Database exists: {abs_path.exists()}")
        self.logger.info(f"🔍 Working directory: {Path.cwd()}")
        
        try:
            import sqlite3

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

                    self.logger.info(
                        f"✅ Loaded compound state from database: ${total_profit:.2f} profit, {new_multiplier:.3f}x multiplier"
                    )
                else:
                    self.logger.info(
                        f"📊 Database profit ${total_profit:.2f} below threshold ${self.min_profit_threshold:.2f}, keeping base settings"
                    )

        except Exception as e:
            self.logger.error(f"❌ Failed to load compound state from database: {e}")
            self.logger.error(f"❌ Database path attempted: {db_path}")
            self.logger.error(f"❌ Working directory: {Path.cwd()}")
            self.logger.info("📊 Using default compound settings")'''

    return compound_manager_fix

def update_compound_manager_file():
    """Update the compound manager file with the fix"""
    
    compound_file = "trading_bot/utils/compound_manager.py"
    
    if not Path(compound_file).exists():
        print(f"❌ Compound manager file not found: {compound_file}")
        return False
    
    print(f"🔧 Updating {compound_file}...")
    
    try:
        with open(compound_file, 'r') as f:
            content = f.read()
        
        # Find the load_state_from_database method
        start_marker = 'def load_state_from_database(self, db_path: str = "data/trading_history.db"):'
        end_marker = 'def record_trade_profit(self'  # Next method
        
        start_pos = content.find(start_marker)
        if start_pos == -1:
            print("❌ Could not find load_state_from_database method")
            return False
        
        end_pos = content.find(end_marker)
        if end_pos == -1:
            # If next method not found, find class end or file end
            end_pos = len(content)
        
        # Replace the method
        fixed_method = create_fixed_compound_manager()
        new_content = content[:start_pos] + fixed_method + content[end_pos-4:]  # Keep some spacing
        
        # Backup original
        with open(f"{compound_file}.backup", 'w') as f:
            f.write(content)
        
        # Write fixed version
        with open(compound_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated {compound_file}")
        print(f"📋 Backup saved as {compound_file}.backup")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update {compound_file}: {e}")
        return False

def create_manual_test_script():
    """Create a script to manually test compound loading"""
    
    test_script = '''#!/usr/bin/env python3
"""
Manually test compound manager loading
"""

import sys
import os
sys.path.append('.')

from utils.compound_manager import CompoundManager
from utils.database_logger import DatabaseLogger

def test_compound_loading():
    """Test compound manager loading manually"""
    print("🧪 Testing compound manager loading...")
    
    # Create compound manager exactly like main.py does
    db_logger = DatabaseLogger()
    compound_manager = CompoundManager(db_logger, base_order_size=100.0)
    
    # Test loading
    compound_manager.load_state_from_database("data/trading_history.db")
    
    # Show results
    status = compound_manager.get_compound_status()
    print(f"\\n📊 Compound Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\\n💰 Current order size: ${compound_manager.get_current_order_size():.2f}")

if __name__ == "__main__":
    test_compound_loading()
'''
    
    with open("trading_bot/test_compound_loading.py", 'w') as f:
        f.write(test_script)
    
    print("✅ Created trading_bot/test_compound_loading.py")

def main():
    """Main fix process"""
    print("🔧 Fixing Compound Manager Database Path")
    print("=" * 50)
    
    # Step 1: Update compound manager
    if update_compound_manager_file():
        print("✅ Compound manager updated with debugging")
    else:
        print("❌ Failed to update compound manager")
        return
    
    # Step 2: Create test script
    create_manual_test_script()
    
    print("\\n" + "=" * 50)
    print("🎯 FIX COMPLETE!")
    
    print("\\n📋 Next Steps:")
    print("1. cd trading_bot")
    print("2. python test_compound_loading.py  # Test the fix")
    print("3. python main.py  # Restart bot")
    print("4. Check logs for detailed debugging output")
    
    print("\\n✅ Expected Results:")
    print("   🔍 Compound manager loading from: data/trading_history.db")
    print("   🔍 Found 37 trades in database")
    print("   🔍 Calculated total profit: $26.5668")
    print("   ✅ Loaded compound state: $26.57 profit, 1.080x multiplier")
    print("   💰 Using compound order size: $108")

if __name__ == "__main__":
    main()
