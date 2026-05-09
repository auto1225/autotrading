from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .models import Candle, decimal_to_str


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CARDS_PATH = ROOT / "reports" / "maeuknam_strategy_cards.json"
CARD_EVIDENCE_SUPPORT_TARGET = Decimal("50")
CARD_EVIDENCE_CONFIDENCE_TARGET = Decimal("0.70")
CARD_EVIDENCE_MAX_THRESHOLD_PREMIUM = Decimal("0.09")


@dataclass(frozen=True)
class MaeuknamTechniqueSignal:
    technique_id: str
    technique_name: str
    direction: str
    score: Decimal
    entry_threshold: Decimal
    watch_threshold: Decimal
    entry_allowed: bool
    hard_blocks: tuple[str, ...]
    entry_price: Decimal
    stop_price: Decimal
    target1_price: Decimal
    target2_price: Decimal
    support_price: Decimal
    resistance_price: Decimal
    risk_pct: Decimal
    reward_risk: Decimal
    features: dict[str, Decimal]
    reason: str
    card_support_count: int = 0
    card_confidence: Decimal = Decimal("0")
    card_evidence_score: Decimal = Decimal("0")
    card_evidence_threshold_premium: Decimal = Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "techniqueId": self.technique_id,
            "techniqueName": self.technique_name,
            "direction": self.direction,
            "score": decimal_to_str(self.score),
            "entryThreshold": decimal_to_str(self.entry_threshold),
            "watchThreshold": decimal_to_str(self.watch_threshold),
            "entryAllowed": self.entry_allowed,
            "hardBlocks": list(self.hard_blocks),
            "entryPrice": decimal_to_str(self.entry_price),
            "stopPrice": decimal_to_str(self.stop_price),
            "target1Price": decimal_to_str(self.target1_price),
            "target2Price": decimal_to_str(self.target2_price),
            "supportPrice": decimal_to_str(self.support_price),
            "resistancePrice": decimal_to_str(self.resistance_price),
            "riskPct": decimal_to_str(self.risk_pct),
            "rewardRisk": decimal_to_str(self.reward_risk),
            "features": {key: decimal_to_str(value) for key, value in self.features.items()},
            "reason": self.reason,
            "cardSupportCount": self.card_support_count,
            "cardConfidence": decimal_to_str(self.card_confidence),
            "cardEvidenceScore": decimal_to_str(self.card_evidence_score),
            "cardEvidenceThresholdPremium": decimal_to_str(self.card_evidence_threshold_premium),
        }


