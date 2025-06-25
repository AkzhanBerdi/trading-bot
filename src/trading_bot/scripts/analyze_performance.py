# trading_bot/scripts/analyze_performance.py
#!/usr/bin/env python3
"""Analyze trading bot performance"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from trading_bot.utils.performance_tracker import PerformanceTracker
from trading_bot.utils.logger import trading_logger

logger = trading_logger.get_logger()

def analyze_performance(days: int = 30):
    """Analyze performance for specified period"""
    
    print(f"📊 Trading Bot Performance Analysis (Last {days} days)")
    print("=" * 60)
    
    try:
        # Initialize performance tracker
        tracker = PerformanceTracker()
        
        # Calculate metrics
        metrics = tracker.calculate_performance_metrics(days)
        
        if "error" in metrics:
            print(f"❌ Error: {metrics['error']}")
            return
        
        # Display results
        print(f"\n📈 Overall Performance:")
        print(f"  Total Return: {metrics['total_return']:+.2f}%")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: -{metrics['max_drawdown']:.2f}%")
        print(f"  Volatility: {metrics['volatility']:.2f}%")
        print(f"  Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        
        print(f"\n🎯 Trading Statistics:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Avg Trade Return: {metrics['avg_trade_return']:+.2f}%")
        
        print(f"\n📋 Strategy Breakdown:")
        for strategy, data in metrics['strategy_breakdown'].items():
            print(f"  {strategy.upper()}:")
            print(f"    Trades: {data['trades']}")
            print(f"    Total P&L: {data['total_pnl']:+.2f}")
            print(f"    Win Rate: {data['win_rate']:.1f}%")
            print(f"    Wins/Losses: {data['wins']}/{data['losses']}")
        
        # Save detailed report
        report_file = f"data/performance/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        print(f"❌ Analysis failed: {e}")

def compare_strategies():
    """Compare performance of different strategies"""
    
    print("\n🔄 Strategy Comparison")
    print("=" * 30)
    
    try:
        tracker = PerformanceTracker()
        
        # Get performance for different periods
        periods = [7, 30, 90]
        
        for days in periods:
            print(f"\n📅 Last {days} days:")
            metrics = tracker.calculate_performance_metrics(days)
            
            if "error" not in metrics:
                for strategy, data in metrics['strategy_breakdown'].items():
                    if data['trades'] > 0:
                        avg_pnl = data['total_pnl'] / data['trades']
                        print(f"  {strategy}: {data['trades']} trades, "
                              f"{data['win_rate']:.1f}% win rate, "
                              f"{avg_pnl:+.2f} avg P&L")
    
    except Exception as e:
        print(f"❌ Strategy comparison failed: {e}")

def main():
    """Main function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze trading bot performance")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--compare", action="store_true", help="Compare strategies")
    
    args = parser.parse_args()
    
    # Run analysis
    analyze_performance(args.days)
    
    if args.compare:
        compare_strategies()

if __name__ == "__main__":
    main()
