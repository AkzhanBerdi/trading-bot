
def log_trade_to_your_database(symbol, side, quantity, price, total_value, order_id=None, notes=""):
    """Log trade using your actual database schema"""
    import sqlite3
    from datetime import datetime
    
    try:
        conn = sqlite3.connect("data/trading_history.db")
        cursor = conn.cursor()
        
        # Use your actual column names
        cursor.execute("""
        INSERT INTO trades (
            timestamp, datetime, symbol, side, quantity, price, total_value, 
            order_id, notes, status, session_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),  # timestamp
            datetime.now().isoformat(),  # datetime
            symbol,
            side,  # BUY or SELL
            quantity,
            price,
            total_value,
            order_id,
            notes,
            "FILLED",
            "enhanced_bot"
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Logged: {side} {quantity} {symbol} @ ${price:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ Logging failed: {e}")
        return False

# Test the logging function
log_trade_to_your_database("TESTUSDT", "BUY", 1.0, 1.0, 1.0, "TEST123", "Schema test")