def load_strategy_cards(path: Path = DEFAULT_CARDS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    cards = payload.get("cards", [])
    return cards if isinstance(cards, list) else []


def evaluate_maeuknam_techniques(
    candles: list[Candle],
    cards_path: Path = DEFAULT_CARDS_PATH,
    allowed_directions: tuple[str, ...] | None = None,
) -> MaeuknamTechniqueSignal | None:
    cards = load_strategy_cards(cards_path)
    if not cards or len(candles) < 30:
        return None
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    if allowed_directions is not None:
        allowed = {direction.upper() for direction in allowed_directions}
        cards = [card for card in cards if str(card.get("direction") or "LONG").upper() in allowed]
    signals = [
        evaluate_card(card, compute_market_features(ordered, str(card.get("direction") or "LONG")))
        for card in cards
    ]
    signals = [signal for signal in signals if signal is not None]
    if not signals:
        return None
    signals.sort(key=lambda signal: (signal.entry_allowed, signal.score), reverse=True)
    return signals[0]


def evaluate_card(card: dict[str, Any], features: dict[str, Decimal]) -> MaeuknamTechniqueSignal | None:
    formula = card.get("score_formula") or {}
    weights = formula.get("weights") or {}
    score = Decimal("0")
    for key, weight in weights.items():
        score += features.get(key, Decimal("0")) * Decimal(str(weight))
    score = clamp(score)
    evidence_score = card_evidence_score(card)
    evidence_threshold_premium = card_evidence_threshold_premium(evidence_score)
    entry_threshold = Decimal(str(formula.get("entry_threshold", "0.72")))
    watch_threshold = Decimal(str(formula.get("watch_threshold", "0.58")))
    hard_blocks = tuple(active_hard_blocks(features))
    entry_allowed = score >= entry_threshold and not hard_blocks
    technique_id = str(card.get("id") or "")
    risk = card.get("risk_algorithm") or {}
    max_stop = Decimal(str(risk.get("max_stop_distance_pct", "0.45")))
    if features["risk_pct_raw"] > max_stop:
        hard_blocks = tuple([*hard_blocks, f"손절폭 {decimal_to_str(features['risk_pct_raw'])}% > {decimal_to_str(max_stop)}%"])
        entry_allowed = False
    reason = (
        f"{card.get('name')}: score {decimal_to_str(score)}, "
        f"structure {decimal_to_str(features['structure_score'])}, "
        f"trigger {decimal_to_str(features['trigger_score'])}, "
        f"stop {decimal_to_str(features['stop_quality_score'])}, "
        f"RR {decimal_to_str(features['reward_risk_raw'])}"
    )
    return MaeuknamTechniqueSignal(
        technique_id=technique_id,
        technique_name=str(card.get("name") or technique_id),
        direction=str(card.get("direction") or "LONG"),
        score=score,
        entry_threshold=entry_threshold,
        watch_threshold=watch_threshold,
        entry_allowed=entry_allowed,
        hard_blocks=hard_blocks,
        entry_price=features["price"],
        stop_price=features["stop_price"],
        target1_price=features["target1_price"],
        target2_price=features["target2_price"],
        support_price=features["support_price"],
        resistance_price=features["resistance_price"],
        risk_pct=features["risk_pct_raw"],
        reward_risk=features["reward_risk_raw"],
        features={
            **{key: value for key, value in features.items() if key.endswith("_score")},
            "card_evidence_score": evidence_score,
        },
        reason=reason,
        card_support_count=int(card.get("support_count") or 0),
        card_confidence=Decimal(str(card.get("confidence") or "0")),
        card_evidence_score=evidence_score,
        card_evidence_threshold_premium=evidence_threshold_premium,
    )


def card_evidence_score(card: dict[str, Any]) -> Decimal:
    support_count = Decimal(str(card.get("support_count") or "0"))
    confidence = Decimal(str(card.get("confidence") or "0"))
    support_score = clamp(support_count / CARD_EVIDENCE_SUPPORT_TARGET)
    confidence_score = clamp(confidence / CARD_EVIDENCE_CONFIDENCE_TARGET)
    return clamp(support_score * Decimal("0.6") + confidence_score * Decimal("0.4"))


def card_evidence_threshold_premium(evidence_score: Decimal) -> Decimal:
    return (Decimal("1") - clamp(evidence_score)) * CARD_EVIDENCE_MAX_THRESHOLD_PREMIUM


def compute_market_features(ordered: list[Candle], direction: str = "LONG") -> dict[str, Decimal]:
    closes = [candle.trade_price for candle in ordered]
    highs = [candle.high_price for candle in ordered]
    lows = [candle.low_price for candle in ordered]
    price = closes[-1]
    short_side = direction.upper() == "SHORT"
    recent = ordered[-min(len(ordered), 48) :]
    support = max([candle.low_price for candle in recent if candle.low_price < price] or [min(lows[-24:])])
    resistance = min([candle.high_price for candle in recent if candle.high_price > price] or [max(highs[-24:])])
    atr = average_true_range(ordered[-min(len(ordered), 20) :])
    if atr <= 0:
        atr = price * Decimal("0.003")
    atr_pct = pct(atr, price)
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    previous_high = max(highs[-40:-5]) if len(highs) >= 45 else max(highs[:-1])
    previous_low = min(lows[-40:-5]) if len(lows) >= 45 else min(lows[:-1])
    range_span = max(recent_high - recent_low, price * Decimal("0.0001"))
    range_position = (price - recent_low) / range_span * Decimal("100")
    ema_fast = ema(closes, 8)
    ema_slow = ema(closes, 21)
    slope_pct = pct(closes[-1] - closes[-10], closes[-10]) if len(closes) >= 10 else Decimal("0")
    volume_ratio = recent_volume_ratio(ordered)

    if short_side:
        stop = resistance + atr * Decimal("0.25")
        if stop <= price:
            stop = price + max(atr, price * Decimal("0.002"))
        risk_price = max(stop - price, price * Decimal("0.0001"))
        target_floor = price * Decimal("0.0001")
        downside_target = min(support, recent_low, previous_low)
        target1 = min(downside_target, price - risk_price * Decimal("1.5"))
        target1 = max(target_floor, target1)
        target2 = min(target1, max(target_floor, price - risk_price * Decimal("2.2")))
        reward_risk = (price - target1) / risk_price if risk_price > 0 else Decimal("0")
        distance_to_resistance_pct = pct(resistance - price, price)
        breakdown_strength_pct = pct(max(previous_low - price, Decimal("0")), price)
        rejection_from_high_pct = pct(recent_high - price, recent_high)
        structure_score = clamp(Decimal("1") - min(distance_to_resistance_pct / Decimal("0.8"), Decimal("1")))
        if breakdown_strength_pct > 0:
            structure_score = max(structure_score, clamp(breakdown_strength_pct / Decimal("0.45")))
        trigger_score = clamp(
            max(
                rejection_from_high_pct / Decimal("0.8"),
                breakdown_strength_pct / Decimal("0.35"),
                (closes[-2] - price) / price * Decimal("220") if len(closes) >= 2 and price < closes[-2] else Decimal("0"),
            )
        )
        wave_score = clamp((-slope_pct + max(rejection_from_high_pct, Decimal("0"))) / Decimal("1.2"))
        regime_score = clamp(Decimal("0.5") - slope_pct / Decimal("1.5"))
        if ema_fast < ema_slow:
            regime_score = min(Decimal("1"), regime_score + Decimal("0.15"))
        chase_penalty = clamp((Decimal("22") - range_position) / Decimal("22"))
    else:
        stop = support - atr * Decimal("0.25")
        if stop <= 0 or stop >= price:
            stop = price - max(atr, price * Decimal("0.002"))
        risk_price = max(price - stop, price * Decimal("0.0001"))
        target1 = resistance if resistance > price else price + risk_price * Decimal("1.5")
        target2 = max(target1, price + risk_price * Decimal("2.2"))
        reward_risk = (target1 - price) / risk_price if risk_price > 0 else Decimal("0")
        pullback_from_high_pct = pct(recent_high - price, recent_high)
        distance_to_support_pct = pct(price - support, price)
        breakout_strength_pct = pct(max(price - previous_high, Decimal("0")), price)
        structure_score = clamp(Decimal("1") - min(distance_to_support_pct / Decimal("0.8"), Decimal("1")))
        if breakout_strength_pct > 0:
            structure_score = max(structure_score, clamp(breakout_strength_pct / Decimal("0.45")))
        trigger_score = clamp(
            max(
                pullback_from_high_pct / Decimal("0.8"),
                breakout_strength_pct / Decimal("0.35"),
                (price - closes[-2]) / price * Decimal("220") if len(closes) >= 2 and price > closes[-2] else Decimal("0"),
            )
        )
        wave_score = clamp((slope_pct + max(pullback_from_high_pct, Decimal("0"))) / Decimal("1.2"))
        regime_score = clamp(Decimal("0.5") + slope_pct / Decimal("1.5"))
        if ema_fast > ema_slow:
            regime_score = min(Decimal("1"), regime_score + Decimal("0.15"))
        chase_penalty = clamp((range_position - Decimal("78")) / Decimal("22"))

    risk_pct = pct(risk_price, price)
    stop_quality = clamp(Decimal("1") - max(risk_pct - Decimal("0.12"), Decimal("0")) / Decimal("0.45"))
    rr_score = clamp((reward_risk - Decimal("1")) / Decimal("1.4"))
    volume_score = clamp((volume_ratio - Decimal("0.8")) / Decimal("1.4"))
    chop_penalty = clamp((Decimal("0.22") - atr_pct) / Decimal("0.22"))
    return {
        "price": price,
        "support_price": support,
        "resistance_price": resistance,
        "stop_price": stop,
        "target1_price": target1,
        "target2_price": target2,
        "risk_pct_raw": risk_pct,
        "reward_risk_raw": reward_risk,
        "structure_score": structure_score,
        "trigger_score": trigger_score,
        "stop_quality_score": stop_quality,
        "reward_risk_score": rr_score,
        "wave_position_score": wave_score,
        "regime_score": regime_score,
        "volume_confirmation_score": volume_score,
        "chase_penalty": chase_penalty,
        "chop_penalty": chop_penalty,
    }


def active_hard_blocks(features: dict[str, Decimal]) -> list[str]:
    blocks: list[str] = []
    if features["risk_pct_raw"] <= 0:
        blocks.append("손절 기준 없음")
    if features["reward_risk_raw"] < Decimal("1.4"):
        blocks.append(f"기대 손익비 {decimal_to_str(features['reward_risk_raw'])} < 1.4")
    if features["chase_penalty"] >= Decimal("0.9"):
        blocks.append("목표가 근처 추격 위험")
    if features["chop_penalty"] >= Decimal("0.9"):
        blocks.append("변동성 부족")
    return blocks


def average_true_range(candles: list[Candle]) -> Decimal:
    if not candles:
        return Decimal("0")
    previous_close: Decimal | None = None
    ranges: list[Decimal] = []
    for candle in candles:
        if previous_close is None:
            ranges.append(candle.high_price - candle.low_price)
        else:
            ranges.append(max(candle.high_price - candle.low_price, abs(candle.high_price - previous_close), abs(candle.low_price - previous_close)))
        previous_close = candle.trade_price
    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def ema(values: list[Decimal], period: int) -> Decimal:
    if not values:
        return Decimal("0")
    multiplier = Decimal("2") / Decimal(period + 1)
    current = values[0]
    for value in values[1:]:
        current = (value - current) * multiplier + current
    return current


def recent_volume_ratio(candles: list[Candle]) -> Decimal:
    if len(candles) < 20:
        return Decimal("1")
    recent = sum((candle.candle_acc_trade_volume for candle in candles[-5:]), Decimal("0")) / Decimal("5")
    base = sum((candle.candle_acc_trade_volume for candle in candles[-20:-5]), Decimal("0")) / Decimal("15")
    if base <= 0:
        return Decimal("1")
    return recent / base


def pct(value: Decimal, base: Decimal) -> Decimal:
    if base <= 0:
        return Decimal("0")
    return value / base * Decimal("100")


def clamp(value: Decimal) -> Decimal:
    if value < 0:
        return Decimal("0")
    if value > 1:
        return Decimal("1")
    return value.quantize(Decimal("0.0001"))
