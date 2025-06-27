# src/trading_bot/strategies/grid_trading.py
import logging
import pandas as pd
from typing import Dict, List, Optional

class GridTrader:
    def __init__(self, symbol: str, grid_size_percent: float = 2.0, num_grids: int = 10, 
                 base_order_size: float = 50.0):
        """
        Grid Trading Strategy
        
        Args:
            symbol: Trading pair (e.g., 'SOLUSDT')
            grid_size_percent: Percentage between grid levels (default 2%)
            num_grids: Number of grid levels (default 10)
            base_order_size: Base order size in USDT (default $50)
        """
        self.symbol = symbol
        self.grid_size = grid_size_percent / 100  # Convert to decimal
        self.num_grids = num_grids
        self.base_order_size = base_order_size
        
        self.buy_levels = []
        self.sell_levels = []
        self.active_orders = {}
        self.filled_orders = []
        
        self.logger = logging.getLogger(f"{__name__}.{symbol}")
        
    def setup_grid(self, current_price: float) -> Dict:
        """Setup grid levels around current price"""
        self.buy_levels = []
        self.sell_levels = []
        
        # Create buy levels below current price
        for i in range(1, self.num_grids + 1):
            price = current_price * (1 - self.grid_size * i)
            quantity = round(self.base_order_size / price, 6)  # Round to 6 decimal places for SOL  # Calculate quantity based on USDT amount
            self.buy_levels.append({
                'price': price,
                'quantity': quantity,
                'level': i,
                'side': 'BUY'
            })
        
        # Create sell levels above current price
        for i in range(1, self.num_grids + 1):
            price = current_price * (1 + self.grid_size * i)
            quantity = round(self.base_order_size / current_price, 6)  # Round to 6 decimal places  # Use current price for quantity calculation
            self.sell_levels.append({
                'price': price,
                'quantity': quantity,
                'level': i,
                'side': 'SELL'
            })
        
        grid_info = {
            'symbol': self.symbol,
            'current_price': current_price,
            'buy_levels': len(self.buy_levels),
            'sell_levels': len(self.sell_levels),
            'grid_range': f"{self.buy_levels[-1]['price']:.4f} - {self.sell_levels[-1]['price']:.4f}",
            'grid_size_percent': self.grid_size * 100
        }
        
        self.logger.info(f"Grid setup complete: {grid_info}")
        return grid_info
    
    def check_signals(self, current_price: float) -> List[Dict]:
        """Check for grid trading signals"""
        signals = []
        
        # Check buy levels
        for level in self.buy_levels:
            if current_price <= level['price'] and level['level'] not in [o['level'] for o in self.filled_orders if o['side'] == 'BUY']:
                signals.append({
                    'action': 'BUY',
                    'price': level['price'],
                    'quantity': level['quantity'],
                    'level': level['level'],
                    'signal_strength': 0.7,
                    'reason': f"Price hit buy grid level {level['level']}"
                })
        
        # Check sell levels
        for level in self.sell_levels:
            if current_price >= level['price'] and level['level'] not in [o['level'] for o in self.filled_orders if o['side'] == 'SELL']:
                signals.append({
                    'action': 'SELL',
                    'price': level['price'],
                    'quantity': level['quantity'],
                    'level': level['level'],
                    'signal_strength': 0.7,
                    'reason': f"Price hit sell grid level {level['level']}"
                })
        
        return signals
    
    def execute_grid_order(self, signal: Dict, binance_manager) -> bool:
        """Execute a grid trading order"""
        try:
            symbol = self.symbol
            action = signal['action']
            quantity = signal['quantity']
            
            if action == 'BUY':
                order = binance_manager.place_market_buy(symbol, quantity)
            else:  # SELL
                order = binance_manager.place_market_sell(symbol, quantity)
            
            if order and order.get('status') == 'FILLED':
                # Record filled order
                self.filled_orders.append({
                    'symbol': symbol,
                    'side': action,
                    'quantity': quantity,
                    'price': signal['price'],
                    'level': signal['level'],
                    'timestamp': pd.Timestamp.now()
                })
                
                self.logger.info(f"Grid order executed: {action} {quantity} {symbol} at level {signal['level']}")
                return True
            else:
                self.logger.error(f"Grid order failed: {order}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing grid order: {e}")
            return False
    
    def get_grid_status(self) -> Dict:
        """Get current grid trading status with error handling"""
        try:
            buy_orders_filled = len([o for o in self.filled_orders if o.get('side') == 'BUY'])
            sell_orders_filled = len([o for o in self.filled_orders if o.get('side') == 'SELL'])
            
            total_volume = 0
            for order in self.filled_orders:
                try:
                    if 'total_value' in order:
                        total_volume += order['total_value']
                    else:
                        # Calculate from quantity and price
                        qty = order.get('quantity', 0)
                        price = order.get('price', 0)
                        total_volume += qty * price
                except:
                    continue
            
            return {
                'symbol': self.symbol,
                'buy_orders_filled': buy_orders_filled,
                'sell_orders_filled': sell_orders_filled,
                'total_orders': len(self.filled_orders),
                'total_volume_usdt': total_volume,
                'grid_levels': {
                    'buy_levels': len(getattr(self, 'buy_levels', [])),
                    'sell_levels': len(getattr(self, 'sell_levels', []))
                }
            }
        except Exception as e:
            # Return safe defaults on error
            return {
                'symbol': getattr(self, 'symbol', 'UNKNOWN'),
                'buy_orders_filled': 0,
                'sell_orders_filled': 0,
                'total_orders': 0,
                'total_volume_usdt': 0,
                'grid_levels': {
                    'buy_levels': 0,
                    'sell_levels': 0
                }
            }
    
    def calculate_grid_profit(self) -> float:
        """Calculate profit from completed grid cycles"""
        profit = 0.0
        
        # Simple profit calculation: each buy-sell cycle
        buy_orders = [o for o in self.filled_orders if o['side'] == 'BUY']
        sell_orders = [o for o in self.filled_orders if o['side'] == 'SELL']
        
        # Match buy and sell orders for profit calculation
        for i in range(min(len(buy_orders), len(sell_orders))):
            buy_price = buy_orders[i]['price']
            sell_price = sell_orders[i]['price']
            quantity = min(buy_orders[i]['quantity'], sell_orders[i]['quantity'])
            
            cycle_profit = (sell_price - buy_price) * quantity
            profit += cycle_profit
        
        return profit

def test_grid_strategy():
    """Test grid strategy with sample data"""
    # Create grid trader
    grid = GridTrader("SOLUSDT", grid_size_percent=2.0, num_grids=5, base_order_size=50)
    
    # Setup grid
    current_price = 100.0
    grid_info = grid.setup_grid(current_price)
    print(f"Grid setup: {grid_info}")
    
    # Test signals at different prices
    test_prices = [98.0, 102.0, 96.0, 104.0, 100.0]
    
    for price in test_prices:
        signals = grid.check_signals(price)
        if signals:
            print(f"Price ${price}: {len(signals)} signals")
            for signal in signals:
                print(f"  - {signal['action']} at level {signal['level']}: {signal['reason']}")
        else:
            print(f"Price ${price}: No signals")
    
    # Test status
    status = grid.get_grid_status()
    print(f"Grid status: {status}")
    
    print("✅ Grid strategy test complete!")

if __name__ == "__main__":
    test_grid_strategy()
