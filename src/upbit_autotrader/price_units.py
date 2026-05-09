from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Literal


RoundMode = Literal["floor", "ceil", "nearest"]


def krw_tick_size(price: Decimal) -> Decimal:
    value = abs(price)
    if value >= Decimal("1000000"):
        return Decimal("1000")
    if value >= Decimal("500000"):
        return Decimal("500")
    if value >= Decimal("100000"):
        return Decimal("100")
    if value >= Decimal("50000"):
        return Decimal("50")
    if value >= Decimal("10000"):
        return Decimal("10")
    if value >= Decimal("5000"):
        return Decimal("5")
    if value >= Decimal("100"):
        return Decimal("1")
    if value >= Decimal("10"):
        return Decimal("0.1")
    if value >= Decimal("1"):
        return Decimal("0.01")
    if value >= Decimal("0.1"):
        return Decimal("0.001")
    if value >= Decimal("0.01"):
        return Decimal("0.0001")
    if value >= Decimal("0.001"):
        return Decimal("0.00001")
    if value >= Decimal("0.0001"):
        return Decimal("0.000001")
    if value >= Decimal("0.00001"):
        return Decimal("0.0000001")
    return Decimal("0.00000001")


def round_krw_price(price: Decimal, mode: RoundMode = "nearest") -> Decimal:
    if price <= 0:
        return Decimal("0")
    tick = krw_tick_size(price)
    rounding = {
        "floor": ROUND_FLOOR,
        "ceil": ROUND_CEILING,
        "nearest": ROUND_HALF_UP,
    }[mode]
    return (price / tick).to_integral_value(rounding=rounding) * tick


def next_krw_price(price: Decimal) -> Decimal:
    if price <= 0:
        return Decimal("0")
    base = round_krw_price(price, "floor")
    return base + krw_tick_size(base if base > 0 else price)


def previous_krw_price(price: Decimal) -> Decimal:
    if price <= 0:
        return Decimal("0")
    base = round_krw_price(price, "floor")
    previous = base - krw_tick_size(base if base > 0 else price)
    return previous if previous > 0 else Decimal("0")


def stop_price_below(stop_price: Decimal, current_price: Decimal) -> Decimal:
    if stop_price <= 0 or current_price <= 0:
        return Decimal("0")
    rounded = round_krw_price(stop_price, "ceil")
    if rounded >= current_price:
        rounded = previous_krw_price(current_price)
    return rounded if rounded > 0 else round_krw_price(current_price * Decimal("0.999"), "floor")


def target_price_above(target_price: Decimal, current_price: Decimal) -> Decimal:
    if target_price <= 0 or current_price <= 0:
        return Decimal("0")
    rounded = round_krw_price(target_price, "ceil")
    if rounded <= current_price:
        rounded = next_krw_price(current_price)
    return rounded
