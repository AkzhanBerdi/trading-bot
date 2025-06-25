# trading_bot/scripts/setup_data_dirs.py
#!/usr/bin/env python3
"""Setup data directories and initial files"""

import json
from pathlib import Path
from datetime import datetime

def setup_directories():
    """Create necessary data directories"""
    
    directories = [
        "data/logs",
        "data/performance", 
        "data/optimizations",
        "data/learning_history",
        "data/market_data",
        "data/news",
        "config"
    ]
    
    print("📁 Setting up data directories...")
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created: {dir_path}")
    
    # Create initial data files
    setup_initial_files()

def setup_initial_files():
    """Create initial data files"""
    
    print("\n📄 Creating initial data files...")
    
    # Performance tracking files
    performance_files = [
        "data/performance/trades.json",
        "data/performance/portfolio_history.json", 
        "data/performance/performance_metrics.json"
    ]
    
    for file_path in performance_files:
        if not Path(file_path).exists():
            with open(file_path, 'w') as f:
                json.dump([], f)
            print(f"  ✅ Created: {file_path}")
    
    # Learning history file
    learning_file = "data/learning_history/ai_optimizations.json"
    if not Path(learning_file).exists():
        with open(learning_file, 'w') as f:
            json.dump({
                "created": datetime.now().isoformat(),
                "optimizations": [],
                "performance_tracking": []
            }, f, indent=2)
        print(f"  ✅ Created: {learning_file}")
    
    # Market data cache
    market_data_file = "data/market_data/cache.json"
    if not Path(market_data_file).exists():
        with open(market_data_file, 'w') as f:
            json.dump({
                "last_updated": datetime.now().isoformat(),
                "price_data": {},
                "news_data": []
            }, f, indent=2)
        print(f"  ✅ Created: {market_data_file}")

def create_systemd_services():
    """Create systemd service files for production deployment"""
    
    print("\n🚀 Creating systemd service files...")
    
    # MCP Server service
    mcp_service = """[Unit]
Description=Trading Bot MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto-trading/trading-bot
Environment=PATH=/home/ubuntu/.cargo/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/.cargo/bin/uv run python trading_bot/scripts/start_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    # AI Trading Bot service
    ai_bot_service = """[Unit]
Description=AI Enhanced Trading Bot
After=network.target
Requires=trading-mcp-server.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto-trading/trading-bot
Environment=PATH=/home/ubuntu/.cargo/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/.cargo/bin/uv run python trading_bot/scripts/run_ai_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    # Save service files
    with open("scripts/trading-mcp-server.service", 'w') as f:
        f.write(mcp_service)
    print("  ✅ Created: scripts/trading-mcp-server.service")
    
    with open("scripts/ai-trading-bot.service", 'w') as f:
        f.write(ai_bot_service)
    print("  ✅ Created: scripts/ai-trading-bot.service")
    
    print("\n📋 To install services:")
    print("  sudo cp scripts/*.service /etc/systemd/system/")
    print("  sudo systemctl enable trading-mcp-server ai-trading-bot")
    print("  sudo systemctl start trading-mcp-server ai-trading-bot")

def main():
    """Main setup function"""
    
    print("🛠️  Trading Bot Setup")
    print("=" * 30)
    
    setup_directories()
    create_systemd_services()
    
    print(f"\n✅ Setup complete!")
    print(f"\nNext steps:")
    print(f"1. Update .env file with your API keys")
    print(f"2. Test components: uv run python trading_bot/scripts/test_all.py")
    print(f"3. Start MCP server: uv run python trading_bot/scripts/start_mcp_server.py")
    print(f"4. Run AI bot: uv run python trading_bot/scripts/run_ai_bot.py")

if __name__ == "__main__":
    main()
