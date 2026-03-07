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

export type NewsArticle = {
  title: string;
  source: string;
  url: string;
  country: string;
  published_at: string;
  sentiment_score: number;
  keyword_score: number;
  war_risk_score: number;
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
};

export type MapLayerResponse = {
  updated_at: string;
  war_zones: MapLayerPoint[];
  nuclear_sites: MapLayerPoint[];
  bunkers: MapLayerPoint[];
  chokepoints: MapLayerPoint[];
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
  errors: string[];
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
  getLatestNews: () => request<NewsArticle[]>("/news/latest?limit=15"),
  getMapLayers: () => request<MapLayerResponse>("/risk/map-layers"),
  getLiveChannels: () => request<LiveChannelResponse>("/news/live-channels"),
  refreshData: () => post<RefreshResult>("/jobs/refresh"),
  newsStreamUrl: () => `${API_BASE}/news/stream?limit=15&interval_seconds=8`,
};
