from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Literal
import json
import time
import uuid

from .binance_client import BinanceFuturesClient, candle_from_binance
from .config import TradingSettings
from .alex_strategy import AlexTechniqueSignal, evaluate_alex_techniques
from .maeuknam_strategy import MaeuknamTechniqueSignal, clamp, evaluate_maeuknam_techniques
from .maeuknam_strategy import (
    CARD_EVIDENCE_CONFIDENCE_TARGET,
    CARD_EVIDENCE_MAX_THRESHOLD_PREMIUM,
    CARD_EVIDENCE_SUPPORT_TARGET,
)
from .models import decimal_to_str, to_decimal


FuturesSide = Literal["LONG", "SHORT"]

DEFAULT_WALLET_BALANCE_USDT = Decimal("1000")
DEFAULT_PAPER_SIDE: FuturesSide = "SHORT"
STRATEGY_SIDE = "CONTRARIAN"
MAEUKNAM_STRATEGY_SIDE = "MAEUKNAM_CARDS"
ALEX_STRATEGY_SIDE = "ALEX_METHOD"
MAEUKNAM_DIRECTION_SIDE = "CARD_DIRECTION"
MANUAL_HOLD_EXIT_BASIS = "manual_hold_until_switch"
AUTO_RELEASED_MANUAL_EXIT_BASIS = "auto_released_manual_hold"
DEFAULT_LEVERAGE = Decimal("10")
MAEUKNAM_BTC_ONLY_SYMBOL = "BTCUSDT"
MAEUKNAM_EXPERIMENT_SYMBOLS = (MAEUKNAM_BTC_ONLY_SYMBOL,)
ALEX_EXPERIMENT_SYMBOLS = (MAEUKNAM_BTC_ONLY_SYMBOL,)
MAEUKNAM_EXPERIMENT_LEVERAGE = Decimal("100")
MAEUKNAM_EXPERIMENT_MAX_OPEN_POSITIONS = 1
DEFAULT_DEPLOY_PCT = Decimal("1")
MAEUKNAM_MAX_OPEN_FEE_EQUITY_PCT = Decimal("0.5")
DEFAULT_FEE_RATE = Decimal("0.0004")
ALEX_ZERO_FEE_EXPERIMENT = True
TAKE_PROFIT_MARGIN_PCT = Decimal("3.0")
STOP_LOSS_MARGIN_PCT = Decimal("-1.6")
MAX_OPEN_POSITIONS = 4
MIN_ENTRY_SCORE = Decimal("1.20")
MIN_TOP_UP_MARGIN_USDT = Decimal("25")
FUTURES_DEEP_ANALYSIS_LIMIT = 60
FUTURES_QUOTE_VOLUME_BASE_USDT = Decimal("10000000")
FUTURES_TRADE_COUNT_BASE = Decimal("100000")
ENTRY_COOLDOWN_SECONDS = 0
MAX_SESSION_ORDER_COUNT = 0
MAX_FEE_DRAG_PCT = Decimal("0")
MIN_DEEP_MOMENTUM_PCT = Decimal("0.12")
MIN_DEEP_RANGE_PCT = Decimal("0.35")
MAEUKNAM_CONFIRMATION_CYCLES = 1
MAEUKNAM_WATCH_STALE_SECONDS = Decimal("900")
MAEUKNAM_MIN_TARGET_FEE_MULTIPLE = Decimal("3")
MAEUKNAM_MIN_HOLD_SECONDS = Decimal("120")
MAEUKNAM_ENTRY_COOLDOWN_SECONDS = 0
MAEUKNAM_REENTRY_COOLDOWN_SECONDS = 0
MAEUKNAM_MAX_SESSION_ORDER_COUNT = 48
MAEUKNAM_MAX_FEE_DRAG_PCT = Decimal("0")
MAEUKNAM_RELAXED_ENTRY_THRESHOLD = Decimal("0.51")
MAEUKNAM_TEST_TRADE_MODE = True
MAEUKNAM_TEST_ENTRY_THRESHOLD = Decimal("0.50")
MAEUKNAM_TEST_MAX_FEE_DRAG_PCT = Decimal("10")
ALEX_MAX_FEE_DRAG_PCT = Decimal("0")
ALEX_MIN_ENTRY_MARGIN_PCT = Decimal("0.10")
ALEX_MAX_ENTRY_MARGIN_PCT = Decimal("0.30")
ALEX_FULL_SIZE_SCORE = Decimal("0.80")
ALEX_MIN_TARGET_MOVE_PCT = Decimal("0.35")
ALEX_MIN_SWITCH_TARGET_MOVE_PCT = Decimal("0.45")
ALEX_SWITCH_EXTRA_FEE_MULTIPLE = Decimal("1")
MAEUKNAM_FEE_DRAG_THROTTLE_PCT = Decimal("5")
MAEUKNAM_FEE_DRAG_MIN_CARD_SCORE = Decimal("0.60")
MAEUKNAM_FEE_DRAG_MIN_CONFIRMATIONS = 2
ALEX_FEE_DRAG_MIN_CONFIRMATIONS = MAEUKNAM_CONFIRMATION_CYCLES
ALEX_FEE_DRAG_MIN_CARD_SCORE = Decimal("0.74")
ALEX_FEE_DRAG_MIN_TARGET_MOVE_PCT = Decimal("0.55")
MAEUKNAM_PROFIT_LOCK_SHARE = Decimal("0.55")
ALEX_RUNNER_PROFIT_LOCK_SHARE = Decimal("0.45")
ALEX_MIN_STOP_DISTANCE_PCT = Decimal("0.12")
ALEX_MAX_OPPOSED_TIMEFRAMES = 1
ALEX_WATCH_PROBE_ENABLED = True
ALEX_WATCH_PROBE_MIN_TARGET_MOVE_PCT = Decimal("0.08")
MAEUKNAM_INVERSE_MIN_REWARD_RISK = Decimal("1.2")
MAEUKNAM_KLINE_INTERVAL = "1m"
MAEUKNAM_KLINE_FETCH_LIMIT = 1500
MAEUKNAM_CLOSED_CANDLE_LIMIT = 1440
BINANCE_KLINE_PAGE_LIMIT = 1500
ALEX_KLINE_INTERVAL = "1m"
ALEX_KLINE_FETCH_LIMIT = 1500
ALEX_CONTEXT_INTERVALS = ("12h", "30m", "1d")
MAEUKNAM_CONTEXT_KLINE_LIMIT = 5000
MAEUKNAM_CONTEXT_CACHE_SECONDS = 900
MAEUKNAM_CONTEXT_INTERVALS = ("1d", "1w", "1M")
MAEUKNAM_CONTEXT_SCORE_WEIGHT = Decimal("0.06")
MAEUKNAM_AGENCY_MAX_OPPOSED_TIMEFRAMES = 2
MAEUKNAM_INVERSE_AGENCY_ENTRY_ENABLED = False
MAEUKNAM_EXECUTION_PROOF_ENABLED = True
MAEUKNAM_EXECUTION_PROOF_MOVE_PCT = Decimal("0")
_KLINE_HISTORY_CACHE: dict[tuple[str, str, str, int], tuple[float, list[list[Any]]]] = {}


def opposite_futures_side(side: FuturesSide) -> FuturesSide:
    return "SHORT" if side == "LONG" else "LONG"


def contrarian_execution_side(analysis_side: FuturesSide | None) -> FuturesSide | None:
    return opposite_futures_side(analysis_side) if analysis_side is not None else None


def maeuknam_futures_mode(settings: TradingSettings) -> bool:
    return settings.strategy_name == "maeuknam_cards"


def alex_futures_mode(settings: TradingSettings) -> bool:
    return settings.strategy_name == "alex_method"


def card_futures_mode(settings: TradingSettings) -> bool:
    return maeuknam_futures_mode(settings) or alex_futures_mode(settings)


def futures_strategy_side(settings: TradingSettings) -> str:
    if maeuknam_futures_mode(settings):
        return MAEUKNAM_STRATEGY_SIDE
    if alex_futures_mode(settings):
        return ALEX_STRATEGY_SIDE
    return STRATEGY_SIDE


def futures_paper_leverage(maeuknam_only: bool = False) -> Decimal:
    return MAEUKNAM_EXPERIMENT_LEVERAGE if maeuknam_only else DEFAULT_LEVERAGE


def futures_paper_max_open_positions(maeuknam_only: bool = False) -> int:
    return MAEUKNAM_EXPERIMENT_MAX_OPEN_POSITIONS if maeuknam_only else MAX_OPEN_POSITIONS


def maeuknam_experiment_symbols(focus_symbols: tuple[str, ...] = ()) -> tuple[str, ...]:
    return tuple(dict.fromkeys([*MAEUKNAM_EXPERIMENT_SYMBOLS, *focus_symbols]))


def maeuknam_signal_futures_side(signal: MaeuknamTechniqueSignal) -> FuturesSide | None:
    side = signal.direction.upper()
    return side if side in {"LONG", "SHORT"} else None


def alex_signal_futures_side(signal: AlexTechniqueSignal) -> FuturesSide | None:
    side = signal.direction.upper()
    return side if side in {"LONG", "SHORT"} else None


def relax_maeuknam_futures_signal(signal: MaeuknamTechniqueSignal) -> MaeuknamTechniqueSignal:
    evidence_floor = MAEUKNAM_RELAXED_ENTRY_THRESHOLD + signal.card_evidence_threshold_premium
    if MAEUKNAM_TEST_TRADE_MODE:
        evidence_floor = MAEUKNAM_TEST_ENTRY_THRESHOLD
    threshold = min(signal.entry_threshold, evidence_floor)
    entry_allowed = signal.score >= threshold and not signal.hard_blocks
    if threshold == signal.entry_threshold and entry_allowed == signal.entry_allowed:
        return signal
    reason = (
        f"{signal.reason}, futures "
        f"{'test-trade' if MAEUKNAM_TEST_TRADE_MODE else 'evidence-balanced'} threshold "
        f"{decimal_to_str(signal.score)}/{decimal_to_str(threshold)}"
    )
    return replace(
        signal,
        entry_threshold=threshold,
        entry_allowed=entry_allowed,
        reason=reason,
    )


def maeuknam_signal_price(candidate: FuturesPaperCandidate, key: str) -> Decimal:
    return card_signal_price(candidate, key)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def futures_paper_state_path(settings: TradingSettings) -> Path:
    return settings.state_file.parent / "binance_futures_paper_state.json"


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
        serialized = json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True)
        json.loads(serialized)
        temp_path.write_text(serialized, encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


@dataclass
class FuturesPaperPosition:
    symbol: str
    side: FuturesSide
    quantity: Decimal
    entry_price: Decimal
    leverage: Decimal
    margin_usdt: Decimal
    opened_at: str
    reason: str = ""
    stop_price: Decimal = Decimal("0")
    target1_price: Decimal = Decimal("0")
    target2_price: Decimal = Decimal("0")
    exit_basis: str = ""
    technique_id: str = ""
    technique_name: str = ""

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        if self.side == "LONG":
            return (current_price - self.entry_price) * self.quantity
        return (self.entry_price - current_price) * self.quantity

    def price_move_pct(self, current_price: Decimal) -> Decimal:
        if self.entry_price <= 0:
            return Decimal("0")
        if self.side == "LONG":
            return (current_price - self.entry_price) / self.entry_price * Decimal("100")
        return (self.entry_price - current_price) / self.entry_price * Decimal("100")

    def notional(self, current_price: Decimal) -> Decimal:
        return self.quantity * current_price

    def return_on_margin_pct(self, current_price: Decimal) -> Decimal:
        if self.margin_usdt <= 0:
            return Decimal("0")
        return self.unrealized_pnl(current_price) / self.margin_usdt * Decimal("100")

    def take_profit_price(self) -> Decimal:
        return self.target2_price if self.target2_price > 0 else self.target1_price

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": decimal_to_str(self.quantity),
            "entryPrice": decimal_to_str(self.entry_price),
            "leverage": decimal_to_str(self.leverage),
            "marginUsdt": decimal_to_str(self.margin_usdt),
            "openedAt": self.opened_at,
            "reason": self.reason,
            "stopPrice": decimal_to_str(self.stop_price),
            "target1Price": decimal_to_str(self.target1_price),
            "target2Price": decimal_to_str(self.target2_price),
            "exitBasis": self.exit_basis,
            "techniqueId": self.technique_id,
            "techniqueName": self.technique_name,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FuturesPaperPosition":
        return cls(
            symbol=str(payload.get("symbol", "")),
            side="SHORT" if str(payload.get("side", "")).upper() == "SHORT" else "LONG",
            quantity=_decimal(payload.get("quantity")),
            entry_price=_decimal(payload.get("entryPrice")),
            leverage=_decimal(payload.get("leverage"), str(DEFAULT_LEVERAGE)),
            margin_usdt=_decimal(payload.get("marginUsdt")),
            opened_at=str(payload.get("openedAt") or utc_now()),
            reason=str(payload.get("reason") or ""),
            stop_price=_decimal(payload.get("stopPrice")),
            target1_price=_decimal(payload.get("target1Price")),
            target2_price=_decimal(payload.get("target2Price")),
            exit_basis=str(payload.get("exitBasis") or ""),
            technique_id=str(payload.get("techniqueId") or ""),
            technique_name=str(payload.get("techniqueName") or ""),
        )


@dataclass
class MaeuknamWatchState:
    symbol: str
    side: FuturesSide
    technique_id: str
    first_seen_at: str
    last_seen_at: str
    confirmations: int = 1
    score: Decimal = Decimal("0")
    target_move_pct: Decimal = Decimal("0")
    last_candle_timestamp: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "techniqueId": self.technique_id,
            "firstSeenAt": self.first_seen_at,
            "lastSeenAt": self.last_seen_at,
            "confirmations": self.confirmations,
            "score": decimal_to_str(self.score),
            "targetMovePct": decimal_to_str(self.target_move_pct),
            "lastCandleTimestamp": self.last_candle_timestamp,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MaeuknamWatchState":
        side: FuturesSide = "SHORT" if str(payload.get("side", "")).upper() == "SHORT" else "LONG"
        return cls(
            symbol=str(payload.get("symbol") or ""),
            side=side,
            technique_id=str(payload.get("techniqueId") or ""),
            first_seen_at=str(payload.get("firstSeenAt") or utc_now()),
            last_seen_at=str(payload.get("lastSeenAt") or utc_now()),
            confirmations=int(payload.get("confirmations", 1) or 1),
            score=_decimal(payload.get("score")),
            target_move_pct=_decimal(payload.get("targetMovePct")),
            last_candle_timestamp=int(payload.get("lastCandleTimestamp") or 0),
        )


@dataclass
class FuturesPaperState:
    wallet_balance_usdt: Decimal
    positions: dict[str, FuturesPaperPosition]
    realized_pnl_usdt: Decimal = Decimal("0")
    gross_realized_pnl_usdt: Decimal = Decimal("0")
    fees_paid_usdt: Decimal = Decimal("0")
    open_fees_paid_usdt: Decimal = Decimal("0")
    close_fees_paid_usdt: Decimal = Decimal("0")
    order_count: int = 0
    last_order_at: str | None = None
    manual_action: str | None = None
    maeuknam_watchlist: dict[str, MaeuknamWatchState] = field(default_factory=dict)
    maeuknam_cooldowns: dict[str, str] = field(default_factory=dict)
    last_closed_candles: dict[str, str] = field(default_factory=dict)

    def used_margin(self) -> Decimal:
        return sum((position.margin_usdt for position in self.positions.values()), Decimal("0"))

    def unrealized_pnl(self, prices: dict[str, Decimal]) -> Decimal:
        total = Decimal("0")
        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.entry_price)
            total += position.unrealized_pnl(price)
        return total

    def equity(self, prices: dict[str, Decimal]) -> Decimal:
        return self.wallet_balance_usdt + self.unrealized_pnl(prices)

    def available_balance(self, prices: dict[str, Decimal]) -> Decimal:
        return self.equity(prices) - self.used_margin()

    def to_dict(self) -> dict[str, Any]:
        return {
            "walletBalanceUsdt": decimal_to_str(self.wallet_balance_usdt),
            "positions": {symbol: position.to_dict() for symbol, position in sorted(self.positions.items())},
            "realizedPnlUsdt": decimal_to_str(self.realized_pnl_usdt),
            "grossRealizedPnlUsdt": decimal_to_str(self.gross_realized_pnl_usdt),
            "feesPaidUsdt": decimal_to_str(self.fees_paid_usdt),
            "openFeesPaidUsdt": decimal_to_str(self.open_fees_paid_usdt),
            "closeFeesPaidUsdt": decimal_to_str(self.close_fees_paid_usdt),
            "orderCount": self.order_count,
            "lastOrderAt": self.last_order_at,
            "manualAction": self.manual_action,
            "maeuknamWatchlist": {key: value.to_dict() for key, value in sorted(self.maeuknam_watchlist.items())},
            "maeuknamCooldowns": dict(sorted(self.maeuknam_cooldowns.items())),
            "lastClosedCandles": dict(sorted(self.last_closed_candles.items())),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FuturesPaperState":
        positions_payload = payload.get("positions", {})
        if not isinstance(positions_payload, dict):
            positions_payload = {}
        watchlist_payload = payload.get("maeuknamWatchlist", {})
        if not isinstance(watchlist_payload, dict):
            watchlist_payload = {}
        cooldowns_payload = payload.get("maeuknamCooldowns", {})
        if not isinstance(cooldowns_payload, dict):
            cooldowns_payload = {}
        last_closed_payload = payload.get("lastClosedCandles", {})
        if not isinstance(last_closed_payload, dict):
            last_closed_payload = {}
        close_fees_paid = _decimal(payload.get("closeFeesPaidUsdt"))
        open_fees_paid = _decimal(payload.get("openFeesPaidUsdt"), str(max(_decimal(payload.get("feesPaidUsdt")) - close_fees_paid, Decimal("0"))))
        return cls(
            wallet_balance_usdt=_decimal(payload.get("walletBalanceUsdt"), str(DEFAULT_WALLET_BALANCE_USDT)),
            positions={
                str(symbol): FuturesPaperPosition.from_dict(position)
                for symbol, position in positions_payload.items()
                if isinstance(position, dict)
            },
            realized_pnl_usdt=_decimal(payload.get("realizedPnlUsdt")),
            gross_realized_pnl_usdt=_decimal(
                payload.get("grossRealizedPnlUsdt"),
                str(_decimal(payload.get("realizedPnlUsdt")) + close_fees_paid),
            ),
            fees_paid_usdt=_decimal(payload.get("feesPaidUsdt")),
            open_fees_paid_usdt=open_fees_paid,
            close_fees_paid_usdt=close_fees_paid,
            order_count=int(payload.get("orderCount", 0) or 0),
            last_order_at=payload.get("lastOrderAt"),
            manual_action=str(payload.get("manualAction") or "") or None,
            maeuknam_watchlist={
                str(key): MaeuknamWatchState.from_dict(value)
                for key, value in watchlist_payload.items()
                if isinstance(value, dict)
            },
            maeuknam_cooldowns={str(key): str(value) for key, value in cooldowns_payload.items()},
            last_closed_candles={str(key): str(value) for key, value in last_closed_payload.items()},
        )


class FuturesPaperStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, default_balance_usdt: Decimal = DEFAULT_WALLET_BALANCE_USDT) -> FuturesPaperState:
        if not self.path.exists():
            return FuturesPaperState(wallet_balance_usdt=default_balance_usdt, positions={})
        payload = _safe_json_payload(self.path)
        if payload is None:
            return FuturesPaperState(wallet_balance_usdt=default_balance_usdt, positions={})
        return FuturesPaperState.from_dict(payload)

    def save(self, state: FuturesPaperState) -> None:
        _atomic_write_json(self.path, state.to_dict())


def reset_futures_paper_state(
    settings: TradingSettings,
    balance_usdt: Decimal = DEFAULT_WALLET_BALANCE_USDT,
) -> FuturesPaperState:
    state = FuturesPaperState(wallet_balance_usdt=balance_usdt, positions={})
    FuturesPaperStateStore(futures_paper_state_path(settings)).save(state)
    return state


