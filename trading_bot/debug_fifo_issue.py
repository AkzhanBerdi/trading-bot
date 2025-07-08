#!/usr/bin/env python3
"""
Debug FIFO Calculation Issue
Why is compound manager showing $0.00 when there are 37 trades?
"""

import sqlite3
from pathlib import Path


def analyze_trades_detailed():
    """Analyze trades in detail to find FIFO issue"""
    print("🔍 Analyzing trades for FIFO calculation issue...")
    
    db_path = "data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get ALL trades in chronological order (same as compound manager)
        cursor.execute("""
            SELECT symbol, side, quantity, price, timestamp 
            FROM trades 
            ORDER BY timestamp ASC
        """)
        trades = cursor.fetchall()
        
        print(f"📊 Processing {len(trades)} trades chronologically...")
        
        # Show first few trades to see the pattern
        print(f"\n📝 First 10 trades:")
        for i, trade in enumerate(trades[:10]):
            symbol, side, quantity, price, timestamp = trade
            print(f"   #{i+1}: {timestamp} | {side:4} {quantity:8.4f} {symbol:8} @ ${price:8.4f}")
        
        # Count by symbol and side
        cursor.execute("""
            SELECT symbol, side, COUNT(*), SUM(quantity), SUM(total_value)
            FROM trades 
            GROUP BY symbol, side
            ORDER BY symbol, side
        """)
        summary = cursor.fetchall()
        
        print(f"\n📈 Trade summary by symbol:")
        for symbol, side, count, qty, value in summary:
            print(f"   {symbol:8} {side:4}: {count:2} trades, {qty:10.4f} qty, ${value:10.2f} value")
        
        # Now trace FIFO calculation with detailed logging
        print(f"\n🧮 FIFO Calculation Trace:")
        
        open_buys = {}
        total_profit = 0.0
        
        for i, trade in enumerate(trades):
            symbol, side, quantity, price, timestamp = trade
            
            if side == "BUY":
                if symbol not in open_buys:
                    open_buys[symbol] = []
                open_buys[symbol].append({"qty": quantity, "price": price})
                print(f"   #{i+1}: BUY  {quantity:8.4f} {symbol} @ ${price:8.4f} → Queue: {len(open_buys[symbol])} orders")
                
            elif side == "SELL":
                print(f"   #{i+1}: SELL {quantity:8.4f} {symbol} @ ${price:8.4f}")
                
                if symbol not in open_buys:
                    print(f"         ❌ No open buys for {symbol} - SKIPPING")
                    continue
                
                if not open_buys[symbol]:
                    print(f"         ❌ Empty buy queue for {symbol} - SKIPPING")
                    continue
                
                remaining_qty = quantity
                sell_profit = 0.0
                matches = 0
                
                while remaining_qty > 0 and open_buys[symbol]:
                    buy = open_buys[symbol][0]
                    match_qty = min(buy["qty"], remaining_qty)
                    profit = (price - buy["price"]) * match_qty
                    matches += 1
                    
                    print(f"         Match #{matches}: {match_qty:8.4f} @ ${buy['price']:8.4f} → profit: ${profit:8.4f}")
                    
                    if profit > 0:
                        total_profit += profit
                        sell_profit += profit
                    
                    remaining_qty -= match_qty
                    buy["qty"] -= match_qty
                    
                    if buy["qty"] <= 0:
                        open_buys[symbol].pop(0)
                
                print(f"         💰 Sell profit: ${sell_profit:8.4f} | Running total: ${total_profit:8.4f}")
        
        print(f"\n🎯 FINAL RESULT:")
        print(f"   Total profit: ${total_profit:.4f}")
        print(f"   Rounded: ${total_profit:.2f}")
        print(f"   Threshold: $5.00")
        
        if total_profit >= 5.0:
            print(f"   ✅ Should trigger compounding!")
        elif total_profit > 0:
            print(f"   📊 Below threshold but profit exists")
        else:
            print(f"   ❌ Zero profit - check for issues above")
        
        # Check for remaining open positions
        print(f"\n📦 Remaining open positions:")
        for symbol, buys in open_buys.items():
            if buys:
                total_qty = sum(buy["qty"] for buy in buys)
                avg_price = sum(buy["qty"] * buy["price"] for buy in buys) / total_qty
                print(f"   {symbol}: {total_qty:.4f} qty @ ${avg_price:.4f} avg")
        
        conn.close()
        return total_profit
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 0.0


def check_duplicate_trades():
    """Check for duplicate trades that might cause issues"""
    print(f"\n🔍 Checking for duplicate trades...")
    
    db_path = "data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find potential duplicates
        cursor.execute("""
            SELECT timestamp, symbol, side, quantity, price, COUNT(*) as count
            FROM trades 
            GROUP BY timestamp, symbol, side, quantity, price
            HAVING COUNT(*) > 1
            ORDER BY timestamp
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"   ⚠️  Found {len(duplicates)} sets of duplicate trades:")
            for dup in duplicates:
                timestamp, symbol, side, qty, price, count = dup
                print(f"      {timestamp} | {side} {qty} {symbol} @ ${price} (×{count})")
        else:
            print(f"   ✅ No duplicate trades found")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Duplicate check failed: {e}")


def test_simplified_profit():
    """Test a simplified profit calculation"""
    print(f"\n🧪 Testing simplified profit calculation...")
    
    db_path = "data/trading_history.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Simple approach: assume each sell is profitable
        cursor.execute("""
            SELECT symbol, quantity, price, total_value
            FROM trades 
            WHERE side = 'SELL'
            ORDER BY timestamp
        """)
        sells = cursor.fetchall()
        
        print(f"   📊 Found {len(sells)} sell trades:")
        
        simple_profit = 0.0
        for sell in sells:
            symbol, qty, price, total_val = sell
            # Rough estimate: assume 2% profit per sell
            estimated_profit = total_val * 0.02
            simple_profit += estimated_profit
            print(f"      {symbol} sell ${total_val:.2f} → ~${estimated_profit:.2f} profit")
        
        print(f"   💰 Estimated total profit: ${simple_profit:.2f}")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Simplified test failed: {e}")


def main():
    """Main debugging process"""
    print("🔍 Debug FIFO Calculation Issue")
    print("=" * 50)
    
    # Step 1: Detailed trade analysis
    total_profit = analyze_trades_detailed()
    
    # Step 2: Check for duplicates
    check_duplicate_trades()
    
    # Step 3: Simplified profit test
    test_simplified_profit()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    
    if total_profit == 0.0:
        print("❌ FIFO calculation is returning exactly $0.00")
        print("   Possible causes:")
        print("   1. All sells are at losses")
        print("   2. Sells happening before corresponding buys") 
        print("   3. Symbol name mismatches")
        print("   4. Timestamp ordering issues")
        print("   5. Duplicate trades causing calculation errors")
    elif total_profit < 5.0:
        print(f"✅ FIFO is working - profit is ${total_profit:.2f}")
        print("📊 Below $5.00 threshold explains the compound behavior")
    else:
        print(f"❌ FIFO found ${total_profit:.2f} profit but compound isn't working")
        print("   Check compound manager database path and error handling")


if __name__ == "__main__":
    main()
