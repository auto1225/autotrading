from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Deque, Iterable, Mapping
import json

from .database import utc_now_iso


ZERO = Decimal("0")
MONEY_QUANTUM = Decimal("1")
PCT_QUANTUM = Decimal("0.01")
SMALL_VOLUME = Decimal("0.00000000000000000001")


@dataclass
class _OpenSignal:
    market: str
    entry_at: str
    entry_price: Decimal
    spent_krw: Decimal
    fee_krw: Decimal
    original_volume: Decimal
    remaining_volume: Decimal


@dataclass(frozen=True)
class ReverseSignalTrade:
    market: str
    entry_at: str
    exit_at: str
    entry_price: Decimal
    exit_price: Decimal
    notional_krw: Decimal
    closed_volume: Decimal
    long_realized_pnl_krw: Decimal
    long_equity_pnl_krw: Decimal
    long_equity_pct: Decimal
    reverse_pnl_krw: Decimal
    reverse_pct: Decimal
    entry_fee_krw: Decimal
    exit_fee_krw: Decimal
    reverse_entry_fee_krw: Decimal
    reverse_exit_fee_krw: Decimal

    @property
    def long_win(self) -> bool:
        return self.long_equity_pnl_krw > ZERO

    @property
    def reverse_win(self) -> bool:
        return self.reverse_pnl_krw > ZERO

    @property
    def price_direction(self) -> str:
        if self.exit_price < self.entry_price:
            return "down"
        if self.exit_price > self.entry_price:
            return "up"
        return "flat"

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "entryAt": self.entry_at,
            "exitAt": self.exit_at,
            "entryPrice": _plain(self.entry_price),
            "exitPrice": _plain(self.exit_price),
            "notionalKrw": _money(self.notional_krw),
            "closedVolume": _plain(self.closed_volume),
            "longRealizedPnlKrw": _money(self.long_realized_pnl_krw),
            "longEquityPnlKrw": _money(self.long_equity_pnl_krw),
            "longEquityPct": _pct(self.long_equity_pct),
            "longWin": self.long_win,
            "reversePnlKrw": _money(self.reverse_pnl_krw),
            "reversePct": _pct(self.reverse_pct),
            "reverseWin": self.reverse_win,
            "priceDirection": self.price_direction,
            "entryFeeKrw": _money(self.entry_fee_krw),
            "exitFeeKrw": _money(self.exit_fee_krw),
            "reverseEntryFeeKrw": _money(self.reverse_entry_fee_krw),
            "reverseExitFeeKrw": _money(self.reverse_exit_fee_krw),
        }


@dataclass(frozen=True)
class ReverseSignalReport:
    generated_at: str
    source: str
    fee_rate: Decimal
    trade_count: int
    long_wins: int
    long_losses: int
    long_win_rate_pct: Decimal
    long_realized_total_pnl_krw: Decimal
    long_equity_total_pnl_krw: Decimal
    reverse_wins: int
    reverse_losses: int
    reverse_win_rate_pct: Decimal
    reverse_total_pnl_krw: Decimal
    reverse_edge_krw: Decimal
    price_down_count: int
    price_flat_count: int
    price_up_count: int
    open_signal_count: int
    unmatched_sell_count: int
    trades: tuple[ReverseSignalTrade, ...]
    open_signals: tuple[_OpenSignal, ...]

    @property
    def verdict(self) -> str:
        if self.trade_count == 0:
            return "no-closed-trades"
        if self.reverse_total_pnl_krw > ZERO and self.reverse_win_rate_pct > self.long_win_rate_pct:
            return "reverse-outperformed"
        if self.reverse_total_pnl_krw > self.long_equity_total_pnl_krw:
            return "reverse-better-but-not-profitable"
        return "reverse-not-confirmed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.trade_count > 0,
            "generatedAt": self.generated_at,
            "source": self.source,
            "feeRate": _plain(self.fee_rate),
            "verdict": self.verdict,
            "tradeCount": self.trade_count,
            "longWins": self.long_wins,
            "longLosses": self.long_losses,
            "longWinRatePct": _pct(self.long_win_rate_pct),
            "longRealizedTotalPnlKrw": _money(self.long_realized_total_pnl_krw),
            "longEquityTotalPnlKrw": _money(self.long_equity_total_pnl_krw),
            "reverseWins": self.reverse_wins,
            "reverseLosses": self.reverse_losses,
            "reverseWinRatePct": _pct(self.reverse_win_rate_pct),
            "reverseTotalPnlKrw": _money(self.reverse_total_pnl_krw),
            "reverseEdgeKrw": _money(self.reverse_edge_krw),
            "priceDownCount": self.price_down_count,
            "priceFlatCount": self.price_flat_count,
            "priceUpCount": self.price_up_count,
            "openSignalCount": self.open_signal_count,
            "unmatchedSellCount": self.unmatched_sell_count,
            "trades": [trade.to_dict() for trade in self.trades],
            "openSignals": [
                {
                    "market": signal.market,
                    "entryAt": signal.entry_at,
                    "entryPrice": _plain(signal.entry_price),
                    "notionalKrw": _money(signal.spent_krw),
                    "remainingVolume": _plain(signal.remaining_volume),
                }
                for signal in self.open_signals
            ],
        }


