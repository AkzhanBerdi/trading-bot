# src/trading_bot/main.py
import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from utils.enhanced_trade_logger import EnhancedTradeLogger
from utils.grid_persistence import GridStatePersistence
from utils.telegram_commands import TelegramBotCommands


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
        # Add these new components:
        self.start_time = time.time()
        self.session_id = f"session_{int(time.time())}_{os.getpid()}"
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5

        # Enhanced logging
        self.trade_logger = EnhancedTradeLogger()

        # Grid persistence
        self.ada_grid_persistence = GridStatePersistence("ADAUSDT")
        self.avax_grid_persistence = GridStatePersistence("AVAXUSDT")

        # Telegram commands
        self.telegram_commands = TelegramBotCommands(
            self, telegram_notifier, self.trade_logger
        )

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
        """Initialize trading grids with state restoration for both ADA and AVAX"""
        try:
            self.logger.info("🔄 Initializing trading grids with state restoration...")

            # Get current prices
            ada_price = self.binance.get_price("ADAUSDT")
            avax_price = self.binance.get_price("AVAXUSDT")

            if not ada_price or not avax_price:
                self.logger.error("❌ Could not get current prices")
                return False

            self.logger.info(
                f"💰 Current prices: ADA=${ada_price:.4f}, AVAX=${avax_price:.4f}"
            )

            # Restore ADA grid state
            ada_state = self.ada_grid_persistence.load_grid_state(ada_price)
            if ada_state:
                self.ada_grid.filled_orders = ada_state["filled_orders"]
                self.ada_grid.buy_levels = ada_state["buy_levels"]
                self.ada_grid.sell_levels = ada_state["sell_levels"]
                self.logger.info(
                    f"🔄 ADA grid restored: {len(ada_state['filled_orders'])} filled orders"
                )

                # Log details of restored orders
                buy_orders = len(
                    [o for o in ada_state["filled_orders"] if o.get("side") == "BUY"]
                )
                sell_orders = len(
                    [o for o in ada_state["filled_orders"] if o.get("side") == "SELL"]
                )
                self.logger.info(
                    f"   📈 ADA: {buy_orders} BUY, {sell_orders} SELL orders restored"
                )
            else:
                # Setup new ADA grid
                self.ada_grid.setup_grid(ada_price)
                self.logger.info("🆕 ADA: Created new grid")

            # Restore AVAX grid state
            avax_state = self.avax_grid_persistence.load_grid_state(avax_price)
            if avax_state:
                self.avax_grid.filled_orders = avax_state["filled_orders"]
                self.avax_grid.buy_levels = avax_state["buy_levels"]
                self.avax_grid.sell_levels = avax_state["sell_levels"]
                self.logger.info(
                    f"🔄 AVAX grid restored: {len(avax_state['filled_orders'])} filled orders"
                )

                # Log details of restored orders
                buy_orders = len(
                    [o for o in avax_state["filled_orders"] if o.get("side") == "BUY"]
                )
                sell_orders = len(
                    [o for o in avax_state["filled_orders"] if o.get("side") == "SELL"]
                )
                self.logger.info(
                    f"   📈 AVAX: {buy_orders} BUY, {sell_orders} SELL orders restored"
                )
            else:
                # Setup new AVAX grid
                self.avax_grid.setup_grid(avax_price)
                self.logger.info("🆕 AVAX: Created new grid")

            self.grid_initialized = True

            # Send notification about grid restoration
            if telegram_notifier.enabled:
                ada_status = "RESTORED" if ada_state else "NEW"
                avax_status = "RESTORED" if avax_state else "NEW"
                ada_orders = len(ada_state["filled_orders"]) if ada_state else 0
                avax_orders = len(avax_state["filled_orders"]) if avax_state else 0

                await telegram_notifier.notify_info(
                    "🎯 Grid Initialization Complete\n"
                    f"ADA: {ada_status} ({ada_orders} orders)\n"
                    f"AVAX: {avax_status} ({avax_orders} orders)\n"
                    f"Ready for trading! 🚀",
                )

            return True

        except Exception as e:
            self.logger.error(f"❌ Grid initialization failed: {e}")
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "error", f"Grid initialization failed: {e}"
                )
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
        """Enhanced grid order execution with comprehensive error handling and logging"""
        start_time = time.time()

        try:
            symbol = grid_trader.symbol
            action = signal["action"]
            quantity = signal["quantity"]

            self.logger.info(
                f"🎯 Executing {action} order: {quantity} {symbol} at level {signal['level']}"
            )

            # 1. Timestamp sync check
            if (
                hasattr(self.binance, "last_sync")
                and time.time() - self.binance.last_sync > 30
            ):
                self.binance._sync_time_offset()
                self.logger.info("🔄 Refreshed timestamp sync before trade")

            # 2. Precision fix (your existing logic)
            if action == "BUY":
                if symbol == "ADAUSDT":
                    quantity = round(quantity, 0)  # Whole numbers for ADA
                elif symbol == "AVAXUSDT":
                    quantity = round(quantity, 2)  # 2 decimals for AVAX
            else:  # SELL
                if symbol == "ADAUSDT":
                    quantity = round(quantity, 0)
                elif symbol == "AVAXUSDT":
                    quantity = round(quantity, 2)

            # 3. Order size validation
            current_price = self.binance.get_price(symbol)
            if current_price:
                order_value = quantity * current_price
                if order_value < 8:  # Safe minimum
                    error_msg = f"Order value ${order_value:.2f} below minimum ($8)"
                    self.logger.warning(f"⚠️ {error_msg}")
                    await telegram_notifier.notify_trade_error(
                        symbol=symbol,
                        action=action,
                        error_message=error_msg,
                        price=signal["price"],
                        quantity=quantity,
                    )
                    return False

            # 4. Balance check
            try:
                balances = self.binance.get_account_balance()

                if action == "BUY":
                    usdt_balance = next(
                        (b["free"] for b in balances if b["asset"] == "USDT"), 0
                    )
                    required_usdt = quantity * current_price * 1.01  # 1% buffer

                    if usdt_balance < required_usdt:
                        error_msg = f"Insufficient USDT: {usdt_balance:.2f} < {required_usdt:.2f}"
                        self.logger.error(f"❌ {error_msg}")
                        await telegram_notifier.notify_trade_error(
                            symbol=symbol,
                            action=action,
                            error_message=error_msg,
                            price=signal["price"],
                            quantity=quantity,
                        )
                        return False
                else:  # SELL
                    base_asset = symbol.replace("USDT", "")
                    asset_balance = next(
                        (b["free"] for b in balances if b["asset"] == base_asset), 0
                    )

                    if asset_balance < quantity:
                        error_msg = (
                            f"Insufficient {base_asset}: {asset_balance} < {quantity}"
                        )
                        self.logger.error(f"❌ {error_msg}")
                        await telegram_notifier.notify_trade_error(
                            symbol=symbol,
                            action=action,
                            error_message=error_msg,
                            price=signal["price"],
                            quantity=quantity,
                        )
                        return False
            except Exception as e:
                self.logger.warning(f"⚠️ Could not check balance: {e}")

            # 5. Execute order with retry logic
            order = None
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    if action == "BUY":
                        order = self.binance.place_market_buy(symbol, quantity)
                    else:
                        order = self.binance.place_market_sell(symbol, quantity)
                    break  # Success, exit retry loop

                except Exception as order_error:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                        self.logger.warning(
                            f"⚠️ Order attempt {attempt + 1} failed: {order_error}"
                        )
                        self.logger.info(f"   Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Final attempt failed
                        error_msg = f"Order failed after {max_retries} attempts: {str(order_error)}"
                        await telegram_notifier.notify_trade_error(
                            symbol=symbol,
                            action=action,
                            error_message=error_msg,
                            price=signal["price"],
                            quantity=quantity,
                        )
                        self.consecutive_failures += 1
                        return False

            # 6. Process successful order
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
                    # Try to find matching buy order for profit calculation
                    buy_orders = [
                        o for o in grid_trader.filled_orders if o.get("side") == "BUY"
                    ]
                    if buy_orders:
                        # Use most recent buy price for simplicity
                        recent_buy = max(
                            buy_orders, key=lambda x: x.get("timestamp", 0)
                        )
                        buy_price = recent_buy.get("price", avg_price * 0.975)
                        profit = (avg_price - buy_price) * filled_quantity

                # Record filled order with enhanced details
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

                # Log trade to database
                trade_id = self.trade_logger.log_trade_execution(
                    symbol=symbol,
                    side=action,
                    quantity=filled_quantity,
                    price=avg_price,
                    order_result=order,
                    grid_level=signal["level"],
                    execution_time_ms=execution_time_ms,
                    session_id=self.session_id,
                )

                # Save grid state after successful trade
                if symbol == "ADAUSDT":
                    self.ada_grid_persistence.save_grid_state(
                        grid_trader, self.session_id
                    )
                elif symbol == "AVAXUSDT":
                    self.avax_grid_persistence.save_grid_state(
                        grid_trader, self.session_id
                    )

                # Send success notification
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
                    f"(${filled_quantity * avg_price:.2f}) [Level: {signal['level']}] [ID: {trade_id}]"
                )

                # Reset consecutive failures on success
                self.consecutive_failures = 0
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

                self.logger.error(f"❌ Grid order failed: {error_msg}")
                self.consecutive_failures += 1
                return False

        except Exception as e:
            # Catch-all exception handler
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Exception in order execution: {str(e)}"

            await telegram_notifier.notify_trade_error(
                symbol=grid_trader.symbol,
                action=signal["action"],
                error_message=error_msg,
                price=signal["price"],
                quantity=signal["quantity"],
            )

            # Log error to database
            self.trade_logger.log_bot_event(
                "TRADE_ERROR",
                error_msg,
                "ERROR",
                "ERROR",
                {
                    "symbol": grid_trader.symbol,
                    "action": signal["action"],
                    "execution_time_ms": execution_time_ms,
                },
                self.session_id,
            )

            self.logger.error(
                f"❌ Critical error in execute_grid_order_with_notifications: {e}"
            )
            self.consecutive_failures += 1
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
        """Simplified run cycle - FIXED VERSION"""
        try:
            # Initialize grids on first cycle
            if not self.grid_initialized:
                success = await self.initialize_grids()
                if not success:
                    return False

            # Get portfolio status with error handling
            try:
                portfolio, total_value = await self.get_portfolio_status()
                if total_value > 0:
                    self.logger.info(f"💰 Portfolio value: ${total_value:.2f}")
            except Exception as e:
                # Check if it's a network error
                if any(
                    keyword in str(e).lower()
                    for keyword in ["timeout", "connection", "network"]
                ):
                    self.logger.warning(f"⚠️ Network issue getting portfolio: {e}")
                    # Try network recovery only if Binance fails
                    if not await self.handle_network_failure():
                        return False
                else:
                    self.logger.error(f"❌ Portfolio error: {e}")
                    return False

            # Execute grid strategies with error handling
            try:
                await self.check_grid_strategies()
            except Exception as e:
                if any(
                    keyword in str(e).lower()
                    for keyword in ["timeout", "connection", "network"]
                ):
                    self.logger.warning(f"⚠️ Network issue in grid strategies: {e}")
                    if not await self.handle_network_failure():
                        return False
                else:
                    raise e

            # Log grid status with error handling
            try:
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
                self.logger.warning(f"⚠️ Error getting grid status: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")

            # Only check network if it's clearly a network error
            if any(
                keyword in str(e).lower()
                for keyword in ["timeout", "connection", "network", "resolve"]
            ):
                self.logger.warning("🌐 Potential network-related error detected")
                await self.handle_network_failure()

            return False

    async def run(self):
        """Enhanced main bot loop with proper start/stop functionality"""
        self.logger.info("🚀 Starting enhanced trading bot...")

        # Log bot start
        self.trade_logger.log_bot_event(
            "START",
            "Enhanced trading bot started",
            "SYSTEM",
            "INFO",
            {
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat(),
                "version": "enhanced_v2.0",
            },
            self.session_id,
        )

        # Start telegram command processor
        command_task = asyncio.create_task(
            self.telegram_commands.start_command_processor()
        )
        self.logger.info("🤖 Telegram command processor started")

        # Send safer startup notification
        if telegram_notifier.enabled:
            try:
                await telegram_notifier.notify_bot_status(
                    "started",
                    "🤖 Enhanced Trading Bot Online!\n"
                    "ADA Grid: 2.5% spacing\n"
                    "AVAX Grid: 2.0% spacing\n"
                    "Database: SQLite logging enabled\n"
                    "Commands: /start for help\n"
                    "Use /resume to start trading!",  # ← ADD THIS LINE
                )
            except Exception as e:
                self.logger.warning(f"Startup notification failed: {e}")

        # Test connection
        if not await self._test_connection_with_retries():
            return

        # Initialize bot state
        self.running = True  # Start in running state
        bot_alive = True  # Controls whether bot stays alive
        cycle_count = 0
        last_portfolio_update = 0
        last_health_check = 0

        try:
            # MAIN BOT LOOP - Always running
            while bot_alive:
                # TRADING SECTION - Only when self.running = True
                if self.running:
                    cycle_count += 1
                    cycle_start_time = time.time()

                    self.logger.info(f"📊 Cycle {cycle_count} starting...")

                    # Health check every 10 cycles (5 minutes)
                    if time.time() - last_health_check > 300:
                        await self._perform_health_check()
                        last_health_check = time.time()

                    # Run trading cycle
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

                        # Log error
                        self.trade_logger.log_bot_event(
                            "CYCLE_ERROR",
                            f"Trading cycle failed: {str(e)}",
                            "TRADING",
                            "ERROR",
                            {
                                "cycle": cycle_count,
                                "consecutive_failures": self.consecutive_failures,
                            },
                            self.session_id,
                        )

                    # Emergency stop check
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        critical_msg = f"🚨 Too many consecutive failures ({self.consecutive_failures}) - stopping trading"
                        self.logger.critical(critical_msg)

                        self.trade_logger.log_bot_event(
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

                        # Stop trading but keep bot alive
                        self.running = False
                        continue

                    # Portfolio update
                    current_time = time.time()
                    if (cycle_count % 2880 == 0) and telegram_notifier.enabled:
                        try:
                            await self.send_portfolio_update()
                            last_portfolio_update = current_time
                        except Exception as e:
                            self.logger.warning(f"⚠️ Portfolio update failed: {e}")

                    # Log cycle performance
                    cycle_time = time.time() - cycle_start_time
                    if cycle_time > 10:
                        self.logger.warning(
                            f"⏱️ Slow cycle {cycle_count}: {cycle_time:.2f}s"
                        )

                    # Wait before next cycle (30 seconds)
                    await asyncio.sleep(30)

                else:
                    # PAUSED SECTION - Trading stopped via /stop command
                    self.logger.debug(
                        "💤 Trading paused, waiting for /start_bot command..."
                    )

                    # Check if restart was requested via Telegram
                    if (
                        hasattr(self.telegram_commands, "restart_requested")
                        and self.telegram_commands.restart_requested
                    ):
                        self.logger.info(
                            "🔄 Restart requested via Telegram, resuming trading..."
                        )
                        self.running = True
                        self.telegram_commands.restart_requested = False
                        self.consecutive_failures = (
                            0  # Reset failures on manual restart
                        )
                        continue

                    # Just wait while paused
                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("👋 Shutting down trading bot (KeyboardInterrupt)...")
            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "stopped", "Bot shutdown requested by user"
                )
            bot_alive = False

        except Exception as e:
            self.logger.error(f"❌ Unexpected error in main loop: {e}")

            self.trade_logger.log_bot_event(
                "CRITICAL_ERROR",
                f"Unexpected error: {str(e)}",
                "SYSTEM",
                "CRITICAL",
                {"error_type": type(e).__name__},
                self.session_id,
            )

            if telegram_notifier.enabled:
                await telegram_notifier.notify_bot_status(
                    "error", f"Critical error: {str(e)[:100]}"
                )
            bot_alive = False

        finally:
            # CLEANUP
            self.running = False

            # Stop telegram command processor
            self.telegram_commands.stop_command_processor()
            command_task.cancel()

            # Log bot stop
            self.trade_logger.log_bot_event(
                "STOP",
                "Enhanced trading bot stopped",
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
                    f"Enhanced Trading Bot Stopped\n"
                    f"Total cycles: {cycle_count}\n"
                    f"Session time: {time.time() - self.start_time:.0f}s",
                )

            self.logger.info("🛑 Enhanced trading bot stopped")

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
        if telegram_notifier.enabled:
            await telegram_notifier.notify_bot_status(
                "error", "Binance connection failed"
            )
        return False

    async def _perform_health_check(self):
        """Perform health check"""
        try:
            test_price = self.binance.get_price("BTCUSDT")
            if test_price:
                self.logger.debug("✅ API health check passed")
            else:
                self.logger.warning("⚠️ API health check failed")
        except Exception as e:
            self.logger.warning(f"⚠️ API health check failed: {e}")

    def _calculate_average_price(self, order):
        """Calculate average fill price from order"""
        try:
            fills = order.get("fills", [])
            if not fills:
                return float(order.get("price", 0))

            total_qty = 0
            total_value = 0

            for fill in fills:
                qty = float(fill["qty"])
                price = float(fill["price"])
                total_qty += qty
                total_value += qty * price

            return total_value / total_qty if total_qty > 0 else 0

        except Exception as e:
            self.logger.error(f"Error calculating average price: {e}")
            return float(order.get("price", 0))

    async def check_api_health(self):
        """Quick API health check"""
        try:
            # Simple test - get BTC price (public endpoint)
            btc_price = self.binance.get_price("BTCUSDT")
            return btc_price is not None
        except:
            return False

    async def check_internet_connection(self) -> bool:
        """Simplified and reliable internet connectivity check"""
        try:
            # If Binance connection works, internet is working
            if hasattr(self, "binance") and self.binance.test_connection():
                return True

            # Fallback: simple ping test
            response = requests.get("https://httpbin.org/status/200", timeout=10)
            return response.status_code == 200

        except Exception as e:
            self.logger.debug(f"Internet check failed: {e}")
            return False

    async def handle_network_failure(self):
        """Handle network connection failures - IMPROVED"""
        self.logger.warning("🌐 Network connectivity issues detected")

        # Try Binance-specific recovery first
        try:
            if self.binance.test_connection():
                self.logger.info("✅ Binance connection is actually working")
                return True
        except:
            pass

        # Notify via Telegram if possible
        try:
            if telegram_notifier.enabled:
                await telegram_notifier.notify_warning(
                    "Network connectivity issues detected - attempting recovery"
                )
        except:
            pass  # Telegram might also be affected

        # Wait and retry with shorter intervals
        for retry_count in range(1, 6):  # Max 5 retries instead of 10
            wait_time = retry_count * 30  # 30s, 60s, 90s, 120s, 150s

            self.logger.info(f"🔄 Network retry {retry_count}/5 in {wait_time}s")
            await asyncio.sleep(wait_time)

            # Test Binance connection directly
            try:
                if self.binance.test_connection():
                    self.logger.info("✅ Network connectivity restored")
                    try:
                        if telegram_notifier.enabled:
                            await telegram_notifier.notify_info(
                                "✅ Network connectivity restored"
                            )
                    except:
                        pass
                    return True
            except Exception as e:
                self.logger.debug(f"Retry {retry_count} failed: {e}")
                continue

        self.logger.error(
            "❌ Network connectivity could not be restored after 5 attempts"
        )
        return False


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
