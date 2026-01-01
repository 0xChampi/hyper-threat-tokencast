"""
Data Pipeline - Fetch price, volume, holder data from DEX APIs
and social data from Twitter/Telegram
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import sqlite3
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Container for token market data"""
    timestamp: datetime
    price: float
    volume_24h: float
    liquidity: float
    txns_24h: int
    buys_24h: int
    sells_24h: int
    holders: Optional[int] = None
    market_cap: Optional[float] = None


@dataclass
class SocialData:
    """Container for social media data"""
    timestamp: datetime
    text: str
    source: str  # twitter, telegram, discord
    author: str
    engagement: int  # likes + retweets + replies
    is_influencer: bool = False


class DexDataFetcher:
    """Fetch on-chain data from DEX aggregators"""
    
    def __init__(self):
        self.dexscreener_base = "https://api.dexscreener.com/latest/dex"
        self.birdeye_base = "https://public-api.birdeye.so"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
    async def get_token_info(self, token_address: str, chain: str = "solana") -> Dict:
        """Get current token info from DexScreener"""
        url = f"{self.dexscreener_base}/tokens/{token_address}"
        async with self.session.get(url) as resp:
            data = await resp.json()
            if "pairs" in data and len(data["pairs"]) > 0:
                return data["pairs"][0]
            return {}
    
    async def get_ohlcv(
        self, 
        token_address: str, 
        interval: str = "1h",
        limit: int = 168  # 1 week of hourly data
    ) -> pd.DataFrame:
        """
        Get OHLCV data - using Birdeye API
        Intervals: 1m, 5m, 15m, 30m, 1h, 4h, 1d
        """
        # Birdeye OHLCV endpoint
        url = f"{self.birdeye_base}/defi/ohlcv"
        params = {
            "address": token_address,
            "type": interval,
            "time_from": int((datetime.now() - timedelta(hours=limit)).timestamp()),
            "time_to": int(datetime.now().timestamp())
        }
        headers = {"X-API-KEY": "YOUR_BIRDEYE_KEY"}
        
        async with self.session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
            
        if "data" not in data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data["data"]["items"])
        df["timestamp"] = pd.to_datetime(df["unixTime"], unit="s")
        df = df.rename(columns={
            "o": "open", "h": "high", "l": "low", 
            "c": "close", "v": "volume"
        })
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
    
    async def get_holder_data(self, token_address: str) -> Dict:
        """Get holder distribution from Birdeye"""
        url = f"{self.birdeye_base}/defi/token_holder_stat"
        params = {"address": token_address}
        headers = {"X-API-KEY": "YOUR_BIRDEYE_KEY"}
        
        async with self.session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
        
        return {
            "total_holders": data.get("data", {}).get("holder", 0),
            "top_10_pct": data.get("data", {}).get("top10HolderPercent", 0),
            "top_20_pct": data.get("data", {}).get("top20HolderPercent", 0),
        }
    
    async def get_trades(
        self, 
        token_address: str, 
        limit: int = 100
    ) -> pd.DataFrame:
        """Get recent trades for transaction analysis"""
        url = f"{self.birdeye_base}/defi/txs/token"
        params = {"address": token_address, "limit": limit}
        headers = {"X-API-KEY": "YOUR_BIRDEYE_KEY"}
        
        async with self.session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
        
        if "data" not in data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data["data"]["items"])
        return df


class SocialDataFetcher:
    """Fetch social media data for sentiment analysis"""
    
    def __init__(self, twitter_bearer: str):
        self.twitter_bearer = twitter_bearer
        self.twitter_base = "https://api.twitter.com/2"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
    async def search_tweets(
        self, 
        query: str,
        max_results: int = 100,
        hours_back: int = 24
    ) -> List[SocialData]:
        """Search recent tweets mentioning token"""
        url = f"{self.twitter_base}/tweets/search/recent"
        
        start_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat() + "Z"
        
        params = {
            "query": f"{query} -is:retweet lang:en",
            "max_results": min(max_results, 100),
            "start_time": start_time,
            "tweet.fields": "created_at,public_metrics,author_id",
            "user.fields": "public_metrics"
        }
        
        headers = {"Authorization": f"Bearer {self.twitter_bearer}"}
        
        async with self.session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
        
        results = []
        for tweet in data.get("data", []):
            metrics = tweet.get("public_metrics", {})
            engagement = (
                metrics.get("like_count", 0) + 
                metrics.get("retweet_count", 0) * 2 +
                metrics.get("reply_count", 0)
            )
            
            results.append(SocialData(
                timestamp=datetime.fromisoformat(tweet["created_at"].replace("Z", "")),
                text=tweet["text"],
                source="twitter",
                author=tweet["author_id"],
                engagement=engagement,
                is_influencer=engagement > 100  # rough heuristic
            ))
        
        return results
    
    async def get_mention_velocity(
        self, 
        ticker: str, 
        windows: List[int] = [1, 4, 12, 24]
    ) -> Dict[str, float]:
        """Calculate mention counts over different time windows"""
        velocities = {}
        
        for hours in windows:
            tweets = await self.search_tweets(ticker, hours_back=hours)
            velocities[f"mentions_{hours}h"] = len(tweets)
            velocities[f"engagement_{hours}h"] = sum(t.engagement for t in tweets)
        
        # Calculate velocity (rate of change)
        if velocities.get("mentions_4h", 0) > 0:
            velocities["mention_velocity"] = (
                velocities.get("mentions_1h", 0) / 
                (velocities.get("mentions_4h", 0) / 4)
            )
        else:
            velocities["mention_velocity"] = 0
        
        return velocities


