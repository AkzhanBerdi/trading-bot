#!/usr/bin/env python3
"""
Trading Bot Log Analyzer
Analyze logs for errors, warnings, and performance issues
"""

import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class LogAnalyzer:
    def __init__(self, log_path="trading_bot/data/logs/trading_bot.log"):
        self.log_path = Path(log_path)
        self.logs = []
        self.load_logs()
    
    def load_logs(self):
        """Load and parse log file"""
        if not self.log_path.exists():
            print(f"❌ Log file not found: {self.log_path}")
            return
        
        print(f"📋 Loading logs from: {self.log_path}")
        
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            # Parse log lines
            log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
            
            for line_num, line in enumerate(lines, 1):
                match = re.match(log_pattern, line.strip())
                if match:
                    timestamp_str, logger, level, message = match.groups()
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    except:
                        timestamp = None
                    
                    self.logs.append({
                        'line_num': line_num,
                        'timestamp': timestamp,
                        'timestamp_str': timestamp_str,
                        'logger': logger.strip(),
                        'level': level,
                        'message': message,
                        'raw_line': line.strip()
                    })
            
            print(f"✅ Loaded {len(self.logs)} log entries from {len(lines)} lines")
            
        except Exception as e:
            print(f"❌ Failed to load logs: {e}")
    
    def get_log_summary(self):
        """Get overall log summary"""
        print("\n📊 LOG SUMMARY")
        print("=" * 50)
        
        if not self.logs:
            print("No logs found")
            return
        
        # Time range
        first_log = min(self.logs, key=lambda x: x['timestamp'] or datetime.min)
        last_log = max(self.logs, key=lambda x: x['timestamp'] or datetime.min)
        
        print(f"📅 Time Range: {first_log['timestamp_str']} → {last_log['timestamp_str']}")
        
        # Level breakdown
        level_counts = Counter(log['level'] for log in self.logs)
        print(f"\n📈 Log Levels:")
        for level, count in level_counts.most_common():
            emoji = {'ERROR': '❌', 'WARNING': '⚠️', 'INFO': 'ℹ️', 'DEBUG': '🔍'}.get(level, '📝')
            print(f"   {emoji} {level}: {count}")
        
        # Logger breakdown
        logger_counts = Counter(log['logger'] for log in self.logs)
        print(f"\n🏷️  Top Loggers:")
        for logger, count in logger_counts.most_common(10):
            print(f"   {logger}: {count}")
    
    def check_errors_and_warnings(self):
        """Check for errors and warnings"""
        print("\n❌ ERRORS & WARNINGS")
        print("=" * 50)
        
        errors = [log for log in self.logs if log['level'] == 'ERROR']
        warnings = [log for log in self.logs if log['level'] == 'WARNING']
        
        if not errors and not warnings:
            print("✅ No errors or warnings found!")
            return
        
        # Recent errors (last 24 hours)
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        
        recent_errors = [log for log in errors if log['timestamp'] and log['timestamp'] > recent_cutoff]
        recent_warnings = [log for log in warnings if log['timestamp'] and log['timestamp'] > recent_cutoff]
        
        print(f"🔥 Recent Errors (24h): {len(recent_errors)}")
        for error in recent_errors[-10:]:  # Last 10
            print(f"   {error['timestamp_str']} | {error['logger']} | {error['message']}")
        
        print(f"\n⚠️  Recent Warnings (24h): {len(recent_warnings)}")
        for warning in recent_warnings[-10:]:  # Last 10
            print(f"   {warning['timestamp_str']} | {warning['logger']} | {warning['message']}")
        
        # Error patterns
        if errors:
            print(f"\n🔍 Error Patterns:")
            error_messages = [log['message'] for log in errors]
            error_patterns = Counter()
            
            for msg in error_messages:
                # Extract key error patterns
                if 'connection' in msg.lower():
                    error_patterns['Connection Issues'] += 1
                elif 'api' in msg.lower() or 'binance' in msg.lower():
                    error_patterns['API/Binance Issues'] += 1
                elif 'database' in msg.lower() or 'sqlite' in msg.lower():
                    error_patterns['Database Issues'] += 1
                elif 'telegram' in msg.lower():
                    error_patterns['Telegram Issues'] += 1
                elif 'trade' in msg.lower() or 'order' in msg.lower():
                    error_patterns['Trading Issues'] += 1
                else:
                    error_patterns['Other'] += 1
            
            for pattern, count in error_patterns.most_common():
                print(f"   {pattern}: {count}")
    
    def check_trading_activity(self):
        """Check trading-related log activity"""
        print("\n💰 TRADING ACTIVITY")
        print("=" * 50)
        
        # Look for trading-related logs
        trading_keywords = [
            'trade', 'order', 'buy', 'sell', 'grid', 'compound', 
            'profit', 'executed', 'filled', 'signal'
        ]
        
        trading_logs = []
        for log in self.logs:
            if any(keyword in log['message'].lower() for keyword in trading_keywords):
                trading_logs.append(log)
        
        print(f"📊 Trading-related logs: {len(trading_logs)}")
        
        # Recent trading activity
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        recent_trading = [log for log in trading_logs 
                         if log['timestamp'] and log['timestamp'] > recent_cutoff]
        
        print(f"🕐 Recent trading activity (24h): {len(recent_trading)}")
        
        # Show last few trading activities
        print(f"\n📝 Recent Trading Events:")
        for log in trading_logs[-15:]:  # Last 15
            if log['level'] in ['INFO', 'WARNING', 'ERROR']:
                level_emoji = {'INFO': 'ℹ️', 'WARNING': '⚠️', 'ERROR': '❌'}[log['level']]
                print(f"   {log['timestamp_str']} {level_emoji} {log['message']}")
        
        # Look for compound interest updates
        compound_logs = [log for log in self.logs if 'compound' in log['message'].lower()]
        if compound_logs:
            print(f"\n🔄 Compound Interest Updates: {len(compound_logs)}")
            for log in compound_logs[-5:]:  # Last 5
                print(f"   {log['timestamp_str']} | {log['message']}")
    
    def check_performance_issues(self):
        """Check for performance and connectivity issues"""
        print("\n⚡ PERFORMANCE & CONNECTIVITY")
        print("=" * 50)
        
        # Connection issues
        connection_keywords = ['connection', 'timeout', 'failed', 'retry', 'reconnect']
        connection_logs = []
        
        for log in self.logs:
            if any(keyword in log['message'].lower() for keyword in connection_keywords):
                connection_logs.append(log)
        
        if connection_logs:
            print(f"🌐 Connection-related logs: {len(connection_logs)}")
            for log in connection_logs[-5:]:  # Last 5
                print(f"   {log['timestamp_str']} | {log['level']} | {log['message']}")
        else:
            print("✅ No connection issues found")
        
        # Rate limiting
        rate_limit_keywords = ['rate', 'limit', '429', 'too many requests']
        rate_limit_logs = []
        
        for log in self.logs:
            if any(keyword in log['message'].lower() for keyword in rate_limit_keywords):
                rate_limit_logs.append(log)
        
        if rate_limit_logs:
            print(f"\n🚦 Rate limiting issues: {len(rate_limit_logs)}")
            for log in rate_limit_logs[-5:]:
                print(f"   {log['timestamp_str']} | {log['message']}")
        else:
            print("\n✅ No rate limiting issues found")
        
        # Timestamp offset (clock sync)
        timestamp_logs = [log for log in self.logs if 'timestamp offset' in log['message'].lower()]
        if timestamp_logs:
            print(f"\n🕐 Clock Sync Issues: {len(timestamp_logs)}")
            for log in timestamp_logs[-3:]:
                print(f"   {log['timestamp_str']} | {log['message']}")
    
    def check_bot_health(self):
        """Check overall bot health indicators"""
        print("\n🏥 BOT HEALTH CHECK")
        print("=" * 50)
        
        # Startup messages
        startup_logs = [log for log in self.logs 
                       if any(keyword in log['message'].lower() 
                             for keyword in ['initialized', 'starting', 'loaded'])]
        
        if startup_logs:
            print(f"🚀 Bot Startups: {len(startup_logs)}")
            for log in startup_logs[-3:]:  # Last 3 startups
                print(f"   {log['timestamp_str']} | {log['message']}")
        
        # Error recovery
        recovery_logs = [log for log in self.logs 
                        if any(keyword in log['message'].lower() 
                              for keyword in ['recovered', 'resumed', 'reconnected'])]
        
        if recovery_logs:
            print(f"\n🔄 Recovery Events: {len(recovery_logs)}")
            for log in recovery_logs[-5:]:
                print(f"   {log['timestamp_str']} | {log['message']}")
        
        # Check for bot crashes/exits
        crash_keywords = ['crash', 'exit', 'shutdown', 'stopped', 'killed']
        crash_logs = []
        
        for log in self.logs:
            if any(keyword in log['message'].lower() for keyword in crash_keywords):
                crash_logs.append(log)
        
        if crash_logs:
            print(f"\n💥 Potential Crashes/Shutdowns: {len(crash_logs)}")
            for log in crash_logs[-5:]:
                print(f"   {log['timestamp_str']} | {log['level']} | {log['message']}")
        else:
            print(f"\n✅ No crashes detected")
    
    def search_logs(self, search_term, case_sensitive=False):
        """Search logs for specific terms"""
        print(f"\n🔍 SEARCH RESULTS FOR: '{search_term}'")
        print("=" * 50)
        
        if not case_sensitive:
            search_term = search_term.lower()
        
        matches = []
        for log in self.logs:
            message = log['message'] if case_sensitive else log['message'].lower()
            if search_term in message:
                matches.append(log)
        
        print(f"Found {len(matches)} matches:")
        for log in matches[-20:]:  # Last 20 matches
            print(f"   {log['timestamp_str']} | {log['level']} | {log['message']}")
    
    def get_daily_activity(self, days=7):
        """Get daily activity summary"""
        print(f"\n📅 DAILY ACTIVITY (Last {days} days)")
        print("=" * 50)
        
        now = datetime.now()
        daily_stats = defaultdict(lambda: {'total': 0, 'errors': 0, 'warnings': 0, 'trading': 0})
        
        for log in self.logs:
            if not log['timestamp']:
                continue
            
            days_ago = (now - log['timestamp']).days
            if days_ago <= days:
                date_key = log['timestamp'].strftime('%Y-%m-%d')
                daily_stats[date_key]['total'] += 1
                
                if log['level'] == 'ERROR':
                    daily_stats[date_key]['errors'] += 1
                elif log['level'] == 'WARNING':
                    daily_stats[date_key]['warnings'] += 1
                
                if any(keyword in log['message'].lower() 
                      for keyword in ['trade', 'order', 'buy', 'sell']):
                    daily_stats[date_key]['trading'] += 1
        
        # Sort by date
        for date in sorted(daily_stats.keys(), reverse=True):
            stats = daily_stats[date]
            print(f"   {date}: {stats['total']:3d} logs | "
                  f"❌{stats['errors']:2d} | ⚠️{stats['warnings']:2d} | 💰{stats['trading']:2d}")

