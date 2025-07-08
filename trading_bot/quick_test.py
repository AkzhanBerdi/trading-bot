#!/usr/bin/env python3
"""
Quick test to find and analyze the database
"""

import sqlite3
from pathlib import Path
import os

print(f"Current directory: {Path.cwd()}")

# Test all possible paths
paths_to_try = [
    "data/trading_history.db",
    "trading_bot/data/trading_history.db", 
    "../data/trading_history.db",
    "./data/trading_history.db"
]

for path in paths_to_try:
    if Path(path).exists():
        print(f"✅ Found database: {path}")
        
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            
            # Test same query as compound manager
            cursor.execute("SELECT symbol, side, quantity, price, timestamp FROM trades ORDER BY timestamp ASC")
            trades = cursor.fetchall()
            print(f"   📊 Contains {len(trades)} trades")
            
            if len(trades) > 0:
                # Quick FIFO test
                open_buys = {}
                total_profit = 0.0
                
                for trade in trades:
                    symbol, side, quantity, price, timestamp = trade
                    
                    if side == "BUY":
                        if symbol not in open_buys:
                            open_buys[symbol] = []
                        open_buys[symbol].append({"qty": quantity, "price": price})
                        
                    elif side == "SELL":
                        if symbol not in open_buys or not open_buys[symbol]:
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
                
                print(f"   💰 Calculated profit: ${total_profit:.4f}")
                
                if total_profit >= 5.0:
                    print(f"   ✅ Above $5 threshold - should compound!")
                elif total_profit > 0:
                    print(f"   📊 Below $5 threshold - explains compound behavior")
                else:
                    print(f"   ❌ Zero profit - need to investigate trades")
                    
                # Show trade breakdown
                cursor.execute("SELECT side, COUNT(*), SUM(total_value) FROM trades GROUP BY side")
                breakdown = cursor.fetchall()
                for side, count, total in breakdown:
                    print(f"   {side}: {count} trades, ${total:.2f}")
            
            conn.close()
            break
            
        except Exception as e:
            print(f"   ❌ Error reading {path}: {e}")
    else:
        print(f"❌ Not found: {path}")
