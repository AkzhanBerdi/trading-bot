# trading_bot/main.py - CLEAN VERSION (No Emergency Logging)
"""Complete Trading Bot - Grid Control + Compound Interest - CLEAN"""

import asyncio
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from utils.database_logger import DatabaseLogger
from utils.simple_profit_tracker import SimpleProfitTracker
from utils.telegram_commands import TelegramBotCommands


def find_and_load_env():
    """Find .env file in project root and load it"""
    current_dir = Path(__file__).parent
    env_paths = [
        current_dir / ".env",
        current_dir.parent / ".env",
        current_dir.parent.parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            print(f"📋 Loading .env from: {env_path}")
            load_dotenv(env_path)
            return True

    print("❌ .env file not found in any expected location")
    return False


# Load environment first
env_loaded = find_and_load_env()

# Local imports
from strategies.grid_trading import GridTrader
from utils.binance_client import BinanceManager
from utils.compound_manager import CompoundManager
from utils.risk_manager import RiskConfig, RiskManager


class TradingBot:
    """Complete trading bot - grid control + compound interest - CLEAN"""

    def __init__(self):
        """Initialize complete trading bot"""
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Import telegram notifier AFTER environment is loaded
        from utils.telegram_notifier import telegram_notifier

        self.telegram_notifier = telegram_notifier

        # Initialize error monitoring AFTER telegram notifier
        try:
            from utils.error_monitor import setup_error_monitoring

            self.error_monitor = setup_error_monitoring(self.telegram_notifier)
            self.health_task = None
            self.logger.info("🔍 Error monitoring initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Error monitoring failed to initialize: {e}")
            self.error_monitor = None
            self.health_task = None

        # Database logging
        self.db_logger = DatabaseLogger()

        # Initialize Binance client
        try:
            self.binance = BinanceManager()
            self.logger.info("✅ Binance client initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Binance client: {e}")
            raise

        # Initialize compound manager with proper error handling
        try:
            self.compound_manager = CompoundManager(
                self.db_logger, base_order_size=100.0
            )
            # Load state from database IMMEDIATELY after initialization
            self.compound_manager.load_state_from_database(
                "trading_bot/data/trading_history.db"
            )
            self.logger.info("🔄 Compound interest initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize compound manager: {e}")
            # Create a minimal compound manager if loading fails
            self.compound_manager = CompoundManager(
                self.db_logger, base_order_size=100.0
            )

        # Get current compound order size for grid initialization
        current_order_size = self.compound_manager.get_current_order_size()
        self.logger.info(f"💰 Using compound order size: ${current_order_size:.0f}")

        # Initialize grid strategies with compound order sizes
        self.ada_grid = GridTrader(
            "ADAUSDT",
            grid_size_percent=2.0,
            num_grids=8,
            base_order_size=current_order_size,
        )
        self.avax_grid = GridTrader(
            "AVAXUSDT",
            grid_size_percent=2.0,
            num_grids=8,
            base_order_size=current_order_size,
        )
        self.profit_tracker = SimpleProfitTracker(
            db_path="trading_bot/data/trading_history.db"
        )

        # Bot state
        self.running = False
        self.grid_initialized = False
        self.start_time = time.time()
        self.session_id = f"session_{int(time.time())}_{os.getpid()}"
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5

        # Risk management
        self.risk_manager = RiskManager(self.db_logger, RiskConfig())
        self.logger.info("🛡️ Risk management initialized")

        # Telegram commands
        self.telegram_commands = TelegramBotCommands(
            self, self.telegram_notifier, self.db_logger
        )

        # Trading configuration
        self.sell_loss_tolerance = 0.01  # 1% max loss on sells
        self.buy_premium_tolerance = 0.02  # 2% max premium on buys

        # Optional features (with error handling)
        try:
            from utils.dynamic_sizing import VolatilityOrderSizer

            self.volatility_sizer = VolatilityOrderSizer(self.binance)
            self.logger.info("📊 Volatility-based order sizing enabled")
        except Exception as e:
            self.logger.warning(f"⚠️ Volatility sizing not available: {e}")
            self.volatility_sizer = None

        try:
            from utils.market_timing import MarketTimer

            self.market_timer = MarketTimer()
            self.logger.info("⏰ Market timing optimization enabled")
        except Exception as e:
            self.logger.warning(f"⚠️ Market timing not available: {e}")
            self.market_timer = None

        try:
            from utils.performance_dashboard import PerformanceDashboard

            self.dashboard = PerformanceDashboard(
                self.profit_tracker,
                self.compound_manager,
                self.telegram_notifier,
                self.db_logger,
            )
            self.logger.info("📊 Performance dashboard enabled")
        except Exception as e:
            self.logger.warning(f"⚠️ Performance dashboard not available: {e}")
            self.dashboard = None

    async def check_live_balance(self, symbol, action, quantity):
        """CRITICAL: Check live exchange balance before trading"""
        try:
            account = self.binance.get_account()
            if not account:
                self.logger.error("❌ Cannot get account data - skipping trade")
                return False

            if action == "SELL":
                # Check if we have enough coins to sell
                base_asset = symbol.replace("USDT", "")
                for balance in account["balances"]:
                    if balance["asset"] == base_asset:
                        available = float(balance["free"])
                        if available < quantity:
                            self.logger.warning(
                                f"🚫 Insufficient {base_asset}: {available:.2f} < {quantity:.2f}"
                            )
                            return False
                        break

            elif action == "BUY":
                # Check if we have enough USDT to buy
                current_price = self.binance.get_price(symbol)
                usdt_needed = quantity * current_price

                for balance in account["balances"]:
                    if balance["asset"] == "USDT":
                        available = float(balance["free"])
                        if available < usdt_needed:
                            self.logger.warning(
                                f"🚫 Insufficient USDT: ${available:.2f} < ${usdt_needed:.2f}"
                            )
                            return False
                        break

            return True

        except Exception as e:
            self.logger.error(f"❌ Balance check failed: {e}")
            return False

    def setup_logging(self):
        """Minimal console logging only"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)

    def update_grid_order_sizes(self):
        """Update grid trader order sizes when compound changes"""
        try:
            current_order_size = self.compound_manager.get_current_order_size()

            # Update both grid traders
            self.ada_grid.base_order_size = current_order_size
            self.avax_grid.base_order_size = current_order_size

            self.logger.info(
                f"🔄 Grid order sizes updated to ${current_order_size:.0f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Error updating grid order sizes: {e}")

    async def initialize_grids(self):
        """Initialize trading grids"""
        try:
            self.logger.info("🔄 Initializing trading grids...")

            # Get current prices
            ada_price = self.binance.get_price("ADAUSDT")
            avax_price = self.binance.get_price("AVAXUSDT")

            if not ada_price or not avax_price:
                self.logger.error("❌ Could not get current prices")
                return False

            # Get compound info for logging
            compound_info = self.compound_manager.get_compound_status()

            self.logger.info(
                f"💰 Current prices: ADA=${ada_price:.4f}, AVAX=${avax_price:.4f}"
            )
            self.logger.info(
                f"📈 Order size: ${compound_info['current_order_size']:.0f} ({compound_info['order_multiplier']:.2f}x)"
            )

            # Create grids with compound order sizes
            self.ada_grid.setup_grid(ada_price)
            self.avax_grid.setup_grid(avax_price)

            # Database logging
            self.db_logger.log_bot_event(
                "GRID_INIT",
                f"Grids initialized with compound orders - ADA: ${ada_price:.4f}, AVAX: ${avax_price:.4f}, Size: ${compound_info['current_order_size']:.0f}",
                "INFO",
                {
                    "ada_price": ada_price,
                    "avax_price": avax_price,
                    "order_size": compound_info["current_order_size"],
                    "multiplier": compound_info["order_multiplier"],
                },
                self.session_id,
            )

            self.grid_initialized = True
            self.logger.info("✅ Grids created with compound interest")

            if self.telegram_notifier.enabled:
                await self.telegram_notifier.notify_info(
                    f"🎯 Grids Initialized\n"
                    f"ADA: ${ada_price:.4f} | AVAX: ${avax_price:.4f}\n"
                    f"Order Size: ${compound_info['current_order_size']:.0f} ({compound_info['order_multiplier']:.2f}x)\n"
                    f"Grid control + compounding ready! 🚀"
                )

            return True

        except Exception as e:
            self.logger.error(f"❌ Grid initialization failed: {e}")
            return False

    async def check_grid_strategies(self):
        """Enhanced grid checking with auto-reset"""
        try:
            # ADA Grid
            try:
                ada_price = self.binance.get_price("ADAUSDT")
                if ada_price:
                    self.logger.info(f"🔸 ADA: ${ada_price:.4f}")

                    # Check for grid reset first
                    ada_reset = self.ada_grid.auto_reset_grid(ada_price)
                    if ada_reset["reset"]:
                        self.logger.info(
                            f"🔄 ADA grid auto-reset: {ada_reset['reason']}"
                        )

                    ada_signals = self.ada_grid.check_signals(ada_price)
                    for signal in ada_signals:
                        success = await self.execute_smart_grid_order(
                            self.ada_grid, signal
                        )
                        if success:
                            break
            except Exception as e:
                self.logger.error(f"❌ ADA grid error: {e}")

            # AVAX Grid
            try:
                avax_price = self.binance.get_price("AVAXUSDT")
                if avax_price:
                    self.logger.info(f"🔸 AVAX: ${avax_price:.4f}")

                    # Check for grid reset first
                    avax_reset = self.avax_grid.auto_reset_grid(avax_price)
                    if avax_reset["reset"]:
                        self.logger.info(
                            f"🔄 AVAX grid auto-reset: {avax_reset['reason']}"
                        )

                    avax_signals = self.avax_grid.check_signals(avax_price)
                    for signal in avax_signals:
                        success = await self.execute_smart_grid_order(
                            self.avax_grid, signal
                        )
                        if success:
                            break
            except Exception as e:
                self.logger.error(f"❌ AVAX grid error: {e}")

        except Exception as e:
            self.logger.error(f"Grid strategy check failed: {e}")

    async def execute_smart_grid_order(self, grid_trader, signal):
        """Execute grid order with basic risk checks"""
        symbol = grid_trader.symbol
        action = signal["action"]
        grid_price = signal["price"]
        quantity = signal["quantity"]
        current_price = self.binance.get_price(symbol)

        if not current_price:
            return False

        # Risk check
        trade_value = current_price * quantity
        allowed, reason = self.risk_manager.check_trade_permission(action, trade_value)

        if not allowed:
            self.logger.warning(f"🚫 {symbol} trade blocked: {reason}")
            return False

        # Profit protection
        price_diff_percent = (current_price - grid_price) / grid_price

        if action == "SELL":
            # Block unprofitable sells
            tolerance = 1 - self.sell_loss_tolerance
            if current_price < grid_price * tolerance:
                loss_percent = abs(price_diff_percent) * 100
                self.logger.warning(
                    f"🚫 {symbol} unprofitable sell blocked: -{loss_percent:.1f}%"
                )
                return False

        elif action == "BUY":
            # Allow reasonable buy premiums
            tolerance = 1 + self.buy_premium_tolerance
            if current_price > grid_price * tolerance:
                premium_percent = price_diff_percent * 100
                self.logger.warning(
                    f"🚫 {symbol} expensive buy blocked: +{premium_percent:.1f}%"
                )
                return False

        # Execute order
        return await self.execute_grid_order(grid_trader, signal)

    async def execute_grid_order(self, grid_trader, signal):
        """Execute grid order with live balance check"""
        try:
            symbol = grid_trader.symbol
            action = signal["action"]
            quantity = signal["quantity"]

            # Check for duplicate trades
            if hasattr(grid_trader, "is_duplicate_trade"):
                if grid_trader.is_duplicate_trade(action, signal["price"], quantity):
                    self.logger.warning(
                        f"🚫 Duplicate trade prevented: {action} {quantity} {symbol}"
                    )
                    return False

            # CRITICAL: Check live balance FIRST
            if not await self.check_live_balance(symbol, action, quantity):
                return False

            # Precision fix
            if symbol == "ADAUSDT":
                quantity = round(quantity, 0)
            elif symbol == "AVAXUSDT":
                quantity = round(quantity, 2)

            # Minimum order check
            current_price = self.binance.get_price(symbol)
            order_value = quantity * current_price

            if order_value < 8:
                self.logger.warning(f"⚠️ Order value ${order_value:.2f} below minimum")
                return False

            # Execute order
            if action == "BUY":
                order = self.binance.place_market_buy(symbol, quantity)
            else:
                order = self.binance.place_market_sell(symbol, quantity)

            # Process successful order
            if order and order.get("status") == "FILLED":
                filled_quantity = float(order.get("executedQty", quantity))

                # Calculate average fill price
                fills = order.get("fills", [])
                if fills:
                    total_qty = sum(float(fill["qty"]) for fill in fills)
                    total_value = sum(
                        float(fill["qty"]) * float(fill["price"]) for fill in fills
                    )
                    avg_price = (
                        total_value / total_qty if total_qty > 0 else current_price
                    )
                else:
                    avg_price = current_price

                order_id = order.get("orderId", "N/A")
                total_value = filled_quantity * avg_price

                # Simple profit tracking
                profit_from_sell = 0.0
                if action == "BUY":
                    self.profit_tracker.record_buy(symbol, filled_quantity, avg_price)
                elif action == "SELL":
                    profit_from_sell = self.profit_tracker.record_sell(
                        symbol, filled_quantity, avg_price
                    )

                # Update compound interest from sell profits
                if action == "SELL" and profit_from_sell > 0:
                    self.compound_manager.record_trade_profit(
                        symbol, action, profit_from_sell
                    )
                    # Update grid order sizes if compound changed
                    self.update_grid_order_sizes()

                # Risk management
                trade_pnl = 0.5 if action == "SELL" else 0.1
                self.risk_manager.update_daily_pnl(trade_pnl)

                # Database logging only
                try:
                    import sqlite3
                    from datetime import datetime

                    conn = sqlite3.connect("trading_bot/data/trading_history.db")
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                    INSERT INTO trades (
                        timestamp, datetime, symbol, side, quantity, price, total_value,
                        order_id, grid_level, status, session_id, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                            symbol,
                            action,
                            filled_quantity,
                            avg_price,
                            total_value,
                            str(order_id),
                            signal.get("level", 0),
                            "FILLED",
                            self.session_id,
                            f"Grid level {signal.get('level', 0)}",
                        ),
                    )

                    conn.commit()
                    conn.close()

                    self.logger.info(
                        f"✅ DB: {action} {filled_quantity} {symbol} @ ${avg_price:.4f}"
                    )

                except Exception as db_error:
                    self.logger.error(f"❌ Database logging failed: {db_error}")

                # Update grid state
                filled_order = {
                    "symbol": symbol,
                    "side": action,
                    "quantity": filled_quantity,
                    "price": avg_price,
                    "level": signal["level"],
                    "timestamp": time.time(),
                    "order_id": str(order_id),
                }
                grid_trader.filled_orders.append(filled_order)

                # Log success
                profit_msg = (
                    f" (${profit_from_sell:.2f} profit)" if profit_from_sell > 0 else ""
                )
                self.logger.info(
                    f"✅ {action} {filled_quantity} {symbol} @ ${avg_price:.4f}{profit_msg}"
                )

                return True

        except Exception as e:
            self.logger.error(f"❌ Error executing order: {e}")
            return False

    async def run_cycle(self):
        """Enhanced trading cycle with daily summary"""
        try:
            # Initialize grids on first cycle
            if not self.grid_initialized:
                success = await self.initialize_grids()
                if not success:
                    return False

            # Check risk mode before trading
            if self.risk_manager.current_mode.value in [
                "EMERGENCY_STOP",
                "CIRCUIT_BREAKER",
            ]:
                self.logger.warning(
                    f"🚫 Trading suspended: {self.risk_manager.current_mode.value}"
                )
                return True

            # Core trading logic
            await self.check_grid_strategies()

            # Daily summary (if dashboard is available)
            if self.dashboard and self.dashboard.should_send_daily_summary():
                asyncio.create_task(self.dashboard.generate_daily_summary())

            return True

        except Exception as e:
            self.logger.error(f"❌ Trading cycle failed: {e}")
            self.consecutive_failures += 1
            return False

    async def run(self):
        """Main bot loop with intelligent timing"""
        self.logger.info("🚀 Starting enhanced trading bot with intelligent timing...")

        # Start error monitoring health checks (if available)
        if self.error_monitor:
            self.health_task = asyncio.create_task(
                self.error_monitor.check_bot_health()
            )
            self.logger.info("📱 Error monitoring health checks started")

        # Log bot start
        compound_info = self.compound_manager.get_compound_status()
        self.db_logger.log_bot_event(
            "BOT_START",
            "Complete trading bot started with compound interest",
            "INFO",
            {
                "session_id": self.session_id,
                "version": "clean_v1.0",
                "initial_order_size": compound_info["current_order_size"],
                "compound_multiplier": compound_info["order_multiplier"],
            },
            self.session_id,
        )

        # Start telegram commands
        command_task = asyncio.create_task(
            self.telegram_commands.start_command_processor()
        )
        self.logger.info("🤖 Telegram commands active (with compounding)")

        # Startup notification
        if self.telegram_notifier.enabled:
            try:
                compound_info = self.compound_manager.get_compound_status()
                await self.telegram_notifier.notify_info(
                    f"🤖 Bot Started - Order Size: ${compound_info['current_order_size']:.0f}"
                )
            except Exception as e:
                self.logger.warning(f"Startup notification failed: {e}")

        # Test connection
        if not self.binance.test_connection():
            self.logger.error("❌ Binance connection failed")
            return

        # Main loop
        self.running = True
        cycle_count = 0

        try:
            while True:
                if self.running:
                    cycle_count += 1

                    # Get market timing info (if available)
                    if self.market_timer:
                        market_info = self.market_timer.get_market_session_info()
                        self.logger.info(
                            f"📊 Cycle {cycle_count} | "
                            f"Market: {market_info['session']} ({market_info['activity_level']})"
                        )
                    else:
                        self.logger.info(f"📊 Cycle {cycle_count}")

                    try:
                        await self.run_cycle()
                        if self.consecutive_failures > 0:
                            self.consecutive_failures = 0
                    except Exception as e:
                        self.consecutive_failures += 1
                        self.logger.error(f"❌ Cycle {cycle_count} failed: {e}")

                    # Emergency stop check
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        self.logger.critical(
                            f"🚨 Too many failures ({self.consecutive_failures}) - stopping"
                        )
                        self.risk_manager.trigger_emergency_stop()
                        self.running = False
                        continue

                    # Intelligent timing (if available)
                    if self.market_timer:
                        base_sleep_time = 15.0
                        optimal_sleep = self.market_timer.get_optimal_sleep_time(
                            base_sleep_time
                        )
                        await asyncio.sleep(optimal_sleep)
                    else:
                        await asyncio.sleep(15.0)  # Default 15 seconds

                else:
                    # Check for restart request
                    if getattr(self.telegram_commands, "restart_requested", False):
                        self.logger.info("🔄 Restart requested, resuming...")
                        self.running = True
                        self.telegram_commands.restart_requested = False
                        self.consecutive_failures = 0
                        continue

                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("👋 Shutting down...")

        finally:
            # Cleanup
            self.running = False
            self.telegram_commands.stop_command_processor()
            command_task.cancel()

            # Stop error monitoring health task
            if self.health_task:
                self.health_task.cancel()
                self.logger.info("📱 Error monitoring health checks stopped")

            # Log bot stop
            compound_info = self.compound_manager.get_compound_status()
            self.db_logger.log_bot_event(
                "BOT_STOP",
                "Enhanced bot stopped",
                "INFO",
                {
                    "total_cycles": cycle_count,
                    "session_duration": time.time() - self.start_time,
                    "final_order_size": compound_info["current_order_size"],
                    "final_multiplier": compound_info["order_multiplier"],
                    "total_accumulated_profit": compound_info["accumulated_profit"],
                },
                self.session_id,
            )

            if self.telegram_notifier.enabled:
                await self.telegram_notifier.notify_info(
                    f"🛑 Bot Stopped - Final Order Size: ${compound_info['current_order_size']:.0f}"
                )

            self.logger.info("🛑 Enhanced bot stopped")


def main():
    """Main entry point"""
    if not env_loaded:
        print("❌ Could not load .env file")
        return

    try:
        bot = TradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown requested")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")


if __name__ == "__main__":
    main()
