from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .models import Candle, decimal_to_str


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CARDS_PATH = ROOT / "reports" / "alex_analysis" / "alex_strategy_cards.json"
ALEX_ENTRY_THRESHOLD = Decimal("0.52")
ALEX_WATCH_THRESHOLD = Decimal("0.42")


@dataclass(frozen=True)
class AlexTechniqueSignal:
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
            "methodName": "Alex Method",
            "modelSource": "alex_method",
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
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    cards = payload.get("cards") if isinstance(payload, dict) else None
    return [item for item in cards if isinstance(item, dict)] if isinstance(cards, list) else []


def evaluate_alex_techniques(
    candles: list[Candle],
    cards_path: Path = DEFAULT_CARDS_PATH,
    allowed_directions: tuple[str, ...] | None = None,
) -> AlexTechniqueSignal | None:
    if len(candles) < 30:
        return None
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    allowed = {direction.upper() for direction in allowed_directions} if allowed_directions else {"LONG", "SHORT"}
    cards = load_strategy_cards(cards_path)
    signals = [
        evaluate_alex_direction(ordered, direction, _card_for_direction(cards, direction))
        for direction in ("LONG", "SHORT")
        if direction in allowed
    ]
    signals = [signal for signal in signals if signal is not None]
    if not signals:
        return None
    signals.sort(key=lambda signal: (signal.entry_allowed, signal.score, signal.reward_risk), reverse=True)
    return signals[0]


def evaluate_alex_direction(
    ordered: list[Candle],
    direction: str,
    card: dict[str, Any],
) -> AlexTechniqueSignal | None:
    window = ordered[-min(len(ordered), 240) :]
    latest = window[-1]
    price = latest.trade_price
    highs = [candle.high_price for candle in window]
    lows = [candle.low_price for candle in window]
    closes = [candle.trade_price for candle in window]
    range_high = max(highs)
    range_low = min(lows)
    if price <= 0 or range_high <= range_low:
        return None

    midpoint = (range_high + range_low) / Decimal("2")
    range_pos_pct = (price - range_low) / (range_high - range_low) * Decimal("100")
    atr = average_true_range(window)
    recent = window[-min(len(window), 20) :]
    previous = window[-min(len(window), 80) : -min(len(window), 5)] or window[:-5] or window
    recent_high = max(candle.high_price for candle in recent)
    recent_low = min(candle.low_price for candle in recent)
    previous_high = max(candle.high_price for candle in previous)
    previous_low = min(candle.low_price for candle in previous)
    trend_pct = pct_change(closes[-min(len(closes), 120)], price) if len(closes) > 1 else Decimal("0")
    fast_ema = ema(closes, 12)
    slow_ema = ema(closes, 36)
    pivot_score = clamp_decimal(Decimal(recent_pivot_count(window)) / Decimal("4"))

    if direction == "LONG":
        value_score = clamp_decimal((Decimal("70") - range_pos_pct) / Decimal("70"))
        trend_score = (Decimal("0.55") if trend_pct > 0 else Decimal("0")) + (Decimal("0.45") if fast_ema >= slow_ema else Decimal("0"))
        swept_liquidity = recent_low <= previous_low * Decimal("1.001") and price > previous_low
        liquidity_score = Decimal("1") if swept_liquidity else clamp_decimal((Decimal("55") - range_pos_pct) / Decimal("55"))
        trigger_score = (Decimal("0.55") if price >= closes[-2] else Decimal("0.15")) + pivot_score * Decimal("0.45")
        stop_price = min(recent_low, previous_low) - atr * Decimal("0.20")
        target1_price = midpoint if midpoint > price else recent_high
        target2_price = range_high
        support_price = recent_low
        resistance_price = range_high
    else:
        value_score = clamp_decimal((range_pos_pct - Decimal("30")) / Decimal("70"))
        trend_score = (Decimal("0.55") if trend_pct < 0 else Decimal("0")) + (Decimal("0.45") if fast_ema <= slow_ema else Decimal("0"))
        swept_liquidity = recent_high >= previous_high * Decimal("0.999") and price < previous_high
        liquidity_score = Decimal("1") if swept_liquidity else clamp_decimal((range_pos_pct - Decimal("45")) / Decimal("55"))
        trigger_score = (Decimal("0.55") if price <= closes[-2] else Decimal("0.15")) + pivot_score * Decimal("0.45")
        stop_price = max(recent_high, previous_high) + atr * Decimal("0.20")
        target1_price = midpoint if midpoint < price else recent_low
        target2_price = range_low
        support_price = range_low
        resistance_price = recent_high

    reward_target = target2_price if target2_price > 0 else target1_price
    risk_pct = risk_distance_pct(direction, price, stop_price)
    reward_risk = reward_risk_ratio(direction, price, stop_price, reward_target)
    rr_score = clamp_decimal(reward_risk / Decimal("2.0"))
    score = clamp_decimal(
        value_score * Decimal("0.24")
        + trend_score * Decimal("0.20")
        + liquidity_score * Decimal("0.20")
        + trigger_score * Decimal("0.26")
        + rr_score * Decimal("0.10")
    )
    hard_blocks = tuple(active_hard_blocks(direction, price, stop_price, reward_target))
    entry_allowed = score >= ALEX_ENTRY_THRESHOLD and not hard_blocks
    support_count = card_support_count(card)
    evidence_score = clamp_decimal(Decimal(support_count) / Decimal("8")) if support_count else Decimal("0.5")
    reason = (
        f"alex-method {direction}: 0.5 midpoint {decimal_to_str(midpoint)}, "
        f"range position {decimal_to_str(range_pos_pct)}%, value {decimal_to_str(value_score)}, "
        f"liquidity {decimal_to_str(liquidity_score)}, 4-count {decimal_to_str(pivot_score)}, "
        f"trigger {decimal_to_str(trigger_score)}, RR {decimal_to_str(reward_risk)}"
    )
    return AlexTechniqueSignal(
        technique_id=str(card.get("id") or f"alex_{direction.lower()}_value_liquidity"),
        technique_name=str(card.get("title") or f"Alex {direction} value-liquidity setup"),
        direction=direction,
        score=score,
        entry_threshold=ALEX_ENTRY_THRESHOLD,
        watch_threshold=ALEX_WATCH_THRESHOLD,
        entry_allowed=entry_allowed,
        hard_blocks=hard_blocks,
        entry_price=price,
        stop_price=stop_price,
        target1_price=target1_price,
        target2_price=target2_price,
        support_price=support_price,
        resistance_price=resistance_price,
        risk_pct=risk_pct,
        reward_risk=reward_risk,
        features={
            "midpoint": midpoint,
            "range_position_pct": range_pos_pct,
            "value_zone_score": value_score,
            "trend_score": trend_score,
            "liquidity_score": liquidity_score,
            "four_count_score": pivot_score,
            "trigger_score": trigger_score,
            "reward_risk_score": rr_score,
            "trend_pct": trend_pct,
        },
        reason=reason,
        card_support_count=support_count,
        card_confidence=evidence_score,
        card_evidence_score=evidence_score,
    )


