#!/usr/bin/env python3
"""
Corrected Telegram Test Script for your directory structure
Run this from: /home/aberdeev/crypto-trading/trading-bot/src/trading_bot/
"""

import os
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

async def test_telegram_setup_corrected():
    """Test Telegram setup with correct paths"""
    print("🧪 TESTING TELEGRAM SETUP (CORRECTED PATHS)")
    print("=" * 60)
    
    # Try to find .env file in possible locations
    env_locations = [
        ".env",  # Current directory
        "../.env",  # Parent directory  
        "../../.env",  # Project root
        "../../../.env"  # Just in case
    ]
    
    env_found = False
    for env_path in env_locations:
        if os.path.exists(env_path):
            print(f"📋 Found .env at: {env_path}")
            load_dotenv(env_path)
            env_found = True
            break
    
    if not env_found:
        print("❌ .env file not found in any expected location")
        print("Expected locations from current directory:")
        for loc in env_locations:
            abs_path = os.path.abspath(loc)
            exists = "✅" if os.path.exists(loc) else "❌"
            print(f"  {exists} {abs_path}")
        return False
    
    # Check environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print(f"📋 Bot Token: {'✅ Found' if bot_token else '❌ Missing'}")
    print(f"📋 Chat ID: {'✅ Found' if chat_id else '❌ Missing'}")
    
    if not bot_token or not chat_id:
        print("\n❌ Missing Telegram credentials in .env file")
        return False
    
    # Test sending message
    print(f"\n📤 Testing message from corrected script...")
    try:
        test_message = (
            "🔧 *Corrected Test Message*\n"
            f"📁 Running from: `{os.getcwd()}`\n"
            f"🕐 {asyncio.get_event_loop().time()}\n\n"
            "✅ Path issues resolved!\n"
            "🤖 Ready for trading bot integration.\n\n"
            "Next: Update main.py with notifications 🚀"
        )
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': test_message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Corrected test message sent successfully!")
            return True
        else:
            print(f"❌ Failed to send test message: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

def check_file_structure():
    """Check current file structure"""
    print(f"\n📁 CHECKING FILE STRUCTURE")
    print("=" * 60)
    
    current_dir = os.getcwd()
    print(f"📍 Current directory: {current_dir}")
    
    required_files = {
        "main.py": "✅ Found" if os.path.exists("main.py") else "❌ Missing",
        "utils/telegram_notifier.py": "✅ Found" if os.path.exists("utils/telegram_notifier.py") else "❌ Missing", 
        "utils/binance_client.py": "✅ Found" if os.path.exists("utils/binance_client.py") else "❌ Missing",
        "strategies/grid_trading.py": "✅ Found" if os.path.exists("strategies/grid_trading.py") else "❌ Missing"
    }
    
    print("\n📋 Required files:")
    for file, status in required_files.items():
        print(f"  {status} {file}")
    
    # Check if main.py has telegram imports
    if os.path.exists("main.py"):
        try:
            with open("main.py", "r") as f:
                content = f.read()
                has_telegram = "telegram_notifier" in content
                print(f"\n📱 Telegram integration in main.py: {'✅ Found' if has_telegram else '❌ Missing'}")
                
                if not has_telegram:
                    print("   → Need to update main.py with Telegram imports")
                
        except Exception as e:
            print(f"   ⚠️ Could not check main.py: {e}")
    
    return all("✅" in status for status in required_files.values())

async def test_telegram_notifier_import():
    """Test importing the telegram notifier"""
    print(f"\n🔧 TESTING TELEGRAM NOTIFIER IMPORT")
    print("=" * 60)
    
    try:
        # Test import
        from utils.telegram_notifier import telegram_notifier, NotificationType
        print("✅ Successfully imported telegram_notifier")
        
        # Test basic functionality
        if telegram_notifier.enabled:
            print("✅ Telegram notifier is enabled")
            
            # Send a test notification
            await telegram_notifier.notify_info(
                "🧪 Import Test Successful",
                {"status": "All imports working", "directory": os.getcwd()}
            )
            print("✅ Test notification sent via notifier class")
            
        else:
            print("⚠️ Telegram notifier is disabled (check credentials)")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   → Check if telegram_notifier.py exists in utils/")
        return False
    except Exception as e:
        print(f"❌ Error testing notifier: {e}")
        return False

def show_next_steps():
    """Show what to do next"""
    print(f"\n🚀 NEXT STEPS")
    print("=" * 60)
    
    steps = [
        "1. ✅ Telegram credentials verified",
        "2. ✅ File structure checked", 
        "3. 🔄 Update main.py with Telegram integration",
        "4. 🛑 Stop current bot (Ctrl+C)",
        "5. 🚀 Restart bot with new notifications",
        "6. 📱 Enjoy real-time trading alerts!"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    print(f"\n💡 To update main.py:")
    print(f"   - Add: from utils.telegram_notifier import telegram_notifier")
    print(f"   - Replace grid execution methods with notification versions")
    print(f"   - Add startup/shutdown notifications")

async def main():
    """Main test function"""
    print("🔧 CORRECTED TELEGRAM INTEGRATION TEST")
    print("=" * 70)
    
    # Test telegram setup
    telegram_ok = await test_telegram_setup_corrected()
    
    if telegram_ok:
        # Check file structure  
        files_ok = check_file_structure()
        
        if files_ok:
            # Test notifier import
            import_ok = await test_telegram_notifier_import()
            
            if import_ok:
                print(f"\n🎉 ALL TESTS PASSED!")
                print("Ready to integrate with your trading bot!")
            else:
                print(f"\n⚠️ Import test failed - check telegram_notifier.py")
        else:
            print(f"\n⚠️ Some files missing - check file structure above")
    else:
        print(f"\n❌ Telegram setup failed - check credentials")
    
    show_next_steps()

if __name__ == "__main__":
    asyncio.run(main())
