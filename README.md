# Global Intelligence Monitor

AI-powered global monitoring platform for geopolitical signals and market probability forecasting.

## Core Capabilities
- Multi-source news ingestion from GDELT + NewsAPI + RSS feeds
- Geopolitical keyword filtering (`war`, `sanctions`, `military`, `invasion`, `oil`, `economy`)
- HuggingFace sentiment analysis with fallback mode
- War risk scoring from sentiment + keyword density
- Market analytics using yfinance for major global indices
- Trainable XGBoost market model (direction + 5-day return)
- Professional dashboard with live world risk map, zoom/pan, and live news stream (SSE)
- Manual refresh workflow (user-triggered ingestion + model predictions)
- Dockerized deployment for Railway / Render / VPS

## Folder Structure
```text
global-intelligence-monitor/
  backend/
    app/
      api/routes/
      core/
      jobs/
      models/
      schemas/
      services/
      main.py
    requirements.txt
    Dockerfile
    .env.example
  frontend/
    app/
    components/
    lib/
    Dockerfile
    package.json
    .env.example
  docker-compose.yml
  README.md
```

## Backend Architecture
- `NewsService`: pulls and stores articles
- `SentimentService`: transformer-based sentiment scoring
- `WarRiskService`: keyword density and country extraction
- `StockService`: market index analytics (momentum, volume spike, MA20/MA50)
- `PredictionService`: trains XGBoost models from historical index data and predicts UP/DOWN + 5D return
- `MarketPipeline`: combines macro signals + market features into predictions

## Tracked Indices
- S&P 500 (`^GSPC`)
- NASDAQ (`^IXIC`)
- NIFTY 50 (`^NSEI`)
- FTSE 100 (`^FTSE`)
- Nikkei 225 (`^N225`)

## Stock Universe
- Default mode tracks a broad universe (global indices + ETFs + major US/Europe/Asia stocks).
- Configure with env vars in `backend/.env`:
  - `STOCK_SYMBOLS=DEFAULT` or comma-separated symbols (example: `DEFAULT,ADBE,NFLX,AMD`)
  - `STOCK_HISTORY_PERIOD=6mo`
  - `STOCK_MIN_POINTS=55`

## Local Run (No Docker)
### 1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### 3) MongoDB
Run local MongoDB and set `MONGODB_URL` + `MONGODB_DB_NAME` in `backend/.env`.

## Docker Run
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Sample API Endpoints
- `GET /api/v1/health`
- `GET /api/v1/news/latest?limit=20`
- `GET /api/v1/news/stream?limit=15&interval_seconds=8` (Server-Sent Events)
- `GET /api/v1/risk/overview`
- `GET /api/v1/markets/snapshots`
- `GET /api/v1/markets/top-gainers?limit=5`
- `POST /api/v1/jobs/run-ingestion`
- `POST /api/v1/jobs/run-market-refresh`
- `POST /api/v1/jobs/refresh` (train + ingest + market refresh)
- `POST /api/v1/jobs/train-model` (force retrain)

## Prediction Logic (v2)
Training data:
- Historical daily bars from `^GSPC`, `^IXIC`, `^NSEI`, `^FTSE`, `^N225`
- Historical VIX (`^VIX`)

Model features:
- 7-day momentum %
- Volume spike %
- MA20/MA50 gap %
- VIX level
- Macro adjustment at inference: sentiment score + keyword risk

Targets:
- Classification: next 5-day direction (UP/DOWN)
- Regression: next 5-day return %

Outputs per index snapshot:
- `prob_up`
- `prob_down`
- `predicted_return_5d`
- `confidence`
- `model_used` (`xgboost` or fallback `rule_based`)
- `risk_level` (`Low` / `Medium` / `High`)

## Deployment Notes
- Railway/Render: deploy `backend` and `frontend` as two services.
- Add managed MongoDB and inject env vars.
- Use a scheduler worker or keep APScheduler in backend process.

## Disclaimer
**Not financial advice.**
