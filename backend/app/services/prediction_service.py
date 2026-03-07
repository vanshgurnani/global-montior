from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import yfinance as yf

from app.core.config import settings

@dataclass
class PredictionResult:
    prob_up: float
    prob_down: float
    risk_level: str
    explanation: str
    predicted_return_5d: float
    confidence: float
    model_used: str


class PredictionService:
    def __init__(self) -> None:
        self._cls_model = None
        self._reg_model = None
        self._model_metrics: Dict[str, float] = {}
        self._trained_at: Optional[datetime] = None
        self._last_train_attempt: Optional[datetime] = None
        self._last_train_result: Dict[str, Any] = {"trained": False, "reason": "not_trained_yet"}

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _build_training_rows(self, period: str = "5y") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        symbols = ["^GSPC", "^IXIC", "^NSEI", "^FTSE", "^N225"]
        vix_hist = yf.Ticker("^VIX").history(period=period)
        if vix_hist.empty:
            return np.empty((0, 4)), np.empty((0,)), np.empty((0,))

        vix_close = vix_hist["Close"]
        x_rows = []
        y_cls = []
        y_reg = []

        for symbol in symbols:
            hist = yf.Ticker(symbol).history(period=period)
            if hist.empty or len(hist) < 90:
                continue

            close = hist["Close"]
            volume = hist["Volume"]
            common_idx = close.index.intersection(vix_close.index)
            if len(common_idx) < 90:
                continue

            close = close.loc[common_idx]
            volume = volume.loc[common_idx]
            vix = vix_close.loc[common_idx]

            for i in range(50, len(close) - 6):
                c = float(close.iloc[i])
                c_prev_7 = float(close.iloc[i - 7])
                c_fwd_5 = float(close.iloc[i + 5])
                if c <= 0 or c_prev_7 <= 0:
                    continue

                momentum_7d = ((c - c_prev_7) / c_prev_7) * 100.0
                recent_vol = float(volume.iloc[i])
                avg_prev_vol = float(volume.iloc[i - 20 : i].mean()) if float(volume.iloc[i - 20 : i].mean()) else 1.0
                volume_spike_pct = ((recent_vol - avg_prev_vol) / avg_prev_vol) * 100.0
                ma20 = float(close.iloc[i - 19 : i + 1].mean())
                ma50 = float(close.iloc[i - 49 : i + 1].mean())
                ma_gap = ((ma20 - ma50) / ma50) * 100.0 if ma50 else 0.0
                vix_now = float(vix.iloc[i])

                ret_5d = ((c_fwd_5 - c) / c) * 100.0
                x_rows.append([momentum_7d, volume_spike_pct, ma_gap, vix_now])
                y_cls.append(1 if ret_5d > 0 else 0)
                y_reg.append(ret_5d)

        if not x_rows:
            return np.empty((0, 4)), np.empty((0,)), np.empty((0,))
        return np.array(x_rows, dtype=float), np.array(y_cls, dtype=float), np.array(y_reg, dtype=float)

    def train_if_needed(self, force: bool = False) -> Dict[str, Any]:
        if self._cls_model is not None and self._reg_model is not None and not force:
            return {
                "trained": True,
                "cached": True,
                "trained_at": self._trained_at.isoformat() if self._trained_at else None,
                "metrics": self._model_metrics,
            }

        now = datetime.utcnow()
        retry_after = timedelta(minutes=max(1, int(settings.model_train_retry_minutes)))
        if (
            not force
            and self._last_train_attempt is not None
            and self._last_train_result.get("trained") is False
            and (now - self._last_train_attempt) < retry_after
        ):
            return {
                "trained": False,
                "cached": True,
                "reason": self._last_train_result.get("reason", "recent_train_failure"),
                "metrics": self._model_metrics,
            }

        x, y_cls, y_reg = self._build_training_rows()
        self._last_train_attempt = now
        if len(x) < 300:
            self._cls_model = None
            self._reg_model = None
            self._model_metrics = {"samples": float(len(x))}
            self._last_train_result = {"trained": False, "reason": "insufficient_samples"}
            return {"trained": False, "reason": "insufficient_samples", "metrics": self._model_metrics}

        try:
            from xgboost import XGBClassifier, XGBRegressor
        except Exception:
            self._cls_model = None
            self._reg_model = None
            self._model_metrics = {"samples": float(len(x))}
            self._last_train_result = {"trained": False, "reason": "xgboost_unavailable"}
            return {"trained": False, "reason": "xgboost_unavailable", "metrics": self._model_metrics}

        try:
            cls = XGBClassifier(
                n_estimators=180,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=42,
            )
            reg = XGBRegressor(
                n_estimators=220,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="reg:squarederror",
                random_state=42,
            )

            cls.fit(x, y_cls)
            reg.fit(x, y_reg)

            cls_pred = cls.predict(x)
            reg_pred = reg.predict(x)
            acc = float((cls_pred == y_cls).mean())
            mae = float(np.mean(np.abs(reg_pred - y_reg)))
        except Exception as exc:
            self._cls_model = None
            self._reg_model = None
            self._model_metrics = {"samples": float(len(x))}
            self._last_train_result = {"trained": False, "reason": "model_fit_failed"}
            return {
                "trained": False,
                "reason": "model_fit_failed",
                "error": str(exc),
                "metrics": self._model_metrics,
            }

        self._cls_model = cls
        self._reg_model = reg
        self._trained_at = datetime.utcnow()
        self._model_metrics = {
            "samples": float(len(x)),
            "train_accuracy": round(acc, 4),
            "train_mae_5d_return": round(mae, 4),
        }
        self._last_train_result = {"trained": True, "reason": "ok"}
        return {
            "trained": True,
            "cached": False,
            "trained_at": self._trained_at.isoformat(),
            "metrics": self._model_metrics,
        }

    def predict_rule_based(
        self,
        sentiment_score: float,
        keyword_risk: float,
        momentum_7d: float,
        volume_spike_pct: float,
        vix_proxy: float,
        ma20: float,
        ma50: float,
    ) -> PredictionResult:
        # Feature normalization
        m = max(-1.0, min(1.0, momentum_7d / 5.0))
        v = max(-1.0, min(1.0, volume_spike_pct / 50.0))
        vx = max(0.0, min(1.0, (vix_proxy - 12) / 30))
        s = max(-1.0, min(1.0, sentiment_score))
        k = max(0.0, min(1.0, keyword_risk))

        composite = (0.32 * m) + (0.18 * v) + (0.2 * s) - (0.2 * k) - (0.1 * vx)
        prob_up = max(0.05, min(0.95, 0.5 + composite / 2.0))
        prob_down = 1.0 - prob_up

        uncertainty = (k + vx + max(0.0, -s)) / 3.0
        if uncertainty > 0.65:
            risk_level = "High"
        elif uncertainty > 0.35:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        ma_gap = ((ma20 - ma50) / ma50) * 100.0 if ma50 else 0.0
        predicted_return_5d = (m * 2.2) + (v * 0.7) - (vx * 1.2) - (k * 1.1)
        confidence = abs(prob_up - 0.5) * 2.0

        explanation = (
            f"Momentum={momentum_7d:.2f}%, VolumeSpike={volume_spike_pct:.2f}%, "
            f"Sentiment={sentiment_score:.2f}, KeywordRisk={keyword_risk:.2f}, "
            f"VIX={vix_proxy:.2f}, MAGap={ma_gap:.2f}%"
        )

        return PredictionResult(
            prob_up=round(prob_up, 4),
            prob_down=round(prob_down, 4),
            risk_level=risk_level,
            explanation=explanation,
            predicted_return_5d=round(predicted_return_5d, 4),
            confidence=round(confidence, 4),
            model_used="rule_based",
        )

    def predict(
        self,
        sentiment_score: float,
        keyword_risk: float,
        momentum_7d: float,
        volume_spike_pct: float,
        vix_proxy: float,
        ma20: float,
        ma50: float,
    ) -> PredictionResult:
        try:
            train_result = self.train_if_needed(force=False)
        except Exception:
            train_result = {"trained": False, "reason": "train_call_failed", "metrics": {}}
        if self._cls_model is None or self._reg_model is None:
            return self.predict_rule_based(
                sentiment_score=sentiment_score,
                keyword_risk=keyword_risk,
                momentum_7d=momentum_7d,
                volume_spike_pct=volume_spike_pct,
                vix_proxy=vix_proxy,
                ma20=ma20,
                ma50=ma50,
            )

        ma_gap = ((ma20 - ma50) / ma50) * 100.0 if ma50 else 0.0
        features = np.array([[momentum_7d, volume_spike_pct, ma_gap, vix_proxy]], dtype=float)

        try:
            ml_prob_up = float(self._cls_model.predict_proba(features)[0][1])
            ml_ret_5d = float(self._reg_model.predict(features)[0])
        except Exception:
            return self.predict_rule_based(
                sentiment_score=sentiment_score,
                keyword_risk=keyword_risk,
                momentum_7d=momentum_7d,
                volume_spike_pct=volume_spike_pct,
                vix_proxy=vix_proxy,
                ma20=ma20,
                ma50=ma50,
            )

        macro_bias = (0.08 * float(sentiment_score)) - (0.12 * float(keyword_risk))
        prob_up = self._clamp(ml_prob_up + macro_bias, 0.03, 0.97)
        prob_down = 1.0 - prob_up
        pred_ret_5d = ml_ret_5d + (macro_bias * 2.0)

        confidence = self._clamp(abs(prob_up - 0.5) * 2.0, 0.0, 1.0)
        uncertainty = ((float(keyword_risk) + self._clamp((vix_proxy - 12) / 30, 0.0, 1.0) + max(0.0, -float(sentiment_score))) / 3.0)
        adjusted_uncertainty = self._clamp((uncertainty * 0.7) + ((1.0 - confidence) * 0.3), 0.0, 1.0)

        if adjusted_uncertainty > 0.66:
            risk_level = "High"
        elif adjusted_uncertainty > 0.33:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        explanation = (
            f"Model=xgboost, P(up)={prob_up:.2f}, Pred5D={pred_ret_5d:.2f}%, "
            f"Momentum={momentum_7d:.2f}%, VolumeSpike={volume_spike_pct:.2f}%, "
            f"Sentiment={sentiment_score:.2f}, KeywordRisk={keyword_risk:.2f}, "
            f"VIX={vix_proxy:.2f}, MAGap={ma_gap:.2f}%, Samples={int(train_result.get('metrics', {}).get('samples', 0))}"
        )

        return PredictionResult(
            prob_up=round(prob_up, 4),
            prob_down=round(prob_down, 4),
            risk_level=risk_level,
            explanation=explanation,
            predicted_return_5d=round(pred_ret_5d, 4),
            confidence=round(confidence, 4),
            model_used="xgboost",
        )


prediction_service = PredictionService()
