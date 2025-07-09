#!/usr/bin/env python3
"""
Fix Import Error - Check and fix error_monitor.py file
"""

from pathlib import Path

def check_error_monitor_file():
    """Check what's in the error_monitor.py file"""
    
    error_file = Path("trading_bot/utils/error_monitor.py")
    
    if not error_file.exists():
        print("❌ error_monitor.py doesn't exist")
        return False
    
    # Check file content
    with open(error_file, 'r') as f:
        content = f.read()
    
    print(f"📁 File size: {len(content)} characters")
    print(f"📝 First 200 characters:")
    print(content[:200])
    
    # Check if CriticalErrorMonitor class exists
    if 'class CriticalErrorMonitor' in content:
        print("✅ CriticalErrorMonitor class found")
        return True
    else:
        print("❌ CriticalErrorMonitor class NOT found")
        return False

def fix_error_monitor_file():
    """Create correct error_monitor.py file"""
    
    print("🔧 Creating correct error_monitor.py file...")
    
    error_monitor_content = '''# trading_bot/utils/error_monitor.py
"""
Simple Error Monitor
Only alerts on critical warnings/errors that prevent trading
"""

import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List

class CriticalErrorMonitor:
    """Monitor only critical errors and warnings that affect trading"""
    
    def __init__(self, telegram_notifier):
        self.telegram = telegram_notifier
        self.logger = logging.getLogger(__name__)
        
        # Track issues for hourly summaries
        self.hourly_errors = []
        self.hourly_warnings = []
        self.last_summary_time = None
        
        # Critical error patterns that prevent trading
        self.critical_patterns = {
            'connection': ['connection', 'timeout', 'network', 'unreachable'],
            'api': ['api error', 'rate limit', '429', 'permission denied'],
            'balance': ['insufficient', 'balance', 'not enough'],
            'order': ['order failed', 'execution failed', 'rejected'],
            'database': ['database', 'sqlite', 'connection failed'],
            'bot_crash': ['crash', 'exception', 'stopped unexpectedly']
        }
        
        self.monitoring_active = False
    
    def start_monitoring(self):
        """Start error monitoring"""
        self.monitoring_active = True
        self.logger.info("🔍 Critical error monitoring started")
    
    def stop_monitoring(self):
        """Stop error monitoring"""
        self.monitoring_active = False
        self.logger.info("🔍 Critical error monitoring stopped")
    
    def is_critical_error(self, message: str) -> str:
        """Check if error message indicates critical trading issue"""
        message_lower = message.lower()
        
        for category, patterns in self.critical_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return category
        
        return None
    
    async def log_error(self, error_message: str, error_type: str = None):
        """Log critical error and send immediate alert if severe"""
        if not self.monitoring_active:
            return
        
        # Check if this is a critical trading issue
        critical_category = self.is_critical_error(error_message)
        
        if critical_category:
            error_data = {
                'timestamp': datetime.now(),
                'message': error_message,
                'category': critical_category,
                'type': error_type or 'ERROR'
            }
            
            self.hourly_errors.append(error_data)
            
            # Send immediate alert for severe issues
            severe_categories = ['connection', 'api', 'bot_crash']
            if critical_category in severe_categories:
                await self.send_immediate_alert(error_data)
            
            self.logger.warning(f"🚨 Critical error logged: {critical_category} - {error_message}")
    
    async def log_warning(self, warning_message: str):
        """Log critical warning"""
        if not self.monitoring_active:
            return
        
        # Check if this warning affects trading
        critical_category = self.is_critical_error(warning_message)
        
        if critical_category:
            warning_data = {
                'timestamp': datetime.now(),
                'message': warning_message,
                'category': critical_category,
                'type': 'WARNING'
            }
            
            self.hourly_warnings.append(warning_data)
            self.logger.warning(f"⚠️ Critical warning logged: {critical_category} - {warning_message}")
    
    async def send_immediate_alert(self, error_data: Dict):
        """Send immediate alert for severe errors"""
        try:
            category_emojis = {
                'connection': '🌐',
                'api': '🔑', 
                'bot_crash': '💥',
                'balance': '💰',
                'order': '📋'
            }
            
            emoji = category_emojis.get(error_data['category'], '🚨')
            
            message = f"""🚨 **CRITICAL ALERT**

{emoji} **{error_data['category'].title()} Issue**
📝 {error_data['message']}

⏰ {error_data['timestamp'].strftime('%H:%M:%S')}
🎯 This may prevent trading execution

💬 Use /status to check bot health
"""
            
            # Use existing telegram notifier send_message method
            await self.telegram.send_message(message)
            self.logger.info(f"📱 Immediate alert sent for {error_data['category']}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send immediate alert: {e}")
    
    async def send_hourly_summary(self):
        """Send hourly summary only if there are critical issues"""
        try:
            now = datetime.now()
            
            # Only send if we have errors/warnings or it's been 6+ hours since last summary
            if not (self.hourly_errors or self.hourly_warnings):
                # Send "all clear" summary every 6 hours
                if (self.last_summary_time is None or 
                    (now - self.last_summary_time).total_seconds() >= 21600):
                    await self.send_all_clear_summary()
                return
            
            # Count issues by category
            error_categories = defaultdict(int)
            warning_categories = defaultdict(int)
            
            for error in self.hourly_errors:
                error_categories[error['category']] += 1
            
            for warning in self.hourly_warnings:
                warning_categories[warning['category']] += 1
            
            # Build summary message
            message = f"⚠️ **Hourly Bot Health Alert**\\n"
            message += f"🕐 {now.strftime('%H:%M')} Summary\\n\\n"
            
            if self.hourly_errors:
                message += f"❌ **{len(self.hourly_errors)} Critical Errors:**\\n"
                for category, count in error_categories.items():
                    message += f"   • {category.title()}: {count}\\n"
                message += "\\n"
            
            if self.hourly_warnings:
                message += f"⚠️ **{len(self.hourly_warnings)} Warnings:**\\n" 
                for category, count in warning_categories.items():
                    message += f"   • {category.title()}: {count}\\n"
                message += "\\n"
            
            # Show recent issues
            recent_issues = (self.hourly_errors + self.hourly_warnings)[-3:]
            if recent_issues:
                message += "🔍 **Recent Issues:**\\n"
                for issue in recent_issues:
                    time_str = issue['timestamp'].strftime('%H:%M')
                    message += f"   {time_str} - {issue['message'][:50]}...\\n"
            
            message += f"\\n💬 Use /status for detailed health check"
            
            await self.telegram.send_message(message)
            self.logger.info(f"📱 Hourly summary sent: {len(self.hourly_errors)} errors, {len(self.hourly_warnings)} warnings")
            
            # Clear hourly counters
            self.hourly_errors.clear()
            self.hourly_warnings.clear()
            self.last_summary_time = now
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send hourly summary: {e}")
    
    async def send_all_clear_summary(self):
        """Send 'all clear' summary when no issues"""
        try:
            now = datetime.now()
            
            message = f"""✅ **Bot Health: All Clear**

🕐 {now.strftime('%H:%M')} - 6 Hour Check
🤖 No critical errors detected
📈 Trading functions operational

⚡ Next health check: +6 hours
💬 Use /status for detailed info
"""
            
            await self.telegram.send_message(message)
            self.last_summary_time = now
            self.logger.info("📱 All clear summary sent")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send all clear summary: {e}")
    
    async def check_bot_health(self):
        """Periodic health check - run every hour"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(3600)  # 1 hour
                await self.send_hourly_summary()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Health check error: {e}")
                await asyncio.sleep(300)  # 5 minute retry on error


# Custom logging handler to capture critical errors
class CriticalErrorHandler(logging.Handler):
    """Logging handler that sends critical errors to monitor"""
    
    def __init__(self, error_monitor):
        super().__init__()
        self.error_monitor = error_monitor
        self.setLevel(logging.WARNING)  # Only WARNING and above
    
    def emit(self, record):
        """Handle log record"""
        if record.levelno >= logging.ERROR:
            # Run in event loop
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.error_monitor.log_error(
                        record.getMessage(), 
                        record.levelname
                    )
                )
            except:
                pass  # Don't break on logging errors
        
        elif record.levelno >= logging.WARNING:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.error_monitor.log_warning(record.getMessage())
                )
            except:
                pass


# Easy integration function
def setup_error_monitoring(telegram_notifier):
    """Set up error monitoring with existing telegram notifier"""
    
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
    
    return error_monitor, health_task

# Global instance (will be initialized in main.py)
error_monitor = None
'''
    
    # Write the file
    error_file = Path("trading_bot/utils/error_monitor.py")
    with open(error_file, 'w') as f:
        f.write(error_monitor_content)
    
    print(f"✅ Created {error_file}")
    return True

