#!/bin/bash
# Clear Python Cache and Force Reload

echo "🧹 Clearing Python cache..."

# Remove Python cache directories
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "✅ Cleared __pycache__ directories"
echo "✅ Cleared .pyc files"

# Force reimport by touching the compound manager file
touch trading_bot/utils/compound_manager.py

echo "✅ Touched compound_manager.py to force reload"
echo "🔄 Python will now use updated code on next import"
