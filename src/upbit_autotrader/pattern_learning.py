from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
import json

from .config import TradingSettings
from .models import Candle, decimal_to_str
from .strategy import make_strategy_by_name


MODEL_VERSION = 2
ALL_STRATEGIES = "__all__"
MAX_STORED_OBSERVATIONS = 1000
MAX_BROKEN_PROFIT_PATTERNS = 200
FEATURE_KEYS = (
    "trend1Pct",
    "trend3Pct",
    "trend12Pct",
    "trend36Pct",
    "volatility12Pct",
    "drawdown36Pct",
    "volumeRatio20",
    "rangePosition36Pct",
    "candleBodyPct",
)
FEATURE_SCALES = {
    "trend1Pct": Decimal("2"),
    "trend3Pct": Decimal("4"),
    "trend12Pct": Decimal("10"),
    "trend36Pct": Decimal("20"),
    "volatility12Pct": Decimal("10"),
    "drawdown36Pct": Decimal("20"),
    "volumeRatio20": Decimal("2"),
    "rangePosition36Pct": Decimal("100"),
    "candleBodyPct": Decimal("3"),
}
LOSS_BLOCK_THRESHOLD = Decimal("0.72")
LOSS_EXIT_THRESHOLD = Decimal("0.82")
PROFIT_CONFIRM_THRESHOLD = Decimal("0.52")
PROFIT_BREAK_THRESHOLD = Decimal("0.68")


@dataclass(frozen=True)
class PatternFeatures:
    trend_1_pct: Decimal
    trend_3_pct: Decimal
    trend_12_pct: Decimal
    trend_36_pct: Decimal
    volatility_12_pct: Decimal
    drawdown_36_pct: Decimal
    volume_ratio_20: Decimal
    range_position_36_pct: Decimal
    candle_body_pct: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "trend1Pct": decimal_to_str(self.trend_1_pct),
            "trend3Pct": decimal_to_str(self.trend_3_pct),
            "trend12Pct": decimal_to_str(self.trend_12_pct),
            "trend36Pct": decimal_to_str(self.trend_36_pct),
            "volatility12Pct": decimal_to_str(self.volatility_12_pct),
            "drawdown36Pct": decimal_to_str(self.drawdown_36_pct),
            "volumeRatio20": decimal_to_str(self.volume_ratio_20),
            "rangePosition36Pct": decimal_to_str(self.range_position_36_pct),
            "candleBodyPct": decimal_to_str(self.candle_body_pct),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PatternFeatures":
        return cls(
            trend_1_pct=d(payload.get("trend1Pct")),
            trend_3_pct=d(payload.get("trend3Pct")),
            trend_12_pct=d(payload.get("trend12Pct")),
            trend_36_pct=d(payload.get("trend36Pct")),
            volatility_12_pct=d(payload.get("volatility12Pct")),
            drawdown_36_pct=d(payload.get("drawdown36Pct")),
            volume_ratio_20=d(payload.get("volumeRatio20")),
            range_position_36_pct=d(payload.get("rangePosition36Pct")),
            candle_body_pct=d(payload.get("candleBodyPct")),
        )

    def vector(self) -> dict[str, Decimal]:
        return {key: d(self.to_dict()[key]) for key in FEATURE_KEYS}


@dataclass(frozen=True)
class PatternObservation:
    market: str
    strategy: str
    entry_time: str
    exit_time: str
    entry_price: Decimal
    exit_price: Decimal
    net_return_pct: Decimal
    outcome: str
    features: PatternFeatures

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "strategy": self.strategy,
            "entryTime": self.entry_time,
            "exitTime": self.exit_time,
            "entryPrice": decimal_to_str(self.entry_price),
            "exitPrice": decimal_to_str(self.exit_price),
            "netReturnPct": decimal_to_str(self.net_return_pct),
            "outcome": self.outcome,
            "features": self.features.to_dict(),
        }


@dataclass(frozen=True)
class PatternScore:
    profit_similarity: Decimal = Decimal("0")
    loss_similarity: Decimal = Decimal("0")
    broken_profit_similarity: Decimal = Decimal("0")
    adjustment: Decimal = Decimal("0")
    blocked: bool = False
    exit_now: bool = False
    reason: str = "no-pattern-model"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profitSimilarity": decimal_to_str(self.profit_similarity),
            "lossSimilarity": decimal_to_str(self.loss_similarity),
            "brokenProfitSimilarity": decimal_to_str(self.broken_profit_similarity),
            "adjustment": decimal_to_str(self.adjustment),
            "blocked": self.blocked,
            "exitNow": self.exit_now,
            "reason": self.reason,
        }


