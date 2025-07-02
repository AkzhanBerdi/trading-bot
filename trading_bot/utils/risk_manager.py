# trading_bot/utils/risk_manager.py - MINIMAL VERSION
"""Minimal Risk Manager - Essential Safety Only"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Tuple


class TradingMode(Enum):
    NORMAL = "NORMAL"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class RiskConfig:
    """Minimal risk configuration - essential limits only"""

    max_daily_loss_percent: float = 2.0  # Stop at 2% daily loss
    max_daily_trades: int = 50  # Prevent overtrading
    emergency_stop_loss: float = 10.0  # Emergency circuit breaker


class RiskManager:
    """Minimal risk management - essential safety only"""

    def __init__(self, db_logger, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.db_logger = db_logger
        self.logger = logging.getLogger(f"{__name__}")

        # Simple state tracking
        self.current_mode = TradingMode.NORMAL
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        self.portfolio_value = 1000.0  # Default value

        self.logger.info("🛡️ Minimal Risk Manager initialized")

    def update_portfolio_value(self, new_value: float) -> None:
        """Update portfolio value - MINIMAL"""
        self.portfolio_value = new_value

    def update_daily_pnl(self, trade_pnl: float) -> None:
        """Update daily P&L - SIMPLIFIED"""
        # Reset daily counters if new day
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trade_count = 0
            self.last_reset_date = today
            self.logger.info("📅 Daily counters reset")

        self.daily_pnl += trade_pnl
        self.daily_trade_count += 1

    def check_trade_permission(
        self, trade_type: str, trade_value: float
    ) -> Tuple[bool, str]:
        """Check if trade is allowed - SIMPLIFIED"""

        # Emergency stop check
        if self.current_mode == TradingMode.EMERGENCY_STOP:
            return False, "🚨 EMERGENCY STOP - All trading halted"

        # Daily trade limit
        if self.daily_trade_count >= self.config.max_daily_trades:
            return (
                False,
                f"📊 Daily trade limit reached ({self.config.max_daily_trades})",
            )

        # Daily loss limit
        if self.daily_pnl <= -abs(self.config.max_daily_loss_percent):
            self.trigger_emergency_stop()
            return (
                False,
                f"📉 Daily loss limit reached ({self.config.max_daily_loss_percent}%)",
            )

        return True, "✅ Trade approved"

    def trigger_emergency_stop(self) -> None:
        """Trigger emergency stop - SIMPLIFIED"""
        self.current_mode = TradingMode.EMERGENCY_STOP
        self.logger.error("🚨 EMERGENCY STOP ACTIVATED")

        self.db_logger.log_bot_event(
            "EMERGENCY_STOP",
            f"Emergency stop - daily P&L: {self.daily_pnl:.2f}%",
            "CRITICAL",
            {"daily_pnl": self.daily_pnl, "trade_count": self.daily_trade_count},
            None,
        )

    def reset_to_normal(self) -> None:
        """Reset to normal mode - SIMPLIFIED"""
        self.current_mode = TradingMode.NORMAL
        self.logger.info("✅ Reset to NORMAL mode")

        self.db_logger.log_bot_event(
            "RISK_RESET",
            "Reset to normal trading mode",
            "INFO",
            {"previous_pnl": self.daily_pnl},
            None,
        )

    def get_risk_status(self) -> Dict:
        """Get current risk status - MINIMAL INFO"""
        return {
            "mode": self.current_mode.value,
            "daily_pnl": round(self.daily_pnl, 2),
            "max_drawdown": 0.0,  # Simplified - not tracking complex drawdown
            "daily_trades": self.daily_trade_count,
            "portfolio_value": round(self.portfolio_value, 2),
            "risk_limits": {
                "daily_loss_limit": self.config.max_daily_loss_percent,
                "max_drawdown_limit": 8.0,  # Static value for compatibility
                "daily_trade_limit": self.config.max_daily_trades,
                "emergency_stop": self.config.emergency_stop_loss,
            },
        }
