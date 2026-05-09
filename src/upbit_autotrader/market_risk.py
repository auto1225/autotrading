from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from typing import Any

from .config import TradingSettings
from .pattern_learning import loss_streak_detail_counts


@dataclass(frozen=True)
class MarketRiskSignal:
    block_entry: bool = False
    exit_now: bool = False
    score_adjustment: Decimal = Decimal("0")
    tags: tuple[str, ...] = ()
    reason: str = "risk-clear"

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockEntry": self.block_entry,
            "exitNow": self.exit_now,
            "scoreAdjustment": str(self.score_adjustment),
            "tags": list(self.tags),
            "reason": self.reason,
        }


def evaluate_market_risk(
    settings: TradingSettings,
    pattern_model: dict[str, Any] | None,
    market: str,
    held: bool,
    trend_1m_pct: Decimal,
    trend_5m_pct: Decimal,
    trend_30m_pct: Decimal,
    volatility_pct: Decimal,
    drawdown_pct: Decimal,
    volume_ratio: Decimal,
    day_change_pct: Decimal = Decimal("0"),
    range_position_pct: Decimal = Decimal("50"),
    trade_value_24h_krw: Decimal | None = None,
    latest_candle_trade_value_krw: Decimal | None = None,
    trade_pressure: Decimal | None = None,
    strategy: str = "",
    now: datetime | None = None,
) -> MarketRiskSignal:
    tags: list[str] = []
    reasons: list[str] = []
    score_adjustment = Decimal("0")
    block_entry = False
    exit_now = False

    if settings.risk_crash_guard_enabled and is_crash_regime(
        settings,
        trend_1m_pct,
        trend_5m_pct,
        trend_30m_pct,
        volatility_pct,
        drawdown_pct,
    ):
        tags.append("crash-guard")
        reasons.append("sharp downside regime")
        block_entry = True
        exit_now = held
        score_adjustment -= Decimal("1.25")

    if is_overheated_entry(settings, trend_1m_pct, day_change_pct, range_position_pct, volume_ratio):
        tags.append("overheat-guard")
        reasons.append("overheated entry risk")
        block_entry = True
        score_adjustment -= Decimal("0.75")

    if is_chase_entry(settings, trend_5m_pct, trend_30m_pct, range_position_pct, volume_ratio):
        tags.append("chase-guard")
        reasons.append("late chase entry risk")
        block_entry = True
        score_adjustment -= Decimal("0.85")

    if is_low_liquidity(settings, trade_value_24h_krw, latest_candle_trade_value_krw):
        tags.append("liquidity-guard")
        reasons.append("liquidity below guard")
        block_entry = True
        score_adjustment -= Decimal("0.60")

    if is_trade_pressure_weak(settings, trade_pressure):
        tags.append("microstructure-guard")
        reasons.append("sell pressure dominates recent trades")
        block_entry = True
        score_adjustment -= Decimal("0.45")

    market_losses, strategy_losses, pattern_losses, global_losses, last_loss_at = loss_streak_detail_counts(
        pattern_model,
        market,
        strategy,
    )
    if loss_streak_blocked(settings, market_losses, global_losses, last_loss_at, now=now):
        tags.append("loss-streak-guard")
        reasons.append(f"loss streak market={market_losses} global={global_losses}")
        block_entry = True
        score_adjustment -= Decimal("0.90")
    if detail_loss_streak_blocked(settings, strategy_losses, pattern_losses, last_loss_at, now=now):
        tags.append("same-pattern-loss-guard")
        reasons.append(f"loss streak strategy={strategy_losses} samePattern={pattern_losses}")
        block_entry = True
        score_adjustment -= Decimal("1.10")

    if not tags:
        return MarketRiskSignal()
    return MarketRiskSignal(
        block_entry=block_entry,
        exit_now=exit_now,
        score_adjustment=score_adjustment,
        tags=tuple(tags),
        reason="; ".join(reasons),
    )