@dataclass(frozen=True)
class FuturesPaperCandidate:
    symbol: str
    side: FuturesSide
    price: Decimal
    score: Decimal
    momentum_5m_pct: Decimal
    momentum_15m_pct: Decimal
    range_15m_pct: Decimal
    volume_ratio: Decimal
    reason: str
    analysis_depth: str = "candle_1m"
    price_change_24h_pct: Decimal = Decimal("0")
    range_24h_pct: Decimal = Decimal("0")
    quote_volume_usdt: Decimal = Decimal("0")
    trade_count: Decimal = Decimal("0")
    universe_source: str = "configured"
    entry_allowed: bool = False
    entry_block_reason: str = "waiting for regime confirmation"
    analysis_side: FuturesSide | None = None
    execution_side: FuturesSide | None = None
    contrarian: bool = False
    maeuknam_signal: dict[str, Any] | None = None
    alex_signal: dict[str, Any] | None = None
    entry_stage: str = "signal"
    confirmation_count: int = 0
    target_move_pct: Decimal = Decimal("0")
    fee_safety_move_pct: Decimal = Decimal("0")
    cooldown_key: str = ""
    latest_candle_timestamp: int = 0
    closed_candle_count: int = 0
    timeframe_context: dict[str, Any] | None = None
    direction_diagnostics: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        analysis_side = self.analysis_side or self.side
        execution_side = self.execution_side or self.side
        return {
            "symbol": self.symbol,
            "side": self.side,
            "analysisSide": analysis_side,
            "executionSide": execution_side,
            "contrarian": "true" if self.contrarian else "false",
            "price": decimal_to_str(self.price),
            "score": decimal_to_str(self.score),
            "momentum5mPct": decimal_to_str(self.momentum_5m_pct),
            "momentum15mPct": decimal_to_str(self.momentum_15m_pct),
            "range15mPct": decimal_to_str(self.range_15m_pct),
            "volumeRatio": decimal_to_str(self.volume_ratio),
            "reason": self.reason,
            "analysisDepth": self.analysis_depth,
            "priceChange24hPct": decimal_to_str(self.price_change_24h_pct),
            "range24hPct": decimal_to_str(self.range_24h_pct),
            "quoteVolumeUsdt": decimal_to_str(self.quote_volume_usdt),
            "tradeCount": decimal_to_str(self.trade_count),
            "universeSource": self.universe_source,
            "entryAllowed": "true" if self.entry_allowed else "false",
            "entryBlockReason": self.entry_block_reason,
            "maeuknamSignal": self.maeuknam_signal or {},
            "alexSignal": self.alex_signal or {},
            "entryStage": self.entry_stage,
            "confirmationCount": str(self.confirmation_count),
            "targetMovePct": decimal_to_str(self.target_move_pct),
            "feeSafetyMovePct": decimal_to_str(self.fee_safety_move_pct),
            "cooldownKey": self.cooldown_key,
            "latestCandleTimestamp": str(self.latest_candle_timestamp),
            "closedCandleCount": str(self.closed_candle_count),
            "timeframeContext": self.timeframe_context or {},
            "directionDiagnostics": self.direction_diagnostics or {},
        }


def card_signal_payload(candidate: FuturesPaperCandidate) -> dict[str, Any]:
    if isinstance(candidate.maeuknam_signal, dict) and candidate.maeuknam_signal:
        return candidate.maeuknam_signal
    if isinstance(candidate.alex_signal, dict) and candidate.alex_signal:
        return candidate.alex_signal
    return {}


def card_signal_price(candidate: FuturesPaperCandidate, key: str) -> Decimal:
    return _decimal(card_signal_payload(candidate).get(key))


def candidate_card_label(candidate: FuturesPaperCandidate | None) -> str:
    if candidate is not None and candidate.alex_signal:
        return "Alex method"
    return "Maeuknam card"


def maeuknam_round_trip_fee_move_pct() -> Decimal:
    return DEFAULT_FEE_RATE * Decimal("2") * Decimal("100")


def maeuknam_fee_safety_move_pct() -> Decimal:
    return maeuknam_round_trip_fee_move_pct() * MAEUKNAM_MIN_TARGET_FEE_MULTIPLE


def alex_fee_rate() -> Decimal:
    return Decimal("0") if ALEX_ZERO_FEE_EXPERIMENT else DEFAULT_FEE_RATE


def alex_round_trip_fee_move_pct() -> Decimal:
    return alex_fee_rate() * Decimal("2") * Decimal("100")


def alex_fee_safety_move_pct() -> Decimal:
    return alex_round_trip_fee_move_pct() * MAEUKNAM_MIN_TARGET_FEE_MULTIPLE


def futures_candidate_fee_rate(candidate: FuturesPaperCandidate) -> Decimal:
    return alex_fee_rate() if candidate.alex_signal else DEFAULT_FEE_RATE


def futures_position_fee_rate(position: FuturesPaperPosition) -> Decimal:
    return alex_fee_rate() if position.exit_basis.startswith("alex") else DEFAULT_FEE_RATE


def maeuknam_fee_budgeted_entry_margin(equity: Decimal, leverage: Decimal) -> Decimal:
    if equity <= 0 or leverage <= 0 or DEFAULT_FEE_RATE <= 0:
        return Decimal("0")
    fee_budget = equity * MAEUKNAM_MAX_OPEN_FEE_EQUITY_PCT / Decimal("100")
    return fee_budget / (leverage * DEFAULT_FEE_RATE)


def maeuknam_target_price_from_signal(signal: MaeuknamTechniqueSignal) -> Decimal:
    return signal.target2_price if signal.target2_price > 0 else signal.target1_price


def maeuknam_target_move_pct(side: FuturesSide, entry_price: Decimal, target_price: Decimal) -> Decimal:
    if entry_price <= 0 or target_price <= 0:
        return Decimal("0")
    if side == "LONG" and target_price > entry_price:
        return (target_price - entry_price) / entry_price * Decimal("100")
    if side == "SHORT" and target_price < entry_price:
        return (entry_price - target_price) / entry_price * Decimal("100")
    return Decimal("0")


def maeuknam_fee_safe_target_price(
    side: FuturesSide,
    entry_price: Decimal,
    target_price: Decimal,
    required_move_pct: Decimal | None = None,
) -> Decimal:
    if entry_price <= 0 or target_price <= 0:
        return target_price
    required_move = maeuknam_fee_safety_move_pct() if required_move_pct is None else required_move_pct
    fee_floor_delta = entry_price * required_move / Decimal("100")
    if side == "LONG":
        return max(target_price, entry_price + fee_floor_delta)
    return min(target_price, entry_price - fee_floor_delta)


def maeuknam_fee_gate(
    signal: MaeuknamTechniqueSignal,
    side: FuturesSide,
    entry_price: Decimal,
) -> tuple[bool, str, Decimal, Decimal]:
    target_price = maeuknam_target_price_from_signal(signal)
    target_move = maeuknam_target_move_pct(side, entry_price, target_price)
    required_move = maeuknam_fee_safety_move_pct()
    if target_move <= 0:
        return (
            False,
            f"Maeuknam card target is not favorable from current entry price {decimal_to_str(entry_price)}",
            target_move,
            required_move,
        )
    if target_move < required_move:
        return (
            True,
            (
                f"Maeuknam card target move {decimal_to_str(target_move)}% below "
                f"fee safety {decimal_to_str(required_move)}%; "
                "entry allowed with fee-floor target extension"
            ),
            target_move,
            required_move,
        )
    return True, "entry allowed", target_move, required_move


def alex_single_fee_move_pct() -> Decimal:
    return alex_fee_rate() * Decimal("100")


def alex_switch_required_move_pct() -> Decimal:
    fee_floor = alex_fee_safety_move_pct() + alex_single_fee_move_pct() * ALEX_SWITCH_EXTRA_FEE_MULTIPLE
    return max(fee_floor, ALEX_MIN_SWITCH_TARGET_MOVE_PCT)


def alex_fee_gate(
    signal: AlexTechniqueSignal,
    side: FuturesSide,
    entry_price: Decimal,
    required_move_pct: Decimal | None = None,
) -> tuple[bool, str, Decimal, Decimal]:
    target_price = maeuknam_target_price_from_signal(signal)
    target_move = maeuknam_target_move_pct(side, entry_price, target_price)
    required_move = max(
        alex_fee_safety_move_pct() if required_move_pct is None else required_move_pct,
        ALEX_MIN_TARGET_MOVE_PCT,
    )
    if target_move <= 0:
        return (
            False,
            f"Alex method target is not favorable from current entry price {decimal_to_str(entry_price)}",
            target_move,
            required_move,
        )
    if target_move < required_move:
        return (
            False,
            (
                f"Alex method target move {decimal_to_str(target_move)}% is below "
                f"required fee-safe move {decimal_to_str(required_move)}%"
            ),
            target_move,
            required_move,
        )
    return True, "entry allowed", target_move, required_move


def alex_entry_margin_pct(candidate: FuturesPaperCandidate) -> Decimal:
    if candidate.entry_stage == "watch_probe":
        return ALEX_MIN_ENTRY_MARGIN_PCT
    signal = card_signal_payload(candidate)
    threshold = _decimal(signal.get("entryThreshold"), "0.52")
    score_span = max(ALEX_FULL_SIZE_SCORE - threshold, Decimal("0.01"))
    strength = clamp((candidate.score - threshold) / score_span)
    return ALEX_MIN_ENTRY_MARGIN_PCT + (ALEX_MAX_ENTRY_MARGIN_PCT - ALEX_MIN_ENTRY_MARGIN_PCT) * strength


def order_minute_bucket(value: str | None = None) -> str:
    if value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.now(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()


def same_minute_reentry_block_reason(state: FuturesPaperState, symbol: str) -> str | None:
    closed_bucket = state.last_closed_candles.get(symbol)
    if closed_bucket and closed_bucket == order_minute_bucket():
        return f"same 1m candle re-entry blocked after close for {symbol}"
    return None


def alex_switch_cost_block_reason(
    position: FuturesPaperPosition,
    candidate: FuturesPaperCandidate,
    price: Decimal,
) -> str | None:
    if not candidate.alex_signal or candidate.side == position.side:
        return None
    signal = AlexTechniqueSignal(
        technique_id=str(candidate.alex_signal.get("techniqueId") or ""),
        technique_name=str(candidate.alex_signal.get("techniqueName") or ""),
        direction=str(candidate.alex_signal.get("direction") or candidate.side),
        score=_decimal(candidate.alex_signal.get("score")),
        entry_threshold=_decimal(candidate.alex_signal.get("entryThreshold"), "0.52"),
        watch_threshold=_decimal(candidate.alex_signal.get("watchThreshold"), "0.42"),
        entry_allowed=bool(candidate.alex_signal.get("entryAllowed")),
        hard_blocks=tuple(candidate.alex_signal.get("hardBlocks") or ()),
        entry_price=_decimal(candidate.alex_signal.get("entryPrice"), str(candidate.price)),
        stop_price=_decimal(candidate.alex_signal.get("stopPrice")),
        target1_price=_decimal(candidate.alex_signal.get("target1Price")),
        target2_price=_decimal(candidate.alex_signal.get("target2Price")),
        support_price=_decimal(candidate.alex_signal.get("supportPrice")),
        resistance_price=_decimal(candidate.alex_signal.get("resistancePrice")),
        risk_pct=_decimal(candidate.alex_signal.get("riskPct")),
        reward_risk=_decimal(candidate.alex_signal.get("rewardRisk")),
        features={},
        reason=str(candidate.alex_signal.get("reason") or candidate.reason),
    )
    _, _, target_move, required_move = alex_fee_gate(
        signal,
        candidate.side,
        price,
        alex_switch_required_move_pct(),
    )
    if target_move < required_move:
        return (
            f"Alex switch to {candidate.side} blocked: target move {decimal_to_str(target_move)}% "
            f"< switch cost floor {decimal_to_str(required_move)}%"
        )
    return None


def maeuknam_candidate_technique_id(candidate: FuturesPaperCandidate) -> str:
    return str(card_signal_payload(candidate).get("techniqueId") or "")


def maeuknam_candidate_technique_name(candidate: FuturesPaperCandidate) -> str:
    return str(card_signal_payload(candidate).get("techniqueName") or "")


def maeuknam_cooldown_key(symbol: str, side: FuturesSide, technique_id: str) -> str:
    return f"{symbol}:{side}:{technique_id or 'unknown'}"


def maeuknam_candidate_cooldown_key(candidate: FuturesPaperCandidate) -> str:
    return maeuknam_cooldown_key(candidate.symbol, candidate.side, maeuknam_candidate_technique_id(candidate))


def maeuknam_candidate_agency_block_reason(candidate: FuturesPaperCandidate) -> str | None:
    if not candidate.maeuknam_signal:
        return None
    if candidate.closed_candle_count < MAEUKNAM_CLOSED_CANDLE_LIMIT and candidate.latest_candle_timestamp > 1_000_000_000_000:
        return (
            "investment agency data veto: "
            f"closed 1m candles {candidate.closed_candle_count}/{MAEUKNAM_CLOSED_CANDLE_LIMIT}"
        )
    context = candidate.timeframe_context or {}
    missing = [
        interval
        for interval in MAEUKNAM_CONTEXT_INTERVALS
        if not isinstance(context.get(interval), dict) or _decimal(context.get(interval, {}).get("count")) <= 0
    ]
    if missing:
        return f"investment agency data veto: missing higher timeframe context {','.join(missing)}"
    opposed = sum(
        1
        for payload in context.values()
        if isinstance(payload, dict) and str(payload.get("alignment") or "") == "opposed"
    )
    if opposed >= MAEUKNAM_AGENCY_MAX_OPPOSED_TIMEFRAMES:
        return (
            "investment agency veto: "
            f"{opposed}/{len(MAEUKNAM_CONTEXT_INTERVALS)} higher timeframes oppose card direction"
        )
    return None


def maeuknam_candidate_opposed_timeframe_count(candidate: FuturesPaperCandidate) -> int:
    context = candidate.timeframe_context or {}
    return sum(
        1
        for payload in context.values()
        if isinstance(payload, dict) and str(payload.get("alignment") or "") == "opposed"
    )


def maeuknam_inverse_agency_candidate(
    candidate: FuturesPaperCandidate,
    agency_reason: str,
) -> FuturesPaperCandidate | None:
    if not MAEUKNAM_INVERSE_AGENCY_ENTRY_ENABLED:
        return None
    if not candidate.maeuknam_signal or "higher timeframes oppose" not in agency_reason:
        return None
    if maeuknam_candidate_opposed_timeframe_count(candidate) < MAEUKNAM_AGENCY_MAX_OPPOSED_TIMEFRAMES:
        return None
    entry_price = candidate.price
    if entry_price <= 0:
        return None

    inverse_side = opposite_futures_side(candidate.side)
    original_stop = maeuknam_signal_price(candidate, "stopPrice")
    original_target1 = maeuknam_signal_price(candidate, "target1Price")
    original_target2 = maeuknam_signal_price(candidate, "target2Price")
    inverse_target = original_stop
    inverse_stop = original_target1 if original_target1 > 0 else original_target2
    if inverse_side == "LONG":
        if inverse_stop <= 0 or inverse_stop >= entry_price or inverse_target <= entry_price:
            return None
    else:
        if inverse_stop <= entry_price or inverse_target <= 0 or inverse_target >= entry_price:
            return None
    fee_safe_inverse_target = maeuknam_fee_safe_target_price(inverse_side, entry_price, inverse_target)
    if maeuknam_inverse_reward_risk_block_reason(
        inverse_side,
        entry_price,
        inverse_stop,
        fee_safe_inverse_target,
    ):
        return None

    signal = dict(candidate.maeuknam_signal)
    original_id = str(signal.get("techniqueId") or maeuknam_candidate_technique_id(candidate) or "unknown")
    original_name = str(signal.get("techniqueName") or maeuknam_candidate_technique_name(candidate) or original_id)
    inverse_id = f"inverse_agency_{original_id}"
    signal.update(
        {
            "techniqueId": inverse_id,
            "techniqueName": f"Agency inverse {original_name}",
            "direction": inverse_side,
            "entryAllowed": True,
            "hardBlocks": [],
            "entryPrice": decimal_to_str(entry_price),
            "stopPrice": decimal_to_str(inverse_stop),
            "target1Price": decimal_to_str(inverse_target),
            "target2Price": decimal_to_str(inverse_target),
            "reason": (
                f"Maeuknam agency inverse: original {candidate.side} card was vetoed because "
                f"{agency_reason}; execute {inverse_side} only as card-failure test"
            ),
            "originalTechniqueId": original_id,
            "originalDirection": candidate.side,
        }
    )
    target_move_pct = maeuknam_target_move_pct(inverse_side, entry_price, inverse_target)
    reason = (
        f"maeuknam-card-inverse: {original_name} {candidate.side} failed agency check; "
        f"HTF opposition flips execution to {inverse_side}; stop {decimal_to_str(inverse_stop)}, "
        f"target {decimal_to_str(inverse_target)}"
    )
    return replace(
        candidate,
        side=inverse_side,
        analysis_side=candidate.side,
        execution_side=inverse_side,
        contrarian=False,
        reason=reason,
        entry_allowed=True,
        entry_block_reason=(
            f"Maeuknam inverse agency entry: {agency_reason}; "
            f"execute {inverse_side} as card-failure confirmation"
        ),
        maeuknam_signal=signal,
        entry_stage="inverse_agency",
        target_move_pct=target_move_pct,
        cooldown_key=maeuknam_cooldown_key(candidate.symbol, inverse_side, inverse_id),
        confirmation_count=max(1, candidate.confirmation_count),
    )


def maeuknam_reward_risk(side: FuturesSide, entry_price: Decimal, stop_price: Decimal, target_price: Decimal) -> Decimal:
    if side == "LONG":
        reward = target_price - entry_price
        risk = entry_price - stop_price
    else:
        reward = entry_price - target_price
        risk = stop_price - entry_price
    if reward <= 0 or risk <= 0:
        return Decimal("0")
    return reward / risk


def maeuknam_inverse_reward_risk_block_reason(
    side: FuturesSide,
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
) -> str | None:
    reward_risk = maeuknam_reward_risk(side, entry_price, stop_price, target_price)
    if reward_risk < MAEUKNAM_INVERSE_MIN_REWARD_RISK:
        return (
            "Maeuknam inverse card reward/risk "
            f"{decimal_to_str(reward_risk)} below {decimal_to_str(MAEUKNAM_INVERSE_MIN_REWARD_RISK)}"
        )
    return None


def is_maeuknam_inverse_position(position: FuturesPaperPosition) -> bool:
    return position.technique_id.startswith("inverse_agency_") or "maeuknam-card-inverse" in position.reason


def maeuknam_symbol_side_cooldown_key(symbol: str, side: FuturesSide) -> str:
    return f"{symbol}:{side}:*"


def maeuknam_cooldown_until() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=MAEUKNAM_REENTRY_COOLDOWN_SECONDS)).isoformat()


