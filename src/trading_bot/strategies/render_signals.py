import logging
import pandas as pd
from typing import Dict, Optional

# Import indicators - use absolute imports that work both ways
try:
    from ..utils.indicators import rsi, bollinger_bands, sma, ema, volume_spike
except ImportError:
    # Fallback for when running directly
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.indicators import rsi, bollinger_bands, sma, ema, volume_spike

class RenderSignalTrader:
    def __init__(self, rebalance_threshold: float = 0.8):
        """
        RENDER Signal Trading Strategy
        
        Args:
            rebalance_threshold: Signal strength threshold for portfolio rebalancing (0.8 = 80%)
        """
        self.symbol = "RENDERUSDT"
        self.rebalance_threshold = rebalance_threshold
        self.logger = logging.getLogger(f"{__name__}.RENDER")
        
    def analyze_render_signals(self, price_data: pd.DataFrame) -> Dict:
        """
        Analyze RENDER for trading signals
        
        Args:
            price_data: DataFrame with columns [timestamp, open, high, low, close, volume]
        
        Returns:
            Dict with signal information
        """
        if len(price_data) < 50:  # Need enough data for indicators
            return {"action": "hold", "strength": 0.0, "reason": "Insufficient data"}
        
        # Calculate technical indicators
        df = price_data.copy()
        
        # RSI
        df['rsi'] = rsi(df['close'], window=14)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = bollinger_bands(df['close'], window=20, num_std=2)
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        # Moving averages
        df['sma_20'] = sma(df['close'], window=20)
        df['ema_12'] = ema(df['close'], window=12)
        df['ema_26'] = ema(df['close'], window=26)
        
        # Volume analysis
        df['volume_spike'] = volume_spike(df['volume'], window=20, threshold=2.0)
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # Price position relative to Bollinger Bands
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Trend analysis
        df['trend_up'] = df['ema_12'] > df['ema_26']
        df['price_above_sma'] = df['close'] > df['sma_20']
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        return self._generate_signal(latest, prev, df)
    
    def _generate_signal(self, latest: pd.Series, prev: pd.Series, df: pd.DataFrame) -> Dict:
        """Generate trading signal based on technical analysis"""
        
        signals = []
        signal_strength = 0.0
        
        # Strong Buy Conditions
        buy_score = 0
        buy_reasons = []
        
        # RSI oversold
        if latest['rsi'] < 30:
            buy_score += 25
            buy_reasons.append("RSI oversold (<30)")
        elif latest['rsi'] < 40:
            buy_score += 15
            buy_reasons.append("RSI low (<40)")
        
        # Price below lower Bollinger Band
        if latest['close'] < latest['bb_lower']:
            buy_score += 20
            buy_reasons.append("Price below BB lower band")
        elif latest['bb_position'] < 0.2:
            buy_score += 10
            buy_reasons.append("Price in lower BB range")
        
        # Volume spike
        if latest['volume_spike']:
            buy_score += 15
            buy_reasons.append("Volume spike detected")
        
        # Trend conditions
        if latest['trend_up']:
            buy_score += 10
            buy_reasons.append("EMA trend bullish")
        
        # Price bouncing from support
        if latest['close'] > prev['close'] and prev['close'] <= latest['bb_lower']:
            buy_score += 15
            buy_reasons.append("Bounce from BB support")
        
        # Strong Sell Conditions
        sell_score = 0
        sell_reasons = []
        
        # RSI overbought
        if latest['rsi'] > 70:
            sell_score += 25
            sell_reasons.append("RSI overbought (>70)")
        elif latest['rsi'] > 60:
            sell_score += 15
            sell_reasons.append("RSI high (>60)")
        
        # Price above upper Bollinger Band
        if latest['close'] > latest['bb_upper']:
            sell_score += 20
            sell_reasons.append("Price above BB upper band")
        elif latest['bb_position'] > 0.8:
            sell_score += 10
            sell_reasons.append("Price in upper BB range")
        
        # Trend reversal
        if not latest['trend_up'] and prev['trend_up']:
            sell_score += 15
            sell_reasons.append("EMA trend turned bearish")
        
        # Price rejection from resistance
        if latest['close'] < prev['close'] and prev['close'] >= latest['bb_upper']:
            sell_score += 15
            sell_reasons.append("Rejection from BB resistance")
        
        # Determine final signal
        if buy_score >= 50:  # Strong buy threshold
            action = "strong_buy"
            signal_strength = min(buy_score / 100, 1.0)
            reasons = buy_reasons
        elif sell_score >= 50:  # Strong sell threshold
            action = "strong_sell"
            signal_strength = min(sell_score / 100, 1.0)
            reasons = sell_reasons
        elif buy_score >= 30:  # Moderate buy
            action = "buy"
            signal_strength = min(buy_score / 100, 0.7)
            reasons = buy_reasons
        elif sell_score >= 30:  # Moderate sell
            action = "sell"
            signal_strength = min(sell_score / 100, 0.7)
            reasons = sell_reasons
        else:
            action = "hold"
            signal_strength = 0.0
            reasons = ["No clear signal"]
        
        return {
            "action": action,
            "strength": signal_strength,
            "reasons": reasons,
            "price": latest['close'],
            "rsi": latest['rsi'],
            "bb_position": latest['bb_position'],
            "volume_spike": latest['volume_spike'],
            "trend_up": latest['trend_up'],
            "buy_score": buy_score,
            "sell_score": sell_score
        }
    
    def should_rebalance_portfolio(self, signal: Dict) -> bool:
        """Determine if portfolio should be rebalanced based on RENDER signal"""
        return signal["strength"] >= self.rebalance_threshold
    
    def calculate_rebalance_allocation(self, signal: Dict, current_render_allocation: float) -> Dict:
        """
        Calculate new portfolio allocation based on RENDER signal
        
        Args:
            signal: RENDER signal dictionary
            current_render_allocation: Current RENDER allocation (0.0 to 1.0)
        
        Returns:
            Dict with suggested allocations
        """
        if not self.should_rebalance_portfolio(signal):
            return {"rebalance": False, "reason": "Signal not strong enough"}
        
        action = signal["action"]
        strength = signal["strength"]
        
        if action in ["strong_buy", "buy"]:
            # Increase RENDER allocation
            target_render_allocation = min(current_render_allocation + (strength * 0.2), 0.4)  # Max 40%
            allocation_change = target_render_allocation - current_render_allocation
            
            return {
                "rebalance": True,
                "action": "increase_render",
                "target_render_allocation": target_render_allocation,
                "allocation_change": allocation_change,
                "reduce_from": ["SOL", "AVAX", "NEAR"],  # Reduce these to increase RENDER
                "strength": strength,
                "reason": f"Strong RENDER {action} signal"
            }
            
        elif action in ["strong_sell", "sell"]:
            # Decrease RENDER allocation
            target_render_allocation = max(current_render_allocation - (strength * 0.15), 0.05)  # Min 5%
            allocation_change = current_render_allocation - target_render_allocation
            
            return {
                "rebalance": True,
                "action": "decrease_render",
                "target_render_allocation": target_render_allocation,
                "allocation_change": allocation_change,
                "allocate_to": ["SOL", "AVAX"],  # Allocate to grid trading assets
                "strength": strength,
                "reason": f"Strong RENDER {action} signal"
            }
        
        return {"rebalance": False, "reason": "Hold signal"}

