from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .config import TradingSettings
from .models import Candle, decimal_to_str
from .price_units import round_krw_price, stop_price_below, target_price_above


@dataclass(frozen=True)
class ChartTradeLevels:
    market: str
    current_price: Decimal
    entry_price: Decimal
    preferred_entry_price: Decimal
    max_entry_price: Decimal
    support_price: Decimal
    resistance_price: Decimal
    stop_loss_price: Decimal
    take_profit_price: Decimal
    trailing_stop_price: Decimal
    vwap_price: Decimal
    atr_price: Decimal
    atr_pct: Decimal
    range_position_pct: Decimal
    risk_pct: Decimal
    reward_pct: Decimal
    risk_reward: Decimal
    method: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "currentPrice": decimal_to_str(self.current_price),
            "entryPrice": decimal_to_str(self.entry_price),
            "preferredEntryPrice": decimal_to_str(self.preferred_entry_price),
            "maxEntryPrice": decimal_to_str(self.max_entry_price),
            "supportPrice": decimal_to_str(self.support_price),
            "resistancePrice": decimal_to_str(self.resistance_price),
            "stopLossPrice": decimal_to_str(self.stop_loss_price),
            "takeProfitPrice": decimal_to_str(self.take_profit_price),
            "trailingStopPrice": decimal_to_str(self.trailing_stop_price),
            "vwapPrice": decimal_to_str(self.vwap_price),
            "atrPrice": decimal_to_str(self.atr_price),
            "atrPct": decimal_round_str(self.atr_pct),
            "rangePositionPct": decimal_round_str(self.range_position_pct),
            "riskPct": decimal_round_str(self.risk_pct),
            "rewardPct": decimal_round_str(self.reward_pct),
            "riskReward": decimal_round_str(self.risk_reward),
            "method": self.method,
            "reason": self.reason,
        }


def chart_trade_levels(
    settings: TradingSettings,
    candles: list[Candle],
    current_price: Decimal | None = None,
    avg_entry_price: Decimal = Decimal("0"),
    held: bool = False,
) -> ChartTradeLevels:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    latest = ordered[-1] if ordered else None
    price = current_price if current_price is not None and current_price > 0 else latest.trade_price if latest else Decimal("0")
    market = latest.market if latest else settings.market
    reference = avg_entry_price if held and avg_entry_price > 0 else price
    if not ordered:
        return empty_levels(settings, market, reference)
    if price <= 0:
        return empty_levels(settings, market, reference)

    windows = window_slices(ordered)
    support = nearest_support(price, windows)
    resistance = nearest_resistance(price, windows)
    atr = average_true_range(ordered, 14)
    if atr <= 0:
        atr = price * Decimal("0.005")
    atr_pct = pct(atr, price)
    current_vwap = vwap(ordered[-min(len(ordered), max(settings.long_window * 2, 20)) :]) if ordered else price
    range_position = range_position_pct(price, windows[-1] if windows else ordered)

    hard_stop = reference * (Decimal("1") - settings.stop_loss_pct / Decimal("100"))
    support_stop = support - atr * Decimal("0.35") if support > 0 else hard_stop
    volatility_stop = price - atr * (Decimal("1.25") if held else Decimal("1.10"))
    stop = max(hard_stop, support_stop, volatility_stop)
    stop = clamp_below_price(stop, price)
    stop = stop_price_below(stop, price)

    risk_price = max(price - stop, price * Decimal("0.001"))
    fixed_target = reference * (Decimal("1") + settings.take_profit_pct / Decimal("100"))
    rr_target = price + risk_price * Decimal("1.65")
    resistance_target = resistance + atr * Decimal("0.20") if resistance > price else price + atr * Decimal("2.20")
    take_profit = max(rr_target, min(max(fixed_target, resistance_target), price + atr * Decimal("4.0")))
    if take_profit <= price:
        take_profit = price + risk_price * Decimal("1.65")
    take_profit = target_price_above(take_profit, price)

    trailing_stop = Decimal("0")
    if held and avg_entry_price > 0 and price > avg_entry_price:
        trailing_stop = max(stop, price - max(atr * Decimal("1.15"), price * Decimal("0.006")))
        trailing_stop = clamp_below_price(trailing_stop, price)
        trailing_stop = stop_price_below(trailing_stop, price)

    preferred_entry = price
    if not held and ordered:
        if range_position >= Decimal("82") and current_vwap > 0 and price > current_vwap:
            preferred_entry = max(support, current_vwap, price - atr * Decimal("0.60"))
        elif support > 0 and price > support + atr * Decimal("1.8"):
            preferred_entry = max(support, price - atr * Decimal("0.50"))
    max_entry = price + min(atr * Decimal("0.35"), price * Decimal("0.004"))
    preferred_entry = round_krw_price(preferred_entry, "floor")
    max_entry = target_price_above(max_entry, price)
    support = round_krw_price(support, "floor")
    resistance = round_krw_price(resistance, "ceil")
    current_vwap = round_krw_price(current_vwap, "nearest")
    atr = round_krw_price(atr, "nearest")

    risk_pct = pct(price - stop, price)
    reward_pct = pct(take_profit - price, price)
    risk_reward = reward_pct / risk_pct if risk_pct > 0 else Decimal("0")
    method = "chart_atr_vwap_sr"
    reason = (
        f"chart levels support {decimal_to_str(support)}, resistance {decimal_to_str(resistance)}, "
        f"ATR {decimal_round_str(atr_pct)}%, VWAP {decimal_to_str(current_vwap)}, "
        f"entry {decimal_to_str(price)}, stop {decimal_to_str(stop)}, "
        f"target {decimal_to_str(take_profit)}, RR {decimal_round_str(risk_reward)}"
    )
    return ChartTradeLevels(
        market=market,
        current_price=price,
        entry_price=price,
        preferred_entry_price=preferred_entry,
        max_entry_price=max_entry,
        support_price=support,
        resistance_price=resistance,
        stop_loss_price=stop,
        take_profit_price=take_profit,
        trailing_stop_price=trailing_stop,
        vwap_price=current_vwap,
        atr_price=atr,
        atr_pct=atr_pct,
        range_position_pct=range_position,
        risk_pct=risk_pct,
        reward_pct=reward_pct,
        risk_reward=risk_reward,
        method=method,
        reason=reason,
    )


