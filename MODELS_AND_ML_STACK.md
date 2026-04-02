# Machine Learning Models & AI Stack Used

## Summary
Your application uses a diverse ML/AI stack combining statistical models, transformer-based NLP, XGBoost tree ensembles, and custom reinforcement learning policies.

---

## 1. **Sentiment Analysis Model**
**Service**: `sentiment_service.py`  
**Framework**: Hugging Face Transformers

### Models Used:
- **Primary**: `cardiffnlp/twitter-roberta-base-sentiment-latest`
  - Type: RoBERTa-based transformer fine-tuned on Twitter sentiment
  - Task: 3-class sentiment classification (positive, negative, neutral)
  - Input: Text (limited to 512 tokens)
  - Output: Score (-1.0 to +1.0)
  - Download: ~500MB (auto-cached first run)

### Fallback Mechanism:
- Uses rule-based sentiment scoring if:
  - Transformer model fails to load
  - `use_transformer_sentiment=False` in config
  - Rules: Keyword matching for explicit sentiment words

### Configuration:
```python
USE_TRANSFORMER_SENTIMENT=false  # Enable/disable transformer model
```

**Performance Impact**: 
- First inference: ~2-3s (model loading)
- Subsequent inference: ~100-500ms per article
- Cache size: 1 (LRU)

---

## 2. **Market Trend Prediction Models**
**Service**: `prediction_service.py`  
**Framework**: XGBoost

### Models Used:

#### A. **Classification Model - XGBClassifier**
- **Task**: Predicts up/down direction (binary: 1 = up, 0 = down)
- **Configuration**:
  - Estimators: 180
  - Max depth: 4
  - Learning rate: 0.05
  - Subsample: 0.9
  - Colsample bytree: 0.9
  - Objective: binary logistic

#### B. **Regression Model - XGBRegressor**
- **Task**: Predicts 5-day return percentage
- **Configuration**:
  - Estimators: 220
  - Max depth: 4
  - Learning rate: 0.05
  - Subsample: 0.9
  - Colsample bytree: 0.9
  - Objective: squared error

### Features (6 base + 4 optional with ground truth):

**Base Features** (always used):
1. `momentum_7d` - 7-day price momentum %
2. `volume_spike_pct` - Volume deviation from 20-day MA
3. `ma_gap` - Gap between 20-day and 50-day MA
4. `vix_now` - Current VIX level
5. `momentum_1d_ago` - 1-day lagged momentum
6. `momentum_3d_ago` - 3-day lagged momentum

**Enhanced Features** (when ground truth enabled):
7. `gdp_growth_pct` - Country GDP growth rate
8. `inflation_pct` - Country inflation rate
9. `debt_pct_gdp` - Country debt-to-GDP ratio (normalized)
10. `conflict_count_normalized` - 30-day conflict count (normalized)

### Training Data:
- **Symbols**: S&P 500, Nasdaq, Nifty 50, FTSE, Nikkei 225
- **Period**: 5 years
- **Minimum samples**: 300
- **Retraining**: Every 6 hours (configurable)

### Metrics Tracked:
- Classification accuracy
- Regression MAE (mean absolute error)

### Configuration:
```python
MODEL_AUTO_TRAIN_ON_REFRESH=false  # Auto-retrain on market refresh
MODEL_TRAIN_RETRY_MINUTES=60       # Retry failed training after N mins
```

---

## 3. **Event Classification Models**

### A. **Transformer-based Event Classifier**
**Service**: `event_classification_service.py`  
**Optional Model**: HuggingFace zero-shot classifier

**Supported Event Types**:
- Military escalation
- Sanctions
- Diplomatic tension
- Civil unrest

**Configuration**:
```python
USE_TRANSFORMER_EVENT_CLASSIFIER=false  # Enable transformer
```

### B. **OpenAI Embeddings-based Classifier**
**Model**: `text-embedding-3-small`
- Method: Cosine similarity matching with prototypes
- Lightweight alternative to transformer models
- No GPU required

**Configuration**:
```python
USE_OPENAI_EVENT_CLASSIFIER=false  # Enable OpenAI embeddings
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
OPENAI_API_KEY=your_key
```