def analyze_futures_symbol(client: BinanceFuturesClient, symbol: str) -> FuturesPaperCandidate:
    rows = client.klines(symbol, interval="1m", limit=30)
    if len(rows) < 16:
        raise ValueError(f"{symbol} needs at least 16 one-minute candles")
    closes = [to_decimal(row[4]) for row in rows]
    highs = [to_decimal(row[2]) for row in rows]
    lows = [to_decimal(row[3]) for row in rows]
    volumes = [to_decimal(row[5]) for row in rows]
    price = closes[-1]
    momentum_5 = pct_change(closes[-6], price)
    momentum_15 = pct_change(closes[-16], price)
    recent_high = max(highs[-15:])
    recent_low = min(lows[-15:])
    range_15 = pct_change(recent_low, recent_high) if recent_low > 0 else Decimal("0")
    recent_volume = sum(volumes[-5:], Decimal("0")) / Decimal("5")
    base_volume = sum(volumes[-25:-5], Decimal("0")) / Decimal("20")
    volume_ratio = recent_volume / base_volume if base_volume > 0 else Decimal("1")
    directional_score = momentum_5 * Decimal("0.65") + momentum_15 * Decimal("0.35")
    side: FuturesSide = "SHORT"
    bearish_score = max(-directional_score, Decimal("0"))
    bullish_score = max(directional_score, Decimal("0"))
    rollover_score = max(momentum_15, Decimal("0")) if momentum_5 < 0 else Decimal("0")
    acceleration_score = max(momentum_5 - momentum_15, Decimal("0")) if momentum_5 > 0 else Decimal("0")
    short_score = (
        bearish_score * Decimal("2.4")
        + rollover_score * Decimal("0.55")
        + range_15 * Decimal("0.20")
        + min(volume_ratio, Decimal("3")) * Decimal("0.2")
    )
    long_score = (
        bullish_score * Decimal("2.2")
        + acceleration_score * Decimal("0.45")
        + range_15 * Decimal("0.25")
        + min(volume_ratio, Decimal("3")) * Decimal("0.2")
    )
    if long_score > short_score:
        side = "LONG"
        score = long_score
        direction_label = "adaptive-long"
    else:
        score = short_score
        direction_label = "adaptive-short"
    reason = (
        f"{direction_label}: 5m {decimal_to_str(momentum_5)}%, "
        f"15m {decimal_to_str(momentum_15)}%, range {decimal_to_str(range_15)}%, "
        f"volume {decimal_to_str(volume_ratio)}x"
    )
    return FuturesPaperCandidate(
        symbol=symbol,
        side=side,
        price=price,
        score=score,
        momentum_5m_pct=momentum_5,
        momentum_15m_pct=momentum_15,
        range_15m_pct=range_15,
        volume_ratio=volume_ratio,
        reason=reason,
    )


def binance_kline_close_time_ms(row: list[Any]) -> int:
    try:
        return int(row[6])
    except Exception:
        return 0


def closed_binance_klines(
    rows: list[list[Any]],
    now_ms: int | None = None,
    limit: int = MAEUKNAM_CLOSED_CANDLE_LIMIT,
) -> list[list[Any]]:
    now = utc_now_ms() if now_ms is None else now_ms
    closed: list[list[Any]] = []
    for row in rows:
        close_time = binance_kline_close_time_ms(row)
        # Synthetic test candles use 0 as close time; treat those as already closed.
        if close_time <= 0 or close_time < now:
            closed.append(row)
    return closed[-limit:] if limit > 0 else closed


def fetch_closed_binance_klines_history(
    client: BinanceFuturesClient,
    symbol: str,
    interval: str,
    limit: int,
    cache_seconds: int = 0,
) -> list[list[Any]]:
    target_limit = max(1, int(limit))
    client_cache_scope = getattr(client, "base_url", None)
    cache_key = (str(client_cache_scope), symbol.upper(), interval, target_limit) if client_cache_scope else None
    now = time.time()
    cached = _KLINE_HISTORY_CACHE.get(cache_key) if cache_key is not None else None
    if cache_key is not None and cache_seconds > 0 and cached is not None and cached[0] > now:
        return list(cached[1])

    rows_by_open_time: dict[int, list[Any]] = {}
    end_time: int | None = None
    while len(rows_by_open_time) < target_limit:
        page_size = min(BINANCE_KLINE_PAGE_LIMIT, target_limit - len(rows_by_open_time))
        if end_time is None:
            raw_page = client.klines(symbol, interval=interval, limit=page_size)
        else:
            raw_page = client.klines(symbol, interval=interval, limit=page_size, end_time=end_time)
        if not raw_page:
            break

        closed_page = closed_binance_klines(raw_page, limit=page_size)
        for row in closed_page:
            if row:
                rows_by_open_time[int(row[0])] = row

        first_open_time = min(int(row[0]) for row in raw_page if row)
        next_end_time = first_open_time - 1
        if len(raw_page) < page_size or end_time == next_end_time:
            break
        end_time = next_end_time

    rows = [rows_by_open_time[key] for key in sorted(rows_by_open_time)][-target_limit:]
    if cache_key is not None and cache_seconds > 0:
        _KLINE_HISTORY_CACHE[cache_key] = (now + cache_seconds, rows)
    return rows


def maeuknam_timeframe_payload(interval: str, side: FuturesSide, candles: list[Any]) -> dict[str, Any]:
    if not candles:
        return {
            "interval": interval,
            "count": "0",
            "alignment": "unavailable",
            "alignmentScore": "0",
        }

    closes = [candle.trade_price for candle in candles]
    highs = [candle.high_price for candle in candles]
    lows = [candle.low_price for candle in candles]
    first_close = closes[0]
    last_close = closes[-1]
    trend_pct = pct_change(first_close, last_close)
    recent_window = min(len(closes), 20)
    recent_trend_pct = pct_change(closes[-recent_window], last_close) if recent_window > 1 else trend_pct
    high = max(highs)
    low = min(lows)
    range_position_pct = Decimal("50")
    if high > low:
        range_position_pct = (last_close - low) / (high - low) * Decimal("100")
        range_position_pct = min(Decimal("100"), max(Decimal("0"), range_position_pct))

    direction_pct = recent_trend_pct if recent_trend_pct != 0 else trend_pct
    alignment_score = Decimal("0")
    if direction_pct > 0:
        alignment_score = Decimal("1") if side == "LONG" else Decimal("-1")
    elif direction_pct < 0:
        alignment_score = Decimal("1") if side == "SHORT" else Decimal("-1")
    alignment = "neutral"
    if alignment_score > 0:
        alignment = "aligned"
    elif alignment_score < 0:
        alignment = "opposed"

    return {
        "interval": interval,
        "count": str(len(candles)),
        "firstOpenTimestamp": str(int(candles[0].timestamp)),
        "latestOpenTimestamp": str(int(candles[-1].timestamp)),
        "firstClose": decimal_to_str(first_close),
        "lastClose": decimal_to_str(last_close),
        "trendPct": decimal_to_str(trend_pct),
        "recentTrendPct": decimal_to_str(recent_trend_pct),
        "rangePositionPct": decimal_to_str(range_position_pct),
        "alignment": alignment,
        "alignmentScore": decimal_to_str(alignment_score),
    }


def maeuknam_multi_timeframe_context(
    client: BinanceFuturesClient,
    symbol: str,
    side: FuturesSide,
) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for interval in MAEUKNAM_CONTEXT_INTERVALS:
        try:
            rows = fetch_closed_binance_klines_history(
                client,
                symbol,
                interval,
                limit=MAEUKNAM_CONTEXT_KLINE_LIMIT,
                cache_seconds=MAEUKNAM_CONTEXT_CACHE_SECONDS,
            )
            candles = [candle_from_binance(symbol, row) for row in rows]
            context[interval] = maeuknam_timeframe_payload(interval, side, candles)
        except Exception as exc:
            context[interval] = {
                "interval": interval,
                "count": "0",
                "alignment": "error",
                "alignmentScore": "0",
                "error": str(exc),
            }
    return context


def maeuknam_context_alignment_score(timeframe_context: dict[str, Any]) -> Decimal:
    scores: list[Decimal] = []
    for payload in timeframe_context.values():
        if isinstance(payload, dict) and "alignmentScore" in payload:
            scores.append(_decimal(payload.get("alignmentScore")))
    if not scores:
        return Decimal("0")
    return sum(scores, Decimal("0")) / Decimal(len(scores))


def apply_maeuknam_timeframe_context(
    signal: MaeuknamTechniqueSignal,
    timeframe_context: dict[str, Any],
) -> MaeuknamTechniqueSignal:
    alignment_score = maeuknam_context_alignment_score(timeframe_context)
    if alignment_score == 0 and not timeframe_context:
        return signal

    adjustment = alignment_score * MAEUKNAM_CONTEXT_SCORE_WEIGHT
    adjusted_score = clamp(signal.score + adjustment)
    entry_allowed = adjusted_score >= signal.entry_threshold and not signal.hard_blocks
    features = {
        **signal.features,
        "multi_timeframe_alignment_score": alignment_score,
        "multi_timeframe_score_adjustment": adjustment,
    }
    reason = (
        f"{signal.reason}, HTF alignment {decimal_to_str(alignment_score)} "
        f"adj {decimal_to_str(adjustment)}"
    )
    return replace(
        signal,
        score=adjusted_score,
        entry_allowed=entry_allowed,
        features=features,
        reason=reason,
    )


def maeuknam_signal_is_fee_safe(
    symbol: str,
    signal: MaeuknamTechniqueSignal,
    price: Decimal,
) -> tuple[bool, FuturesSide | None, str, Decimal, Decimal]:
    signal_side = maeuknam_signal_futures_side(signal)
    entry_allowed = signal_side is not None and signal.entry_allowed
    block_reason = maeuknam_entry_block_reason(signal)
    target_move_pct = Decimal("0")
    fee_safety_move_pct = maeuknam_fee_safety_move_pct()
    if entry_allowed and signal_side is not None:
        entry_allowed, block_reason, target_move_pct, fee_safety_move_pct = maeuknam_fee_gate(
            signal,
            signal_side,
            price,
        )
    return entry_allowed, signal_side, block_reason, target_move_pct, fee_safety_move_pct


def maeuknam_historical_confirmation_count(
    symbol: str,
    candles: list[Any],
    current_signal: MaeuknamTechniqueSignal,
    current_side: FuturesSide,
    timeframe_context: dict[str, Any] | None = None,
) -> int:
    confirmations = 0
    for offset in range(MAEUKNAM_CONFIRMATION_CYCLES):
        end = len(candles) - offset
        if end < 30:
            break
        window = candles[:end]
        signal = current_signal
        if offset:
            try:
                historical_signal = evaluate_maeuknam_techniques(window, allowed_directions=(current_side,))
            except Exception:
                break
            if historical_signal is None:
                break
            signal = apply_maeuknam_timeframe_context(historical_signal, timeframe_context or {})
            signal = relax_maeuknam_futures_signal(signal)
        if signal.technique_id != current_signal.technique_id:
            break
        entry_allowed, side, _, _, _ = maeuknam_signal_is_fee_safe(symbol, signal, window[-1].trade_price)
        if side != current_side or not entry_allowed:
            break
        confirmations += 1
    return confirmations


def analyze_maeuknam_futures_symbol(client: BinanceFuturesClient, symbol: str) -> FuturesPaperCandidate:
    rows = closed_binance_klines(
        client.klines(symbol, interval=MAEUKNAM_KLINE_INTERVAL, limit=MAEUKNAM_KLINE_FETCH_LIMIT)
    )
    candles = [candle_from_binance(symbol, row) for row in rows]
    if len(candles) < 30:
        raise ValueError(f"{symbol} needs at least 30 one-minute candles for Maeuknam cards")

    closes = [candle.trade_price for candle in candles]
    highs = [candle.high_price for candle in candles]
    lows = [candle.low_price for candle in candles]
    volumes = [candle.candle_acc_trade_volume for candle in candles]
    price = closes[-1]
    momentum_5 = pct_change(closes[-6], price) if len(closes) >= 6 else Decimal("0")
    momentum_15 = pct_change(closes[-16], price) if len(closes) >= 16 else Decimal("0")
    recent_high = max(highs[-15:])
    recent_low = min(lows[-15:])
    range_15 = pct_change(recent_low, recent_high) if recent_low > 0 else Decimal("0")
    recent_volume = sum(volumes[-5:], Decimal("0")) / Decimal("5")
    base_volume = sum(volumes[-25:-5], Decimal("0")) / Decimal("20") if len(volumes) >= 25 else Decimal("0")
    volume_ratio = recent_volume / base_volume if base_volume > 0 else Decimal("1")
    latest_candle_timestamp = int(candles[-1].timestamp)
    closed_candle_count = len(candles)

    direction_diagnostics: dict[str, Any] = {}
    direction_candidates: list[FuturesPaperCandidate] = []
    for direction in ("LONG", "SHORT"):
        signal = evaluate_maeuknam_techniques(candles, allowed_directions=(direction,))
        if signal is None:
            direction_diagnostics[direction] = {
                "direction": direction,
                "entryAllowed": False,
                "entryStage": "unavailable",
                "score": "0",
                "blockReason": "no usable Maeuknam card signal",
            }
            continue
        signal_side = maeuknam_signal_futures_side(signal)
        candidate_side: FuturesSide = signal_side or ("SHORT" if direction == "SHORT" else "LONG")
        timeframe_context = maeuknam_multi_timeframe_context(client, symbol, candidate_side)
        signal = apply_maeuknam_timeframe_context(signal, timeframe_context)
        signal = relax_maeuknam_futures_signal(signal)
        entry_allowed, signal_side, block_reason, target_move_pct, fee_safety_move_pct = maeuknam_signal_is_fee_safe(
            symbol,
            signal,
            price,
        )
        candidate_side = signal_side or candidate_side
        entry_stage = "card"
        if entry_allowed:
            historical_confirmations = maeuknam_historical_confirmation_count(
                symbol,
                candles,
                signal,
                candidate_side,
                timeframe_context,
            )
            entry_allowed = historical_confirmations >= MAEUKNAM_CONFIRMATION_CYCLES
            if entry_allowed:
                entry_stage = "entry"
                block_reason = (
                    f"Maeuknam confirmed {historical_confirmations}/{MAEUKNAM_CONFIRMATION_CYCLES}; "
                    "card-only entry allowed; fee-floor target extension will be used"
                )
            else:
                entry_stage = "historical"
                block_reason = f"Maeuknam confirmation {historical_confirmations}/{MAEUKNAM_CONFIRMATION_CYCLES}"
        else:
            historical_confirmations = 0
            if "fee safety" in block_reason or "fee-safe" in block_reason:
                entry_stage = "fee_gate"
        direction_diagnostics[direction] = {
            "direction": candidate_side,
            "techniqueId": signal.technique_id,
            "techniqueName": signal.technique_name,
            "score": decimal_to_str(signal.score),
            "entryThreshold": decimal_to_str(signal.entry_threshold),
            "entryAllowed": entry_allowed,
            "entryStage": entry_stage,
            "confirmationCount": str(historical_confirmations),
            "targetMovePct": decimal_to_str(target_move_pct),
            "feeSafetyMovePct": decimal_to_str(fee_safety_move_pct),
            "blockReason": block_reason,
            "reason": signal.reason,
        }
        direction_candidates.append(
            FuturesPaperCandidate(
                symbol=symbol,
                side=candidate_side,
                price=price,
                score=signal.score * Decimal("2"),
                momentum_5m_pct=momentum_5,
                momentum_15m_pct=momentum_15,
                range_15m_pct=range_15,
                volume_ratio=volume_ratio,
                reason=maeuknam_futures_reason(signal),
                analysis_depth="maeuknam_card_1m_htf",
                universe_source="configured_maeuknam_cards",
                entry_allowed=entry_allowed,
                entry_block_reason="entry allowed" if entry_allowed else block_reason,
                analysis_side=candidate_side,
                execution_side=candidate_side,
                contrarian=False,
                maeuknam_signal=signal.to_dict(),
                entry_stage=entry_stage,
                target_move_pct=target_move_pct,
                fee_safety_move_pct=fee_safety_move_pct,
                cooldown_key=maeuknam_cooldown_key(symbol, candidate_side, signal.technique_id),
                confirmation_count=historical_confirmations,
                latest_candle_timestamp=latest_candle_timestamp,
                closed_candle_count=closed_candle_count,
                timeframe_context=timeframe_context,
                direction_diagnostics=direction_diagnostics,
            )
        )

    if not direction_candidates:
        return FuturesPaperCandidate(
            symbol=symbol,
            side="LONG",
            price=price,
            score=Decimal("0"),
            momentum_5m_pct=momentum_5,
            momentum_15m_pct=momentum_15,
            range_15m_pct=range_15,
            volume_ratio=volume_ratio,
            reason="maeuknam-card: no usable card signal",
            analysis_depth="maeuknam_card_1m_htf",
            universe_source="configured_maeuknam_cards",
            entry_allowed=False,
            entry_block_reason="maeuknam card unavailable",
            analysis_side="LONG",
            execution_side="LONG",
            contrarian=False,
            latest_candle_timestamp=latest_candle_timestamp,
            closed_candle_count=closed_candle_count,
            direction_diagnostics=direction_diagnostics,
        )

    entry_candidates = [candidate for candidate in direction_candidates if candidate.entry_allowed]
    selected = max(
        entry_candidates or direction_candidates,
        key=lambda candidate: (
            candidate.entry_allowed,
            candidate.confirmation_count,
            candidate.score,
            candidate.target_move_pct,
        ),
    )
    return replace(selected, direction_diagnostics=direction_diagnostics)


def maeuknam_entry_block_reason(signal: MaeuknamTechniqueSignal) -> str:
    if maeuknam_signal_futures_side(signal) is None:
        return f"maeuknam direction {signal.direction} is not supported for Binance futures paper"
    if signal.hard_blocks:
        return "; ".join(signal.hard_blocks)
    if signal.score < signal.entry_threshold:
        return f"maeuknam score {decimal_to_str(signal.score)} below {decimal_to_str(signal.entry_threshold)}"
    return "entry allowed"


def maeuknam_futures_reason(signal: MaeuknamTechniqueSignal) -> str:
    return (
        f"maeuknam-card: {signal.technique_name}, score {decimal_to_str(signal.score)}/"
        f"{decimal_to_str(signal.entry_threshold)}, stop {decimal_to_str(signal.stop_price)}, "
        f"target1 {decimal_to_str(signal.target1_price)}, target2 {decimal_to_str(signal.target2_price)}, "
        f"RR {decimal_to_str(signal.reward_risk)}"
    )


def alex_multi_timeframe_context(
    client: BinanceFuturesClient,
    symbol: str,
    side: FuturesSide,
) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for interval in ALEX_CONTEXT_INTERVALS:
        try:
            rows = fetch_closed_binance_klines_history(
                client,
                symbol,
                interval,
                limit=MAEUKNAM_CONTEXT_KLINE_LIMIT,
                cache_seconds=MAEUKNAM_CONTEXT_CACHE_SECONDS,
            )
            candles = [candle_from_binance(symbol, row) for row in rows]
            context[interval] = maeuknam_timeframe_payload(interval, side, candles)
        except Exception as exc:
            context[interval] = {
                "interval": interval,
                "count": "0",
                "alignment": "error",
                "alignmentScore": "0",
                "error": str(exc),
            }
    return context


def apply_alex_timeframe_context(
    signal: AlexTechniqueSignal,
    timeframe_context: dict[str, Any],
) -> AlexTechniqueSignal:
    alignment_score = maeuknam_context_alignment_score(timeframe_context)
    if alignment_score == 0 and not timeframe_context:
        return signal
    adjustment = alignment_score * MAEUKNAM_CONTEXT_SCORE_WEIGHT
    adjusted_score = clamp(signal.score + adjustment)
    entry_allowed = adjusted_score >= signal.entry_threshold and not signal.hard_blocks
    features = {
        **signal.features,
        "multi_timeframe_alignment_score": alignment_score,
        "multi_timeframe_score_adjustment": adjustment,
    }
    reason = (
        f"{signal.reason}, HTF alignment {decimal_to_str(alignment_score)} "
        f"adj {decimal_to_str(adjustment)}"
    )
    return replace(
        signal,
        score=adjusted_score,
        entry_allowed=entry_allowed,
        features=features,
        reason=reason,
    )


def alex_entry_block_reason(signal: AlexTechniqueSignal) -> str:
    if alex_signal_futures_side(signal) is None:
        return f"alex direction {signal.direction} is not supported for Binance futures paper"
    if signal.hard_blocks:
        return "; ".join(signal.hard_blocks)
    if signal.score < signal.entry_threshold:
        return f"alex score {decimal_to_str(signal.score)} below {decimal_to_str(signal.entry_threshold)}"
    return "entry allowed"


def alex_signal_target_move_pct(signal: AlexTechniqueSignal, side: FuturesSide, entry_price: Decimal) -> Decimal:
    target_price = maeuknam_target_price_from_signal(signal)
    return maeuknam_target_move_pct(side, entry_price, target_price)


