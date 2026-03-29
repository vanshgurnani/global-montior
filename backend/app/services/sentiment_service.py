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
        # Neutral words (don't confuse event mentions with sentiment)
        event_words = ["war", "crisis", "sanctions", "invasion", "attack", "conflict", "tensions"]
        
        # Explicitly positive sentiment
        positives = ["peace", "deal", "growth", "stability", "recovery", "agreement", "talks", "resolution"]
        
        # Explicitly negative sentiment (market harm)
        negatives = ["collapse", "recession", "default", "bankruptcy", "crash", "plunge", "freefall"]
        
        t = text.lower()
        
        # Count positives vs negatives (not event mentions)
        neg_count = sum(1 for w in negatives if w in t)
        pos_count = sum(1 for w in positives if w in t)
        
        # Event mentions are neutral (0.0) unless paired with sentiment
        event_count = sum(1 for w in event_words if w in t)
        
        # If only event words mentioned (no sentiment), neutral
        if pos_count == 0 and neg_count == 0:
            return 0.0
        
        # Scale: More explicit sentiment words = stronger signal
        if pos_count > neg_count:
            return max(0.0, min(1.0, (pos_count - neg_count) / 5.0))
        elif neg_count > pos_count:
            return max(-1.0, min(0.0, (pos_count - neg_count) / 5.0))
        return 0.0


sentiment_service = SentimentService()
