"""Enhanced Binance client with timestamp handling"""

import os
import logging
import time
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

class BinanceManager:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.testnet = os.getenv('ENVIRONMENT', 'development') == 'development'
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Binance API keys not found in environment variables")
        
        try:
            # Initialize client
            self.client = Client(
                self.api_key, 
                self.secret_key,
                testnet=self.testnet
            )
            
            # Time synchronization
            self.time_offset = 0
            self.last_sync = 0
            self.sync_interval = 30  # seconds
            self._sync_time_offset()
            
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"✅ Binance client initialized (testnet: {self.testnet})")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Binance: {e}")
    
    def _sync_time_offset(self):
        """Calculate time offset with Binance servers"""
        try:
            base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"
            response = requests.get(f"{base_url}/api/v3/time", timeout=10)
            
            if response.status_code == 200:
                server_time = response.json()['serverTime']
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
                self.last_sync = time.time()
                
                if hasattr(self, 'logger'):
                    self.logger.info(f"🔄 Time offset synced: {self.time_offset}ms")
                else:
                    print(f"🔄 Time offset synced: {self.time_offset}ms")
                return True
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f"⚠️ Time sync failed: {e}")
            else:
                print(f"⚠️ Time sync failed: {e}")
        return False
    
    def _get_timestamp(self):
        """Get corrected timestamp"""
        # Re-sync if needed
        if time.time() - self.last_sync > self.sync_interval:
            self._sync_time_offset()
        
        return int(time.time() * 1000) + self.time_offset
    
    def _make_authenticated_request(self, method_name, max_retries=3, **kwargs):
        """Make authenticated request with timestamp retry logic"""
        method = getattr(self.client, method_name)
        
        for attempt in range(max_retries):
            try:
                # Add corrected timestamp and larger recv window
                if 'timestamp' not in kwargs:
                    kwargs['timestamp'] = self._get_timestamp()
                if 'recvWindow' not in kwargs:
                    kwargs['recvWindow'] = 60000  # 60 second window
                
                return method(**kwargs)
                
            except BinanceAPIException as e:
                if e.code == -1021:  # Timestamp error
                    self.logger.warning(f"⚠️ Timestamp error on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        self.logger.info("🔄 Re-syncing time and retrying...")
                        self._sync_time_offset()
                        kwargs['timestamp'] = self._get_timestamp()
                        time.sleep(0.5)
                        continue
                    else:
                        self.logger.error("❌ All timestamp retry attempts failed")
                        raise e
                else:
                    raise e
            except Exception as e:
                self.logger.error(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    raise e
        
        return None
    
    def test_connection(self):
        """Test API connection"""
        try:
            status = self.client.get_system_status()
            return status['status'] == 0
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_account(self):
        """Get account information with timestamp correction"""
        return self._make_authenticated_request('get_account')
    
    def get_account_balance(self):
        """Get account balances with enhanced error handling"""
        account = self.get_account()
        if account:
            balances = []
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    balances.append({
                        'asset': balance['asset'],
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    })
            return balances
        return []
    
    def get_ticker(self, symbol="BTCUSDT"):
        """Get ticker price (no auth needed)"""
        return self.client.get_ticker(symbol=symbol)
    
    def get_price(self, symbol="BTCUSDT"):
        """Get current price for symbol (fixed for ADA/AVAX)"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f'Error getting price for {symbol}: {e}')
            else:
                print(f'Error getting price for {symbol}: {e}')
            return None
    
    def get_open_orders(self, symbol=None):
        """Get open orders with timestamp correction"""
        return self._make_authenticated_request('get_open_orders', symbol=symbol)
    
    def create_order(self, **kwargs):
        """Create order with timestamp correction"""
        return self._make_authenticated_request('create_order', **kwargs)
    
    def cancel_order(self, symbol, orderId):
        """Cancel order with timestamp correction"""
        return self._make_authenticated_request('cancel_order', symbol=symbol, orderId=orderId)
    
    def get_klines(self, symbol, interval, limit=100):
        """Get kline data (no auth needed)"""
        return self.client.get_klines(symbol=symbol, interval=interval, limit=limit)

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
