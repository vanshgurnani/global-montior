export type CountryRisk = {
  country: string;
  avg_war_risk: number;
  article_count: number;
};

export type RiskOverview = {
  global_sentiment: number;
  global_war_risk: number;
  risk_level: "Low" | "Medium" | "High";
  high_risk_countries: CountryRisk[];
};

export type MarketSnapshot = {
  symbol: string;
  name: string;
  asset_type?: string;
  price: number;
  momentum_7d: number;
  volume_spike_pct: number;
  ma20: number;
  ma50: number;
  vix_proxy: number;
  prob_up: number;
  prob_down: number;
  risk_level: "Low" | "Medium" | "High";
  explanation: string;
  predicted_return_5d?: number;
  confidence?: number;
  model_used?: string;
  as_of: string;
};

export type MarketCandle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
};

export type NewsArticle = {
  title: string;
  source: string;
  url: string;
  country: string;
  published_at: string;
  sentiment_score: number;
  keyword_score: number;
  war_risk_score: number;
  event_type?: string | null;
  event_severity?: string | null;
  event_confidence?: number | null;
};

export type LiveChannel = {
  name: string;
  channelId: string;
  embedUrl: string;
  watchUrl: string;
  liveVideoId?: string | null;
};

export type LiveChannelResponse = {
  used_api_key: boolean;
  channels: LiveChannel[];
};

export type MapLayerPoint = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  intensity: number;
  source: string;
  confidence?: "confirmed" | "emerging" | "low-confidence" | string;
  status?: string;
  currency?: string;
  tension_risk?: number;
  reason?: string;
};

export type MapLayerResponse = {
  updated_at: string;
  war_zones: MapLayerPoint[];
  nuclear_sites: MapLayerPoint[];
  bunkers: MapLayerPoint[];
  chokepoints: MapLayerPoint[];
  osint_overlays?: {
    fire_hotspots?: MapLayerPoint[];
    ship_density?: MapLayerPoint[];
    flight_diversions?: MapLayerPoint[];
  };
  top_currency_risks?: Array<{
    currency: string;
    score: number;
    count: number;
    reason: string;
  }>;
};

export type RefreshResult = {
  ok: boolean;
  training?: {
    trained: boolean;
    cached?: boolean;
    reason?: string;
    trained_at?: string | null;
    metrics?: Record<string, number>;
  } | null;
  news: {
    provider: string;
    sources?: string[];
    fetched: number;
    inserted: number;
    duplicates: number;
    invalid: number;
    source_counts?: Record<string, number>;
  } | null;
  markets: {
    refreshed: number;
  } | null;
  ground_truth?: {
    vix?: { fetched: number; stored: number; error?: string | null };
    world_bank?: { fetched: number; stored: number; error?: string | null };
    acled?: { fetched: number; stored: number; error?: string | null; skipped?: string };
  } | null;
  errors: string[];
};

export type ConflictTrackerItem = {
  id: string;
  name: string;
  escalation_level: string;
  war_probability: number;
  event_count: number;
  recent_events: Array<{
    title: string;
    source: string;
    time: string;
    category: string;
    severity: number;
  }>;
};

