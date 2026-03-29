import { useEffect, useState, type ReactNode } from "react";

export interface PredictionAccuracyItem {
  asset: string;
  symbol: string;
  prediction_date: string;
  predicted_direction: "up" | "down" | "neutral";
  prediction_confidence: number;
  actual_outcome: "up" | "down" | "sideways";
  outcome_severity: "high" | "medium" | "low";
  prediction_accuracy: number;
  days_to_outcome: string;
  news_count: number;
  top_headlines: string[];
  avg_market_risk: number;
  avg_sentiment: number;
}

export interface PredictionAccuracyResponse {
  generated_at: string;
  predictions: PredictionAccuracyItem[];
  total_predictions_analyzed: number;
  average_accuracy: number;
}

function formatDate(date: string | null | undefined): string | null {
  if (!date) return null;
  try {
    const d = new Date(date);
    if (Number.isNaN(d.valueOf())) return date;
    return d.toLocaleDateString();
  } catch {
    return date;
  }
}

function getAccuracyColor(accuracy: number): string {
  if (accuracy >= 0.7) return "pill-positive";
  if (accuracy >= 0.5) return "pill-neutral";
  return "pill-risk";
}

function getDirectionArrow(predicted: string, actual: string): ReactNode {
  if (predicted === actual) return " ✓ ";
  return " ✗ ";
}

export function PredictionAccuracy({ data }: { data: PredictionAccuracyResponse }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggleExpanded = (index: number) => {
    const next = new Set(expanded);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    setExpanded(next);
  };

  if (!data.predictions || data.predictions.length === 0) {
    return (
      <div className="card">
        <p className="status-line">No prediction-vs-reality data available yet. Model is learning from early predictions.</p>
      </div>
    );
  }

  const avgAccuracy = Math.round(data.average_accuracy * 100);

  return (
    <div className="stack">
      <div className="kv-grid">
        <div className="kv">
          <div className="kv-k">Total predictions analyzed</div>
          <div className="kv-v">{data.total_predictions_analyzed}</div>
        </div>
        <div className="kv">
          <div className="kv-k">Average accuracy</div>
          <div className="kv-v">{avgAccuracy}%</div>
        </div>
        <div className="kv">
          <div className="kv-k">Updated</div>
          <div className="kv-v">{formatDate(data.generated_at)}</div>
        </div>
      </div>

      <div className="card">
        <ul className="list list-rows">
          {data.predictions.map((pred, idx) => (
            <li key={`${pred.symbol}-${pred.prediction_date}`}>
              <button
                type="button"
                className="row-link"
                onClick={() => toggleExpanded(idx)}
              >
                <div className="row-main">
                  <div className="row-title">
                    <strong>{pred.asset}</strong>
                    <span className="text-muted"> {pred.predicted_direction.toUpperCase()}</span>
                    {getDirectionArrow(pred.predicted_direction, pred.actual_outcome)}
                    <span className="text-muted">{pred.actual_outcome.toUpperCase()}</span>
                  </div>
                  <div className="row-meta">
                    <span className="text-muted">
                      Predicted: {formatDate(pred.prediction_date)} • 
                      Outcome ({pred.outcome_severity}): {formatDate(pred.days_to_outcome)}
                    </span>
                  </div>
                </div>
                <span className={`pill ${getAccuracyColor(pred.prediction_accuracy)}`}>
                  {Math.round(pred.prediction_accuracy * 100)}% accurate
                </span>
              </button>

              {expanded.has(idx) && (
                <div style={{ padding: "1rem", borderTop: "1px solid var(--color-border)" }}>
                  <div className="kv-grid">
                    <div className="kv">
                      <div className="kv-k">Prediction confidence</div>
                      <div className="kv-v">{Math.round(pred.prediction_confidence * 100)}%</div>
                    </div>
                    <div className="kv">
                      <div className="kv-k">Market risk in news</div>
                      <div className="kv-v">{Math.round(pred.avg_market_risk * 100)}%</div>
                    </div>
                    <div className="kv">
                      <div className="kv-k">Average sentiment</div>
                      <div className="kv-v">{pred.avg_sentiment.toFixed(2)}</div>
                    </div>
                    <div className="kv">
                      <div className="kv-k">Related news articles</div>
                      <div className="kv-v">{pred.news_count}</div>
                    </div>
                  </div>

                  {pred.top_headlines.length > 0 && (
                    <div style={{ marginTop: "1rem" }}>
                      <div className="mini-head">Top headlines</div>
                      <ul className="list" style={{ fontSize: "14px" }}>
                        {pred.top_headlines.map((headline) => (
                          <li key={headline}>
                            <span className="text-muted">{headline}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
