#!/usr/bin/env python3
"""
Force reload compound manager module
"""

import sys
import importlib
from pathlib import Path

def force_reload_test():
    """Force reload and test compound manager"""
    print("🔄 Force reloading compound manager...")
    
    # Remove from sys.modules if already imported
    modules_to_remove = []
    for module_name in sys.modules:
        if 'compound_manager' in module_name:
            modules_to_remove.append(module_name)
    
    for module_name in modules_to_remove:
        print(f"   🗑️  Removing {module_name} from sys.modules")
        del sys.modules[module_name]
    
    # Force fresh import
    from utils.database_logger import DatabaseLogger
    from utils.compound_manager import CompoundManager
    
    print("   ✅ Fresh import complete")
    
    # Test it
    print("   🧪 Testing fresh compound manager...")
    db_logger = DatabaseLogger()
    compound_manager = CompoundManager(db_logger, base_order_size=100.0)
    
    # This should now show debugging output
    compound_manager.load_state_from_database("data/trading_history.db")
    
    status = compound_manager.get_compound_status()
    print(f"   💰 Result: ${status['current_order_size']:.2f}")
    print(f"   📊 Profit: ${status['accumulated_profit']:.2f}")
    
    if status['accumulated_profit'] > 0:
        print("   ✅ SUCCESS: Fresh reload is working!")
        return True
    else:
        print("   ❌ FAILED: Still showing $0.00 after fresh reload")
        return False

if __name__ == "__main__":
    force_reload_test()
