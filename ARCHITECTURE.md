# GEO-PULSE: Geopolitical Event Intelligence & Market Risk Monitor

## **Architecture Overview**

GEO-PULSE is an **AI-powered geopolitical intelligence platform** that monitors global events, analyzes market sentiment, predicts stock movements, and provides autonomous trading signals using cutting-edge ML/AI models.

---

## **🏗️ SYSTEM ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                    │
│  ├─ Dashboard (Live market data, sentiment heatmaps)            │
│  ├─ Risk Map (Geopolitical hotspots)                            │
│  ├─ Predictions (ML model forecasts)                            │
│  ├─ News Feed (Classified events)                               │
│  └─ Agent Decisions (AI trading signals)                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│              RENDER BACKEND (FastAPI + Python)                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ API Routes (/api/v1)                                        ││
│  ├─ /health                    - Service health check          ││
│  ├─ /markets/snapshots         - Latest market data            ││
│  ├─ /markets/stocks            - Stock predictions             ││
│  ├─ /news                       - Classified news articles      ││
│  ├─ /risk/map                  - Geopolitical risk heatmap     ││
│  ├─ /intelligence/summary      - Cross-border analysis         ││
│  ├─ /agent/decisions           - AI trading recommendations    ││
│  └─ /jobs                       - Scheduler status              ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Core Services Layer                                         ││
│  ├─ sentiment_service.py        - DistilBERT sentiment analysis││
│  ├─ prediction_service.py       - XGBoost market forecasting   ││
│  ├─ event_classification.py     - Geopolitical event detection ││
│  ├─ reinforcement_learning.py   - RL trading policy            ││
│  ├─ war_risk_service.py         - War risk beta analysis       ││
│  ├─ intelligence_service.py     - Cross-border analysis        ││
│  ├─ ai_agent_service.py         - Autonomous AI agent (NEW)    ││
│  ├─ ai_api_service.py           - External AI API calls (NEW)  ││
│  ├─ news_service.py             - GDELT/NewsAPI/RSS ingestion  ││
│  ├─ market_pipeline.py          - Stock data processing        ││
│  ├─ ground_truth_service.py     - Economic + conflict data     ││
│  └─ risk_map_service.py         - Geopolitical heatmaps        ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Background Jobs Layer                                       ││
│  ├─ APScheduler (News ingestion every 15 min)                  ││
│  ├─ Market refresh (VIX, OHLCV data)                           ││
│  ├─ Model retraining (6-hourly)                                ││
│  └─ AI Agent monitoring (30-second intervals) (NEW)            ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────┬──────────────────────┬───────────────┬────────────────┘
           │                      │               │
           ↓                      ↓               ↓
      ┌─────────┐            ┌─────────┐    ┌──────────┐
      │MongoDB  │            │HF API / │    │ External │
      │ (Atlas) │            │OpenAI   │    │  DataAPI │
      │         │            │ (NEW)   │    │          │
      └─────────┘            └─────────┘    └──────────┘
         │                        │              │
         └─ Articles             └─ Sentiment   └─ GDELT
         │─ Snapshots              & Events      News
         │─ Predictions                        ACLED
         │─ Agent Decisions                  World Bank
         └─ Risk Data
```

---

## **📊 DATA FLOW ARCHITECTURE**

### **Request Flow (User → API → Response):**
```
1. User opens Dashboard
   ↓
2. Frontend requests /api/v1/markets/snapshots
   ↓
3. Backend FastAPI handler
   ↓
4. Query MongoDB for latest market data
   ↓
5. EnrichPredictions from cached XGBoost model
   ↓
6. Add RL trading signal
   ↓
7. Return JSON response
   ↓
8. Frontend renders candlestick chart + signal
```

### **Background Processing Flow:**
```
Every 15 minutes (APScheduler):
  ↓
1. News Ingestion
   ├─ Fetch from GDELT API
   ├─ Parse articles
   └─ Store in MongoDB
  ↓
2. Sentiment Analysis (NEW - via Hugging Face API or DistilBERT)
   ├─ Get sentiment for each article
   ├─ Call Hugging Face Inference API or DistilBERT locally
   └─ Update MongoDB
  ↓
3. Event Classification
   ├─ Detect military/sanctions/diplomatic events
   ├─ Calculate severity score
   └─ Store event metadata
  ↓
