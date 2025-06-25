#!/usr/bin/env python3
"""
Standalone Grid Trading Diagnostic Script
Run this in a separate terminal to check grid status and market conditions
while your trading bot continues running.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from trading_bot.utils.binance_client import BinanceManager
from trading_bot.strategies.grid_trading import GridTrader
from dotenv import load_dotenv

def analyze_volatility(binance, symbol, hours=24):
    """Analyze recent price volatility"""
    try:
        # Get recent klines (hourly data for the specified hours)
        klines = binance.get_klines(symbol, "1h", limit=hours)
        if not klines or len(klines) < 2:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert price columns to float
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        # Calculate volatility metrics
        current_price = df['close'].iloc[-1]
        price_range_24h = (df['high'].max() - df['low'].min()) / current_price * 100
        avg_hourly_change = df['close'].pct_change().abs().mean() * 100
        max_hourly_change = df['close'].pct_change().abs().max() * 100
        
        # Calculate recent trend
        price_6h_ago = df['close'].iloc[-7] if len(df) >= 7 else df['close'].iloc[0]
        trend_6h = (current_price - price_6h_ago) / price_6h_ago * 100
        
        return {
            'current_price': current_price,
            'price_range_24h_percent': price_range_24h,
            'avg_hourly_change_percent': avg_hourly_change,
            'max_hourly_change_percent': max_hourly_change,
            'trend_6h_percent': trend_6h,
            'high_24h': df['high'].max(),
            'low_24h': df['low'].min()
        }
        
    except Exception as e:
        print(f"Error analyzing volatility for {symbol}: {e}")
        return None

def simulate_grid_levels(current_price, grid_size_percent=2.5, num_grids=8):
    """Simulate what grid levels would look like"""
    grid_size = grid_size_percent / 100
    
    buy_levels = []
    sell_levels = []
    
    # Create buy levels below current price
    for i in range(1, num_grids + 1):
        price = current_price * (1 - grid_size * i)
        buy_levels.append({
            'level': i,
            'price': price,
            'distance_from_current': current_price - price,
            'distance_percent': (current_price - price) / current_price * 100
        })
    
    # Create sell levels above current price
    for i in range(1, num_grids + 1):
        price = current_price * (1 + grid_size * i)
        sell_levels.append({
            'level': i,
            'price': price,
            'distance_from_current': price - current_price,
            'distance_percent': (price - current_price) / current_price * 100
        })
    
    return buy_levels, sell_levels

def diagnose_grid_trading():
    """Main diagnostic function"""
    print("🔍 GRID TRADING DIAGNOSTIC")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    # Initialize Binance client
    try:
        binance = BinanceManager()
        if not binance.test_connection():
            print("❌ Failed to connect to Binance")
            return
        print("✅ Connected to Binance")
    except Exception as e:
        print(f"❌ Binance initialization failed: {e}")
        return
    
    # Assets to analyze (matching your bot config)
    assets = [
        {"symbol": "ADAUSDT", "name": "ADA", "grid_size": 2.5, "num_grids": 8},
        {"symbol": "AVAXUSDT", "name": "AVAX", "grid_size": 2.0, "num_grids": 8}
    ]
    
    for asset in assets:
        print(f"\n🔸 {asset['name']} ({asset['symbol']}) ANALYSIS")
        print("-" * 40)
        
        # Get current price
        current_price = binance.get_price(asset['symbol'])
        if not current_price:
            print(f"❌ Could not get price for {asset['symbol']}")
            continue
        
        print(f"📊 Current Price: ${current_price:.4f}")
        
        # Analyze volatility
        vol_data = analyze_volatility(binance, asset['symbol'], 24)
        if vol_data:
            print(f"📈 24h Range: ${vol_data['low_24h']:.4f} - ${vol_data['high_24h']:.4f} "
                  f"({vol_data['price_range_24h_percent']:.1f}%)")
            print(f"📊 Avg Hourly Change: {vol_data['avg_hourly_change_percent']:.2f}%")
            print(f"📊 Max Hourly Change: {vol_data['max_hourly_change_percent']:.2f}%")
            print(f"📈 6h Trend: {vol_data['trend_6h_percent']:+.2f}%")
            
            # Volatility assessment
            if vol_data['avg_hourly_change_percent'] < 0.5:
                print("💤 LOW volatility - consider smaller grid spacing")
            elif vol_data['avg_hourly_change_percent'] > 2.0:
                print("⚡ HIGH volatility - current grid spacing should work well")
            else:
                print("📊 MODERATE volatility - grid spacing looks appropriate")
        
        # Simulate grid levels
        buy_levels, sell_levels = simulate_grid_levels(
            current_price, 
            asset['grid_size'], 
            asset['num_grids']
        )
        
        print(f"\n🎯 GRID LEVELS (±{asset['grid_size']}% spacing):")
        
        # Show nearest buy/sell levels
        nearest_buy = buy_levels[0]  # Level 1 is nearest
        nearest_sell = sell_levels[0]  # Level 1 is nearest
        
        print(f"🟢 Nearest BUY:  ${nearest_buy['price']:.4f} "
              f"({nearest_buy['distance_percent']:.1f}% below)")
        print(f"🔴 Nearest SELL: ${nearest_sell['price']:.4f} "
              f"({nearest_sell['distance_percent']:.1f}% above)")
        
        # Check if recent volatility would have triggered trades
        if vol_data:
            would_buy = vol_data['low_24h'] <= nearest_buy['price']
            would_sell = vol_data['high_24h'] >= nearest_sell['price']
            
            if would_buy:
                print(f"✅ 24h low (${vol_data['low_24h']:.4f}) would have triggered BUY")
            else:
                drop_needed = (current_price - nearest_buy['price']) / current_price * 100
                print(f"⏳ Need {drop_needed:.1f}% drop to trigger BUY "
                      f"(${current_price - nearest_buy['price']:.4f})")
            
            if would_sell:
                print(f"✅ 24h high (${vol_data['high_24h']:.4f}) would have triggered SELL")
            else:
                rise_needed = (nearest_sell['price'] - current_price) / current_price * 100
                print(f"⏳ Need {rise_needed:.1f}% rise to trigger SELL "
                      f"(${nearest_sell['price'] - current_price:.4f})")
        
        # Show all grid levels for reference
        print(f"\n📋 ALL {asset['name']} GRID LEVELS:")
        print("BUY LEVELS (below current price):")
        for level in buy_levels[:5]:  # Show first 5 levels
            print(f"  Level {level['level']}: ${level['price']:.4f} "
                  f"({level['distance_percent']:.1f}% below)")
        
        print("SELL LEVELS (above current price):")
        for level in sell_levels[:5]:  # Show first 5 levels
            print(f"  Level {level['level']}: ${level['price']:.4f} "
                  f"({level['distance_percent']:.1f}% above)")
    
    print(f"\n⏰ Analysis completed at {datetime.now().strftime('%H:%M:%S')}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("• If volatility is low and no trades happening:")
    print("  - Consider reducing grid_size_percent (e.g., 1.5% instead of 2.5%)")
    print("  - Or be patient - grid trading profits from waiting for volatility")
    print("• If price moved significantly since bot start:")
    print("  - Consider restarting bot to reset grids around current price")
    print("• Grid trading works best in ranging/sideways markets")

def check_recent_trades():
    """Check if there have been any recent significant price movements"""
    print(f"\n🕐 RECENT MOVEMENT CHECK (last 3 hours)")
    print("-" * 40)
    
    load_dotenv()
    binance = BinanceManager()
    
    for symbol in ["ADAUSDT", "AVAXUSDT"]:
        try:
            klines = binance.get_klines(symbol, "5m", limit=36)  # 3 hours of 5min candles
            if not klines:
                continue
                
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float) 
            df['low'] = df['low'].astype(float)
            
            current_price = df['close'].iloc[-1]
            high_3h = df['high'].max()
            low_3h = df['low'].min()
            range_3h = (high_3h - low_3h) / current_price * 100
            
            print(f"{symbol}: ${low_3h:.4f} - ${high_3h:.4f} (±{range_3h:.1f}%)")
            
            if range_3h < 1.0:
                print(f"  💤 Very low movement - {symbol} is consolidating")
            elif range_3h > 3.0:
                print(f"  ⚡ High movement - {symbol} had good volatility")
            else:
                print(f"  📊 Moderate movement in {symbol}")
                
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    try:
        diagnose_grid_trading()
        check_recent_trades()
        
        print(f"\n🔄 Run this script again anytime to check current status:")
        print(f"python {__file__}")
        
    except KeyboardInterrupt:
        print("\n👋 Diagnostic interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
