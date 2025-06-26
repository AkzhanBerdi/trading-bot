
# Quick fix for LOT_SIZE errors - add to your BinanceManager class

def round_quantity(self, symbol, quantity):
    """Round quantity to correct precision for symbol"""
    # Binance precision requirements for your trading pairs
    if symbol == 'ADAUSDT':
        return round(float(quantity), 0)  # Whole numbers
    elif symbol == 'AVAXUSDT':  
        return round(float(quantity), 2)  # 2 decimal places
    else:
        return round(float(quantity), 2)  # Default 2 decimals

def place_market_buy_fixed(self, symbol, usd_amount):
    """Fixed market buy using USD amount"""
    try:
        # Get current price
        current_price = self.get_price(symbol)
        if not current_price:
            return None
        
        # Calculate quantity
        raw_quantity = usd_amount / current_price
        quantity = self.round_quantity(symbol, raw_quantity)
        
        self.logger.info(f"Buy order: ${usd_amount} → {quantity} {symbol}")
        
        if self.testnet:
            return {
                "status": "FILLED", 
                "symbol": symbol, 
                "side": "BUY",
                "executedQty": str(quantity),
                "fills": [{"price": str(current_price)}],
                "orderId": 12345
            }
        
        # Place actual order
        order = self.client.order_market_buy(
            symbol=symbol,
            quantity=quantity,
            timestamp=self._get_timestamp(),
            recvWindow=60000
        )
        return order
        
    except Exception as e:
        self.logger.error(f"Error in fixed buy order: {e}")
        return None

def place_market_sell_fixed(self, symbol, quantity):
    """Fixed market sell with proper precision"""
    try:
        # Round to correct precision
        rounded_quantity = self.round_quantity(symbol, quantity)
        
        self.logger.info(f"Sell order: {rounded_quantity} {symbol}")
        
        if self.testnet:
            current_price = self.get_price(symbol)
            return {
                "status": "FILLED", 
                "symbol": symbol, 
                "side": "SELL",
                "executedQty": str(rounded_quantity),
                "fills": [{"price": str(current_price)}],
                "orderId": 12346
            }
        
        # Place actual order
        order = self.client.order_market_sell(
            symbol=symbol,
            quantity=rounded_quantity,
            timestamp=self._get_timestamp(),
            recvWindow=60000
        )
        return order
        
    except Exception as e:
        self.logger.error(f"Error in fixed sell order: {e}")
        return None
