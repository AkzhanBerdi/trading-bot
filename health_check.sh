#!/bin/bash
# Bot Health Diagnostic Script
# Check why bot has been failing

echo "🔍 Trading Bot Health Diagnostic"
echo "==============================="

# 1. Check if bot is currently running
echo "1️⃣ Bot Process Check:"
bot_processes=$(ps aux | grep -v grep | grep -c "python.*main.py\|trading.*bot")
if [ "$bot_processes" -gt 0 ]; then
    echo "   ✅ Bot is currently running ($bot_processes processes)"
    ps aux | grep -v grep | grep "python.*main.py\|trading.*bot"
else
    echo "   ❌ Bot is NOT running"
fi

echo ""

# 2. Network connectivity
echo "2️⃣ Network Connectivity:"

# Test basic internet
if ping -c 1 google.com >/dev/null 2>&1; then
    echo "   ✅ Internet connection working"
else
    echo "   ❌ No internet connection"
fi

# Test Binance API specifically
if ping -c 1 api.binance.com >/dev/null 2>&1; then
    echo "   ✅ Can reach api.binance.com"
else
    echo "   ❌ Cannot reach api.binance.com"
fi

# Test API endpoint
api_response=$(curl -s --max-time 5 "https://api.binance.com/api/v3/ping" 2>/dev/null)
if [ "$api_response" = "{}" ]; then
    echo "   ✅ Binance API responding"
else
    echo "   ❌ Binance API not responding"
fi

echo ""

# 3. Check environment and files
echo "3️⃣ Environment Check:"

if [ -f "trading_bot/.env" ]; then
    echo "   ✅ .env file exists"
    # Check if API keys are set (without showing them)
    if grep -q "API_KEY=" "trading_bot/.env" && grep -q "API_SECRET=" "trading_bot/.env"; then
        echo "   ✅ API keys configured in .env"
    else
        echo "   ❌ API keys missing from .env"
    fi
else
    echo "   ❌ .env file missing"
fi

if [ -f "trading_bot/data/trading_history.db" ]; then
    echo "   ✅ Database file exists"
    db_size=$(du -h trading_bot/data/trading_history.db | cut -f1)
    echo "      Database size: $db_size"
else
    echo "   ❌ Database file missing"
fi

echo ""

# 4. Recent error analysis
echo "4️⃣ Recent Error Analysis:"

if [ -f "trading_bot/data/logs/trading_bot.log" ]; then
    log_size=$(du -h trading_bot/data/logs/trading_bot.log | cut -f1)
    echo "   📁 Log file size: $log_size"
    
    # Check last few lines for immediate issues
    echo "   📝 Last 5 log entries:"
    tail -5 trading_bot/data/logs/trading_bot.log | while read line; do
        if echo "$line" | grep -q "ERROR"; then
            echo "      ❌ $line"
        elif echo "$line" | grep -q "WARNING"; then
            echo "      ⚠️  $line"
        else
            echo "      ℹ️  $line"
        fi
    done
    
    # Count recent errors
    recent_errors=$(grep "$(date '+%Y-%m-%d')" trading_bot/data/logs/trading_bot.log 2>/dev/null | grep -c "ERROR" || echo 0)
    echo "   🔥 Errors today: $recent_errors"
    
else
    echo "   ❌ Log file not found"
fi

echo ""

# 5. System resources
echo "5️⃣ System Resources:"

# Check disk space
disk_usage=$(df -h . | tail -1 | awk '{print $5}')
echo "   💾 Disk usage: $disk_usage"

# Check memory
if command -v free >/dev/null; then
    memory_usage=$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')
    echo "   🧠 Memory usage: $memory_usage"
fi

# Check load average
if [ -f /proc/loadavg ]; then
    load_avg=$(cat /proc/loadavg | cut -d' ' -f1-3)
    echo "   ⚡ Load average: $load_avg"
fi

echo ""

# 6. Recommendations
echo "6️⃣ Recommendations:"

if [ "$bot_processes" -eq 0 ]; then
    echo "   🔧 Bot is not running - start it with:"
    echo "      cd trading_bot && python main.py"
fi

if ! ping -c 1 api.binance.com >/dev/null 2>&1; then
    echo "   🌐 Fix network connectivity to api.binance.com"
    echo "      - Check firewall settings"
    echo "      - Verify DNS configuration"
    echo "      - Check if ISP blocks Binance"
fi

if [ "$recent_errors" -gt 10 ]; then
    echo "   🔥 High error count ($recent_errors today)"
    echo "      - Check API key validity"
    echo "      - Review connection stability"
    echo "      - Consider increasing timeouts"
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Fix connectivity issues if any"
echo "2. Restart bot: cd trading_bot && python main.py"
echo "3. Monitor logs: tail -f trading_bot/data/logs/trading_bot.log"
echo "4. Verify trading activity resumes"
