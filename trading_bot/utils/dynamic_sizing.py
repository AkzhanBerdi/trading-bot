# Step 2: Dynamic Order Sizing Based on Volatility
# Add to your trading_bot/utils/dynamic_sizing.py (new file)
import time
from typing import Dict


class VolatilityOrderSizer:
    def __init__(self, binance_client):
        self.binance = binance_client
        self.volatility_cache = {}
        self.cache_duration = 300  # 5 minutes cache

    def get_dynamic_order_size(self, symbol: str, base_size: float) -> float:
        """Adjust order size based on recent volatility"""
        try:
            # Check cache first
            if self._is_cached_valid(symbol):
                multiplier = self.volatility_cache[symbol]["multiplier"]
            else:
                multiplier = self._calculate_volatility_multiplier(symbol)

            return base_size * multiplier

        except Exception as e:
            print(f"Volatility sizing failed for {symbol}: {e}")
            return base_size  # Fallback to base size

    def _calculate_volatility_multiplier(self, symbol: str) -> float:
        """Calculate multiplier based on 24h price change"""
        try:
            # Get 24h price change
            ticker = self.binance.client.get_24hr_ticker(symbol=symbol)
            price_change = abs(float(ticker["priceChangePercent"]))

            # Calculate multiplier
            if price_change > 8:  # High volatility
                multiplier = 1.5
                volatility_level = "HIGH"
            elif price_change < 2:  # Low volatility
                multiplier = 0.75
                volatility_level = "LOW"
            else:  # Normal volatility
                multiplier = 1.0
                volatility_level = "NORMAL"

            # Cache the result
            self.volatility_cache[symbol] = {
                "multiplier": multiplier,
                "volatility_level": volatility_level,
                "price_change": price_change,
                "timestamp": time.time(),
            }

            return multiplier

        except Exception:
            return 1.0  # Default multiplier

    def _is_cached_valid(self, symbol: str) -> bool:
        """Check if cached volatility data is still valid"""
        if symbol not in self.volatility_cache:
            return False

        cache_age = time.time() - self.volatility_cache[symbol]["timestamp"]
        return cache_age < self.cache_duration

    def get_volatility_status(self, symbol: str) -> Dict:
        """Get current volatility status for a symbol"""
        if symbol in self.volatility_cache:
            return self.volatility_cache[symbol]
        return {"volatility_level": "UNKNOWN", "multiplier": 1.0}
