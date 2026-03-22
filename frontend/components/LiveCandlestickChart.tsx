"use client";

import { useEffect, useMemo, useState } from "react";

import { api, type MarketCandle, type MarketSnapshot } from "@/lib/api";

const CHART_W = 760;
const CHART_H = 240;
const PAD_L = 18;
const PAD_R = 18;
const PAD_T = 14;
const PAD_B = 24;

function fmtLabel(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function LiveCandlestickChart({ snapshots }: { snapshots: MarketSnapshot[] }) {
  const symbolOptions = useMemo(
    () =>
      snapshots
        .slice()
        .sort((a, b) => b.prob_up - a.prob_up)
        .slice(0, 8),
    [snapshots]
  );
  const [symbol, setSymbol] = useState<string>(symbolOptions[0]?.symbol || "^GSPC");
  const [candles, setCandles] = useState<MarketCandle[]>([]);
  const [updatedAt, setUpdatedAt] = useState<string>("waiting");

  useEffect(() => {
    if (!symbolOptions.length) return;
    if (!symbolOptions.some((item) => item.symbol === symbol)) {
      setSymbol(symbolOptions[0].symbol);
    }
  }, [symbolOptions, symbol]);

  useEffect(() => {
    if (!symbol) return;
    const load = () => {
      api
        .getMarketCandles(symbol, { period: "5d", interval: "15m", limit: 60 })
        .then((rows) => {
          setCandles(rows);
          setUpdatedAt(new Date().toLocaleTimeString());
        })
        .catch(() => {
          setCandles([]);
        });
    };

    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, [symbol]);

  const chart = useMemo(() => {
    if (!candles.length) return null;

    const minPrice = Math.min(...candles.map((c) => c.low));
    const maxPrice = Math.max(...candles.map((c) => c.high));
    const range = Math.max(0.0001, maxPrice - minPrice);
    const innerW = CHART_W - PAD_L - PAD_R;
    const innerH = CHART_H - PAD_T - PAD_B;
    const candleW = Math.max(4, innerW / Math.max(candles.length, 1) - 3);

    const y = (price: number) => PAD_T + ((maxPrice - price) / range) * innerH;

    return {
      minPrice,
      maxPrice,
      y,
      candleW,
      points: candles.map((candle, index) => {
        const step = innerW / Math.max(candles.length, 1);
        const x = PAD_L + index * step + step / 2;
        const openY = y(candle.open);
        const closeY = y(candle.close);
        const highY = y(candle.high);
        const lowY = y(candle.low);
        const up = candle.close >= candle.open;
        return {
          ...candle,
          x,
          openY,
          closeY,
          highY,
          lowY,
          up,
          bodyY: Math.min(openY, closeY),
          bodyH: Math.max(2, Math.abs(closeY - openY)),
        };
      }),
    };
  }, [candles]);

  const latest = candles.length ? candles[candles.length - 1] : null;

  return (
    <div className="card candlestick-card">
      <div className="candlestick-head">
        <h3>Live Candlestick Chart</h3>
        <span className="map-caption">Updated {updatedAt}</span>
      </div>

      <div className="candlestick-toolbar">
        <label>
          <span className="map-caption">Symbol</span>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbolOptions.map((item) => (
              <option key={item.symbol} value={item.symbol}>
                {item.symbol} - {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {latest ? (
        <div className="candlestick-stats">
          <span>O {latest.open.toFixed(2)}</span>
          <span>H {latest.high.toFixed(2)}</span>
          <span>L {latest.low.toFixed(2)}</span>
          <span>C {latest.close.toFixed(2)}</span>
        </div>
      ) : null}

      {chart ? (
        <div className="candlestick-wrap">
          <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="candlestick-svg" role="img" aria-label={`Candlestick chart for ${symbol}`}>
            <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={CHART_H - PAD_B} className="axis-line" />
            <line x1={PAD_L} y1={CHART_H - PAD_B} x2={CHART_W - PAD_R} y2={CHART_H - PAD_B} className="axis-line" />
            {[0, 0.5, 1].map((ratio) => {
              const price = chart.maxPrice - (chart.maxPrice - chart.minPrice) * ratio;
              const yPos = chart.y(price);
              return (
                <g key={ratio}>
                  <line x1={PAD_L} y1={yPos} x2={CHART_W - PAD_R} y2={yPos} className="grid-line" />
                  <text x="0" y={yPos + 4} className="axis-text">
                    {price.toFixed(2)}
                  </text>
                </g>
              );
            })}
            {chart.points.map((point, index) => (
              <g key={`${point.time}-${index}`}>
                <line x1={point.x} y1={point.highY} x2={point.x} y2={point.lowY} className={point.up ? "wick-up" : "wick-down"} />
                <rect
                  x={point.x - chart.candleW / 2}
                  y={point.bodyY}
                  width={chart.candleW}
                  height={point.bodyH}
                  rx="1.5"
                  className={point.up ? "candle-up" : "candle-down"}
                />
              </g>
            ))}
            {chart.points
              .filter((_, index) => index % Math.max(1, Math.floor(chart.points.length / 6)) === 0)
              .map((point, index) => (
                <text key={`${point.time}-label-${index}`} x={point.x} y={CHART_H - 6} textAnchor="middle" className="axis-text">
                  {fmtLabel(point.time)}
                </text>
              ))}
          </svg>
        </div>
      ) : (
        <p className="video-help">No candle data available right now.</p>
      )}
    </div>
  );
}
