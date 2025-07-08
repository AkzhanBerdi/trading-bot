#!/usr/bin/env python3
"""
Manually test compound manager loading
"""

import sys
import os
sys.path.append('.')

from utils.compound_manager import CompoundManager
from utils.database_logger import DatabaseLogger

def test_compound_loading():
    """Test compound manager loading manually"""
    print("🧪 Testing compound manager loading...")
    
    # Create compound manager exactly like main.py does
    db_logger = DatabaseLogger()
    compound_manager = CompoundManager(db_logger, base_order_size=100.0)
    
    # Test loading
    compound_manager.load_state_from_database("data/trading_history.db")
    
    # Show results
    status = compound_manager.get_compound_status()
    print(f"\n📊 Compound Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\n💰 Current order size: ${compound_manager.get_current_order_size():.2f}")

if __name__ == "__main__":
    test_compound_loading()
