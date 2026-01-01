"""
Hyper-Threat Tokencast Server

FastAPI server for running live cryptocurrency shows with 9 rotating segments.

Integrates:
- SWARM API for market intelligence
- Pump.fun for token launch monitoring
- Telegram for community interaction
- Automated segment orchestration
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from tokencast.database import init_db, get_db
from tokencast.orchestrator import TokencastOrchestrator
from tokencast.routes import tokencast_router, pump_fun_router
from tokencast.routes.tokencast import set_orchestrator
from tokencast.routes.pump_fun import set_pump_fun_client
from tokencast.segment_generators import (
    TokenLaunchGenerator,
    SwarmAnalysisGenerator,
    MemeEconomyGenerator,
    CommunityInteractionGenerator,
    GambaSegmentGenerator
)
from tokencast.models import SegmentType
from data.pump_fetcher import PumpFunFetcher

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SWARM_API_URL = os.getenv("SWARM_API_URL", "http://localhost:8001")
SWARM_API_KEY = os.getenv("SWARM_API_KEY", "")
PUMPFUN_API_BASE = os.getenv("PUMPFUN_API_BASE", "https://api.pump.fun")
TOKENCAST_PORT = int(os.getenv("PORT", os.getenv("TOKENCAST_PORT", "8002")))

# Global instances
orchestrator = None
pump_fun_client = None
swarm_client = None


class SwarmClient:
    """Simple SWARM API client wrapper"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def analyze_token(self, ticker: str, token_address: str = None):
        """Analyze a token with full SWARM (PERCEPTRON + FOOLIO + AZOKA)"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self.client.post(
                f"{self.api_url}/api/analyze-token",
                json={"ticker": ticker, "token_address": token_address or ""},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SWARM analyze_token error: {e}")
            return {}

    async def query(self, question: str, ticker: str = None, token_address: str = None):
        """Ask GIZMO a question"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self.client.post(
                f"{self.api_url}/api/swarm/query",
                json={"question": question, "ticker": ticker, "token_address": token_address},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SWARM query error: {e}")
            return {}

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown

    Startup:
    - Initialize database
    - Create pump.fun client
    - Create SWARM client
    - Initialize orchestrator
    - Register segment generators

    Shutdown:
    - Close connections
    """
    global orchestrator, pump_fun_client, swarm_client

    # Startup
    logger.info("🚀 Starting Hyper-Threat Tokencast Server...")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Create pump.fun client
    logger.info(f"Connecting to pump.fun API: {PUMPFUN_API_BASE}")
    pump_fun_client = PumpFunFetcher(api_base=PUMPFUN_API_BASE)
    set_pump_fun_client(pump_fun_client)

    # Create SWARM client
    logger.info(f"Connecting to SWARM API: {SWARM_API_URL}")
    swarm_client = SwarmClient(api_url=SWARM_API_URL, api_key=SWARM_API_KEY)

    # Create orchestrator
    logger.info("Initializing Tokencast Orchestrator...")
    # Create a database session for the orchestrator (stays open during app lifetime)
    from tokencast.database.db import SessionLocal
    db = SessionLocal()
    orchestrator = TokencastOrchestrator(
        db_session=db,
        swarm_client=swarm_client,
        pump_fun_client=pump_fun_client,
        telegram_bot=None  # TODO: Add telegram bot if needed
    )

    # Register segment generators
    logger.info("Registering segment generators...")
    orchestrator.register_segment_generator(
        SegmentType.TOKEN_LAUNCH_LIVE,
        TokenLaunchGenerator(swarm_client, None, pump_fun_client)
    )
    orchestrator.register_segment_generator(
        SegmentType.SWARM_ANALYSIS,
        SwarmAnalysisGenerator(swarm_client, None, pump_fun_client)
    )
    orchestrator.register_segment_generator(
        SegmentType.MEME_ECONOMY,
        MemeEconomyGenerator(swarm_client, None, pump_fun_client)
    )
    orchestrator.register_segment_generator(
        SegmentType.COMMUNITY_INTERACTION,
        CommunityInteractionGenerator(swarm_client, None, pump_fun_client)
    )
    orchestrator.register_segment_generator(
        SegmentType.GAMBA,
        GambaSegmentGenerator(swarm_client, None, pump_fun_client)
    )

    # Set global orchestrator for routes
    set_orchestrator(orchestrator)

    logger.info("✅ Tokencast Server Ready!")

    yield

    # Shutdown
    logger.info("👋 Shutting down Tokencast Server...")

    # Close connections
    if pump_fun_client:
        await pump_fun_client.close()

    if swarm_client:
        await swarm_client.close()

    # Close database session
    if orchestrator and orchestrator.db:
        orchestrator.db.close()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Hyper-Threat Tokencast",
    description="9-segment rotating cryptocurrency live show orchestration system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else [
        "https://hyper-threat.tv",
        "http://localhost:3000",
        "https://attn.money"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tokencast_router)
app.include_router(pump_fun_router)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Hyper-Threat Tokencast",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "show_management": "/api/tokencast",
            "pump_fun": "/api/pump-fun",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    current_show = orchestrator.get_current_state() if orchestrator else None

    return {
        "status": "healthy",
        "orchestrator_initialized": orchestrator is not None,
        "show_running": current_show is not None,
        "current_show_id": current_show.show_id if current_show else None
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"""
    ╔══════════════════════════════════════════════╗
    ║   HYPER-THREAT TOKENCAST SERVER              ║
    ║                                              ║
    ║   9-Segment Rotating Show System             ║
    ║   • Pump.fun token launch monitoring         ║
    ║   • SWARM market intelligence                ║
    ║   • Automated segment transitions            ║
    ╚══════════════════════════════════════════════╝

    Starting on port {TOKENCAST_PORT}...
    """)

    uvicorn.run(
        "tokencast_server:app",
        host="0.0.0.0",
        port=TOKENCAST_PORT,
        reload=ENVIRONMENT == "development"
    )
