"""Enhanced Binance client with simplified timestamp handling"""

import logging
import os
import time
from pathlib import Path

import requests
from binance.client import Client
from dotenv import load_dotenv


class BinanceManager:
    def __init__(self):
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.testnet = os.getenv("ENVIRONMENT", "development") == "development"

        if not self.api_key or not self.secret_key:
            raise ValueError("Binance API keys not found in environment variables")

        try:
            # Initialize client
            self.client = Client(self.api_key, self.secret_key, testnet=self.testnet)

            # SIMPLE TIMESTAMP FIX - Set offset once
            try:
                base_url = (
                    "https://testnet.binance.vision"
                    if self.testnet
                    else "https://api.binance.com"
                )
                server_response = requests.get(f"{base_url}/api/v3/time", timeout=10)
                server_time = server_response.json()["serverTime"]
                local_time = int(time.time() * 1000)

                # Set client timestamp offset
                self.client.timestamp_offset = server_time - local_time
                print(f"🔄 Timestamp offset set: {self.client.timestamp_offset}ms")

            except Exception as e:
                print(f"⚠️ Could not sync timestamp: {e}")
                # Fallback: set a conservative offset
                self.client.timestamp_offset = -5000  # 5 seconds behind

            self.logger = logging.getLogger(__name__)
            self.logger.info(f"✅ Binance client initialized (testnet: {self.testnet})")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to Binance: {e}")

    def _make_authenticated_request(self, method_name, max_retries=3, **kwargs):
        """Simple authenticated request - let the client handle timestamps"""
        method = getattr(self.client, method_name)

        # Set large receive window and let client handle timestamp
        kwargs["recvWindow"] = 60000

        # Remove any manual timestamp - let the client handle it
        if "timestamp" in kwargs:
            del kwargs["timestamp"]

        try:
            return method(**kwargs)
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            raise e

    def test_connection(self):
        """Test API connection"""
        try:
            status = self.client.get_system_status()
            return status["status"] == 0
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def get_account(self):
        """Get account information with timestamp correction"""
        return self._make_authenticated_request("get_account")

    def get_account_balance(self):
        """Get account balances with enhanced error handling"""
        account = self.get_account()
        if account:
            balances = []
            for balance in account["balances"]:
                free = float(balance["free"])
                locked = float(balance["locked"])
                if free > 0 or locked > 0:
                    balances.append(
                        {
                            "asset": balance["asset"],
                            "free": free,
                            "locked": locked,
                            "total": free + locked,
                        }
                    )
            return balances
        return []

    def get_ticker(self, symbol="BTCUSDT"):
        """Get ticker price (no auth needed)"""
        return self.client.get_ticker(symbol=symbol)

    def get_price(self, symbol="BTCUSDT"):
        """Get current price for symbol (fixed for ADA/AVAX)"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error getting price for {symbol}: {e}")
            else:
                print(f"Error getting price for {symbol}: {e}")
            return None

    def get_open_orders(self, symbol=None):
        """Get open orders with timestamp correction"""
        return self._make_authenticated_request("get_open_orders", symbol=symbol)

    def create_order(self, **kwargs):
        """Create order with timestamp correction"""
        return self._make_authenticated_request("create_order", **kwargs)

    def cancel_order(self, symbol, orderId):
        """Cancel order with timestamp correction"""
        return self._make_authenticated_request(
            "cancel_order", symbol=symbol, orderId=orderId
        )

    def get_klines(self, symbol, interval, limit=100):
        """Get kline data (no auth needed)"""
        return self.client.get_klines(symbol=symbol, interval=interval, limit=limit)

    def place_market_buy(self, symbol, quantity):
        """Place market buy order with precision handling"""
        try:
            # Round to correct precision FIRST
            if symbol == "ADAUSDT":
                quantity = round(float(quantity), 0)  # Whole numbers
            elif symbol == "AVAXUSDT":
                quantity = round(float(quantity), 2)  # 2 decimals
            else:
                quantity = round(float(quantity), 2)  # Default 2 decimals

            # Validate order value
            current_price = self.get_price(symbol)
            if current_price:
                order_value = quantity * current_price
                if order_value < 5:
                    self.logger.warning(
                        f"Order value ${order_value:.2f} below minimum ($5)"
                    )
                    return None

            if self.testnet:
                self.logger.info(
                    f"TESTNET: Would buy {quantity} {symbol} (~${order_value:.2f})"
                )
                return {
                    "status": "FILLED",
                    "symbol": symbol,
                    "side": "BUY",
                    "executedQty": str(quantity),
                    "fills": [{"price": str(current_price)}],
                    "orderId": 12345,
                }

            # For live trading, place actual order
            order = self._make_authenticated_request(
                "order_market_buy", symbol=symbol, quantity=quantity
            )
            self.logger.info(f"Market buy order placed: {order}")
            return order

        except Exception as e:
            self.logger.error(f"Error placing buy order: {e}")
            if "LOT_SIZE" in str(e):
                self.logger.error(f"Quantity precision error for {symbol}")
            return None

    def place_market_sell(self, symbol, quantity):
        """Place market sell order with precision handling"""
        try:
            # Round to correct precision FIRST
            if symbol == "ADAUSDT":
                quantity = round(float(quantity), 0)  # Whole numbers
            elif symbol == "AVAXUSDT":
                quantity = round(float(quantity), 2)  # 2 decimals
            else:
                quantity = round(float(quantity), 2)  # Default 2 decimals

            # Validate order value
            current_price = self.get_price(symbol)
            if current_price:
                order_value = quantity * current_price
                if order_value < 5:
                    self.logger.warning(
                        f"Order value ${order_value:.2f} below minimum ($5)"
                    )
                    return None

            if self.testnet:
                self.logger.info(
                    f"TESTNET: Would sell {quantity} {symbol} (~${order_value:.2f})"
                )
                return {
                    "status": "FILLED",
                    "symbol": symbol,
                    "side": "SELL",
                    "executedQty": str(quantity),
                    "fills": [{"price": str(current_price)}],
                    "orderId": 12346,
                }

            # For live trading, place actual order
            order = self._make_authenticated_request(
                "order_market_sell", symbol=symbol, quantity=quantity
            )
            self.logger.info(f"Market sell order placed: {order}")
            return order

        except Exception as e:
            self.logger.error(f"Error placing sell order: {e}")
            if "LOT_SIZE" in str(e):
                self.logger.error(f"Quantity precision error for {symbol}")
            return None


def test_binance_connection():
    """Test function for standalone testing"""
    try:
        bm = BinanceManager()
        print(f"🌐 Connected to {'Testnet' if bm.testnet else 'Live Trading'}")

        # Test market data
        btc_price = bm.get_price("BTCUSDT")
        print(f"📈 BTC Price: ${btc_price:,.2f}")

        # Test account access
        account = bm.get_account()
        if account:
            print("✅ Account access successful")
            return True
        else:
            print("❌ Account access failed")
            return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_binance_connection()
