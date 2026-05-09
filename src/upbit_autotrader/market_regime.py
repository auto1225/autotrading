from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .config import TradingSettings
from .models import Candle, decimal_to_str


@dataclass(frozen=True)
class MarketRegimeSignal:
    label: str = "neutral"
    block_new_entries: bool = False
    score_adjustment: Decimal = Decimal("0")
    min_score_adjustment: Decimal = Decimal("0")
    deploy_multiplier: Decimal = Decimal("1")
    positive_ratio: Decimal = Decimal("0")
    crash_ratio: Decimal = Decimal("0")
    average_trend_pct: Decimal = Decimal("0")
    tags: tuple[str, ...] = ()
    reason: str = "market-regime-clear"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "blockNewEntries": self.block_new_entries,
            "scoreAdjustment": decimal_to_str(self.score_adjustment),
            "minScoreAdjustment": decimal_to_str(self.min_score_adjustment),
            "deployMultiplier": decimal_to_str(self.deploy_multiplier),
            "positiveRatio": decimal_to_str(self.positive_ratio),
            "crashRatio": decimal_to_str(self.crash_ratio),
            "averageTrendPct": decimal_to_str(self.average_trend_pct),
            "tags": list(self.tags),
            "reason": self.reason,
        }


def evaluate_market_regime(
    settings: TradingSettings,
    candle_map: Mapping[str, Sequence[Candle]],
) -> MarketRegimeSignal:
    if not settings.risk_regime_guard_enabled:
        return MarketRegimeSignal(reason="market-regime-disabled")

    trends: list[Decimal] = []
    crash_count = 0
    for candles in candle_map.values():
        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        if len(ordered) < 2:
            continue
        trend = trend_pct(ordered, settings.risk_regime_trend_window_candles)
        trends.append(trend)
        if trend <= -settings.risk_regime_crash_trend_pct:
            crash_count += 1

    if len(trends) < settings.risk_regime_min_market_count:
        return MarketRegimeSignal(reason=f"market-regime-insufficient-sample n={len(trends)}")

    positive_count = sum(1 for trend in trends if trend > 0)
    positive_ratio = Decimal(positive_count) / Decimal(len(trends))
    crash_ratio = Decimal(crash_count) / Decimal(len(trends))
    average_trend = sum(trends, Decimal("0")) / Decimal(len(trends))
    tags: list[str] = []

    if crash_ratio >= settings.risk_regime_max_crash_ratio or average_trend <= settings.risk_regime_min_avg_trend_pct:
        tags.append("market-risk-off")
        return MarketRegimeSignal(
            label="risk-off",
            block_new_entries=True,
            score_adjustment=Decimal("-1.20"),
            min_score_adjustment=Decimal("0.40"),
            deploy_multiplier=Decimal("0"),
            positive_ratio=positive_ratio,
            crash_ratio=crash_ratio,
            average_trend_pct=average_trend,
            tags=tuple(tags),
            reason=(
                f"risk-off breadth positive={positive_ratio:.2f} "
                f"crash={crash_ratio:.2f} avgTrend={average_trend:.2f}%"
            ),
        )

    if positive_ratio < settings.risk_regime_min_positive_ratio:
        tags.append("market-weak")
        tags.append("market-narrow-breadth")
        return MarketRegimeSignal(
            label="weak",
            block_new_entries=True,
            score_adjustment=Decimal("-0.65"),
            min_score_adjustment=Decimal("0.35"),
            deploy_multiplier=Decimal("0.85"),
            positive_ratio=positive_ratio,
            crash_ratio=crash_ratio,
            average_trend_pct=average_trend,
            tags=tuple(tags),
            reason=(
                f"weak narrow breadth positive={positive_ratio:.2f} "
                f"crash={crash_ratio:.2f} avgTrend={average_trend:.2f}%"
            ),
        )

    if positive_ratio < settings.risk_regime_soft_positive_ratio or average_trend < Decimal("0"):
        tags.append("market-weak")
        return MarketRegimeSignal(
            label="weak",
            block_new_entries=True,
            score_adjustment=Decimal("-0.35"),
            min_score_adjustment=Decimal("0.20"),
            deploy_multiplier=Decimal("0.70"),
            positive_ratio=positive_ratio,
            crash_ratio=crash_ratio,
            average_trend_pct=average_trend,
            tags=tuple(tags),
            reason=(
                f"weak breadth positive={positive_ratio:.2f} "
                f"crash={crash_ratio:.2f} avgTrend={average_trend:.2f}%"
            ),
        )

    if positive_ratio >= settings.risk_regime_risk_on_positive_ratio and average_trend > Decimal("0"):
        tags.append("market-risk-on")
        return MarketRegimeSignal(
            label="risk-on",
            score_adjustment=Decimal("0.08"),
            deploy_multiplier=Decimal("1"),
            positive_ratio=positive_ratio,
            crash_ratio=crash_ratio,
            average_trend_pct=average_trend,
            tags=tuple(tags),
            reason=(
                f"risk-on breadth positive={positive_ratio:.2f} "
                f"crash={crash_ratio:.2f} avgTrend={average_trend:.2f}%"
            ),
        )

    return MarketRegimeSignal(
        positive_ratio=positive_ratio,
        crash_ratio=crash_ratio,
        average_trend_pct=average_trend,
        reason=(
            f"neutral breadth positive={positive_ratio:.2f} "
            f"crash={crash_ratio:.2f} avgTrend={average_trend:.2f}%"
        ),
    )


def trend_pct(candles: Sequence[Candle], window: int) -> Decimal:
    if len(candles) < 2:
        return Decimal("0")
    start_index = max(0, len(candles) - max(1, window) - 1)
    start = candles[start_index].trade_price
    end = candles[-1].trade_price
    if start <= 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")
