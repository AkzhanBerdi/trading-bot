# AI-Enhanced Crypto Trading Bot

A sophisticated cryptocurrency trading bot with AI-powered continuous learning and optimization through Model Context Protocol (MCP) integration.

## Features

🤖 **AI-Enhanced Trading**: Continuous learning and parameter optimization  
📊 **Grid Trading**: Automated grid strategies for SOL and AVAX  
🎯 **Signal-Based Trading**: RENDER token signal analysis and portfolio rebalancing  
🔗 **MCP Integration**: Connect to Claude/ChatGPT for intelligent analysis  
📈 **Performance Tracking**: Comprehensive metrics and reporting  
⚠️ **Risk Management**: Adaptive risk controls and monitoring  
📱 **Real-time Monitoring**: Live performance and health monitoring  

## Quick Start

### 1. Installation

```bash
# Clone and navigate to project
cd ~/crypto-trading/trading-bot

# Install all dependencies
uv sync

# Setup data directories and initial files
uv run python trading_bot/scripts/setup_data_dirs.py
```

### 2. Configuration

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

Add your Binance API credentials:
```env
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
ENVIRONMENT=development  # Use 'production' for live trading
LOG_LEVEL=INFO

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Test Setup

```bash
# Test all components
uv run python trading_bot/scripts/test_all.py

# Test Binance connection
uv run python trading_bot/utils/binance_client.py

# Monitor bot health
uv run python trading_bot/scripts/monitor_bot.py
```

## Usage

### Basic Trading Bot (No AI)

```bash
# Run the basic rule-based trading bot
uv run python trading_bot/main.py
```

### AI-Enhanced Trading Bot

```bash
# Terminal 1: Start MCP server
uv run python trading_bot/scripts/start_mcp_server.py

# Terminal 2: Run AI-enhanced bot
uv run python trading_bot/scripts/run_ai_bot.py

# Terminal 3: Monitor performance
uv run python trading_bot/scripts/monitor_bot.py --continuous
```

### Performance Analysis

```bash
# Analyze recent performance
uv run python trading_bot/scripts/analyze_performance.py --days 30

# Compare strategies
uv run python trading_bot/scripts/analyze_performance.py --compare

# Monitor portfolio
uv run python trading_bot/scripts/monitor_bot.py --portfolio
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Trading Bot   │◄──►│   MCP Server    │◄──►│ Claude/ChatGPT  │
│                 │    │                 │    │                 │
│ • Grid Trading  │    │ • Market Data   │    │ • Analysis      │
│ • RENDER Signals│    │ • Performance   │    │ • Optimization  │
│ • Risk Mgmt     │    │ • Tools/Resources│    │ • Suggestions   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Binance API    │    │ Performance DB  │    │ Learning Engine │
│                 │    │                 │    │                 │
│ • Price Data    │    │ • Trades        │    │ • Track Results │
│ • Order Exec    │    │ • Metrics       │    │ • Improve AI    │
│ • Account Info  │    │ • Optimizations │    │ • Meta-learning │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Configuration

### Trading Parameters

Edit `trading_bot/config/trading_config.py`:

```python
# Grid trading settings
ASSET_CONFIGS = {
    'SOL': {
        'grid_size_percent': 2.0,      # 2% between levels
        'num_grids': 8,                # 8 levels each direction
        'base_order_size': 50.0,       # $50 per order
    },
    'AVAX': {
        'grid_size_percent': 2.5,      # 2.5% between levels  
        'num_grids': 8,
        'base_order_size': 50.0,
    }
}

# RENDER signal settings
RENDER_CONFIG = {
    'rebalance_threshold': 0.75,       # 75% confidence required
    'max_allocation_percent': 40.0,    # Max 40% in RENDER
    'min_allocation_percent': 5.0,     # Min 5% in RENDER
}
```

### AI Settings

Edit `config/ai_settings.json`:

```json
{
  "learning_parameters": {
    "optimization_confidence_threshold": 0.7,
    "max_parameter_change_percent": 50,
    "learning_lookback_days": 30
  },
  "risk_controls": {
    "max_ai_suggested_position_size": 100,
    "ai_suggestion_cooldown_hours": 6,
    "human_approval_required_for": [
      "risk_optimization", 
      "major_parameter_changes"
    ]
  }
}
```

## Trading Strategies

### 1. Grid Trading (SOL/AVAX)
- **Automatic buy orders** below current price
- **Automatic sell orders** above current price  
- **Profits from volatility** in ranging markets
- **AI optimization** of grid spacing and levels

### 2. Signal-Based Trading (RENDER)
- **Technical analysis** using RSI, Bollinger Bands, volume
- **Portfolio rebalancing** based on signal strength
- **AI enhancement** of signal interpretation
- **News sentiment integration**

