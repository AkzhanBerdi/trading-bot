# trading_bot/config/trading_config.py
"""Trading bot configuration settings"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class GridTradingConfig:
    """Grid trading configuration"""
    grid_size_percent: float = 2.0
    num_grids: int = 8
    base_order_size: float = 50.0
    max_open_orders: int = 20

@dataclass
class RenderSignalConfig:
    """RENDER signal trading configuration"""
    rebalance_threshold: float = 0.75
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    bb_period: int = 20
    bb_std: float = 2.0
    volume_spike_threshold: float = 2.0

@dataclass
class RiskManagementConfig:
    """Risk management configuration"""
    max_daily_loss_percent: float = 2.0
    max_position_size_percent: float = 25.0
    stop_loss_percent: float = 5.0
    max_concurrent_trades: int = 10
    max_correlation_exposure: float = 0.8

@dataclass
class AIConfig:
    """AI enhancement configuration"""
    enabled: bool = True
    confidence_threshold: float = 0.7
    max_parameter_change_percent: float = 50.0
    learning_lookback_days: int = 30
    min_trades_for_optimization: int = 20
    real_time_analysis_interval_minutes: int = 15
    daily_analysis_hour: int = 6

@dataclass
class MCPConfig:
    """MCP server configuration"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8080
    max_connections: int = 10

@dataclass
class TradingBotConfig:
    """Main trading bot configuration"""
    
    # API Configuration
    binance_api_key: str = os.getenv('BINANCE_API_KEY', '')
    binance_secret_key: str = os.getenv('BINANCE_SECRET_KEY', '')
    environment: str = os.getenv('ENVIRONMENT', 'development')  # development/production
    
    # Trading Assets
    grid_trading_assets: List[str] = None
    signal_trading_assets: List[str] = None
    hold_assets: List[str] = None
    
    # Component Configurations
    grid_config: GridTradingConfig = None
    render_config: RenderSignalConfig = None
    risk_config: RiskManagementConfig = None
    ai_config: AIConfig = None
    mcp_config: MCPConfig = None
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = 'data/logs/trading_bot.log'
    
    def __post_init__(self):
        """Initialize default configurations"""
        if self.grid_trading_assets is None:
            self.grid_trading_assets = ['SOL', 'AVAX']
        
        if self.signal_trading_assets is None:
            self.signal_trading_assets = ['RENDER']
        
        if self.hold_assets is None:
            self.hold_assets = ['NEAR']
        
        if self.grid_config is None:
            self.grid_config = GridTradingConfig()
        
        if self.render_config is None:
            self.render_config = RenderSignalConfig()
        
        if self.risk_config is None:
            self.risk_config = RiskManagementConfig()
        
        if self.ai_config is None:
            self.ai_config = AIConfig()
        
        if self.mcp_config is None:
            self.mcp_config = MCPConfig()

# Global configuration instance
config = TradingBotConfig()

# Asset-specific configurations
ASSET_CONFIGS = {
    'SOL': {
        'grid_size_percent': 2.0,
        'num_grids': 8,
        'base_order_size': 50.0,
        'symbol': 'SOLUSDT'
    },
    'AVAX': {
        'grid_size_percent': 2.5,
        'num_grids': 8,
        'base_order_size': 50.0,
        'symbol': 'AVAXUSDT'
    },
    'RENDER': {
        'rebalance_threshold': 0.75,
        'max_allocation_percent': 40.0,
        'min_allocation_percent': 5.0,
        'symbol': 'RENDERUSDT'
    },
    'NEAR': {
        'hold_strategy': True,
        'rebalance_only': True,
        'symbol': 'NEARUSDT'
    }
}

# Trading pairs configuration
TRADING_PAIRS = {
    'SOL': 'SOLUSDT',
    'AVAX': 'AVAXUSDT', 
    'RENDER': 'RENDERUSDT',
    'NEAR': 'NEARUSDT',
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT'
}

# Binance API configuration
BINANCE_CONFIG = {
    'base_url': 'https://api.binance.com',
    'testnet_url': 'https://testnet.binance.vision',
    'timeout': 10,
    'recv_window': 5000
}

# MCP Tools configuration
MCP_TOOLS = [
    'get_portfolio_status',
    'get_market_analysis', 
    'get_trading_performance',
    'analyze_render_signals',
    'get_recent_news_impact',
    'simulate_parameter_change',
    'get_risk_metrics'
]

# MCP Resources configuration
MCP_RESOURCES = [
    'trading_logs',
    'grid_trading_status',
    'performance_history',
    'optimization_history'
]
