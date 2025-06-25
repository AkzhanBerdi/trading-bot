# trading_bot/scripts/start_mcp_server.py
#!/usr/bin/env python3
"""Start the MCP server for trading bot"""

import asyncio
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from trading_bot.main import TradingBot
from trading_bot.mcp.trading_mcp_server import setup_mcp_server
from trading_bot.utils.logger import trading_logger

logger = trading_logger.get_logger()

class MCPServerRunner:
    def __init__(self):
        self.trading_bot = None
        self.mcp_server = None
        self.running = False
    
    async def start(self):
        """Start MCP server"""
        try:
            logger.info("🚀 Initializing MCP Trading Server...")
            
            # Initialize trading bot
            self.trading_bot = TradingBot()
            logger.info("✅ Trading bot initialized")
            
            # Setup MCP server
            self.mcp_server = setup_mcp_server(self.trading_bot)
            logger.info("✅ MCP server configured")
            
            # Start server
            logger.info("🌐 Starting MCP server on localhost:8080...")
            self.running = True
            await self.mcp_server.start_server(host="localhost", port=8080)
            
        except Exception as e:
            logger.error(f"❌ Failed to start MCP server: {e}")
            raise
    
    async def stop(self):
        """Stop MCP server gracefully"""
        logger.info("🛑 Stopping MCP server...")
        self.running = False
        
        if self.mcp_server:
            # Stop MCP server (if it has a stop method)
            pass
        
        logger.info("✅ MCP server stopped")

async def main():
    """Main entry point"""
    server_runner = MCPServerRunner()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler():
        logger.info("🔔 Shutdown signal received")
        asyncio.create_task(server_runner.stop())
    
    # Register signal handlers
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for signame in {'SIGINT', 'SIGTERM'}:
            loop.add_signal_handler(getattr(signal, signame), signal_handler)
    
    try:
        await server_runner.start()
    except KeyboardInterrupt:
        logger.info("🔔 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    finally:
        await server_runner.stop()

if __name__ == "__main__":
    print("🤖 MCP Trading Server")
    print("===================")
    asyncio.run(main())