def d(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def pattern_model_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "pattern_model.json"


def load_pattern_model(settings: TradingSettings) -> dict[str, Any]:
    path = pattern_model_path(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_pattern_model(settings: TradingSettings, model: dict[str, Any]) -> Path:
    path = pattern_model_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def feature_snapshot(candles: Iterable[Candle]) -> PatternFeatures:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    if not ordered:
        zero = Decimal("0")
        return PatternFeatures(zero, zero, zero, zero, zero, zero, Decimal("1"), Decimal("50"), zero)

    latest = ordered[-1]
    return PatternFeatures(
        trend_1_pct=trend_pct(ordered, 1),
        trend_3_pct=trend_pct(ordered, 3),
        trend_12_pct=trend_pct(ordered, 12),
        trend_36_pct=trend_pct(ordered, 36),
        volatility_12_pct=volatility_pct(ordered, 12),
        drawdown_36_pct=drawdown_pct(ordered, 36),
        volume_ratio_20=volume_ratio(ordered, 20),
        range_position_36_pct=range_position_pct(ordered, 36),
        candle_body_pct=price_change_pct(latest.opening_price, latest.trade_price),
    )


def trend_pct(candles: list[Candle], window: int) -> Decimal:
    if len(candles) < 2:
        return Decimal("0")
    start_index = max(0, len(candles) - window - 1)
    return price_change_pct(candles[start_index].trade_price, candles[-1].trade_price)


def volatility_pct(candles: list[Candle], window: int) -> Decimal:
    subset = candles[-window:] if len(candles) >= window else candles
    ranges = [
        (candle.high_price - candle.low_price) / candle.trade_price * Decimal("100")
        for candle in subset
        if candle.trade_price > 0
    ]
    if not ranges:
        return Decimal("0")
    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def drawdown_pct(candles: list[Candle], window: int) -> Decimal:
    subset = candles[-window:] if len(candles) >= window else candles
    if not subset:
        return Decimal("0")
    recent_high = max(candle.high_price for candle in subset)
    if recent_high <= 0:
        return Decimal("0")
    return (candles[-1].trade_price - recent_high) / recent_high * Decimal("100")


def volume_ratio(candles: list[Candle], window: int) -> Decimal:
    if len(candles) < 2:
        return Decimal("1")
    previous = candles[max(0, len(candles) - window - 1) : -1]
    if not previous:
        return Decimal("1")
    average = sum((candle.candle_acc_trade_price for candle in previous), Decimal("0")) / Decimal(len(previous))
    if average <= 0:
        return Decimal("1")
    return candles[-1].candle_acc_trade_price / average


def range_position_pct(candles: list[Candle], window: int) -> Decimal:
    subset = candles[-window:] if len(candles) >= window else candles
    if not subset:
        return Decimal("50")
    high = max(candle.high_price for candle in subset)
    low = min(candle.low_price for candle in subset)
    if high <= low:
        return Decimal("50")
    return (candles[-1].trade_price - low) / (high - low) * Decimal("100")


def price_change_pct(start: Decimal, end: Decimal) -> Decimal:
    if start <= 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def build_pattern_model(observations: Iterable[PatternObservation]) -> dict[str, Any]:
    rows = list(observations)
    prototypes = []
    for strategy in sorted({row.strategy for row in rows} | ({ALL_STRATEGIES} if rows else set())):
        strategy_rows = rows if strategy == ALL_STRATEGIES else [row for row in rows if row.strategy == strategy]
        for outcome in ("profit", "loss"):
            outcome_rows = [row for row in strategy_rows if row.outcome == outcome]
            if not outcome_rows:
                continue
            prototypes.append(make_prototype(strategy, outcome, outcome_rows))

    profit_rows = [row for row in rows if row.outcome == "profit"]
    loss_rows = [row for row in rows if row.outcome == "loss"]
    return {
        "version": MODEL_VERSION,
        "observationCount": len(rows),
        "profitCount": len(profit_rows),
        "lossCount": len(loss_rows),
        "averageProfitPct": decimal_to_str(average_return(profit_rows)),
        "averageLossPct": decimal_to_str(average_return(loss_rows)),
        "lossBlockThreshold": decimal_to_str(LOSS_BLOCK_THRESHOLD),
        "lossExitThreshold": decimal_to_str(LOSS_EXIT_THRESHOLD),
        "profitConfirmThreshold": decimal_to_str(PROFIT_CONFIRM_THRESHOLD),
        "featureKeys": list(FEATURE_KEYS),
        "prototypes": prototypes,
        "observations": [row.to_dict() for row in rows[-MAX_STORED_OBSERVATIONS:]],
        "brokenProfitPatterns": [],
        "openEntries": {},
        "lossStreaks": empty_loss_streaks(),
    }


def make_prototype(strategy: str, outcome: str, rows: list[PatternObservation]) -> dict[str, Any]:
    averaged = {}
    for key in FEATURE_KEYS:
        averaged[key] = decimal_to_str(sum((row.features.vector()[key] for row in rows), Decimal("0")) / Decimal(len(rows)))
    return {
        "strategy": strategy,
        "outcome": outcome,
        "sampleCount": len(rows),
        "averageReturnPct": decimal_to_str(average_return(rows)),
        "features": averaged,
    }


def average_return(rows: list[PatternObservation]) -> Decimal:
    if not rows:
        return Decimal("0")
    return sum((row.net_return_pct for row in rows), Decimal("0")) / Decimal(len(rows))


def empty_loss_streaks() -> dict[str, Any]:
    return {
        "globalConsecutiveLosses": 0,
        "globalLastLossAt": "",
        "markets": {},
    }


def record_pattern_entry(
    settings: TradingSettings,
    model: dict[str, Any] | None,
    market: str,
    strategy: str,
    entry_price: Decimal,
    features: PatternFeatures | dict[str, Any],
    entry_time: str | None = None,
    amount_krw: Decimal | None = None,
) -> dict[str, Any]:
    next_model = normalize_pattern_model(model)
    if entry_price <= 0:
        return next_model
    feature_payload = features.to_dict() if isinstance(features, PatternFeatures) else dict(features)
    open_entries = next_model.setdefault("openEntries", {})
    if not isinstance(open_entries, dict):
        open_entries = {}
        next_model["openEntries"] = open_entries

    existing = open_entries.get(market)
    entry_weight = amount_krw if amount_krw is not None and amount_krw > 0 else Decimal("1")
    if isinstance(existing, dict):
        old_weight = d(existing.get("weightKrw")) or Decimal("1")
        total_weight = old_weight + entry_weight
        old_price = d(existing.get("entryPrice"))
        entry_price = weighted_average(old_price, old_weight, entry_price, entry_weight)
        feature_payload = merge_feature_payloads(existing.get("features"), old_weight, feature_payload, entry_weight)
        entry_weight = total_weight

    open_entries[market] = {
        "market": market,
        "strategy": strategy or ALL_STRATEGIES,
        "entryTime": entry_time or now_iso(),
        "entryPrice": decimal_to_str(entry_price),
        "weightKrw": decimal_to_str(entry_weight),
        "features": feature_payload,
    }
    save_pattern_model(settings, next_model)
    return next_model


def record_pattern_exit(
    settings: TradingSettings,
    model: dict[str, Any] | None,
    market: str,
    exit_price: Decimal,
    fee_rate: Decimal,
    exit_time: str | None = None,
) -> tuple[dict[str, Any], PatternObservation | None]:
    next_model = normalize_pattern_model(model)
    open_entries = next_model.setdefault("openEntries", {})
    if not isinstance(open_entries, dict):
        open_entries = {}
        next_model["openEntries"] = open_entries
    open_entry = open_entries.pop(market, None)
    if not isinstance(open_entry, dict) or exit_price <= 0:
        save_pattern_model(settings, next_model)
        return next_model, None

    entry_features = open_entry.get("features")
    if isinstance(entry_features, dict):
        open_entry = dict(open_entry)
        open_entry["features"] = PatternFeatures.from_dict(entry_features)
    observation = close_observation(
        {
            "market": market,
            "strategy": str(open_entry.get("strategy") or ALL_STRATEGIES),
            "entryTime": str(open_entry.get("entryTime") or ""),
            "entryPrice": d(open_entry.get("entryPrice")),
            "features": open_entry.get("features"),
        },
        SyntheticExitCandle(exit_price, exit_time or now_iso()),
        fee_rate,
    )
    next_model = update_pattern_model_with_observation(next_model, observation)
    save_pattern_model(settings, next_model)
    return next_model, observation


def normalize_pattern_model(model: dict[str, Any] | None) -> dict[str, Any]:
    next_model = dict(model or {})
    next_model.setdefault("version", MODEL_VERSION)
    next_model.setdefault("observationCount", 0)
    next_model.setdefault("profitCount", 0)
    next_model.setdefault("lossCount", 0)
    next_model.setdefault("averageProfitPct", "0")
    next_model.setdefault("averageLossPct", "0")
    next_model.setdefault("lossBlockThreshold", decimal_to_str(LOSS_BLOCK_THRESHOLD))
    next_model.setdefault("lossExitThreshold", decimal_to_str(LOSS_EXIT_THRESHOLD))
    next_model.setdefault("profitConfirmThreshold", decimal_to_str(PROFIT_CONFIRM_THRESHOLD))
    next_model.setdefault("featureKeys", list(FEATURE_KEYS))
    next_model.setdefault("prototypes", [])
    next_model.setdefault("observations", [])
    next_model.setdefault("brokenProfitPatterns", [])
    next_model.setdefault("openEntries", {})
    next_model.setdefault("lossStreaks", empty_loss_streaks())
    return next_model


def update_pattern_model_with_observation(
    model: dict[str, Any],
    observation: PatternObservation,
) -> dict[str, Any]:
    next_model = normalize_pattern_model(model)
    outcome = observation.outcome
    if outcome not in {"profit", "loss"}:
        outcome = "profit" if observation.net_return_pct > 0 else "loss"

    next_model["observationCount"] = int(next_model.get("observationCount") or 0) + 1
    if outcome == "profit":
        next_model["profitCount"] = int(next_model.get("profitCount") or 0) + 1
        next_model["averageProfitPct"] = decimal_to_str(
            update_average(d(next_model.get("averageProfitPct")), next_model["profitCount"], observation.net_return_pct)
        )
    else:
        next_model["lossCount"] = int(next_model.get("lossCount") or 0) + 1
        next_model["averageLossPct"] = decimal_to_str(
            update_average(d(next_model.get("averageLossPct")), next_model["lossCount"], observation.net_return_pct)
        )
        profit_similarity = best_similarity(next_model, observation.strategy, "profit", observation.features)
        if profit_similarity >= PROFIT_BREAK_THRESHOLD:
            record_broken_profit_pattern(next_model, observation, profit_similarity)

    prototypes = next_model.setdefault("prototypes", [])
    if not isinstance(prototypes, list):
        prototypes = []
        next_model["prototypes"] = prototypes
    for strategy in (observation.strategy, ALL_STRATEGIES):
        merge_observation_into_prototype(prototypes, strategy, outcome, observation)

    observations = next_model.setdefault("observations", [])
    if not isinstance(observations, list):
        observations = []
    observations.append(observation.to_dict())
    next_model["observations"] = observations[-MAX_STORED_OBSERVATIONS:]
    update_loss_streaks(next_model, observation)
    return next_model


def merge_observation_into_prototype(
    prototypes: list[Any],
    strategy: str,
    outcome: str,
    observation: PatternObservation,
) -> None:
    prototype = next(
        (
            item
            for item in prototypes
            if isinstance(item, dict)
            and item.get("strategy") == strategy
            and item.get("outcome") == outcome
        ),
        None,
    )
    if prototype is None:
        prototypes.append(make_prototype(strategy, outcome, [observation]))
        return

    sample_count = int(prototype.get("sampleCount") or 0) + 1
    old_count = sample_count - 1
    features = prototype.get("features")
    if not isinstance(features, dict):
        features = {}
    current_features = observation.features.vector()
    merged_features = {}
    for key in FEATURE_KEYS:
        merged_features[key] = decimal_to_str(
            weighted_average(d(features.get(key)), Decimal(old_count), current_features[key], Decimal("1"))
        )
    prototype["sampleCount"] = sample_count
    prototype["averageReturnPct"] = decimal_to_str(
        update_average(d(prototype.get("averageReturnPct")), sample_count, observation.net_return_pct)
    )
    prototype["features"] = merged_features


def update_loss_streaks(model: dict[str, Any], observation: PatternObservation) -> None:
    streaks = model.setdefault("lossStreaks", empty_loss_streaks())
    if not isinstance(streaks, dict):
        streaks = empty_loss_streaks()
        model["lossStreaks"] = streaks
    markets = streaks.setdefault("markets", {})
    if not isinstance(markets, dict):
        markets = {}
        streaks["markets"] = markets
    strategies = streaks.setdefault("strategies", {})
    if not isinstance(strategies, dict):
        strategies = {}
        streaks["strategies"] = strategies
    market_strategies = streaks.setdefault("marketStrategies", {})
    if not isinstance(market_strategies, dict):
        market_strategies = {}
        streaks["marketStrategies"] = market_strategies
    market_row = markets.get(observation.market)
    if not isinstance(market_row, dict):
        market_row = {"consecutiveLosses": 0, "lastLossAt": ""}
    strategy_row = strategies.get(observation.strategy)
    if not isinstance(strategy_row, dict):
        strategy_row = {"consecutiveLosses": 0, "lastLossAt": ""}
    pattern_key = pattern_streak_key(observation.market, observation.strategy)
    pattern_row = market_strategies.get(pattern_key)
    if not isinstance(pattern_row, dict):
        pattern_row = {"consecutiveLosses": 0, "lastLossAt": ""}
    if observation.outcome == "loss":
        streaks["globalConsecutiveLosses"] = int(streaks.get("globalConsecutiveLosses") or 0) + 1
        streaks["globalLastLossAt"] = observation.exit_time
        market_row["consecutiveLosses"] = int(market_row.get("consecutiveLosses") or 0) + 1
        market_row["lastLossAt"] = observation.exit_time
        strategy_row["consecutiveLosses"] = int(strategy_row.get("consecutiveLosses") or 0) + 1
        strategy_row["lastLossAt"] = observation.exit_time
        pattern_row["consecutiveLosses"] = int(pattern_row.get("consecutiveLosses") or 0) + 1
        pattern_row["lastLossAt"] = observation.exit_time
    else:
        streaks["globalConsecutiveLosses"] = 0
        market_row["consecutiveLosses"] = 0
        strategy_row["consecutiveLosses"] = 0
        pattern_row["consecutiveLosses"] = 0
    markets[observation.market] = market_row
    strategies[observation.strategy] = strategy_row
    market_strategies[pattern_key] = pattern_row


def loss_streak_counts(model: dict[str, Any] | None, market: str) -> tuple[int, int, str]:
    market_losses, _strategy_losses, _pattern_losses, global_losses, last_loss_at = loss_streak_detail_counts(
        model,
        market,
        ALL_STRATEGIES,
    )
    return market_losses, global_losses, last_loss_at


def loss_streak_detail_counts(
    model: dict[str, Any] | None,
    market: str,
    strategy: str,
) -> tuple[int, int, int, int, str]:
    if not isinstance(model, dict):
        return 0, 0, 0, 0, ""
    streaks = model.get("lossStreaks")
    if not isinstance(streaks, dict):
        return 0, 0, 0, 0, ""
    markets = streaks.get("markets")
    market_row = markets.get(market) if isinstance(markets, dict) else None
    market_losses = int(market_row.get("consecutiveLosses") or 0) if isinstance(market_row, dict) else 0
    strategies = streaks.get("strategies")
    strategy_row = strategies.get(strategy) if isinstance(strategies, dict) else None
    strategy_losses = int(strategy_row.get("consecutiveLosses") or 0) if isinstance(strategy_row, dict) else 0
    market_strategies = streaks.get("marketStrategies")
    pattern_row = market_strategies.get(pattern_streak_key(market, strategy)) if isinstance(market_strategies, dict) else None
    pattern_losses = int(pattern_row.get("consecutiveLosses") or 0) if isinstance(pattern_row, dict) else 0
    global_losses = int(streaks.get("globalConsecutiveLosses") or 0)
    last_loss_at = ""
    for row in (pattern_row, strategy_row, market_row):
        if isinstance(row, dict) and row.get("lastLossAt"):
            last_loss_at = str(row.get("lastLossAt") or "")
            break
    return market_losses, strategy_losses, pattern_losses, global_losses, last_loss_at or str(streaks.get("globalLastLossAt") or "")


def pattern_streak_key(market: str, strategy: str) -> str:
    return f"{market}|{strategy or ALL_STRATEGIES}"


def record_broken_profit_pattern(
    model: dict[str, Any],
    observation: PatternObservation,
    profit_similarity: Decimal,
) -> None:
    rows = model.setdefault("brokenProfitPatterns", [])
    if not isinstance(rows, list):
        rows = []
    rows.append(
        {
            "market": observation.market,
            "strategy": observation.strategy,
            "brokeAt": observation.exit_time,
            "lossReturnPct": decimal_to_str(observation.net_return_pct),
            "profitSimilarity": decimal_to_str(profit_similarity),
            "features": observation.features.to_dict(),
        }
    )
    model["brokenProfitPatterns"] = rows[-MAX_BROKEN_PROFIT_PATTERNS:]


def update_average(old_average: Decimal, new_count: int, latest: Decimal) -> Decimal:
    if new_count <= 1:
        return latest
    return ((old_average * Decimal(new_count - 1)) + latest) / Decimal(new_count)


def weighted_average(old_value: Decimal, old_weight: Decimal, new_value: Decimal, new_weight: Decimal) -> Decimal:
    total_weight = old_weight + new_weight
    if total_weight <= 0:
        return new_value
    return ((old_value * old_weight) + (new_value * new_weight)) / total_weight


def merge_feature_payloads(
    old_payload: Any,
    old_weight: Decimal,
    new_payload: dict[str, Any],
    new_weight: Decimal,
) -> dict[str, str]:
    old_features = PatternFeatures.from_dict(old_payload if isinstance(old_payload, dict) else {})
    new_features = PatternFeatures.from_dict(new_payload)
    old_vector = old_features.vector()
    new_vector = new_features.vector()
    return {
        key: decimal_to_str(weighted_average(old_vector[key], old_weight, new_vector[key], new_weight))
        for key in FEATURE_KEYS
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SyntheticExitCandle:
    trade_price: Decimal
    candle_date_time_kst: str


def score_current_pattern(
    model: dict[str, Any] | None,
    market: str,
    strategy: str,
    candles: Iterable[Candle],
) -> PatternScore:
    if not model or not isinstance(model.get("prototypes"), list):
        return PatternScore()
    features = feature_snapshot(candles)
    raw_profit_similarity = best_similarity(model, strategy, "profit", features)
    loss_similarity = best_similarity(model, strategy, "loss", features)
    broken_profit_similarity = best_broken_profit_similarity(model, strategy, features)
    profit_similarity = max(Decimal("0"), raw_profit_similarity - broken_profit_similarity * Decimal("0.45"))
    adjustment = profit_similarity * Decimal("0.30") - loss_similarity * Decimal("0.55")
    if broken_profit_similarity >= PROFIT_BREAK_THRESHOLD:
        adjustment -= broken_profit_similarity * Decimal("0.35")
    blocked = loss_similarity >= LOSS_BLOCK_THRESHOLD and profit_similarity < loss_similarity
    if broken_profit_similarity >= Decimal("0.78") and loss_similarity >= PROFIT_CONFIRM_THRESHOLD:
        blocked = True
    exit_now = loss_similarity >= LOSS_EXIT_THRESHOLD and profit_similarity < PROFIT_CONFIRM_THRESHOLD
    reason = (
        f"pattern {market}/{strategy} "
        f"profit={profit_similarity:.3f} loss={loss_similarity:.3f} broken={broken_profit_similarity:.3f} "
        f"adj={adjustment:.3f}"
    )
    return PatternScore(
        profit_similarity=profit_similarity,
        loss_similarity=loss_similarity,
        broken_profit_similarity=broken_profit_similarity,
        adjustment=adjustment,
        blocked=blocked,
        exit_now=exit_now,
        reason=reason,
    )


def best_similarity(model: dict[str, Any], strategy: str, outcome: str, features: PatternFeatures) -> Decimal:
    scores: list[Decimal] = []
    for prototype in model.get("prototypes", []):
        if not isinstance(prototype, dict) or prototype.get("outcome") != outcome:
            continue
        proto_strategy = str(prototype.get("strategy") or "")
        if proto_strategy not in {strategy, ALL_STRATEGIES}:
            continue
        proto_features = prototype.get("features")
        if not isinstance(proto_features, dict):
            continue
        similarity = feature_similarity(features, PatternFeatures.from_dict(proto_features))
        if proto_strategy == ALL_STRATEGIES:
            similarity *= Decimal("0.88")
        scores.append(similarity)
    return max(scores) if scores else Decimal("0")


def best_broken_profit_similarity(model: dict[str, Any], strategy: str, features: PatternFeatures) -> Decimal:
    scores: list[Decimal] = []
    rows = model.get("brokenProfitPatterns", [])
    if not isinstance(rows, list):
        return Decimal("0")
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_strategy = str(row.get("strategy") or "")
        if row_strategy not in {strategy, ALL_STRATEGIES}:
            continue
        row_features = row.get("features")
        if not isinstance(row_features, dict):
            continue
        scores.append(feature_similarity(features, PatternFeatures.from_dict(row_features)))
    return max(scores) if scores else Decimal("0")


def feature_similarity(current: PatternFeatures, prototype: PatternFeatures) -> Decimal:
    current_vector = current.vector()
    prototype_vector = prototype.vector()
    total = Decimal("0")
    for key in FEATURE_KEYS:
        scale = FEATURE_SCALES[key]
        distance = abs(current_vector[key] - prototype_vector[key]) / scale if scale > 0 else Decimal("0")
        total += min(Decimal("1"), distance)
    average_distance = total / Decimal(len(FEATURE_KEYS))
    return max(Decimal("0"), Decimal("1") - average_distance)


def simulate_strategy_observations(
    market: str,
    candles: list[Candle],
    settings: TradingSettings,
    strategy_name: str,
) -> list[PatternObservation]:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    if len(ordered) < settings.long_window + 2:
        return []
    strategy_settings = replace(settings, market=market, markets=(market,), strategy_name=strategy_name)
    strategy = make_strategy_by_name(strategy_settings, strategy_name)
    observations: list[PatternObservation] = []
    open_entry: dict[str, Any] | None = None
    start_index = max(settings.long_window + 1, 60)

    for index in range(start_index, len(ordered)):
        history = ordered[max(0, index + 1 - 240) : index + 1]
        current = history[-1]
        signal = strategy.evaluate(history)
        if open_entry is not None:
            if signal.action == "sell" or pattern_training_exit(history, d(open_entry["entryPrice"]), settings):
                observations.append(
                    close_observation(open_entry, current, settings.fee_rate)
                )
                open_entry = None
            continue
        if signal.action == "buy":
            open_entry = {
                "market": market,
                "strategy": strategy_name,
                "entryTime": current.candle_date_time_kst,
                "entryPrice": current.trade_price,
                "features": feature_snapshot(history),
            }

    return observations


def pattern_training_exit(candles: list[Candle], entry_price: Decimal, settings: TradingSettings) -> bool:
    if not candles or entry_price <= 0:
        return False
    latest = candles[-1]
    pnl_pct = price_change_pct(entry_price, latest.trade_price)
    if pnl_pct <= -settings.stop_loss_pct:
        return True
    if pnl_pct < settings.take_profit_pct:
        return False
    closes = [candle.trade_price for candle in candles]
    short = sum(closes[-settings.short_window:], Decimal("0")) / Decimal(settings.short_window)
    long = sum(closes[-settings.long_window:], Decimal("0")) / Decimal(settings.long_window)
    recent_high = max(closes[-settings.long_window:])
    pullback = (latest.trade_price - recent_high) / recent_high * Decimal("100") if recent_high > 0 else Decimal("0")
    return short < long or pullback <= -settings.strategy_pullback_sell_pct


def close_observation(open_entry: dict[str, Any], exit_candle: Candle, fee_rate: Decimal) -> PatternObservation:
    entry_price = d(open_entry["entryPrice"])
    exit_price = exit_candle.trade_price
    net_return = ((exit_price / entry_price) * (Decimal("1") - fee_rate) * (Decimal("1") - fee_rate) - Decimal("1")) * Decimal("100")
    outcome = "profit" if net_return > 0 else "loss"
    return PatternObservation(
        market=str(open_entry["market"]),
        strategy=str(open_entry["strategy"]),
        entry_time=str(open_entry["entryTime"]),
        exit_time=exit_candle.candle_date_time_kst,
        entry_price=entry_price,
        exit_price=exit_price,
        net_return_pct=net_return,
        outcome=outcome,
        features=open_entry["features"],
    )
