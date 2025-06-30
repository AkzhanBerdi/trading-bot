# src/trading_bot/main.py
import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from utils.database_logger import DatabaseLogger
from utils.telegram_commands import TelegramBotCommands


def find_and_load_env():
    """Find .env file in project root and load it"""
    current_dir = Path(__file__).parent
    env_paths = [
        current_dir / ".env",
        current_dir.parent / ".env",
        current_dir.parent.parent / ".env",
        current_dir.parent.parent.parent / ".env",
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
from utils.telegram_notifier import NotificationType, telegram_notifier


class TradingBot:
    def __init__(self):
        """Initialize the simplified trading bot"""
        # Setup minimal logging (console only)
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        try:
            self.binance = BinanceManager()
            self.logger.info("✅ Binance client initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Binance client: {e}")
            raise

        # Initialize strategies
        self.ada_grid = GridTrader(
            "ADAUSDT", grid_size_percent=2.5, num_grids=8, base_order_size=50
        )
        self.avax_grid = GridTrader(
            "AVAXUSDT", grid_size_percent=2.0, num_grids=8, base_order_size=50
        )

        # Bot state
        self.running = False
        self.grid_initialized = False
        self.start_time = time.time()
        self.session_id = f"session_{int(time.time())}_{os.getpid()}"
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5

        # Database logger (single source of truth)
        self.db_logger = DatabaseLogger()

        # Telegram commands
        self.telegram_commands = TelegramBotCommands(
            self, telegram_notifier, self.db_logger
        )

        # Trading configuration
        self.sell_loss_tolerance = 0.01  # 1% max loss on sells
        self.buy_premium_tolerance = 0.02  # 2% max premium on buys

    def setup_logging(self):
        """Setup minimal console-only logging"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Console handler only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ Simplified console-only logging setup")

    async def initialize_grids(self):
        """Initialize fresh trading grids"""
        try:
            self.logger.info("🔄 Initializing fresh trading grids...")

            # Get current prices
            ada_price = self.binance.get_price("ADAUSDT")
            avax_price = self.binance.get_price("AVAXUSDT")

            if not ada_price or not avax_price:
                self.logger.error("❌ Could not get current prices")
                return False

            self.logger.info(
                f"💰 Current prices: ADA=${ada_price:.4f}, AVAX=${avax_price:.4f}"
            )

            # Create fresh grids
            self.ada_grid.setup_grid(ada_price)
            self.avax_grid.setup_grid(avax_price)

            # Log grid initialization to database
            self.db_logger.log_bot_event(
                "GRID_INIT",
                f"Fresh grids initialized - ADA: ${ada_price:.4f}, AVAX: ${avax_price:.4f}",
                "SYSTEM",
                "INFO",
                {
                    "ada_price": ada_price,
                    "avax_price": avax_price,
                    "ada_levels": self.ada_grid.num_grids * 2,
                    "avax_levels": self.avax_grid.num_grids * 2,
                },
                self.session_id,
            )

            self.grid_initialized = True
            self.logger.info("✅ Fresh grids created")

            if telegram_notifier.enabled:
                await telegram_notifier.notify_info(
                    "🎯 Fresh Grids Initialized\n"
                    f"ADA: {self.ada_grid.num_grids * 2} levels around ${ada_price:.4f}\n"
                    f"AVAX: {self.avax_grid.num_grids * 2} levels around ${avax_price:.4f}\n"
                    f"Database logging active! 🚀"
                )

            return True

        except Exception as e:
            self.logger.error(f"❌ Grid initialization failed: {e}")
            self.db_logger.log_bot_event(
                "GRID_INIT_ERROR",
                f"Grid initialization failed: {e}",
                "SYSTEM",
                "ERROR",
                {"error": str(e)},
                self.session_id,
            )
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "error", f"Grid initialization failed: {e}"
                )
            return False

    async def get_portfolio_status(self):
        """Get current portfolio status and save to database"""
        try:
            balances = self.binance.get_account_balance()
            portfolio = {}
            total_value = 0.0

            for balance in balances:
                asset = balance["asset"]
                if balance["total"] > 0:
                    if asset in ["USDT", "USDC"]:
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

            # Save portfolio snapshot to database
            self.db_logger.log_portfolio_snapshot(
                total_value=total_value,
                assets=portfolio,
                session_id=self.session_id,
                notes="Automated portfolio snapshot",
            )

            return portfolio, total_value

        except Exception as e:
            self.logger.error(f"Error getting portfolio status: {e}")
            self.db_logger.log_bot_event(
                "PORTFOLIO_ERROR",
                f"Portfolio status error: {e}",
                "SYSTEM",
                "ERROR",
                {"error": str(e)},
                self.session_id,
            )
            return {}, 0.0

    async def check_grid_strategies(self):
        """Smart grid strategies with database logging"""
        # ADA Grid
        try:
            ada_price = self.binance.get_price("ADAUSDT")
            if ada_price:
                self.logger.info(f"🔸 ADA Current Price: ${ada_price:.4f}")
                ada_signals = self.ada_grid.check_signals(ada_price)

                for signal in ada_signals:
                    success = await self.execute_smart_grid_order(self.ada_grid, signal)
                    if success:
                        break

        except Exception as e:
            self.logger.error(f"❌ ADA grid error: {e}")
            self.db_logger.log_bot_event(
                "ADA_GRID_ERROR",
                f"ADA grid error: {e}",
                "TRADING",
                "ERROR",
                {"error": str(e)},
                self.session_id,
            )

        # AVAX Grid
        try:
            avax_price = self.binance.get_price("AVAXUSDT")
            if avax_price:
                self.logger.info(f"🔸 AVAX Current Price: ${avax_price:.4f}")
                avax_signals = self.avax_grid.check_signals(avax_price)

                for signal in avax_signals:
                    success = await self.execute_smart_grid_order(
                        self.avax_grid, signal
                    )
                    if success:
                        break

        except Exception as e:
            self.logger.error(f"❌ AVAX grid error: {e}")
            self.db_logger.log_bot_event(
                "AVAX_GRID_ERROR",
                f"AVAX grid error: {e}",
                "TRADING",
                "ERROR",
                {"error": str(e)},
                self.session_id,
            )

    async def execute_smart_grid_order(self, grid_trader, signal):
        """Smart execution with profit protection and database logging"""
        symbol = grid_trader.symbol
        action = signal["action"]
        grid_price = signal["price"]
        current_price = self.binance.get_price(symbol)

        if not current_price:
            self.logger.error(f"❌ Cannot get current price for {symbol}")
            return False

        price_diff_percent = (current_price - grid_price) / grid_price

        # SELL LOGIC: Profit protection
        if action == "SELL":
            tolerance = 1 - self.sell_loss_tolerance
            if current_price >= grid_price * tolerance:
                profit_percent = price_diff_percent * 100
                self.logger.info(
                    f"✅ {symbol} PROFITABLE SELL: Grid ${grid_price:.4f} → "
                    f"Market ${current_price:.4f} ({profit_percent:+.2f}%)"
                )
            else:
                loss_percent = abs(price_diff_percent) * 100
                self.logger.warning(
                    f"🚫 {symbol} UNPROFITABLE SELL BLOCKED: Grid ${grid_price:.4f} → "
                    f"Market ${current_price:.4f} (-{loss_percent:.2f}% loss)"
                )

                # Log blocked trade to database
                self.db_logger.log_bot_event(
                    "TRADE_BLOCKED",
                    f"Unprofitable {symbol} sell blocked - would lose {loss_percent:.1f}%",
                    "TRADING",
                    "WARNING",
                    {
                        "symbol": symbol,
                        "action": action,
                        "grid_price": grid_price,
                        "current_price": current_price,
                        "loss_percent": loss_percent,
                    },
                    self.session_id,
                )

                if telegram_notifier.enabled:
                    await telegram_notifier.send_notification(
                        NotificationType.WARNING,
                        "Unprofitable Sell Blocked",
                        f"🚫 {symbol} SELL blocked\nWould lose {loss_percent:.1f}%\nWaiting for better price...",
                    )
                return False

        # BUY LOGIC: Allow reasonable premiums
        elif action == "BUY":
            tolerance = 1 + self.buy_premium_tolerance
            if current_price <= grid_price * tolerance:
                if current_price <= grid_price:
                    discount_percent = abs(price_diff_percent) * 100
                    self.logger.info(
                        f"✅ {symbol} DISCOUNT BUY: Grid ${grid_price:.4f} → "
                        f"Market ${current_price:.4f} (-{discount_percent:.2f}% discount)"
                    )
                else:
                    premium_percent = price_diff_percent * 100
                    self.logger.info(
                        f"✅ {symbol} ACCEPTABLE BUY: Grid ${grid_price:.4f} → "
                        f"Market ${current_price:.4f} (+{premium_percent:.2f}% premium)"
                    )
            else:
                premium_percent = price_diff_percent * 100
                self.logger.warning(
                    f"🚫 {symbol} EXPENSIVE BUY BLOCKED: Grid ${grid_price:.4f} → "
                    f"Market ${current_price:.4f} (+{premium_percent:.2f}% premium)"
                )
                return False

        # Execute if we reach here
        return await self.execute_grid_order_with_db_logging(grid_trader, signal)

    async def execute_grid_order_with_db_logging(self, grid_trader, signal):
        """Execute grid order with comprehensive database logging"""
        start_time = time.time()

        try:
            symbol = grid_trader.symbol
            action = signal["action"]
            quantity = signal["quantity"]

            self.logger.info(
                f"🎯 Executing {action} order: {quantity} {symbol} at level {signal['level']}"
            )

            # Log trade attempt to database
            self.db_logger.log_bot_event(
                "TRADE_ATTEMPT",
                f"Attempting {action} {quantity} {symbol} at level {signal['level']}",
                "TRADING",
                "INFO",
                {
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "grid_level": signal["level"],
                    "grid_price": signal["price"],
                },
                self.session_id,
            )

            # Precision fix
            if action == "BUY":
                if symbol == "ADAUSDT":
                    quantity = round(quantity, 0)
                elif symbol == "AVAXUSDT":
                    quantity = round(quantity, 2)
            else:
                if symbol == "ADAUSDT":
                    quantity = round(quantity, 0)
                elif symbol == "AVAXUSDT":
                    quantity = round(quantity, 2)

            # Balance check
            current_price = self.binance.get_price(symbol)
            order_value = quantity * current_price

            if order_value < 8:
                error_msg = f"Order value ${order_value:.2f} below minimum ($8)"
                self.logger.warning(f"⚠️ {error_msg}")

                # Log error to database
                self.db_logger.log_bot_event(
                    "TRADE_ERROR",
                    error_msg,
                    "TRADING",
                    "WARNING",
                    {
                        "symbol": symbol,
                        "action": action,
                        "order_value": order_value,
                        "minimum_required": 8,
                    },
                    self.session_id,
                )

                if telegram_notifier.enabled:
                    await telegram_notifier.notify_trade_error(
                        symbol=symbol,
                        action=action,
                        error_message=error_msg,
                        price=signal["price"],
                        quantity=quantity,
                    )
                return False

            # Execute order with retry logic
            order = None
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    if action == "BUY":
                        order = self.binance.place_market_buy(symbol, quantity)
                    else:
                        order = self.binance.place_market_sell(symbol, quantity)
                    break

                except Exception as order_error:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        self.logger.warning(
                            f"⚠️ Order attempt {attempt + 1} failed: {order_error}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        error_msg = f"Order failed after {max_retries} attempts: {str(order_error)}"

                        # Log final failure to database
                        self.db_logger.log_bot_event(
                            "TRADE_FAILED",
                            error_msg,
                            "TRADING",
                            "ERROR",
                            {
                                "symbol": symbol,
                                "action": action,
                                "attempts": max_retries,
                                "final_error": str(order_error),
                            },
                            self.session_id,
                        )

                        if telegram_notifier.enabled:
                            await telegram_notifier.notify_trade_error(
                                symbol=symbol,
                                action=action,
                                error_message=error_msg,
                                price=signal["price"],
                                quantity=quantity,
                            )
                        self.consecutive_failures += 1
                        return False

            # Process successful order
            if order and order.get("status") == "FILLED":
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Calculate average fill price
                filled_quantity = float(order.get("executedQty", quantity))
                fills = order.get("fills", [])

                if fills:
                    total_qty = 0
                    total_value = 0
                    commission = 0
                    commission_asset = ""

                    for fill in fills:
                        qty = float(fill["qty"])
                        price = float(fill["price"])
                        total_qty += qty
                        total_value += qty * price
                        commission += float(fill.get("commission", 0))
                        commission_asset = fill.get("commissionAsset", "")

                    avg_price = (
                        total_value / total_qty if total_qty > 0 else current_price
                    )
                else:
                    avg_price = current_price
                    commission = 0
                    commission_asset = ""

                order_id = order.get("orderId", "N/A")

                # Calculate profit for sell orders
                profit = None
                if action == "SELL":
                    buy_orders = [
                        o for o in grid_trader.filled_orders if o.get("side") == "BUY"
                    ]
                    if buy_orders:
                        recent_buy = max(
                            buy_orders, key=lambda x: x.get("timestamp", 0)
                        )
                        buy_price = recent_buy.get("price", avg_price * 0.975)
                        profit = (avg_price - buy_price) * filled_quantity

                # Log successful trade to database
                trade_id = self.db_logger.log_trade_execution(
                    symbol=symbol,
                    side=action,
                    quantity=filled_quantity,
                    price=avg_price,
                    order_result=order,
                    grid_level=signal["level"],
                    execution_time_ms=execution_time_ms,
                    session_id=self.session_id,
                )

                # Update in-memory grid state
                filled_order = {
                    "symbol": symbol,
                    "side": action,
                    "quantity": filled_quantity,
                    "price": avg_price,
                    "level": signal["level"],
                    "timestamp": time.time(),
                    "order_id": str(order_id),
                    "commission": commission,
                    "commission_asset": commission_asset,
                    "total_value": filled_quantity * avg_price,
                    "profit_loss": profit or 0,
                    "execution_time_ms": execution_time_ms,
                }

                grid_trader.filled_orders.append(filled_order)

                # Send success notification
                if telegram_notifier.enabled:
                    await telegram_notifier.notify_trade_success(
                        symbol=symbol,
                        action=action,
                        price=avg_price,
                        quantity=filled_quantity,
                        order_id=str(order_id),
                        profit=profit,
                    )

                self.logger.info(
                    f"✅ {action} order filled: {filled_quantity} {symbol} @ ${avg_price:.6f} "
                    f"(${filled_quantity * avg_price:.2f}) [Level: {signal['level']}] [DB ID: {trade_id}]"
                )

                self.consecutive_failures = 0
                return True

            else:
                error_msg = (
                    order.get("msg", "Unknown order error")
                    if order
                    else "Order returned None"
                )

                # Log order failure to database
                self.db_logger.log_bot_event(
                    "ORDER_FAILED",
                    f"Order failed: {error_msg}",
                    "TRADING",
                    "ERROR",
                    {
                        "symbol": symbol,
                        "action": action,
                        "error": error_msg,
                        "order_status": order.get("status") if order else None,
                    },
                    self.session_id,
                )

                if telegram_notifier.enabled:
                    await telegram_notifier.notify_trade_error(
                        symbol=symbol,
                        action=action,
                        error_message=error_msg,
                        price=signal["price"],
                        quantity=quantity,
                    )

                self.logger.error(f"❌ Grid order failed: {error_msg}")
                self.consecutive_failures += 1
                return False

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Exception in order execution: {str(e)}"

            # Log critical error to database
            self.db_logger.log_bot_event(
                "CRITICAL_TRADE_ERROR",
                error_msg,
                "TRADING",
                "CRITICAL",
                {
                    "symbol": grid_trader.symbol,
                    "action": signal["action"],
                    "execution_time_ms": execution_time_ms,
                    "error": str(e),
                },
                self.session_id,
            )

            if telegram_notifier.enabled:
                await telegram_notifier.notify_trade_error(
                    symbol=grid_trader.symbol,
                    action=signal["action"],
                    error_message=error_msg,
                    price=signal["price"],
                    quantity=signal["quantity"],
                )

            self.logger.error(f"❌ Critical error in execute_grid_order: {e}")
            self.consecutive_failures += 1
            return False

    async def run_cycle(self):
        """Simplified run cycle with database logging"""
        try:
            # Initialize grids on first cycle
            if not self.grid_initialized:
                success = await self.initialize_grids()
                if not success:
                    return False

            # Core trading logic
            await self.check_grid_strategies()

            # Log cycle completion to database
            self.db_logger.log_bot_event(
                "CYCLE_COMPLETE",
                "Trading cycle completed successfully",
                "SYSTEM",
                "DEBUG",
                {
                    "ada_orders": len(self.ada_grid.filled_orders),
                    "avax_orders": len(self.avax_grid.filled_orders),
                    "consecutive_failures": self.consecutive_failures,
                },
                self.session_id,
            )

            return True

        except Exception as e:
            self.logger.error(f"❌ Critical error in run_cycle: {e}")

            # Log cycle error to database
            self.db_logger.log_bot_event(
                "CYCLE_ERROR",
                f"Trading cycle failed: {str(e)}",
                "SYSTEM",
                "ERROR",
                {"error": str(e)},
                self.session_id,
            )

            self.consecutive_failures += 1
            return False

    async def run(self):
        """Main bot loop with database logging"""
        self.logger.info("🚀 Starting trading bot...")

        # Log bot start to database
        self.db_logger.log_bot_event(
            "BOT_START",
            "Trading bot started",
            "SYSTEM",
            "INFO",
            {
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat(),
                "version": "database_v1.0",
            },
            self.session_id,
        )

        # Start telegram command processor
        command_task = asyncio.create_task(
            self.telegram_commands.start_command_processor()
        )
        self.logger.info("🤖 Telegram command processor started")

        # Send startup notification
        if telegram_notifier.enabled:
            try:
                await telegram_notifier.notify_bot_status(
                    "started",
                    "🤖 Trading Bot Online!\n"
                    "✅ Simplified & reliable architecture\n"
                    "✅ All data persisted to database\n"
                    "Commands: /start for help",
                )
            except Exception as e:
                self.logger.warning(f"Startup notification failed: {e}")

        # Test connection
        if not await self._test_connection_with_retries():
            return

        # Initialize bot state
        self.running = True
        bot_alive = True
        cycle_count = 0

        try:
            while bot_alive:
                if self.running:
                    cycle_count += 1
                    self.logger.info(f"📊 Cycle {cycle_count} starting...")

                    try:
                        await self.run_cycle()
                        if self.consecutive_failures > 0:
                            self.logger.info(
                                "✅ Cycle successful, resetting failure count"
                            )
                            self.consecutive_failures = 0
                    except Exception as e:
                        self.consecutive_failures += 1
                        self.logger.error(f"❌ Trading cycle {cycle_count} failed: {e}")

                    # Emergency stop check
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        critical_msg = f"🚨 Too many consecutive failures ({self.consecutive_failures}) - stopping trading"
                        self.logger.critical(critical_msg)

                        self.db_logger.log_bot_event(
                            "EMERGENCY_STOP",
                            critical_msg,
                            "SYSTEM",
                            "CRITICAL",
                            {"consecutive_failures": self.consecutive_failures},
                            self.session_id,
                        )

                        if telegram_notifier.enabled:
                            await telegram_notifier.notify_bot_status(
                                "error", critical_msg
                            )

                        self.running = False
                        continue

                    await asyncio.sleep(30)

                else:
                    # Check for restart request
                    if (
                        hasattr(self.telegram_commands, "restart_requested")
                        and self.telegram_commands.restart_requested
                    ):
                        self.logger.info(
                            "🔄 Restart requested via Telegram, resuming trading..."
                        )
                        self.running = True
                        self.telegram_commands.restart_requested = False
                        self.consecutive_failures = 0
                        continue

                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("👋 Shutting down trading bot (KeyboardInterrupt)...")
            bot_alive = False

        except Exception as e:
            self.logger.error(f"❌ Unexpected error in main loop: {e}")

            self.db_logger.log_bot_event(
                "CRITICAL_ERROR",
                f"Unexpected error: {str(e)}",
                "SYSTEM",
                "CRITICAL",
                {"error_type": type(e).__name__},
                self.session_id,
            )

            bot_alive = False

        finally:
            # Cleanup
            self.running = False
            self.telegram_commands.stop_command_processor()
            command_task.cancel()

            # Log bot stop to database
            self.db_logger.log_bot_event(
                "BOT_STOP",
                "Trading bot stopped",
                "SYSTEM",
                "INFO",
                {
                    "total_cycles": cycle_count,
                    "session_duration": time.time() - self.start_time,
                },
                self.session_id,
            )

            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "stopped",
                    f"Trading Bot Stopped\n"
                    f"Total cycles: {cycle_count}\n"
                    f"Session time: {time.time() - self.start_time:.0f}s\n"
                    f"All data saved to database",
                )

            self.logger.info("🛑 Trading bot stopped")

    async def _test_connection_with_retries(self):
        """Test connection with retries"""
        for attempt in range(3):
            try:
                if self.binance.test_connection():
                    self.logger.info("✅ Binance connection successful")
                    return True
                else:
                    if attempt < 2:
                        self.logger.warning(
                            f"⚠️ Connection attempt {attempt + 1} failed, retrying..."
                        )
                        await asyncio.sleep(5)
            except Exception as e:
                if attempt < 2:
                    self.logger.error(f"❌ Connection test error: {e}")
                    await asyncio.sleep(5)

        self.logger.error("❌ Binance connection failed after all attempts")

        # Log connection failure to database
        self.db_logger.log_bot_event(
            "CONNECTION_FAILED",
            "Binance connection failed after all attempts",
            "SYSTEM",
            "CRITICAL",
            {},
            self.session_id,
        )

        if telegram_notifier.enabled:
            await telegram_notifier.notify_bot_status(
                "error", "Binance connection failed"
            )
        return False


def main():
    """Main entry point"""
    if not env_loaded:
        print("❌ Could not load .env file. Please check the location.")
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