def test_import():
    """Test that the import works now"""
    
    print("🧪 Testing import...")
    
    try:
        import sys
        sys.path.insert(0, 'trading_bot')
        
        from utils.error_monitor import CriticalErrorMonitor, setup_error_monitoring
        print("✅ Import successful!")
        
        # Quick test
        from utils.telegram_notifier import telegram_notifier
        monitor = CriticalErrorMonitor(telegram_notifier)
        
        # Test error detection
        result = monitor.is_critical_error("Connection timeout to Binance API")
        print(f"✅ Error detection test: 'Connection timeout' → '{result}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Import still failing: {e}")
        return False

def main():
    """Fix the import error"""
    
    print("🔧 Fixing Error Monitor Import Issue")
    print("=" * 40)
    
    # Step 1: Check current file
    print("1️⃣ Checking current error_monitor.py...")
    file_ok = check_error_monitor_file()
    
    if not file_ok:
        # Step 2: Fix the file
        print("\n2️⃣ Fixing error_monitor.py...")
        if fix_error_monitor_file():
            # Step 3: Test import
            print("\n3️⃣ Testing import...")
            if test_import():
                print("\n✅ IMPORT ERROR FIXED!")
                print("\n📋 Next Steps:")
                print("1. Restart your trading bot:")
                print("   cd trading_bot && python main.py")
                print("\n2. Look for:")
                print("   🔍 Critical error monitoring started")
                print("\n3. Test with a fake error:")
                print("   import logging")
                print("   logging.error('Connection timeout to Binance API')")
                
            else:
                print("\n❌ Import still failing - please check manually")
        else:
            print("\n❌ Failed to fix file")
    else:
        print("\n🤔 File looks correct but import failing...")
        print("Let's test the import:")
        if test_import():
            print("\n✅ Import working now!")
        else:
            print("\n❌ Still having import issues")

if __name__ == "__main__":
    main()