export type IntelligenceDashboard = {
  generated_at: string;
  upcoming_world_war_probability: number;
  global_conflict_tracker: ConflictTrackerItem[];
  real_time_sentiment: {
    overall_geopolitical_sentiment: number;
    country_sentiment: Array<{
      country: string;
      sentiment: number;
      war_risk: number;
      articles: number;
    }>;
  };
  breaking_event_detection: {
    high_impact_alerts: Array<{
      time: string;
      title: string;
      country: string;
      category: string;
      severity: number;
      source: string;
      url: string;
      high_impact: boolean;
    }>;
    alert_banner: string;
  };
  global_risk_index: {
    war_risk: number;
    energy_risk: number;
    market_risk: number;
    global_instability_score: number;
    risk_level: string;
  };
  market_impact_predictor: Array<{
    asset: string;
    price: number;
    predicted_return_5d: number;
    prob_down: number;
    impact_risk: number;
  }>;
  commodity_risk_monitor: Array<{
    commodity: string;
    predicted_return_5d: number;
    risk: number;
  }>;
  trade_route_chokepoints: Array<{
    name: string;
    shipping_disruption_risk: number;
    related_events: number;
    risk_level: string;
  }>;
  military_activity_monitor: {
    feeds: Array<{
      title: string;
      country: string;
      region: string;
      time: string;
      source: string;
      url: string;
      severity: number;
      category: string;
    }>;
    by_region: Record<string, number>;
  };
  nuclear_activity_monitor: {
    risk_zones: Array<{ name: string; lat: number; lon: number }>;
    events: Array<{
      title: string;
      country: string;
      time: string;
      source: string;
      url: string;
      severity: number;
      category: string;
    }>;
  };
  civil_unrest_tracker: Array<{
    title: string;
    country: string;
    time: string;
    source: string;
    url: string;
    severity: number;
    category: string;
  }>;
  live_news_wall: Array<{ name: string; watchUrl: string }>;
  ai_news_summaries: Array<{
    title: string;
    country: string;
    briefing: string;
    category: string;
    risk_level: string;
    time: string;
    source: string;
  }>;
  event_timeline: Array<{
    time: string;
    title: string;
    country: string;
    source: string;
    url: string;
    category: string;
    severity: number;
    high_impact: boolean;
  }>;
  country_risk_dashboard: Array<{
    country: string;
    risk_score: number;
    sentiment: number;
    military_activity: number;
    news: string[];
    predicted_market_impact: number;
  }>;
  predictive_geopolitics_engine: Array<{
    conflict: string;
    war_probability_7d: number;
    war_probability_30d: number;
    confidence: number;
  }>;
  event_classification_ai: Array<{ title: string; category: string; severity: number }>;
  global_sentiment_heatmap: Array<{
    country: string;
    sentiment: number;
    war_risk: number;
    articles: number;
  }>;
  geopolitical_forecast_panel: {
    next_7d_instability: number;
    next_30d_instability: number;
    trend: string;
    signal_strength: number;
  };
  multi_screen_layout: { enabled: boolean; panels: number };
  ui_mode: {
    theme: string;
    density: string;
    global_instability_score: number;
    attention_mode: boolean;
  };
};

export type CountryIntelligence = {
  country: string;
  snapshot: {
    country: string;
    risk_score: number;
    sentiment: number;
    military_activity: number;
    news: string[];
    predicted_market_impact: number;
  } | null;
};

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

export const api = {
  getRiskOverview: () => request<RiskOverview>("/risk/overview"),
  getTopGainers: () => request<MarketSnapshot[]>("/markets/top-gainers?limit=5"),
  getMarketSnapshots: () => request<MarketSnapshot[]>("/markets/snapshots"),
  getStocks: (limit: number = 25) => request<MarketSnapshot[]>(`/markets/stocks?limit=${limit}`),
  getCrypto: (limit: number = 25) => request<MarketSnapshot[]>(`/markets/crypto?limit=${limit}`),
  getMarketCandles: (symbol: string, opts?: { period?: string; interval?: string; limit?: number }) => {
    const params = new URLSearchParams({
      symbol,
      period: opts?.period || "5d",
      interval: opts?.interval || "15m",
      limit: String(opts?.limit || 80),
    });
    return request<MarketCandle[]>(`/markets/candles?${params.toString()}`);
  },
  getLatestNews: () => request<NewsArticle[]>("/news/latest?limit=15"),
  getMapLayers: (opts?: { include_osint?: boolean; overlays?: Array<"fire_hotspots" | "ship_density" | "flight_diversions"> }) => {
    const params = new URLSearchParams();
    if (opts?.include_osint) params.set("include_osint", "true");
    if (opts?.overlays && opts.overlays.length > 0) params.set("overlays", opts.overlays.join(","));
    const query = params.toString();
    return request<MapLayerResponse>(`/risk/map-layers${query ? `?${query}` : ""}`);
  },
  getLiveChannels: () => request<LiveChannelResponse>("/news/live-channels"),
  getIntelligenceDashboard: () => request<IntelligenceDashboard>("/intelligence/dashboard"),
  getPredictionAccuracy: () => request<any>("/intelligence/prediction-accuracy"),
  getCountryIntelligence: (country: string) => request<CountryIntelligence>(`/intelligence/country/${encodeURIComponent(country)}`),
  refreshData: () => post<RefreshResult>("/jobs/refresh"),
  newsStreamUrl: () => `${API_BASE}/news/stream?limit=15&interval_seconds=8`,
};
