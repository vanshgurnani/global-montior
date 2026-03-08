# Global Intelligence Monitor

AI-powered geopolitical intelligence platform with real-time threat monitoring, conflict analytics, market risk modeling, and a multi-panel operations dashboard.

## 1) System Overview
The platform is split into two services:
- `backend` (FastAPI + MongoDB): ingestion, scoring, intelligence synthesis, and API serving
- `frontend` (React + Vite + TypeScript): intelligence operations dashboard UI

High-level flow:
1. News is ingested from GDELT / NewsAPI / RSS.
2. Each article is enriched with sentiment + keyword + war risk.
3. Market snapshots are fetched from yfinance (indices/stocks/ETFs/crypto).
4. Prediction engine produces market direction/return probabilities.
5. Intelligence engine composes conflict, risk, forecast, and scenario views.
6. Frontend renders map + feeds + risk cards + drilldowns in a multi-screen layout.

## 2) Repository Structure
```text
global-montior/
  backend/
    app/
      api/
        routes/
          health.py
          news.py
          risk.py
          markets.py
          jobs.py
          intelligence.py
      core/
        config.py
        database.py
      jobs/
        scheduler.py
      schemas/
        news.py
        market.py
        risk.py
      services/
        news_service.py
        sentiment_service.py
        war_risk_service.py
        stock_service.py
        prediction_service.py
        market_pipeline.py
        risk_service.py
        risk_map_service.py
        youtube_service.py
        intelligence_service.py
      main.py
    requirements.txt
    Dockerfile
    .env

  frontend/
    src/
      main.tsx
      App.tsx
      globals.css
    components/
      RiskMap.tsx
      TrendChart.tsx
    lib/
      api.ts
    vite.config.ts
    package.json
    Dockerfile
    .env

  docker-compose.yml
  README.md
```

## 3) Backend Architecture

### 3.1 Core Services
- `NewsService`
  - Pulls articles from configured providers (`gdelt`, `newsapi`, `rss`)
  - Normalizes title/source/url/published_at
  - Enriches each article with sentiment, keyword score, war risk score, country, matched keywords

- `SentimentService`
  - Uses transformer sentiment model when available
  - Falls back safely if model load fails

- `WarRiskService`
  - Geopolitical keyword scoring
  - Country extraction from text
  - Combined war-risk function from sentiment + keyword density

- `StockService`
  - Fetches market snapshots via yfinance
  - Supports indices, stocks, ETFs, and crypto
  - Computes momentum, volume spike, MA20/MA50, VIX proxy
  - Classifies `asset_type` (`index`, `stock`, `etf`, `crypto`)
  - Prioritizes key symbols (including major crypto) when symbol cap is enforced

- `PredictionService`
  - Produces probability of up/down move + predicted 5D return
  - Uses trained model if available, fallback logic otherwise

- `MarketPipeline`
  - Joins macro sentiment/risk signals with market features
  - Refreshes and stores `market_snapshots`

- `RiskService`
  - Global war/sentiment overview
  - High-risk country aggregation

- `RiskMapService`
  - Returns map layers (war/nuclear/bunkers/chokepoints)

- `IntelligenceService`
  - Composes full intelligence dashboard payload:
    - conflict tracker
    - real-time sentiment
    - breaking event detection
    - global risk index
    - market impact predictor
    - commodity risk monitor
    - trade route/chokepoint risk
    - military/nuclear/civil unrest monitors
    - AI news summaries
    - event timeline
    - country risk dashboard
    - predictive geopolitics engine
    - classification outputs
    - 7D/30D forecast panel
    - UI metadata

### 3.2 API Routes
Base prefix: `/api/v1`

- Health
  - `GET /health`

- News
  - `GET /news/latest?limit=20`
  - `GET /news/stream?limit=15&interval_seconds=8` (SSE)
  - `GET /news/live-channels`

- Risk
  - `GET /risk/overview`
  - `GET /risk/map-layers`

- Markets
  - `GET /markets/snapshots`
  - `GET /markets/top-gainers?limit=5`
  - `GET /markets/stocks?limit=25`
  - `GET /markets/crypto?limit=25`

- Intelligence
  - `GET /intelligence/dashboard`
  - `GET /intelligence/country/{country}`

- Jobs
  - `POST /jobs/run-ingestion`
  - `POST /jobs/run-market-refresh`
  - `POST /jobs/refresh`
  - `POST /jobs/train-model`

### 3.3 Storage Model (MongoDB)
- `articles`
  - title, source, url, summary, country, published_at
  - sentiment_score, keyword_score, war_risk_score, matched_keywords

- `market_snapshots`
  - symbol, name, asset_type, price
  - momentum_7d, volume_spike_pct, ma20, ma50, vix_proxy
  - prob_up, prob_down, predicted_return_5d, confidence, risk_level, model_used, as_of

### 3.4 Background/Scheduling
- APScheduler job runner available in backend
- Supports periodic ingestion + market refresh flow

## 4) Frontend Architecture

### 4.1 App Composition
- `src/main.tsx`: app bootstrap
- `src/App.tsx`: orchestration + multi-panel dashboard
- `components/RiskMap.tsx`: global map + layer controls
- `components/TrendChart.tsx`: trend/market chart
- `lib/api.ts`: typed API client

### 4.2 Major Dashboard Panels
- Global risk + refresh controls
- High-risk countries with click-to-open threat popup
- Live news stream (SSE)
- Live news channels carousel
  - manual navigation
  - channel chips
  - optional auto-switch toggle
- Top predicted gainers table
- Conflict tracker
- Risk index block
- Market impact predictor
- Stocks & crypto data tables
- Commodity + chokepoint monitor
- Military / nuclear / civil unrest feeds
- AI summaries + timeline
- Country risk dashboard (drilldown)
- Predictive geopolitics + forecast
- Scenario simulation cards

### 4.3 High-Risk Country Popup
Clicking a country in "High-Risk Countries" opens a modal showing:
- risk percentage at top
- future market risk estimate
- sentiment
- military activity signals
- top potential threat headlines

## 5) Configuration

### 5.1 Backend (`backend/.env`)
Common keys:
- `MONGODB_URL`, `MONGODB_DB_NAME`
- `NEWS_PROVIDER`, `NEWS_SOURCES`, `NEWS_API_KEY`, `RSS_FEEDS`
- `YOUTUBE_API_KEY`
- `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`
- `STOCK_SYMBOLS=DEFAULT`
- `STOCK_HISTORY_PERIOD=6mo`
- `STOCK_MIN_POINTS=55`
- `STOCK_MAX_SYMBOLS=30`

### 5.2 Frontend (`frontend/.env`)
- `VITE_API_BASE=http://localhost:8000/api/v1`

## 6) Running the Project

### Local
Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

### Docker
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## 7) Current Capability Snapshot
- End-to-end ingestion -> scoring -> risk -> forecasting pipeline
- Real-time dashboard with intelligence-focused dark UI
- Country-level threat drilldown popup
- Stocks + crypto exposure integrated into risk workflow
- Scenario cards for quick strategic what-if monitoring

## 8) Disclaimer
Not financial advice.
