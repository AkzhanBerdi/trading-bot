# src/trading_bot/main.py
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


# Find and load .env file from project root
def find_and_load_env():
    """Find .env file in project root and load it"""
    current_dir = Path(__file__).parent

    # Try different locations for .env file
    env_paths = [
        current_dir / ".env",  # Current directory
        current_dir.parent / ".env",  # Parent directory
        current_dir.parent.parent / ".env",  # Project root
        current_dir.parent.parent.parent / ".env",  # Just in case
    ]

    for env_path in env_paths:
        if env_path.exists():
            print(f"📋 Loading .env from: {env_path}")
            load_dotenv(env_path)
            return True

    print("❌ .env file not found in any expected location:")
    for path in env_paths:
        print(f"  Checked: {path.absolute()}")
    return False


# Load environment first
env_loaded = find_and_load_env()

# Local imports (using relative paths for your directory structure)
from strategies.grid_trading import GridTrader
from strategies.render_signals import RenderSignalTrader
from utils.binance_client import BinanceManager

# Import telegram notifier after env is loaded
from utils.telegram_notifier import telegram_notifier


class TradingBot:
    def __init__(self):
        """Initialize the trading bot"""
        # Don't send notifications during __init__ - no event loop yet!

        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        try:
            self.binance = BinanceManager()
            self.logger.info("✅ Binance client initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Binance client: {e}")
            raise  # Don't try to send notifications here

        # Initialize strategies with your current parameters
        self.ada_grid = GridTrader(
            "ADAUSDT", grid_size_percent=2.5, num_grids=8, base_order_size=50
        )
        self.avax_grid = GridTrader(
            "AVAXUSDT", grid_size_percent=2.0, num_grids=8, base_order_size=50
        )
        self.render_signals = RenderSignalTrader(rebalance_threshold=0.75)

        # Bot state
        self.running = False
        self.last_render_check = None
        self.portfolio_value = 0.0
        self.daily_trades = 0
        self.last_portfolio_update = None
        self.grid_initialized = False

        self.logger.info("🤖 Trading Bot initialized successfully")

    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory relative to current location
        log_dir = Path("scripts/data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # File handler
        file_handler = logging.FileHandler(log_dir / "trading_bot.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    async def initialize_grids(self):
        """Initialize grids with initial notifications - called after event loop starts"""
        try:
            ada_price = self.binance.get_price("ADAUSDT")
            avax_price = self.binance.get_price("AVAXUSDT")

            if ada_price and avax_price:
                self.ada_grid.setup_grid(ada_price)
                self.avax_grid.setup_grid(avax_price)
                self.logger.info(
                    f"Grids initialized: ADA @ ${ada_price:.4f}, AVAX @ ${avax_price:.4f}"
                )

                # Now we can send notifications (event loop is running)
                await telegram_notifier.notify_info(
                    f"🎯 Grids Initialized\n"
                    f"• ADA: ${ada_price:.4f} (±{2.5}% spacing)\n"
                    f"• AVAX: ${avax_price:.4f} (±{2.0}% spacing)\n"
                    f"Ready to capture volatility!"
                )
                self.grid_initialized = True
                return True
        except Exception as e:
            self.logger.error(f"Failed to initialize grids: {e}")
            await telegram_notifier.notify_warning(f"Grid initialization failed: {e}")
            return False

    async def get_portfolio_status(self):
        """Get current portfolio status"""
        try:
            balances = self.binance.get_account_balance()
            portfolio = {}
            total_value = 0.0

            for balance in balances:
                asset = balance["asset"]
                if balance["total"] > 0:
                    # Get USD value
                    if asset == "USDT" or asset == "USDC":
                        usd_value = balance["total"]
                    else:
                        try:
                            price = self.binance.get_price(f"{asset}USDT")
                            usd_value = balance["total"] * price if price else 0
                        except:
                            usd_value = 0

                    portfolio[asset] = {
                        "quantity": balance["total"],
                        "usd_value": usd_value,
                    }
                    total_value += usd_value

            self.portfolio_value = total_value
            return portfolio, total_value

        except Exception as e:
            self.logger.error(f"Error getting portfolio status: {e}")
            await telegram_notifier.notify_warning(f"Portfolio status error: {e}")
            return {}, 0.0

    async def check_grid_strategies(self):
        """Check and execute grid trading strategies with detailed logging and notifications"""
        try:
            # Check ADA grid
            ada_price = self.binance.get_price("ADAUSDT")
            if ada_price:
                self.logger.info(f"🔸 ADA Current Price: ${ada_price:.4f}")

                # Log grid levels and distances
                self._log_grid_details("ADA", self.ada_grid, ada_price)

                ada_signals = self.ada_grid.check_signals(ada_price)
                if ada_signals:
                    self.logger.info(f"⚡ ADA: {len(ada_signals)} signals detected!")
                    for signal in ada_signals:
                        self.logger.info(
                            f"   📍 Signal: {signal['action']} level {signal['level']} "
                            f"at ${signal['price']:.4f} (strength: {signal['signal_strength']:.2f})"
                        )

                        if signal["signal_strength"] >= 0.7:
                            # Send trade attempt notification
                            await telegram_notifier.notify_trade_attempt(
                                symbol="ADAUSDT",
                                action=signal["action"],
                                price=signal["price"],
                                quantity=signal["quantity"],
                                level=signal["level"],
                            )

                            success = await self.execute_grid_order_with_notifications(
                                self.ada_grid, signal, "ADA"
                            )

                            if success:
                                self.daily_trades += 1
                                self.logger.info(
                                    f"✅ ADA grid trade executed: {signal['action']} at ${signal['price']:.4f}"
                                )
                else:
                    self.logger.info("🔹 ADA: No grid signals detected")

            # Check AVAX grid
            avax_price = self.binance.get_price("AVAXUSDT")
            if avax_price:
                self.logger.info(f"🔸 AVAX Current Price: ${avax_price:.4f}")

                # Log grid levels and distances
                self._log_grid_details("AVAX", self.avax_grid, avax_price)

                avax_signals = self.avax_grid.check_signals(avax_price)
                if avax_signals:
                    self.logger.info(f"⚡ AVAX: {len(avax_signals)} signals detected!")
                    for signal in avax_signals:
                        self.logger.info(
                            f"   📍 Signal: {signal['action']} level {signal['level']} "
                            f"at ${signal['price']:.4f} (strength: {signal['signal_strength']:.2f})"
                        )

                        if signal["signal_strength"] >= 0.7:
                            # Send trade attempt notification
                            await telegram_notifier.notify_trade_attempt(
                                symbol="AVAXUSDT",
                                action=signal["action"],
                                price=signal["price"],
                                quantity=signal["quantity"],
                                level=signal["level"],
                            )

                            success = await self.execute_grid_order_with_notifications(
                                self.avax_grid, signal, "AVAX"
                            )

                            if success:
                                self.daily_trades += 1
                                self.logger.info(
                                    f"✅ AVAX grid trade executed: {signal['action']} at ${signal['price']:.4f}"
                                )
                else:
                    self.logger.info("🔹 AVAX: No grid signals detected")

        except Exception as e:
            self.logger.error(f"Error in grid strategies: {e}")
            await telegram_notifier.notify_trade_error(
                symbol="GRID_SYSTEM", action="CHECK_STRATEGIES", error_message=str(e)
            )

    async def execute_grid_order_with_notifications(
        self, grid_trader, signal, asset_name
    ):
        """Execute grid order with comprehensive notifications"""
        try:
            symbol = grid_trader.symbol
            action = signal["action"]
            quantity = signal["quantity"]

            # AFTER (fixes LOT_SIZE error):
            if action == "BUY":
                # Fix quantity precision
                if symbol == "ADAUSDT":
                    quantity = round(quantity, 0)  # Whole numbers for ADA
                elif symbol == "AVAXUSDT":
                    quantity = round(quantity, 2)  # 2 decimals for AVAX

                order = self.binance.place_market_buy(symbol, quantity)
            else:  # SELL
                # Fix quantity precision
                if symbol == "ADAUSDT":
                    quantity = round(quantity, 0)
                elif symbol == "AVAXUSDT":
                    quantity = round(quantity, 2)

                order = self.binance.place_market_sell(symbol, quantity)

            if order and order.get("status") == "FILLED":
                # Get filled price and calculate profit if applicable
                filled_price = float(
                    order.get("fills", [{}])[0].get("price", signal["price"])
                )
                filled_quantity = float(order.get("executedQty", quantity))
                order_id = order.get("orderId", "N/A")

                # Calculate profit for this trade (simplified)
                profit = None
                if action == "SELL":
                    # For sell orders, try to estimate profit based on grid spacing
                    estimated_buy_price = filled_price * 0.975  # Rough estimate
                    profit = (filled_price - estimated_buy_price) * filled_quantity

                # Record filled order
                grid_trader.filled_orders.append(
                    {
                        "symbol": symbol,
                        "side": action,
                        "quantity": filled_quantity,
                        "price": filled_price,
                        "level": signal["level"],
                        "timestamp": datetime.now(),
                        "order_id": order_id,
                    }
                )

                # Send success notification
                await telegram_notifier.notify_trade_success(
                    symbol=symbol,
                    action=action,
                    price=filled_price,
                    quantity=filled_quantity,
                    order_id=str(order_id),
                    profit=profit,
                )

                self.logger.info(
                    f"Grid order executed: {action} {filled_quantity} {symbol} at level {signal['level']}"
                )
                return True

            else:
                # Order failed
                error_msg = (
                    order.get("msg", "Unknown order error")
                    if order
                    else "Order returned None"
                )

                await telegram_notifier.notify_trade_error(
                    symbol=symbol,
                    action=action,
                    error_message=error_msg,
                    price=signal["price"],
                    quantity=quantity,
                )

                self.logger.error(f"Grid order failed: {error_msg}")
                return False

        except Exception as e:
            # Exception during order execution
            await telegram_notifier.notify_trade_error(
                symbol=grid_trader.symbol,
                action=signal["action"],
                error_message=f"Exception: {str(e)}",
                price=signal["price"],
                quantity=signal["quantity"],
            )

            self.logger.error(f"Error executing grid order: {e}")
            return False

    def _log_grid_details(self, asset_name: str, grid_trader, current_price: float):
        """Log detailed grid information to understand why trades aren't happening"""

        # Get filled order levels to show which are already used
        filled_buy_levels = [
            o["level"] for o in grid_trader.filled_orders if o["side"] == "BUY"
        ]
        filled_sell_levels = [
            o["level"] for o in grid_trader.filled_orders if o["side"] == "SELL"
        ]

        # Find nearest buy and sell levels
        nearest_buy_price = None
        nearest_buy_distance = float("inf")
        nearest_sell_price = None
        nearest_sell_distance = float("inf")

        # Check buy levels (below current price)
        for level in grid_trader.buy_levels:
            distance = current_price - level["price"]
            if (
                distance < nearest_buy_distance
                and level["level"] not in filled_buy_levels
            ):
                nearest_buy_distance = distance
                nearest_buy_price = level["price"]

        # Check sell levels (above current price)
        for level in grid_trader.sell_levels:
            distance = level["price"] - current_price
            if (
                distance < nearest_sell_distance
                and level["level"] not in filled_sell_levels
            ):
                nearest_sell_distance = distance
                nearest_sell_price = level["price"]

        # Log summary of nearest levels
        if nearest_buy_price:
            self.logger.info(
                f"   🎯 {asset_name} Nearest BUY: ${nearest_buy_price:.4f} "
                f"(${nearest_buy_distance:.4f} below current)"
            )

        if nearest_sell_price:
            self.logger.info(
                f"   🎯 {asset_name} Nearest SELL: ${nearest_sell_price:.4f} "
                f"(${nearest_sell_distance:.4f} above current)"
            )

        # Log grid statistics
        total_buy_levels = len(grid_trader.buy_levels)
        total_sell_levels = len(grid_trader.sell_levels)
        filled_buys = len(filled_buy_levels)
        filled_sells = len(filled_sell_levels)

        self.logger.info(
            f"   📊 {asset_name} Grid Status: "
            f"BUY {filled_buys}/{total_buy_levels} filled, "
            f"SELL {filled_sells}/{total_sell_levels} filled"
        )

    async def send_portfolio_update(self):
        """Send periodic portfolio update"""
        try:
            portfolio, total_value = await self.get_portfolio_status()

            # Calculate daily change (simplified)
            daily_change = None
            if hasattr(self, "previous_portfolio_value"):
                daily_change = total_value - self.previous_portfolio_value
            self.previous_portfolio_value = total_value

            # Get top assets
            top_assets = {}
            for asset, info in portfolio.items():
                if info["usd_value"] > 1:  # Only assets worth more than $1
                    top_assets[asset] = info["usd_value"]

            # Sort by value
            top_assets = dict(
                sorted(top_assets.items(), key=lambda x: x[1], reverse=True)
            )

            await telegram_notifier.notify_portfolio_update(
                total_value=total_value,
                daily_change=daily_change,
                top_assets=top_assets,
            )

        except Exception as e:
            self.logger.error(f"Error sending portfolio update: {e}")

    async def run_cycle(self):
        """Run one complete trading cycle"""
        try:
            # Initialize grids on first cycle
            if not self.grid_initialized:
                success = await self.initialize_grids()
                if not success:
                    return  # Skip this cycle if grid initialization failed

            # Check portfolio status
            portfolio, total_value = await self.get_portfolio_status()
            self.logger.info(f"💰 Portfolio value: ${total_value:.2f}")

            # Execute grid strategies (every cycle)
            await self.check_grid_strategies()

            # Log grid status
            ada_status = self.ada_grid.get_grid_status()
            avax_status = self.avax_grid.get_grid_status()

            self.logger.info(
                f"ADA Grid: {ada_status['total_orders']} orders, "
                f"${ada_status['total_volume_usdt']:.2f} volume"
            )
            self.logger.info(
                f"AVAX Grid: {avax_status['total_orders']} orders, "
                f"${avax_status['total_volume_usdt']:.2f} volume"
            )

        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")
            await telegram_notifier.notify_bot_status(
                "error", f"Trading cycle error: {e}"
            )

    async def run(self):
        """Main bot loop"""
        self.logger.info("🚀 Starting trading bot...")

        # Check if Telegram is enabled and send startup notification
        if telegram_notifier.enabled:
            await telegram_notifier.notify_bot_status(
                "started",
                f"🤖 Trading Bot Online!\n"
                f"• ADA Grid: {2.5}% spacing\n"
                f"• AVAX Grid: {2.0}% spacing\n"
                f"• Monitoring: Portfolio + Signals\n"
                f"Ready to trade!",
            )
        else:
            self.logger.warning(
                "📴 Telegram notifications disabled - check credentials in .env"
            )

        # Test connection
        if not self.binance.test_connection():
            self.logger.error("❌ Binance connection failed, exiting")
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "error", "Binance connection failed - bot stopping"
                )
            return

        self.running = True
        cycle_count = 0

        try:
            while self.running:
                cycle_count += 1
                self.logger.info(f"📊 Cycle {cycle_count} starting...")

                await self.run_cycle()

                # Send portfolio update every 20 cycles (10 minutes)
                if cycle_count % 1440 == 0 and telegram_notifier.enabled:
                    await self.send_portfolio_update()

                # Wait before next cycle (30 seconds)
                await asyncio.sleep(30)

        except KeyboardInterrupt:
            self.logger.info("👋 Shutting down trading bot...")
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "stopped", "Bot shutdown requested by user"
                )
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "error", f"Unexpected error: {e}"
                )
        finally:
            self.running = False
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "stopped", "Trading bot has stopped"
                )
            self.logger.info("🛑 Trading bot stopped")


def main():
    """Main entry point"""
    if not env_loaded:
        print("❌ Could not load .env file. Please check the location.")
        print("Expected locations:")
        print("  - Project root: /home/aberdeev/crypto-trading/trading-bot/.env")
        return

    try:
        bot = TradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown requested")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        # Only try to send notification if event loop is available
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    telegram_notifier.notify_bot_status(
                        "error", f"Failed to start bot: {e}"
                    )
                )
        except:
            pass  # If no event loop, just exit gracefully


if __name__ == "__main__":
    main()
