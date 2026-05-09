from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal


Action = Literal["buy", "sell", "hold"]
OrderSide = Literal["bid", "ask"]
OrderType = Literal["limit", "price", "market", "best"]


def decimal_to_str(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def to_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


@dataclass(frozen=True)
class Candle:
    market: str
    candle_date_time_utc: str
    candle_date_time_kst: str
    opening_price: Decimal
    high_price: Decimal
    low_price: Decimal
    trade_price: Decimal
    timestamp: int
    candle_acc_trade_price: Decimal
    candle_acc_trade_volume: Decimal

    @classmethod
    def from_upbit(cls, payload: dict[str, Any]) -> "Candle":
        return cls(
            market=str(payload["market"]),
            candle_date_time_utc=str(payload["candle_date_time_utc"]),
            candle_date_time_kst=str(payload["candle_date_time_kst"]),
            opening_price=to_decimal(payload["opening_price"]),
            high_price=to_decimal(payload["high_price"]),
            low_price=to_decimal(payload["low_price"]),
            trade_price=to_decimal(payload["trade_price"]),
            timestamp=int(payload["timestamp"]),
            candle_acc_trade_price=to_decimal(payload["candle_acc_trade_price"]),
            candle_acc_trade_volume=to_decimal(payload["candle_acc_trade_volume"]),
        )


@dataclass(frozen=True)
class Signal:
    action: Action
    market: str
    reference_price: Decimal
    reason: str
    strength: Decimal = Decimal("1")


@dataclass(frozen=True)
class OrderIntent:
    market: str
    side: OrderSide
    ord_type: OrderType
    reason: str
    price: Decimal | None = None
    volume: Decimal | None = None
    identifier: str | None = None
    time_in_force: str | None = None
    smp_type: str | None = None

    def to_upbit_body(self) -> dict[str, str]:
        body: dict[str, str] = {
            "market": self.market,
            "side": self.side,
            "ord_type": self.ord_type,
        }
        if self.price is not None:
            body["price"] = decimal_to_str(self.price)
        if self.volume is not None:
            body["volume"] = decimal_to_str(self.volume)
        if self.identifier:
            body["identifier"] = self.identifier
        if self.time_in_force:
            body["time_in_force"] = self.time_in_force
        if self.smp_type:
            body["smp_type"] = self.smp_type
        return body


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str
    intent: OrderIntent | None = None


@dataclass(frozen=True)
class OrderResult:
    ok: bool
    mode: Literal["paper", "live"]
    message: str
    raw: dict[str, Any]
