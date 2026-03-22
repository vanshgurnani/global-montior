from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import requests

from app.core.config import settings


@dataclass(frozen=True)
class EventClassification:
    event_type: str
    severity_score: float
    severity: str
    confidence: float
    rationale: str


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _severity_label(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return float(dot / (na * nb))


class EventClassificationService:
    LABELS = {
        "military_escalation": "military escalation",
        "sanctions": "sanctions",
        "diplomatic_tension": "diplomatic tension",
        "civil_unrest": "civil unrest",
    }

    RULES: dict[str, set[str]] = {
        "military_escalation": {
            "attack",
            "airstrike",
            "missile",
            "drone",
            "troops",
            "shelling",
            "invasion",
            "incursion",
            "mobilization",
            "ceasefire",
            "frontline",
            "killed",
            "wounded",
            "strike",
        },
        "sanctions": {
            "sanction",
            "embargo",
            "tariff",
            "export ban",
            "asset freeze",
            "blacklist",
            "designation",
            "secondary sanctions",
            "trade restrictions",
        },
        "diplomatic_tension": {
            "talks",
            "summit",
            "diplomat",
            "ambassador",
            "negotiation",
            "ceasefire talks",
            "dialogue",
            "warning",
            "ultimatum",
            "expel",
            "protest note",
            "border dispute",
        },
        "civil_unrest": {
            "protest",
            "riot",
            "strike",
            "unrest",
            "demonstration",
            "clash",
            "curfew",
            "police",
            "tear gas",
            "detained",
            "arrested",
        },
    }

    HIGH_IMPACT = {
        "nuclear",
        "chemical",
        "ballistic",
        "assassination",
        "coup",
        "martial law",
        "state of emergency",
        "terror attack",
        "genocide",
        "mass casualty",
        "supply shock",
    }

    def classify(self, text: str) -> EventClassification:
        normalized = (text or "").strip()
        if not normalized:
            return EventClassification(
                event_type="diplomatic_tension",
                severity_score=0.2,
                severity="low",
                confidence=0.25,
                rationale="empty_text",
            )

        if settings.use_transformer_event_classifier:
            classified = self._classify_transformer(normalized)
            if classified is not None:
                return classified

        if settings.use_openai_event_classifier and settings.openai_api_key:
            classified = self._classify_openai_embeddings(normalized)
            if classified is not None:
                return classified

        return self._classify_rules(normalized)

    @lru_cache(maxsize=1)
    def _load_zero_shot(self):
        from transformers import pipeline

        # Uses cached weights if present; if not, caller falls back safely.
        return pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    def _classify_transformer(self, text: str) -> Optional[EventClassification]:
        try:
            model = self._load_zero_shot()
            labels = list(self.LABELS.values())
            result = model(text[:512], candidate_labels=labels, multi_label=False)
            best_label = str(result["labels"][0])
            score = float(result["scores"][0])
            event_type = next((k for k, v in self.LABELS.items() if v == best_label), "diplomatic_tension")
            impact = 1.0 if any(w in text.lower() for w in self.HIGH_IMPACT) else 0.0
            severity_score = _clip01(0.55 * score + 0.45 * impact)
            return EventClassification(
                event_type=event_type,
                severity_score=round(severity_score, 4),
                severity=_severity_label(severity_score),
                confidence=round(_clip01(score), 4),
                rationale="transformer_zero_shot",
            )
        except Exception:
            return None

    def _classify_openai_embeddings(self, text: str) -> Optional[EventClassification]:
        try:
            text_vec = self._openai_embedding(text)
            proto = self._prototype_embeddings()
            sims = {k: _cosine_similarity(text_vec, v) for k, v in proto.items()}
            # Convert cosine similarities to a pseudo-probability distribution.
            # Scale by temperature-ish factor to sharpen a bit.
            exps = {k: math.exp(5.5 * float(s)) for k, s in sims.items()}
            denom = sum(exps.values()) or 1.0
            probs = {k: float(v / denom) for k, v in exps.items()}
            event_type = max(probs, key=probs.get)
            confidence = _clip01(float(probs[event_type]))
            impact = 1.0 if any(w in text.lower() for w in self.HIGH_IMPACT) else 0.0
            severity_score = _clip01(0.6 * confidence + 0.4 * impact)
            return EventClassification(
                event_type=event_type,
                severity_score=round(severity_score, 4),
                severity=_severity_label(severity_score),
                confidence=round(confidence, 4),
                rationale="openai_embeddings_prototypes",
            )
        except Exception:
            return None

    @lru_cache(maxsize=1)
    def _prototype_embeddings(self) -> dict[str, list[float]]:
        prototypes: dict[str, str] = {
            "military_escalation": (
                "Airstrikes, troop movements, missile launches, invasion, frontline clashes, mobilization."
            ),
            "sanctions": "New sanctions, embargoes, asset freezes, export bans, tariff escalation, blacklisting.",
            "diplomatic_tension": "Diplomatic talks stall, ambassadors recalled, summit warnings, border dispute rhetoric.",
            "civil_unrest": "Mass protests, riots, strikes, curfews, police clashes, detentions, demonstrations.",
        }
        return {k: self._openai_embedding(v) for k, v in prototypes.items()}

    def _openai_embedding(self, input_text: str) -> list[float]:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": settings.openai_embeddings_model, "input": input_text[:2000]}
        resp = requests.post("https://api.openai.com/v1/embeddings", json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return list(data["data"][0]["embedding"])

    def _classify_rules(self, text: str) -> EventClassification:
        t = text.lower()
        best = "diplomatic_tension"
        best_hits = 0
        best_words: list[str] = []
        for label, words in self.RULES.items():
            hits = [w for w in words if w in t]
            if len(hits) > best_hits:
                best = label
                best_hits = len(hits)
                best_words = hits

        impact_hits = [w for w in self.HIGH_IMPACT if w in t]
        base = _clip01(best_hits / 6.0)
        impact = _clip01(len(impact_hits) / 2.0)
        severity_score = _clip01(0.7 * base + 0.3 * impact)
        confidence = _clip01(0.35 + 0.11 * best_hits + 0.1 * impact)
        rationale_bits = []
        if best_words:
            rationale_bits.append(f"rule_hits={','.join(best_words[:4])}")
        if impact_hits:
            rationale_bits.append(f"impact={','.join(impact_hits[:2])}")
        rationale = "rules" + (f" ({'|'.join(rationale_bits)})" if rationale_bits else "")
        return EventClassification(
            event_type=best,
            severity_score=round(severity_score, 4),
            severity=_severity_label(severity_score),
            confidence=round(confidence, 4),
            rationale=rationale,
        )


event_classification_service = EventClassificationService()

