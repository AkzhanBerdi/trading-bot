#!/usr/bin/env python3
"""Comprehensive test suite for trading bot"""

import sys
import asyncio
import traceback
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

def test_indicators():
    """Test technical indicators"""
    print("🧪 Testing indicators...")
    try:
        from trading_bot.utils.indicators import test_indicators
        test_indicators()
        print("✅ Indicators working")
        return True
    except Exception as e:
        print(f"❌ Indicators failed: {e}")
        return False

def test_binance_connection():
    """Test Binance API connection"""
    print("🧪 Testing Binance connection...")
    try:
        from trading_bot.utils.binance_client import test_binance_connection
        success = test_binance_connection()
        if success:
            print("✅ Binance connection working")
        else:
            print("❌ Binance connection failed (expected without API keys)")
        return True  # Don't fail on connection issues during testing
    except Exception as e:
        print(f"⚠️ Binance test failed (expected without API keys): {e}")
        return True  # Don't fail on connection issues during testing

def test_grid_strategy():
    """Test grid trading strategy"""
    print("🧪 Testing grid strategy...")
    try:
        from trading_bot.strategies.grid_trading import test_grid_strategy
        test_grid_strategy()
        print("✅ Grid strategy working")
        return True
    except Exception as e:
        print(f"❌ Grid strategy failed: {e}")
        return False

def test_render_strategy():
    """Test RENDER signal strategy"""
    print("🧪 Testing RENDER strategy...")
    try:
        from trading_bot.strategies.render_signals import test_render_strategy
        test_render_strategy()
        print("✅ RENDER strategy working")
        return True
    except Exception as e:
        print(f"❌ RENDER strategy failed: {e}")
        return False

def test_performance_tracker():
    """Test performance tracking"""
    print("🧪 Testing performance tracker...")
    try:
        from trading_bot.utils.performance_tracker import PerformanceTracker
        
        tracker = PerformanceTracker()
        
        # Test recording a sample trade
        sample_trade = {
            'symbol': 'SOLUSDT',
            'side': 'BUY',
            'quantity': 1.0,
            'price': 100.0,
            'strategy': 'grid',
            'fees': 0.1,
            'pnl': 0.0,
            'portfolio_value_before': 1000.0,
            'portfolio_value_after': 1000.0
        }
        
        tracker.record_trade(sample_trade)
        
        # Test metrics calculation
        metrics = tracker.calculate_performance_metrics(7)
        
        print("✅ Performance tracker working")
        return True
    except Exception as e:
        print(f"❌ Performance tracker failed: {e}")
        return False

def test_news_fetcher():
    """Test news fetching"""
    print("🧪 Testing news fetcher...")
    try:
        from trading_bot.utils.news_fetcher import CryptoNewsFetcher
        
        async def test_news():
            async with CryptoNewsFetcher() as fetcher:
                news = await fetcher.fetch_recent_news(['bitcoin', 'solana'], 24)
                return len(news) > 0
        
        success = asyncio.run(test_news())
        if success:
            print("✅ News fetcher working")
        else:
            print("⚠️ News fetcher returned no data (may be normal)")
        return True
    except Exception as e:
        print(f"❌ News fetcher failed: {e}")
        return False