### C. **Rule-based Classifier** (Always Active)
- Keyword matching for event detection
- Hardcoded rules for military, sanctions, diplomatic, civil unrest
- Fallback when other classifiers unavailable
- Instantaneous, no model loading

---

## 4. **Reinforcement Learning Policy**
**Service**: `reinforcement_learning_service.py`  
**Type**: Q-learning inspired policy (lightweight, no training required)

### Components:

#### State Representation:
- **Momentum**: bullish/neutral/bearish (based on 7-day momentum)
- **Sentiment**: positive/flat/negative (based on sentiment score)
- **Risk**: high_risk/medium_risk/low_risk (based on keyword risk + VIX)

#### Actions:
- `buy` - Long signal
- `hold` - Neutral signal
- `sell` - Short signal

#### Q-function (Value Calculation):
```python
q_buy = (predicted_return_5d * 0.55)
      + (momentum_7d * 0.20)
      + (sentiment_score * 2.0)
      - (keyword_risk * 2.4)
      - max(0.0, vix_proxy - 18.0) * 0.08
      + max(0.0, volume_spike_pct) * 0.01

q_sell = (-predicted_return_5d * 0.55)
       + max(0.0, -momentum_7d) * 0.22
       + max(0.0, -sentiment_score) * 2.0
       + (keyword_risk * 2.2)
       + max(0.0, vix_proxy - 18.0) * 0.08

q_hold = 0.75
       - abs(predicted_return_5d) * 0.08
       - abs(momentum_7d) * 0.03
       - abs(sentiment_score) * 0.4
       + max(0.0, 0.6 - keyword_risk) * 0.5
```

#### Output:
- Best action (highest Q-value)
- Confidence (0.25 - 0.95 range)
- State description

**Configuration**:
```python
RL_ENABLED=true  # Enable RL policy
RL_POLICY_NAME=market_q_policy_v1  # Policy version
```

---

## 5. **War Risk Analysis Models**
**Service**: `war_risk_service.py`

### Approach:
- **Beta coefficients** - Pre-calculated war risk sensitivity per symbol
- **Regression-based**: Asset returns = beta × war_risk_index

### Beta Values by Asset Class:

| Asset Type | Beta | Rationale |
|-----------|------|-----------|
| Gold (GLD) | +0.20 | Safe haven |
| Oil (USO, CL=F) | +0.25 | Supply shock sensitive |
| Bonds (TLT, IEF) | +0.06-0.08 | Flight-to-safety |
| Defense (RTX, LMT, NOC) | +0.12-0.14 | War beneficiaries |
| Boeing (BA) | +0.08 | Aerospace/defense |
| Tech (XLK, QQQ) | -0.15-0.18 | Growth hurt by uncertainty |
| S&P 500 (SPY, ^GSPC) | -0.15 | Broad market downturn |
| Nasdaq (^IXIC) | -0.18 | High growth stocks hurt |
| Utilities (XLU) | -0.05 | Slight defensive |
| Software (ACE) | -0.18 | High valuation compression |

---

## 6. **Ground Truth Models**
**Service**: `ground_truth_service.py`

### Data Sources (Not ML Models - Data Enrichment):

#### A. **Economic Data** (World Bank)
- GDP growth (%)
- Inflation rate (%)
- Debt-to-GDP ratio (%)
- Used as features for prediction model training

#### B. **Conflict Data** (ACLED - Armed Conflict Location & Event Data)
- Event counts by country and date
- Enriches features: `conflict_count`
- Optional (requires free API registration)

**Configuration**:
```python
GROUND_TRUTH_ENABLED=true
ACLED_API_KEY=your_key
ACLED_EMAIL=your_email
```

---

## 7. **Data Aggregation & Statistical Models**

### Intelligence Service (`intelligence_service.py`)
- **Sentiment Heatmap**: Aggregates sentiment by country
- **Risk Aggregation**: Country-level risk scores
- **Correlation Analysis**: Cross-border event spillovers
- **Moving Averages**: 7, 14, 30-day sentiment/risk windows

