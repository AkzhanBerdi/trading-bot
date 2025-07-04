# trading_bot/config/trading_config.py
"""Simplified trading bot configuration - No AI complexity"""

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class GridTradingConfig:
    """Core grid trading configuration"""

    grid_size_percent: float = 2.0
    num_grids: int = 8
    base_order_size: float = 100.0
    max_open_orders: int = 20


@dataclass
class RiskManagementConfig:
    """Essential risk management settings"""

    max_daily_loss_percent: float = 2.0
    max_position_size_percent: float = 25.0
    stop_loss_percent: float = 5.0
    max_concurrent_trades: int = 10


@dataclass
class TradingBotConfig:
    """Simplified trading bot configuration"""

    # API Configuration
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_secret_key: str = os.getenv("BINANCE_SECRET_KEY", "")
    environment: str = os.getenv("ENVIRONMENT", "development")  # development/production

    # Trading Assets (simplified)
    grid_trading_assets: List[str] = None

    # Core Configurations
    grid_config: GridTradingConfig = None
    risk_config: RiskManagementConfig = None

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = "data/logs/trading_bot.log"

    def __post_init__(self):
        """Initialize default configurations"""
        if self.grid_trading_assets is None:
            self.grid_trading_assets = [
                "ADA",
                "AVAX",
            ]  # Match what you're actually trading

        if self.grid_config is None:
            self.grid_config = GridTradingConfig()

        if self.risk_config is None:
            self.risk_config = RiskManagementConfig()


# Global configuration instance
config = TradingBotConfig()

# Simplified asset configurations - match your actual trading pairs
ASSET_CONFIGS = {
    "ADA": {
        "grid_size_percent": 2.0,  # ✅ CHANGED: 2.5 → 2.0% spacing for ADA
        "num_grids": 8,
        "base_order_size": 100.0,
        "symbol": "ADAUSDT",
    },
    "AVAX": {
        "grid_size_percent": 2.0,  # ✅ KEPT: 2.0% spacing for AVAX
        "num_grids": 8,
        "base_order_size": 100.0,
        "symbol": "AVAXUSDT",
    },
}

# Trading pairs configuration - match your test results
TRADING_PAIRS = {"ADA": "ADAUSDT", "AVAX": "AVAXUSDT"}

# Binance API configuration
BINANCE_CONFIG = {
    "base_url": "https://api.binance.com",
    "testnet_url": "https://testnet.binance.vision",
    "timeout": 10,
    "recv_window": 5000,
}