def alex_signal_is_fee_safe(
    symbol: str,
    signal: AlexTechniqueSignal,
    price: Decimal,
) -> tuple[bool, FuturesSide | None, str, Decimal, Decimal]:
    signal_side = alex_signal_futures_side(signal)
    entry_allowed = signal_side is not None and signal.entry_allowed
    block_reason = alex_entry_block_reason(signal)
    target_move_pct = alex_signal_target_move_pct(signal, signal_side, price) if signal_side is not None else Decimal("0")
    fee_safety_move_pct = max(alex_fee_safety_move_pct(), ALEX_MIN_TARGET_MOVE_PCT)
    if entry_allowed and signal_side is not None:
        entry_allowed, block_reason, target_move_pct, fee_safety_move_pct = alex_fee_gate(
            signal,
            signal_side,
            price,
        )
    return entry_allowed, signal_side, block_reason, target_move_pct, fee_safety_move_pct


def alex_opposed_timeframe_count(timeframe_context: dict[str, Any]) -> int:
    return sum(
        1
        for payload in timeframe_context.values()
        if isinstance(payload, dict) and str(payload.get("alignment") or "") == "opposed"
    )


def alex_timeframe_veto_reason(timeframe_context: dict[str, Any]) -> str | None:
    opposed = alex_opposed_timeframe_count(timeframe_context)
    if opposed > ALEX_MAX_OPPOSED_TIMEFRAMES:
        return f"Alex HTF veto: {opposed}/{len(ALEX_CONTEXT_INTERVALS)} higher timeframes oppose entry direction"
    return None


def alex_stop_distance_block_reason(signal: AlexTechniqueSignal) -> str | None:
    side = alex_signal_futures_side(signal)
    if side is None:
        return None
    risk_pct = maeuknam_target_move_pct("SHORT" if side == "LONG" else "LONG", signal.entry_price, signal.stop_price)
    if Decimal("0") < risk_pct < ALEX_MIN_STOP_DISTANCE_PCT:
        return (
            f"Alex stop distance {decimal_to_str(risk_pct)}% below noise floor "
            f"{decimal_to_str(ALEX_MIN_STOP_DISTANCE_PCT)}%"
        )
    return None


def alex_watch_probe_block_reason(
    signal: AlexTechniqueSignal,
    side: FuturesSide,
    timeframe_context: dict[str, Any],
    target_move_pct: Decimal,
) -> str | None:
    if not ALEX_WATCH_PROBE_ENABLED:
        return "Alex watch probe disabled"
    if signal.hard_blocks:
        return "; ".join(signal.hard_blocks)
    if signal.score < signal.watch_threshold:
        return (
            f"alex score {decimal_to_str(signal.score)} below watch "
            f"{decimal_to_str(signal.watch_threshold)}"
        )
    opposed = alex_opposed_timeframe_count(timeframe_context)
    if opposed > 0:
        return f"Alex watch probe blocked: {opposed} higher timeframes oppose direction"
    stop_veto = alex_stop_distance_block_reason(signal)
    if stop_veto is not None:
        return stop_veto
    if target_move_pct < ALEX_WATCH_PROBE_MIN_TARGET_MOVE_PCT:
        return (
            f"Alex watch probe target {decimal_to_str(target_move_pct)}% below "
            f"{decimal_to_str(ALEX_WATCH_PROBE_MIN_TARGET_MOVE_PCT)}%"
        )
    return None


def alex_historical_confirmation_count(
    symbol: str,
    candles: list[Any],
    current_signal: AlexTechniqueSignal,
    current_side: FuturesSide,
    timeframe_context: dict[str, Any] | None = None,
) -> int:
    confirmations = 0
    for offset in range(MAEUKNAM_CONFIRMATION_CYCLES):
        end = len(candles) - offset
        if end < 30:
            break
        window = candles[:end]
        signal = current_signal
        if offset:
            try:
                historical_signal = evaluate_alex_techniques(window, allowed_directions=(current_side,))
            except Exception:
                break
            if historical_signal is None:
                break
            signal = apply_alex_timeframe_context(historical_signal, timeframe_context or {})
        if signal.technique_id != current_signal.technique_id:
            break
        entry_allowed, side, _, _, _ = alex_signal_is_fee_safe(symbol, signal, window[-1].trade_price)
        if side != current_side or not entry_allowed:
            break
        confirmations += 1
    return confirmations


def analyze_alex_futures_symbol(client: BinanceFuturesClient, symbol: str) -> FuturesPaperCandidate:
    rows = closed_binance_klines(
        client.klines(symbol, interval=ALEX_KLINE_INTERVAL, limit=ALEX_KLINE_FETCH_LIMIT)
    )
    candles = [candle_from_binance(symbol, row) for row in rows]
    if len(candles) < 30:
        raise ValueError(f"{symbol} needs at least 30 one-minute candles for Alex method")

    closes = [candle.trade_price for candle in candles]
    highs = [candle.high_price for candle in candles]
    lows = [candle.low_price for candle in candles]
    volumes = [candle.candle_acc_trade_volume for candle in candles]
    price = closes[-1]
    momentum_5 = pct_change(closes[-6], price) if len(closes) >= 6 else Decimal("0")
    momentum_15 = pct_change(closes[-16], price) if len(closes) >= 16 else Decimal("0")
    recent_high = max(highs[-15:])
    recent_low = min(lows[-15:])
    range_15 = pct_change(recent_low, recent_high) if recent_low > 0 else Decimal("0")
    recent_volume = sum(volumes[-5:], Decimal("0")) / Decimal("5")
    base_volume = sum(volumes[-25:-5], Decimal("0")) / Decimal("20") if len(volumes) >= 25 else Decimal("0")
    volume_ratio = recent_volume / base_volume if base_volume > 0 else Decimal("1")
    latest_candle_timestamp = int(candles[-1].timestamp)
    closed_candle_count = len(candles)

    direction_diagnostics: dict[str, Any] = {}
    direction_candidates: list[FuturesPaperCandidate] = []
    for direction in ("LONG", "SHORT"):
        signal = evaluate_alex_techniques(candles, allowed_directions=(direction,))
        if signal is None:
            direction_diagnostics[direction] = {
                "direction": direction,
                "entryAllowed": False,
                "entryStage": "unavailable",
                "score": "0",
                "blockReason": "no usable Alex method signal",
            }
            continue
        signal_side = alex_signal_futures_side(signal)
        candidate_side: FuturesSide = signal_side or ("SHORT" if direction == "SHORT" else "LONG")
        timeframe_context = alex_multi_timeframe_context(client, symbol, candidate_side)
        signal = apply_alex_timeframe_context(signal, timeframe_context)
        entry_allowed, signal_side, block_reason, target_move_pct, fee_safety_move_pct = alex_signal_is_fee_safe(
            symbol,
            signal,
            price,
        )
        candidate_side = signal_side or candidate_side
        entry_stage = "alex_card"
        if entry_allowed:
            htf_veto = alex_timeframe_veto_reason(timeframe_context)
            stop_veto = alex_stop_distance_block_reason(signal)
            if htf_veto is not None:
                entry_allowed = False
                entry_stage = "htf_veto"
                block_reason = htf_veto
            elif stop_veto is not None:
                entry_allowed = False
                entry_stage = "stop_noise"
                block_reason = stop_veto
        elif not signal.entry_allowed and signal_side is not None and not signal.hard_blocks:
            probe_block = alex_watch_probe_block_reason(signal, signal_side, timeframe_context, target_move_pct)
            if probe_block is None:
                entry_allowed = True
                entry_stage = "watch_probe"
                block_reason = (
                    f"Alex watch probe: score {decimal_to_str(signal.score)} >= watch "
                    f"{decimal_to_str(signal.watch_threshold)}, HTF aligned, target "
                    f"{decimal_to_str(target_move_pct)}%; 10% margin diagnostic entry"
                )
        if entry_allowed and entry_stage != "watch_probe":
            historical_confirmations = alex_historical_confirmation_count(
                symbol,
                candles,
                signal,
                candidate_side,
                timeframe_context,
            )
            entry_allowed = historical_confirmations >= MAEUKNAM_CONFIRMATION_CYCLES
            if entry_allowed:
                entry_stage = "entry"
                block_reason = (
                    f"Alex method confirmed {historical_confirmations}/{MAEUKNAM_CONFIRMATION_CYCLES}; "
                    "0.5/value/liquidity/4-count entry allowed"
                )
            else:
                entry_stage = "historical"
                block_reason = f"Alex method confirmation {historical_confirmations}/{MAEUKNAM_CONFIRMATION_CYCLES}"
        elif entry_allowed:
            historical_confirmations = 1
        else:
            historical_confirmations = 0
            if "fee safety" in block_reason or "fee-safe" in block_reason:
                entry_stage = "fee_gate"
        direction_diagnostics[direction] = {
            "direction": candidate_side,
            "techniqueId": signal.technique_id,
            "techniqueName": signal.technique_name,
            "score": decimal_to_str(signal.score),
            "entryThreshold": decimal_to_str(signal.entry_threshold),
            "entryAllowed": entry_allowed,
            "entryStage": entry_stage,
            "confirmationCount": str(historical_confirmations),
            "targetMovePct": decimal_to_str(target_move_pct),
            "feeSafetyMovePct": decimal_to_str(fee_safety_move_pct),
            "blockReason": block_reason,
            "reason": signal.reason,
        }
        direction_candidates.append(
            FuturesPaperCandidate(
                symbol=symbol,
                side=candidate_side,
                price=price,
                score=signal.score * Decimal("2"),
                momentum_5m_pct=momentum_5,
                momentum_15m_pct=momentum_15,
                range_15m_pct=range_15,
                volume_ratio=volume_ratio,
                reason=alex_futures_reason(signal),
                analysis_depth="alex_method_1m_htf",
                universe_source="configured_alex_method",
                entry_allowed=entry_allowed,
                entry_block_reason=block_reason if entry_stage == "watch_probe" else "entry allowed" if entry_allowed else block_reason,
                analysis_side=candidate_side,
                execution_side=candidate_side,
                contrarian=False,
                alex_signal=signal.to_dict(),
                entry_stage=entry_stage,
                target_move_pct=target_move_pct,
                fee_safety_move_pct=fee_safety_move_pct,
                cooldown_key=maeuknam_cooldown_key(symbol, candidate_side, signal.technique_id),
                confirmation_count=historical_confirmations,
                latest_candle_timestamp=latest_candle_timestamp,
                closed_candle_count=closed_candle_count,
                timeframe_context=timeframe_context,
                direction_diagnostics=direction_diagnostics,
            )
        )

    if not direction_candidates:
        return FuturesPaperCandidate(
            symbol=symbol,
            side="LONG",
            price=price,
            score=Decimal("0"),
            momentum_5m_pct=momentum_5,
            momentum_15m_pct=momentum_15,
            range_15m_pct=range_15,
            volume_ratio=volume_ratio,
            reason="alex-method: no usable signal",
            analysis_depth="alex_method_1m_htf",
            universe_source="configured_alex_method",
            entry_allowed=False,
            entry_block_reason="alex method signal unavailable",
            analysis_side="LONG",
            execution_side="LONG",
            contrarian=False,
            latest_candle_timestamp=latest_candle_timestamp,
            closed_candle_count=closed_candle_count,
            direction_diagnostics=direction_diagnostics,
        )

    entry_candidates = [candidate for candidate in direction_candidates if candidate.entry_allowed]
    selected = max(
        entry_candidates or direction_candidates,
        key=lambda candidate: (
            candidate.entry_allowed,
            candidate.confirmation_count,
            candidate.score,
            candidate.target_move_pct,
        ),
    )
    return replace(selected, direction_diagnostics=direction_diagnostics)


def alex_futures_reason(signal: AlexTechniqueSignal) -> str:
    return (
        f"alex-method: {signal.technique_name}, score {decimal_to_str(signal.score)}/"
        f"{decimal_to_str(signal.entry_threshold)}, stop {decimal_to_str(signal.stop_price)}, "
        f"target1 {decimal_to_str(signal.target1_price)}, target2 {decimal_to_str(signal.target2_price)}, "
        f"RR {decimal_to_str(signal.reward_risk)}"
    )


@dataclass(frozen=True)
class FuturesMarketRegime:
    trade_side: FuturesSide | None
    label: str
    bullish_ratio: Decimal
    bearish_ratio: Decimal
    avg_direction_pct: Decimal
    avg_context_pct: Decimal
    reason: str
    execution_side: FuturesSide | None = None

    def to_dict(self) -> dict[str, str]:
        execution_side = self.execution_side if self.execution_side is not None else contrarian_execution_side(self.trade_side)
        return {
            "tradeSide": self.trade_side or "FLAT",
            "analysisSide": self.trade_side or "FLAT",
            "executionSide": execution_side or "FLAT",
            "label": self.label,
            "bullishRatio": decimal_to_str(self.bullish_ratio),
            "bearishRatio": decimal_to_str(self.bearish_ratio),
            "avgDirectionPct": decimal_to_str(self.avg_direction_pct),
            "avgContextPct": decimal_to_str(self.avg_context_pct),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FuturesPaperCandidateScan:
    candidates: list[FuturesPaperCandidate]
    universe_count: int
    evaluated_count: int
    universe_source: str
    ticker_count: int = 0
    deep_analysis_count: int = 0
    market_regime: FuturesMarketRegime | None = None


@dataclass(frozen=True)
class FuturesSymbolUniverse:
    symbols: tuple[str, ...]
    source: str


def futures_symbol_universe(settings: TradingSettings, client: BinanceFuturesClient) -> FuturesSymbolUniverse:
    try:
        payload = client.exchange_info()
        rows = payload.get("symbols", []) if isinstance(payload, dict) else []
        symbols = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "").upper()
            if not symbol.endswith("USDT"):
                continue
            if str(row.get("quoteAsset") or "").upper() != "USDT":
                continue
            if str(row.get("contractType") or "").upper() != "PERPETUAL":
                continue
            if str(row.get("status") or "").upper() != "TRADING":
                continue
            symbols.append(symbol)
        unique = tuple(dict.fromkeys(symbols))
        if unique:
            return FuturesSymbolUniverse(unique, "binance_exchange_info_usdt_perpetual")
    except Exception:
        pass
    return FuturesSymbolUniverse(tuple(settings.binance_futures_symbols), "configured_symbols_fallback")


def analyze_futures_ticker(row: dict[str, Any], universe_source: str) -> FuturesPaperCandidate | None:
    symbol = str(row.get("symbol") or "").upper()
    price = _decimal(row.get("lastPrice") or row.get("weightedAvgPrice") or row.get("price"))
    if not symbol or price <= 0:
        return None
    change_24h = _decimal(row.get("priceChangePercent"))
    high = _decimal(row.get("highPrice"))
    low = _decimal(row.get("lowPrice"))
    range_24h = pct_change(low, high) if low > 0 else Decimal("0")
    quote_volume = _decimal(row.get("quoteVolume"))
    trade_count = _decimal(row.get("count"))
    volume_score = min(quote_volume / FUTURES_QUOTE_VOLUME_BASE_USDT, Decimal("5"))
    activity_score = min(trade_count / FUTURES_TRADE_COUNT_BASE, Decimal("3"))
    bearish_score = max(-change_24h, Decimal("0"))
    bullish_score = max(change_24h, Decimal("0"))
    short_score = (
        bearish_score * Decimal("0.45")
        + min(range_24h, Decimal("25")) * Decimal("0.04")
        + volume_score * Decimal("0.14")
        + activity_score * Decimal("0.08")
    )
    long_score = (
        bullish_score * Decimal("0.38")
        + min(range_24h, Decimal("25")) * Decimal("0.04")
        + volume_score * Decimal("0.14")
        + activity_score * Decimal("0.08")
    )
    side: FuturesSide = "LONG" if long_score > short_score else "SHORT"
    score = max(long_score, short_score)
    reason = (
        f"all-symbol 24h screen: 24h {decimal_to_str(change_24h)}%, "
        f"range {decimal_to_str(range_24h)}%, quote volume {decimal_to_str(quote_volume)} USDT, "
        f"trades {decimal_to_str(trade_count)}"
    )
    return FuturesPaperCandidate(
        symbol=symbol,
        side=side,
        price=price,
        score=score,
        momentum_5m_pct=Decimal("0"),
        momentum_15m_pct=Decimal("0"),
        range_15m_pct=Decimal("0"),
        volume_ratio=volume_score,
        reason=reason,
        analysis_depth="ticker_24h",
        price_change_24h_pct=change_24h,
        range_24h_pct=range_24h,
        quote_volume_usdt=quote_volume,
        trade_count=trade_count,
        universe_source=universe_source,
    )


def merge_deep_futures_candidate(
    deep: FuturesPaperCandidate,
    baseline: FuturesPaperCandidate | None,
    universe_source: str,
) -> FuturesPaperCandidate:
    if baseline is None:
        return replace(deep, universe_source=universe_source)
    score = deep.score + min(baseline.score, Decimal("2")) * Decimal("0.15")
    reason = (
        f"{deep.reason}; 24h {decimal_to_str(baseline.price_change_24h_pct)}%, "
        f"range {decimal_to_str(baseline.range_24h_pct)}%, "
        f"quote volume {decimal_to_str(baseline.quote_volume_usdt)} USDT"
    )
    return replace(
        deep,
        score=score,
        reason=reason,
        analysis_depth="candle_1m_plus_24h",
        price_change_24h_pct=baseline.price_change_24h_pct,
        range_24h_pct=baseline.range_24h_pct,
        quote_volume_usdt=baseline.quote_volume_usdt,
        trade_count=baseline.trade_count,
        universe_source=universe_source,
    )


def futures_candidate_direction_pct(candidate: FuturesPaperCandidate) -> Decimal:
    if candidate.analysis_depth.startswith("candle") and candidate.momentum_5m_pct != 0:
        return candidate.momentum_5m_pct
    return candidate.price_change_24h_pct


def futures_candidate_context_pct(candidate: FuturesPaperCandidate) -> Decimal:
    if candidate.analysis_depth.startswith("candle") and candidate.momentum_15m_pct != 0:
        return candidate.momentum_15m_pct
    return candidate.price_change_24h_pct


def futures_market_regime_from_candidates(candidates: list[FuturesPaperCandidate]) -> FuturesMarketRegime:
    if not candidates:
        return FuturesMarketRegime(None, "flat", Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), "no futures candidates")
    count = Decimal(len(candidates))
    direction_values = [futures_candidate_direction_pct(candidate) for candidate in candidates]
    context_values = [futures_candidate_context_pct(candidate) for candidate in candidates]
    bullish_count = sum(1 for value in direction_values if value > 0)
    bearish_count = sum(1 for value in direction_values if value < 0)
    bullish_ratio = Decimal(bullish_count) / count
    bearish_ratio = Decimal(bearish_count) / count
    avg_direction = sum(direction_values, Decimal("0")) / count
    avg_context = sum(context_values, Decimal("0")) / count
    if bullish_ratio >= Decimal("0.56") and avg_direction > Decimal("0.20"):
        trade_side: FuturesSide | None = "LONG"
        label = "long-favorable"
    elif bearish_ratio >= Decimal("0.56") and avg_direction < Decimal("-0.20"):
        trade_side = "SHORT"
        label = "short-favorable"
    else:
        trade_side = None
        label = "flat"
    reason = (
        f"adaptive futures regime: bullish={decimal_to_str(bullish_ratio)}, "
        f"bearish={decimal_to_str(bearish_ratio)}, avgDirection={decimal_to_str(avg_direction)}%, "
        f"avgContext={decimal_to_str(avg_context)}%"
    )
    return FuturesMarketRegime(trade_side, label, bullish_ratio, bearish_ratio, avg_direction, avg_context, reason)


