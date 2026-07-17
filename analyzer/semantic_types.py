from dataclasses import dataclass, field
from typing import List


VALID_INTENTS = {"buy", "sell", "hold", "unknown"}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, float(value)))


@dataclass
class SemanticClassification:
    author_is_beginner: float
    targets_beginners: float
    decision_dependence: float
    basic_knowledge_gap: float
    fomo_or_panic: float
    investment_intent: str
    spam_or_marketing: float
    professional_depth: float
    confidence: float
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self):
        for field_name in [
            "author_is_beginner",
            "targets_beginners",
            "decision_dependence",
            "basic_knowledge_gap",
            "spam_or_marketing",
            "professional_depth",
            "confidence",
        ]:
            setattr(self, field_name, clamp(getattr(self, field_name)))
        self.fomo_or_panic = max(-100, min(100, float(self.fomo_or_panic)))
        if self.investment_intent not in VALID_INTENTS:
            self.investment_intent = "unknown"

    def to_newbie_score(self) -> float:
        raw = (
            self.author_is_beginner * 0.45
            + self.decision_dependence * 0.25
            + self.basic_knowledge_gap * 0.20
            + max(abs(self.fomo_or_panic) - 25, 0) * 0.10
            - self.spam_or_marketing * 0.35
            - self.professional_depth * 0.25
        )
        confidence_penalty = (100 - self.confidence) * 0.10
        return round(clamp(raw - confidence_penalty), 1)

    @property
    def level(self) -> str:
        score = self.to_newbie_score()
        if self.spam_or_marketing >= 80:
            return "垃圾帖"
        if score >= 50:
            return "纯小白"
        if score >= 35:
            return "偏小白"
        if score >= 20:
            return "中间派"
        if score >= 10:
            return "偏专业"
        return "专业投资者"

    @property
    def intent(self) -> str:
        if self.investment_intent == "buy":
            return "buy"
        if self.investment_intent == "sell":
            return "sell"
        return "neutral"

    @property
    def intent_strength(self) -> float:
        if self.intent != "neutral":
            return round(clamp(abs(self.fomo_or_panic), 0, 100) / 100, 2)
        hold_pressure = max(self.decision_dependence, self.basic_knowledge_gap, abs(self.fomo_or_panic))
        return round(clamp(hold_pressure, 0, 100) / 100, 2)

    @property
    def sentiment_score(self) -> float:
        return round(max(-100, min(100, self.fomo_or_panic)) / 100, 2)

    @property
    def key_signals(self) -> List[str]:
        signals = []
        if self.author_is_beginner >= 60:
            signals.append(f"语义判断: 作者像真实小白 ({self.author_is_beginner:.0f}/100)")
        if self.targets_beginners >= 60 and self.author_is_beginner < 40:
            signals.append(f"语义判断: 内容面向小白但作者未必是小白 ({self.targets_beginners:.0f}/100)")
        if self.decision_dependence >= 60:
            signals.append(f"语义判断: 依赖他人决策 ({self.decision_dependence:.0f}/100)")
        if self.basic_knowledge_gap >= 60:
            signals.append(f"语义判断: 基础知识缺口 ({self.basic_knowledge_gap:.0f}/100)")
        if self.spam_or_marketing >= 60:
            signals.append(f"语义判断: 营销/引流风险 ({self.spam_or_marketing:.0f}/100)")
        return signals[:3] or [f"语义置信度 {self.confidence:.0f}/100"]