### 3. Risk Management
- **Position size limits** (max 25% per asset)
- **Daily loss limits** (max 2% portfolio drawdown)
- **Correlation monitoring** between assets
- **Dynamic adjustment** based on market conditions

## AI Enhancement Features

### Continuous Learning
- **Daily market analysis** and regime detection
- **Parameter optimization** based on performance  
- **Strategy adaptation** to changing market conditions
- **News sentiment integration** for better timing

### Performance Tracking
- **Trade-by-trade analysis** and learning
- **Strategy effectiveness** measurement
- **AI suggestion accuracy** tracking
- **Meta-learning** for improving AI over time

### MCP Integration
- **Real-time market analysis** from Claude/ChatGPT
- **Parameter optimization suggestions**
- **Risk assessment** and recommendations
- **Portfolio rebalancing** guidance

## Monitoring & Alerts

### Health Monitoring
```bash
# Check bot status
uv run python trading_bot/scripts/monitor_bot.py

# Continuous monitoring
uv run python trading_bot/scripts/monitor_bot.py --continuous

# Performance analysis
uv run python trading_bot/scripts/analyze_performance.py
```

### Log Files
- `data/logs/trading_bot.log` - Main bot activity
- `data/logs/trades.log` - Trade execution logs
- `data/logs/errors.log` - Error and exception logs

### Performance Data
- `data/performance/trades.json` - All completed trades
- `data/performance/portfolio_history.json` - Portfolio snapshots
- `data/performance/performance_metrics.json` - Calculated metrics

## Production Deployment

### 1. Setup Systemd Services
```bash
# Copy service files
sudo cp scripts/*.service /etc/systemd/system/

# Enable services
sudo systemctl enable trading-mcp-server ai-trading-bot

# Start services
sudo systemctl start trading-mcp-server ai-trading-bot

# Check status
sudo systemctl status trading-mcp-server ai-trading-bot
```

### 2. Monitoring in Production
```bash
# View logs
sudo journalctl -u ai-trading-bot -f

# Monitor performance
uv run python trading_bot/scripts/monitor_bot.py --continuous

# Restart if needed
sudo systemctl restart ai-trading-bot
```

## Safety & Risk Management

### Built-in Safety Features
- 🔒 **Testnet mode** for safe testing
- 📊 **Paper trading** simulation
- ⚠️ **Position limits** and stop losses
- 🛡️ **AI confidence thresholds** before applying changes
- 🔄 **Rollback capability** for failed optimizations

### Risk Controls
- **Maximum daily loss**: 2% of portfolio
- **Position size limit**: 25% per asset
- **AI change limits**: Max 50% parameter adjustments
- **Human approval**: Required for major changes
- **Correlation monitoring**: Prevent overexposure

## Troubleshooting

### Common Issues

**1. Binance Connection Failed**
```bash
# Check API keys in .env file
# Verify IP whitelist on Binance
# Test connection manually
uv run python trading_bot/utils/binance_client.py
```

**2. No Trading Activity**
```bash
# Check if in testnet mode (ENVIRONMENT=development)
# Verify sufficient balance for trading
# Check grid setup and price levels
uv run python trading_bot/scripts/monitor_bot.py
```

**3. AI Features Not Working**
```bash
# Check MCP server is running
curl http://localhost:8080/health

# Verify AI configuration
cat config/ai_settings.json

# Check learning history
ls data/learning_history/
```

**4. Performance Issues**
```bash
# Check system resources
htop

# Monitor log file sizes
du -sh data/logs/

# Clear old logs if needed
find data/logs/ -name "*.log" -mtime +30 -delete
```

### Getting Help

1. **Check logs**: `tail -f data/logs/trading_bot.log`
2. **Run diagnostics**: `uv run python trading_bot/scripts/test_all.py`
3. **Monitor health**: `uv run python trading_bot/scripts/monitor_bot.py`
4. **Review configuration**: Verify `.env` and config files

## Development

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_grid_trading.py

# Run with coverage
uv run pytest --cov=trading_bot
```

### Code Quality
```bash
# Format code
uv run black trading_bot/

# Check style
uv run flake8 trading_bot/

# Type checking
uv run mypy trading_bot/
```

### Adding New Features
1. **Create feature branch**: `git checkout -b feature/new-strategy`
2. **Implement changes** in appropriate modules
3. **Add tests** in `tests/` directory
4. **Update configuration** if needed
5. **Test thoroughly** before deployment

## License

This project is for educational and personal use only. Use at your own risk. 
Not financial advice. Always test thoroughly before using real funds.

## Disclaimer

⚠️ **Important**: This trading bot involves financial risk. Never trade with money you can't afford to lose. Always test in development/testnet mode first. The AI suggestions are experimental and should be validated before implementation. Past performance does not guarantee future results.