def main():
    """Main analysis function"""
    print("🔍 Trading Bot Log Analyzer")
    print("=" * 60)
    
    analyzer = LogAnalyzer()
    
    if not analyzer.logs:
        print("❌ No logs to analyze")
        return
    
    # Run all analyses
    analyzer.get_log_summary()
    analyzer.check_errors_and_warnings()
    analyzer.check_trading_activity()
    analyzer.check_performance_issues()
    analyzer.check_bot_health()
    analyzer.get_daily_activity()
    
    print("\n" + "=" * 60)
    print("🎯 ANALYSIS COMPLETE!")
    
    # Quick health assessment
    errors = len([log for log in analyzer.logs if log['level'] == 'ERROR'])
    warnings = len([log for log in analyzer.logs if log['level'] == 'WARNING'])
    
    print(f"\n📋 Quick Health Assessment:")
    if errors == 0 and warnings < 5:
        print("✅ Bot appears healthy - minimal issues found")
    elif errors < 5 and warnings < 20:
        print("⚠️  Bot has some issues but seems stable")
    else:
        print("❌ Bot may have significant issues - review errors above")
    
    print(f"\n💡 To search for specific issues:")
    print(f"   python log_analyzer.py search 'connection'")
    print(f"   python log_analyzer.py search 'binance'")
    print(f"   python log_analyzer.py search 'error'")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'search':
        if len(sys.argv) > 2:
            analyzer = LogAnalyzer()
            analyzer.search_logs(sys.argv[2])
        else:
            print("Usage: python log_analyzer.py search 'search_term'")
    else:
        main()