def test_render_strategy():
    """Test RENDER strategy with sample data"""
    import numpy as np
    
    # Create sample price data
    dates = pd.date_range('2024-01-01', periods=100, freq='h')
    np.random.seed(42)
    
    # Generate realistic RENDER price data
    base_price = 7.5  # Starting price around $7.50
    returns = np.random.normal(0, 0.03, 100)  # Higher volatility for RENDER
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(max(prices[-1] * (1 + ret), 0.1))  # Prevent negative prices
    
    # Create OHLCV data
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.02))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.02))) for p in prices],
        'close': prices,
        'volume': np.random.randint(10000, 100000, 100)
    })
    
    # Test RENDER strategy
    render_strategy = RenderSignalTrader(rebalance_threshold=0.7)
    
    # Analyze signals
    signal = render_strategy.analyze_render_signals(df)
    print(f"RENDER Signal: {signal}")
    
    # Test rebalancing
    if render_strategy.should_rebalance_portfolio(signal):
        rebalance = render_strategy.calculate_rebalance_allocation(signal, 0.15)  # Current 15% allocation
        print(f"Rebalance recommendation: {rebalance}")
    else:
        print("No rebalancing recommended")
    
    print("✅ RENDER strategy test complete!")

if __name__ == "__main__":
    test_render_strategy()
