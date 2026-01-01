"""
Pump.fun Token Launch Routes

/api/pump-fun/* endpoints for token launch monitoring
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..database.models import PumpFunToken, TrackingStatus
from ..database.schemas import TokenStatusResponse, TokenAnalyzeRequest, TokenAnalyzeResponse
from data.pump_fetcher import PumpFunFetcher

router = APIRouter(prefix="/api/pump-fun", tags=["Pump.fun"])

# Global pump.fun client (set by main app)
_pump_fun_client: Optional[PumpFunFetcher] = None


def set_pump_fun_client(client: PumpFunFetcher):
    """Set the global pump.fun client"""
    global _pump_fun_client
    _pump_fun_client = client


def get_pump_fun_client() -> PumpFunFetcher:
    """Get the pump.fun client"""
    if not _pump_fun_client:
        raise HTTPException(status_code=503, detail="Pump.fun client not initialized")
    return _pump_fun_client


@router.get("/live-launches")
async def get_live_launches(
    minutes_back: int = 5,
    client: PumpFunFetcher = Depends(get_pump_fun_client)
):
    """
    Get recent token launches

    Args:
        minutes_back: How far back to look (default 5 minutes)

    Returns:
        List of recent launches
    """
    try:
        launches = await client.detect_launches(lookback_minutes=minutes_back)

        return {
            "count": len(launches),
            "launches": launches,
            "lookback_minutes": minutes_back
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch launches: {str(e)}")


@router.get("/status/{token_address}", response_model=TokenStatusResponse)
async def get_token_status(
    token_address: str,
    db: Session = Depends(get_db),
    client: PumpFunFetcher = Depends(get_pump_fun_client)
):
    """
    Get current status for a token

    Args:
        token_address: Token contract address

    Returns:
        Current token metrics and status
    """
    try:
        # Check database first
        token = db.query(PumpFunToken).filter_by(token_address=token_address).first()

        if not token:
            raise HTTPException(status_code=404, detail=f"Token {token_address} not found")

        # Get live metrics from pump.fun
        metrics = await client.get_token_metrics(token_address)

        if metrics:
            # Update database with fresh data
            token.current_price = metrics.get("price")
            token.market_cap = metrics.get("market_cap")
            token.holders_count = metrics.get("holders")
            token.volume_24h = metrics.get("volume_24h")
            db.commit()
            db.refresh(token)

        return token

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token status: {str(e)}")


@router.post("/analyze", response_model=TokenAnalyzeResponse)
async def analyze_token(
    request: TokenAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze a token with SWARM

    This endpoint would typically call the SWARM API to get
    regime detection, narrative analysis, and risk assessment.

    For now, returns a placeholder response.
    """
    # TODO: Integrate with SWARM API
    # For now, return mock data

    from datetime import datetime

    return TokenAnalyzeResponse(
        token_address=request.token_address,
        ticker=request.ticker,
        regime="Accumulation",
        narrative_phase="Discovery",
        risk_score=0.45,
        divergence_detected=False,
        analysis_timestamp=datetime.utcnow()
    )


@router.get("/trending")
async def get_trending_launches(
    window_minutes: int = 30,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get trending launches by velocity (volume, holders growth)

    Args:
        window_minutes: Time window to analyze
        limit: Max tokens to return

    Returns:
        List of trending tokens
    """
    from datetime import datetime, timedelta

    # Get recent tokens
    since = datetime.utcnow() - timedelta(minutes=window_minutes)

    tokens = db.query(PumpFunToken).filter(
        PumpFunToken.discovered_at >= since,
        PumpFunToken.tracking_status == TrackingStatus.ACTIVE
    ).order_by(
        PumpFunToken.volume_24h.desc()
    ).limit(limit).all()

    return {
        "trending_tokens": [
            {
                "token_address": t.token_address,
                "ticker": t.ticker,
                "volume_24h": t.volume_24h,
                "market_cap": t.market_cap,
                "holders": t.holders_count,
                "price": t.current_price
            }
            for t in tokens
        ],
        "window_minutes": window_minutes
    }
