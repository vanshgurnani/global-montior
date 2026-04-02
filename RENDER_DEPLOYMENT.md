# Render Deployment Guide - Performance Optimization

## Critical Issues Fixed

### 1. ✅ Database Connection Pooling
- **Issue**: Aggressive timeouts (5s) caused "Service Denied" on Render
- **Fix**: 
  - Increased timeouts to 30s (Render has variable latency)
  - Added connection pooling: `maxPoolSize=50`, `minPoolSize=10`
  - Enabled retry for transient failures

### 2. ✅ Environment Configuration
- **Issue**: Debug mode enabled in production, hardcoded CORS
- **Fix**:
  - Set `debug=False` by default
  - Dynamic CORS origins based on environment
  - Added request timeout settings

### 3. ✅ Startup Performance
- **Issue**: Initial data ingestion could block requests
- **Fix**:
  - Background scheduler starts after 2s delay
  - Errors in scheduler don't block API startup

## Render Environment Setup

### Backend Environment Variables

Create a `.env` file for Render with these settings:

```bash
# Application
APP_ENV=production
DEBUG=false

# Database (use Render PostgreSQL or external MongoDB Atlas)
MONGODB_URL=mongodb+srv://username:password@your-cluster.mongodb.net/gim?retryWrites=true&w=majority
MONGODB_DB_NAME=gim

# API Keys
NEWS_API_KEY=your_news_api_key
YOUTUBE_API_KEY=your_youtube_key
OPENAI_API_KEY=your_openai_key
ACLED_API_KEY=your_acled_key
ACLED_EMAIL=your_acled_email

# Features
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_MINUTES=15
GROUND_TRUTH_ENABLED=true

# CORS (only your frontend)
CORS_ORIGINS=https://global-montior.vercel.app,https://global-montior.netlify.app
```

### Render Service Configuration

**Backend Service Settings:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
- **Instance Type**: Standard (minimum for production)
- **Plan**: At least $7/month (to prevent cold starts on Free tier)

**Environment Variables:**
In Render dashboard → Environment:
```
APP_ENV = production
DEBUG = false
MONGODB_URL = (your MongoDB Atlas URL)
```

## Database Optimization for Render

### MongoDB Atlas Setup (Recommended)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free tier M0 cluster
3. Add your Render IP to IP Whitelist (0.0.0.0/0 for development)
4. Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/gim`

### Connection String Format
```
mongodb+srv://username:password@cluster-name.mongodb.net/database_name?retryWrites=true&w=majority
```

## Performance Tuning

### 1. Database Query Optimization
Queries are now indexed on:
- Articles: url (unique), published_at, country, event_type
- Market snapshots: symbol, prob_up, as_of
- Ground truth: date, year, country_iso, indicator

### 2. Request Timeouts
Add to external service calls:
```python
import httpx

client = httpx.AsyncClient(timeout=30.0)
response = await client.get(url)
```

### 3. Caching for Render
Add Redis for caching expensive queries:
```bash
# In requirements.txt
redis
fastapi-cache2
```

## Monitoring & Troubleshooting

### Check Render Logs
```bash
# View real-time logs
render logs <service-name>

# Common issues:
# 1. "Connection timeout" → Increase MONGODB_URL timeouts
# 2. "Service denied" → Check IP whitelist on MongoDB Atlas
# 3. "Cold start delays" → Upgrade to paid plan, reduce startup time
```

### Health Check Endpoint
```
GET https://your-backend.onrender.com/health
Response: {"status": "ok"}
```

### Performance Metrics
Monitor in Render dashboard:
- **Response Time**: Should be <200ms after warm-up
- **Error Percentage**: Should be <1%
- **Memory Usage**: Monitor for leaks

## Deployment Checklist

- [ ] Set `APP_ENV=production` in Render
- [ ] Configure MongoDB Atlas connection string
- [ ] Add all API keys in Render environment
- [ ] Update CORS origins to your frontend domains
- [ ] Deploy backend first, then frontend
- [ ] Test health endpoint: `/health`
- [ ] Monitor first run for any errors
- [ ] Set up error alerting (optional)

## Frontend Configuration

Update frontend to use Render backend:

**Environment Variables for Frontend:**
```bash
VITE_API_BASE=https://your-backend.onrender.com/api/v1
```

## Quick Diagnostics

If still experiencing issues:

1. **Check Connection**:
   ```bash
   curl https://your-backend.onrender.com/health
   ```

2. **Test Database**:
   ```python
   # Add to routes/health.py temporarily
   @app.get("/health/db")
   def health_db(db=Depends(get_db)):
       db.command('ping')
       return {"db": "connected"}
   ```

3. **Review Scheduler Logs**:
   The scheduler logs will show in Render logs if data ingestion is failing

## Scale Up Later

When ready to scale:
- Add Redis for caching
- Split scheduler to separate service
- Use MongoDB Atlas M2+ tier
- Add CDN for frontend assets
