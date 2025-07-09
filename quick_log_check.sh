#!/bin/bash
# Quick Trading Bot Log Analysis
# Fast command-line log checking

LOG_FILE="trading_bot/data/logs/trading_bot.log"

echo "🔍 Trading Bot Log Quick Check"
echo "============================="

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    exit 1
fi

echo "📁 Log file: $LOG_FILE"
echo "📊 File size: $(du -h "$LOG_FILE" | cut -f1)"
echo "📅 Last modified: $(date -r "$LOG_FILE" '+%Y-%m-%d %H:%M:%S')"
echo ""

function show_section() {
    echo "🔍 $1"
    echo "---"
}

case "${1:-summary}" in
    "errors"|"error")
        show_section "ERRORS (Last 20)"
        grep " - ERROR - " "$LOG_FILE" | tail -20 | while read line; do
            echo "❌ $line"
        done
        ;;
        
    "warnings"|"warning")
        show_section "WARNINGS (Last 20)"
        grep " - WARNING - " "$LOG_FILE" | tail -20 | while read line; do
            echo "⚠️  $line"
        done
        ;;
        
    "recent")
        show_section "RECENT ACTIVITY (Last 30 lines)"
        tail -30 "$LOG_FILE" | while read line; do
            if echo "$line" | grep -q " - ERROR - "; then
                echo "❌ $line"
            elif echo "$line" | grep -q " - WARNING - "; then
                echo "⚠️  $line"
            elif echo "$line" | grep -qi "trade\|order\|buy\|sell\|compound"; then
                echo "💰 $line"
            else
                echo "ℹ️  $line"
            fi
        done
        ;;
        
    "trading")
        show_section "TRADING ACTIVITY (Last 20)"
        grep -i "trade\|order\|buy\|sell\|executed\|filled\|compound" "$LOG_FILE" | tail -20 | while read line; do
            echo "💰 $line"
        done
        ;;
        
    "connection"|"conn")
        show_section "CONNECTION ISSUES"
        grep -i "connection\|timeout\|failed\|retry\|reconnect\|binance.*error" "$LOG_FILE" | tail -15 | while read line; do
            echo "🌐 $line"
        done
        ;;
        
    "compound")
        show_section "COMPOUND INTEREST ACTIVITY"
        grep -i "compound\|profit.*accumulated\|order.*size\|multiplier" "$LOG_FILE" | tail -10 | while read line; do
            echo "📈 $line"
        done
        ;;
        
    "startup"|"start")
        show_section "BOT STARTUPS"
        grep -i "initialized\|starting\|loading.*env\|binance.*client.*initialized" "$LOG_FILE" | tail -10 | while read line; do
            echo "🚀 $line"
        done
        ;;
        
    "count"|"summary")
        show_section "LOG SUMMARY"
        
        total_lines=$(wc -l < "$LOG_FILE")
        error_count=$(grep -c " - ERROR - " "$LOG_FILE" 2>/dev/null || echo 0)
        warning_count=$(grep -c " - WARNING - " "$LOG_FILE" 2>/dev/null || echo 0)
        info_count=$(grep -c " - INFO - " "$LOG_FILE" 2>/dev/null || echo 0)
        
        echo "📊 Total lines: $total_lines"
        echo "❌ Errors: $error_count"
        echo "⚠️  Warnings: $warning_count" 
        echo "ℹ️  Info: $info_count"
        echo ""
        
        # Recent activity (last hour)
        echo "🕐 Activity in last hour:"
        recent_time=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M')
        recent_count=$(grep "$recent_time\|$(date '+%Y-%m-%d %H:')" "$LOG_FILE" 2>/dev/null | wc -l)
        echo "   Recent logs: $recent_count"
        
        # Trading activity
        trading_count=$(grep -ic "trade\|order\|buy\|sell\|compound" "$LOG_FILE" 2>/dev/null || echo 0)
        echo "💰 Trading logs: $trading_count"
        
        # Connection issues
        conn_issues=$(grep -ic "connection\|timeout\|failed\|error.*binance" "$LOG_FILE" 2>/dev/null || echo 0)
        echo "🌐 Connection issues: $conn_issues"
        
        echo ""
        if [ "$error_count" -eq 0 ] && [ "$warning_count" -lt 5 ]; then
            echo "✅ Bot looks healthy!"
        elif [ "$error_count" -lt 5 ] && [ "$warning_count" -lt 20 ]; then
            echo "⚠️  Some issues found, but bot seems stable"
        else
            echo "❌ Significant issues detected - check errors and warnings"
        fi
        ;;
        
    "search")
        if [ -z "$2" ]; then
            echo "Usage: $0 search <term>"
            echo "Example: $0 search 'connection'"
            exit 1
        fi
        
        show_section "SEARCH RESULTS FOR: '$2'"
        grep -i "$2" "$LOG_FILE" | tail -20 | while read line; do
            echo "🔍 $line"
        done
        ;;
        
    "tail"|"live")
        show_section "LIVE LOG TAIL (Press Ctrl+C to stop)"
        tail -f "$LOG_FILE" | while read line; do
            if echo "$line" | grep -q " - ERROR - "; then
                echo "❌ $line"
            elif echo "$line" | grep -q " - WARNING - "; then
                echo "⚠️  $line"
            elif echo "$line" | grep -qi "trade\|order\|buy\|sell\|compound"; then
                echo "💰 $line"
            else
                echo "ℹ️  $line"
            fi
        done
        ;;
        
    "help"|*)
        echo "Available commands:"
        echo "  summary    - Overview and health check (default)"
        echo "  errors     - Show recent errors"
        echo "  warnings   - Show recent warnings"
        echo "  recent     - Show recent activity (last 30 lines)"
        echo "  trading    - Show trading-related logs"
        echo "  connection - Show connection issues"
        echo "  compound   - Show compound interest activity"
        echo "  startup    - Show bot startup messages"
        echo "  search <term> - Search for specific term"
        echo "  tail       - Live log monitoring"
        echo ""
        echo "Examples:"
        echo "  $0                    # Quick summary"
        echo "  $0 errors            # Show errors"
        echo "  $0 search 'timeout'  # Search for timeout issues"
        echo "  $0 tail              # Watch logs live"
        ;;
esac

echo ""