class FeatureEngineer:
    """Transform raw data into ML features"""
    
    @staticmethod
    def compute_price_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute price-based features from OHLCV"""
        features = pd.DataFrame(index=df.index)
        
        # Returns at different windows
        for window in [1, 4, 12, 24]:
            features[f"return_{window}h"] = df["close"].pct_change(window)
        
        # Volatility
        features["volatility_24h"] = df["close"].rolling(24).std() / df["close"].rolling(24).mean()
        
        # Volume features
        features["volume_ratio"] = df["volume"] / df["volume"].rolling(24).mean()
        features["volume_momentum"] = df["volume"].pct_change(4)
        
        # Price-volume divergence (key signal)
        features["pv_divergence"] = (
            features["return_4h"] - 
            features["volume_momentum"] * 0.5
        )
        
        # Trend strength
        features["trend_strength"] = (
            df["close"].rolling(12).mean() / 
            df["close"].rolling(24).mean() - 1
        )
        
        # ATH distance
        features["ath_distance"] = df["close"] / df["close"].cummax() - 1
        
        # Candle patterns
        features["body_ratio"] = (df["close"] - df["open"]) / (df["high"] - df["low"] + 1e-10)
        features["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)) / (df["high"] - df["low"] + 1e-10)
        features["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]) / (df["high"] - df["low"] + 1e-10)
        
        return features.fillna(0)
    
    @staticmethod
    def compute_holder_features(holder_snapshots: List[Dict]) -> pd.DataFrame:
        """Compute holder-based features"""
        df = pd.DataFrame(holder_snapshots)
        
        features = pd.DataFrame()
        features["holder_count"] = df["total_holders"]
        features["holder_growth"] = df["total_holders"].pct_change()
        features["concentration"] = df["top_10_pct"]
        features["concentration_delta"] = df["top_10_pct"].diff()
        
        # Whale behavior signal
        # Negative delta = whales distributing
        features["whale_signal"] = -features["concentration_delta"]
        
        return features.fillna(0)
    
    @staticmethod
    def compute_social_features(social_data: List[SocialData]) -> Dict:
        """Aggregate social data into features"""
        if not social_data:
            return {
                "mention_count": 0,
                "total_engagement": 0,
                "avg_engagement": 0,
                "influencer_ratio": 0,
                "sentiment_score": 0
            }
        
        df = pd.DataFrame([vars(s) for s in social_data])
        
        return {
            "mention_count": len(df),
            "total_engagement": df["engagement"].sum(),
            "avg_engagement": df["engagement"].mean(),
            "influencer_ratio": df["is_influencer"].mean(),
            "unique_authors": df["author"].nunique()
        }
    
    @staticmethod
    def create_observation_vector(
        price_features: pd.DataFrame,
        holder_features: pd.DataFrame,
        social_features: Dict,
        idx: int
    ) -> np.ndarray:
        """Create single observation vector for HMM"""
        
        pf = price_features.iloc[idx]
        hf = holder_features.iloc[min(idx, len(holder_features)-1)]
        
        return np.array([
            pf["volume_ratio"],
            pf["return_4h"],
            pf["pv_divergence"],
            pf["trend_strength"],
            pf["ath_distance"],
            hf["holder_growth"],
            hf["whale_signal"],
            social_features.get("mention_count", 0) / 100,  # normalize
            social_features.get("influencer_ratio", 0)
        ])


class DataStorage:
    """SQLite storage for time-series data"""
    
    def __init__(self, db_path: str = "data/memecoin.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_data (
                token_address TEXT,
                timestamp DATETIME,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (token_address, timestamp)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT,
                timestamp DATETIME,
                text TEXT,
                source TEXT,
                author TEXT,
                engagement INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holder_data (
                token_address TEXT,
                timestamp DATETIME,
                total_holders INTEGER,
                top_10_pct REAL,
                top_20_pct REAL,
                PRIMARY KEY (token_address, timestamp)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def store_price_data(self, token_address: str, df: pd.DataFrame):
        conn = sqlite3.connect(self.db_path)
        df["token_address"] = token_address
        df.to_sql("price_data", conn, if_exists="append", index=False)
        conn.close()
    
    def load_price_data(
        self, 
        token_address: str, 
        start_time: datetime = None
    ) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM price_data WHERE token_address = ?"
        params = [token_address]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df


# Main data collection pipeline
async def collect_token_data(
    token_address: str,
    ticker: str,
    twitter_bearer: str
) -> Tuple[pd.DataFrame, pd.DataFrame, List[SocialData]]:
    """
    Full data collection pipeline for a single token
    Returns: (price_features, holder_features, social_data)
    """
    
    async with DexDataFetcher() as dex:
        # Get OHLCV
        ohlcv = await dex.get_ohlcv(token_address, interval="1h", limit=168)
        
        # Get holder data
        holder_data = await dex.get_holder_data(token_address)
    
    async with SocialDataFetcher(twitter_bearer) as social:
        # Get tweets
        tweets = await social.search_tweets(f"${ticker}", hours_back=24)
        velocities = await social.get_mention_velocity(f"${ticker}")
    
    # Engineer features
    fe = FeatureEngineer()
    price_features = fe.compute_price_features(ohlcv)
    
    # Single holder snapshot for now
    holder_features = pd.DataFrame([holder_data])
    
    return price_features, holder_features, tweets, velocities


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        token = "YOUR_TOKEN_ADDRESS"
        ticker = "TICKER"
        bearer = "YOUR_TWITTER_BEARER"
        
        price_feat, holder_feat, tweets, velocities = await collect_token_data(
            token, ticker, bearer
        )
        
        print(f"Price features shape: {price_feat.shape}")
        print(f"Tweets collected: {len(tweets)}")
        print(f"Velocities: {velocities}")
    
    asyncio.run(main())
