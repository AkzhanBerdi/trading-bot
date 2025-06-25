# src/trading_bot/mcp/trading_mcp_server.py
"""
MCP Server for Trading Bot - Connects Claude/ChatGPT to trading data and analysis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# MCP imports (would need to install: uv add mcp)
try:
    from mcp import MCPServer, Tool, Resource
    from mcp.types import TextContent, EmbeddedResource
except ImportError:
    print("MCP not installed. Run: uv add mcp")
    exit(1)

class TradingMCPServer:
    """MCP Server that provides trading data and analysis to LLMs"""
    
    def __init__(self, trading_bot):
        self.trading_bot = trading_bot
        self.server = MCPServer("trading-bot")
        self.logger = logging.getLogger(__name__)
        
        # Register tools and resources
        self.register_tools()
        self.register_resources()
        
    def register_tools(self):
        """Register MCP tools for LLM interaction"""
        
        @self.server.tool("get_portfolio_status")
        async def get_portfolio_status() -> str:
            """Get current portfolio status and performance"""
            try:
                portfolio, total_value = await self.trading_bot.get_portfolio_status()
                
                status = {
                    "total_portfolio_value": total_value,
                    "assets": portfolio,
                    "last_updated": datetime.now().isoformat(),
                    "daily_pnl": await self.get_daily_pnl(),
                    "total_trades_today": self.trading_bot.daily_trades
                }
                
                return json.dumps(status, indent=2)
            except Exception as e:
                return f"Error getting portfolio status: {e}"
        
        @self.server.tool("get_market_analysis")
        async def get_market_analysis(assets: str = "SOL,AVAX,RENDER,NEAR") -> str:
            """Get comprehensive market analysis for specified assets"""
            try:
                asset_list = assets.split(',')
                analysis = {}
                
                for asset in asset_list:
                    asset = asset.strip()
                    price = self.trading_bot.binance.get_price(f"{asset}USDT")
                    klines = self.trading_bot.binance.get_klines(f"{asset}USDT", "1h", 100)
                    
                    if price and klines is not None:
                        # Calculate technical indicators
                        from ..utils.indicators import rsi, bollinger_bands, sma
                        
                        df = klines
                        df['rsi'] = rsi(df['close'])
                        bb_upper, bb_middle, bb_lower = bollinger_bands(df['close'])
                        df['sma_20'] = sma(df['close'], 20)
                        
                        latest = df.iloc[-1]
                        prev = df.iloc[-2]
                        
                        analysis[asset] = {
                            "current_price": price,
                            "price_change_24h": ((price - df.iloc[-24]['close']) / df.iloc[-24]['close'] * 100) if len(df) >= 24 else 0,
                            "rsi": latest['rsi'],
                            "bb_position": (latest['close'] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]),
                            "above_sma20": latest['close'] > latest['sma_20'],
                            "volume_24h": df['volume'].tail(24).sum(),
                            "trend": "bullish" if latest['close'] > prev['close'] else "bearish",
                            "support_level": df['low'].tail(20).min(),
                            "resistance_level": df['high'].tail(20).max()
                        }
                
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "market_analysis": analysis
                }, indent=2)
                
            except Exception as e:
                return f"Error getting market analysis: {e}"
        
        @self.server.tool("get_trading_performance")
        async def get_trading_performance(days: int = 7) -> str:
            """Get trading performance over specified days"""
            try:
                # Get performance data
                performance = await self.calculate_performance_metrics(days)
                
                return json.dumps({
                    "period_days": days,
                    "performance_metrics": performance,
                    "grid_trading": {
                        "sol_grid": self.trading_bot.sol_grid.get_grid_status(),
                        "avax_grid": self.trading_bot.avax_grid.get_grid_status()
                    },
                    "total_trades": len(self.trading_bot.sol_grid.filled_orders) + len(self.trading_bot.avax_grid.filled_orders)
                }, indent=2)
                
            except Exception as e:
                return f"Error getting performance: {e}"
        
        @self.server.tool("analyze_render_signals")
        async def analyze_render_signals() -> str:
            """Get current RENDER signal analysis"""
            try:
                render_data = self.trading_bot.binance.get_klines("RENDERUSDT", "1h", 100)
                if render_data is not None:
                    signal = self.trading_bot.render_signals.analyze_render_signals(render_data)
                    
                    return json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "render_analysis": signal,
                        "should_rebalance": self.trading_bot.render_signals.should_rebalance_portfolio(signal)
                    }, indent=2)
                else:
                    return "Error: Could not fetch RENDER data"
                    
            except Exception as e:
                return f"Error analyzing RENDER signals: {e}"
        
        @self.server.tool("get_recent_news_impact")
        async def get_recent_news_impact() -> str:
            """Get recent crypto news and potential impact analysis"""
            try:
                # Get recent news (would integrate with news API)
                news_items = await self.fetch_recent_crypto_news()
                
                # Basic sentiment analysis
                impact_analysis = {
                    "news_count": len(news_items),
                    "overall_sentiment": self.analyze_news_sentiment(news_items),
                    "asset_mentions": self.count_asset_mentions(news_items),
                    "recent_items": news_items[:5]  # Latest 5 items
                }
                
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "news_impact_analysis": impact_analysis
                }, indent=2)
                
            except Exception as e:
                return f"Error getting news impact: {e}"
        
        @self.server.tool("simulate_parameter_change")
        async def simulate_parameter_change(asset: str, parameter: str, new_value: float) -> str:
            """Simulate the impact of changing trading parameters"""
            try:
                # Get current parameters
                if asset.upper() == "SOL":
                    grid_trader = self.trading_bot.sol_grid
                elif asset.upper() == "AVAX":
                    grid_trader = self.trading_bot.avax_grid
                else:
                    return f"Error: Asset {asset} not supported for grid trading"
                
                current_params = {
                    "grid_size": grid_trader.grid_size * 100,
                    "num_grids": grid_trader.num_grids,
                    "base_order_size": grid_trader.base_order_size
                }
                
                # Simulate new parameters
                simulated_params = current_params.copy()
                simulated_params[parameter] = new_value
                
                # Basic simulation (in real implementation, would use historical backtesting)
                simulation_result = await self.simulate_grid_performance(asset, simulated_params)
                
                return json.dumps({
                    "asset": asset,
                    "parameter_change": {
                        "parameter": parameter,
                        "current_value": current_params.get(parameter),
                        "new_value": new_value
                    },
                    "simulation_result": simulation_result
                }, indent=2)
                
            except Exception as e:
                return f"Error simulating parameter change: {e}"
        
        @self.server.tool("get_risk_metrics")
        async def get_risk_metrics() -> str:
            """Get current risk metrics and exposure analysis"""
            try:
                portfolio, total_value = await self.trading_bot.get_portfolio_status()
                
                # Calculate risk metrics
                risk_metrics = {
                    "total_exposure": total_value,
                    "asset_allocation": {asset: (info['usd_value'] / total_value * 100) for asset, info in portfolio.items()},
                    "concentration_risk": max([info['usd_value'] / total_value for info in portfolio.values()]) * 100,
                    "daily_var": await self.calculate_daily_var(),
                    "correlation_risk": await self.calculate_correlation_risk(),
                    "active_orders": len(self.trading_bot.sol_grid.active_orders) + len(self.trading_bot.avax_grid.active_orders)
                }
                
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "risk_analysis": risk_metrics
                }, indent=2)
                
            except Exception as e:
                return f"Error getting risk metrics: {e}"
    
    def register_resources(self):
        """Register MCP resources for LLM access"""
        
        @self.server.resource("trading_logs")
        async def get_trading_logs() -> str:
            """Get recent trading bot logs"""
            try:
                log_file = Path("data/logs/trading_bot.log")
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        # Return last 100 lines
                        recent_logs = ''.join(lines[-100:])
                        return recent_logs
                else:
                    return "No log file found"
            except Exception as e:
                return f"Error reading logs: {e}"
        
        @self.server.resource("grid_trading_status")
        async def get_grid_status() -> str:
            """Get detailed grid trading status"""
            try:
                sol_status = self.trading_bot.sol_grid.get_grid_status()
                avax_status = self.trading_bot.avax_grid.get_grid_status()
                
                grid_details = {
                    "SOL_grid": {
                        **sol_status,
                        "buy_levels": len(self.trading_bot.sol_grid.buy_levels),
                        "sell_levels": len(self.trading_bot.sol_grid.sell_levels),
                        "filled_orders": len(self.trading_bot.sol_grid.filled_orders)
                    },
                    "AVAX_grid": {
                        **avax_status,
                        "buy_levels": len(self.trading_bot.avax_grid.buy_levels),
                        "sell_levels": len(self.trading_bot.avax_grid.sell_levels),
                        "filled_orders": len(self.trading_bot.avax_grid.filled_orders)
                    }
                }
                
                return json.dumps(grid_details, indent=2)
            except Exception as e:
                return f"Error getting grid status: {e}"
    
    # Helper methods
    async def get_daily_pnl(self) -> float:
        """Calculate daily P&L"""
        try:
            # Simple calculation - would be more sophisticated in practice
            current_portfolio, current_value = await self.trading_bot.get_portfolio_status()
            
            # Estimate based on price changes (simplified)
            daily_change = 0.0
            for asset, info in current_portfolio.items():
                if asset != 'USDT' and asset != 'USDC':
                    try:
                        price = self.trading_bot.binance.get_price(f"{asset}USDT")
                        klines = self.trading_bot.binance.get_klines(f"{asset}USDT", "1h", 24)
                        if price and klines is not None and len(klines) >= 24:
                            price_24h_ago = klines.iloc[-24]['close']
                            price_change = (price - price_24h_ago) / price_24h_ago
                            daily_change += info['usd_value'] * price_change
                    except:
                        continue
            
            return daily_change
        except:
            return 0.0
    
    async def calculate_performance_metrics(self, days: int) -> Dict:
        """Calculate performance metrics over specified period"""
        # Simplified performance calculation
        return {
            "total_return_percent": 2.5,  # Would calculate from actual data
            "sharpe_ratio": 1.2,
            "max_drawdown": -3.1,
            "win_rate": 68.5,
            "total_trades": 45,
            "avg_profit_per_trade": 0.8
        }
    
    async def simulate_grid_performance(self, asset: str, params: Dict) -> Dict:
        """Simulate grid performance with new parameters"""
        # Simplified simulation
        current_performance = 100
        
        # Adjust based on parameter changes
        grid_size_factor = params["grid_size"] / 2.0  # Baseline 2%
        performance_adjustment = 1.0 + (0.1 * (1/grid_size_factor - 0.5))  # Wider grids = less frequent but more profitable
        
        simulated_performance = current_performance * performance_adjustment
        
        return {
            "estimated_monthly_return": simulated_performance - 100,
            "estimated_trade_frequency": 20 * (2.0 / params["grid_size"]),
            "risk_level": "low" if params["grid_size"] > 3 else "medium"
        }
    
    async def calculate_daily_var(self) -> float:
        """Calculate daily Value at Risk"""
        # Simplified VaR calculation
        return 2.3  # 2.3% daily VaR
    
    async def calculate_correlation_risk(self) -> Dict:
        """Calculate correlation risk between assets"""
        return {
            "SOL_AVAX_correlation": 0.75,
            "RENDER_market_correlation": 0.65,
            "portfolio_correlation": 0.72
        }
    
    async def fetch_recent_crypto_news(self) -> List[str]:
        """Fetch recent crypto news (placeholder)"""
        return [
            "Bitcoin ETF sees record inflows",
            "Ethereum upgrade scheduled for next month",
            "Solana network performance improvements",
            "DeFi TVL reaches new highs",
            "Regulatory clarity improving in key markets"
        ]
    
    def analyze_news_sentiment(self, news_items: List[str]) -> str:
        """Analyze news sentiment (simplified)"""
        positive_words = ['record', 'improvement', 'upgrade', 'new highs', 'clarity']
        negative_words = ['hack', 'crash', 'regulation', 'ban', 'problem']
        
        positive_count = sum([any(word in item.lower() for word in positive_words) for item in news_items])
        negative_count = sum([any(word in item.lower() for word in negative_words) for item in news_items])
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def count_asset_mentions(self, news_items: List[str]) -> Dict:
        """Count mentions of portfolio assets in news"""
        assets = ['SOL', 'SOLANA', 'AVAX', 'AVALANCHE', 'RENDER', 'NEAR']
        mentions = {}
        
        for asset in assets:
            count = sum([asset.lower() in item.lower() for item in news_items])
            if count > 0:
                mentions[asset] = count
        
        return mentions
    
    async def start_server(self, host: str = "localhost", port: int = 8080):
        """Start the MCP server"""
        self.logger.info(f"Starting Trading MCP Server on {host}:{port}")
        await self.server.start(host, port)

# MCP Client for connecting to LLMs
class MCPTradingClient:
    """Client for sending trading data to LLMs via MCP"""
    
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.logger = logging.getLogger(__name__)
    
    async def analyze(self, prompt: str) -> str:
        """Send analysis request to LLM via MCP"""
        try:
            # This would connect to Claude or ChatGPT via MCP
            # For now, return a placeholder response
            
            # In real implementation:
            # 1. Send prompt + trading data to LLM
            # 2. LLM analyzes using MCP tools/resources
            # 3. Return LLM response
            
            response = await self.send_to_llm(prompt)
            return response
            
        except Exception as e:
            self.logger.error(f"MCP analysis failed: {e}")
            return "Analysis failed"
    
    async def send_to_llm(self, prompt: str) -> str:
        """Send prompt to LLM (placeholder)"""
        # This would integrate with actual LLM API
        return "LLM analysis response placeholder"

# Configuration for MCP setup
def setup_mcp_server(trading_bot) -> TradingMCPServer:
    """Setup and configure MCP server"""
    
    # Create MCP server
    mcp_server = TradingMCPServer(trading_bot)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return mcp_server

# Startup script
async def run_mcp_server():
    """Run the MCP server standalone"""
    
    from ..main import TradingBot
    
    # Initialize trading bot
    trading_bot = TradingBot()
    
    # Setup MCP server
    mcp_server = setup_mcp_server(trading_bot)
    
    # Start server
    await mcp_server.start_server()

if __name__ == "__main__":
    asyncio.run(run_mcp_server())
