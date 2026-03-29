from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class RLDecision:
    action: str
    confidence: float
    state: str
    policy: str


class ReinforcementLearningService:
    """
    Lightweight RL-style policy scaffold.

    This is intentionally small and dependency-free so it fits the existing
    backend without forcing a gym/training stack into app startup. The service
    can later be replaced by a trained agent while keeping the same interface.
    """

    ACTIONS = ("buy", "hold", "sell")

    def _bucket_momentum(self, momentum_7d: float) -> str:
        if momentum_7d >= 3.0:
            return "bullish"
        if momentum_7d <= -3.0:
            return "bearish"
        return "neutral"

    def _bucket_risk(self, keyword_risk: float, vix_proxy: float) -> str:
        if keyword_risk >= 0.7 or vix_proxy >= 28.0:
            return "high_risk"
        if keyword_risk >= 0.4 or vix_proxy >= 20.0:
            return "medium_risk"
        return "low_risk"

    def _bucket_sentiment(self, sentiment_score: float) -> str:
        if sentiment_score >= 0.2:
            return "positive"
        if sentiment_score <= -0.2:
            return "negative"
        return "flat"

    def _state_key(self, momentum_7d: float, sentiment_score: float, keyword_risk: float, vix_proxy: float) -> str:
        return "|".join(
            [
                self._bucket_momentum(momentum_7d),
                self._bucket_sentiment(sentiment_score),
                self._bucket_risk(keyword_risk, vix_proxy),
            ]
        )

    def decide(
        self,
        sentiment_score: float,
        keyword_risk: float,
        momentum_7d: float,
        volume_spike_pct: float,
        vix_proxy: float,
        predicted_return_5d: float,
    ) -> RLDecision:
        state = self._state_key(momentum_7d, sentiment_score, keyword_risk, vix_proxy)

        q_buy = (
            (predicted_return_5d * 0.55)
            + (momentum_7d * 0.20)
            + (sentiment_score * 2.0)
            - (keyword_risk * 2.4)
            - max(0.0, vix_proxy - 18.0) * 0.08
            + max(0.0, volume_spike_pct) * 0.01
        )
        q_sell = (
            (-predicted_return_5d * 0.55)
            + max(0.0, -momentum_7d) * 0.22
            + max(0.0, -sentiment_score) * 2.0
            + (keyword_risk * 2.2)
            + max(0.0, vix_proxy - 18.0) * 0.08
        )
        q_hold = (
            0.75
            - abs(predicted_return_5d) * 0.08
            - abs(momentum_7d) * 0.03
            - abs(sentiment_score) * 0.4
            + max(0.0, 0.6 - keyword_risk) * 0.5
        )

        scores = {"buy": q_buy, "hold": q_hold, "sell": q_sell}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        action, best_score = ranked[0]
        second_score = ranked[1][1]

        margin = max(0.0, best_score - second_score)
        confidence = min(0.95, max(0.25, 0.5 + (margin / 4.0)))

        return RLDecision(
            action=action,
            confidence=round(confidence, 4),
            state=state,
            policy=settings.rl_policy_name,
        )


reinforcement_learning_service = ReinforcementLearningService()