def empty_levels(settings: TradingSettings, market: str, reference: Decimal) -> ChartTradeLevels:
    reference = reference if reference > 0 else Decimal("0")
    stop = reference * (Decimal("1") - settings.stop_loss_pct / Decimal("100")) if reference > 0 else Decimal("0")
    target = reference * (Decimal("1") + settings.take_profit_pct / Decimal("100")) if reference > 0 else Decimal("0")
    if reference > 0:
        stop = stop_price_below(stop, reference)
        target = target_price_above(target, reference)
    return ChartTradeLevels(
        market=market,
        current_price=reference,
        entry_price=reference,
        preferred_entry_price=reference,
        max_entry_price=reference,
        support_price=Decimal("0"),
        resistance_price=Decimal("0"),
        stop_loss_price=stop,
        take_profit_price=target,
        trailing_stop_price=Decimal("0"),
        vwap_price=reference,
        atr_price=Decimal("0"),
        atr_pct=Decimal("0"),
        range_position_pct=Decimal("50"),
        risk_pct=settings.stop_loss_pct if reference > 0 else Decimal("0"),
        reward_pct=settings.take_profit_pct if reference > 0 else Decimal("0"),
        risk_reward=settings.take_profit_pct / settings.stop_loss_pct if settings.stop_loss_pct > 0 else Decimal("0"),
        method="fixed_fallback",
        reason="chart levels unavailable; fixed fallback levels are used",
    )


def window_slices(ordered: list[Candle]) -> list[list[Candle]]:
    if not ordered:
        return []
    sizes = (12, 24, 48)
    return [ordered[-min(len(ordered), size) :] for size in sizes]


def nearest_support(price: Decimal, windows: list[list[Candle]]) -> Decimal:
    candidates = [min(candle.low_price for candle in window) for window in windows if window]
    below = [candidate for candidate in candidates if Decimal("0") < candidate < price]
    if below:
        return max(below)
    return min(candidates) if candidates else Decimal("0")


def nearest_resistance(price: Decimal, windows: list[list[Candle]]) -> Decimal:
    candidates = [max(candle.high_price for candle in window) for window in windows if window]
    above = [candidate for candidate in candidates if candidate > price]
    if above:
        return min(above)
    return max(candidates) if candidates else Decimal("0")


def average_true_range(ordered: list[Candle], period: int) -> Decimal:
    if not ordered:
        return Decimal("0")
    subset = ordered[-min(len(ordered), period) :]
    ranges: list[Decimal] = []
    previous_close: Decimal | None = None
    for candle in subset:
        if previous_close is None:
            ranges.append(candle.high_price - candle.low_price)
        else:
            ranges.append(
                max(
                    candle.high_price - candle.low_price,
                    abs(candle.high_price - previous_close),
                    abs(candle.low_price - previous_close),
                )
            )
        previous_close = candle.trade_price
    return sum(ranges, Decimal("0")) / Decimal(len(ranges)) if ranges else Decimal("0")


def vwap(candles: list[Candle]) -> Decimal:
    if not candles:
        return Decimal("0")
    volume = sum((candle.candle_acc_trade_volume for candle in candles), Decimal("0"))
    if volume > 0:
        return sum((candle.trade_price * candle.candle_acc_trade_volume for candle in candles), Decimal("0")) / volume
    trade_value = sum((candle.candle_acc_trade_price for candle in candles), Decimal("0"))
    fallback_volume = sum(
        (candle.candle_acc_trade_price / candle.trade_price for candle in candles if candle.trade_price > 0),
        Decimal("0"),
    )
    if fallback_volume <= 0:
        return candles[-1].trade_price
    return trade_value / fallback_volume


def range_position_pct(price: Decimal, window: list[Candle]) -> Decimal:
    if not window:
        return Decimal("50")
    high = max(candle.high_price for candle in window)
    low = min(candle.low_price for candle in window)
    if high <= low:
        return Decimal("50")
    return (price - low) / (high - low) * Decimal("100")


def pct(value: Decimal, base: Decimal) -> Decimal:
    if base <= 0:
        return Decimal("0")
    return value / base * Decimal("100")


def clamp_below_price(value: Decimal, price: Decimal) -> Decimal:
    if price <= 0:
        return Decimal("0")
    upper = price * Decimal("0.999")
    lower = price * Decimal("0.80")
    return max(lower, min(value, upper))


def decimal_round_str(value: Decimal, places: str = "0.01") -> str:
    return decimal_to_str(value.quantize(Decimal(places)))
