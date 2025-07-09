#!/bin/bash
# Verify Bot Startup - Check if bot is working after fix

echo "✅ Bot Startup Verification"
echo "========================="

cd trading_bot

echo "1️⃣ Checking bot process..."
if pgrep -f "python.*main.py" > /dev/null; then
    bot_pid=$(pgrep -f "python.*main.py")
    echo "   ✅ Bot is running (PID: $bot_pid)"
    
    # Check how long it's been running
    bot_start_time=$(ps -o lstart= -p $bot_pid)
    echo "   🕐 Started: $bot_start_time"
else
    echo "   ❌ Bot is not running"
    exit 1
fi

echo ""
echo "2️⃣ Checking log activity..."
if [ -f "data/logs/trading_bot.log" ]; then
    log_lines=$(wc -l < data/logs/trading_bot.log)
    log_size=$(du -h data/logs/trading_bot.log | cut -f1)
    echo "   📁 Log file: $log_lines lines, $log_size"
    
    # Check for recent entries (last 5 minutes)
    recent_entries=$(grep "$(date '+%Y-%m-%d %H:%M')\|$(date -d '1 minute ago' '+%Y-%m-%d %H:%M')\|$(date -d '2 minutes ago' '+%Y-%m-%d %H:%M')" data/logs/trading_bot.log 2>/dev/null | wc -l)
    echo "   🕐 Recent entries (last few minutes): $recent_entries"
    
    if [ $recent_entries -gt 0 ]; then
        echo "   ✅ Bot is actively logging"
        
        echo ""
        echo "📝 Latest log entries:"
        tail -10 data/logs/trading_bot.log | while read line; do
            if echo "$line" | grep -q "ERROR"; then
                echo "      ❌ $line"
            elif echo "$line" | grep -q "WARNING"; then
                echo "      ⚠️  $line"
            elif echo "$line" | grep -qi "compound\|profit\|multiplier"; then
                echo "      💰 $line"
            elif echo "$line" | grep -qi "order.*executed\|buy\|sell"; then
                echo "      💰 $line"
            else
                echo "      ℹ️  $line"
            fi
        done
    else
        echo "   ⚠️  No recent log activity"
    fi
else
    echo "   ❌ Log file not found"
fi

echo ""
echo "3️⃣ Checking compound interest..."
compound_logs=$(grep -i "compound\|multiplier.*profit\|order.*size.*\$" data/logs/trading_bot.log 2>/dev/null | tail -3)
if [ -n "$compound_logs" ]; then
    echo "   ✅ Compound interest logs found:"
    echo "$compound_logs" | while read line; do
        echo "      💰 $line"
    done
else
    echo "   ⚠️  No compound interest logs yet"
fi

echo ""
echo "4️⃣ Checking for errors..."
recent_errors=$(grep "$(date '+%Y-%m-%d')" data/logs/trading_bot.log 2>/dev/null | grep -c "ERROR" || echo 0)
echo "   🔥 Errors today: $recent_errors"

if [ $recent_errors -gt 0 ]; then
    echo "   ❌ Recent errors found:"
    grep "$(date '+%Y-%m-%d')" data/logs/trading_bot.log | grep "ERROR" | tail -3 | while read line; do
        echo "      ❌ $line"
    done
fi

echo ""
echo "5️⃣ Quick health assessment..."
if [ $recent_entries -gt 5 ] && [ $recent_errors -eq 0 ]; then
    echo "   ✅ Bot appears healthy and active"
elif [ $recent_entries -gt 0 ]; then
    echo "   ⚠️  Bot is running but may have some issues"
else
    echo "   ❌ Bot may be stuck or not working properly"
fi

echo ""
echo "🎯 Monitoring commands:"
echo "   Live logs: tail -f data/logs/trading_bot.log"
echo "   Search compound: grep -i 'compound\|multiplier' data/logs/trading_bot.log"
echo "   Search trading: grep -i 'buy\|sell\|executed' data/logs/trading_bot.log"
echo "   Check errors: grep 'ERROR' data/logs/trading_bot.log"

cd ..
