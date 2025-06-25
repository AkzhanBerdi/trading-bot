# trading_bot/utils/performance_tracker.py
"""Performance tracking and metrics calculation"""

import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

class PerformanceTracker:
    """Track and analyze trading performance"""
    
    def __init__(self, data_dir: str = "data/performance"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Performance data storage
        self.trades_file = self.data_dir / "trades.json"
        self.portfolio_file = self.data_dir / "portfolio_history.json"
        self.metrics_file = self.data_dir / "performance_metrics.json"
        
        # Initialize files if they don't exist
        self._initialize_files()
    
    def _initialize_files(self):
        """Initialize performance tracking files"""
        
        for file_path in [self.trades_file, self.portfolio_file, self.metrics_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def record_trade(self, trade_data: Dict):
        """Record a completed trade"""
        
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': trade_data.get('symbol'),
            'side': trade_data.get('side'),  # BUY/SELL
            'quantity': trade_data.get('quantity'),
            'price': trade_data.get('price'),
            'value': trade_data.get('quantity', 0) * trade_data.get('price', 0),
            'strategy': trade_data.get('strategy'),  # grid/signal/rebalance
            'fees': trade_data.get('fees', 0),
            'pnl': trade_data.get('pnl', 0),
            'portfolio_value_before': trade_data.get('portfolio_value_before'),
            'portfolio_value_after': trade_data.get('portfolio_value_after')
        }
        
        try:
            # Load existing trades
            with open(self.trades_file, 'r') as f:
                trades = json.load(f)
            
            # Add new trade
            trades.append(trade_record)
            
            # Save updated trades
            with open(self.trades_file, 'w') as f:
                json.dump(trades, f, indent=2)
            
            self.logger.info(f"Recorded trade: {trade_record['side']} {trade_record['symbol']}")
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
    
    def record_portfolio_snapshot(self, portfolio_data: Dict):
        """Record portfolio snapshot"""
        
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'total_value': portfolio_data.get('total_value'),
            'assets': portfolio_data.get('assets', {}),
            'daily_pnl': portfolio_data.get('daily_pnl', 0),
            'unrealized_pnl': portfolio_data.get('unrealized_pnl', 0)
        }
        
        try:
            # Load existing snapshots
            with open(self.portfolio_file, 'r') as f:
                snapshots = json.load(f)
            
            # Add new snapshot
            snapshots.append(snapshot)
            
            # Keep only last 1000 snapshots to manage file size
            if len(snapshots) > 1000:
                snapshots = snapshots[-1000:]
            
            # Save updated snapshots
            with open(self.portfolio_file, 'w') as f:
                json.dump(snapshots, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error recording portfolio snapshot: {e}")
    
    def calculate_performance_metrics(self, days: int = 30) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        try:
            # Load trades and portfolio data
            with open(self.trades_file, 'r') as f:
                trades = json.load(f)
            
            with open(self.portfolio_file, 'r') as f:
                snapshots = json.load(f)
            
            # Filter by time period
            cutoff_date = datetime.now() - timedelta(days=days)
            
            recent_trades = [
                t for t in trades 
                if datetime.fromisoformat(t['timestamp']) >= cutoff_date
            ]
            
            recent_snapshots = [
                s for s in snapshots
                if datetime.fromisoformat(s['timestamp']) >= cutoff_date
            ]
            
            if not recent_snapshots:
                return {"error": "No data available for the specified period"}
            
            # Calculate metrics
            metrics = {
                'period_days': days,
                'total_trades': len(recent_trades),
                'total_return': self._calculate_total_return(recent_snapshots),
                'sharpe_ratio': self._calculate_sharpe_ratio(recent_snapshots),
                'max_drawdown': self._calculate_max_drawdown(recent_snapshots),
                'win_rate': self._calculate_win_rate(recent_trades),
                'profit_factor': self._calculate_profit_factor(recent_trades),
                'avg_trade_return': self._calculate_avg_trade_return(recent_trades),
                'volatility': self._calculate_volatility(recent_snapshots),
                'calmar_ratio': self._calculate_calmar_ratio(recent_snapshots),
                'strategy_breakdown': self._calculate_strategy_breakdown(recent_trades)
            }
            
            # Save metrics
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_total_return(self, snapshots: List[Dict]) -> float:
        """Calculate total return percentage"""
        if len(snapshots) < 2:
            return 0.0
        
        start_value = snapshots[0]['total_value']
        end_value = snapshots[-1]['total_value']
        
        if start_value == 0:
            return 0.0
        
        return ((end_value - start_value) / start_value) * 100
    
    def _calculate_sharpe_ratio(self, snapshots: List[Dict]) -> float:
        """Calculate Sharpe ratio (assuming 0% risk-free rate)"""
        if len(snapshots) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i-1]['total_value']
            curr_value = snapshots[i]['total_value']
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming daily returns)
        return (mean_return / std_return) * np.sqrt(365)
    
    def _calculate_max_drawdown(self, snapshots: List[Dict]) -> float:
        """Calculate maximum drawdown percentage"""
        if len(snapshots) < 2:
            return 0.0
        
        values = [s['total_value'] for s in snapshots]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = ((peak - value) / peak) * 100
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate percentage"""
        if not trades:
            return 0.0
        
        profitable_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
        return (profitable_trades / len(trades)) * 100
    
    def _calculate_profit_factor(self, trades: List[Dict]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        if not trades:
            return 0.0
        
        gross_profit = sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) > 0)
        gross_loss = abs(sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def _calculate_avg_trade_return(self, trades: List[Dict]) -> float:
        """Calculate average trade return percentage"""
        if not trades:
            return 0.0
        
        total_pnl = sum(trade.get('pnl', 0) for trade in trades)
        return total_pnl / len(trades)
    
    def _calculate_volatility(self, snapshots: List[Dict]) -> float:
        """Calculate annualized volatility"""
        if len(snapshots) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i-1]['total_value']
            curr_value = snapshots[i]['total_value']
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        return np.std(returns) * np.sqrt(365) * 100  # Annualized percentage
    
    def _calculate_calmar_ratio(self, snapshots: List[Dict]) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)"""
        total_return = self._calculate_total_return(snapshots)
        max_drawdown = self._calculate_max_drawdown(snapshots)
        
        if max_drawdown == 0:
            return float('inf') if total_return > 0 else 0.0
        
        # Annualize the return
        days = len(snapshots)
        if days == 0:
            return 0.0
        
        annual_return = total_return * (365 / days)
        return annual_return / max_drawdown
    
    def _calculate_strategy_breakdown(self, trades: List[Dict]) -> Dict:
        """Calculate performance breakdown by strategy"""
        
        strategies = {}
        
        for trade in trades:
            strategy = trade.get('strategy', 'unknown')
            if strategy not in strategies:
                strategies[strategy] = {
                    'trades': 0,
                    'total_pnl': 0,
                    'wins': 0,
                    'losses': 0
                }
            
            strategies[strategy]['trades'] += 1
            strategies[strategy]['total_pnl'] += trade.get('pnl', 0)
            
            if trade.get('pnl', 0) > 0:
                strategies[strategy]['wins'] += 1
            elif trade.get('pnl', 0) < 0:
                strategies[strategy]['losses'] += 1
        
        # Calculate win rates
        for strategy_data in strategies.values():
            total_trades = strategy_data['trades']
            if total_trades > 0:
                strategy_data['win_rate'] = (strategy_data['wins'] / total_trades) * 100
            else:
                strategy_data['win_rate'] = 0.0
        
        return strategies
