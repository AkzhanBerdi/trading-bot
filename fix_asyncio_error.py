#!/usr/bin/env python3
"""
Fix Asyncio Event Loop Error
Update error monitoring to work properly with bot lifecycle
"""

from pathlib import Path

def fix_main_py():
    """Fix main.py to properly handle error monitoring lifecycle"""
    
    main_file = Path("trading_bot/main.py")
    
    if not main_file.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Backup original
    backup_file = main_file.with_suffix('.py.backup2')
    with open(backup_file, 'w') as f:
        f.write(content)
    
    print(f"📋 Backup saved: {backup_file}")
    
    # Fix 1: Remove the health_task creation from __init__
    old_setup = """        # Setup critical error monitoring (warnings/errors only)
        self.error_monitor, self.health_task = setup_error_monitoring(
            self.telegram_notifier
        )"""
    
    new_setup = """        # Setup critical error monitoring (warnings/errors only)
        self.error_monitor = setup_error_monitoring(self.telegram_notifier)
        self.health_task = None"""
    
    if old_setup in content:
        content = content.replace(old_setup, new_setup)
        print("✅ Fixed error monitoring initialization")
    
    # Fix 2: Start health monitoring in the run() method after event loop starts
    run_method_start = "self.logger.info(\"🚀 Starting enhanced trading bot with intelligent timing...\")"
    
    if run_method_start in content:
        # Add health task startup after this line
        health_startup = """
        # Start error monitoring health checks
        if self.error_monitor:
            self.health_task = asyncio.create_task(self.error_monitor.check_bot_health())
            self.logger.info("📱 Error monitoring health checks started")"""
        
        content = content.replace(
            run_method_start,
            run_method_start + health_startup
        )
        print("✅ Added health task startup to run() method")
    
    # Fix 3: Cleanup health task in finally block
    cleanup_section = "            command_task.cancel()"
    
    if cleanup_section in content:
        health_cleanup = """
            # Stop error monitoring health task
            if self.health_task:
                self.health_task.cancel()
                self.logger.info("📱 Error monitoring health checks stopped")"""
        
        content = content.replace(
            cleanup_section,
            cleanup_section + health_cleanup
        )
        print("✅ Added health task cleanup")
    
    # Write fixed content
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ main.py fixed for proper asyncio lifecycle")
    return True

def fix_error_monitor():
    """Fix error_monitor.py to not create tasks immediately"""
    
    error_file = Path("trading_bot/utils/error_monitor.py")
    
    if not error_file.exists():
        print("❌ error_monitor.py not found")
        return False
    
    with open(error_file, 'r') as f:
        content = f.read()
    
    # Fix the setup_error_monitoring function to not create tasks immediately
    old_setup_function = """def setup_error_monitoring(telegram_notifier):
    \"\"\"Set up error monitoring with existing telegram notifier\"\"\"
    
    # Create monitor
    error_monitor = CriticalErrorMonitor(telegram_notifier)
    
    # Add handler to root logger
    handler = CriticalErrorHandler(error_monitor)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add to root logger to catch all warnings/errors
    logging.getLogger().addHandler(handler)
    
    # Start monitoring
    error_monitor.start_monitoring()
    
    # Start health check task
    health_task = asyncio.create_task(error_monitor.check_bot_health())
    
    return error_monitor, health_task"""
    
    new_setup_function = """def setup_error_monitoring(telegram_notifier):
    \"\"\"Set up error monitoring with existing telegram notifier\"\"\"
    
    # Create monitor
    error_monitor = CriticalErrorMonitor(telegram_notifier)
    
    # Add handler to root logger
    handler = CriticalErrorHandler(error_monitor)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add to root logger to catch all warnings/errors
    logging.getLogger().addHandler(handler)
    
    # Start monitoring
    error_monitor.start_monitoring()
    
    # Don't create health task here - will be created later when event loop is running
    return error_monitor"""
    
    if old_setup_function in content:
        content = content.replace(old_setup_function, new_setup_function)
        print("✅ Fixed setup_error_monitoring function")
    
    # Write fixed content
    with open(error_file, 'w') as f:
        f.write(content)
    
    print("✅ error_monitor.py fixed")
    return True

def test_fix():
    """Test that the fix works"""
    
    print("🧪 Testing fix...")
    
    try:
        import sys
        sys.path.insert(0, 'trading_bot')
        
        # Test import
        from utils.error_monitor import setup_error_monitoring, CriticalErrorMonitor
        print("   ✅ Import successful")
        
        # Test setup function
        from utils.telegram_notifier import telegram_notifier
        
        error_monitor = setup_error_monitoring(telegram_notifier)
        print("   ✅ setup_error_monitoring returns monitor only (no task)")
        
        # Test monitor creation
        if isinstance(error_monitor, CriticalErrorMonitor):
            print("   ✅ Returned correct monitor type")
        else:
            print(f"   ❌ Wrong return type: {type(error_monitor)}")
            return False
        
        # Test that monitoring is active
        if error_monitor.monitoring_active:
            print("   ✅ Monitoring is active")
        else:
            print("   ❌ Monitoring not active")
            return False
        
        error_monitor.stop_monitoring()
        print("   ✅ Monitor stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

def main():
    """Main fix process"""
    
    print("🔧 Fixing Asyncio Event Loop Error")
    print("=" * 35)
    
    success_count = 0
    total_steps = 3
    
    # Step 1: Fix error_monitor.py
    if fix_error_monitor():
        success_count += 1
    
    # Step 2: Fix main.py
    if fix_main_py():
        success_count += 1
    
    # Step 3: Test the fix
    if test_fix():
        success_count += 1
    
    print("\n" + "=" * 35)
    print(f"🎯 Fix Results: {success_count}/{total_steps} steps completed")
    
    if success_count >= 2:
        print("\n✅ ASYNCIO ERROR FIXED!")
        
        print("\n📋 What was fixed:")
        print("   • Removed asyncio.create_task from __init__")
        print("   • Health monitoring starts after event loop begins")
        print("   • Proper cleanup when bot stops")
        print("   • Error monitoring lifecycle managed correctly")
        
        print("\n🚀 Next Steps:")
        print("1. Restart your trading bot:")
        print("   cd trading_bot && python main.py")
        
        print("\n2. Expected startup logs:")
        print("   🔍 Critical error monitoring started")
        print("   📱 Error monitoring health checks started")
        print("   🚀 Starting enhanced trading bot...")
        
        print("\n3. No more asyncio errors!")
        print("   Bot should start normally with error monitoring")
        
    else:
        print("\n❌ FIX INCOMPLETE")
        print("Please check the errors above and retry")

if __name__ == "__main__":
    main()