def load_events_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def reverse_signal_report(settings: Any, events_path: Path | None = None) -> ReverseSignalReport:
    path = events_path or Path(settings.state_file).parent / "events.jsonl"
    return reverse_signal_report_from_events(
        load_events_jsonl(path),
        fee_rate=_decimal(getattr(settings, "fee_rate", Decimal("0.0005"))),
        source=str(path),
    )


def reverse_signal_report_from_events(
    events: Iterable[Mapping[str, Any]],
    fee_rate: Decimal = Decimal("0.0005"),
    source: str = "events",
) -> ReverseSignalReport:
    open_by_market: dict[str, Deque[_OpenSignal]] = defaultdict(deque)
    trades: list[ReverseSignalTrade] = []
    unmatched_sell_count = 0

    for event in events:
        if event.get("type") != "paper_order":
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping) or payload.get("ok") is False:
            continue
        raw = payload.get("raw")
        if not isinstance(raw, Mapping):
            continue

        market = str(payload.get("market") or raw.get("market") or "")
        side = str(raw.get("side") or "")
        if not market or side not in {"bid", "ask"}:
            continue

        if side == "bid":
            entry = _entry_signal(market, _event_time(event), raw, fee_rate)
            if entry is not None:
                open_by_market[market].append(entry)
            continue

        unmatched_sell_count += _consume_sell(
            trades=trades,
            open_signals=open_by_market[market],
            event_time=_event_time(event),
            market=market,
            raw=raw,
            fee_rate=fee_rate,
        )

    open_signals = tuple(signal for queue in open_by_market.values() for signal in queue if signal.remaining_volume > ZERO)
    long_wins = sum(1 for trade in trades if trade.long_win)
    reverse_wins = sum(1 for trade in trades if trade.reverse_win)
    trade_count = len(trades)
    long_realized_total = sum((trade.long_realized_pnl_krw for trade in trades), ZERO)
    long_equity_total = sum((trade.long_equity_pnl_krw for trade in trades), ZERO)
    reverse_total = sum((trade.reverse_pnl_krw for trade in trades), ZERO)

    return ReverseSignalReport(
        generated_at=utc_now_iso(),
        source=source,
        fee_rate=fee_rate,
        trade_count=trade_count,
        long_wins=long_wins,
        long_losses=trade_count - long_wins,
        long_win_rate_pct=_rate(long_wins, trade_count),
        long_realized_total_pnl_krw=long_realized_total,
        long_equity_total_pnl_krw=long_equity_total,
        reverse_wins=reverse_wins,
        reverse_losses=trade_count - reverse_wins,
        reverse_win_rate_pct=_rate(reverse_wins, trade_count),
        reverse_total_pnl_krw=reverse_total,
        reverse_edge_krw=reverse_total - long_equity_total,
        price_down_count=sum(1 for trade in trades if trade.price_direction == "down"),
        price_flat_count=sum(1 for trade in trades if trade.price_direction == "flat"),
        price_up_count=sum(1 for trade in trades if trade.price_direction == "up"),
        open_signal_count=len(open_signals),
        unmatched_sell_count=unmatched_sell_count,
        trades=tuple(trades),
        open_signals=open_signals,
    )


