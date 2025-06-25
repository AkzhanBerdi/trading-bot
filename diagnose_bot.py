#!/usr/bin/env python3
"""
Trading Bot Diagnostic Tool
Checks timestamp sync, API connectivity, and bot health
"""

import sys
import os
import time
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_system_time():
    """Check system time vs Binance server time"""
    print("🕒 CHECKING SYSTEM TIME...")
    
    try:
        # Get Binance server time
        response = requests.get('https://api.binance.com/api/v3/time', timeout=10)
        if response.status_code == 200:
            server_time = response.json()['serverTime']
            local_time = int(time.time() * 1000)
            offset = server_time - local_time
            
            print(f"📅 Local time:  {datetime.fromtimestamp(local_time/1000)}")
            print(f"📅 Server time: {datetime.fromtimestamp(server_time/1000)}")
            print(f"⏰ Time offset: {offset} ms ({offset/1000:.2f} seconds)")
            
            if abs(offset) > 1000:
                print("❌ CRITICAL: Time offset > 1 second!")
                print("🔧 Fix: Sync system time with NTP server")
                return False
            elif abs(offset) > 500:
                print("⚠️ WARNING: Time offset > 500ms")
                return False
            else:
                print("✅ Time sync is acceptable")
                return True
        else:
            print(f"❌ Failed to get server time: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Time check failed: {e}")
        return False

def diagnose_api_connection():
    """Diagnose Binance API connection"""
    print("\n🔗 CHECKING API CONNECTION...")
    
    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY', '')
    secret_key = os.getenv('BINANCE_SECRET_KEY', '')
    environment = os.getenv('ENVIRONMENT', 'development')
    
    print(f"🔑 API Key: {'Set' if api_key else 'Missing'} ({len(api_key)} chars)")
    print(f"🔐 Secret: {'Set' if secret_key else 'Missing'} ({len(secret_key)} chars)")
    print(f"🌐 Environment: {environment}")
    
    if not api_key or not secret_key:
        print("❌ API credentials missing!")
        return False
    
    try:
        # Import your enhanced client
        from trading_bot.utils.binance_client import BinanceManager
        
        # Test connection
        bm = BinanceManager()
        print(f"🌐 Using: {'Testnet' if bm.testnet else 'Live Trading'}")
        
        # Test market data (public)
        try:
            btc_price = float(bm.get_ticker("BTCUSDT")['price'])
            print(f"📈 BTC Price: ${btc_price:,.2f} (✅ Market data OK)")
        except Exception as e:
            print(f"❌ Market data failed: {e}")
            return False
        
        # Test account access (authenticated)
        try:
            account = bm.get_account()
            if account:
                balances = [b for b in account['balances'] 
                           if float(b['free']) > 0 or float(b['locked']) > 0]
                print(f"✅ Account access OK ({len(balances)} assets with balance)")
                
                # Calculate portfolio value
                total_value = 0
                for balance in balances:
                    asset = balance['asset']
                    total = float(balance['free']) + float(balance['locked'])
                    
                    if asset in ['USDT', 'USDC', 'BUSD']:
                        total_value += total
                    else:
                        try:
                            ticker = bm.get_ticker(f"{asset}USDT")
                            price = float(ticker['price'])
                            total_value += total * price
                        except:
                            pass  # Skip if price unavailable
                
                print(f"💰 Estimated portfolio value: ${total_value:.2f}")
                return True
            else:
                print("⚠️ Account access returned empty")
                return False
                
        except Exception as e:
            if "Timestamp" in str(e) or "-1021" in str(e):
                print("❌ TIMESTAMP ERROR in account access!")
                print("🔧 Solution: Run timestamp fix or sync system time")
                return False
            else:
                print(f"❌ Account access failed: {e}")
                return False
    
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def check_bot_health():
    """Check bot configuration and health"""
    print("\n🤖 CHECKING BOT HEALTH...")
    
    # Check if bot files exist
    required_files = [
        "src/trading_bot/main.py",
        "src/trading_bot/utils/binance_client.py",
        "src/trading_bot/strategies/grid_trading.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
    
    # Check data directories
    data_dirs = ["data/logs", "data/performance", "data/learning_history"]
    for dir_path in data_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path}/")
        else:
            print(f"⚠️ Missing: {dir_path}/ (will be created)")
            os.makedirs(dir_path, exist_ok=True)

def main():
    """Run complete diagnosis"""
    print("🔍 TRADING BOT DIAGNOSTIC")
    print("=" * 50)
    
    # Run all checks
    time_ok = check_system_time()
    api_ok = diagnose_api_connection()
    check_bot_health()
    
    print("\n📋 DIAGNOSIS SUMMARY")
    print("=" * 30)
    
    if time_ok and api_ok:
        print("✅ All systems operational!")
        print("🚀 Bot should work normally")
    elif not time_ok:
        print("❌ Time synchronization issue")
        print("🔧 IMMEDIATE FIX:")
        print("   sudo ntpdate -s time.nist.gov")
        print("   # or")
        print("   uv run python quick_binance_timestamp_fix.py")
    elif not api_ok:
        print("❌ API connection issue")
        print("🔧 Check API credentials and permissions")
    
    print(f"\n🕒 Diagnosis completed at: {datetime.now()}")

if __name__ == "__main__":
    main()
