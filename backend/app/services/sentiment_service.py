from functools import lru_cache

from app.core.config import settings


class SentimentService:
    def __init__(self) -> None:
        self._model = None

    @lru_cache(maxsize=1)
    def _load_model(self):
        from transformers import pipeline

        return pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")

    def analyze(self, text: str) -> float:
        text = (text or "").strip()
        if not text:
            return 0.0
        if not settings.use_transformer_sentiment:
            return self._fallback_score(text)

        try:
            if self._model is None:
                self._model = self._load_model()
            result = self._model(text[:512])[0]
            label = result["label"].lower()
            score = float(result["score"])
            if "positive" in label:
                return score
            if "negative" in label:
                return -score
            return 0.0
        except Exception:
            return self._fallback_score(text)

    @staticmethod
    def _fallback_score(text: str) -> float:
        negatives = ["war", "crisis", "collapse", "sanctions", "invasion", "attack"]
        positives = ["peace", "deal", "growth", "stability", "recovery"]
        t = text.lower()
        neg = sum(1 for w in negatives if w in t)
        pos = sum(1 for w in positives if w in t)
        if neg == pos:
            return 0.0
        return max(-1.0, min(1.0, (pos - neg) / 6.0))


sentiment_service = SentimentService()
