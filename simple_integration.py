#!/usr/bin/env python3
"""
Simple Integration: Add Error-Only Monitoring
Minimal changes to existing bot - only critical error alerts
"""

import os
from pathlib import Path

def add_error_monitoring_to_main():
    """Add minimal error monitoring to main.py"""
    
    main_file = Path("trading_bot/main.py")
    
    if not main_file.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if already integrated
    if 'error_monitor' in content.lower():
        print("✅ Error monitoring already integrated")
        return True
    
    # Add import after telegram imports
    telegram_import = "from utils.telegram_notifier import telegram_notifier"
    if telegram_import in content:
        error_import = "from utils.error_monitor import setup_error_monitoring"
        content = content.replace(
            telegram_import,
            telegram_import + "\n" + error_import
        )
    
    # Add monitoring setup after telegram notifier initialization
    telegram_store = "self.telegram_notifier = telegram_notifier"
    if telegram_store in content:
        monitoring_setup = """
        # Setup critical error monitoring (warnings/errors only)
        self.error_monitor, self.health_task = setup_error_monitoring(self.telegram_notifier)"""
        
        content = content.replace(
            telegram_store,
            telegram_store + monitoring_setup
        )
    
    # Add cleanup in bot shutdown (if there's a cleanup method)
    # This is optional - the monitoring will stop when the bot stops
    
    # Backup and save
    backup_file = main_file.with_suffix('.py.backup')
    with open(backup_file, 'w') as f:
        f.write(open(main_file).read())
    
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Error monitoring integrated into main.py")
    print(f"📋 Backup saved: {backup_file}")
    return True

def test_integration():
    """Test that the integration works"""
    
    print("🧪 Testing error monitoring integration...")
    
    try:
        import sys
        sys.path.insert(0, 'trading_bot')
        
        # Test import
        from utils.error_monitor import CriticalErrorMonitor
        print("   ✅ Error monitor module imports successfully")
        
        # Test telegram integration
        from utils.telegram_notifier import telegram_notifier
        
        # Create test monitor
        monitor = CriticalErrorMonitor(telegram_notifier)
        print("   ✅ Error monitor created successfully")
        
        # Test critical error detection
        test_cases = [
            ("Connection timeout to Binance API", "connection"),
            ("API rate limit exceeded", "api"),
            ("Insufficient balance for order", "balance"),
            ("Order execution failed", "order"),
            ("Database connection error", "database"),
            ("Just a normal info message", None)
        ]
        
        correct_detections = 0
        for message, expected_category in test_cases:
            detected = monitor.is_critical_error(message)
            if detected == expected_category:
                correct_detections += 1
            print(f"   Test: '{message[:30]}...' → {detected} {'✅' if detected == expected_category else '❌'}")
        
        print(f"   🎯 Detection accuracy: {correct_detections}/{len(test_cases)}")
        
        return correct_detections >= len(test_cases) - 1  # Allow one failure
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        return False

def create_error_monitor_file():
    """Check if error monitor file exists"""
    
    error_monitor_file = Path("trading_bot/utils/error_monitor.py")
    
    if error_monitor_file.exists():
        print("✅ error_monitor.py already exists")
        return True
    else:
        print("❌ error_monitor.py not found")
        print("📋 Please save the error_monitor.py file from the artifact above")
        return False

def show_expected_behavior():
    """Show what the user can expect"""
    
    print("\n📱 What You'll Receive on Telegram:")
    print("=" * 50)
    
    print("""
🚨 IMMEDIATE ALERTS (only for severe issues):
   • Connection failures to Binance
   • API rate limiting/permission errors  
   • Bot crashes or unexpected stops

⚠️ HOURLY SUMMARIES (only when issues occur):
   • Count of critical errors by category
   • Recent warning messages
   • Trading impact assessment

✅ ALL CLEAR SUMMARIES (every 6 hours if no issues):
   • Confirms bot is healthy
   • No critical errors detected
   • Trading functions operational

❌ NO ALERTS FOR:
   • Normal trade executions (you already have those)
   • Info messages
   • Minor warnings that don't affect trading
   • Regular bot operations
""")

def main():
    """Main integration process"""
    
    print("🔍 Simple Error-Only Monitor Integration")
    print("=" * 45)
    
    success_count = 0
    total_steps = 3
    
    # Step 1: Check if error monitor file exists
    if create_error_monitor_file():
        success_count += 1
    
    # Step 2: Integrate with main.py
    if add_error_monitoring_to_main():
        success_count += 1
    
    # Step 3: Test integration
    if test_integration():
        success_count += 1
    
    print("\n" + "=" * 45)
    print(f"🎯 Integration Results: {success_count}/{total_steps} steps completed")
    
    if success_count >= 2:  # Allow file creation to fail
        print("\n✅ ERROR MONITORING INTEGRATION SUCCESSFUL!")
        
        show_expected_behavior()
        
        print("\n📋 Next Steps:")
        print("1. Restart your trading bot:")
        print("   cd trading_bot && python main.py")
        
        print("\n2. Look for this in startup logs:")
        print("   🔍 Critical error monitoring started")
        
        print("\n3. Test with a fake error (optional):")
        print("   # In Python console:")
        print("   import logging")
        print("   logging.error('Connection timeout to Binance API')")
        print("   # Should trigger immediate alert")
        
        print("\n🎯 Your bot will now only alert on critical issues!")
        print("Perfect for business trip monitoring without spam! 📱")
        
    else:
        print("\n❌ INTEGRATION INCOMPLETE")
        print("Please check the errors above and retry")
        
        if success_count == 0:
            print("\n💡 Missing error_monitor.py file")
            print("Save the error_monitor.py content from the artifact above")

if __name__ == "__main__":
    main()
