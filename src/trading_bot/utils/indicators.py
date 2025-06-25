# src/trading_bot/utils/indicators.py
import pandas as pd
import numpy as np

def sma(data, window):
    """Simple Moving Average"""
    return data.rolling(window=window).mean()

def ema(data, window):
    """Exponential Moving Average"""
    return data.ewm(span=window, adjust=False).mean()

def rsi(data, window=14):
    """Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def bollinger_bands(data, window=20, num_std=2):
    """Bollinger Bands - returns upper, middle, lower"""
    rolling_mean = data.rolling(window=window).mean()
    rolling_std = data.rolling(window=window).std()
    upper = rolling_mean + (rolling_std * num_std)
    lower = rolling_mean - (rolling_std * num_std)
    return upper, rolling_mean, lower

def macd(data, fast=12, slow=26, signal=9):
    """MACD - returns macd_line, signal_line, histogram"""
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def volume_spike(volume, window=20, threshold=2.0):
    """Detect volume spikes"""
    volume_ma = volume.rolling(window=window).mean()
    return volume > (volume_ma * threshold)

# Test function
def test_indicators():
    """Test indicators with sample data"""
    # Sample price data
    prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 
                       111, 110, 112, 114, 113, 115, 117, 116, 118, 120])
    volumes = pd.Series([1000, 1200, 800, 1500, 2000, 1100, 1300, 1800, 
                        900, 1600, 2200, 1000, 1400, 1700, 1200, 1900, 
                        2100, 1300, 1500, 2500])
    
    print("Testing indicators...")
    print(f"RSI: {rsi(prices, 10).iloc[-1]:.2f}")
    
    bb_upper, bb_mid, bb_lower = bollinger_bands(prices, 10)
    print(f"Bollinger Bands: Upper={bb_upper.iloc[-1]:.2f}, Lower={bb_lower.iloc[-1]:.2f}")
    
    macd_line, signal_line, hist = macd(prices)
    print(f"MACD: {macd_line.iloc[-1]:.3f}")
    
    vol_spike = volume_spike(volumes, 10)
    print(f"Volume spikes: {vol_spike.sum()}")
    
    print("✅ All indicators working!")

if __name__ == "__main__":
    test_indicators()
