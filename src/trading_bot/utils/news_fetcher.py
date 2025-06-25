# trading_bot/utils/news_fetcher.py
"""News fetching and sentiment analysis utilities"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

class CryptoNewsFetcher:
    """Fetch and analyze crypto news from various sources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        
        # News sources (free APIs)
        self.sources = {
            'coindesk': 'https://api.coindesk.com/v1/news/search',
            'cointelegraph': 'https://cointelegraph.com/rss',
            'cryptonews': 'https://cryptonews.com/news/feed/'
        }
        
        # Sentiment keywords
        self.positive_keywords = {
            'bullish', 'bull', 'pump', 'moon', 'rally', 'surge', 'breakout', 
            'adoption', 'upgrade', 'partnership', 'institutional', 'etf', 
            'approval', 'breakthrough', 'innovation', 'growth', 'expansion'
        }
        
        self.negative_keywords = {
            'bearish', 'bear', 'dump', 'crash', 'decline', 'fall', 'drop',
            'hack', 'exploit', 'regulation', 'ban', 'lawsuit', 'security',
            'vulnerability', 'concern', 'warning', 'risk', 'problem'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_recent_news(self, assets: List[str] = None, hours: int = 24) -> List[Dict]:
        """Fetch recent crypto news"""
        
        if assets is None:
            assets = ['bitcoin', 'ethereum', 'solana', 'avalanche', 'render', 'near']
        
        all_news = []
        
        try:
            # Simulate news fetching (replace with actual API calls)
            news_items = await self._simulate_news_fetch(assets, hours)
            all_news.extend(news_items)
            
        except Exception as e:
            self.logger.error(f"Error fetching news: {e}")
        
        return all_news
    
    async def _simulate_news_fetch(self, assets: List[str], hours: int) -> List[Dict]:
        """Simulate news fetching for testing"""
        
        sample_news = [
            {
                'title': 'Bitcoin ETF sees record inflows as institutional adoption grows',
                'summary': 'Major institutions continue to embrace Bitcoin through ETF products...',
                'source': 'CoinDesk',
                'timestamp': datetime.now() - timedelta(hours=2),
                'url': 'https://coindesk.com/example1',
                'assets_mentioned': ['bitcoin', 'btc'],
                'sentiment_score': 0.8
            },
            {
                'title': 'Solana network upgrade improves transaction speeds by 40%',
                'summary': 'Latest Solana upgrade delivers significant performance improvements...',
                'source': 'CoinTelegraph', 
                'timestamp': datetime.now() - timedelta(hours=4),
                'url': 'https://cointelegraph.com/example2',
                'assets_mentioned': ['solana', 'sol'],
                'sentiment_score': 0.7
            },
            {
                'title': 'Avalanche announces major DeFi partnership with traditional finance',
                'summary': 'Traditional financial institutions partner with Avalanche ecosystem...',
                'source': 'CryptoNews',
                'timestamp': datetime.now() - timedelta(hours=6),
                'url': 'https://cryptonews.com/example3', 
                'assets_mentioned': ['avalanche', 'avax'],
                'sentiment_score': 0.6
            },
            {
                'title': 'RENDER token gains as AI and GPU demand surges',
                'summary': 'Growing demand for AI computing power boosts RENDER network usage...',
                'source': 'CoinDesk',
                'timestamp': datetime.now() - timedelta(hours=8),
                'url': 'https://coindesk.com/example4',
                'assets_mentioned': ['render', 'rndr'],
                'sentiment_score': 0.75
            },
            {
                'title': 'Market volatility increases amid regulatory uncertainty',
                'summary': 'Crypto markets experience increased volatility as regulatory concerns mount...',
                'source': 'CryptoNews',
                'timestamp': datetime.now() - timedelta(hours=12),
                'url': 'https://cryptonews.com/example5',
                'assets_mentioned': ['bitcoin', 'ethereum', 'crypto'],
                'sentiment_score': -0.4
            }
        ]
        
        # Filter by requested assets and time window
        filtered_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for news in sample_news:
            if news['timestamp'] >= cutoff_time:
                # Check if any requested assets are mentioned
                if any(asset.lower() in ' '.join(news['assets_mentioned']) for asset in assets):
                    filtered_news.append(news)
        
        return filtered_news
    
    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text (-1 to 1)"""
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.positive_keywords if word in text_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in text_lower)
        
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.0
        
        # Calculate sentiment score
        sentiment = (positive_count - negative_count) / max(total_words / 10, 1)
        
        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, sentiment))
    
    def extract_asset_mentions(self, text: str, assets: List[str]) -> List[str]:
        """Extract mentioned assets from text"""
        
        mentioned = []
        text_lower = text.lower()
        
        asset_mappings = {
            'bitcoin': ['bitcoin', 'btc', 'btc/usd'],
            'ethereum': ['ethereum', 'eth', 'ether'],
            'solana': ['solana', 'sol'],
            'avalanche': ['avalanche', 'avax'],
            'render': ['render', 'rndr', 'render token'],
            'near': ['near', 'near protocol']
        }
        
        for asset, keywords in asset_mappings.items():
            if any(keyword in text_lower for keyword in keywords):
                mentioned.append(asset.upper())
        
        return list(set(mentioned))
