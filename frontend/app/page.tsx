"use client";

import { useEffect, useRef, useState } from "react";

import { RiskMap } from "@/components/RiskMap";
import { TrendChart } from "@/components/TrendChart";
import { api, type LiveChannel, type MarketSnapshot, type NewsArticle, type RefreshResult, type RiskOverview } from "@/lib/api";

export default function DashboardPage() {
  const [risk, setRisk] = useState<RiskOverview | null>(null);
  const [snapshots, setSnapshots] = useState<MarketSnapshot[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshResult, setRefreshResult] = useState<RefreshResult | null>(null);
  const [activeChannelIndex, setActiveChannelIndex] = useState(0);
  const [videoError, setVideoError] = useState(false);
  const [liveChannels, setLiveChannels] = useState<LiveChannel[]>([]);
  const [youtubeApiEnabled, setYoutubeApiEnabled] = useState(false);
  const channelRailRef = useRef<HTMLDivElement | null>(null);
  const channelItemRefs = useRef<Record<number, HTMLSpanElement | null>>({});

  const loadDashboard = () => {
    setError(null);
    setLoading(true);
    return Promise.all([api.getRiskOverview(), api.getMarketSnapshots(), api.getLatestNews()])
      .then(([riskData, marketData, newsData]) => {
        setRisk(riskData);
        setSnapshots(marketData);
        setNews(newsData);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data");
      })
      .finally(() => setLoading(false));
  };

  const refreshData = () => {
    setError(null);
    setRefreshResult(null);
    setRefreshing(true);
    api
      .refreshData()
      .then((result) => {
        setRefreshResult(result);
        return loadDashboard();
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to refresh data");
      })
      .finally(() => setRefreshing(false));
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    const stream = new EventSource(api.newsStreamUrl());
    stream.addEventListener("news", (event) => {
      try {
        const parsed = JSON.parse((event as MessageEvent).data) as { items?: NewsArticle[] };
        if (Array.isArray(parsed.items)) {
          setNews(parsed.items);
        }
      } catch {
        // no-op
      }
    });
    return () => {
      stream.close();
    };
  }, []);

  useEffect(() => {
    api
      .getLiveChannels()
      .then((result) => {
        setYoutubeApiEnabled(result.used_api_key);
        setLiveChannels(result.channels || []);
        if (result.channels && result.channels.length > 0) {
          setActiveChannelIndex(0);
        }
      })
      .catch(() => {
        // no-op
      });
  }, []);

  useEffect(() => {
    const node = channelItemRefs.current[activeChannelIndex];
    if (node) {
      node.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    }
  }, [activeChannelIndex]);

  const topGainers = [...snapshots].sort((a, b) => b.prob_up - a.prob_up).slice(0, 5);
  const currentChannel = liveChannels[activeChannelIndex] || liveChannels[0] || null;
  const slideChannels = (dir: "left" | "right") => {
    const rail = channelRailRef.current;
    if (!rail) return;
    const amount = Math.max(180, Math.floor(rail.clientWidth * 0.65));
    rail.scrollBy({ left: dir === "left" ? -amount : amount, behavior: "smooth" });
    if (liveChannels.length > 0) {
      setActiveChannelIndex((idx) =>
        dir === "left" ? (idx - 1 + liveChannels.length) % liveChannels.length : (idx + 1) % liveChannels.length
      );
      setVideoError(false);
    }
  };

  return (
    <main className="container dashboard-screen">
      <header className="hero">
        <div>
          <p className="eyebrow">Global Intelligence Monitor</p>
          <h1>AI Geopolitical & Market Intelligence</h1>
          <p className="subtitle">Real-time news, war signal detection, sentiment, and probabilistic market outlook.</p>
          <button type="button" onClick={refreshData} disabled={refreshing} style={{ marginTop: "12px" }}>
            {refreshing ? "Refreshing..." : "Refresh Data"}
          </button>
        </div>
        <div className="risk-pill">Global Risk: {risk?.risk_level ?? "Loading"}</div>
      </header>

      {loading ? <p className="status-line">Loading dashboard...</p> : null}
      {error ? <p className="status-line status-error">Data load error: {error}</p> : null}
      {refreshResult ? (
        <p className="status-line">
          model_trained={String(refreshResult.training?.trained ?? false)}, samples=
          {Math.round(refreshResult.training?.metrics?.samples ?? 0)}, 
          Refresh result: provider={refreshResult.news?.provider ?? "n/a"}, sources=
          {(refreshResult.news?.sources || []).join(",") || "n/a"}, fetched={refreshResult.news?.fetched ?? 0},
          inserted={refreshResult.news?.inserted ?? 0}, by_source=
          {JSON.stringify(refreshResult.news?.source_counts || {})}, market_refreshed=
          {refreshResult.markets?.refreshed ?? 0}
          {refreshResult.errors.length > 0 ? `, errors=${refreshResult.errors.join(" | ")}` : ""}
        </p>
      ) : null}
      {!loading && !error && snapshots.length === 0 ? <p className="status-line">No market data available yet.</p> : null}

      <div className="screen-grid">
        <section className="map-center map-pane">
          <RiskMap countries={risk?.high_risk_countries || []} />
        </section>

        <section className="side-pane">
          <div className="card pane-scroll">
            <h3>High-Risk Countries</h3>
            <ul className="list">
              {(risk?.high_risk_countries || []).map((c) => (
                <li key={c.country}>
                  <span>{c.country}</span>
                  <span>{(c.avg_war_risk * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card pane-scroll">
            <h3>Live News Stream</h3>
            <ul className="list">
              {news.slice(0, 8).map((item) => (
                <li key={item.url} className="news-item">
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                  <span>{item.source}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="bottom-pane">
          <div className="card pane-scroll">
            <h3>Top Predicted Gainers</h3>
            <table className="table compact-table">
              <thead>
                <tr>
                  <th>Index</th>
                  <th>Price</th>
                  <th>Prob Up</th>
                  <th>Pred 5D</th>
                  <th>Conf</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {topGainers.map((g) => (
                  <tr key={g.symbol}>
                    <td>{g.name}</td>
                    <td>{g.price.toFixed(2)}</td>
                    <td>{(g.prob_up * 100).toFixed(1)}%</td>
                    <td>{typeof g.predicted_return_5d === "number" ? `${g.predicted_return_5d.toFixed(2)}%` : "--"}</td>
                    <td>{typeof g.confidence === "number" ? `${(g.confidence * 100).toFixed(0)}%` : "--"}</td>
                    <td>{g.risk_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card pane-scroll">
            <h3>Live News Channels</h3>
            <div className="video-carousel">
              <button type="button" className="video-nav" onClick={() => slideChannels("left")} aria-label="Previous channels">
                {"<"}
              </button>
              <div ref={channelRailRef} className="video-switch video-switch-rail">
                {liveChannels.map((channel, index) => (
                  <span
                    key={channel.name}
                    ref={(el) => {
                      channelItemRefs.current[index] = el;
                    }}
                    className={channel.name === currentChannel?.name ? "video-chip active" : "video-chip"}
                  >
                    {channel.name}
                  </span>
                ))}
              </div>
              <button type="button" className="video-nav" onClick={() => slideChannels("right")} aria-label="Next channels">
                {">"}
              </button>
            </div>
            {currentChannel ? (
              <div className="video-frame-wrap">
                <iframe
                  key={`${currentChannel.name}-${activeChannelIndex}`}
                  title={`${currentChannel.name} live`}
                  src={currentChannel.embedUrl}
                  allow="autoplay; encrypted-media; picture-in-picture"
                  allowFullScreen
                  onError={() => setVideoError(true)}
                />
              </div>
            ) : (
              <p className="video-help">No channels available.</p>
            )}
            <p className="video-help">
              {videoError ? "Embed blocked for this channel. " : ""}
              {currentChannel ? (
                <a href={currentChannel.watchUrl} target="_blank" rel="noreferrer">
                  Open {currentChannel.name} live on YouTube
                </a>
              ) : null}
            </p>
            <p className="video-help">YouTube API mode: {youtubeApiEnabled ? "enabled" : "fallback stream lookup"}</p>
          </div>

          <TrendChart data={snapshots} compact />
        </section>
      </div>
    </main>
  );
}
