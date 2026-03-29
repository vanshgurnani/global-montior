import { useMemo, useState, type ReactNode, useEffect } from "react";

import { RiskMap } from "@/components/RiskMap";
import { TrendChart } from "@/components/TrendChart";
import { ImpactTag, type ImpactLevel } from "@/components/ui/ImpactTag";
import { Modal } from "@/components/ui/Modal";
import { PredictionAccuracy, type PredictionAccuracyResponse } from "@/components/PredictionAccuracy";
import { api, type IntelligenceDashboard, type MarketSnapshot, type NewsArticle, type RiskOverview } from "@/lib/api";

type ModalState =
  | { open: true; title: string; subtitle?: string | null; body: ReactNode }
  | { open: false; title?: never; subtitle?: never; body?: never };

function to01(raw: number) {
  if (!Number.isFinite(raw)) return 0;
  let n = raw;
  if (n > 1.2 && n <= 100) n = n / 100;
  return Math.max(0, Math.min(1, n));
}

function pct01(raw: number) {
  return Math.round(to01(raw) * 100);
}

function impactFromScore(score: number): ImpactLevel {
  if (score >= 0.72) return "high";
  if (score >= 0.38) return "medium";
  return "low";
}

function marketStateLabel({
  marketRisk01,
  sentiment01,
}: {
  marketRisk01: number;
  sentiment01: number | null;
}): "Bullish" | "Bearish" | "Volatile" {
  if (marketRisk01 >= 0.66) return "Volatile";
  if (sentiment01 === null) return marketRisk01 >= 0.45 ? "Volatile" : "Bullish";
  if (sentiment01 <= -0.12) return "Bearish";
  if (sentiment01 >= 0.12) return "Bullish";
  return "Volatile";
}

function formatAsOf(value: string | null | undefined) {
  if (!value) return null;
  try {
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return value;
    return date.toLocaleString();
  } catch {
    return value;
  }
}

function TopNav({
  lastUpdatedLabel,
  refreshing,
  onRefresh,
}: {
  lastUpdatedLabel: string | null;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  return (
    <header className="topnav">
      <div className="brand">
        <div className="brand-title">Global Intelligence Monitor</div>
        <div className="brand-meta">{lastUpdatedLabel ? `Updated ${lastUpdatedLabel}` : "Live view"}</div>
      </div>
      <div className="nav-right">
        <button type="button" className="btn" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
    </header>
  );
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string | null;
  children: ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-head">
        <div className="section-title">{title}</div>
        {hint ? <div className="section-hint">{hint}</div> : null}
      </div>
      {children}
    </section>
  );
}

function CardButton({
  title,
  summary,
  indicator,
  onClick,
  children,
}: {
  title: string;
  summary?: string | null;
  indicator?: ReactNode;
  onClick: () => void;
  children?: ReactNode;
}) {
  return (
    <button type="button" className="card card-btn" onClick={onClick}>
      <div className="card-head">
        <h3 className="card-title">{title}</h3>
        {indicator ? <div className="card-indicator">{indicator}</div> : null}
      </div>
      {summary ? <p className="card-summary">{summary}</p> : null}
      {children ? <div className="card-body">{children}</div> : null}
    </button>
  );
}

