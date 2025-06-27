#!/usr/bin/env python3
"""
Quick Precision Fix for LOT_SIZE Errors
Patches your existing trading methods to handle quantity precision correctly
"""

import os
import re
from pathlib import Path

def create_quick_fix():
    """Create a quick fix file that adds precision handling"""
    
    quick_fix_code = '''
# Quick fix for LOT_SIZE errors - add to your BinanceManager class

def round_quantity(self, symbol, quantity):
    """Round quantity to correct precision for symbol"""
    # Binance precision requirements for your trading pairs
    if symbol == 'ADAUSDT':
        return round(float(quantity), 0)  # Whole numbers
    elif symbol == 'AVAXUSDT':  
        return round(float(quantity), 2)  # 2 decimal places
    else:
        return round(float(quantity), 2)  # Default 2 decimals

def place_market_buy_fixed(self, symbol, usd_amount):
    """Fixed market buy using USD amount"""
    try:
        # Get current price
        current_price = self.get_price(symbol)
        if not current_price:
            return None
        
        # Calculate quantity
        raw_quantity = usd_amount / current_price
        quantity = self.round_quantity(symbol, raw_quantity)
        
        self.logger.info(f"Buy order: ${usd_amount} → {quantity} {symbol}")
        
        if self.testnet:
            return {
                "status": "FILLED", 
                "symbol": symbol, 
                "side": "BUY",
                "executedQty": str(quantity),
                "fills": [{"price": str(current_price)}],
                "orderId": 12345
            }
        
        # Place actual order
        order = self.client.order_market_buy(
            symbol=symbol,
            quantity=quantity,
            timestamp=self._get_timestamp(),
            recvWindow=60000
        )
        return order
        
    except Exception as e:
        self.logger.error(f"Error in fixed buy order: {e}")
        return None

def place_market_sell_fixed(self, symbol, quantity):
    """Fixed market sell with proper precision"""
    try:
        # Round to correct precision
        rounded_quantity = self.round_quantity(symbol, quantity)
        
        self.logger.info(f"Sell order: {rounded_quantity} {symbol}")
        
        if self.testnet:
            current_price = self.get_price(symbol)
            return {
                "status": "FILLED", 
                "symbol": symbol, 
                "side": "SELL",
                "executedQty": str(rounded_quantity),
                "fills": [{"price": str(current_price)}],
                "orderId": 12346
            }
        
        # Place actual order
        order = self.client.order_market_sell(
            symbol=symbol,
            quantity=rounded_quantity,
            timestamp=self._get_timestamp(),
            recvWindow=60000
        )
        return order
        
    except Exception as e:
        self.logger.error(f"Error in fixed sell order: {e}")
        return None
'''
    
    with open("binance_precision_fix.py", "w") as f:
        f.write(quick_fix_code)
    
    print("📁 Created: binance_precision_fix.py")
    return True

def show_manual_fix_instructions():
    """Show instructions for manual fix"""
    
    instructions = """
🔧 MANUAL PRECISION FIX INSTRUCTIONS:

1. QUICK TEMPORARY FIX (Test immediately):
   
   In your main.py, update the execute_grid_order_with_notifications method:
   
   # Replace this line:
   if action == 'BUY':
       order = self.binance.place_market_buy(symbol, quantity)
   
   # With this:
   if action == 'BUY':
       # Convert quantity back to USD amount for precision fix
       current_price = self.binance.get_price(symbol)
       usd_amount = quantity * current_price
       
       # Round to proper precision
       if symbol == 'ADAUSDT':
           fixed_quantity = round(quantity, 0)  # Whole numbers
       elif symbol == 'AVAXUSDT':
           fixed_quantity = round(quantity, 2)  # 2 decimals  
       else:
           fixed_quantity = round(quantity, 2)
           
       order = self.binance.place_market_buy(symbol, fixed_quantity)

2. BETTER APPROACH (Modify your GridTrader):
   
   Change your grid setup to use USD amounts instead of quantities:
   
   # In your GridTrader.setup_grid method, change:
   quantity = self.base_order_size / price
   
   # To:
   usd_amount = self.base_order_size  # Keep as USD amount
   
   # Then in your trading logic:
   current_price = self.binance.get_price(symbol)
   quantity = usd_amount / current_price
   
   # Round properly:
   if symbol == 'ADAUSDT':
       quantity = round(quantity, 0)
   elif symbol == 'AVAXUSDT': 
       quantity = round(quantity, 2)

3. PRECISION RULES:
   - ADAUSDT: Whole numbers (87, not 87.49)
   - AVAXUSDT: 2 decimal places (2.82, not 2.825)
   - Always check Binance docs for exact precision requirements

4. TEST WITH:
   python3 main.py
   
   You should see:
   ✅ BUY Order Filled! instead of LOT_SIZE errors
"""
    
    return instructions

def test_precision_fix():
    """Test the precision rounding"""
    
    print("🧪 TESTING PRECISION ROUNDING")
    print("=" * 40)
    
    # Test quantities from your error
    test_cases = [
        ('ADAUSDT', 87.49, 87),     # Should round to whole number
        ('AVAXUSDT', 2.825, 2.82), # Should round to 2 decimals
        ('AVAXUSDT', 2.8666, 2.87) # Another test case
    ]
    
    for symbol, input_qty, expected in test_cases:
        if symbol == 'ADAUSDT':
            result = round(input_qty, 0)
        elif symbol == 'AVAXUSDT':
            result = round(input_qty, 2)
        else:
            result = round(input_qty, 2)
        
        status = "✅" if result == expected else "❌"
        print(f"{status} {symbol}: {input_qty} → {result} (expected {expected})")
    
    print(f"\n💰 ORDER VALUE CHECK:")
    print(f"ADA: 87 × $0.5715 = ${87 * 0.5715:.2f}")
    print(f"AVAX: 2.82 × $17.70 = ${2.82 * 17.70:.2f}")
    print(f"Both values > $5 minimum ✅")

def main():
    """Main fix function"""
    print("🔧 BINANCE PRECISION FIX")
    print("=" * 50)
    
    print("📊 Analysis of your LOT_SIZE error:")
    print("   ADA: 87.49 → Should be 87 (whole numbers)")
    print("   AVAX: 2.825 → Should be 2.82 (2 decimals)")
    
    # Test precision rounding
    test_precision_fix()
    
    # Create fix file
    create_quick_fix()
    
    # Show instructions
    print(f"\n{show_manual_fix_instructions()}")
    
    print(f"\n🎯 FASTEST FIX (Do this now):")
    print("1. Edit your main.py")
    print("2. In execute_grid_order_with_notifications method:")
    print("3. Before calling place_market_buy, add:")
    print("   if symbol == 'ADAUSDT':")
    print("       quantity = round(quantity, 0)")
    print("   elif symbol == 'AVAXUSDT':")
    print("       quantity = round(quantity, 2)")
    print("4. Save and restart: python3 main.py")
    
    print(f"\n🚀 Expected result: ✅ Successful trades!")

if __name__ == "__main__":
    main()
