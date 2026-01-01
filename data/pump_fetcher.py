"""
Pump.fun Token Launch Fetcher

Real-time monitoring of pump.fun token launches via API polling.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class LaunchEvent:
    """Represents a token launch event"""

    def __init__(
        self,
        token_address: str,
        ticker: Optional[str],
        mint_address: Optional[str],
        creator: str,
        initial_price: float,
        discovered_timestamp: datetime,
        bonding_curve_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.token_address = token_address
        self.ticker = ticker
        self.mint_address = mint_address
        self.creator = creator
        self.initial_price = initial_price
        self.discovered_timestamp = discovered_timestamp
        self.bonding_curve_address = bonding_curve_address
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "token_address": self.token_address,
            "ticker": self.ticker,
            "mint_address": self.mint_address,
            "creator": self.creator,
            "price_at_discovery": self.initial_price,
            "discovered_at": self.discovered_timestamp.isoformat(),
            "bonding_curve_address": self.bonding_curve_address,
            "metadata": self.metadata
        }


class BondingCurveState:
    """Current state of a bonding curve"""

    def __init__(
        self,
        token_address: str,
        progress_pct: float,
        current_price: float,
        market_cap: float,
        holders_count: int,
        volume_24h: float = 0.0
    ):
        self.token_address = token_address
        self.progress_pct = progress_pct  # 0-100%
        self.current_price = current_price
        self.market_cap = market_cap
        self.holders_count = holders_count
        self.volume_24h = volume_24h


class PumpFunFetcher:
    """
    Fetches token launches from pump.fun

    Note: Pump.fun API endpoints are examples and may need adjustment
    based on actual API documentation.
    """

    def __init__(
        self,
        api_base: str = "https://api.pump.fun",
        polling_interval: int = 10
    ):
        """
        Initialize PumpFunFetcher

        Args:
            api_base: Base URL for pump.fun API
            polling_interval: Seconds between polls
        """
        self.api_base = api_base
        self.polling_interval = polling_interval
        self.client = httpx.AsyncClient(timeout=30.0)

        # Cache of seen token addresses to avoid duplicates
        self.seen_tokens: set = set()

    async def detect_launches(
        self,
        lookback_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Detect newly launched tokens in past N minutes

        Args:
            lookback_minutes: How far back to look for launches

        Returns:
            List of launch event dictionaries
        """
        try:
            # Example endpoint - adjust based on actual API
            url = f"{self.api_base}/tokens/new"

            params = {
                "limit": 50,
                "since": int((datetime.utcnow() - timedelta(minutes=lookback_minutes)).timestamp())
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse launches
            launches = []
            for token_data in data.get("tokens", []):
                token_address = token_data.get("address")

                # Skip if already seen
                if token_address in self.seen_tokens:
                    continue

                self.seen_tokens.add(token_address)

                launch = LaunchEvent(
                    token_address=token_address,
                    ticker=token_data.get("symbol"),
                    mint_address=token_data.get("mint"),
                    creator=token_data.get("creator"),
                    initial_price=float(token_data.get("initialPrice", 0)),
                    discovered_timestamp=datetime.utcnow(),
                    bonding_curve_address=token_data.get("bondingCurve"),
                    metadata={
                        "name": token_data.get("name"),
                        "description": token_data.get("description"),
                        "image": token_data.get("image")
                    }
                )

                launches.append(launch.to_dict())

            logger.info(f"Detected {len(launches)} new launches (lookback: {lookback_minutes}m)")
            return launches

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching launches: {e}")
            return []
        except Exception as e:
            logger.error(f"Error detecting launches: {e}", exc_info=True)
            return []

    async def get_bonding_curve_progress(
        self,
        token_address: str
    ) -> Optional[BondingCurveState]:
        """
        Get current bonding curve state for a token

        Args:
            token_address: Token contract address

        Returns:
            BondingCurveState or None if unavailable
        """
        try:
            # Example endpoint
            url = f"{self.api_base}/tokens/{token_address}/bonding-curve"

            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            return BondingCurveState(
                token_address=token_address,
                progress_pct=float(data.get("progressPercent", 0)),
                current_price=float(data.get("price", 0)),
                market_cap=float(data.get("marketCap", 0)),
                holders_count=int(data.get("holders", 0)),
                volume_24h=float(data.get("volume24h", 0))
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching bonding curve for {token_address}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching bonding curve: {e}", exc_info=True)
            return None

    async def get_token_metrics(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get current metrics for a token

        Args:
            token_address: Token contract address

        Returns:
            Dictionary with price, volume, holders, etc.
        """
        try:
            url = f"{self.api_base}/tokens/{token_address}"

            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            return {
                "token_address": token_address,
                "ticker": data.get("symbol"),
                "price": float(data.get("price", 0)),
                "market_cap": float(data.get("marketCap", 0)),
                "volume_24h": float(data.get("volume24h", 0)),
                "holders": int(data.get("holders", 0)),
                "bonding_progress": float(data.get("bondingProgress", 0))
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metrics for {token_address}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching token metrics: {e}", exc_info=True)
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
