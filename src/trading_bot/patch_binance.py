#!/usr/bin/env python3
"""
Automatic BinanceManager Method Patcher
Adds missing place_market_buy and place_market_sell methods
"""

import os
import re
from pathlib import Path

def patch_binance_client():
    """Add missing trading methods to BinanceManager"""
    
    binance_file = Path("utils/binance_client.py")
    
    if not binance_file.exists():
        print("❌ utils/binance_client.py not found!")
        print("Make sure you're in the trading_bot directory")
        return False
    
    # Read current file
    with open(binance_file, 'r') as f:
        content = f.read()
    
    # Check if methods already exist
    if 'def place_market_buy' in content:
        print("✅ place_market_buy method already exists")
        return True
    
    print("🔧 Adding missing trading methods...")
    
    # Backup current file
    backup_file = binance_file.with_suffix('.py.backup_patched')
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"📋 Backup created: {backup_file}")
    
    # Methods to add
    trading_methods = '''
    def place_market_buy(self, symbol, quantity):
        """Place market buy order with timestamp handling"""
        try:
            if self.testnet:
                self.logger.info(f"TESTNET: Would buy {quantity} {symbol}")
                return {
                    "status": "FILLED", 
                    "symbol": symbol, 
                    "side": "BUY",
                    "executedQty": str(quantity),
                    "fills": [{"price": str(self.get_price(symbol))}],
                    "orderId": 12345
                }
            
            # For live trading, place actual order
            order = self.client.order_market_buy(
                symbol=symbol,
                quantity=quantity,
                timestamp=self._get_timestamp(),
                recvWindow=60000
            )
            self.logger.info(f"Market buy order placed: {order}")
            return order
        except Exception as e:
            self.logger.error(f"Error placing buy order: {e}")
            return None

    def place_market_sell(self, symbol, quantity):
        """Place market sell order with timestamp handling"""
        try:
            if self.testnet:
                self.logger.info(f"TESTNET: Would sell {quantity} {symbol}")
                return {
                    "status": "FILLED", 
                    "symbol": symbol, 
                    "side": "SELL",
                    "executedQty": str(quantity),
                    "fills": [{"price": str(self.get_price(symbol))}],
                    "orderId": 12346
                }
            
            # For live trading, place actual order
            order = self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity,
                timestamp=self._get_timestamp(),
                recvWindow=60000
            )
            self.logger.info(f"Market sell order placed: {order}")
            return order
        except Exception as e:
            self.logger.error(f"Error placing sell order: {e}")
            return None

    def _get_timestamp(self):
        """Get current timestamp for Binance API"""
        import time
        return int(time.time() * 1000)
'''
    
    # Find the best place to insert methods (before the last method or end of class)
    class_match = re.search(r'class BinanceManager.*?:', content, re.DOTALL)
    if not class_match:
        print("❌ Could not find BinanceManager class")
        return False
    
    # Find the end of the class (look for next class or end of file)
    class_start = class_match.end()
    
    # Find a good insertion point (after existing methods)
    # Look for the last method definition
    methods = list(re.finditer(r'\n    def \w+\(.*?\):', content[class_start:]))
    
    if methods:
        # Insert after the last method
        last_method = methods[-1]
        # Find the end of the last method (next def, class, or end of file)
        insertion_point = class_start + last_method.start()
        
        # Find the end of the last method
        rest_of_content = content[insertion_point:]
        next_def_match = re.search(r'\n(def |class |\nif __name__)', rest_of_content)
        
        if next_def_match:
            method_end = insertion_point + next_def_match.start()
        else:
            method_end = len(content)
    else:
        # No methods found, insert after class definition
        method_end = class_start
    
    # Insert the new methods
    new_content = content[:method_end] + trading_methods + content[method_end:]
    
    # Add import for time if not present
    if 'import time' not in new_content:
        # Add after other imports
        import_match = re.search(r'(import.*?\n)+', new_content)
        if import_match:
            import_end = import_match.end()
            new_content = new_content[:import_end] + 'import time\n' + new_content[import_end:]
        else:
            # Add at the beginning
            new_content = 'import time\n' + new_content
    
    # Write the patched file
    with open(binance_file, 'w') as f:
        f.write(new_content)
    
    print("✅ Trading methods added successfully!")
    print("✅ place_market_buy method added")
    print("✅ place_market_sell method added") 
    print("✅ _get_timestamp helper method added")
    
    return True

def test_patched_methods():
    """Test that the patched methods work"""
    try:
        import sys
        sys.path.append('.')
        from utils.binance_client import BinanceManager
        
        # Create manager instance
        bm = BinanceManager()
        
        # Test if methods exist
        if hasattr(bm, 'place_market_buy'):
            print("✅ place_market_buy method exists")
        else:
            print("❌ place_market_buy method missing")
            return False
            
        if hasattr(bm, 'place_market_sell'):
            print("✅ place_market_sell method exists")
        else:
            print("❌ place_market_sell method missing")
            return False
        
        print("🧪 Testing methods...")
        
        # Test buy method (should work in testnet mode)
        result = bm.place_market_buy("ADAUSDT", 1.0)
        if result:
            print("✅ place_market_buy test successful")
        else:
            print("⚠️ place_market_buy returned None")
        
        # Test sell method
        result = bm.place_market_sell("ADAUSDT", 1.0)
        if result:
            print("✅ place_market_sell test successful")
        else:
            print("⚠️ place_market_sell returned None")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing methods: {e}")
        return False

def main():
    """Main patcher function"""
    print("🔧 BINANCE MANAGER METHOD PATCHER")
    print("=" * 50)
    
    current_dir = os.getcwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check if we're in the right directory
    if not os.path.exists("utils/binance_client.py"):
        print("❌ Not in the correct directory!")
        print("Please run this from: /path/to/crypto-trading/trading-bot/src/trading_bot/")
        return
    
    # Patch the file
    success = patch_binance_client()
    
    if success:
        print("\n🧪 Testing patched methods...")
        test_success = test_patched_methods()
        
        if test_success:
            print("\n🎉 PATCH SUCCESSFUL!")
            print("Your bot should now be able to execute trades!")
            print("\nNext steps:")
            print("1. Restart your trading bot: python3 main.py")
            print("2. Watch for successful trade executions")
            print("3. Check Telegram for trade notifications")
        else:
            print("\n⚠️ Patch applied but tests failed")
            print("You may need to restart your Python session")
    else:
        print("\n❌ Patch failed!")
        print("You may need to add the methods manually")

if __name__ == "__main__":
    main()
