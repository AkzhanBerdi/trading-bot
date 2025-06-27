# trading_bot/utils/logger.py
"""Enhanced logging utilities for trading bot"""

import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class TradingBotLogger:
    """Enhanced logger for trading bot with structured logging"""
    
    def __init__(self, name: str = "trading_bot", log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Setup handlers
        self._setup_file_handler()
        self._setup_console_handler()
        self._setup_trade_handler()
        self._setup_error_handler()
    
    def _setup_file_handler(self):
        """Setup main log file handler"""
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "trading_bot.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def _setup_console_handler(self):
        """Setup console handler"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def _setup_trade_handler(self):
        """Setup dedicated trade log handler"""
        trade_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "trades.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        trade_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        trade_handler.setFormatter(formatter)
        
        # Create trade logger
        self.trade_logger = logging.getLogger("trade_logger")
        self.trade_logger.setLevel(logging.INFO)
        self.trade_logger.addHandler(trade_handler)
        self.trade_logger.propagate = False
    
    def _setup_error_handler(self):
        """Setup error-only handler"""
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s'
        )
        error_handler.setFormatter(formatter)
        
        self.logger.addHandler(error_handler)
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log trade with structured data"""
        trade_log = {
            'timestamp': datetime.now().isoformat(),
            'type': 'TRADE',
            **trade_data
        }
        
        self.trade_logger.info(json.dumps(trade_log))
    
    def log_performance(self, performance_data: Dict[str, Any]):
        """Log performance metrics"""
        perf_log = {
            'timestamp': datetime.now().isoformat(),
            'type': 'PERFORMANCE',
            **performance_data
        }
        
        self.logger.info(f"PERFORMANCE: {json.dumps(perf_log)}")
    
    def log_ai_analysis(self, analysis_data: Dict[str, Any]):
        """Log AI analysis results"""
        ai_log = {
            'timestamp': datetime.now().isoformat(),
            'type': 'AI_ANALYSIS',
            **analysis_data
        }
        
        self.logger.info(f"AI_ANALYSIS: {json.dumps(ai_log)}")
    
    def log_optimization(self, optimization_data: Dict[str, Any]):
        """Log parameter optimizations"""
        opt_log = {
            'timestamp': datetime.now().isoformat(),
            'type': 'OPTIMIZATION',
            **optimization_data
        }
        
        self.logger.info(f"OPTIMIZATION: {json.dumps(opt_log)}")
    
    def get_logger(self):
        """Get the main logger instance"""
        return self.logger

# Global logger instance
trading_logger = TradingBotLogger()
logger = trading_logger.get_logger()
