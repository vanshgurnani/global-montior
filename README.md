# Global Intelligence Monitor

AI-powered geopolitical monitoring platform with conflict intelligence, real-time sentiment analytics, market impact modeling, and multi-panel operations dashboard.

## What It Does
- Ingests live news from GDELT + NewsAPI + RSS
- Runs sentiment and war-risk scoring per article
- Detects and classifies high-impact events (war, sanctions, diplomacy, economic crisis, terrorism)
- Builds a global risk index (war + energy + market)
- Tracks conflict theaters (Russia-Ukraine, Israel-Hamas, Taiwan Strait)
- Monitors chokepoints (Hormuz, Suez, Bab el-Mandeb, Taiwan Strait)
- Surfaces military, nuclear, and civil unrest signals
- Produces AI-style short intelligence briefings + event timeline
- Predicts market direction and 5-day return probabilities
- Tracks stocks and crypto datasets
- Provides country drill-down intelligence snapshots

## Tech Stack
- Backend: FastAPI + MongoDB
- Frontend: React + Vite + TypeScript
- Data/Sources: yfinance, GDELT, NewsAPI, RSS, YouTube channels

## Project Structure
```text
global-montior/
  backend/
    app/
      api/routes/
      core/
      jobs/
      schemas/
      services/
    requirements.txt
    Dockerfile
    .env
  frontend/
    src/
    components/
    lib/
    package.json
    vite.config.ts
    Dockerfile
    .env
  docker-compose.yml
  README.md
```

## Key Backend Services
- `NewsService`: ingestion + normalization + scoring
- `SentimentService`: sentiment model wrapper with fallback
- `WarRiskService`: keyword/country extraction + risk scoring
- `StockService`: pulls indices, equities, ETFs, crypto snapshots
- `PredictionService`: market probability + return prediction engine
- `IntelligenceService`: conflict tracker, timeline, alerts, forecasts, country dashboard

## Main API Endpoints
- `GET /api/v1/health`
- `GET /api/v1/news/latest?limit=20`
- `GET /api/v1/news/stream?limit=15&interval_seconds=8`
- `GET /api/v1/news/live-channels`
- `GET /api/v1/risk/overview`
- `GET /api/v1/risk/map-layers`
- `GET /api/v1/markets/snapshots`
- `GET /api/v1/markets/top-gainers?limit=5`
- `GET /api/v1/markets/stocks?limit=25`
- `GET /api/v1/markets/crypto?limit=25`
- `GET /api/v1/intelligence/dashboard`
- `GET /api/v1/intelligence/country/{country}`
- `POST /api/v1/jobs/refresh`

## Environment Variables
Set in `backend/.env`:
- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `NEWS_PROVIDER`
- `NEWS_SOURCES`
- `NEWS_API_KEY`
- `YOUTUBE_API_KEY`
- `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`
- `STOCK_SYMBOLS=DEFAULT` (supports custom CSV and crypto symbols like `BTC-USD`)
- `STOCK_HISTORY_PERIOD=6mo`
- `STOCK_MIN_POINTS=55`
- `STOCK_MAX_SYMBOLS=30`

Set in `frontend/.env`:
- `VITE_API_BASE=http://localhost:8000/api/v1`

## Run Locally
### 1) Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3) MongoDB
Run MongoDB locally (or use Docker) and ensure backend env vars point to it.

## Run with Docker
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Dashboard Notes
- Live News Channels carousel now supports:
  - auto-switch every 12 seconds
  - hover pause
  - manual channel selection
  - `Auto switch ON/OFF` toggle

## Disclaimer
Not financial advice.
