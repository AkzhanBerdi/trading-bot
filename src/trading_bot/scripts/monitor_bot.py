# trading_bot/scripts/monitor_bot.py
#!/usr/bin/env python3
"""Enhanced monitoring script for trading bot"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from trading_bot.utils.performance_tracker import PerformanceTracker
from trading_bot.utils.binance_client import BinanceManager

def check_bot_health():
    """Check overall bot health"""
    
    print("🏥 Bot Health Check")
    print("=" * 25)
    
    # Check log files
    log_file = Path("data/logs/trading_bot.log")
    if log_file.exists():
        # Get last few lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if lines:
                last_log = lines[-1].strip()
                print(f"📝 Last log: {last_log[:100]}...")
                
                # Check for recent activity (last 5 minutes)
                recent_logs = [line for line in lines[-20:] 
                             if datetime.now().strftime('%Y-%m-%d %H:%M') in line]
                print(f"🕐 Recent activity: {len(recent_logs)} logs in last 20 entries")
            else:
                print("⚠️  No logs found")
    else:
        print("❌ Log file not found")
    
    # Check connection to Binance
    try:
        binance = BinanceManager()
        if binance.test_connection():
            print("✅ Binance connection: OK")
        else:
            print("❌ Binance connection: FAILED")
    except Exception as e:
        print(f"❌ Binance connection error: {e}")
    
    # Check data files
    data_files = [
        "data/performance/trades.json",
        "data/performance/portfolio_history.json"
    ]
    
    for file_path in data_files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    print(f"✅ {file_path}: {len(data)} records")
            except Exception as e:
                print(f"❌ {file_path}: Error reading - {e}")
        else:
            print(f"⚠️  {file_path}: Not found")

def show_portfolio_status():
    """Show current portfolio status"""
    
    print("\n💰 Portfolio Status")
    print("=" * 25)
    
    try:
        binance = BinanceManager()
        balances = binance.get_account_balance()
        
        if balances:
            total_value = 0
            print(f"{'Asset':<8} {'Quantity':<15} {'USD Value':<12}")
            print("-" * 40)
            
            for balance in balances:
                asset = balance['asset']
                quantity = balance['total']
                
                # Get USD value
                if asset in ['USDT', 'USDC']:
                    usd_value = quantity
                else:
                    try:
                        price = binance.get_price(f"{asset}USDT")
                        usd_value = quantity * price if price else 0
                    except:
                        usd_value = 0
                
                if usd_value > 1:  # Only show significant balances
                    print(f"{asset:<8} {quantity:<15.4f} ${usd_value:<11.2f}")
                    total_value += usd_value
            
            print("-" * 40)
            print(f"{'TOTAL':<8} {'':<15} ${total_value:<11.2f}")
        else:
            print("❌ Could not fetch portfolio data")
            
    except Exception as e:
        print(f"❌ Portfolio status error: {e}")

def show_recent_performance():
    """Show recent trading performance"""
    
    print("\n📊 Recent Performance")
    print("=" * 25)
    
    try:
        tracker = PerformanceTracker()
        
        for days in [1, 7, 30]:
            metrics = tracker.calculate_performance_metrics(days)
            
            if "error" not in metrics:
                print(f"\n📅 Last {days} day(s):")
                print(f"  Return: {metrics['total_return']:+.2f}%")
                print(f"  Trades: {metrics['total_trades']}")
                print(f"  Win Rate: {metrics['win_rate']:.1f}%")
                print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
            else:
                print(f"📅 Last {days} day(s): No data")
    
    except Exception as e:
        print(f"❌ Performance error: {e}")

def show_ai_status():
    """Show AI system status"""
    
    print("\n🧠 AI System Status")
    print("=" * 25)
    
    # Check if AI files exist
    ai_files = [
        "data/learning_history/ai_optimizations.json",
        "data/optimizations/"
    ]
    
    ai_active = False
    for file_path in ai_files:
        if Path(file_path).exists():
            ai_active = True
            break
    
    if ai_active:
        print("✅ AI system: ACTIVE")
        
        # Check recent AI activity
        try:
            opt_file = Path("data/learning_history/ai_optimizations.json")
            if opt_file.exists():
                with open(opt_file, 'r') as f:
                    data = json.load(f)
                    optimizations = data.get('optimizations', [])
                    print(f"🔧 Total optimizations: {len(optimizations)}")
                    
                    if optimizations:
                        latest = optimizations[-1]
                        print(f"🕐 Latest optimization: {latest.get('timestamp', 'Unknown')}")
        except Exception as e:
            print(f"⚠️  AI data error: {e}")
    else:
        print("⚠️  AI system: INACTIVE")

def monitor_continuously():
    """Continuous monitoring mode"""
    
    print("🔄 Continuous Monitoring Mode (Press Ctrl+C to stop)")
    print("=" * 55)
    
    try:
        while True:
            print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Quick health check
            try:
                binance = BinanceManager()
                if binance.test_connection():
                    print("✅ Binance: Connected")
                else:
                    print("❌ Binance: Disconnected")
            except:
                print("❌ Binance: Error")
            
            # Check recent logs for errors
            log_file = Path("data/logs/trading_bot.log")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    recent_lines = f.readlines()[-10:]
                    errors = [line for line in recent_lines if 'ERROR' in line]
                    if errors:
                        print(f"⚠️  Recent errors: {len(errors)}")
                        print(f"   Latest: {errors[-1].strip()[:80]}...")
                    else:
                        print("✅ No recent errors")
            
            print("-" * 40)
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")

def main():
    """Main monitoring function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor trading bot")
    parser.add_argument("--continuous", "-c", action="store_true", 
                       help="Continuous monitoring mode")
    parser.add_argument("--portfolio", "-p", action="store_true",
                       help="Show portfolio status only")
    parser.add_argument("--performance", "-perf", action="store_true",
                       help="Show performance only")
    
    args = parser.parse_args()
    
    if args.continuous:
        monitor_continuously()
    elif args.portfolio:
        show_portfolio_status()
    elif args.performance:
        show_recent_performance()
    else:
        # Full status check
        check_bot_health()
        show_portfolio_status()
        show_recent_performance()
        show_ai_status()

if __name__ == "__main__":
    main()