def futures_entry_block_reason(candidate: FuturesPaperCandidate, regime: FuturesMarketRegime) -> str:
    if regime.trade_side is None:
        return f"market regime is {regime.label}; wait for directional edge"
    if candidate.side != regime.trade_side:
        return f"{candidate.side} conflicts with {regime.label}"
    if not candidate.analysis_depth.startswith("candle"):
        return "ticker-only candidate; wait for 1m candle confirmation"
    if candidate.score < MIN_ENTRY_SCORE:
        return f"score {decimal_to_str(candidate.score)} below {decimal_to_str(MIN_ENTRY_SCORE)}"
    if candidate.range_15m_pct < MIN_DEEP_RANGE_PCT:
        return f"15m range {decimal_to_str(candidate.range_15m_pct)}% below noise floor"
    if candidate.side == "LONG":
        if candidate.momentum_5m_pct <= MIN_DEEP_MOMENTUM_PCT or candidate.momentum_15m_pct <= 0:
            return "long needs positive 5m and 15m confirmation"
    else:
        if candidate.momentum_5m_pct >= -MIN_DEEP_MOMENTUM_PCT:
            return "short needs negative 5m confirmation"
        if candidate.momentum_15m_pct > 0 and candidate.price_change_24h_pct > Decimal("8"):
            return "do not short a strong 24h uptrend without deeper breakdown"
    return "entry allowed"


def apply_futures_regime_gate(
    candidates: list[FuturesPaperCandidate],
    regime: FuturesMarketRegime,
) -> list[FuturesPaperCandidate]:
    gated = []
    for candidate in candidates:
        reason = futures_entry_block_reason(candidate, regime)
        gated.append(replace(candidate, entry_allowed=reason == "entry allowed", entry_block_reason=reason))
    return gated


def apply_futures_contrarian_execution(candidates: list[FuturesPaperCandidate]) -> list[FuturesPaperCandidate]:
    converted: list[FuturesPaperCandidate] = []
    for candidate in candidates:
        analysis_side = candidate.analysis_side or candidate.side
        execution_side = opposite_futures_side(analysis_side)
        reason = (
            f"{candidate.reason}; contrarian execution: analysis {analysis_side} -> bet {execution_side}"
        )
        block_reason = candidate.entry_block_reason
        if candidate.entry_allowed:
            block_reason = f"analysis {analysis_side} allowed; execute opposite {execution_side}"
        converted.append(
            replace(
                candidate,
                side=execution_side,
                analysis_side=analysis_side,
                execution_side=execution_side,
                contrarian=True,
                reason=reason,
                entry_block_reason=block_reason,
            )
        )
    return converted


def is_entry_eligible(candidate: FuturesPaperCandidate) -> bool:
    if candidate.maeuknam_signal or candidate.alex_signal:
        return candidate.entry_allowed
    return candidate.entry_allowed and candidate.score >= MIN_ENTRY_SCORE


def maeuknam_candidate_with_entry_block(
    candidate: FuturesPaperCandidate,
    stage: str,
    reason: str,
) -> FuturesPaperCandidate:
    diagnostics = dict(candidate.direction_diagnostics or {})
    direction_payload = diagnostics.get(candidate.side)
    if isinstance(direction_payload, dict):
        updated_direction = dict(direction_payload)
        updated_direction["entryAllowed"] = False
        updated_direction["entryStage"] = stage
        updated_direction["blockReason"] = reason
        diagnostics[candidate.side] = updated_direction
    return replace(
        candidate,
        entry_allowed=False,
        entry_block_reason=reason,
        entry_stage=stage,
        direction_diagnostics=diagnostics,
    )


def maeuknam_execution_proof_block_reason(
    candidate: FuturesPaperCandidate,
    live_price: Decimal,
) -> str | None:
    if not MAEUKNAM_EXECUTION_PROOF_ENABLED or not (candidate.maeuknam_signal or candidate.alex_signal):
        return None
    label = candidate_card_label(candidate)
    if live_price <= 0:
        return f"{label} execution proof blocked: live Binance price is unavailable"

    reference_price = candidate.price
    proof_move_pct = MAEUKNAM_EXECUTION_PROOF_MOVE_PCT
    require_live_direction_confirmation = bool(candidate.maeuknam_signal) and not candidate.alex_signal
    if reference_price > 0 and require_live_direction_confirmation:
        required_delta = reference_price * proof_move_pct / Decimal("100")
        if candidate.side == "LONG" and live_price < reference_price + required_delta:
            return (
                f"{label} execution proof blocked: live price has not confirmed LONG "
                f"from closed-card price {decimal_to_str(reference_price)} to {decimal_to_str(live_price)}"
            )
        if candidate.side == "SHORT" and live_price > reference_price - required_delta:
            return (
                f"{label} execution proof blocked: live price has not confirmed SHORT "
                f"from closed-card price {decimal_to_str(reference_price)} to {decimal_to_str(live_price)}"
            )

    stop_price = card_signal_price(candidate, "stopPrice")
    raw_target1 = card_signal_price(candidate, "target1Price")
    raw_target2 = card_signal_price(candidate, "target2Price")
    card_target = raw_target2 if raw_target2 > 0 else raw_target1
    if candidate.side == "LONG":
        if stop_price > 0 and stop_price >= live_price:
            return (
                f"{label} execution proof blocked: live LONG entry is already at or below card stop "
                f"{decimal_to_str(stop_price)}"
            )
        if card_target > 0 and card_target <= live_price:
            return (
                f"{label} execution proof blocked: live LONG entry already chased past card target "
                f"{decimal_to_str(card_target)}"
            )
    else:
        if stop_price > 0 and stop_price <= live_price:
            return (
                f"{label} execution proof blocked: live SHORT entry is already at or above card stop "
                f"{decimal_to_str(stop_price)}"
            )
        if card_target > 0 and card_target >= live_price:
            return (
                f"{label} execution proof blocked: live SHORT entry already chased past card target "
                f"{decimal_to_str(card_target)}"
            )
    return None


def apply_maeuknam_execution_proof(
    candidates: list[FuturesPaperCandidate],
    live_prices: dict[str, Decimal],
) -> list[FuturesPaperCandidate]:
    if not MAEUKNAM_EXECUTION_PROOF_ENABLED:
        return candidates
    gated: list[FuturesPaperCandidate] = []
    for candidate in candidates:
        if not is_entry_eligible(candidate):
            gated.append(candidate)
            continue
        reason = maeuknam_execution_proof_block_reason(candidate, live_prices.get(candidate.symbol, candidate.price))
        if reason is None:
            gated.append(candidate)
            continue
        gated.append(maeuknam_candidate_with_entry_block(candidate, "execution_proof", reason))
    return sorted(gated, key=lambda candidate: (candidate.entry_allowed, candidate.score), reverse=True)


def maeuknam_candidate_card_score(candidate: FuturesPaperCandidate) -> Decimal:
    signal = card_signal_payload(candidate)
    try:
        return to_decimal(signal.get("score"))
    except Exception:
        return candidate.score


def maeuknam_fee_drag_throttle_reason(
    state: FuturesPaperState,
    prices: dict[str, Decimal],
    candidate: FuturesPaperCandidate,
) -> str | None:
    drag = fee_drag_pct(state, prices)
    if drag < MAEUKNAM_FEE_DRAG_THROTTLE_PCT:
        return None
    card_score = maeuknam_candidate_card_score(candidate)
    if candidate.alex_signal:
        if (
            candidate.confirmation_count >= ALEX_FEE_DRAG_MIN_CONFIRMATIONS
            and card_score >= ALEX_FEE_DRAG_MIN_CARD_SCORE
            and candidate.target_move_pct >= ALEX_FEE_DRAG_MIN_TARGET_MOVE_PCT
        ):
            return None
        return (
            f"fee drag throttle {decimal_to_str(drag)}%: require Alex A+ score >= "
            f"{decimal_to_str(ALEX_FEE_DRAG_MIN_CARD_SCORE)}, target >= "
            f"{decimal_to_str(ALEX_FEE_DRAG_MIN_TARGET_MOVE_PCT)}%, confirmations >= "
            f"{ALEX_FEE_DRAG_MIN_CONFIRMATIONS}"
        )
    required_confirmations = (
        ALEX_FEE_DRAG_MIN_CONFIRMATIONS
        if candidate.alex_signal
        else MAEUKNAM_FEE_DRAG_MIN_CONFIRMATIONS
    )
    if (
        candidate.confirmation_count >= required_confirmations
        and card_score >= MAEUKNAM_FEE_DRAG_MIN_CARD_SCORE
    ):
        return None
    return (
        f"fee drag throttle {decimal_to_str(drag)}%: require card score >= "
        f"{decimal_to_str(MAEUKNAM_FEE_DRAG_MIN_CARD_SCORE)} and confirmations >= "
        f"{required_confirmations}"
    )


def apply_maeuknam_fee_drag_throttle(
    candidates: list[FuturesPaperCandidate],
    state: FuturesPaperState,
    prices: dict[str, Decimal],
) -> list[FuturesPaperCandidate]:
    gated: list[FuturesPaperCandidate] = []
    for candidate in candidates:
        if not is_entry_eligible(candidate):
            gated.append(candidate)
            continue
        reason = maeuknam_fee_drag_throttle_reason(state, prices, candidate)
        if reason is None:
            gated.append(candidate)
            continue
        gated.append(maeuknam_candidate_with_entry_block(candidate, "fee_drag_throttle", reason))
    return sorted(gated, key=lambda candidate: (candidate.entry_allowed, candidate.score), reverse=True)


def apply_same_minute_reentry_blocks(
    candidates: list[FuturesPaperCandidate],
    state: FuturesPaperState,
    closed_sides: dict[str, FuturesSide] | None = None,
) -> list[FuturesPaperCandidate]:
    gated: list[FuturesPaperCandidate] = []
    for candidate in candidates:
        reason = same_minute_reentry_block_reason(state, candidate.symbol)
        if reason is not None and candidate.entry_allowed:
            if closed_sides and candidate.symbol in closed_sides and candidate.side != closed_sides[candidate.symbol]:
                gated.append(candidate)
                continue
            gated.append(maeuknam_candidate_with_entry_block(candidate, "reentry_candle", reason))
        else:
            gated.append(candidate)
    return gated


