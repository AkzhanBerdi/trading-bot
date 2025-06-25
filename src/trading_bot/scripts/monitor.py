# Create monitoring script
cat << 'EOF' > scripts/monitor.py
#!/usr/bin/env python3
import sys
sys.path.append('src')

def monitor_bot():
    """Simple monitoring script"""
    print("📊 Trading Bot Monitor")
    print("=" * 40)
    
    try:
        from trading_bot.utils.binance_client import test_binance_connection
        
        # Test connection
        if test_binance_connection():
            print("\n✅ Ready to trade!")
        else:
            print("\n❌ Fix connection issues first")
            
    except Exception as e:
        print(f"❌ Monitor failed: {e}")

if __name__ == "__main__":
    monitor_bot()
EOF

chmod +x scripts/monitor.py

# Test monitor
uv run python scripts/monitor.py