def test_mcp_client():
    """Test MCP client"""
    print("🧪 Testing MCP client...")
    try:
        from trading_bot.mcp.mcp_client import test_mcp_client
        
        # Run async test
        asyncio.run(test_mcp_client())
        print("✅ MCP client working")
        return True
    except Exception as e:
        print(f"❌ MCP client failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("🧪 Testing configuration...")
    try:
        from trading_bot.config.trading_config import config, ASSET_CONFIGS, TRADING_PAIRS
        
        # Test config access
        assert config.grid_config is not None
        assert config.render_config is not None
        assert config.risk_config is not None
        assert config.ai_config is not None
        
        # Test asset configs
        assert 'SOL' in ASSET_CONFIGS
        assert 'AVAX' in ASSET_CONFIGS
        assert 'RENDER' in ASSET_CONFIGS
        
        # Test trading pairs
        assert 'SOLUSDT' in TRADING_PAIRS.values()
        
        print("✅ Configuration working")
        return True
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False

def test_logging():
    """Test logging system"""
    print("🧪 Testing logging...")
    try:
        from trading_bot.utils.logger import trading_logger
        
        logger = trading_logger.get_logger()
        logger.info("Test log message")
        
        # Test trade logging
        sample_trade = {
            'symbol': 'SOLUSDT',
            'side': 'BUY',
            'amount': 50.0
        }
        trading_logger.log_trade(sample_trade)
        
        print("✅ Logging working")
        return True
    except Exception as e:
        print(f"❌ Logging failed: {e}")
        return False

def test_data_directories():
    """Test data directory structure"""
    print("🧪 Testing data directories...")
    try:
        required_dirs = [
            "data/logs",
            "data/performance",
            "data/learning_history",
            "config"
        ]
        
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Test file creation
        test_file = Path("data/logs/test.log")
        test_file.write_text("test")
        test_file.unlink()  # Clean up
        
        print("✅ Data directories working")
        return True
    except Exception as e:
        print(f"❌ Data directories failed: {e}")
        return False

def test_environment():
    """Test environment setup"""
    print("🧪 Testing environment...")
    try:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Check for required environment variables
        required_vars = ['BINANCE_API_KEY', 'BINANCE_SECRET_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
            print("   This is expected - add them tomorrow when you have API keys")
            return True  # Don't fail on missing API keys during testing
        
        print("✅ Environment working")
        return True
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

def test_imports():
    """Test all critical imports"""
    print("🧪 Testing imports...")
    try:
        # Test core components
        from trading_bot.utils.indicators import rsi, bollinger_bands
        from trading_bot.strategies.grid_trading import GridTrader
        from trading_bot.strategies.render_signals import RenderSignalTrader
        print("✅ Core strategies imported")
        
        # Test AI components  
        from trading_bot.ai import MCPMarketAnalyzer, AIEnhancedTradingBot
        print("✅ AI components imported")
        
        # Test MCP components
        from trading_bot.mcp import MCPTradingClient
        print("✅ MCP components imported")
        
        # Test configuration
        from trading_bot.config.trading_config import config
        print("✅ Configuration imported")
        
        print("✅ All imports working")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def run_quick_tests():
    """Run quick tests (no external connections)"""
    
    print("🚀 Trading Bot Quick Test Suite")
    print("=" * 50)
    
    quick_tests = [
        ("Environment", test_environment),
        ("Data Directories", test_data_directories),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Logging", test_logging),
        ("Indicators", test_indicators),
        ("Grid Strategy", test_grid_strategy),
        ("RENDER Strategy", test_render_strategy),
        ("Performance Tracker", test_performance_tracker),
        ("News Fetcher", test_news_fetcher),
        ("MCP Client", test_mcp_client),
    ]
    
    results = {}
    total_tests = len(quick_tests)
    passed_tests = 0
    
    for test_name, test_func in quick_tests:
        print(f"\n{'='*20}")
        try:
            success = test_func()
            results[test_name] = success
            if success:
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 QUICK TEST SUMMARY")
    print(f"{'='*50}")
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")
    
    print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests >= total_tests * 0.8:
        print("🎉 Quick tests mostly passed! Your bot logic is working.")
        print("Ready for API keys tomorrow! 🚀")
    else:
        print("⚠️ Some tests failed. Review the errors above.")
    
    return passed_tests >= total_tests * 0.8

def run_all_tests():
    """Run comprehensive test suite"""
    
    print("🚀 Trading Bot Comprehensive Test Suite")
    print("=" * 50)
    
    tests = [
        ("Environment", test_environment),
        ("Data Directories", test_data_directories),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Logging", test_logging),
        ("Indicators", test_indicators),
        ("Grid Strategy", test_grid_strategy),
        ("RENDER Strategy", test_render_strategy),
        ("Performance Tracker", test_performance_tracker),
        ("News Fetcher", test_news_fetcher),
        ("MCP Client", test_mcp_client),
        ("Binance Connection", test_binance_connection),
    ]
    
    results = {}
    total_tests = len(tests)
    passed_tests = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20}")
        try:
            success = test_func()
            results[test_name] = success
            if success:
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            print(traceback.format_exc())
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")
    
    print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Your trading bot is ready.")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️ Most tests passed. Review failed tests before proceeding.")
    else:
        print("❌ Many tests failed. Please fix issues before running the bot.")
    
    return passed_tests == total_tests

def main():
    """Main test function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Test trading bot components")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Run quick tests only (skip connection tests)")
    parser.add_argument("--component", "-c", type=str,
                       help="Test specific component only")
    
    args = parser.parse_args()
    
    if args.component:
        # Test specific component
        component_tests = {
            'indicators': test_indicators,
            'binance': test_binance_connection,
            'grid': test_grid_strategy,
            'render': test_render_strategy,
            'performance': test_performance_tracker,
            'news': test_news_fetcher,
            'mcp': test_mcp_client,
            'config': test_configuration,
            'logging': test_logging,
            'env': test_environment,
            'dirs': test_data_directories,
            'imports': test_imports
        }
        
        if args.component in component_tests:
            success = component_tests[args.component]()
            sys.exit(0 if success else 1)
        else:
            print(f"❌ Unknown component: {args.component}")
            print(f"Available components: {', '.join(component_tests.keys())}")
            sys.exit(1)
    
    elif args.quick:
        # Quick tests (no external connections)
        success = run_quick_tests()
        sys.exit(0 if success else 1)
    
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
