#!/bin/bash
# Fix Stuck Bot Issues
# Resolve .env path issue and restart bot properly

echo "🔧 Fixing Stuck Trading Bot"
echo "=========================="

# 1. Kill the stuck bot process
echo "1️⃣ Stopping stuck bot process..."
pkill -f "python.*main.py"
sleep 2

# Check if process is gone
if pgrep -f "python.*main.py" > /dev/null; then
    echo "   ⚠️  Bot process still running, force killing..."
    pkill -9 -f "python.*main.py"
    sleep 2
else
    echo "   ✅ Bot process stopped"
fi

# 2. Fix .env file location
echo ""
echo "2️⃣ Fixing .env file location..."

if [ -f ".env" ] && [ ! -f "trading_bot/.env" ]; then
    echo "   📋 Copying .env to trading_bot directory..."
    cp .env trading_bot/.env
    echo "   ✅ .env copied to trading_bot/.env"
elif [ -f "trading_bot/.env" ]; then
    echo "   ✅ .env already exists in trading_bot/"
else
    echo "   ❌ No .env file found - create one first!"
    exit 1
fi

# 3. Clear old log to see fresh activity
echo ""
echo "3️⃣ Preparing fresh logs..."

if [ -f "trading_bot/data/logs/trading_bot.log" ]; then
    # Backup old log
    timestamp=$(date +%Y%m%d_%H%M%S)
    cp trading_bot/data/logs/trading_bot.log trading_bot/data/logs/trading_bot_backup_$timestamp.log
    echo "   📋 Backed up old log to trading_bot_backup_$timestamp.log"
    
    # Clear current log for fresh start
    > trading_bot/data/logs/trading_bot.log
    echo "   🗑️  Cleared log file for fresh start"
fi

# 4. Test environment before starting
echo ""
echo "4️⃣ Testing environment..."

cd trading_bot

# Test if .env loads properly
if python3 -c "
import os
from pathlib import Path
from dotenv import load_dotenv

# Try to load .env
env_loaded = False
for env_path in ['.env', '../.env']:
    if Path(env_path).exists():
        load_dotenv(env_path)
        print(f'   ✅ Loaded .env from: {env_path}')
        env_loaded = True
        break

if not env_loaded:
    print('   ❌ Could not load .env file')
    exit(1)

# Check if required variables exist
required_vars = ['BINANCE_API_KEY', 'BINANCE_API_SECRET', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
missing_vars = []

for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f'   ❌ Missing environment variables: {missing_vars}')
else:
    print('   ✅ All required environment variables found')
"; then
    echo "   ✅ Environment test passed"
else
    echo "   ❌ Environment test failed"
    cd ..
    exit 1
fi

# 5. Start bot with monitoring
echo ""
echo "5️⃣ Starting bot with monitoring..."

echo "   🚀 Starting trading bot..."
echo "   📊 Monitor logs in another terminal with:"
echo "      tail -f trading_bot/data/logs/trading_bot.log"
echo ""
echo "   🔍 Starting bot now..."

# Start bot in background but show initial output
python3 main.py &
bot_pid=$!

echo "   ✅ Bot started with PID: $bot_pid"

# Monitor for first few seconds
echo ""
echo "6️⃣ Initial startup check (10 seconds)..."
sleep 10

if ps -p $bot_pid > /dev/null; then
    echo "   ✅ Bot is running successfully"
    
    # Check if logs are being generated
    if [ -s "data/logs/trading_bot.log" ]; then
        echo "   ✅ New logs are being generated"
        echo ""
        echo "📝 Recent log entries:"
        tail -5 data/logs/trading_bot.log | while read line; do
            if echo "$line" | grep -q "ERROR"; then
                echo "      ❌ $line"
            elif echo "$line" | grep -q "WARNING"; then
                echo "      ⚠️  $line"
            elif echo "$line" | grep -q "compound\|profit\|order.*size"; then
                echo "      💰 $line"
            else
                echo "      ℹ️  $line"
            fi
        done
    else
        echo "   ⚠️  No new logs yet - may need more time"
    fi
else
    echo "   ❌ Bot failed to start or crashed"
fi

cd ..

echo ""
echo "🎯 Next Steps:"
echo "1. Monitor logs: tail -f trading_bot/data/logs/trading_bot.log"
echo "2. Check for compound interest: grep 'compound\|multiplier' trading_bot/data/logs/trading_bot.log"
echo "3. Watch for trading activity: grep 'BUY\|SELL\|executed' trading_bot/data/logs/trading_bot.log"
echo ""
echo "✅ Bot fix complete!"