def _card_for_direction(cards: list[dict[str, Any]], direction: str) -> dict[str, Any]:
    for card in cards:
        if str(card.get("direction") or "").upper() == direction:
            return card
    for card in cards:
        if str(card.get("direction") or "").upper() == "BOTH":
            return card
    return {
        "id": f"alex_{direction.lower()}_value_liquidity",
        "title": f"Alex {direction} value-liquidity setup",
        "direction": direction,
        "evidenceTimes": [],
    }


def active_hard_blocks(direction: str, entry: Decimal, stop: Decimal, target: Decimal) -> list[str]:
    blocks: list[str] = []
    if direction == "LONG":
        if stop >= entry:
            blocks.append("LONG stop is not below entry")
        if target <= entry:
            blocks.append("LONG target is not above entry")
    else:
        if stop <= entry:
            blocks.append("SHORT stop is not above entry")
        if target >= entry:
            blocks.append("SHORT target is not below entry")
    return blocks


def average_true_range(candles: list[Candle], period: int = 14) -> Decimal:
    if len(candles) < 2:
        return max(candles[-1].high_price - candles[-1].low_price, Decimal("0")) if candles else Decimal("0")
    ranges: list[Decimal] = []
    previous_close = candles[0].trade_price
    for candle in candles[1:]:
        true_range = max(
            candle.high_price - candle.low_price,
            abs(candle.high_price - previous_close),
            abs(candle.low_price - previous_close),
        )
        ranges.append(true_range)
        previous_close = candle.trade_price
    sample = ranges[-period:] if len(ranges) >= period else ranges
    return sum(sample, Decimal("0")) / Decimal(len(sample)) if sample else Decimal("0")


def recent_pivot_count(candles: list[Candle], lookback: int = 80, width: int = 2) -> int:
    window = candles[-min(len(candles), lookback) :]
    if len(window) < width * 2 + 1:
        return 0
    pivots = 0
    for index in range(width, len(window) - width):
        left = window[index - width : index]
        right = window[index + 1 : index + 1 + width]
        candle = window[index]
        if candle.high_price >= max(item.high_price for item in left + right):
            pivots += 1
        elif candle.low_price <= min(item.low_price for item in left + right):
            pivots += 1
    return pivots


def ema(values: list[Decimal], period: int) -> Decimal:
    if not values:
        return Decimal("0")
    alpha = Decimal("2") / Decimal(period + 1)
    result = values[0]
    for value in values[1:]:
        result = value * alpha + result * (Decimal("1") - alpha)
    return result


def pct_change(start: Decimal, end: Decimal) -> Decimal:
    if start == 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def risk_distance_pct(direction: str, entry: Decimal, stop: Decimal) -> Decimal:
    if entry <= 0:
        return Decimal("0")
    if direction == "LONG":
        return max(Decimal("0"), (entry - stop) / entry * Decimal("100"))
    return max(Decimal("0"), (stop - entry) / entry * Decimal("100"))


def reward_risk_ratio(direction: str, entry: Decimal, stop: Decimal, target: Decimal) -> Decimal:
    if direction == "LONG":
        risk = entry - stop
        reward = target - entry
    else:
        risk = stop - entry
        reward = entry - target
    if risk <= 0 or reward <= 0:
        return Decimal("0")
    return reward / risk


def card_support_count(card: dict[str, Any]) -> int:
    evidence = card.get("evidenceTimes")
    return len(evidence) if isinstance(evidence, list) else 0


def clamp_decimal(value: Decimal, minimum: Decimal = Decimal("0"), maximum: Decimal = Decimal("1")) -> Decimal:
    return max(minimum, min(maximum, value))