export function Dashboard({
  risk,
  intel,
  news,
  snapshots,
  stocks,
  crypto,
  loading,
  refreshing,
  error,
  lastUpdatedLabel,
  onRefresh,
}: {
  risk: RiskOverview | null;
  intel: IntelligenceDashboard | null;
  news: NewsArticle[];
  snapshots: MarketSnapshot[];
  stocks: MarketSnapshot[];
  crypto: MarketSnapshot[];
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  lastUpdatedLabel: string | null;
  onRefresh: () => void;
}) {
  const [modal, setModal] = useState<ModalState>({ open: false });
  const [predictionAccuracy, setPredictionAccuracy] = useState<PredictionAccuracyResponse | null>(null);

  // Fetch prediction accuracy data
  useEffect(() => {
    api
      .getPredictionAccuracy()
      .then((data) => setPredictionAccuracy(data))
      .catch(() => setPredictionAccuracy(null));
  }, []);

  const globalRiskIndex01 = intel?.global_risk_index.global_instability_score ?? risk?.global_war_risk ?? 0;
  const globalRiskIndex = pct01(globalRiskIndex01);
  const trendLabel = intel?.geopolitical_forecast_panel.trend ?? "stable";
  const sentiment01 = typeof risk?.global_sentiment === "number" ? risk.global_sentiment : null;
  const marketRisk01 = intel?.global_risk_index.market_risk ?? 0;
  const marketState = marketStateLabel({ marketRisk01: to01(marketRisk01), sentiment01 });

  const criticalAlerts = useMemo(() => {
    const fromIntel = (intel?.breaking_event_detection.high_impact_alerts || [])
      .filter((a) => a.high_impact)
      .slice()
      .sort((a, b) => b.severity - a.severity)
      .slice(0, 3);
    if (fromIntel.length > 0) return fromIntel;

    return news
      .slice()
      .sort((a, b) => b.war_risk_score - a.war_risk_score)
      .slice(0, 3)
      .map((n) => ({
        time: n.published_at,
        title: n.title,
        country: n.country,
        category: "news",
        severity: Math.round(n.war_risk_score * 100),
        source: n.source,
        url: n.url,
        high_impact: n.war_risk_score >= 0.72,
      }));
  }, [intel?.breaking_event_detection.high_impact_alerts, news]);

  const topRiskCountries = useMemo(() => {
    const rows = intel?.country_risk_dashboard || [];
    return rows.slice().sort((a, b) => b.risk_score - a.risk_score).slice(0, 5);
  }, [intel?.country_risk_dashboard]);

  const topRegions = useMemo(() => {
    const byRegion = intel?.military_activity_monitor.by_region || {};
    return Object.entries(byRegion)
      .slice()
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([region, count]) => ({ region, count }));
  }, [intel?.military_activity_monitor.by_region]);

  const keyEvents = useMemo(() => {
    const rows = (intel?.event_timeline || []).filter((e) => e.high_impact);
    return rows.slice().sort((a, b) => b.severity - a.severity).slice(0, 2);
  }, [intel?.event_timeline]);

  const oilSignal = useMemo(() => {
    const items = intel?.commodity_risk_monitor || [];
    const oil = items.find((x) => x.commodity.toLowerCase().includes("oil")) || null;
    if (!oil) return null;
    const direction = oil.predicted_return_5d >= 0 ? "up" : "down";
    return { direction, risk: oil.risk, predicted: oil.predicted_return_5d };
  }, [intel?.commodity_risk_monitor]);

  const forecast = intel?.geopolitical_forecast_panel || null;
  const prediction = useMemo(() => {
    const next7 = forecast?.next_7d_instability ?? null;
    const next30 = forecast?.next_30d_instability ?? null;
    const trend = forecast?.trend ?? "stable";
    const risk = intel?.global_risk_index || null;
    if (next7 === null || next30 === null || !risk) return null;

    const expected =
      risk.market_risk >= 0.66 || next7 >= 0.66 ? "Volatile" : risk.war_risk >= 0.55 ? "Defensive" : "Risk-on";

    const bullets = [
      `War risk ${pct01(risk.war_risk)}%, energy risk ${pct01(risk.energy_risk)}%.`,
      oilSignal ? `Oil signal ${oilSignal.direction} (${(oilSignal.predicted * 100).toFixed(1)}% / 5D).` : null,
      `7D instability ${pct01(next7)}% → 30D ${pct01(next30)}% (${trend}).`,
    ].filter(Boolean) as string[];

    return { expected, bullets };
  }, [forecast?.next_7d_instability, forecast?.next_30d_instability, forecast?.trend, intel?.global_risk_index, oilSignal]);

  const narrative = useMemo(() => {
    const regionPhrase = topRegions.length ? topRegions.map((r) => r.region).join(" + ") : "multiple regions";
    const oilPhrase = oilSignal ? `oil signal ${oilSignal.direction}` : "energy markets mixed";
    const marketPhrase = marketState === "Volatile" ? "volatility elevated" : marketState === "Bearish" ? "risk appetite softening" : "risk appetite improving";
    const riskPhrase = intel?.global_risk_index
      ? `Global instability is ${pct01(intel.global_risk_index.global_instability_score)}% with war risk ${pct01(intel.global_risk_index.war_risk)}%.`
      : `Global risk is elevated with broad uncertainty.`;

    return [
      `Situation: Concentrated pressure from ${regionPhrase} with ${oilPhrase} and ${marketPhrase}.`,
      riskPhrase,
      `Assessment: Expect intermittent shocks; prioritize monitoring the highest-risk countries and energy-linked assets.`,
    ].join(" ");
  }, [intel?.global_risk_index, marketState, oilSignal, topRegions]);

  const topHeadlines = useMemo(() => {
    return news
      .slice()
      .sort((a, b) => b.war_risk_score - a.war_risk_score)
      .slice(0, 3)
      .map((n) => ({ ...n, impact: impactFromScore(n.war_risk_score) }));
  }, [news]);

  const openModal = (next: Omit<ModalState & { open: true }, "open">) =>
    setModal({ open: true, title: next.title, subtitle: next.subtitle ?? null, body: next.body });

  const openCountry = (country: string) => {
    openModal({
      title: `${country} — Intelligence Snapshot`,
      subtitle: "Risk score, sentiment, and near-term market impact.",
      body: (
        <div>
          <p className="status-line">Loading snapshot…</p>
        </div>
      ),
    });

    api
      .getCountryIntelligence(country)
      .then((data) => {
        openModal({
          title: `${country} — Intelligence Snapshot`,
          subtitle: "Risk score, sentiment, and near-term market impact.",
          body: (
            <div className="stack">
              {!data.snapshot ? (
                <p className="status-line">No snapshot available.</p>
              ) : (
                <>
                  <div className="kv-grid">
                    <div className="kv">
                      <div className="kv-k">Risk score</div>
                      <div className="kv-v">{pct01(data.snapshot.risk_score)}%</div>
                    </div>
                    <div className="kv">
                      <div className="kv-k">Sentiment</div>
                      <div className="kv-v">{data.snapshot.sentiment.toFixed(2)}</div>
                    </div>
                    <div className="kv">
                      <div className="kv-k">Military activity</div>
                      <div className="kv-v">{data.snapshot.military_activity}</div>
                    </div>
                    <div className="kv">
                      <div className="kv-k">Market impact</div>
                      <div className="kv-v">{pct01(data.snapshot.predicted_market_impact)}%</div>
                    </div>
                  </div>
                  <div>
                    <div className="mini-head">Relevant headlines</div>
                    <ul className="list">
                      {data.snapshot.news.slice(0, 8).map((h) => (
                        <li key={h}>
                          <span className="text-muted">{h}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          ),
        });
      })
      .catch(() => {
        openModal({
          title: `${country} — Intelligence Snapshot`,
          subtitle: "Risk score, sentiment, and near-term market impact.",
          body: <p className="status-line">Unable to load snapshot right now.</p>,
        });
      });
  };

  const pageHint = loading ? "Loading core signals…" : error ? error : null;

  return (
    <div className="shell">
      <TopNav lastUpdatedLabel={lastUpdatedLabel} refreshing={refreshing} onRefresh={onRefresh} />
      <main className="page">
        {pageHint ? <div className="banner">{pageHint}</div> : null}

        <Section title="Overview" hint="Top → Why → Explore">
          <div className="hero-grid">
            <div className="card hero-card">
              <div className="hero-kicker">Global Risk Index</div>
              <div className="hero-metric">
                <span className="hero-value">{globalRiskIndex}</span>
                <span className="hero-unit">/ 100</span>
              </div>
              <div className="hero-meta">
                <span className="pill pill-neutral">Trend: {trendLabel}</span>
                <span className={marketState === "Bearish" ? "pill pill-risk" : marketState === "Bullish" ? "pill pill-positive" : "pill pill-neutral"}>
                  Market: {marketState}
                </span>
              </div>
              <p className="card-summary">
                {intel?.breaking_event_detection.alert_banner
                  ? intel.breaking_event_detection.alert_banner
                  : "Surface view only. Open cards for evidence and deeper context."}
              </p>
            </div>

            <CardButton
              title="Market State"
              summary={prediction?.bullets?.[0] ?? "Macro regime inferred from market risk + sentiment."}
              indicator={<span className="pill pill-neutral">{marketState}</span>}
              onClick={() =>
                openModal({
                  title: "Market State",
                  subtitle: "Regime summary with supporting signals.",
                  body: (
                    <div className="stack">
                      <div className="kv-grid">
                        <div className="kv">
                          <div className="kv-k">Regime</div>
                          <div className="kv-v">{marketState}</div>
                        </div>
                        <div className="kv">
                          <div className="kv-k">Market risk</div>
                          <div className="kv-v">{pct01(marketRisk01)}%</div>
                        </div>
                        <div className="kv">
                          <div className="kv-k">Global sentiment</div>
                          <div className="kv-v">{sentiment01 === null ? "n/a" : sentiment01.toFixed(2)}</div>
                        </div>
                      </div>
                      {prediction ? (
                        <div>
                          <div className="mini-head">Rationale</div>
                          <ul className="bullets">
                            {prediction.bullets.map((b) => (
                              <li key={b}>{b}</li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <p className="status-line">No forecast panel available.</p>
                      )}
                    </div>
                  ),
                })
              }
            />

            <CardButton
              title="Critical Alerts"
              summary={criticalAlerts.length ? `${criticalAlerts.length} items require attention.` : "No high-impact alerts available."}
              indicator={<span className="pill pill-risk">Watch</span>}
              onClick={() =>
                openModal({
                  title: "Critical Alerts",
                  subtitle: "High-salience items only.",
                  body: (
                    <ul className="list list-rows">
                      {criticalAlerts.length ? (
                        criticalAlerts.map((a) => (
                          <li key={`${a.time}-${a.title}`} className="row">
                            <div className="row-main">
                              <div className="row-title">{a.title}</div>
                              <div className="row-meta">
                                <span className="text-muted">{a.country}</span>
                                <span className="dot-sep">•</span>
                                <span className="text-muted">{formatAsOf(a.time) || a.time}</span>
                              </div>
                            </div>
                            {"url" in a && a.url ? (
                              <a className="link" href={a.url} target="_blank" rel="noreferrer">
                                Source
                              </a>
                            ) : null}
                          </li>
                        ))
                      ) : (
                        <li className="row">
                          <div className="row-main">
                            <div className="row-title">No alerts</div>
                            <div className="row-meta">
                              <span className="text-muted">Nothing above the high-impact threshold.</span>
                            </div>
                          </div>
                        </li>
                      )}
                    </ul>
                  ),
                })
              }
            >
              {criticalAlerts.length ? (
                <ul className="list list-compact">
                  {criticalAlerts.slice(0, 3).map((a) => (
                    <li key={`${a.time}-${a.title}`} className="list-item">
                      <span className="truncate">{a.title}</span>
                      <span className="text-muted">{a.country}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="status-line">No items.</p>
              )}
            </CardButton>
          </div>
        </Section>

        <Section title="Why" hint="Drivers behind the situation">
          <div className="why-grid">
            <CardButton
              title="Conflict Drivers"
              summary={
                topRegions.length
                  ? `Risk concentrated across ${topRegions.map((r) => r.region).join(", ")}.`
                  : "Regional drivers unavailable."
              }
              indicator={<span className="pill pill-risk">Risk</span>}
              onClick={() =>
                openModal({
                  title: "Conflict Drivers",
                  subtitle: "Top regions contributing to risk signals.",
                  body: (
                    <div className="stack">
                      <div className="mini-head">Activity by region</div>
                      {topRegions.length ? (
                        <ul className="list list-rows">
                          {topRegions.map((r) => (
                            <li key={r.region} className="row">
                              <div className="row-main">
                                <div className="row-title">{r.region}</div>
                                <div className="row-meta">
                                  <span className="text-muted">{r.count} signals</span>
                                </div>
                              </div>
                              <div className="bar">
                                <i style={{ width: `${Math.min(100, (r.count / Math.max(1, topRegions[0].count)) * 100)}%` }} />
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="status-line">No regional breakdown available.</p>
                      )}
                      <div className="mini-head">High-impact alerts</div>
                      <ul className="list list-compact">
                        {criticalAlerts.slice(0, 5).map((a) => (
                          <li key={`${a.time}-${a.title}`} className="list-item">
                            <span className="truncate">{a.title}</span>
                            <span className="text-muted">{a.country}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ),
                })
              }
            >
              {topRegions.length ? (
                <div className="micro">
                  {topRegions.map((r) => (
                    <div key={r.region} className="micro-row">
                      <span className="text-muted">{r.region}</span>
                      <span className="mono">{r.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="status-line">No regional signal.</p>
              )}
            </CardButton>

            <CardButton
              title="Market Signals"
              summary={
                oilSignal
                  ? `Oil ${oilSignal.direction}; volatility proxy ${pct01(marketRisk01)}%; sentiment ${sentiment01 === null ? "n/a" : sentiment01.toFixed(2)}.`
                  : `Volatility proxy ${pct01(marketRisk01)}%; sentiment ${sentiment01 === null ? "n/a" : sentiment01.toFixed(2)}.`
              }
              indicator={<span className="pill pill-neutral">Signals</span>}
              onClick={() =>
                openModal({
                  title: "Market Signals",
                  subtitle: "Oil, volatility, and sentiment summary.",
                  body: (
                    <div className="stack">
                      <div className="kv-grid">
                        <div className="kv">
                          <div className="kv-k">Market risk</div>
                          <div className="kv-v">{pct01(marketRisk01)}%</div>
                        </div>
                        <div className="kv">
                          <div className="kv-k">Sentiment</div>
                          <div className="kv-v">{sentiment01 === null ? "n/a" : sentiment01.toFixed(2)}</div>
                        </div>
                        <div className="kv">
                          <div className="kv-k">Oil (5D)</div>
                          <div className="kv-v">{oilSignal ? `${(oilSignal.predicted * 100).toFixed(1)}%` : "n/a"}</div>
                        </div>
                      </div>
                      {snapshots.length ? (
                        <div>
                          <div className="mini-head">Top gain probability (sample)</div>
                          <table className="table compact-table">
                            <thead>
                              <tr>
                                <th>Symbol</th>
                                <th>Prob Up</th>
                                <th>7D Mom</th>
                              </tr>
                            </thead>
                            <tbody>
                              {snapshots
                                .slice()
                                .sort((a, b) => b.prob_up - a.prob_up)
                                .slice(0, 6)
                                .map((s) => (
                                  <tr key={s.symbol}>
                                    <td>{s.symbol}</td>
                                    <td>{pct01(s.prob_up)}%</td>
                                    <td>{s.momentum_7d.toFixed(2)}</td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="status-line">No market snapshots available.</p>
                      )}
                    </div>
                  ),
                })
              }
            />

            <CardButton
              title="Key Events"
              summary={keyEvents.length ? `${keyEvents[0].title}` : "No high-impact events detected."}
              indicator={<span className="pill pill-neutral">Events</span>}
              onClick={() =>
                openModal({
                  title: "Key Events",
                  subtitle: "High-impact events only (no long feed).",
                  body: (
                    <ul className="list list-rows">
                      {keyEvents.length ? (
                        keyEvents.map((e) => (
                          <li key={`${e.time}-${e.url}`} className="row">
                            <div className="row-main">
                              <div className="row-title">{e.title}</div>
                              <div className="row-meta">
                                <span className="text-muted">{e.country}</span>
                                <span className="dot-sep">•</span>
                                <span className="text-muted">{formatAsOf(e.time) || e.time}</span>
                              </div>
                            </div>
                            <a className="link" href={e.url} target="_blank" rel="noreferrer">
                              Source
                            </a>
                          </li>
                        ))
                      ) : (
                        <li className="row">
                          <div className="row-main">
                            <div className="row-title">No events</div>
                            <div className="row-meta">
                              <span className="text-muted">Nothing above the high-impact threshold.</span>
                            </div>
                          </div>
                        </li>
                      )}
                    </ul>
                  ),
                })
              }
            />
          </div>
        </Section>

        <Section title="Core Insight" hint="Focus areas + forward view">
          <div className="core-grid">
            <CardButton
              title="Top Risk Countries"
              summary={topRiskCountries.length ? "Highest-risk countries (max 5)." : "Country risk board unavailable."}
              indicator={<span className="pill pill-risk">Top 5</span>}
              onClick={() =>
                openModal({
                  title: "Top Risk Countries",
                  subtitle: "Click a country to open the intelligence snapshot.",
                  body: (
                    <ul className="list list-rows">
                      {topRiskCountries.length ? (
                        topRiskCountries.map((c) => (
                          <li key={c.country} className="row">
                            <button type="button" className="row-link" onClick={() => openCountry(c.country)}>
                              <div className="row-main">
                                <div className="row-title">{c.country}</div>
                                <div className="row-meta">
                                  <span className="text-muted">Risk {pct01(c.risk_score)}%</span>
                                  <span className="dot-sep">•</span>
                                  <span className="text-muted">Sent {c.sentiment.toFixed(2)}</span>
                                </div>
                              </div>
                              <span className="pill pill-risk">Inspect</span>
                            </button>
                          </li>
                        ))
                      ) : (
                        <li className="row">
                          <div className="row-main">
                            <div className="row-title">No countries</div>
                            <div className="row-meta">
                              <span className="text-muted">Waiting for risk dashboard data.</span>
                            </div>
                          </div>
                        </li>
                      )}
                    </ul>
                  ),
                })
              }
            >
              {topRiskCountries.length ? (
                <ul className="list list-compact">
                  {topRiskCountries.map((c) => (
                    <li key={c.country} className="list-item">
                      <span className="truncate">{c.country}</span>
                      <span className="text-muted">{pct01(c.risk_score)}%</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="status-line">No country risk.</p>
              )}
            </CardButton>

            <CardButton
              title="Market Prediction"
              summary={prediction ? `${prediction.expected} regime expected.` : "Forecast panel unavailable."}
              indicator={<span className="pill pill-neutral">{prediction?.expected ?? "n/a"}</span>}
              onClick={() =>
                openModal({
                  title: "Market Prediction",
                  subtitle: "Expected direction with short reasoning.",
                  body: prediction ? (
                    <div className="stack">
                      <div className="mini-head">Expected</div>
                      <div className="big-line">{prediction.expected}</div>
                      <div className="mini-head">Reasoning</div>
                      <ul className="bullets">
                        {prediction.bullets.map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className="status-line">No forecast data available.</p>
                  ),
                })
              }
            />

            <CardButton
              title="AI Narrative"
              summary="Plain-English brief (intelligence style)."
              indicator={<span className="pill pill-neutral">Brief</span>}
              onClick={() =>
                openModal({
                  title: "AI Narrative Brief",
                  subtitle: "Plain-English synthesis (surface view).",
                  body: (
                    <div className="stack">
                      <p className="narrative">{narrative}</p>
                      {intel?.ai_news_summaries?.length ? (
                        <div>
                          <div className="mini-head">Recent AI summary (evidence)</div>
                          <ul className="list">
                            {intel.ai_news_summaries.slice(0, 4).map((x) => (
                              <li key={`${x.time}-${x.title}`}>
                                <span className="text-muted">{x.briefing}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ),
                })
              }
            >
              <p className="narrative narrative-compact">{narrative}</p>
            </CardButton>
          </div>
        </Section>

        <Section title="News" hint="Only what matters">
          <div className="card">
            <ul className="list list-rows">
              {topHeadlines.length ? (
                topHeadlines.map((h) => (
                  <li key={h.url} className="row">
                    <button
                      type="button"
                      className="row-link"
                      onClick={() =>
                        openModal({
                          title: h.title,
                          subtitle: `${h.source} • ${formatAsOf(h.published_at) || h.published_at}`,
                          body: (
                            <div className="stack">
                              <div className="kv-grid">
                                <div className="kv">
                                  <div className="kv-k">Impact</div>
                                  <div className="kv-v">
                                    <ImpactTag level={h.impact} />
                                  </div>
                                </div>
                                <div className="kv">
                                  <div className="kv-k">Country</div>
                                  <div className="kv-v">{h.country}</div>
                                </div>
                                <div className="kv">
                                  <div className="kv-k">War risk</div>
                                  <div className="kv-v">{pct01(h.war_risk_score)}%</div>
                                </div>
                              </div>
                              <a className="btn btn-ghost" href={h.url} target="_blank" rel="noreferrer">
                                Open source
                              </a>
                            </div>
                          ),
                        })
                      }
                    >
                      <div className="row-main">
                        <div className="row-title">{h.title}</div>
                        <div className="row-meta">
                          <span className="text-muted">{h.source}</span>
                        </div>
                      </div>
                      <ImpactTag level={h.impact} />
                    </button>
                  </li>
                ))
              ) : (
                <li className="row">
                  <div className="row-main">
                    <div className="row-title">No headlines</div>
                    <div className="row-meta">
                      <span className="text-muted">Waiting for news feed.</span>
                    </div>
                  </div>
                </li>
              )}
            </ul>
          </div>
        </Section>

        <Section title="Prediction Before News" hint="Model accuracy tracking">
          {predictionAccuracy ? (
            <PredictionAccuracy data={predictionAccuracy} />
          ) : (
            <div className="card">
              <p className="status-line">Loading prediction accuracy data…</p>
            </div>
          )}
        </Section>

        <Section title="Explore" hint="Deeper tools (collapsed by default)">
          <div className="explore">
            <details>
              <summary>Map</summary>
              <div className="details-body">
                <RiskMap countries={risk?.high_risk_countries || []} />
              </div>
            </details>

            <details>
              <summary>Markets (tables)</summary>
              <div className="details-body">
                <div className="grid2">
                  <MarketsTable title="Stocks" rows={stocks} />
                  <MarketsTable title="Crypto" rows={crypto} />
                </div>
                {snapshots.length ? <TrendChart data={snapshots.slice(0, 10)} compact /> : null}
              </div>
            </details>

            <details>
              <summary>Full news stream</summary>
              <div className="details-body">
                <FullNewsList rows={news} />
              </div>
            </details>

            <details>
              <summary>Country drilldowns</summary>
              <div className="details-body">
                <CountrySearch intel={intel} onOpenCountry={openCountry} />
              </div>
            </details>
          </div>
        </Section>
      </main>

      <Modal
        title={modal.open ? modal.title : ""}
        subtitle={modal.open ? modal.subtitle : null}
        open={modal.open}
        onClose={() => setModal({ open: false })}
      >
        {modal.open ? modal.body : null}
      </Modal>
    </div>
  );
}

function MarketsTable({ title, rows }: { title: string; rows: MarketSnapshot[] }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows.slice(0, 20) : rows.slice(0, 5);

  return (
    <div className="card">
      <div className="card-head">
        <h3 className="card-title">{title}</h3>
        {rows.length ? (
          <button type="button" className="btn btn-ghost" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "View less" : "View more"}
          </button>
        ) : null}
      </div>
      {rows.length ? (
        <table className="table compact-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Price</th>
              <th>Prob Up</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.symbol}>
                <td>{r.symbol}</td>
                <td>{r.price.toFixed(2)}</td>
                <td>{pct01(r.prob_up)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="status-line">No data.</p>
      )}
    </div>
  );
}

function FullNewsList({ rows }: { rows: NewsArticle[] }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows.slice(0, 15) : rows.slice(0, 6);

  return (
    <div className="card">
      <div className="card-head">
        <h3 className="card-title">News stream</h3>
        {rows.length ? (
          <button type="button" className="btn btn-ghost" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "View less" : "View more"}
          </button>
        ) : null}
      </div>
      <ul className="list list-rows">
        {visible.map((n) => (
          <li key={n.url} className="row">
            <div className="row-main">
              <div className="row-title">{n.title}</div>
              <div className="row-meta">
                <span className="text-muted">{n.source}</span>
                <span className="dot-sep">•</span>
                <span className="text-muted">{formatAsOf(n.published_at) || n.published_at}</span>
              </div>
            </div>
            <a className="link" href={n.url} target="_blank" rel="noreferrer">
              Open
            </a>
          </li>
        ))}
      </ul>
      {!rows.length ? <p className="status-line">Waiting for feed…</p> : null}
    </div>
  );
}

function CountrySearch({
  intel,
  onOpenCountry,
}: {
  intel: IntelligenceDashboard | null;
  onOpenCountry: (country: string) => void;
}) {
  const [q, setQ] = useState("");

  const results = useMemo(() => {
    const rows = intel?.country_risk_dashboard || [];
    const query = q.trim().toLowerCase();
    const filtered = query ? rows.filter((r) => r.country.toLowerCase().includes(query)) : rows;
    return filtered.slice(0, 12);
  }, [intel?.country_risk_dashboard, q]);

  return (
    <div className="card">
      <div className="card-head">
        <h3 className="card-title">Country drilldown</h3>
      </div>
      <div className="input-row">
        <input
          className="input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search country…"
          aria-label="Search country"
        />
      </div>
      {results.length ? (
        <ul className="list list-rows">
          {results.map((r) => (
            <li key={r.country} className="row">
              <button type="button" className="row-link" onClick={() => onOpenCountry(r.country)}>
                <div className="row-main">
                  <div className="row-title">{r.country}</div>
                  <div className="row-meta">
                    <span className="text-muted">Risk {pct01(r.risk_score)}%</span>
                    <span className="dot-sep">•</span>
                    <span className="text-muted">Sent {r.sentiment.toFixed(2)}</span>
                  </div>
                </div>
                <span className="pill pill-neutral">Open</span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="status-line">{intel ? "No matches." : "Waiting for country dashboard…"}</p>
      )}
    </div>
  );
}
