#!/usr/bin/env python3
"""
Sync System Time to Binance Server Time
Sets your system clock to exactly match Binance servers
"""

import requests
import subprocess
import time
from datetime import datetime

def get_binance_server_time():
    """Get current Binance server time"""
    try:
        response = requests.get('https://api.binance.com/api/v3/time', timeout=10)
        if response.status_code == 200:
            server_time_ms = response.json()['serverTime']
            return server_time_ms
        else:
            print(f"❌ Failed to get server time: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting server time: {e}")
        return None

def set_system_time(timestamp_ms):
    """Set system time to match timestamp"""
    try:
        # Convert milliseconds to seconds
        timestamp_s = timestamp_ms / 1000
        
        # Format for timedatectl (YYYY-MM-DD HH:MM:SS)
        dt = datetime.fromtimestamp(timestamp_s)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"🕒 Setting system time to: {time_str}")
        
        # First disable NTP to allow manual time setting
        subprocess.run(['sudo', 'timedatectl', 'set-ntp', 'false'], check=True)
        print("📡 NTP disabled")
        
        # Set the time
        subprocess.run(['sudo', 'timedatectl', 'set-time', time_str], check=True)
        print("✅ System time updated")
        
        # Re-enable NTP for future syncing
        subprocess.run(['sudo', 'timedatectl', 'set-ntp', 'true'], check=True)
        print("📡 NTP re-enabled")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to set system time: {e}")
        print("💡 Try running with sudo privileges")
        return False
    except Exception as e:
        print(f"❌ Error setting time: {e}")
        return False

def verify_sync():
    """Verify time sync with Binance"""
    print("\n🔍 Verifying synchronization...")
    
    # Get Binance time again
    server_time = get_binance_server_time()
    if not server_time:
        return False
    
    # Get local time
    local_time = int(time.time() * 1000)
    
    # Calculate offset
    offset = server_time - local_time
    
    print(f"📅 Binance time: {datetime.fromtimestamp(server_time/1000)}")
    print(f"📅 Local time:   {datetime.fromtimestamp(local_time/1000)}")
    print(f"⏰ Offset: {offset} ms ({offset/1000:.2f} seconds)")
    
    if abs(offset) <= 100:
        print("✅ PERFECT: Time sync within 100ms!")
        return True
    elif abs(offset) <= 500:
        print("✅ GOOD: Time sync within 500ms")
        return True
    elif abs(offset) <= 1000:
        print("⚠️ ACCEPTABLE: Time sync within 1 second")
        return True
    else:
        print("❌ BAD: Time offset too large")
        return False

def main():
    print("🕒 SYNC SYSTEM TIME TO BINANCE SERVERS")
    print("=" * 45)
    
    # Step 1: Get Binance server time
    print("📡 Getting Binance server time...")
    server_time = get_binance_server_time()
    
    if not server_time:
        print("❌ Cannot proceed without server time")
        return False
    
    # Show current offset
    local_time = int(time.time() * 1000)
    offset = server_time - local_time
    
    print(f"📊 Current offset: {offset} ms ({offset/1000:.2f} seconds)")
    print(f"📅 Binance time: {datetime.fromtimestamp(server_time/1000)}")
    print(f"📅 Your time:    {datetime.fromtimestamp(local_time/1000)}")
    
    if abs(offset) <= 100:
        print("✅ Your time is already perfectly synced!")
        return True
    
    # Step 2: Ask for confirmation
    print(f"\n⚠️ This will change your system time by {offset/1000:.2f} seconds")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Operation cancelled")
        return False
    
    # Step 3: Set system time
    print(f"\n🔧 Syncing system time...")
    if set_system_time(server_time):
        # Step 4: Verify sync
        time.sleep(1)  # Wait a moment
        return verify_sync()
    else:
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("📋 Next steps:")
        print("   1. uv run python diagnose_bot.py")
        print("   2. uv run python trading_bot/main.py")
    else:
        print("\n❌ FAILED!")
        print("💡 Alternative: sudo ntpdate -s time.nist.gov")