def is_crash_regime(
    settings: TradingSettings,
    trend_1m_pct: Decimal,
    trend_5m_pct: Decimal,
    trend_30m_pct: Decimal,
    volatility_pct: Decimal,
    drawdown_pct: Decimal,
) -> bool:
    if trend_1m_pct <= -settings.risk_crash_1m_drop_pct:
        return True
    if trend_5m_pct <= -settings.risk_crash_5m_drop_pct:
        return True
    if trend_30m_pct <= -settings.risk_crash_30m_drop_pct:
        return True
    if drawdown_pct <= -settings.risk_crash_drawdown_pct and trend_5m_pct < 0:
        return True
    return volatility_pct >= settings.risk_crash_volatility_pct and trend_5m_pct < 0


def is_overheated_entry(
    settings: TradingSettings,
    trend_1m_pct: Decimal,
    day_change_pct: Decimal,
    range_position_pct: Decimal,
    volume_ratio: Decimal,
) -> bool:
    if day_change_pct >= settings.risk_overheat_day_change_pct and trend_1m_pct <= settings.risk_overheat_1m_reversal_pct:
        return True
    if range_position_pct >= settings.risk_overheat_range_position_pct and trend_1m_pct <= settings.risk_overheat_1m_reversal_pct:
        return True
    return (
        volume_ratio >= settings.risk_overheat_volume_ratio
        and range_position_pct >= settings.risk_overheat_range_position_pct
        and trend_1m_pct < 0
    )


def is_chase_entry(
    settings: TradingSettings,
    trend_5m_pct: Decimal,
    trend_30m_pct: Decimal,
    range_position_pct: Decimal,
    volume_ratio: Decimal,
) -> bool:
    if range_position_pct < settings.risk_chase_range_position_pct:
        return False
    if volume_ratio < settings.risk_chase_volume_ratio:
        return False
    return trend_5m_pct >= settings.risk_chase_5m_rise_pct or trend_30m_pct >= settings.risk_chase_30m_rise_pct


def is_trade_pressure_weak(settings: TradingSettings, trade_pressure: Decimal | None) -> bool:
    return trade_pressure is not None and trade_pressure <= settings.risk_min_trade_pressure


def is_low_liquidity(
    settings: TradingSettings,
    trade_value_24h_krw: Decimal | None,
    latest_candle_trade_value_krw: Decimal | None,
) -> bool:
    if (
        trade_value_24h_krw is not None
        and settings.risk_market_min_trade_value_24h_krw > 0
        and trade_value_24h_krw < settings.risk_market_min_trade_value_24h_krw
    ):
        return True
    return (
        latest_candle_trade_value_krw is not None
        and settings.risk_min_candle_trade_value_krw > 0
        and latest_candle_trade_value_krw < settings.risk_min_candle_trade_value_krw
    )


def loss_streak_blocked(
    settings: TradingSettings,
    market_losses: int,
    global_losses: int,
    last_loss_at: str,
    now: datetime | None = None,
) -> bool:
    if market_losses < settings.risk_max_consecutive_losses and global_losses < settings.risk_global_max_consecutive_losses:
        return False
    if settings.risk_loss_streak_cooldown_minutes <= 0:
        return True
    parsed = parse_time(last_loss_at)
    if parsed is None:
        return True
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return current - parsed <= timedelta(minutes=settings.risk_loss_streak_cooldown_minutes)


def detail_loss_streak_blocked(
    settings: TradingSettings,
    strategy_losses: int,
    pattern_losses: int,
    last_loss_at: str,
    now: datetime | None = None,
) -> bool:
    if (
        strategy_losses < settings.risk_strategy_max_consecutive_losses
        and pattern_losses < settings.risk_same_pattern_max_consecutive_losses
    ):
        return False
    if settings.risk_loss_streak_cooldown_minutes <= 0:
        return True
    parsed = parse_time(last_loss_at)
    if parsed is None:
        return True
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return current - parsed <= timedelta(minutes=settings.risk_loss_streak_cooldown_minutes)


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
