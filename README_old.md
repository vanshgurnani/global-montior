# Global Intelligence Monitor

Geopolitical and market intelligence stack: **FastAPI + MongoDB** backend for ingestion, scoring, and intelligence APIs; **React + Vite + TypeScript** frontend for a multi-panel operations dashboard (dark UI, map, live feeds, markets).

---

## Current state (snapshot)

| Area | Details |
|------|---------|
| **Backend** | FastAPI app with `/api/v1` router; MongoDB via PyMongo; APScheduler in a background thread on startup; optional XGBoost prediction, RL policy hooks, ground-truth ingestion (VIX / World Bank / ACLED). |
| **Frontend** | Single-page app: `App.tsx` is the main screen (`Dashboard.tsx` is an alternate layout). Map + news embed + candlestick + tables + intel cards; styles in `src/globals.css` (viewport-aware grid for map/candlestick/bottom pane). |
| **Deploy** | Docker Compose brings up MongoDB, backend, and frontend. CORS in `main.py` includes `https://global-montior.vercel.app` for a hosted UI. |

---

## System flow

1. News ingested from **GDELT** / **NewsAPI** / **RSS** (configurable).
2. Articles enriched with sentiment, keyword and war-risk scores; optional **event classification** (transformer or OpenAI embeddings, feature-flagged).
3. **Market snapshots** refreshed via **yfinance** (indices, stocks, ETFs, crypto).
4. **Prediction** + optional **RL** actions attached to snapshots; stored in MongoDB.
5. **Intelligence** payload aggregates conflict tracker, risk index, forecasts, country views, etc.
6. UI polls APIs and streams news (SSE); map loads OSINT overlays when layers are enabled.

---

## Repository layout

```text
global-montior/
  backend/
    app/
      api/routes/      health, news, risk, markets, jobs, intelligence
      core/            config.py, database.py
      jobs/            scheduler.py
      models/          article, market_snapshot
      schemas/         news, market, risk
      services/        see “Backend services” below
      main.py
    requirements.txt
    Dockerfile
    .env               (local; not committed)
  frontend/
    src/               main.tsx, App.tsx, globals.css
    components/        RiskMap, LiveCandlestickChart, TrendChart, dashboard/, ui/
    lib/               api.ts
    vite.config.ts
    package.json
    Dockerfile
    .env
  docker-compose.yml
  README.md
```

---

## Backend services

| Service | Role |
|---------|------|
| `NewsService` | Ingestion, normalization, enrichment |
| `SentimentService` | Transformer or fallback sentiment |
| `WarRiskService` | Keyword + country extraction + war-risk scoring |
| `EventClassificationService` | Optional event type/severity on articles (`use_transformer_*` / `use_openai_*` in config) |
| `StockService` | yfinance snapshots, OHLC **candles** for charts |
| `PredictionService` | Up/down probability, predicted return; optional training |
| `ReinforcementLearningService` | RL-style actions on snapshots (`rl_enabled`) |
| `MarketPipeline` | Joins signals, refreshes `market_snapshots` |
| `RiskService` | Global overview, high-risk countries |
| `RiskMapService` | Map layers + optional OSINT overlays |
| `GroundTruthService` | VIX, World Bank, ACLED when enabled |
| `IntelligenceService` | Full dashboard payload |
| `YouTubeService` | Resolves live channel embeds |

---

## API (`/api/v1`)

All routes below are prefixed with **`/api/v1`**.

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | Liveness |
| GET | `/news/latest` | `?limit=` |
| GET | `/news/stream` | SSE; `?interval_seconds=` |
| GET | `/news/live-channels` | YouTube live channels |
| GET | `/risk/overview` | Global risk |
| GET | `/risk/map-layers` | `?include_osint=` `&overlays=` (comma-separated OSINT keys) |
| GET | `/markets/snapshots` | All stored snapshots |
| GET | `/markets/top-gainers` | `?limit=` |
| GET | `/markets/stocks` | `?limit=` (≤100) |
| GET | `/markets/crypto` | `?limit=` |
| GET | `/markets/candles` | `symbol`, `period`, `interval`, `limit` (10–200) — candlestick UI |
| POST | `/jobs/refresh` | Ingest news, refresh markets, optional ground truth, optional model train |
| GET | `/intelligence/dashboard` | Full intel JSON |
| GET | `/intelligence/country/{country}` | Country slice |

