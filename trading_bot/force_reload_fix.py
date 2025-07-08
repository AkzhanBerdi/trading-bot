#!/usr/bin/env python3
"""
Force reload compound manager - nuclear option
"""

import os
import shutil
import sys
from pathlib import Path

def force_clear_all_cache():
    """Aggressively clear all Python cache"""
    print("🧹 Nuclear cache clearing...")
    
    # Remove all __pycache__ directories recursively
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            if d == '__pycache__':
                cache_path = Path(root) / d
                print(f"   🗑️  Removing {cache_path}")
                shutil.rmtree(cache_path, ignore_errors=True)
    
    # Remove all .pyc files
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.pyc'):
                pyc_path = Path(root) / f
                print(f"   🗑️  Removing {pyc_path}")
                pyc_path.unlink(missing_ok=True)
    
    print("✅ All cache cleared")

def verify_compound_manager_update():
    """Verify the compound manager file actually has the new code"""
    print("\n🔍 Verifying compound manager update...")
    
    compound_file = "utils/compound_manager.py"
    
    with open(compound_file, 'r') as f:
        content = f.read()
    
    # Check for specific debugging strings
    debug_indicators = [
        '🔍 Compound manager loading from:',
        '🔍 Absolute path:',
        '🔍 Database exists:',
        '🔍 Working directory:',
        '🔍 Found',
        '🔍 Calculated total profit:'
    ]
    
    found_indicators = []
    for indicator in debug_indicators:
        if indicator in content:
            found_indicators.append(indicator)
    
    print(f"   📊 Found {len(found_indicators)}/{len(debug_indicators)} debug indicators")
    
    if len(found_indicators) == len(debug_indicators):
        print("   ✅ Compound manager has all debugging code")
        return True
    else:
        print("   ❌ Compound manager missing debugging code")
        print("   🔧 Need to re-apply the fix")
        return False

def create_reload_test_script():
    """Create a script that forces module reload"""
    print("\n📝 Creating reload test script...")
    
    reload_script = '''#!/usr/bin/env python3
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
'''
    
    with open("force_reload_test.py", 'w') as f:
        f.write(reload_script)
    
    print("   ✅ Created force_reload_test.py")

def restart_python_environment():
    """Instructions to restart Python environment"""
    print(f"\n🔄 Python Environment Restart:")
    print(f"   1. Exit any running Python processes")
    print(f"   2. Close all terminals/IDEs with Python")
    print(f"   3. Open fresh terminal")
    print(f"   4. cd to trading_bot directory")
    print(f"   5. Run python main.py")

def main():
    """Force reload fix"""
    print("🔧 Force Reload Compound Manager Fix")
    print("=" * 45)
    
    force_clear_all_cache()
    
    if not verify_compound_manager_update():
        print("\n❌ Need to re-apply compound manager fix first!")
        return
    
    create_reload_test_script()
    restart_python_environment()
    
    print("\n" + "=" * 45)
    print("🎯 FORCE RELOAD COMPLETE!")
    
    print("\n📋 Next Steps:")
    print("1. python force_reload_test.py  # Test fresh reload")
    print("2. If that works, restart main.py in fresh terminal")
    print("3. Look for debugging output in logs")
    
    print("\n🔍 Expected debugging output:")
    print("   🔍 Compound manager loading from: data/trading_history.db")
    print("   🔍 Database exists: True")
    print("   🔍 Found 37 trades in database")
    print("   💰 Using compound order size: $108")

if __name__ == "__main__":
    main()
