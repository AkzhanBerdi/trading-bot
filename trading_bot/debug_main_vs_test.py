#!/usr/bin/env python3
"""
Debug why main.py shows $0.00 but test script shows $26.57
"""

import os
import sys
from pathlib import Path

def check_main_py_call():
    """Check exactly how main.py calls compound manager"""
    print("🔍 Analyzing main.py compound manager usage...")
    
    main_file = "main.py"
    
    if not Path(main_file).exists():
        print(f"❌ {main_file} not found")
        return
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find compound manager initialization
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'compound_manager' in line.lower():
            print(f"   Line {i+1}: {line.strip()}")
        if 'load_state_from_database' in line:
            print(f"   Line {i+1}: {line.strip()}")

def check_compound_manager_file():
    """Check if compound manager file was actually updated"""
    print("\n🔍 Checking compound manager file...")
    
    compound_file = "utils/compound_manager.py"
    
    if not Path(compound_file).exists():
        print(f"❌ {compound_file} not found")
        return
    
    with open(compound_file, 'r') as f:
        content = f.read()
    
    # Check if debugging was added
    if '🔍 Compound manager loading from:' in content:
        print("   ✅ Debugging code found in compound manager")
    else:
        print("   ❌ Debugging code NOT found in compound manager")
        print("   📝 The file may not have been updated properly")
    
    # Check the method signature
    if 'def load_state_from_database(self, db_path: str = "data/trading_history.db"):' in content:
        print("   ✅ load_state_from_database method found")
    else:
        print("   ❌ load_state_from_database method not found or different signature")

def test_import_and_run():
    """Test importing and running compound manager like main.py does"""
    print("\n🧪 Testing compound manager import like main.py...")
    
    try:
        # Add current directory to path like main.py would
        sys.path.insert(0, '.')
        
        from utils.database_logger import DatabaseLogger
        from utils.compound_manager import CompoundManager
        
        print("   ✅ Successfully imported modules")
        
        # Create exactly like main.py does
        db_logger = DatabaseLogger()
        compound_manager = CompoundManager(db_logger, base_order_size=100.0)
        
        print("   ✅ Created compound manager")
        
        # Call load_state_from_database without explicit path (default)
        print("   🔄 Calling load_state_from_database() with default path...")
        compound_manager.load_state_from_database()
        
        # Check results
        status = compound_manager.get_compound_status()
        print(f"   💰 Result: ${status['current_order_size']:.2f} order size")
        print(f"   📊 Profit: ${status['accumulated_profit']:.2f}")
        
        if status['accumulated_profit'] > 0:
            print("   ✅ Working when called like main.py!")
        else:
            print("   ❌ Still $0.00 when called like main.py")
            
        # Now try with explicit path
        print("   🔄 Calling load_state_from_database('data/trading_history.db')...")
        compound_manager.load_state_from_database("data/trading_history.db")
        
        status2 = compound_manager.get_compound_status()
        print(f"   💰 Result: ${status2['current_order_size']:.2f} order size")
        print(f"   📊 Profit: ${status2['accumulated_profit']:.2f}")
        
    except Exception as e:
        print(f"   ❌ Import/run test failed: {e}")

def check_working_directory():
    """Check working directory when running from different locations"""
    print(f"\n📁 Working directory analysis:")
    print(f"   Current directory: {Path.cwd()}")
    print(f"   Script location: {Path(__file__).parent}")
    
    # Check database paths
    possible_db_paths = [
        "data/trading_history.db",
        "trading_bot/data/trading_history.db",
        "./data/trading_history.db"
    ]
    
    for path in possible_db_paths:
        exists = Path(path).exists()
        if exists:
            abs_path = Path(path).resolve()
            print(f"   ✅ {path} → {abs_path}")
        else:
            print(f"   ❌ {path} (not found)")

def check_python_cache():
    """Check if Python is using cached bytecode"""
    print(f"\n🔄 Checking Python cache...")
    
    cache_dirs = [
        "utils/__pycache__",
        "__pycache__"
    ]
    
    for cache_dir in cache_dirs:
        if Path(cache_dir).exists():
            files = list(Path(cache_dir).glob("*.pyc"))
            print(f"   📁 {cache_dir}: {len(files)} cached files")
            
            # Check compound manager cache age
            compound_cache = Path(cache_dir) / "compound_manager.cpython-310.pyc"
            if compound_cache.exists():
                mtime = compound_cache.stat().st_mtime
                import time
                age = time.time() - mtime
                print(f"      compound_manager.pyc is {age:.0f} seconds old")
                
                if age > 300:  # 5 minutes
                    print(f"      ⚠️  Cache may be stale")

def suggest_fixes():
    """Suggest fixes based on findings"""
    print(f"\n💡 SUGGESTED FIXES:")
    print(f"1. Clear Python cache:")
    print(f"   rm -rf utils/__pycache__ __pycache__")
    print(f"2. Restart Python completely")
    print(f"3. Check if main.py has the correct import path")
    print(f"4. Verify the compound manager file was actually updated")

def main():
    """Main debugging process"""
    print("🔍 Debug Main.py vs Test Script Discrepancy")
    print("=" * 55)
    
    check_main_py_call()
    check_compound_manager_file()
    check_working_directory()
    check_python_cache()
    test_import_and_run()
    suggest_fixes()
    
    print("\n" + "=" * 55)
    print("🎯 DEBUGGING COMPLETE!")

if __name__ == "__main__":
    main()
