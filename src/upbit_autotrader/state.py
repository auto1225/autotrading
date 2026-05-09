from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from json import JSONDecodeError
from pathlib import Path
from typing import Any
import json
import uuid


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _safe_json_payload(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return None
        payload = json.loads(raw)
    except (OSError, JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


@dataclass
class PaperState:
    cash_krw: Decimal
    position_volume: Decimal = Decimal("0")
    avg_entry_price: Decimal = Decimal("0")
    realized_pnl_krw: Decimal = Decimal("0")
    fees_paid_krw: Decimal = Decimal("0")
    order_count: int = 0
    last_order_at: str | None = None

    def position_value(self, current_price: Decimal) -> Decimal:
        return self.position_volume * current_price

    def equity(self, current_price: Decimal) -> Decimal:
        return self.cash_krw + self.position_value(current_price)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash_krw": str(self.cash_krw),
            "position_volume": str(self.position_volume),
            "avg_entry_price": str(self.avg_entry_price),
            "realized_pnl_krw": str(self.realized_pnl_krw),
            "fees_paid_krw": str(self.fees_paid_krw),
            "order_count": self.order_count,
            "last_order_at": self.last_order_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PaperState":
        return cls(
            cash_krw=_decimal(payload.get("cash_krw"), "1000000"),
            position_volume=_decimal(payload.get("position_volume")),
            avg_entry_price=_decimal(payload.get("avg_entry_price")),
            realized_pnl_krw=_decimal(payload.get("realized_pnl_krw")),
            fees_paid_krw=_decimal(payload.get("fees_paid_krw")),
            order_count=int(payload.get("order_count", 0)),
            last_order_at=payload.get("last_order_at"),
        )


class JsonStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, default_cash_krw: Decimal) -> PaperState:
        if not self.path.exists():
            return PaperState(cash_krw=default_cash_krw)
        payload = _safe_json_payload(self.path)
        if payload is None:
            return PaperState(cash_krw=default_cash_krw)
        return PaperState.from_dict(payload)

    def save(self, state: PaperState) -> None:
        _atomic_write_json(self.path, state.to_dict())


@dataclass
class PortfolioPosition:
    volume: Decimal = Decimal("0")
    avg_entry_price: Decimal = Decimal("0")

    def value(self, current_price: Decimal) -> Decimal:
        return self.volume * current_price

    def to_dict(self) -> dict[str, str]:
        return {
            "volume": str(self.volume),
            "avg_entry_price": str(self.avg_entry_price),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PortfolioPosition":
        return cls(
            volume=_decimal(payload.get("volume")),
            avg_entry_price=_decimal(payload.get("avg_entry_price")),
        )


@dataclass
class PortfolioState:
    cash_krw: Decimal
    positions: dict[str, PortfolioPosition]
    realized_pnl_krw: Decimal = Decimal("0")
    realized_pnl_by_market: dict[str, Decimal] | None = None
    fees_paid_krw: Decimal = Decimal("0")
    order_count: int = 0
    last_order_at: str | None = None
    risk_date: str = ""
    daily_realized_pnl_krw: Decimal = Decimal("0")
    daily_order_count: int = 0
    last_order_by_market: dict[str, str] | None = None
    last_order_reason_by_market: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.risk_date:
            self.risk_date = current_utc_date()
        if self.last_order_by_market is None:
            self.last_order_by_market = {}
        if self.last_order_reason_by_market is None:
            self.last_order_reason_by_market = {}
        if self.realized_pnl_by_market is None:
            self.realized_pnl_by_market = {}

    def position(self, market: str) -> PortfolioPosition:
        return self.positions.setdefault(market, PortfolioPosition())

    def position_value(self, market: str, current_price: Decimal) -> Decimal:
        return self.position(market).value(current_price)

    def total_position_value(self, prices: dict[str, Decimal]) -> Decimal:
        total = Decimal("0")
        for market, position in self.positions.items():
            total += position.value(prices.get(market, Decimal("0")))
        return total

    def equity(self, prices: dict[str, Decimal]) -> Decimal:
        return self.cash_krw + self.total_position_value(prices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash_krw": str(self.cash_krw),
            "positions": {
                market: position.to_dict()
                for market, position in sorted(self.positions.items())
                if position.volume != 0 or position.avg_entry_price != 0
            },
            "realized_pnl_krw": str(self.realized_pnl_krw),
            "realized_pnl_by_market": {
                market: str(value)
                for market, value in sorted((self.realized_pnl_by_market or {}).items())
                if value != 0
            },
            "fees_paid_krw": str(self.fees_paid_krw),
            "order_count": self.order_count,
            "last_order_at": self.last_order_at,
            "risk_date": self.risk_date,
            "daily_realized_pnl_krw": str(self.daily_realized_pnl_krw),
            "daily_order_count": self.daily_order_count,
            "last_order_by_market": dict(sorted((self.last_order_by_market or {}).items())),
            "last_order_reason_by_market": {
                market: reason
                for market, reason in sorted((self.last_order_reason_by_market or {}).items())
                if reason
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PortfolioState":
        positions_payload = payload.get("positions", {})
        if not isinstance(positions_payload, dict):
            positions_payload = {}
        return cls(
            cash_krw=_decimal(payload.get("cash_krw"), "1000000"),
            positions={
                str(market): PortfolioPosition.from_dict(position)
                for market, position in positions_payload.items()
                if isinstance(position, dict)
            },
            realized_pnl_krw=_decimal(payload.get("realized_pnl_krw")),
            realized_pnl_by_market={
                str(market): _decimal(value)
                for market, value in dict(payload.get("realized_pnl_by_market", {})).items()
            },
            fees_paid_krw=_decimal(payload.get("fees_paid_krw")),
            order_count=int(payload.get("order_count", 0)),
            last_order_at=payload.get("last_order_at"),
            risk_date=str(payload.get("risk_date") or current_utc_date()),
            daily_realized_pnl_krw=_decimal(payload.get("daily_realized_pnl_krw")),
            daily_order_count=int(payload.get("daily_order_count", 0)),
            last_order_by_market={
                str(market): str(last_order_at)
                for market, last_order_at in dict(payload.get("last_order_by_market", {})).items()
            },
            last_order_reason_by_market={
                str(market): str(reason)
                for market, reason in dict(payload.get("last_order_reason_by_market", {})).items()
            },
        )


class JsonPortfolioStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, default_cash_krw: Decimal) -> PortfolioState:
        if not self.path.exists():
            return PortfolioState(cash_krw=default_cash_krw, positions={})
        payload = _safe_json_payload(self.path)
        if payload is None:
            return PortfolioState(cash_krw=default_cash_krw, positions={})
        if "positions" not in payload and "position_volume" in payload:
            migrated = PaperState.from_dict(payload)
            positions = {}
            if migrated.position_volume != 0:
                positions["KRW-BTC"] = PortfolioPosition(
                    volume=migrated.position_volume,
                    avg_entry_price=migrated.avg_entry_price,
                )
            return PortfolioState(
                cash_krw=migrated.cash_krw,
                positions=positions,
                realized_pnl_krw=migrated.realized_pnl_krw,
                fees_paid_krw=migrated.fees_paid_krw,
                order_count=migrated.order_count,
                last_order_at=migrated.last_order_at,
                risk_date=current_utc_date(),
                daily_realized_pnl_krw=Decimal("0"),
                daily_order_count=0,
                last_order_by_market={},
                last_order_reason_by_market={},
            )
        return PortfolioState.from_dict(payload)

    def save(self, state: PortfolioState) -> None:
        _atomic_write_json(self.path, state.to_dict())


def current_utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def reset_daily_counters_if_needed(state: PortfolioState) -> None:
    today = current_utc_date()
    if state.risk_date != today:
        state.risk_date = today
        state.daily_realized_pnl_krw = Decimal("0")
        state.daily_order_count = 0