**Root:** `GET /` returns `{ name, disclaimer }`. Interactive docs: **`/docs`**.

---

## MongoDB collections (high level)

- **`articles`** — text, scores, sentiment, war risk, optional event fields  
- **`market_snapshots`** — price, momentum, predictions, RL fields, `as_of`  
- **`ground_truth_vix`**, **`ground_truth_economic`**, **`ground_truth_conflicts`** — when ground truth is enabled  

---

## Configuration (`backend/.env`)

Loaded via Pydantic Settings (`app/core/config.py`). Common variables:

| Variable | Purpose |
|----------|---------|
| `MONGODB_URL`, `MONGODB_DB_NAME` | Mongo connection |
| `NEWS_PROVIDER`, `NEWS_SOURCES`, `NEWS_API_KEY`, `RSS_FEEDS`, `NEWS_INGEST_LIMIT` | News ingestion |
| `YOUTUBE_API_KEY` | Live channels |
| `CORS_ORIGINS` | Comma-separated origins (note: production CORS also lists Vercel in `main.py`) |
| `STOCK_SYMBOLS`, `STOCK_HISTORY_PERIOD`, `STOCK_MIN_POINTS`, `STOCK_MAX_SYMBOLS` | Markets |
| `MODEL_AUTO_TRAIN_ON_REFRESH`, `MODEL_TRAIN_RETRY_MINUTES` | Training on refresh |
| `USE_TRANSFORMER_SENTIMENT` | Heavier sentiment path |
| `RL_ENABLED`, `RL_POLICY_NAME` | RL policy |
| `USE_TRANSFORMER_EVENT_CLASSIFIER`, `USE_OPENAI_EVENT_CLASSIFIER`, `OPENAI_API_KEY`, `OPENAI_EMBEDDINGS_MODEL` | Event classification |
| `GROUND_TRUTH_ENABLED`, `ACLED_API_KEY`, `ACLED_EMAIL` | Ground truth |
| `SCHEDULER_ENABLED`, `SCHEDULER_INTERVAL_MINUTES` | Background jobs |

**Frontend (`frontend/.env`):** `VITE_API_BASE=http://localhost:8000/api/v1` (or your deployed API URL).

---

## Frontend (`frontend`)

- **Entry:** `src/main.tsx` → `App.tsx` (not `Dashboard.tsx` by default).
- **Map:** `components/RiskMap.tsx` — heatmap, zoom, layer chips, OSINT layers when requested.
- **Markets:** `LiveCandlestickChart.tsx` (`/markets/candles`), `TrendChart.tsx` (Recharts).
- **API:** `lib/api.ts` — typed client; Vite alias `@` → project root.
- **Layout:** CSS grid (`screen-grid`): map (top-left), live news + candlestick (right), gainers / high-risk / trend (bottom-left), intel cards below. Map and candlestick use viewport-relative sizing so more content fits on one screen (`globals.css`).

**Dependencies (current):** React 18, Vite 5, `react-simple-maps`, `recharts`.

---

## Run locally

**Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Vite dev server defaults to port **5173**; ensure `VITE_API_BASE` points at the API.

**Docker Compose**

```bash
docker compose up --build
```

`docker-compose.yml` references `env_file` paths for backend and frontend; if those files are missing, copy from your local **`backend/.env`** / **`frontend/.env`** or add the example files the compose file expects. Published ports: MongoDB **27017**, API **8000**, UI **3000** (Vite preview in the frontend image).

---

## Prediction / ML (brief)

- Rolling sentiment windows and lagged momentum features; **XGBoost** when trained.  
- Ground truth (VIX, macro, ACLED) can support training/validation when enabled.  
- RL policy is optional and stored on snapshots.

---

## Disclaimer

Not financial advice.