### Market Pipeline (`market_pipeline.py`)
- Stock history fetching (yfinance)
- Feature engineering
- Data pipeline orchestration

---

## 8. **Deep Learning Stack** (Optional, Not Fully Integrated)

### Installed but Optional:
```
transformers  - HuggingFace NLP models
torch         - PyTorch deep learning framework
scikit-learn  - ML utilities & preprocessing
```

**Note**: These add ~2-3GB to Docker image. Consider slim builds for production.

---

## Performance & Resource Comparison

| Model | Type | Inference Time | Memory | GPU Required | Status |
|-------|------|-----------------|--------|--------------|--------|
| RoBERTa Sentiment | Transformer | 100-500ms | 1.2GB | No | **Enabled** |
| XGBoost Classifier | Tree ensemble | <10ms | 50MB | No | **Enabled** |
| XGBoost Regressor | Tree ensemble | <10ms | 50MB | No | **Enabled** |
| Event Classifier | Rule-based | <1ms | <1MB | No | **Always active** |
| Event Classifier | Transformer | 50-100ms | 1GB | No | Optional |
| Event Classifier | OpenAI | 200-300ms | API | No | Optional |
| RL Policy | Rule-based | <1ms | <1MB | No | **Enabled** |
| War Risk | Beta lookup | <1ms | <1MB | No | **Enabled** |

---

## Configuration Flags

### Enable/Disable Models:

```python
# Core Sentiment
USE_TRANSFORMER_SENTIMENT = false (default: use rules)

# Event Classification
USE_TRANSFORMER_EVENT_CLASSIFIER = false
USE_OPENAI_EVENT_CLASSIFIER = false

# Ground Truth Data
GROUND_TRUTH_ENABLED = true
ACLED_API_KEY = (optional)
ACLED_EMAIL = (optional)

# RL Policy
RL_ENABLED = true
RL_POLICY_NAME = market_q_policy_v1

# Model Training
MODEL_AUTO_TRAIN_ON_REFRESH = false
MODEL_TRAIN_RETRY_MINUTES = 60
```

---

## API Response Models

### Example Prediction Response:
```json
{
  "symbol": "^GSPC",
  "prob_up": 0.65,
  "prob_down": 0.35,
  "risk_level": "medium",
  "explanation": "Moderate geopolitical risk with positive momentum",
  "predicted_return_5d": 2.34,
  "confidence": 0.78,
  "model_used": "XGBoost (180 cls, 220 reg)",
  "trained_at": "2026-04-03T10:30:00Z",
  "age_hours": 0.5
}
```

### Example Event Classification Response:
```json
{
  "event_type": "military_escalation",
  "severity_score": 0.78,
  "severity": "high",
  "confidence": 0.85,
  "rationale": "Article mentions military operations, escalation keywords detected"
}
```

---

## Recommendations for Optimization

### Production Improvements:
1. **Cache model outputs** - Add Redis for 24h sentiment/event classification cache
2. **Batch inference** - Process articles in batches (5-10) for transformers
3. **Model quantization** - Convert RoBERTa to ONNX for 50% faster inference
4. **Separate services**:
   - Move heavy models to separate worker
   - Keep API lightweight for Render free tier
5. **Use ClearML/MLflow** - Track model versions and performance
6. **A/B Testing** - Compare rule-based vs transformer performance

### Model Improvements:
1. Retrain sentiment model on domain-specific news articles
2. Fine-tune event classifier on your news data
3. Implement proper Q-learning training for RL policy
4. Add LSTM for time-series forecasting (stock return)

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **NLP Sentiment** | cardiffnlp/twitter-roberta | Article sentiment |
| **Structured Prediction** | XGBoost | Market direction & returns |
| **Decision Policy** | Q-learning (custom) | Trading signals |
| **Event Detection** | Rule-based + optional transformers | Geopolitical events |
| **Data Pipeline** | yfinance, ACLED API, World Bank | Feature engineering |
| **Framework** | FastAPI + AsyncIO | API serving |
| **Database** | MongoDB | Data persistence |
| **Scheduling** | APScheduler | Periodic model training & data ingestion |
