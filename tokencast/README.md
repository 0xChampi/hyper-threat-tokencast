# Hyper-Threat Tokencast System

9-segment rotating cryptocurrency live show orchestration system with pump.fun integration and SWARM market intelligence.

## Overview

The Tokencast system runs automated 60-minute shows with 9 rotating segments:

1. **TOKEN LAUNCH LIVE** (7 min) - Real-time pump.fun token launches
2. **SWARM ANALYSIS** (9 min) - Deep token analysis with PERCEPTRON, FOOLIO, AZOKA
3. **R3LL MUSIC** (5 min) - Creative break
4. **MEME ECONOMY** (7 min) - Trending meme coins
5. **CRYPTO DEEP DIVE** (10 min) - Comprehensive single-token analysis
6. **COMMUNITY INTERACTION** (7 min) - Q&A and polls
7. **AI HOST BREAKDOWN** (9 min) - Meta-analysis of show metrics
8. **NARRATIVE ALPHA** (8 min) - Market meta insights

## Quick Start

### 1. Set Environment Variables

```bash
# Database
export DATABASE_URL="postgresql://localhost/hyper_threat"

# SWARM API
export SWARM_API_URL="https://swarm-production-82b2.up.railway.app"
export SWARM_API_KEY="your_api_key"

# Pump.fun (optional, defaults to https://api.pump.fun)
export PUMPFUN_API_BASE="https://api.pump.fun"

# Server
export TOKENCAST_PORT=8002
export ENVIRONMENT="development"
```

### 2. Initialize Database

```bash
python -c "from tokencast.database import init_db; init_db()"
```

### 3. Start Server

```bash
python tokencast_server.py
```

Server will start on `http://localhost:8002`

## API Endpoints

### Show Management

```
POST /api/tokencast/start        # Start new show
POST /api/tokencast/end          # End current show
GET  /api/tokencast/current      # Get current show state
GET  /api/tokencast/show/{id}    # Get show details
```

### Segments

```
GET  /api/tokencast/segments/current         # Current segment
POST /api/tokencast/segments/transition      # Manual segment transition
```

### Pump.fun Integration

```
GET  /api/pump-fun/live-launches?minutes_back=5    # Recent launches
GET  /api/pump-fun/status/{token_address}          # Token status
GET  /api/pump-fun/trending?window_minutes=30      # Trending tokens
POST /api/pump-fun/analyze                         # SWARM analysis
```

## Usage Example

```python
import httpx

# Start a show
async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8002/api/tokencast/start", json={
        "estimated_duration": 60
    })
    show = response.json()
    print(f"Started show #{show['show_number']}")

    # Check current state
    response = await client.get("http://localhost:8002/api/tokencast/current")
    state = response.json()
    print(f"Current segment: {state['current_segment_index']}")
    print(f"Upcoming: {state['upcoming_segments']}")

    # Get live launches
    response = await client.get("http://localhost:8002/api/pump-fun/live-launches")
    launches = response.json()
    print(f"Detected {launches['count']} new launches")
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│        TOKENCAST ORCHESTRATOR                       │
│  - Show lifecycle management                        │
│  - Segment state machine (9 segments)               │
│  - Automatic transitions                            │
└───────────┬─────────────────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
┌─────────┐    ┌──────────────┐
│ SWARM   │    │ PUMP.FUN     │
│ API     │    │ FETCHER      │
│         │    │              │
│ PERCEP  │    │ - Launches   │
│ FOOLIO  │    │ - Bonding    │
│ AZOKA   │    │ - Metrics    │
└─────────┘    └──────────────┘
```

## Segment Generators

Each segment type has a specialized generator in `tokencast/segment_generators/`:

- **TokenLaunchGenerator** - Fetches pump.fun launches and analyzes with SWARM
- **SwarmAnalysisGenerator** - Full token deep-dive with all agents
- **MemeEconomyGenerator** - Tracks meme coin narratives
- **CommunityInteractionGenerator** - Community highlights and Q&A

### Adding Custom Generators

```python
from tokencast.segment_generators.base import SegmentGenerator
from tokencast.models import SegmentContext, SegmentOutput

class CustomGenerator(SegmentGenerator):
    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        # Your custom logic
        return SegmentOutput(
            speaker_notes="Custom segment content",
            featured_tokens=[],
            swarm_analyses=[]
        )

# Register with orchestrator
orchestrator.register_segment_generator(
    SegmentType.CUSTOM,
    CustomGenerator(swarm_client, telegram_bot, pump_fun_client)
)
```

## Database Schema

The system uses PostgreSQL with the following key tables:

- **tokencast_shows** - Show records
- **tokencast_segments** - Individual segments within shows
- **pump_fun_tokens** - Tracked tokens from pump.fun
- **swarm_segment_outputs** - SWARM analysis results
- **community_interactions** - User interactions

## Configuration

All configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://localhost/hyper_threat` | PostgreSQL connection string |
| `SWARM_API_URL` | `http://localhost:8001` | SWARM API endpoint |
| `SWARM_API_KEY` | `""` | SWARM API authentication |
| `PUMPFUN_API_BASE` | `https://api.pump.fun` | Pump.fun API endpoint |
| `TOKENCAST_PORT` | `8002` | Server port |
| `ENVIRONMENT` | `development` | `development` or `production` |

## Development

### Run in development mode

```bash
ENVIRONMENT=development python tokencast_server.py
```

Development mode enables:
- Auto-reload on code changes
- CORS from all origins
- Verbose logging

### Testing

```bash
# Start server
python tokencast_server.py

# In another terminal
curl http://localhost:8002/health

# Start a show
curl -X POST http://localhost:8002/api/tokencast/start \
  -H "Content-Type: application/json" \
  -d '{"estimated_duration": 60}'

# Check current segment
curl http://localhost:8002/api/tokencast/segments/current
```

## Deployment

### Railway

1. Set environment variables in Railway dashboard
2. Deploy from GitHub
3. Railway will automatically run `tokencast_server.py`

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "tokencast_server.py"]
```

## Monitoring

### Health Check

```bash
curl http://localhost:8002/health
```

Response:
```json
{
  "status": "healthy",
  "orchestrator_initialized": true,
  "show_running": true,
  "current_show_id": 1
}
```

### Show State

```bash
curl http://localhost:8002/api/tokencast/current
```

Response:
```json
{
  "show_id": 1,
  "show_number": 1,
  "current_segment_id": 5,
  "current_segment_index": 2,
  "started_at": "2025-12-31T12:00:00",
  "status": "live",
  "total_segments_completed": 2,
  "viewer_count": 0,
  "upcoming_segments": [
    {"type": "R3LL_MUSIC", "duration_seconds": 300},
    {"type": "MEME_ECONOMY", "duration_seconds": 420}
  ]
}
```

## Troubleshooting

### Database connection errors

Ensure PostgreSQL is running and `DATABASE_URL` is correct:

```bash
psql $DATABASE_URL -c "SELECT 1"
```

### SWARM API errors

Check SWARM API is accessible:

```bash
curl https://swarm-production-82b2.up.railway.app/health
```

### Pump.fun API errors

Pump.fun integration is optional. If unavailable, segments will use fallback content.

## License

MIT