def maeuknam_balanced_entry_candidates(
    candidates: list[FuturesPaperCandidate],
    state: FuturesPaperState,
    open_slots: int,
) -> list[FuturesPaperCandidate]:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.symbol not in state.positions and is_entry_eligible(candidate)
    ]
    if open_slots <= 0 or not eligible:
        return []
    long_candidates = [candidate for candidate in eligible if candidate.side == "LONG"]
    short_candidates = [candidate for candidate in eligible if candidate.side == "SHORT"]
    if not long_candidates or not short_candidates:
        return eligible

    per_side_cap = max(1, futures_paper_max_open_positions(maeuknam_only=True) // 2)
    current_long = sum(1 for position in state.positions.values() if position.side == "LONG")
    current_short = sum(1 for position in state.positions.values() if position.side == "SHORT")
    side_allowance = {
        "LONG": max(0, per_side_cap - current_long),
        "SHORT": max(0, per_side_cap - current_short),
    }

    selected: list[FuturesPaperCandidate] = []
    for side_candidates in (long_candidates, short_candidates):
        side = side_candidates[0].side
        selected.extend(side_candidates[: min(len(side_candidates), side_allowance[side], open_slots - len(selected))])

    selected_symbols = {candidate.symbol for candidate in selected}
    if len(selected) < open_slots:
        selected.extend(
            candidate
            for candidate in eligible
            if candidate.symbol not in selected_symbols
        )

    return sorted(selected[:open_slots], key=lambda candidate: candidate.score, reverse=True)


def configured_futures_candidate_scan(
    settings: TradingSettings,
    client: BinanceFuturesClient,
    focus_symbols: tuple[str, ...] = (),
) -> FuturesPaperCandidateScan:
    symbols = tuple(dict.fromkeys([*settings.binance_futures_symbols, *focus_symbols]))
    candidates = sorted(
        (
            replace(analyze_futures_symbol(client, symbol), universe_source="configured_symbols_fallback")
            for symbol in symbols
        ),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    regime = futures_market_regime_from_candidates(candidates)
    candidates = apply_futures_regime_gate(candidates, regime)
    candidates = apply_futures_contrarian_execution(candidates)
    return FuturesPaperCandidateScan(
        candidates=candidates,
        universe_count=len(symbols),
        evaluated_count=len(candidates),
        universe_source="configured_symbols_fallback",
        ticker_count=0,
        deep_analysis_count=len(candidates),
        market_regime=regime,
    )


def scan_futures_paper_candidates(
    settings: TradingSettings,
    client: BinanceFuturesClient,
    focus_symbols: tuple[str, ...] = (),
) -> FuturesPaperCandidateScan:
    if maeuknam_futures_mode(settings):
        return scan_maeuknam_futures_paper_candidates(settings, client, focus_symbols)
    if alex_futures_mode(settings):
        return scan_alex_futures_paper_candidates(settings, client, focus_symbols)

    universe = futures_symbol_universe(settings, client)
    try:
        raw_tickers = client.ticker_24hr()
        ticker_rows = raw_tickers if isinstance(raw_tickers, list) else [raw_tickers]
        universe_symbols = set(universe.symbols)
        broad_candidates = [
            candidate
            for row in ticker_rows
            if isinstance(row, dict)
            for candidate in [analyze_futures_ticker(row, universe.source)]
            if candidate is not None and candidate.symbol in universe_symbols
        ]
        if not broad_candidates:
            raise ValueError("Binance futures ticker screen returned no candidates")
    except Exception:
        return configured_futures_candidate_scan(settings, client, focus_symbols)

    broad_candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    broad_by_symbol = {candidate.symbol: candidate for candidate in broad_candidates}
    deep_symbols = tuple(
        dict.fromkeys(
            [
                *settings.binance_futures_symbols,
                *focus_symbols,
                *[candidate.symbol for candidate in broad_candidates[:FUTURES_DEEP_ANALYSIS_LIMIT]],
            ]
        )
    )
    deep_by_symbol: dict[str, FuturesPaperCandidate] = {}
    for symbol in deep_symbols:
        if symbol not in broad_by_symbol:
            continue
        try:
            deep = analyze_futures_symbol(client, symbol)
        except Exception:
            continue
        deep_by_symbol[symbol] = merge_deep_futures_candidate(deep, broad_by_symbol.get(symbol), universe.source)

    candidates = [deep_by_symbol.get(candidate.symbol, candidate) for candidate in broad_candidates]
    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    regime = futures_market_regime_from_candidates(candidates)
    candidates = apply_futures_regime_gate(candidates, regime)
    candidates = apply_futures_contrarian_execution(candidates)
    return FuturesPaperCandidateScan(
        candidates=candidates,
        universe_count=len(universe.symbols),
        evaluated_count=len(candidates),
        universe_source=universe.source,
        ticker_count=len(broad_candidates),
        deep_analysis_count=len(deep_by_symbol),
        market_regime=regime,
    )

def scan_maeuknam_futures_paper_candidates(
    settings: TradingSettings,
    client: BinanceFuturesClient,
    focus_symbols: tuple[str, ...] = (),
) -> FuturesPaperCandidateScan:
    symbols = MAEUKNAM_EXPERIMENT_SYMBOLS
    universe_source = "maeuknam_cards_btcusdt_only"
    candidates: list[FuturesPaperCandidate] = []
    for symbol in symbols:
        try:
            candidates.append(replace(analyze_maeuknam_futures_symbol(client, symbol), universe_source=universe_source))
        except Exception as exc:
            candidates.append(
                FuturesPaperCandidate(
                    symbol=symbol,
                    side="LONG",
                    price=Decimal("0"),
                    score=Decimal("0"),
                    momentum_5m_pct=Decimal("0"),
                    momentum_15m_pct=Decimal("0"),
                    range_15m_pct=Decimal("0"),
                    volume_ratio=Decimal("0"),
                    reason=f"maeuknam-card: analysis failed: {exc}",
                    analysis_depth="maeuknam_card_1m",
                    universe_source=universe_source,
                    entry_allowed=False,
                    entry_block_reason=str(exc),
                    analysis_side="LONG",
                    execution_side="LONG",
                    contrarian=False,
                )
            )
    candidates.sort(key=lambda candidate: (candidate.entry_allowed, candidate.score), reverse=True)
    regime = maeuknam_futures_market_regime(candidates)
    return FuturesPaperCandidateScan(
        candidates=candidates,
        universe_count=len(symbols),
        evaluated_count=len(candidates),
        universe_source=universe_source,
        ticker_count=0,
        deep_analysis_count=len(candidates),
        market_regime=regime,
    )


def scan_alex_futures_paper_candidates(
    settings: TradingSettings,
    client: BinanceFuturesClient,
    focus_symbols: tuple[str, ...] = (),
) -> FuturesPaperCandidateScan:
    symbols = ALEX_EXPERIMENT_SYMBOLS
    universe_source = "alex_method_btcusdt_only"
    candidates: list[FuturesPaperCandidate] = []
    for symbol in symbols:
        try:
            candidates.append(replace(analyze_alex_futures_symbol(client, symbol), universe_source=universe_source))
        except Exception as exc:
            candidates.append(
                FuturesPaperCandidate(
                    symbol=symbol,
                    side="LONG",
                    price=Decimal("0"),
                    score=Decimal("0"),
                    momentum_5m_pct=Decimal("0"),
                    momentum_15m_pct=Decimal("0"),
                    range_15m_pct=Decimal("0"),
                    volume_ratio=Decimal("0"),
                    reason=f"alex-method: analysis failed: {exc}",
                    analysis_depth="alex_method_1m",
                    universe_source=universe_source,
                    entry_allowed=False,
                    entry_block_reason=str(exc),
                    analysis_side="LONG",
                    execution_side="LONG",
                    contrarian=False,
                )
            )
    candidates.sort(key=lambda candidate: (candidate.entry_allowed, candidate.score), reverse=True)
    regime = maeuknam_futures_market_regime(candidates)
    return FuturesPaperCandidateScan(
        candidates=candidates,
        universe_count=len(symbols),
        evaluated_count=len(candidates),
        universe_source=universe_source,
        ticker_count=0,
        deep_analysis_count=len(candidates),
        market_regime=regime,
    )


def maeuknam_futures_market_regime(candidates: list[FuturesPaperCandidate]) -> FuturesMarketRegime:
    if not candidates:
        return FuturesMarketRegime(None, "maeuknam_wait", Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), "no Maeuknam futures candidates", None)
    alex_mode = all(candidate.alex_signal for candidate in candidates)
    prefix = "alex" if alex_mode else "maeuknam"
    display = "Alex method" if alex_mode else "Maeuknam card"
    allowed_candidates = [candidate for candidate in candidates if candidate.entry_allowed]
    allowed = len(allowed_candidates)
    long_allowed = sum(1 for candidate in allowed_candidates if candidate.side == "LONG")
    short_allowed = sum(1 for candidate in allowed_candidates if candidate.side == "SHORT")
    long_ratio = Decimal(long_allowed) / Decimal(len(candidates))
    short_ratio = Decimal(short_allowed) / Decimal(len(candidates))
    avg_momentum = sum((candidate.momentum_5m_pct for candidate in candidates), Decimal("0")) / Decimal(len(candidates))
    avg_context = sum((candidate.momentum_15m_pct for candidate in candidates), Decimal("0")) / Decimal(len(candidates))
    trade_side: FuturesSide | None = allowed_candidates[0].side if allowed_candidates else None
    if long_allowed and short_allowed:
        label = f"{prefix}_mixed_entry"
    elif long_allowed:
        label = f"{prefix}_long_entry"
    elif short_allowed:
        label = f"{prefix}_short_entry"
    else:
        label = f"{prefix}_wait"
    reason = (
        f"{display} gate: {allowed}/{len(candidates)} entries allowed "
        f"(LONG {long_allowed}, SHORT {short_allowed}); execution follows each card direction"
    )
    return FuturesMarketRegime(trade_side, label, long_ratio, short_ratio, avg_momentum, avg_context, reason, trade_side)


def maeuknam_plan_side(candidates: list[FuturesPaperCandidate]) -> str:
    sides = {candidate.side for candidate in candidates if candidate.entry_allowed}
    if len(sides) == 1:
        return next(iter(sides))
    if len(sides) > 1:
        return MAEUKNAM_DIRECTION_SIDE
    return "FLAT"


def maeuknam_status_side(state: FuturesPaperState) -> str:
    sides = {position.side for position in state.positions.values()}
    if len(sides) == 1:
        return next(iter(sides))
    return MAEUKNAM_DIRECTION_SIDE


def futures_paper_candidates(settings: TradingSettings, client: BinanceFuturesClient) -> list[FuturesPaperCandidate]:
    return scan_futures_paper_candidates(settings, client).candidates


def pct_change(start: Decimal, end: Decimal) -> Decimal:
    if start <= 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def fetch_futures_prices(client: BinanceFuturesClient, symbols: tuple[str, ...]) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    for symbol in symbols:
        row = client.ticker_price(symbol)
        prices[symbol] = to_decimal(row.get("price", "0"))
    return prices


def futures_paper_status(
    settings: TradingSettings,
    client: BinanceFuturesClient,
    state: FuturesPaperState | None = None,
) -> dict[str, Any]:
    store = FuturesPaperStateStore(futures_paper_state_path(settings))
    loaded_state = state if state is not None else store.load()
    symbols = (
        maeuknam_experiment_symbols(tuple(loaded_state.positions.keys()))
        if card_futures_mode(settings)
        else tuple(dict.fromkeys([*settings.binance_futures_symbols, *loaded_state.positions.keys()]))
    )
    prices = fetch_futures_prices(client, symbols)
    payload = state_payload(loaded_state, prices)
    if card_futures_mode(settings):
        manual_action = normalize_manual_futures_action(loaded_state.manual_action) if loaded_state.manual_action else None
        side = manual_action if manual_action and manual_action != "STOP" else "FLAT" if manual_action == "STOP" else maeuknam_status_side(loaded_state)
        payload["paperSide"] = futures_strategy_side(settings)
        payload["strategySide"] = futures_strategy_side(settings)
        payload["analysisSide"] = side
        payload["executionSide"] = side
        payload["exitBasis"] = MANUAL_HOLD_EXIT_BASIS if manual_action else ("alex_method_levels" if alex_futures_mode(settings) else "maeuknam_card_levels")
        payload["leverage"] = decimal_to_str(futures_paper_leverage(maeuknam_only=True))
        payload["maxOpenPositions"] = futures_paper_max_open_positions(maeuknam_only=True)
        payload["manualMode"] = manual_action is not None
        payload["manualAction"] = manual_action
    return payload


def parse_utc_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def seconds_since(value: str | None) -> Decimal:
    parsed = parse_utc_datetime(value)
    if parsed is None:
        return Decimal("999999")
    elapsed = datetime.now(timezone.utc) - parsed
    return Decimal(str(max(0, elapsed.total_seconds())))


def fee_drag_pct(state: FuturesPaperState, prices: dict[str, Decimal]) -> Decimal:
    equity = state.equity(prices)
    if equity <= 0:
        return Decimal("100")
    return state.fees_paid_usdt / equity * Decimal("100")


def prune_maeuknam_cooldowns(state: FuturesPaperState) -> None:
    now = datetime.now(timezone.utc)
    for key, until in list(state.maeuknam_cooldowns.items()):
        parsed = parse_utc_datetime(until)
        if parsed is None or parsed <= now:
            state.maeuknam_cooldowns.pop(key, None)


def maeuknam_cooldown_block_reason(state: FuturesPaperState, candidate: FuturesPaperCandidate) -> str | None:
    state.maeuknam_cooldowns.clear()
    return None


def prune_maeuknam_watchlist(state: FuturesPaperState, seen_keys: set[str]) -> None:
    for key, watch in list(state.maeuknam_watchlist.items()):
        if key in seen_keys:
            continue
        if seconds_since(watch.last_seen_at) >= MAEUKNAM_WATCH_STALE_SECONDS:
            state.maeuknam_watchlist.pop(key, None)


def apply_maeuknam_entry_lifecycle(
    candidates: list[FuturesPaperCandidate],
    state: FuturesPaperState,
) -> list[FuturesPaperCandidate]:
    now = utc_now()
    seen_keys: set[str] = set()
    gated: list[FuturesPaperCandidate] = []
    for candidate in candidates:
        if not candidate.maeuknam_signal or not candidate.cooldown_key:
            gated.append(candidate)
            continue
        key = maeuknam_candidate_cooldown_key(candidate)
        seen_keys.add(key)
        if not is_entry_eligible(candidate):
            gated.append(candidate)
            continue
        cooldown_reason = maeuknam_cooldown_block_reason(state, candidate)
        if cooldown_reason is not None:
            gated.append(
                maeuknam_candidate_with_entry_block(
                    candidate,
                    "cooldown",
                    cooldown_reason,
                )
            )
            continue
        agency_reason = maeuknam_candidate_agency_block_reason(candidate)
        if agency_reason is not None:
            inverse_candidate = maeuknam_inverse_agency_candidate(candidate, agency_reason)
            if inverse_candidate is not None:
                state.maeuknam_watchlist.pop(key, None)
                gated.append(inverse_candidate)
                continue
            gated.append(
                maeuknam_candidate_with_entry_block(
                    candidate,
                    "agency",
                    agency_reason,
                )
            )
            continue
        previous = state.maeuknam_watchlist.get(key)
        historical_confirmations = max(candidate.confirmation_count, 1)
        if previous is None:
            confirmations = historical_confirmations
        elif previous.last_candle_timestamp and previous.last_candle_timestamp == candidate.latest_candle_timestamp:
            confirmations = max(previous.confirmations, historical_confirmations)
        else:
            confirmations = max(previous.confirmations + 1, historical_confirmations)
        first_seen_at = now if previous is None else previous.first_seen_at
        state.maeuknam_watchlist[key] = MaeuknamWatchState(
            symbol=candidate.symbol,
            side=candidate.side,
            technique_id=maeuknam_candidate_technique_id(candidate),
            first_seen_at=first_seen_at,
            last_seen_at=now,
            confirmations=confirmations,
            score=candidate.score,
            target_move_pct=candidate.target_move_pct,
            last_candle_timestamp=candidate.latest_candle_timestamp,
        )
        if confirmations < MAEUKNAM_CONFIRMATION_CYCLES:
            gated.append(
                replace(
                    maeuknam_candidate_with_entry_block(
                        candidate,
                        "watch",
                        f"Maeuknam watch stage {confirmations}/{MAEUKNAM_CONFIRMATION_CYCLES}: "
                        "same symbol/card must confirm before entry",
                    ),
                    confirmation_count=confirmations,
                    cooldown_key=key,
                )
            )
            continue
        entry_reason = (
            f"Maeuknam confirmed {confirmations}/{MAEUKNAM_CONFIRMATION_CYCLES}; "
            "card-only entry allowed"
        )
        if Decimal("0") < candidate.target_move_pct < candidate.fee_safety_move_pct:
            entry_reason = f"{entry_reason}; fee-floor target extension will be used"
        gated.append(
            replace(
                candidate,
                entry_allowed=True,
                entry_block_reason=entry_reason,
                entry_stage="entry",
                confirmation_count=confirmations,
                cooldown_key=key,
            )
        )
    prune_maeuknam_watchlist(state, seen_keys)
    return sorted(gated, key=lambda candidate: (candidate.entry_allowed, candidate.score), reverse=True)


def register_maeuknam_reentry_cooldown(
    state: FuturesPaperState,
    position: FuturesPaperPosition,
    candidate: FuturesPaperCandidate | None,
) -> None:
    state.maeuknam_cooldowns.clear()


def new_entries_block_reason(
    state: FuturesPaperState,
    prices: dict[str, Decimal],
    maeuknam_only: bool = False,
    alex_only: bool = False,
) -> str | None:
    max_orders = MAEUKNAM_MAX_SESSION_ORDER_COUNT if maeuknam_only else MAX_SESSION_ORDER_COUNT
    max_fee_drag_pct = (
        ALEX_MAX_FEE_DRAG_PCT
        if alex_only
        else (
            MAEUKNAM_TEST_MAX_FEE_DRAG_PCT
            if maeuknam_only and MAEUKNAM_TEST_TRADE_MODE
            else MAEUKNAM_MAX_FEE_DRAG_PCT
            if maeuknam_only
            else MAX_FEE_DRAG_PCT
        )
    )
    cooldown_seconds = MAEUKNAM_ENTRY_COOLDOWN_SECONDS if maeuknam_only else ENTRY_COOLDOWN_SECONDS
    if max_orders > 0 and state.order_count >= max_orders:
        return f"session order count {state.order_count} reached cap {max_orders}"
    drag = fee_drag_pct(state, prices)
    if max_fee_drag_pct > 0 and drag >= max_fee_drag_pct:
        return f"fee drag {decimal_to_str(drag)}% reached cap {decimal_to_str(max_fee_drag_pct)}%"
    elapsed = seconds_since(state.last_order_at)
    if cooldown_seconds > 0 and elapsed < cooldown_seconds:
        return f"entry cooldown {decimal_to_str(elapsed)}s/{cooldown_seconds}s"
    return None


def maeuknam_entry_policy_payload(state: FuturesPaperState) -> dict[str, Any]:
    return {
        "source": "maeuknam_cards_only",
        "symbols": list(MAEUKNAM_EXPERIMENT_SYMBOLS),
        "leverage": decimal_to_str(futures_paper_leverage(maeuknam_only=True)),
        "maxOpenPositions": futures_paper_max_open_positions(maeuknam_only=True),
        "relaxedEntryThreshold": decimal_to_str(MAEUKNAM_RELAXED_ENTRY_THRESHOLD),
        "testTradeMode": MAEUKNAM_TEST_TRADE_MODE,
        "testEntryThreshold": decimal_to_str(MAEUKNAM_TEST_ENTRY_THRESHOLD),
        "candleInterval": MAEUKNAM_KLINE_INTERVAL,
        "fetchLimit": MAEUKNAM_KLINE_FETCH_LIMIT,
        "closedCandleLimit": MAEUKNAM_CLOSED_CANDLE_LIMIT,
        "openCandleExcluded": True,
        "confirmationCycles": MAEUKNAM_CONFIRMATION_CYCLES,
        "confirmationBasis": "closed_1m_candle_history",
        "multiTimeframeIntervals": list(MAEUKNAM_CONTEXT_INTERVALS),
        "multiTimeframeFetchLimit": MAEUKNAM_CONTEXT_KLINE_LIMIT,
        "multiTimeframePageLimit": BINANCE_KLINE_PAGE_LIMIT,
        "multiTimeframeCacheSeconds": MAEUKNAM_CONTEXT_CACHE_SECONDS,
        "multiTimeframeBasis": "closed_1d_1w_1M_history",
        "multiTimeframeScoreWeight": decimal_to_str(MAEUKNAM_CONTEXT_SCORE_WEIGHT),
        "maxOpposedTimeframes": MAEUKNAM_AGENCY_MAX_OPPOSED_TIMEFRAMES,
        "inverseAgencyEntryEnabled": MAEUKNAM_INVERSE_AGENCY_ENTRY_ENABLED,
        "inverseAgencyBasis": "card_direction_vetoed_by_two_or_more_opposing_higher_timeframes",
        "inverseAgencyMinRewardRisk": decimal_to_str(MAEUKNAM_INVERSE_MIN_REWARD_RISK),
        "executionProofEnabled": MAEUKNAM_EXECUTION_PROOF_ENABLED,
        "executionProofMovePct": decimal_to_str(MAEUKNAM_EXECUTION_PROOF_MOVE_PCT),
        "executionProofBasis": "latest_binance_ticker_vs_closed_card_price_and_card_exit_levels",
        "directionBalanceMode": "card_evidence_weighted_threshold",
        "evidenceSupportTarget": decimal_to_str(CARD_EVIDENCE_SUPPORT_TARGET),
        "evidenceConfidenceTarget": decimal_to_str(CARD_EVIDENCE_CONFIDENCE_TARGET),
        "evidenceMaxThresholdPremium": decimal_to_str(CARD_EVIDENCE_MAX_THRESHOLD_PREMIUM),
        "watchStaleSeconds": decimal_to_str(MAEUKNAM_WATCH_STALE_SECONDS),
        "minTargetFeeMultiple": decimal_to_str(MAEUKNAM_MIN_TARGET_FEE_MULTIPLE),
        "roundTripFeeMovePct": decimal_to_str(maeuknam_round_trip_fee_move_pct()),
        "requiredTargetMovePct": decimal_to_str(maeuknam_fee_safety_move_pct()),
        "smallTargetHandling": "card_direction_entry_with_fee_floor_target_extension",
        "maxOpenFeeEquityPct": decimal_to_str(MAEUKNAM_MAX_OPEN_FEE_EQUITY_PCT),
        "positionSizingMode": "100x_leverage_with_open_fee_budget",
        "minHoldSeconds": decimal_to_str(MAEUKNAM_MIN_HOLD_SECONDS),
        "entryCooldownSeconds": MAEUKNAM_ENTRY_COOLDOWN_SECONDS,
        "reentryCooldownSeconds": MAEUKNAM_REENTRY_COOLDOWN_SECONDS,
        "cooldownMode": "disabled",
        "maxSessionOrderCount": MAEUKNAM_MAX_SESSION_ORDER_COUNT,
        "sessionOrderLimitEnabled": MAEUKNAM_MAX_SESSION_ORDER_COUNT > 0,
        "maxFeeDragPct": decimal_to_str(
            MAEUKNAM_TEST_MAX_FEE_DRAG_PCT if MAEUKNAM_TEST_TRADE_MODE else MAEUKNAM_MAX_FEE_DRAG_PCT
        ),
        "feeDragThrottlePct": decimal_to_str(MAEUKNAM_FEE_DRAG_THROTTLE_PCT),
        "feeDragMinCardScore": decimal_to_str(MAEUKNAM_FEE_DRAG_MIN_CARD_SCORE),
        "feeDragMinConfirmations": str(MAEUKNAM_FEE_DRAG_MIN_CONFIRMATIONS),
        "feeDragLimitEnabled": (
            MAEUKNAM_TEST_MAX_FEE_DRAG_PCT if MAEUKNAM_TEST_TRADE_MODE else MAEUKNAM_MAX_FEE_DRAG_PCT
        )
        > 0,
        "watchCount": len(state.maeuknam_watchlist),
        "cooldownCount": len(state.maeuknam_cooldowns),
    }


def alex_entry_policy_payload(state: FuturesPaperState) -> dict[str, Any]:
    return {
        "source": "alex_method_only",
        "symbols": list(ALEX_EXPERIMENT_SYMBOLS),
        "leverage": decimal_to_str(futures_paper_leverage(maeuknam_only=True)),
        "maxOpenPositions": futures_paper_max_open_positions(maeuknam_only=True),
        "candleInterval": ALEX_KLINE_INTERVAL,
        "fetchLimit": ALEX_KLINE_FETCH_LIMIT,
        "openCandleExcluded": True,
        "confirmationCycles": MAEUKNAM_CONFIRMATION_CYCLES,
        "confirmationBasis": "closed_1m_candle_history",
        "multiTimeframeIntervals": list(ALEX_CONTEXT_INTERVALS),
        "multiTimeframeFetchLimit": MAEUKNAM_CONTEXT_KLINE_LIMIT,
        "multiTimeframePageLimit": BINANCE_KLINE_PAGE_LIMIT,
        "multiTimeframeCacheSeconds": MAEUKNAM_CONTEXT_CACHE_SECONDS,
        "multiTimeframeBasis": "closed_12h_30m_1d_history",
        "multiTimeframeScoreWeight": decimal_to_str(MAEUKNAM_CONTEXT_SCORE_WEIGHT),
        "methodRules": [
            "do not pre-fix LONG or SHORT",
            "build range midpoint 0.5 first",
            "prefer discount LONG or premium SHORT value areas",
            "require liquidity/failed-break behavior and 1-2-3-4 confirmation score",
            "zero-fee experiment mode isolates method performance from commission drag",
            "enter only when raw target move beats the configured quality/fee floor",
            "block entries when 2+ higher timeframes oppose the Alex direction",
            "block entries whose stop is inside the 1m noise floor",
            "if normal entry is too strict, allow HTF-aligned watch probes with 10% margin for data collection",
            "hold active positions through weak/flat analysis until target, stop, or fee-safe switch",
            "extend profitable target hits with runner trailing instead of closing immediately",
            "block same 1m candle re-entry immediately after a close",
            "switch LONG/SHORT only when the new setup beats transition fee cost",
            "do not flip a newly opened position again inside its entry 1m candle",
            "after fee drag appears, permit only Alex A+ setups to avoid fee-storm churn",
        ],
        "zeroFeeExperiment": ALEX_ZERO_FEE_EXPERIMENT,
        "feeRate": decimal_to_str(alex_fee_rate()),
        "minTargetFeeMultiple": decimal_to_str(MAEUKNAM_MIN_TARGET_FEE_MULTIPLE),
        "roundTripFeeMovePct": decimal_to_str(alex_round_trip_fee_move_pct()),
        "requiredTargetMovePct": decimal_to_str(alex_fee_safety_move_pct()),
        "alexMinTargetMovePct": decimal_to_str(ALEX_MIN_TARGET_MOVE_PCT),
        "alexMinStopDistancePct": decimal_to_str(ALEX_MIN_STOP_DISTANCE_PCT),
        "alexMaxOpposedTimeframes": ALEX_MAX_OPPOSED_TIMEFRAMES,
        "watchProbeEnabled": ALEX_WATCH_PROBE_ENABLED,
        "watchProbeMinTargetMovePct": decimal_to_str(ALEX_WATCH_PROBE_MIN_TARGET_MOVE_PCT),
        "watchProbeMarginPct": decimal_to_str(ALEX_MIN_ENTRY_MARGIN_PCT * Decimal("100")),
        "alexFeeDragMinTargetMovePct": decimal_to_str(ALEX_FEE_DRAG_MIN_TARGET_MOVE_PCT),
        "switchRequiredTargetMovePct": decimal_to_str(alex_switch_required_move_pct()),
        "smallTargetHandling": "block_entry_until_target_beats_fee_floor",
        "minEntryMarginPct": decimal_to_str(ALEX_MIN_ENTRY_MARGIN_PCT * Decimal("100")),
        "maxEntryMarginPct": decimal_to_str(ALEX_MAX_ENTRY_MARGIN_PCT * Decimal("100")),
        "fullSizeScore": decimal_to_str(ALEX_FULL_SIZE_SCORE),
        "positionSizingMode": "100x_leverage_dynamic_10_30_margin",
        "sameMinuteReentryBlock": True,
        "sameEntryCandleFlipBlock": True,
        "profitRunnerMode": True,
        "runnerProfitLockShare": decimal_to_str(ALEX_RUNNER_PROFIT_LOCK_SHARE),
        "liveDirectionConfirmationRequired": False,
        "executionProofBasis": "latest_binance_ticker_must_not_violate_alex_stop_or_target_levels",
        "minHoldSeconds": decimal_to_str(MAEUKNAM_MIN_HOLD_SECONDS),
        "entryCooldownSeconds": MAEUKNAM_ENTRY_COOLDOWN_SECONDS,
        "reentryCooldownSeconds": MAEUKNAM_REENTRY_COOLDOWN_SECONDS,
        "cooldownMode": "disabled",
        "maxSessionOrderCount": MAEUKNAM_MAX_SESSION_ORDER_COUNT,
        "sessionOrderLimitEnabled": MAEUKNAM_MAX_SESSION_ORDER_COUNT > 0,
        "maxFeeDragPct": decimal_to_str(ALEX_MAX_FEE_DRAG_PCT),
        "feeDragThrottlePct": decimal_to_str(MAEUKNAM_FEE_DRAG_THROTTLE_PCT),
        "feeDragMinCardScore": decimal_to_str(ALEX_FEE_DRAG_MIN_CARD_SCORE),
        "feeDragMinConfirmations": str(ALEX_FEE_DRAG_MIN_CONFIRMATIONS),
        "feeDragMode": "alex_a_plus_only_after_fee_drag",
        "feeDragConfirmationBasis": "current_alex_closed_candle_confirmation",
        "feeDragLimitEnabled": ALEX_MAX_FEE_DRAG_PCT > 0,
        "watchCount": len(state.maeuknam_watchlist),
        "cooldownCount": len(state.maeuknam_cooldowns),
    }


def run_futures_paper_cycle(settings: TradingSettings, client: BinanceFuturesClient) -> dict[str, Any]:
    store = FuturesPaperStateStore(futures_paper_state_path(settings))
    state = store.load()
    maeuknam_only = maeuknam_futures_mode(settings)
    alex_only = alex_futures_mode(settings)
    card_only = maeuknam_only or alex_only
    manual_action = normalize_manual_futures_action(state.manual_action) if state.manual_action else None
    if manual_action is not None:
        symbols = tuple(dict.fromkeys([MAEUKNAM_BTC_ONLY_SYMBOL, *state.positions.keys()]))
        prices = fetch_futures_prices(client, symbols)
        actions: list[dict[str, Any]] = []
        if manual_action == "STOP":
            for symbol, position in list(state.positions.items()):
                actions.append(
                    close_position(
                        state,
                        position,
                        prices.get(symbol, position.entry_price),
                        "manual STOP mode keeps futures paper flat",
                    )
                )
            if actions:
                store.save(state)
        payload = state_payload(state, prices)
        status_side = manual_action if manual_action != "STOP" else "FLAT"
        payload["paperSide"] = futures_strategy_side(settings)
        payload["strategySide"] = futures_strategy_side(settings)
        payload["analysisSide"] = status_side
        payload["executionSide"] = status_side
        payload["exitBasis"] = MANUAL_HOLD_EXIT_BASIS
        payload["leverage"] = decimal_to_str(MAEUKNAM_EXPERIMENT_LEVERAGE)
        payload["maxOpenPositions"] = futures_paper_max_open_positions(maeuknam_only=True)
        payload["manualMode"] = True
        payload["manualAction"] = manual_action
        payload["actions"] = actions
        payload["entryBlockReason"] = "manual futures paper mode is active until LONG/SHORT/STOP is pressed"
        payload["message"] = f"Manual Binance futures paper {manual_action} mode is active; automatic entries skipped."
        payload["updatedAt"] = utc_now()
        return payload
    candidate_scan = scan_futures_paper_candidates(settings, client, tuple(state.positions.keys()))
    candidates = (
        apply_maeuknam_entry_lifecycle(candidate_scan.candidates, state)
        if maeuknam_only
        else candidate_scan.candidates
    )
    prices = {candidate.symbol: candidate.price for candidate in candidates}
    market_regime = (
        maeuknam_futures_market_regime(candidates)
        if card_only
        else candidate_scan.market_regime or futures_market_regime_from_candidates(candidates)
    )
    prices.update({candidate.symbol: candidate.price for candidate in candidates if candidate.symbol not in prices})
    if state.positions:
        prices.update(fetch_futures_prices(client, tuple(sorted(state.positions.keys()))))
    actions: list[dict[str, Any]] = []
    closed_sides: dict[str, FuturesSide] = {}

    for symbol, position in list(state.positions.items()):
        price = prices.get(symbol)
        if price is None:
            price = to_decimal(client.ticker_price(symbol).get("price", "0"))
            prices[symbol] = price
        matching_candidate = next((candidate for candidate in candidates if candidate.symbol == symbol), None)
        if alex_only:
            estimated_entry_fee = position.margin_usdt * position.leverage * futures_position_fee_rate(position)
            margin_cap = (state.equity(prices) + estimated_entry_fee) * ALEX_MAX_ENTRY_MARGIN_PCT
            if margin_cap > 0 and position.margin_usdt > margin_cap:
                actions.append(
                    close_position(
                        state,
                        position,
                        price,
                        (
                            "Alex method margin cap reset: position margin "
                            f"{decimal_to_str(position.margin_usdt)} USDT exceeds "
                            f"{decimal_to_str(ALEX_MAX_ENTRY_MARGIN_PCT * Decimal('100'))}% cap"
                        ),
                    )
                )
                closed_sides[symbol] = position.side
                continue
        if card_only and symbol not in MAEUKNAM_EXPERIMENT_SYMBOLS:
            label = "Alex" if alex_only else "Maeuknam"
            actions.append(close_position(state, position, price, f"{label} BTCUSDT-only experiment removed non-BTC position"))
            closed_sides[symbol] = position.side
            continue
        if card_only:
            should_close, close_reason = should_close_maeuknam_position(
                position,
                price,
                matching_candidate,
                futures_paper_leverage(maeuknam_only=True),
            )
        else:
            should_close, close_reason = should_close_position(position, price, matching_candidate, market_regime)
        if should_close:
            actions.append(close_position(state, position, price, close_reason))
            if card_only:
                register_maeuknam_reentry_cooldown(state, position, matching_candidate)
            closed_sides[symbol] = position.side

    if card_only:
        proof_symbols = tuple(
            sorted({candidate.symbol for candidate in candidates if card_signal_payload(candidate) and candidate.entry_allowed})
        )
        if proof_symbols:
            prices.update(fetch_futures_prices(client, proof_symbols))
            candidates = apply_maeuknam_execution_proof(candidates, prices)
            candidates = apply_maeuknam_fee_drag_throttle(candidates, state, prices)
        if alex_only:
            candidates = apply_same_minute_reentry_blocks(candidates, state, closed_sides)
        market_regime = maeuknam_futures_market_regime(candidates)

    entry_block_reason = new_entries_block_reason(state, prices, card_only, alex_only)
    open_slots = max(0, futures_paper_max_open_positions(card_only) - len(state.positions))
    entry_candidates = maeuknam_balanced_entry_candidates(candidates, state, open_slots) if card_only else candidates
    for candidate in entry_candidates:
        if open_slots <= 0:
            break
        if entry_block_reason is not None:
            break
        if candidate.symbol in state.positions:
            continue
        if card_only and closed_sides.get(candidate.symbol) == candidate.side:
            continue
        if (
            alex_only
            and same_minute_reentry_block_reason(state, candidate.symbol) is not None
            and not (closed_sides.get(candidate.symbol) is not None and candidate.side != closed_sides[candidate.symbol])
        ):
            continue
        if not is_entry_eligible(candidate):
            continue
        prices.update(fetch_futures_prices(client, (candidate.symbol,)))
        action = open_position_from_candidate(state, candidate, prices, open_slots, card_only)
        if action is not None:
            actions.append(action)
            if maeuknam_only:
                state.maeuknam_watchlist.pop(maeuknam_candidate_cooldown_key(candidate), None)
            open_slots -= 1

    if entry_block_reason is None and not card_only:
        actions.extend(increase_positions_to_full_deploy(state, prices, candidates))

    store.save(state)
    payload = state_payload(state, prices)
    payload["candidates"] = [candidate.to_dict() for candidate in candidates]
    payload["universeCount"] = candidate_scan.universe_count
    payload["evaluatedCount"] = candidate_scan.evaluated_count
    payload["universeSource"] = candidate_scan.universe_source
    payload["tickerCount"] = candidate_scan.ticker_count
    payload["deepAnalysisCount"] = candidate_scan.deep_analysis_count
    payload["marketRegime"] = market_regime.to_dict()
    payload["paperSide"] = futures_strategy_side(settings) if card_only else STRATEGY_SIDE
    payload["strategySide"] = futures_strategy_side(settings) if card_only else STRATEGY_SIDE
    payload["analysisSide"] = maeuknam_plan_side(candidates) if card_only else market_regime.trade_side or "FLAT"
    payload["executionSide"] = maeuknam_plan_side(candidates) if card_only else contrarian_execution_side(market_regime.trade_side) or "FLAT"
    payload["exitBasis"] = (
        "alex_method_levels" if alex_only else "maeuknam_card_levels" if maeuknam_only else payload.get("exitBasis")
    )
    if card_only:
        payload["leverage"] = decimal_to_str(futures_paper_leverage(maeuknam_only=True))
        payload["maxOpenPositions"] = futures_paper_max_open_positions(maeuknam_only=True)
    if maeuknam_only:
        payload["maeuknamEntryPolicy"] = maeuknam_entry_policy_payload(state)
    if alex_only:
        payload["alexEntryPolicy"] = alex_entry_policy_payload(state)
    payload["entryBlockReason"] = entry_block_reason
    payload["actions"] = actions
    payload["message"] = cycle_message(actions)
    payload["updatedAt"] = utc_now()
    return payload


def should_close_position(
    position: FuturesPaperPosition,
    price: Decimal,
    candidate: FuturesPaperCandidate | None,
    regime: FuturesMarketRegime,
) -> tuple[bool, str]:
    roi = position.return_on_margin_pct(price)
    if position.leverage != DEFAULT_LEVERAGE:
        return True, f"leverage changed to {decimal_to_str(DEFAULT_LEVERAGE)}x"
    if roi >= TAKE_PROFIT_MARGIN_PCT:
        return True, f"take-profit {decimal_to_str(roi)}% on margin"
    if roi <= STOP_LOSS_MARGIN_PCT:
        return True, f"stop-loss {decimal_to_str(roi)}% on margin"
    expected_side = contrarian_execution_side(regime.trade_side)
    if expected_side is not None and expected_side != position.side:
        return True, f"contrarian execution flipped to {expected_side} after analysis {regime.trade_side}: {regime.reason}"
    if regime.trade_side is None and roi <= Decimal("0.4"):
        return True, f"flat regime protection: {regime.reason}"
    if candidate is not None and candidate.side != position.side and is_entry_eligible(candidate):
        return True, f"signal flipped to {candidate.side} score {decimal_to_str(candidate.score)}"
    return False, "hold"


def should_close_maeuknam_position(
    position: FuturesPaperPosition,
    price: Decimal,
    candidate: FuturesPaperCandidate | None,
    expected_leverage: Decimal,
) -> tuple[bool, str]:
    alex_position = position.exit_basis.startswith("alex") or (candidate is not None and candidate.alex_signal)
    label = "Alex method" if alex_position else "Maeuknam card"
    if position.leverage != expected_leverage:
        return True, f"leverage changed to {decimal_to_str(expected_leverage)}x"
    if position.side not in {"LONG", "SHORT"}:
        return True, f"unsupported {label} futures side detected; reset to card-direction mode"
    if position.exit_basis == MANUAL_HOLD_EXIT_BASIS:
        return False, f"manual {position.side} hold until explicit switch command"
    take_profit = position.take_profit_price()
    stop_loss = position.stop_price
    if take_profit <= 0 or stop_loss <= 0:
        return True, f"missing {label} exit levels; reset to card-based exits"
    if is_maeuknam_inverse_position(position):
        inverse_risk_reason = maeuknam_inverse_reward_risk_block_reason(
            position.side,
            position.entry_price,
            stop_loss,
            take_profit,
        )
        if inverse_risk_reason is not None:
            return True, f"{inverse_risk_reason}; close inverse-risk card position"
    held_seconds = seconds_since(position.opened_at)
    min_hold_met = MAEUKNAM_MIN_HOLD_SECONDS <= 0 or held_seconds >= MAEUKNAM_MIN_HOLD_SECONDS
    if position.side == "LONG":
        if price <= stop_loss:
            return True, f"{label} stop reached at {decimal_to_str(stop_loss)}"
        if position.entry_price < position.target1_price <= price < take_profit:
            if alex_position:
                protect_maeuknam_profit(position, price, ALEX_RUNNER_PROFIT_LOCK_SHARE)
                return False, f"{label} first target reached; runner trailing stop protected"
            if maeuknam_candidate_still_supports_position(candidate, position):
                protect_maeuknam_profit(position, price)
                return False, f"{label} first target reached; trailing stop protected"
        if price >= take_profit:
            if alex_position:
                protect_maeuknam_profit(position, price, ALEX_RUNNER_PROFIT_LOCK_SHARE)
                if candidate is not None and candidate.entry_allowed and candidate.side != position.side:
                    if order_minute_bucket(position.opened_at) == order_minute_bucket():
                        return False, f"{label} runner target reached; same-candle flip blocked, trailing stop protected"
                    switch_block = alex_switch_cost_block_reason(position, candidate, price)
                    if switch_block is None:
                        return True, f"{label} runner target reached and fee-safe switch to {candidate.side}"
                return False, f"{label} target reached; runner mode keeps profit open with trailing stop"
            if maeuknam_candidate_still_supports_position(candidate, position):
                protect_maeuknam_profit(position, price)
                return False, f"{label} target reached, but same-direction card remains valid; trailing stop protected"
            return True, f"{label} target reached at {decimal_to_str(take_profit)}"
    else:
        if price >= stop_loss:
            return True, f"{label} stop reached at {decimal_to_str(stop_loss)}"
        if take_profit < price <= position.target1_price < position.entry_price:
            if alex_position:
                protect_maeuknam_profit(position, price, ALEX_RUNNER_PROFIT_LOCK_SHARE)
                return False, f"{label} first target reached; runner trailing stop protected"
            if maeuknam_candidate_still_supports_position(candidate, position):
                protect_maeuknam_profit(position, price)
                return False, f"{label} first target reached; trailing stop protected"
        if price <= take_profit:
            if alex_position:
                protect_maeuknam_profit(position, price, ALEX_RUNNER_PROFIT_LOCK_SHARE)
                if candidate is not None and candidate.entry_allowed and candidate.side != position.side:
                    if order_minute_bucket(position.opened_at) == order_minute_bucket():
                        return False, f"{label} runner target reached; same-candle flip blocked, trailing stop protected"
                    switch_block = alex_switch_cost_block_reason(position, candidate, price)
                    if switch_block is None:
                        return True, f"{label} runner target reached and fee-safe switch to {candidate.side}"
                return False, f"{label} target reached; runner mode keeps profit open with trailing stop"
            if maeuknam_candidate_still_supports_position(candidate, position):
                protect_maeuknam_profit(position, price)
                return False, f"{label} target reached, but same-direction card remains valid; trailing stop protected"
            return True, f"{label} target reached at {decimal_to_str(take_profit)}"
    if not min_hold_met:
        return False, f"minimum {label} hold {decimal_to_str(held_seconds)}s/{decimal_to_str(MAEUKNAM_MIN_HOLD_SECONDS)}s"
    if candidate is None or not candidate.entry_allowed:
        if alex_position:
            return False, f"{label} weak/flat realtime card; keep holding until target, stop, or fee-safe switch"
        return True, f"{label} realtime direction is FLAT; close stale card position"
    if candidate.side != position.side:
        if alex_position and order_minute_bucket(position.opened_at) == order_minute_bucket():
            return False, f"{label} switch blocked inside entry 1m candle; avoid flip-flop fee churn"
        switch_block = alex_switch_cost_block_reason(position, candidate, price)
        if switch_block is not None:
            return False, switch_block
        return True, f"{label} signal flipped to {candidate.side} score {decimal_to_str(candidate.score)}"
    return False, "hold"


def maeuknam_candidate_still_supports_position(
    candidate: FuturesPaperCandidate | None,
    position: FuturesPaperPosition,
) -> bool:
    if candidate is None or candidate.side != position.side:
        return False
    signal = card_signal_payload(candidate)
    hard_blocks = signal.get("hardBlocks") if isinstance(signal.get("hardBlocks"), list) else []
    return bool(signal.get("entryAllowed")) and not hard_blocks


def protect_maeuknam_profit(
    position: FuturesPaperPosition,
    price: Decimal,
    lock_share: Decimal = MAEUKNAM_PROFIT_LOCK_SHARE,
) -> None:
    if position.side == "LONG":
        profit_move = max(Decimal("0"), price - position.entry_price)
        locked_stop = position.entry_price + profit_move * lock_share
        position.stop_price = max(position.stop_price, position.entry_price, locked_stop)
    else:
        profit_move = max(Decimal("0"), position.entry_price - price)
        locked_stop = position.entry_price - profit_move * lock_share
        position.stop_price = min(position.stop_price, position.entry_price, locked_stop)


def open_position_from_candidate(
    state: FuturesPaperState,
    candidate: FuturesPaperCandidate,
    prices: dict[str, Decimal],
    open_slots: int,
    maeuknam_only: bool = False,
) -> dict[str, Any] | None:
    if open_slots <= 0:
        return None
    equity = state.equity(prices)
    available = state.available_balance(prices)
    leverage = futures_paper_leverage(maeuknam_only)
    slot_count = 1 if maeuknam_only else open_slots
    target_margin = remaining_target_margin(state, equity) / Decimal(slot_count)
    alex_margin_pct = alex_entry_margin_pct(candidate) if candidate.alex_signal else Decimal("0")
    alex_full_deploy = False
    fee_budgeted_margin = bool(maeuknam_only and candidate.maeuknam_signal and not alex_full_deploy)
    fee_budget_margin = maeuknam_fee_budgeted_entry_margin(equity, leverage) if fee_budgeted_margin else target_margin
    if candidate.alex_signal:
        target_margin = remaining_target_margin(state, equity) * alex_margin_pct
    elif fee_budgeted_margin:
        target_margin = min(target_margin, fee_budget_margin)
    fee_rate = futures_candidate_fee_rate(candidate)
    deploy_margin = min(target_margin, fee_adjusted_available_margin(available, leverage, fee_rate))
    entry_price = prices.get(candidate.symbol, candidate.price)
    if entry_price <= 0:
        entry_price = candidate.price
    if deploy_margin <= Decimal("5") or entry_price <= 0:
        return None
    notional = deploy_margin * leverage
    quantity = notional / entry_price
    fee = notional * fee_rate
    now = utc_now()
    state.wallet_balance_usdt -= fee
    state.fees_paid_usdt += fee
    state.open_fees_paid_usdt += fee
    state.order_count += 1
    state.last_order_at = now
    raw_target1 = card_signal_price(candidate, "target1Price")
    raw_target2 = card_signal_price(candidate, "target2Price")
    card_take_profit = raw_target2 if raw_target2 > 0 else raw_target1
    card_signal = card_signal_payload(candidate)
    fee_safe_take_profit = (
        maeuknam_fee_safe_target_price(candidate.side, entry_price, card_take_profit)
        if card_signal
        else card_take_profit
    )
    exit_basis = "alex_method" if candidate.alex_signal else "maeuknam_card" if candidate.maeuknam_signal else ""
    if card_signal and fee_safe_take_profit != card_take_profit:
        exit_basis = "alex_method_fee_floor" if candidate.alex_signal else "maeuknam_card_fee_floor"
    position = FuturesPaperPosition(
        symbol=candidate.symbol,
        side=candidate.side,
        quantity=quantity,
        entry_price=entry_price,
        leverage=leverage,
        margin_usdt=deploy_margin,
        opened_at=now,
        reason=candidate.reason,
        stop_price=card_signal_price(candidate, "stopPrice"),
        target1_price=raw_target1,
        target2_price=fee_safe_take_profit,
        exit_basis=exit_basis,
        technique_id=maeuknam_candidate_technique_id(candidate),
        technique_name=maeuknam_candidate_technique_name(candidate),
    )
    state.positions[candidate.symbol] = position
    return {
        "type": "OPEN",
        "symbol": candidate.symbol,
        "side": candidate.side,
        "analysisSide": candidate.analysis_side or candidate.side,
        "executionSide": candidate.execution_side or candidate.side,
        "price": decimal_to_str(entry_price),
        "analysisPrice": decimal_to_str(candidate.price),
        "quantity": decimal_to_str(quantity),
        "leverage": decimal_to_str(leverage),
        "marginUsdt": decimal_to_str(deploy_margin),
        "notionalUsdt": decimal_to_str(notional),
        "feeRate": decimal_to_str(fee_rate),
        "zeroFeeExperiment": bool(candidate.alex_signal and ALEX_ZERO_FEE_EXPERIMENT),
        "feeUsdt": decimal_to_str(fee),
        "openFeeEquityPct": decimal_to_str((fee / equity * Decimal("100")) if equity > 0 else Decimal("0")),
        "feeBudgetedMargin": fee_budgeted_margin,
        "fullDeployMargin": alex_full_deploy,
        "marginCapPct": decimal_to_str(alex_margin_pct * Decimal("100")) if candidate.alex_signal else None,
        "positionSizingMode": "100x_leverage_dynamic_10_30_margin" if candidate.alex_signal else None,
        "stopPrice": decimal_to_str(position.stop_price),
        "target1Price": decimal_to_str(position.target1_price),
        "target2Price": decimal_to_str(position.target2_price),
        "cardTarget2Price": decimal_to_str(card_take_profit),
        "feeFloorTargetExtended": fee_safe_take_profit != card_take_profit,
        "exitBasis": position.exit_basis,
        "techniqueId": position.technique_id,
        "techniqueName": position.technique_name,
        "entryStage": candidate.entry_stage,
        "confirmationCount": candidate.confirmation_count,
        "reason": candidate.reason,
    }


def increase_positions_to_full_deploy(
    state: FuturesPaperState,
    prices: dict[str, Decimal],
    candidates: list[FuturesPaperCandidate],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not state.positions:
        return actions

    candidate_by_symbol = {candidate.symbol: candidate for candidate in candidates}
    ranked_positions = sorted(
        state.positions.values(),
        key=lambda position: candidate_by_symbol.get(position.symbol, FuturesPaperCandidate(position.symbol, position.side, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), "")).score,
        reverse=True,
    )

    for index, position in enumerate(ranked_positions):
        candidate = candidate_by_symbol.get(position.symbol)
        if candidate is None or candidate.side != position.side or not is_entry_eligible(candidate):
            continue
        price = prices.get(position.symbol)
        if price is None or price <= 0:
            continue
        equity = state.equity(prices)
        remaining = remaining_target_margin(state, equity)
        deployable = min(remaining, fee_adjusted_available_margin(state.available_balance(prices)))
        positions_left = len(ranked_positions) - index
        if deployable <= MIN_TOP_UP_MARGIN_USDT or positions_left <= 0:
            break
        split_margin = deployable / Decimal(positions_left)
        deploy_margin = deployable if split_margin < MIN_TOP_UP_MARGIN_USDT else split_margin
        action = increase_position_margin(state, position, price, deploy_margin)
        if action is not None:
            actions.append(action)
        if deploy_margin == deployable:
            break
    return actions


def remaining_target_margin(state: FuturesPaperState, equity: Decimal) -> Decimal:
    target_total_margin = equity * DEFAULT_DEPLOY_PCT
    return max(target_total_margin - state.used_margin(), Decimal("0"))


def fee_adjustment_multiplier(leverage: Decimal = DEFAULT_LEVERAGE) -> Decimal:
    return Decimal("1") + leverage * DEFAULT_FEE_RATE


def fee_adjusted_available_margin(
    available: Decimal,
    leverage: Decimal = DEFAULT_LEVERAGE,
    fee_rate: Decimal = DEFAULT_FEE_RATE,
) -> Decimal:
    if available <= 0:
        return Decimal("0")
    return available / (Decimal("1") + leverage * fee_rate)


def increase_position_margin(
    state: FuturesPaperState,
    position: FuturesPaperPosition,
    price: Decimal,
    deploy_margin: Decimal,
) -> dict[str, Any] | None:
    if deploy_margin <= MIN_TOP_UP_MARGIN_USDT or price <= 0:
        return None
    leverage = DEFAULT_LEVERAGE
    notional = deploy_margin * leverage
    added_quantity = notional / price
    fee = notional * DEFAULT_FEE_RATE
    total_quantity = position.quantity + added_quantity
    if total_quantity <= 0:
        return None
    previous_quantity = position.quantity
    previous_entry = position.entry_price
    position.entry_price = ((position.entry_price * position.quantity) + (price * added_quantity)) / total_quantity
    position.quantity = total_quantity
    position.margin_usdt += deploy_margin
    position.leverage = leverage
    state.wallet_balance_usdt -= fee
    state.fees_paid_usdt += fee
    state.open_fees_paid_usdt += fee
    state.order_count += 1
    state.last_order_at = utc_now()
    return {
        "type": "INCREASE",
        "symbol": position.symbol,
        "side": position.side,
        "price": decimal_to_str(price),
        "quantity": decimal_to_str(added_quantity),
        "previousQuantity": decimal_to_str(previous_quantity),
        "previousEntryPrice": decimal_to_str(previous_entry),
        "entryPrice": decimal_to_str(position.entry_price),
        "leverage": decimal_to_str(leverage),
        "marginUsdt": decimal_to_str(deploy_margin),
        "notionalUsdt": decimal_to_str(notional),
        "feeUsdt": decimal_to_str(fee),
        "reason": "full-equity deploy top-up",
    }


def close_position(
    state: FuturesPaperState,
    position: FuturesPaperPosition,
    price: Decimal,
    reason: str,
) -> dict[str, Any]:
    pnl = position.unrealized_pnl(price)
    notional = position.notional(price)
    fee_rate = futures_position_fee_rate(position)
    fee = notional * fee_rate
    state.wallet_balance_usdt += pnl - fee
    state.realized_pnl_usdt += pnl - fee
    state.gross_realized_pnl_usdt += pnl
    state.fees_paid_usdt += fee
    state.close_fees_paid_usdt += fee
    state.order_count += 1
    now = utc_now()
    state.last_order_at = now
    state.last_closed_candles[position.symbol] = order_minute_bucket(now)
    state.positions.pop(position.symbol, None)
    return {
        "type": "CLOSE",
        "symbol": position.symbol,
        "side": position.side,
        "price": decimal_to_str(price),
        "quantity": decimal_to_str(position.quantity),
        "pnlUsdt": decimal_to_str(pnl),
        "feeRate": decimal_to_str(fee_rate),
        "zeroFeeExperiment": bool(position.exit_basis.startswith("alex") and ALEX_ZERO_FEE_EXPERIMENT),
        "feeUsdt": decimal_to_str(fee),
        "realizedAfterFeeUsdt": decimal_to_str(pnl - fee),
        "returnOnMarginPct": decimal_to_str(position.return_on_margin_pct(price)),
        "reason": reason,
    }


def normalize_manual_futures_action(action: str | None) -> Literal["LONG", "SHORT", "STOP", "MANUAL", "AUTO"]:
    normalized = str(action or "").strip().upper()
    aliases = {
        "M": "MANUAL",
        "MANUAL": "MANUAL",
        "수동": "MANUAL",
        "A": "AUTO",
        "AUTO": "AUTO",
        "자동": "AUTO",
        "L": "LONG",
        "LONG": "LONG",
        "BUY": "LONG",
        "롱": "LONG",
        "S": "SHORT",
        "SHORT": "SHORT",
        "SELL": "SHORT",
        "숏": "SHORT",
        "STOP": "STOP",
        "CLOSE": "STOP",
        "FLAT": "STOP",
        "스탑": "STOP",
        "정지": "STOP",
    }
    mapped = aliases.get(normalized)
    if mapped not in {"LONG", "SHORT", "STOP", "MANUAL", "AUTO"}:
        raise ValueError(f"Unsupported manual futures action: {action}")
    return mapped  # type: ignore[return-value]


def open_manual_futures_position(
    state: FuturesPaperState,
    symbol: str,
    side: FuturesSide,
    price: Decimal,
    prices: dict[str, Decimal],
    requested_margin_usdt: Decimal | None = None,
    requested_margin_percent: Decimal | None = None,
) -> dict[str, Any] | None:
    leverage = MAEUKNAM_EXPERIMENT_LEVERAGE
    available = state.available_balance(prices)
    max_margin = fee_adjusted_available_margin(available, leverage)
    deploy_margin = max_margin
    sizing_note = "100% available balance"
    if requested_margin_percent is not None:
        pct = max(Decimal("0"), min(Decimal("100"), requested_margin_percent))
        deploy_margin = max_margin * pct / Decimal("100")
        sizing_note = f"{decimal_to_str(pct)}% of available balance"
    if requested_margin_usdt is not None and requested_margin_usdt > 0:
        deploy_margin = min(requested_margin_usdt, max_margin)
        sizing_note = f"requested {decimal_to_str(requested_margin_usdt)} USDT margin"
    if deploy_margin <= Decimal("5") or price <= 0:
        return None
    notional = deploy_margin * leverage
    quantity = notional / price
    fee = notional * DEFAULT_FEE_RATE
    now = utc_now()
    state.wallet_balance_usdt -= fee
    state.fees_paid_usdt += fee
    state.open_fees_paid_usdt += fee
    state.order_count += 1
    state.last_order_at = now
    position = FuturesPaperPosition(
        symbol=symbol,
        side=side,
        quantity=quantity,
        entry_price=price,
        leverage=leverage,
        margin_usdt=deploy_margin,
        opened_at=now,
        reason=f"manual full-equity {side} hold until explicit switch command",
        stop_price=Decimal("0"),
        target1_price=Decimal("0"),
        target2_price=Decimal("0"),
        exit_basis=MANUAL_HOLD_EXIT_BASIS,
        technique_id=f"manual_full_equity_{side.lower()}",
        technique_name=f"Manual Full Equity {side}",
    )
    state.positions[symbol] = position
    return {
        "type": "OPEN",
        "symbol": symbol,
        "side": side,
        "analysisSide": side,
        "executionSide": side,
        "price": decimal_to_str(price),
        "quantity": decimal_to_str(quantity),
        "leverage": decimal_to_str(leverage),
        "marginUsdt": decimal_to_str(deploy_margin),
        "requestedMarginUsdt": decimal_to_str(requested_margin_usdt) if requested_margin_usdt is not None else None,
        "marginPercent": decimal_to_str(requested_margin_percent) if requested_margin_percent is not None else None,
        "maxMarginUsdt": decimal_to_str(max_margin),
        "sizingNote": sizing_note,
        "notionalUsdt": decimal_to_str(notional),
        "feeUsdt": decimal_to_str(fee),
        "exitBasis": MANUAL_HOLD_EXIT_BASIS,
        "techniqueId": position.technique_id,
        "techniqueName": position.technique_name,
        "reason": position.reason,
    }


def manual_futures_paper_trade(
    settings: TradingSettings,
    client: BinanceFuturesClient,
    action: str,
    symbol: str = MAEUKNAM_BTC_ONLY_SYMBOL,
    margin_usdt: Decimal | None = None,
    margin_percent: Decimal | None = None,
) -> dict[str, Any]:
    manual_action = normalize_manual_futures_action(action)
    clean_symbol = "".join(ch for ch in str(symbol or MAEUKNAM_BTC_ONLY_SYMBOL).upper() if ch.isalnum())
    if not clean_symbol.endswith("USDT"):
        raise ValueError(f"Manual futures paper symbol must be a USDT perpetual symbol: {symbol}")

    store = FuturesPaperStateStore(futures_paper_state_path(settings))
    state = store.load()
    price_symbols = tuple(dict.fromkeys([clean_symbol, *state.positions.keys()]))
    prices = fetch_futures_prices(client, price_symbols)
    if prices.get(clean_symbol, Decimal("0")) <= 0:
        raise ValueError(f"Manual futures paper price is unavailable for {clean_symbol}")

    actions: list[dict[str, Any]] = []
    existing_position = state.positions.get(clean_symbol)
    if manual_action == "AUTO":
        for position in state.positions.values():
            if position.exit_basis == MANUAL_HOLD_EXIT_BASIS:
                position.exit_basis = AUTO_RELEASED_MANUAL_EXIT_BASIS
                position.reason = f"{position.reason}; automatic mode restored"
        state.manual_action = None
        store.save(state)
        payload = state_payload(state, prices)
        status_side = maeuknam_status_side(state)
        payload["paperSide"] = futures_strategy_side(settings)
        payload["strategySide"] = futures_strategy_side(settings)
        payload["analysisSide"] = status_side
        payload["executionSide"] = status_side
        payload["exitBasis"] = "alex_method_levels" if alex_futures_mode(settings) else "maeuknam_card_levels"
        payload["leverage"] = decimal_to_str(MAEUKNAM_EXPERIMENT_LEVERAGE)
        payload["maxOpenPositions"] = futures_paper_max_open_positions(maeuknam_only=True)
        payload["manualMode"] = False
        payload["manualAction"] = None
        payload["requestedMarginUsdt"] = decimal_to_str(margin_usdt) if margin_usdt is not None else None
        payload["marginPercent"] = decimal_to_str(margin_percent) if margin_percent is not None else None
        payload["actions"] = actions
        payload["message"] = (
            "Automatic Binance futures paper mode restored; "
            f"{'Alex-method' if alex_futures_mode(settings) else 'Maeuknam-card'} cycle may manage positions again."
        )
        payload["updatedAt"] = utc_now()
        return payload

    if manual_action == "MANUAL":
        active_position = existing_position or next(iter(state.positions.values()), None)
        if active_position is None:
            manual_action = "STOP"
        else:
            clean_symbol = active_position.symbol
            existing_position = active_position
            active_position.exit_basis = MANUAL_HOLD_EXIT_BASIS
            manual_action = active_position.side

    if (
        manual_action in {"LONG", "SHORT"}
        and existing_position is not None
        and len(state.positions) == 1
        and existing_position.side == manual_action
        and existing_position.exit_basis == MANUAL_HOLD_EXIT_BASIS
        and margin_usdt is None
        and margin_percent is None
    ):
        state.manual_action = manual_action
        store.save(state)
        payload = state_payload(state, prices)
        payload["paperSide"] = futures_strategy_side(settings)
        payload["strategySide"] = futures_strategy_side(settings)
        payload["analysisSide"] = manual_action
        payload["executionSide"] = manual_action
        payload["exitBasis"] = MANUAL_HOLD_EXIT_BASIS
        payload["leverage"] = decimal_to_str(MAEUKNAM_EXPERIMENT_LEVERAGE)
        payload["maxOpenPositions"] = futures_paper_max_open_positions(maeuknam_only=True)
        payload["manualMode"] = True
        payload["manualAction"] = manual_action
        payload["requestedMarginUsdt"] = decimal_to_str(margin_usdt) if margin_usdt is not None else None
        payload["marginPercent"] = decimal_to_str(margin_percent) if margin_percent is not None else None
        payload["actions"] = actions
        payload["message"] = f"Manual Binance futures paper {manual_action} is already active."
        payload["updatedAt"] = utc_now()
        return payload

    for existing_symbol, position in list(state.positions.items()):
        close_price = prices.get(existing_symbol, position.entry_price)
        if close_price <= 0:
            close_price = position.entry_price
        actions.append(
            close_position(
                state,
                position,
                close_price,
                f"manual {manual_action} command closes existing {position.side}",
            )
        )

    if manual_action in {"LONG", "SHORT"}:
        actions_open = open_manual_futures_position(
            state,
            clean_symbol,
            manual_action,  # type: ignore[arg-type]
            prices[clean_symbol],
            {clean_symbol: prices[clean_symbol]},
            requested_margin_usdt=margin_usdt,
            requested_margin_percent=margin_percent,
        )
        if actions_open is None:
            raise ValueError("Manual futures paper account does not have enough available balance to open a position.")
        actions.append(actions_open)

    state.manual_action = manual_action
    store.save(state)
    payload = state_payload(state, prices)
    status_side = manual_action if manual_action != "STOP" else "FLAT"
    payload["paperSide"] = futures_strategy_side(settings)
    payload["strategySide"] = futures_strategy_side(settings)
    payload["analysisSide"] = status_side
    payload["executionSide"] = status_side
    payload["exitBasis"] = MANUAL_HOLD_EXIT_BASIS
    payload["leverage"] = decimal_to_str(MAEUKNAM_EXPERIMENT_LEVERAGE)
    payload["maxOpenPositions"] = futures_paper_max_open_positions(maeuknam_only=True)
    payload["manualMode"] = True
    payload["manualAction"] = manual_action
    payload["requestedMarginUsdt"] = decimal_to_str(margin_usdt) if margin_usdt is not None else None
    payload["marginPercent"] = decimal_to_str(margin_percent) if margin_percent is not None else None
    payload["actions"] = actions
    payload["message"] = f"Manual Binance futures paper {manual_action} applied."
    payload["updatedAt"] = utc_now()
    return payload


def futures_price_for_margin_return(position: FuturesPaperPosition, return_on_margin_pct: Decimal) -> Decimal:
    if position.leverage <= 0:
        return position.entry_price
    move_pct = return_on_margin_pct / Decimal("100") / position.leverage
    if position.side == "LONG":
        return position.entry_price * (Decimal("1") + move_pct)
    return position.entry_price * (Decimal("1") - move_pct)


def state_payload(state: FuturesPaperState, prices: dict[str, Decimal]) -> dict[str, Any]:
    positions = []
    total_notional = Decimal("0")
    for symbol, position in sorted(state.positions.items()):
        price = prices.get(symbol, position.entry_price)
        notional = position.notional(price)
        total_notional += notional
        take_profit_price = position.take_profit_price()
        if take_profit_price <= 0:
            take_profit_price = futures_price_for_margin_return(position, TAKE_PROFIT_MARGIN_PCT)
        stop_loss_price = position.stop_price
        if stop_loss_price <= 0:
            stop_loss_price = futures_price_for_margin_return(position, STOP_LOSS_MARGIN_PCT)
        positions.append(
            {
                "symbol": symbol,
                "side": position.side,
                "quantity": decimal_to_str(position.quantity),
                "entryPrice": decimal_to_str(position.entry_price),
                "currentPrice": decimal_to_str(price),
                "marginUsdt": decimal_to_str(position.margin_usdt),
                "notionalUsdt": decimal_to_str(notional),
                "leverage": decimal_to_str(position.leverage),
                "priceMovePct": decimal_to_str(position.price_move_pct(price)),
                "unrealizedPnlUsdt": decimal_to_str(position.unrealized_pnl(price)),
                "returnOnMarginPct": decimal_to_str(position.return_on_margin_pct(price)),
                "takeProfitPrice": decimal_to_str(take_profit_price),
                "stopLossPrice": decimal_to_str(stop_loss_price),
                "target1Price": decimal_to_str(position.target1_price),
                "target2Price": decimal_to_str(position.target2_price),
                "exitBasis": position.exit_basis,
                "techniqueId": position.technique_id,
                "techniqueName": position.technique_name,
                "openedAt": position.opened_at,
                "reason": position.reason,
            }
        )
    return {
        "mode": "local-binance-futures-paper",
        "simulated": True,
        "currency": "USDT",
        "quoteAsset": "USDT",
        "aggressive": True,
        "paperSide": STRATEGY_SIDE,
        "strategySide": STRATEGY_SIDE,
        "leverage": decimal_to_str(DEFAULT_LEVERAGE),
        "maxOpenPositions": MAX_OPEN_POSITIONS,
        "deployPct": decimal_to_str(DEFAULT_DEPLOY_PCT),
        "takeProfitMarginPct": decimal_to_str(TAKE_PROFIT_MARGIN_PCT),
        "stopLossMarginPct": decimal_to_str(STOP_LOSS_MARGIN_PCT),
        "exitBasis": "fixed_roe_guard",
        "goalStartUsdt": decimal_to_str(DEFAULT_WALLET_BALANCE_USDT),
        "goalTargetUsdt": decimal_to_str(DEFAULT_WALLET_BALANCE_USDT * Decimal("100")),
        "walletBalanceUsdt": decimal_to_str(state.wallet_balance_usdt),
        "availableBalanceUsdt": decimal_to_str(state.available_balance(prices)),
        "usedMarginUsdt": decimal_to_str(state.used_margin()),
        "totalNotionalUsdt": decimal_to_str(total_notional),
        "equityUsdt": decimal_to_str(state.equity(prices)),
        "unrealizedPnlUsdt": decimal_to_str(state.unrealized_pnl(prices)),
        "realizedPnlUsdt": decimal_to_str(state.realized_pnl_usdt),
        "grossRealizedPnlUsdt": decimal_to_str(state.gross_realized_pnl_usdt),
        "pricePnlUsdt": decimal_to_str(state.gross_realized_pnl_usdt + state.unrealized_pnl(prices)),
        "feesPaidUsdt": decimal_to_str(state.fees_paid_usdt),
        "openFeesPaidUsdt": decimal_to_str(state.open_fees_paid_usdt),
        "closeFeesPaidUsdt": decimal_to_str(state.close_fees_paid_usdt),
        "orderCount": state.order_count,
        "openPositions": len(state.positions),
        "lastOrderAt": state.last_order_at,
        "manualAction": state.manual_action,
        "positions": positions,
    }


def cycle_message(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "No futures paper order was needed in this cycle."
    if len(actions) > 1:
        return f"Applied {len(actions)} futures paper action(s)."
    first = actions[0]
    if first.get("type") == "OPEN":
        return f"Opened {first.get('side')} paper position on {first.get('symbol')}."
    if first.get("type") == "CLOSE":
        return f"Closed {first.get('side')} paper position on {first.get('symbol')}."
    return f"Applied {len(actions)} futures paper action(s)."