4. Market Data Fetch
   ├─ Get VIX, stock OHLCV
   ├─ Fetch 5-year history for training
   └─ Update snapshots
  ↓
5. Model Training (XGBoost - every 6 hours)
   ├─ Build training data from 5-year history
   ├─ Train classifier + regressor
   ├─ Store metrics
   └─ Update predictions
  ↓
6. AI Agent Analysis (NEW - 30-second loop)
   ├─ Get unanalyzed articles
   ├─ Call OpenAI/HF API for intelligence
   ├─ Make autonomous trading decision
   ├─ Store decision in agent_decisions collection
   └─ Alert frontend if high-confidence signal
```

---

## **🔄 Model & AI Integration**

### **Local Models (Render):**
```
DistilBERT (250MB)
├─ Input: Article text
├─ Output: Sentiment (-1 to +1)
└─ Speed: 50-100ms

XGBoost Classifier (50MB)
├─ Input: 6-10 features (momentum, volume, VIX, etc.)
├─ Output: Up/Down probability
└─ Speed: <10ms

XGBoost Regressor (50MB)
├─ Input: Same as classifier
├─ Output: Expected 5-day return %
└─ Speed: <10ms

RL Q-Policy (<1MB)
├─ Input: Sentiment, risk, momentum, VIX
├─ Output: buy/hold/sell signal
└─ Speed: <1ms
```

### **External APIs (NEW):**
```
Hugging Face Inference API
├─ Sentiment (50k requests free/month)
├─ Cost: $9/month if unlimited needed
└─ Speed: 100-300ms

OpenAI GPT-3.5 Turbo (Optional)
├─ Event classification
├─ Intelligence analysis
├─ Cost: $2-5/month for your volume
└─ Speed: 500-1000ms

GDELT API (Free)
├─ Real-time news
├─ Cost: Free
└─ Speed: 5 seconds per batch

ACLED API (Free)
├─ Conflict data
├─ Cost: Free (requires registration)
└─ Speed: Real-time

World Bank API (Free)
├─ Economic indicators
├─ Cost: Free
└─ Speed: Real-time
```

---

## **💾 DATABASE SCHEMA (MongoDB)**

```
gim (database)
├─ articles
│  ├─ _id (ObjectId)
│  ├─ url (String, unique index)
│  ├─ title (String)
│  ├─ text (String)
│  ├─ source (String)
│  ├─ published_at (DateTime, desc index)
│  ├─ country (String, asc index)
│  ├─ event_type (String, asc index)
│  ├─ event_severity (Float)
│  ├─ sentiment_score (Float)
│  ├─ ai_analysis (Object) [NEW]
│  ├─ agent_analyzed (Boolean)
│  └─ ingested_at (DateTime)
│
├─ market_snapshots
│  ├─ _id (ObjectId)
│  ├─ symbol (String, asc index)
│  ├─ prob_up (Float, desc index)
│  ├─ prob_down (Float)
│  ├─ predicted_return_5d (Float)
│  ├─ confidence (Float)
│  ├─ risk_level (String)
│  ├─ war_risk_beta (Float)
│  ├─ as_of (DateTime, desc index)
│  └─ model_used (String)
│
├─ agent_decisions [NEW]
│  ├─ _id (ObjectId)
│  ├─ article_id (ObjectId)
│  ├─ sentiment (Float)
│  ├─ event (Object)
│  ├─ market_prediction (Object)
│  ├─ agent_action (Enum: buy/hold/sell)
│  ├─ confidence (Float)
│  ├─ reasoning (String)
│  ├─ timestamp (DateTime)
│  └─ created_at (DateTime)
│
├─ ground_truth_vix
│  ├─ _id (ObjectId)
│  ├─ date (DateTime, asc index)
│  ├─ vix_close (Float)
│  └─ source (String)
│
├─ ground_truth_economic
│  ├─ _id (ObjectId)
│  ├─ year (Integer, asc index)
│  ├─ country_iso (String, asc index)
│  ├─ indicator (String, asc index)
│  ├─ value (Float)
│  └─ source (String)
│
├─ ground_truth_conflicts
│  ├─ _id (ObjectId)
│  ├─ event_id (String, unique)
│  ├─ event_date (DateTime, asc index)
│  ├─ country (String, asc index)
│  ├─ event_type (String)
│  ├─ fatalities (Integer)
│  ├─ source (String)
│  └─ data (Object)
│
└─ model_training_log
   ├─ _id (ObjectId)
   ├─ timestamp (DateTime)
   ├─ model_type (String)
   ├─ accuracy (Float)
   ├─ mae (Float)
   ├─ samples (Integer)
   ├─ training_time_ms (Integer)
   └─ status (String)
