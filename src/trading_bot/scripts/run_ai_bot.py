# trading_bot/scripts/run_ai_bot.py
#!/usr/bin/env python3
"""Run the AI-enhanced trading bot"""

import asyncio
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from trading_bot.ai.continuous_learning_system import AIEnhancedTradingBot
from trading_bot.utils.logger import trading_logger
from trading_bot.config.trading_config import config

logger = trading_logger.get_logger()

class AIBotRunner:
    def __init__(self):
        self.bot = None
        self.running = False
    
    async def start(self):
        """Start AI-enhanced trading bot"""
        try:
            logger.info("🤖 Starting AI-Enhanced Trading Bot...")
            logger.info(f"Environment: {config.environment}")
            logger.info(f"AI Enabled: {config.ai_config.enabled}")
            
            # Initialize AI-enhanced bot
            self.bot = AIEnhancedTradingBot()
            logger.info("✅ AI trading bot initialized")
            
            # Start trading
            self.running = True
            await self.bot.run()
            
        except Exception as e:
            logger.error(f"❌ Failed to start AI bot: {e}")
            raise
    
    async def stop(self):
        """Stop bot gracefully"""
        logger.info("🛑 Stopping AI trading bot...")
        self.running = False
        
        if self.bot:
            self.bot.running = False
        
        logger.info("✅ AI trading bot stopped")

async def main():
    """Main entry point"""
    bot_runner = AIBotRunner()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler():
        logger.info("🔔 Shutdown signal received")
        asyncio.create_task(bot_runner.stop())
    
    # Register signal handlers
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for signame in {'SIGINT', 'SIGTERM'}:
            loop.add_signal_handler(getattr(signal, signame), signal_handler)
    
    try:
        await bot_runner.start()
    except KeyboardInterrupt:
        logger.info("🔔 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        await bot_runner.stop()

if __name__ == "__main__":
    print("🤖 AI-Enhanced Trading Bot")
    print("==========================")
    asyncio.run(main())
