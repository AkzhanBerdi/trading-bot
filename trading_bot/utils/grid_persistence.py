# utils/grid_persistence.py
import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

class GridStatePersistence:
    """Advanced grid state persistence with validation and recovery"""
    
    def __init__(self, symbol: str, data_dir: str = "data/grid_states"):
        self.symbol = symbol
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / f"{symbol}_grid_state.json"
        self.backup_file = self.data_dir / f"{symbol}_grid_state_backup.json"
        self.logger = logging.getLogger(__name__)
    
    def save_grid_state(self, grid_trader, session_id: str = None) -> bool:
        """Save grid state with backup and validation"""
        try:
            # Create backup of existing state
            if self.state_file.exists():
                shutil.copy2(self.state_file, self.backup_file)
            
            state = {
                'symbol': grid_trader.symbol,
                'session_id': session_id or f"session_{int(time.time())}",
                'saved_at': datetime.now().isoformat(),
                'grid_config': {
                    'grid_size_percent': grid_trader.grid_size * 100,
                    'num_grids': grid_trader.num_grids,
                    'base_order_size': grid_trader.base_order_size,
                    'center_price': self._estimate_center_price(grid_trader)
                },
                'buy_levels': grid_trader.buy_levels,
                'sell_levels': grid_trader.sell_levels,
                'filled_orders': self._serialize_filled_orders(grid_trader.filled_orders),
                'active_orders': getattr(grid_trader, 'active_orders', {}),
                'statistics': {
                    'total_filled': len(grid_trader.filled_orders),
                    'buy_filled': len([o for o in grid_trader.filled_orders if o.get('side') == 'BUY']),
                    'sell_filled': len([o for o in grid_trader.filled_orders if o.get('side') == 'SELL']),
                    'total_volume': sum(o.get('total_value', 0) for o in grid_trader.filled_orders)
                },
                'version': '2.0'  # State format version
            }
            
            # Validate state before saving
            if self._validate_state(state):
                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                self.logger.info(
                    f"✅ Grid state saved: {state['statistics']['total_filled']} filled orders, "
                    f"${state['statistics']['total_volume']:.2f} volume"
                )
                return True
            else:
                self.logger.error("❌ State validation failed, not saving")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to save grid state: {e}")
            return False
    
    def load_grid_state(self, current_price: float, max_age_hours: int = 168) -> Optional[Dict]:
        """Load and validate grid state"""
        try:
            if not self.state_file.exists():
                self.logger.info(f"📂 No saved state found for {self.symbol}")
                return None
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Validate state age
            saved_at = datetime.fromisoformat(state['saved_at'])
            age_hours = (datetime.now() - saved_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                self.logger.warning(f"⚠️ Saved state is {age_hours:.1f} hours old (max: {max_age_hours})")
                return None
            
            # Validate price movement
            center_price = state['grid_config'].get('center_price')
            if center_price:
                price_change = abs(current_price - center_price) / center_price
                if price_change > 0.15:  # 15% threshold
                    self.logger.warning(
                        f"⚠️ Price moved {price_change:.1%} since state save "
                        f"(${center_price:.4f} → ${current_price:.4f})"
                    )
                    return None
            
            # Validate state integrity
            if not self._validate_state(state):
                self.logger.error("❌ State validation failed")
                return None
            
            # Deserialize filled orders
            state['filled_orders'] = self._deserialize_filled_orders(state['filled_orders'])
            
            self.logger.info(
                f"✅ Grid state loaded: {state['statistics']['total_filled']} filled orders, "
                f"age: {age_hours:.1f}h"
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load grid state: {e}")
            
            # Try backup file
            if self.backup_file.exists():
                self.logger.info("🔄 Trying backup state file...")
                try:
                    with open(self.backup_file, 'r') as f:
                        backup_state = json.load(f)
                    return backup_state
                except:
                    pass
            
            return None
    
    def _serialize_filled_orders(self, filled_orders: List) -> List:
        """Convert filled orders to JSON-serializable format"""
        serialized = []
        for order in filled_orders:
            serialized_order = order.copy()
            
            # Convert timestamp to string if needed
            if 'timestamp' in serialized_order:
                if hasattr(serialized_order['timestamp'], 'isoformat'):
                    serialized_order['timestamp'] = serialized_order['timestamp'].isoformat()
                elif isinstance(serialized_order['timestamp'], (int, float)):
                    serialized_order['timestamp'] = datetime.fromtimestamp(
                        serialized_order['timestamp']
                    ).isoformat()
            
            # Calculate total_value if missing
            if 'total_value' not in serialized_order:
                qty = serialized_order.get('quantity', 0)
                price = serialized_order.get('price', 0)
                serialized_order['total_value'] = qty * price
            
            serialized.append(serialized_order)
        
        return serialized
    
    def _deserialize_filled_orders(self, filled_orders: List) -> List:
        """Convert filled orders back from JSON format"""
        deserialized = []
        for order in filled_orders:
            deserialized_order = order.copy()
            
            # Convert timestamp back to float
            if 'timestamp' in deserialized_order:
                if isinstance(deserialized_order['timestamp'], str):
                    try:
                        dt = datetime.fromisoformat(deserialized_order['timestamp'])
                        deserialized_order['timestamp'] = dt.timestamp()
                    except:
                        deserialized_order['timestamp'] = time.time()
            
            deserialized.append(deserialized_order)
        
        return deserialized
    
    def _validate_state(self, state: Dict) -> bool:
        """Validate state integrity"""
        required_fields = ['symbol', 'grid_config', 'buy_levels', 'sell_levels', 'filled_orders']
        
        for field in required_fields:
            if field not in state:
                self.logger.error(f"❌ Missing required field: {field}")
                return False
        
        # Validate grid config
        grid_config = state['grid_config']
        required_config = ['grid_size_percent', 'num_grids', 'base_order_size']
        for field in required_config:
            if field not in grid_config:
                self.logger.error(f"❌ Missing grid config field: {field}")
                return False
        
        return True
    
    def _estimate_center_price(self, grid_trader) -> Optional[float]:
        """Estimate center price from grid levels"""
        try:
            if grid_trader.buy_levels and grid_trader.sell_levels:
                highest_buy = max(level['price'] for level in grid_trader.buy_levels)
                lowest_sell = min(level['price'] for level in grid_trader.sell_levels)
                return (highest_buy + lowest_sell) / 2
        except:
            pass
        return None
    
    def clear_state(self) -> bool:
        """Clear saved state files"""
        try:
            files_removed = 0
            for file_path in [self.state_file, self.backup_file]:
                if file_path.exists():
                    file_path.unlink()
                    files_removed += 1
            
            if files_removed > 0:
                self.logger.info(f"🗑️ Cleared {files_removed} state files for {self.symbol}")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to clear state: {e}")
            return False