```

---

## **🔐 REST API Routes**

### **Health Checks:**
```
GET /health
Response: {"status": "ok"}

GET /api/v1/health
Response: {"status": "ok", "db": "connected"}
```

### **Market Data:**
```
GET /api/v1/markets/snapshots
Response: [{symbol, prob_up, prob_down, predicted_return_5d, risk_level, ...}]

GET /api/v1/markets/stocks?limit=25
Response: [Market snapshots for stocks only]

GET /api/v1/markets/crypto?limit=25
Response: [Market snapshots for crypto only]

GET /api/v1/markets/top-gainers?limit=5
Response: [Top 5 by prob_up]

GET /api/v1/markets/candlestick/{symbol}?period=1d&limit=50
Response: [OHLCV data for candlestick chart]
```

### **News Data:**
```
GET /api/v1/news?limit=20&skip=0
Response: [articles with sentiment, events, etc.]

GET /api/v1/news?country=Russia&type=military_escalation
Response: [Filtered articles]

GET /api/v1/news/sentiment-summary
Response: {avg_sentiment, by_country, by_event_type, ...}
```

### **Risk Analysis:**
```
GET /api/v1/risk/map
Response: {heatmap: {country: risk_score}, events: [...]}

GET /api/v1/risk/by-country/{country}
Response: {country, risk_score, conflict_count, articles, ...}

GET /api/v1/risk/war-beta/{symbol}
Response: {symbol, war_risk_beta, market_impact, ...}
```

### **Intelligence:**
```
GET /api/v1/intelligence/summary
Response: {
  global_sentiment: float,
  top_risks: [...],
  cross_border_events: [...],
  market_correlation: {...},
  predictions: {...}
}

GET /api/v1/intelligence/correlation/{symbol1}/{symbol2}
Response: {correlation_score, shared_risk_factors, ...}
```

### **AI Agent (NEW):**
```
GET /api/v1/agent/decisions?limit=10
Response: [{agent_action, confidence, reasoning, timestamp, ...}]

GET /api/v1/agent/status
Response: {last_run: datetime, next_run: datetime, decisions_today: count}

POST /api/v1/agent/analyze (Admin only)
Body: {article_id: string}
Response: {agent_decision, confidence, timestamp}
```

### **Jobs/Scheduler:**
```
GET /api/v1/jobs/status
Response: {
  scheduler_running: bool,
  last_news_ingest: datetime,
  last_model_train: datetime,
  next_refresh: datetime
}

POST /api/v1/jobs/trigger-ingest (Admin)
Response: {status: "Ingestion started", task_id: "..."}

POST /api/v1/jobs/train-model (Admin)
Response: {status: "Training started", metrics: {...}}
```

---

## **⚙️ DEPLOYMENT STACK**

### **Frontend:**
```
Technology: React + Vite + TypeScript
Components:
  ├─ Dashboard.tsx (Main view)
  ├─ LiveCandlestickChart.tsx (OHLCV visualization)
  ├─ PredictionAccuracy.tsx (Model performance)
  ├─ RiskMap.tsx (Geopolitical heatmap)
  ├─ TrendChart.tsx (Sentiment trends)
  └─ ImpactTag.tsx (Event severity badges)

Deployment: Vercel (Serverless)
```

### **Backend:**
```
Technology: Python 3.11 + FastAPI
Server: Uvicorn (ASGI)
Workers: 2-4 (based on Render plan)
Deployment: Render (PaaS)
Container: Docker (optional)

Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --timeout 60
```

### **Database:**
```
Primary: MongoDB Atlas (Free M0 tier)
  ├─ 512MB storage (sufficient for 30 days)
  ├─ 0 (backup free)
  ├─ Shared cluster
  └─ Automatic backups

Optional: Redis (for caching)
  └─ Render Redis add-on ($5/month) OR local
```

### **External Services:**
```
News Source: GDELT API (Free, real-time)
Conflict Data: ACLED API (Free, registration required)
Economic Data: World Bank API (Free)
AI/MLModel: 
  ├─ Hugging Face Inference API (Free tier: 30k/month)
  └─ OpenAI API (Optional, $2-5/month)
