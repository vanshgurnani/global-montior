import { useEffect, useRef, useState } from "react";

import { RiskMap } from "@/components/RiskMap";
import { TrendChart } from "@/components/TrendChart";
import {
  api,
  type CountryRisk,
  type CountryIntelligence,
  type IntelligenceDashboard,
  type LiveChannel,
  type MarketSnapshot,
  type NewsArticle,
  type RefreshResult,
  type RiskOverview,
} from "@/lib/api";

export default function App() {
  const [risk, setRisk] = useState<RiskOverview | null>(null);
  const [snapshots, setSnapshots] = useState<MarketSnapshot[]>([]);
  const [stockData, setStockData] = useState<MarketSnapshot[]>([]);
  const [cryptoData, setCryptoData] = useState<MarketSnapshot[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshResult, setRefreshResult] = useState<RefreshResult | null>(null);
  const [activeChannelIndex, setActiveChannelIndex] = useState(0);
  const [videoError, setVideoError] = useState(false);
  const [liveChannels, setLiveChannels] = useState<LiveChannel[]>([]);
  const [youtubeApiEnabled, setYoutubeApiEnabled] = useState(false);
  const [autoRotateChannels, setAutoRotateChannels] = useState(false);
  const [carouselHovered, setCarouselHovered] = useState(false);
  const [intel, setIntel] = useState<IntelligenceDashboard | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string>("");
  const [countryIntel, setCountryIntel] = useState<CountryIntelligence | null>(null);
  const [popupCountry, setPopupCountry] = useState<CountryRisk | null>(null);
  const [popupIntel, setPopupIntel] = useState<CountryIntelligence | null>(null);
  const [popupLoading, setPopupLoading] = useState(false);
  const channelRailRef = useRef<HTMLDivElement | null>(null);
  const channelItemRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  const loadDashboard = () => {
    setError(null);
    setLoading(true);
    return Promise.all([
      api.getRiskOverview(),
      api.getMarketSnapshots(),
      api.getStocks(20),
      api.getCrypto(20),
      api.getLatestNews(),
      api.getIntelligenceDashboard(),
    ])
      .then(([riskData, marketData, stocks, crypto, newsData, intelData]) => {
        setRisk(riskData);
        setSnapshots(marketData);
        setStockData(stocks);
        setCryptoData(crypto);
        setNews(newsData);
        setIntel(intelData);
        const topCountry = intelData.country_risk_dashboard?.[0]?.country || "";
        setSelectedCountry(topCountry);
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

  useEffect(() => {
    if (!autoRotateChannels || carouselHovered || liveChannels.length < 2 || document.hidden) return;
    const timer = window.setInterval(() => {
      setActiveChannelIndex((idx) => (idx + 1) % liveChannels.length);
      setVideoError(false);
    }, 12000);
    return () => {
      window.clearInterval(timer);
    };
  }, [autoRotateChannels, carouselHovered, liveChannels.length]);

  useEffect(() => {
    if (!selectedCountry) return;
    api
      .getCountryIntelligence(selectedCountry)
      .then(setCountryIntel)
      .catch(() => {
        setCountryIntel(null);
      });
  }, [selectedCountry]);

  const topGainers = [...snapshots].sort((a, b) => b.prob_up - a.prob_up).slice(0, 5);
  const currentChannel = liveChannels[activeChannelIndex] || liveChannels[0] || null;
  const baseInstability = intel?.global_risk_index.global_instability_score ?? 0;
  const scenarioCards = [
    {
      name: "De-escalation Window",
      description: "Ceasefire momentum and lower sanctions pressure.",
      instability: Math.max(0, baseInstability - 0.12),
      marketBias: "Risk-on",
    },
    {
      name: "Status Quo Tension",
      description: "Current conflict intensity persists with intermittent shocks.",
      instability: baseInstability,
      marketBias: "Range-bound",
    },
    {
      name: "Escalation Shock",
      description: "Military escalation with energy-route disruption risk.",
      instability: Math.min(1, baseInstability + 0.18),
      marketBias: "Risk-off",
    },
  ];
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

  const openHighRiskPopup = (country: CountryRisk) => {
    setPopupCountry(country);
    setPopupLoading(true);
    api
      .getCountryIntelligence(country.country)
      .then(setPopupIntel)
      .catch(() => setPopupIntel(null))
      .finally(() => setPopupLoading(false));
  };

  return (
    <main className="container dashboard-screen">
      <header className="hero">
        <div>
          <p className="eyebrow">Global Intelligence Monitor</p>
          <h1>AI Geopolitical & Market Intelligence</h1>
          <p className="subtitle">Real-time news, war signal detection, sentiment, and probabilistic market outlook.</p>
        </div>
        <div className="risk-actions">
          <div className="risk-pill">
            World War Probability: {((intel?.upcoming_world_war_probability ?? 0) * 100).toFixed(1)}%
          </div>
          <div className="risk-pill">Global Risk: {risk?.risk_level ?? "Loading"}</div>
          <button
            type="button"
            className="refresh-icon-btn"
            onClick={refreshData}
            disabled={refreshing}
            title={refreshing ? "Refreshing..." : "Refresh dashboard"}
            aria-label={refreshing ? "Refreshing dashboard" : "Refresh dashboard"}
          >
            ↻
          </button>
        </div>
      </header>

      {loading ? <p className="status-line">Loading dashboard...</p> : null}
      {error ? <p className="status-line status-error">Data load error: {error}</p> : null}
      {refreshResult ? (
        <p className="status-line">
          model_trained={String(refreshResult.training?.trained ?? false)}, samples=
          {Math.round(refreshResult.training?.metrics?.samples ?? 0)}, Refresh result: provider=
          {refreshResult.news?.provider ?? "n/a"}, sources=
          {(refreshResult.news?.sources || []).join(",") || "n/a"}, fetched={refreshResult.news?.fetched ?? 0}, inserted=
          {refreshResult.news?.inserted ?? 0}, by_source=
          {JSON.stringify(refreshResult.news?.source_counts || {})}, market_refreshed=
          {refreshResult.markets?.refreshed ?? 0}
          {refreshResult.errors.length > 0 ? `, errors=${refreshResult.errors.join(" | ")}` : ""}
        </p>
      ) : null}
      {!loading && !error && snapshots.length === 0 ? <p className="status-line">No market data available yet.</p> : null}
      {intel?.breaking_event_detection.alert_banner ? (
        <div className="alert-banner">Breaking Alert: {intel.breaking_event_detection.alert_banner}</div>
      ) : null}

      <div className="screen-grid">
        <section className="map-center map-pane">
          <RiskMap countries={risk?.high_risk_countries || []} />
        </section>

        <section className="side-pane">
          <div className="card live-channel-card">
            <h3>Live News Channels</h3>
            <div
              className="video-carousel"
              onMouseEnter={() => setCarouselHovered(true)}
              onMouseLeave={() => setCarouselHovered(false)}
            >
              <button type="button" className="video-nav" onClick={() => slideChannels("left")} aria-label="Previous channels">
                {"<"}
              </button>
              <div ref={channelRailRef} className="video-switch video-switch-rail">
                {liveChannels.map((channel, index) => (
                  <button
                    type="button"
                    key={channel.name}
                    ref={(el) => {
                      channelItemRefs.current[index] = el;
                    }}
                    className={channel.name === currentChannel?.name ? "video-chip active" : "video-chip"}
                    onClick={() => {
                      setActiveChannelIndex(index);
                      setVideoError(false);
                    }}
                  >
                    {channel.name}
                  </button>
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
            <h3>High-Risk Countries</h3>
            <ul className="list">
              {(risk?.high_risk_countries || []).map((c) => (
                <li key={c.country}>
                  <button type="button" className="country-link-btn" onClick={() => openHighRiskPopup(c)}>
                    {c.country}
                  </button>
                  <span>{(c.avg_war_risk * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          </div>

          <TrendChart data={snapshots} compact />
        </section>
      </div>

      <section className="intel-grid">
        <div className="card pane-scroll">
          <h3>Global Conflict Tracker</h3>
          <ul className="list">
            {(intel?.global_conflict_tracker || []).map((item) => (
              <li key={item.id}>
                <span>
                  {item.name}
                  <span className="mono-line">
                    {item.escalation_level} | {Math.round(item.war_probability * 100)}% war probability
                  </span>
                </span>
                <span>{item.event_count} events</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card pane-scroll">
          <h3>Global Risk Index</h3>
          <p className="status-line">
            Instability: {Math.round((intel?.global_risk_index.global_instability_score || 0) * 100)}%
            {" | "}
            {intel?.global_risk_index.risk_level || "N/A"}
          </p>
          <ul className="list">
            <li>
              <span>War Risk</span>
              <span>{Math.round((intel?.global_risk_index.war_risk || 0) * 100)}%</span>
            </li>
            <li>
              <span>Energy Risk</span>
              <span>{Math.round((intel?.global_risk_index.energy_risk || 0) * 100)}%</span>
            </li>
            <li>
              <span>Market Risk</span>
              <span>{Math.round((intel?.global_risk_index.market_risk || 0) * 100)}%</span>
            </li>
          </ul>
        </div>

        <div className="card pane-scroll">
          <h3>Market Impact Predictor</h3>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>5D Return</th>
                <th>Down Prob</th>
                <th>Impact Risk</th>
              </tr>
            </thead>
            <tbody>
              {(intel?.market_impact_predictor || []).map((row) => (
                <tr key={row.asset}>
                  <td>{row.asset}</td>
                  <td>{row.predicted_return_5d.toFixed(2)}%</td>
                  <td>{(row.prob_down * 100).toFixed(1)}%</td>
                  <td>{(row.impact_risk * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card pane-scroll">
          <h3>Stocks & Crypto Data</h3>
          <p className="map-caption">Stocks</p>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>Prob Up</th>
              </tr>
            </thead>
            <tbody>
              {stockData.slice(0, 8).map((row) => (
                <tr key={row.symbol}>
                  <td>{row.symbol}</td>
                  <td>{row.price.toFixed(2)}</td>
                  <td>{(row.prob_up * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="map-caption">Crypto</p>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>Prob Up</th>
              </tr>
            </thead>
            <tbody>
              {cryptoData.slice(0, 8).map((row) => (
                <tr key={row.symbol}>
                  <td>{row.symbol}</td>
                  <td>{row.price.toFixed(2)}</td>
                  <td>{(row.prob_up * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card pane-scroll">
          <h3>Commodity & Chokepoint Risk</h3>
          <p className="map-caption">Commodities</p>
          <ul className="list">
            {(intel?.commodity_risk_monitor || []).map((row) => (
              <li key={row.commodity}>
                <span>{row.commodity}</span>
                <span>{(row.risk * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
          <p className="map-caption">Trade Routes</p>
          <ul className="list">
            {(intel?.trade_route_chokepoints || []).map((row) => (
              <li key={row.name}>
                <span>{row.name}</span>
                <span>{(row.shipping_disruption_risk * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card pane-scroll">
          <h3>Military, Nuclear, Civil Unrest</h3>
          <p className="map-caption">Military Feed</p>
          <ul className="list">
            {(intel?.military_activity_monitor.feeds || []).slice(0, 4).map((row) => (
              <li key={`${row.time}-${row.title}`}>
                <span>{row.title}</span>
                <span>{row.region}</span>
              </li>
            ))}
          </ul>
          <p className="map-caption">Nuclear Events</p>
          <ul className="list">
            {(intel?.nuclear_activity_monitor.events || []).slice(0, 3).map((row) => (
              <li key={`${row.time}-${row.title}`}>
                <span>{row.title}</span>
                <span>{row.country}</span>
              </li>
            ))}
          </ul>
          <p className="map-caption">Civil Unrest</p>
          <ul className="list">
            {(intel?.civil_unrest_tracker || []).slice(0, 3).map((row) => (
              <li key={`${row.time}-${row.title}`}>
                <span>{row.title}</span>
                <span>{row.country}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card pane-scroll">
          <h3>AI News Summaries & Timeline</h3>
          <ul className="list">
            {(intel?.ai_news_summaries || []).slice(0, 6).map((row) => (
              <li key={`${row.time}-${row.title}`} className="news-item">
                <span>{row.briefing}</span>
                <span>{row.source}</span>
              </li>
            ))}
          </ul>
          <p className="map-caption">Recent Event Timeline</p>
          <ul className="list">
            {(intel?.event_timeline || []).slice(0, 6).map((row) => (
              <li key={`${row.time}-${row.url}`}>
                <span>{row.title}</span>
                <span>{row.category}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card pane-scroll">
          <h3>Country Risk Dashboard</h3>
          <div className="chip-list">
            {(intel?.country_risk_dashboard || []).slice(0, 10).map((row) => (
              <button
                type="button"
                key={row.country}
                className={selectedCountry === row.country ? "map-chip active" : "map-chip"}
                onClick={() => setSelectedCountry(row.country)}
              >
                {row.country}
              </button>
            ))}
          </div>
          {countryIntel?.snapshot ? (
            <div className="country-card">
              <p>Risk Score: {(countryIntel.snapshot.risk_score * 100).toFixed(1)}%</p>
              <p>Sentiment: {countryIntel.snapshot.sentiment.toFixed(2)}</p>
              <p>Military Activity: {countryIntel.snapshot.military_activity}</p>
              <p>Predicted Market Impact: {(countryIntel.snapshot.predicted_market_impact * 100).toFixed(1)}%</p>
              <ul className="list">
                {countryIntel.snapshot.news.map((headline) => (
                  <li key={headline}>
                    <span>{headline}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="status-line">Select a country to inspect intelligence snapshot.</p>
          )}
        </div>

        <div className="card pane-scroll">
          <h3>Predictive Geopolitics & Forecast</h3>
          <ul className="list">
            {(intel?.predictive_geopolitics_engine || []).map((row) => (
              <li key={row.conflict}>
                <span>{row.conflict}</span>
                <span>7D {(row.war_probability_7d * 100).toFixed(0)}% | 30D {(row.war_probability_30d * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
          <p className="status-line">
            Forecast: 7D {(intel?.geopolitical_forecast_panel.next_7d_instability || 0) * 100}% | 30D{" "}
            {(intel?.geopolitical_forecast_panel.next_30d_instability || 0) * 100}% | Trend{" "}
            {intel?.geopolitical_forecast_panel.trend || "n/a"}
          </p>
          <p className="map-caption">Live News Wall</p>
          <ul className="list">
            {(intel?.live_news_wall || []).map((row) => (
              <li key={row.name}>
                <a href={row.watchUrl} target="_blank" rel="noreferrer">
                  {row.name}
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div className="card pane-scroll">
          <h3>Scenario Simulation Cards</h3>
          <div className="scenario-grid">
            {scenarioCards.map((scenario) => (
              <div key={scenario.name} className="scenario-card">
                <h4>{scenario.name}</h4>
                <p>{scenario.description}</p>
                <p>Projected Instability: {(scenario.instability * 100).toFixed(1)}%</p>
                <p>Expected Market Regime: {scenario.marketBias}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {popupCountry ? (
        <div className="modal-overlay" role="presentation" onClick={() => setPopupCountry(null)}>
          <div className="modal-card" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>{popupCountry.country} Threat Outlook</h3>
              <button type="button" className="video-nav" onClick={() => setPopupCountry(null)} aria-label="Close">
                x
              </button>
            </div>
            <div className="popup-risk-percent">{(popupCountry.avg_war_risk * 100).toFixed(1)}% Risk</div>
            {popupLoading ? (
              <p className="status-line">Loading country outlook...</p>
            ) : popupIntel?.snapshot ? (
              <div className="country-card">
                <p>Future Market Risk: {(popupIntel.snapshot.predicted_market_impact * 100).toFixed(1)}%</p>
                <p>Sentiment: {popupIntel.snapshot.sentiment.toFixed(2)}</p>
                <p>Military Activity Signals: {popupIntel.snapshot.military_activity}</p>
                <p>Potential Threat Headlines:</p>
                <ul className="list">
                  {popupIntel.snapshot.news.map((headline) => (
                    <li key={headline}>
                      <span>{headline}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="status-line">No country intelligence snapshot available.</p>
            )}
          </div>
        </div>
      ) : null}
    </main>
  );
}