def _entry_signal(
    market: str,
    event_time: str,
    raw: Mapping[str, Any],
    fee_rate: Decimal,
) -> _OpenSignal | None:
    spent_krw = _decimal(raw.get("spent_krw"))
    entry_price = _decimal(raw.get("fill_price"))
    if spent_krw <= ZERO or entry_price <= ZERO:
        return None
    fee_krw = _decimal(raw.get("fee_krw"), spent_krw * fee_rate)
    volume = _decimal(raw.get("volume"))
    if volume <= ZERO:
        volume = (spent_krw - fee_krw) / entry_price
    if volume <= ZERO:
        return None
    return _OpenSignal(
        market=market,
        entry_at=event_time,
        entry_price=entry_price,
        spent_krw=spent_krw,
        fee_krw=fee_krw,
        original_volume=volume,
        remaining_volume=volume,
    )


def _consume_sell(
    trades: list[ReverseSignalTrade],
    open_signals: Deque[_OpenSignal],
    event_time: str,
    market: str,
    raw: Mapping[str, Any],
    fee_rate: Decimal,
) -> int:
    exit_price = _decimal(raw.get("fill_price"))
    sell_volume = _decimal(raw.get("volume"))
    if exit_price <= ZERO or sell_volume <= ZERO:
        return 0

    remaining = sell_volume
    sell_fee = _decimal(raw.get("fee_krw"), sell_volume * exit_price * fee_rate)
    sell_received = _decimal(raw.get("received_krw"), sell_volume * exit_price - sell_fee)
    sell_realized = _decimal(raw.get("realized_pnl_krw"))
    unmatched = 0

    while remaining > SMALL_VOLUME:
        if not open_signals:
            unmatched = 1
            break

        signal = open_signals[0]
        close_volume = min(remaining, signal.remaining_volume)
        exit_ratio = close_volume / sell_volume
        entry_ratio = close_volume / signal.original_volume

        entry_spent = signal.spent_krw * entry_ratio
        entry_fee = signal.fee_krw * entry_ratio
        exit_fee = sell_fee * exit_ratio
        exit_received = sell_received * exit_ratio
        long_realized = sell_realized * exit_ratio if sell_realized != ZERO else (
            close_volume * exit_price - exit_fee - close_volume * signal.entry_price
        )
        long_equity = exit_received - entry_spent

        reverse_qty = entry_spent / signal.entry_price
        reverse_entry_fee = entry_fee
        reverse_exit_notional = reverse_qty * exit_price
        reverse_exit_fee = reverse_exit_notional * fee_rate
        reverse_pnl = entry_spent - reverse_entry_fee - reverse_exit_notional - reverse_exit_fee

        trades.append(
            ReverseSignalTrade(
                market=market,
                entry_at=signal.entry_at,
                exit_at=event_time,
                entry_price=signal.entry_price,
                exit_price=exit_price,
                notional_krw=entry_spent,
                closed_volume=close_volume,
                long_realized_pnl_krw=long_realized,
                long_equity_pnl_krw=long_equity,
                long_equity_pct=_percent(long_equity, entry_spent),
                reverse_pnl_krw=reverse_pnl,
                reverse_pct=_percent(reverse_pnl, entry_spent),
                entry_fee_krw=entry_fee,
                exit_fee_krw=exit_fee,
                reverse_entry_fee_krw=reverse_entry_fee,
                reverse_exit_fee_krw=reverse_exit_fee,
            )
        )

        signal.remaining_volume -= close_volume
        remaining -= close_volume
        if signal.remaining_volume <= SMALL_VOLUME:
            open_signals.popleft()

    return unmatched


def _event_time(event: Mapping[str, Any]) -> str:
    return str(event.get("time") or event.get("created_at") or "")


def _decimal(value: Any, default: Decimal = ZERO) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _rate(count: int, total: int) -> Decimal:
    if total <= 0:
        return ZERO
    return Decimal(count) / Decimal(total) * Decimal("100")


def _percent(value: Decimal, base: Decimal) -> Decimal:
    if base <= ZERO:
        return ZERO
    return value / base * Decimal("100")


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _money(value: Decimal) -> str:
    return format(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP), "f")


def _pct(value: Decimal) -> str:
    return format(value.quantize(PCT_QUANTUM, rounding=ROUND_HALF_UP), "f")