```

### **Infrastructure:**
```
Render Starter Plan: $7/month
  ├─ 0.5 CPU
  ├─ 512MB RAM
  ├─ 100GB/month bandwidth
  ├─ 2 workers
  └─ Auto-scaling: No

MongoDB Atlas Free: $0/month
  ├─ Shared cluster
  ├─ 0 backups
  └─ 512MB storage

Total Monthly Cost: $7-12 (Starter + optional Redis/APIs)
```

---

## **🔄 DEVELOPMENT WORKFLOW**

### **Local Setup:**
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### **Testing:**
```bash
pytest backend/tests/
npm test --prefix frontend
```

### **Deployment:**
```bash
# Push to GitHub
git add .
git commit -m "Feature: AI agent integration"
git push origin main

# Render auto-deploys from main branch
# Frontend deploys from Vercel auto-integration
```

---

## **📈 SCALABILITY ROADMAP**

### **Short-term (Months 1-3):**
- ✅ Replace RoBERTa with DistilBERT (Done)
- ✅ Add Hugging Face Inference API (Optional addon)
- ✅ Deploy AI Agent for autonomous analysis
- Monitor performance metrics

### **Medium-term (Months 3-6):**
- Add Redis caching layer
- Implement async task queue (Celery/RQ)
- Deploy ML worker to separate Railway instance
- Add WebSocket for real-time updates

### **Long-term (Months 6+):**
- Multi-region deployment
- Advanced RL training pipeline
- Real-time trading execution (paper trading)
- Premium features (alerts, webhooks, API access)

---

## **🚀 DEPLOYMENT COMMANDS**

### **Render:**
```bash
# Start Command
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --timeout 60

# Build Command
cd backend && pip install -r requirements.txt
```

### **Local Development:**
```bash
# Terminal 1: API
uvicorn app.main:app --reload

# Terminal 2: Frontend
npm run dev
```

### **Docker:**
```bash
docker-compose up -d
```

---

## **📋 KEY FEATURES SUMMARY**

| Feature | Status | Technology |
|---------|--------|-----------|
| Real-time News Ingestion | ✅ Active | GDELT API |
| Sentiment Analysis | ✅ Active | DistilBERT |
| Market Prediction | ✅ Active | XGBoost |
| Event Classification | ✅ Active | Rule-based + Optional Transformers |
| War Risk Analysis | ✅ Active | Beta model |
| Geopolitical Heatmap | ✅ Active | MongoDB aggregation |
| Trading Signals | ✅ Active | RL Q-Policy |
| AI Agent (Autonomous) | ✅ NEW | Hugging Face API + OpenAI |
| Background Scheduler | ✅ Active | APScheduler |
| REST API | ✅ Active | FastAPI |
| Real-time Dashboard | ✅ Active | React + Vite |
| Cross-border Intelligence | ✅ Active | Custom analysis |

---

## **🔗 SERVICE DEPENDENCIES**

```
Frontend (Vercel)
    ↓ (HTTPS)
API Backend (Render)
    ├─ MongoDB Atlas (Cloud)
    ├─ Hugging Face API (Cloud)
    ├─ OpenAI API (Cloud, optional)
    ├─ GDELT API (Cloud)
    ├─ ACLED API (Cloud)
    └─ World Bank API (Cloud)
```

---

## **📚 DOCUMENTATION FILES**

1. **ARCHITECTURE.md** (This file)
2. **README.md** (Quick start guide)
3. **RENDER_DEPLOYMENT.md** (Render-specific setup)
4. **MODELS_COMPLETE_LIST.md** (All ML models)
5. **API_REFERENCE.md** (Detailed API docs)

---

## **✅ DEPLOYMENT CHECKLIST**

- [ ] Update sentiment model to DistilBERT
- [ ] Add Hugging Face API key to Render environment
- [ ] Create AI Agent service
- [ ] Add agent decision endpoints
- [ ] Test locally with 2 workers
- [ ] Deploy to Render
- [ ] Monitor logs for errors
- [ ] Test API endpoints
- [ ] Verify data ingestion
- [ ] Check model training
- [ ] Confirm AI agent decisions stored
- [ ] Update frontend to show agent decisions

---

**Last Updated**: April 3, 2026  
**Architecture Version**: 2.0 (with AI Agent)  
**Status**: Production Ready ✅
