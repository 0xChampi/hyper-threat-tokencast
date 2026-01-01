# Tokencast Railway Deployment Guide

## Current Status

✅ Code committed and pushed to repository
✅ SWARM API service still running correctly at https://swarm-production-82b2.up.railway.app
⏳ Tokencast service needs to be created as separate service

---

## Deployment Steps

### Option 1: Manual Railway Dashboard Setup (Recommended)

1. **Open Railway Project**: https://railway.com/project/c8d506c4-9331-45e5-9078-5b20408babe4

2. **Create New Service**:
   - Click "+ New Service"
   - Select "GitHub Repo"
   - Choose the hyper-threat repository
   - Name it "Tokencast"

3. **Configure Service Settings**:
   - Go to Settings → Deploy
   - Set **Start Command**: `uvicorn tokencast_server:app --host 0.0.0.0 --port $PORT`
   - Set **Health Check Path**: `/health`
   - Set **Health Check Timeout**: 100 seconds

4. **Add Environment Variables**:
   ```
   ENVIRONMENT=production
   SWARM_API_URL=https://swarm-production-82b2.up.railway.app
   SWARM_API_KEY=1-2fsQxR1CdPeRaLQXIAom0kR6BavShlTs-bHBwTcsg
   PUMPFUN_API_BASE=https://api.pump.fun
   DATABASE_URL=${{Postgres.DATABASE_URL}}  (if using Railway Postgres)
   ```

5. **Add PostgreSQL Database** (Optional):
   - Click "+ New" → "Database" → "PostgreSQL"
   - Link to Tokencast service
   - DATABASE_URL will be auto-injected

6. **Deploy**:
   - Railway will automatically deploy
   - Monitor logs for successful startup
   - Note the generated public URL

7. **Generate Public Domain**:
   - Go to Settings → Networking
   - Click "Generate Domain"
   - Your tokencast API will be at: `tokencast-production-xxxx.up.railway.app`

---

### Option 2: Use SQLite (Simpler, No Database Setup)

If you want to skip PostgreSQL setup for now:

1. Follow steps 1-3 above
2. Skip the DATABASE_URL variable (will use SQLite by default)
3. Deploy as normal

**Note**: SQLite data will be ephemeral on Railway (resets on redeploy). Fine for testing, but use PostgreSQL for production.

---

## Testing Deployed Service

Once deployed, test with:

```bash
# Get deployment URL (replace with your actual URL)
TOKENCAST_URL="https://tokencast-production-xxxx.up.railway.app"

# Health check
curl $TOKENCAST_URL/health

# Start a show
curl -X POST $TOKENCAST_URL/api/tokencast/start \
  -H "Content-Type: application/json" \
  -d '{"estimated_duration": 60}'

# Check current state
curl $TOKENCAST_URL/api/tokencast/current

# View segment
curl $TOKENCAST_URL/api/tokencast/segments/current

# End show
curl -X POST $TOKENCAST_URL/api/tokencast/end
```

---

## Architecture

```
┌────────────────────────────────────┐
│  Railway Project: Swarm            │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ Service: Swarm               │  │
│  │ https://swarm-production-    │  │
│  │   82b2.up.railway.app        │  │
│  │ Runs: api_server.py          │  │
│  └──────────────────────────────┘  │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ Service: Tokencast (NEW)     │  │
│  │ https://tokencast-production-│  │
│  │   xxxx.up.railway.app        │  │
│  │ Runs: tokencast_server.py    │  │
│  │ Connects to SWARM ↑          │  │
│  └──────────────────────────────┘  │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ Database: PostgreSQL         │  │
│  │ (Optional)                   │  │
│  │ Linked to Tokencast          │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

---

## Files in Repository

- `tokencast_server.py` - Main FastAPI application
- `tokencast/` - Full tokencast system package
- `railway.toml` - SWARM service config (runs api_server.py)
- `railway.tokencast.toml` - Tokencast config (reference only, not used by Railway)

Railway automatically uses `railway.toml` for the Swarm service. For Tokencast service, configure the start command manually in the Railway dashboard.

---

## Environment Variables Reference

### Required
- `SWARM_API_URL` - SWARM backend URL
- `SWARM_API_KEY` - SWARM API authentication

### Optional
- `ENVIRONMENT` - `production` or `development` (default: development)
- `PUMPFUN_API_BASE` - Pump.fun API endpoint (default: https://api.pump.fun)
- `DATABASE_URL` - PostgreSQL connection string (default: SQLite)
- `TOKENCAST_PORT` - Local port (Railway overrides with $PORT)

---

## Next Steps After Deployment

1. Test all endpoints with live SWARM API
2. Monitor logs for any errors
3. Test with actual pump.fun launches (if API is available)
4. Integrate with Telegram bot (optional)
5. Set up WebSocket for real-time updates (future enhancement)

---

## Troubleshooting

### Service won't start
- Check logs in Railway dashboard
- Verify all environment variables are set
- Ensure DATABASE_URL is valid (if using PostgreSQL)

### SWARM API errors
- Verify SWARM_API_URL points to: https://swarm-production-82b2.up.railway.app
- Verify SWARM_API_KEY matches: 1-2fsQxR1CdPeRaLQXIAom0kR6BavShlTs-bHBwTcsg
- Check SWARM service is healthy: curl https://swarm-production-82b2.up.railway.app/health

### Database errors
- If using PostgreSQL, verify DATABASE_URL is set
- If using SQLite, data will reset on redeploy (this is normal)
- Check database initialization logs

---

## Rollback

If deployment fails:
1. Go to Railway dashboard
2. Click on Tokencast service
3. Go to "Deployments" tab
4. Click "Rollback" on last working deployment

Or delete the service and recreate.
