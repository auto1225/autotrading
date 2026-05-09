from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
import json
import os
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from upbit_autotrader.config import TradingSettings  # noqa: E402
from upbit_autotrader.config import load_settings  # noqa: E402
from upbit_autotrader.learning import LEARNABLE_STRATEGY_NAMES  # noqa: E402
from upbit_autotrader.market_regime import evaluate_market_regime  # noqa: E402
from upbit_autotrader.market_risk import evaluate_market_risk  # noqa: E402
from upbit_autotrader.models import Candle  # noqa: E402
from upbit_autotrader.models import Signal  # noqa: E402
from upbit_autotrader.models import decimal_to_str  # noqa: E402
from upbit_autotrader.pattern_learning import (  # noqa: E402
    PatternObservation,
    build_pattern_model,
    feature_snapshot,
    save_pattern_model,
    score_current_pattern,
    simulate_strategy_observations,
    update_pattern_model_with_observation,
)
from upbit_autotrader.strategy import make_strategy_by_name  # noqa: E402
from upbit_autotrader.upbit_client import UpbitClient  # noqa: E402


KST = timezone(timedelta(hours=9), "KST")
UTC = timezone.utc
START_KST = datetime.fromisoformat(os.environ.get("SIM_START_KST", "2026-04-04T00:00:00+09:00"))
UNIT = int(os.environ.get("SIM_UNIT", "5"))
MAX_MARKETS = int(os.environ.get("SIM_MAX_MARKETS", "25"))
STARTING_CASH = Decimal(os.environ.get("SIM_STARTING_CASH", "1000000"))
HISTORY_LIMIT = int(os.environ.get("SIM_HISTORY_LIMIT", "240"))
SCAN_STRIDE = int(os.environ.get("SIM_SCAN_STRIDE", "3"))
REQUEST_PAUSE_SECONDS = float(os.environ.get("SIM_REQUEST_PAUSE_SECONDS", "0.10"))
TOP_LIQUIDITY_FILL = int(os.environ.get("SIM_TOP_LIQUIDITY_FILL", "80"))


@dataclass(frozen=True)
class StrategyPick:
    market: str
    strategy: str
    score: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    order_count: int
    final_equity_krw: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "strategy": self.strategy,
            "score": decimal_to_str(self.score),
            "totalReturnPct": decimal_to_str(self.total_return_pct),
            "maxDrawdownPct": decimal_to_str(self.max_drawdown_pct),
            "orderCount": self.order_count,
            "finalEquityKrw": decimal_to_str(self.final_equity_krw),
        }


@dataclass
class SimPosition:
    market: str
    volume: Decimal = Decimal("0")
    cost_krw: Decimal = Decimal("0")

    @property
    def avg_entry_price(self) -> Decimal:
        if self.volume <= 0:
            return Decimal("0")
        return self.cost_krw / self.volume

    def value(self, price: Decimal) -> Decimal:
        return self.volume * price


@dataclass
class SimulationState:
    cash_krw: Decimal
    positions: dict[str, SimPosition]
    fees_paid_krw: Decimal = Decimal("0")
    realized_pnl_krw: Decimal = Decimal("0")
    order_count: int = 0
    daily_order_count: int = 0
    current_day: str = ""


def d(value: Any) -> Decimal:
    return Decimal(str(value))


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return decimal_to_str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def request_with_retry(func, *args, **kwargs):
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.6 + attempt * 0.8)
    assert last_error is not None
    raise last_error


def parse_upbit_utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def fetch_range_candles(
    client: UpbitClient,
    market: str,
    unit: int,
    start_kst: datetime,
    end_kst: datetime,
) -> list[Candle]:
    start_ms = int(start_kst.timestamp() * 1000)
    end_ms = int(end_kst.timestamp() * 1000)
    candles_by_timestamp: dict[int, Candle] = {}
    cursor_to = end_kst.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")

    while True:
        raw_page = request_with_retry(client.get_minute_candles, market=market, unit=unit, count=200, to=cursor_to)
        if not raw_page:
            break

        page = [Candle.from_upbit(item) for item in raw_page]
        for candle in page:
            if start_ms <= candle.timestamp <= end_ms:
                candles_by_timestamp[candle.timestamp] = candle

        oldest = min(page, key=lambda candle: candle.timestamp)
        if oldest.timestamp < start_ms or len(raw_page) < 200:
            break

        oldest_dt = parse_upbit_utc(oldest.candle_date_time_utc) - timedelta(seconds=1)
        cursor_to = oldest_dt.strftime("%Y-%m-%dT%H:%M:%S")
        time.sleep(REQUEST_PAUSE_SECONDS)

    return sorted(candles_by_timestamp.values(), key=lambda candle: candle.timestamp)


def is_warning_market(item: dict[str, Any]) -> bool:
    event = item.get("market_event")
    if not isinstance(event, dict):
        return False
    if event.get("warning"):
        return True
    caution = event.get("caution")
    if isinstance(caution, dict):
        return any(bool(value) for value in caution.values())
    return bool(caution)


def krw_markets(client: UpbitClient) -> list[str]:
    raw = request_with_retry(client.get_markets, is_details=True)
    result: list[str] = []
    for item in raw:
        market = str(item.get("market") or "").upper()
        if market.startswith("KRW-") and not is_warning_market(item):
            result.append(market)
    return list(dict.fromkeys(result))


def top_liquidity_markets(client: UpbitClient, candidates: list[str], limit: int) -> list[str]:
    rows: list[tuple[Decimal, str]] = []
    for index in range(0, len(candidates), 90):
        chunk = candidates[index : index + 90]
        tickers = request_with_retry(client.get_ticker, chunk)
        for ticker in tickers:
            market = str(ticker.get("market") or "")
            trade_value = d(ticker.get("acc_trade_price_24h") or "0")
            rows.append((trade_value, market))
        time.sleep(REQUEST_PAUSE_SECONDS)
    rows.sort(reverse=True)
    return [market for _, market in rows[:limit]]


def prior_learning_recommendations(settings: TradingSettings) -> dict[str, tuple[str, Decimal]]:
    path = settings.state_file.parent / "learning_model.json"
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        markets = payload.get("markets") if isinstance(payload, dict) else None
        if isinstance(markets, dict):
            result: dict[str, tuple[str, Decimal]] = {}
            for market, row in markets.items():
                if not isinstance(row, dict):
                    continue
                strategy = str(row.get("bestStrategy") or "")
                if strategy in LEARNABLE_STRATEGY_NAMES:
                    result[str(market)] = (strategy, d(row.get("score") or "0"))
            return result
    except (OSError, json.JSONDecodeError):
        pass

    raw = path.read_text(encoding="utf-8", errors="ignore")
    ranking_index = raw.find('"ranking"')
    if ranking_index >= 0:
        raw = raw[ranking_index:]

    result: dict[str, tuple[str, Decimal]] = {}
    current: dict[str, str] = {}
    for line in raw.splitlines():
        market_match = re.search(r'"market"\s*:\s*"(KRW-[A-Z0-9-]+)"', line)
        strategy_match = re.search(r'"strategy"\s*:\s*"([a-z_]+)"', line)
        score_match = re.search(r'"score"\s*:\s*"([-0-9.]+)"', line)
        if market_match:
            current["market"] = market_match.group(1)
        if strategy_match:
            current["strategy"] = strategy_match.group(1)
        if score_match:
            current["score"] = score_match.group(1)
        if line.strip().startswith("}") and "market" in current and "strategy" in current:
            strategy = current["strategy"]
            market = current["market"]
            if strategy in LEARNABLE_STRATEGY_NAMES and market not in result:
                result[market] = (strategy, d(current.get("score") or "0"))
            current = {}
    return result


def select_markets(settings: TradingSettings, client: UpbitClient) -> tuple[list[str], dict[str, tuple[str, Decimal]]]:
    available = krw_markets(client)
    available_set = set(available)
    prior = prior_learning_recommendations(settings)
    selected: list[str] = []

    prior_ranked = sorted(prior.items(), key=lambda item: item[1][1], reverse=True)
    for market, _recommendation in prior_ranked:
        if market in available_set and market not in selected:
            selected.append(market)
        if len(selected) >= MAX_MARKETS:
            return selected, prior

    for market in settings.markets:
        if market in available_set and market not in selected:
            selected.append(market)
        if len(selected) >= MAX_MARKETS:
            return selected, prior

    for market in top_liquidity_markets(client, available, TOP_LIQUIDITY_FILL):
        if market not in selected:
            selected.append(market)
        if len(selected) >= MAX_MARKETS:
            break

    return selected, prior


def moving_average(values: list[Decimal], window: int) -> Decimal:
    if len(values) < window:
        return values[-1] if values else Decimal("0")
    return sum(values[-window:], Decimal("0")) / Decimal(window)


def trend_hold_exit(candles: list[Candle], position: SimPosition, settings: TradingSettings) -> bool:
    if not candles or position.volume <= 0 or position.avg_entry_price <= 0:
        return False

    latest = candles[-1]
    pnl_pct = (latest.trade_price - position.avg_entry_price) / position.avg_entry_price * Decimal("100")
    if pnl_pct <= -settings.stop_loss_pct:
        return True

    if pnl_pct < settings.take_profit_pct:
        return False

    closes = [candle.trade_price for candle in candles]
    current_short = moving_average(closes, settings.short_window)
    current_long = moving_average(closes, settings.long_window)
    recent_high = max(closes[-settings.long_window :]) if len(closes) >= settings.long_window else max(closes)
    pullback_pct = (latest.trade_price - recent_high) / recent_high * Decimal("100") if recent_high > 0 else Decimal("0")
    return current_short < current_long or pullback_pct <= -settings.strategy_pullback_sell_pct


def equity(state: SimulationState, latest_prices: dict[str, Decimal]) -> Decimal:
    total = state.cash_krw
    for market, position in state.positions.items():
        price = latest_prices.get(market, Decimal("0"))
        total += position.value(price)
    return total


def buy(state: SimulationState, market: str, price: Decimal, budget: Decimal, fee_rate: Decimal) -> None:
    if budget <= 0 or price <= 0:
        return
    fee = budget * fee_rate
    volume = (budget - fee) / price
    position = state.positions.setdefault(market, SimPosition(market=market))
    position.volume += volume
    position.cost_krw += budget
    state.cash_krw -= budget
    state.fees_paid_krw += fee
    state.order_count += 1
    state.daily_order_count += 1


def sell(state: SimulationState, market: str, price: Decimal, fee_rate: Decimal) -> None:
    position = state.positions.get(market)
    if position is None or position.volume <= 0 or price <= 0:
        return
    gross = position.volume * price
    fee = gross * fee_rate
    net = gross - fee
    state.cash_krw += net
    state.fees_paid_krw += fee
    state.realized_pnl_krw += net - position.cost_krw
    state.order_count += 1
    state.daily_order_count += 1
    position.volume = Decimal("0")
    position.cost_krw = Decimal("0")


def score_return(total_return_pct: Decimal, max_drawdown_pct: Decimal, order_count: int) -> Decimal:
    drawdown_penalty = abs(max_drawdown_pct) * Decimal("0.65")
    idle_penalty = Decimal("2.5") if order_count == 0 else Decimal("0")
    churn_penalty = max(0, order_count - 80) * Decimal("0.02")
    return total_return_pct - drawdown_penalty - idle_penalty - churn_penalty


def simulate_single_strategy(
    market: str,
    candles: list[Candle],
    settings: TradingSettings,
    strategy_name: str,
    stride: int,
) -> StrategyPick:
    strategy_settings = replace(settings, market=market, markets=(market,), strategy_name=strategy_name)
    strategy = make_strategy_by_name(strategy_settings, strategy_name)
    state = SimulationState(cash_krw=STARTING_CASH, positions={})
    latest_prices: dict[str, Decimal] = {}
    peak = STARTING_CASH
    max_drawdown = Decimal("0")
    start_index = max(settings.long_window + 1, 60)

    for index in range(start_index, len(candles), max(1, stride)):
        history = candles[max(0, index + 1 - HISTORY_LIMIT) : index + 1]
        current = history[-1]
        latest_prices[market] = current.trade_price
        position = state.positions.get(market, SimPosition(market=market))
        signal = strategy.evaluate(history)

        if position.volume > 0 and (signal.action == "sell" or trend_hold_exit(history, position, settings)):
            sell(state, market, current.trade_price, settings.fee_rate)
        elif position.volume <= 0 and signal.action == "buy" and state.cash_krw >= settings.min_order_krw:
            buy(state, market, current.trade_price, state.cash_krw, settings.fee_rate)

        current_equity = equity(state, latest_prices)
        peak = max(peak, current_equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, (current_equity - peak) / peak * Decimal("100"))

    final_price = candles[-1].trade_price if candles else Decimal("0")
    latest_prices[market] = final_price
    final_equity = equity(state, latest_prices)
    total_return_pct = (final_equity - STARTING_CASH) / STARTING_CASH * Decimal("100")
    return StrategyPick(
        market=market,
        strategy=strategy_name,
        score=score_return(total_return_pct, max_drawdown, state.order_count),
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown,
        order_count=state.order_count,
        final_equity_krw=final_equity,
    )


def pick_strategy_for_market(
    market: str,
    candles: list[Candle],
    settings: TradingSettings,
    prior: dict[str, tuple[str, Decimal]],
) -> tuple[StrategyPick, list[StrategyPick]]:
    strategy_names = tuple(LEARNABLE_STRATEGY_NAMES)
    picks = [
        simulate_single_strategy(market, candles, settings, strategy_name, SCAN_STRIDE)
        for strategy_name in strategy_names
    ]
    picks.sort(key=lambda item: item.score, reverse=True)

    prior_row = prior.get(market)
    if prior_row is None:
        return picks[0], picks

    prior_strategy, prior_score = prior_row
    prior_pick = next((item for item in picks if item.strategy == prior_strategy), None)
    if prior_pick is None:
        return picks[0], picks

    if picks[0].score - prior_pick.score <= Decimal("0.15") and prior_score > Decimal("0"):
        return prior_pick, picks
    return picks[0], picks


def recent_return_pct(candles: list[Candle], lookback: int = 12) -> Decimal:
    if len(candles) <= lookback:
        return Decimal("0")
    start = candles[-lookback - 1].trade_price
    end = candles[-1].trade_price
    if start <= 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def recent_volatility_pct(candles: list[Candle], window: int = 12) -> Decimal:
    subset = candles[-window:]
    ranges = [
        (candle.high_price - candle.low_price) / candle.trade_price * Decimal("100")
        for candle in subset
        if candle.trade_price > 0
    ]
    if not ranges:
        return Decimal("0")
    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def recent_drawdown_pct(candles: list[Candle], window: int = 30) -> Decimal:
    subset = candles[-window:]
    if not subset:
        return Decimal("0")
    high = max(candle.high_price for candle in subset)
    if high <= 0:
        return Decimal("0")
    return (subset[-1].trade_price - high) / high * Decimal("100")


def recent_volume_ratio(candles: list[Candle], window: int = 20) -> Decimal:
    if len(candles) < 2:
        return Decimal("1")
    previous = candles[max(0, len(candles) - window - 1) : -1]
    if not previous:
        return Decimal("1")
    average = sum((candle.candle_acc_trade_price for candle in previous), Decimal("0")) / Decimal(len(previous))
    if average <= 0:
        return Decimal("1")
    return candles[-1].candle_acc_trade_price / average


def recent_range_position_pct(candles: list[Candle], window: int = 30) -> Decimal:
    subset = candles[-window:]
    if not subset:
        return Decimal("50")
    high = max(candle.high_price for candle in subset)
    low = min(candle.low_price for candle in subset)
    if high <= low:
        return Decimal("50")
    return (subset[-1].trade_price - low) / (high - low) * Decimal("100")


def simulation_risk_signal(
    settings: TradingSettings,
    pattern_model: dict[str, Any] | None,
    market: str,
    position: SimPosition,
    history: list[Candle],
    strategy: str = "",
):
    return evaluate_market_risk(
        settings=settings,
        pattern_model=pattern_model,
        market=market,
        held=position.volume > 0,
        trend_1m_pct=recent_return_pct(history, 1),
        trend_5m_pct=recent_return_pct(history, 5),
        trend_30m_pct=recent_return_pct(history, 30),
        volatility_pct=recent_volatility_pct(history, 12),
        drawdown_pct=recent_drawdown_pct(history, 30),
        volume_ratio=recent_volume_ratio(history, 20),
        range_position_pct=recent_range_position_pct(history, 30),
        latest_candle_trade_value_krw=history[-1].candle_acc_trade_price if history else None,
        strategy=strategy,
        now=datetime.fromtimestamp(history[-1].timestamp / 1000, KST) if history else None,
    )


def record_simulation_entry(
    open_entries: dict[str, dict[str, Any]],
    market: str,
    strategy: str,
    history: list[Candle],
    price: Decimal,
) -> None:
    if price <= 0 or not history:
        return
    open_entries[market] = {
        "market": market,
        "strategy": strategy,
        "entryTime": datetime.fromtimestamp(history[-1].timestamp / 1000, KST).isoformat(),
        "entryPrice": price,
        "features": feature_snapshot(history),
    }


def record_simulation_exit(
    pattern_model: dict[str, Any] | None,
    open_entries: dict[str, dict[str, Any]],
    market: str,
    history: list[Candle],
    price: Decimal,
    fee_rate: Decimal,
) -> dict[str, Any] | None:
    entry = open_entries.pop(market, None)
    if not entry or price <= 0 or not history:
        return pattern_model
    entry_price = Decimal(str(entry["entryPrice"]))
    net_return = ((price / entry_price) * (Decimal("1") - fee_rate) * (Decimal("1") - fee_rate) - Decimal("1")) * Decimal("100")
    observation = PatternObservation(
        market=market,
        strategy=str(entry["strategy"]),
        entry_time=str(entry["entryTime"]),
        exit_time=datetime.fromtimestamp(history[-1].timestamp / 1000, KST).isoformat(),
        entry_price=entry_price,
        exit_price=price,
        net_return_pct=net_return,
        outcome="profit" if net_return > 0 else "loss",
        features=entry["features"],
    )
    next_model = update_pattern_model_with_observation(pattern_model or {}, observation)
    if pattern_model is not None:
        pattern_model.clear()
        pattern_model.update(next_model)
        return pattern_model
    return next_model


def run_portfolio_simulation(
    candles_by_market: dict[str, list[Candle]],
    picks: dict[str, StrategyPick],
    settings: TradingSettings,
    pattern_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    markets = tuple(candles_by_market.keys())
    portfolio_settings = replace(settings, markets=markets)
    strategies = {
        market: make_strategy_by_name(
            replace(portfolio_settings, market=market, strategy_name=pick.strategy),
            pick.strategy,
        )
        for market, pick in picks.items()
    }

    candles_by_time: dict[str, dict[int, Candle]] = {
        market: {candle.timestamp: candle for candle in candles}
        for market, candles in candles_by_market.items()
    }
    all_times = sorted({timestamp for rows in candles_by_time.values() for timestamp in rows})
    histories: dict[str, list[Candle]] = {market: [] for market in markets}
    latest_prices: dict[str, Decimal] = {}
    state = SimulationState(cash_krw=STARTING_CASH, positions={})
    peak = STARTING_CASH
    max_drawdown = Decimal("0")
    curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    open_entries: dict[str, dict[str, Any]] = {}
    bar_count = 0

    for timestamp in all_times:
        bar_count += 1
        updated_markets: list[str] = []
        current_day = ""
        for market, rows in candles_by_time.items():
            candle = rows.get(timestamp)
            if candle is None:
                continue
            histories[market].append(candle)
            if len(histories[market]) > HISTORY_LIMIT:
                histories[market] = histories[market][-HISTORY_LIMIT:]
            latest_prices[market] = candle.trade_price
            updated_markets.append(market)
            current_day = candle.candle_date_time_kst[:10]

        if current_day and current_day != state.current_day:
            state.current_day = current_day
            state.daily_order_count = 0

        market_regime = evaluate_market_regime(settings, histories)

        # Sells first so fast regime changes can free cash before new entries.
        for market in list(state.positions):
            if market not in updated_markets or state.daily_order_count >= settings.max_daily_orders:
                continue
            position = state.positions[market]
            if position.volume <= 0:
                continue
            history = histories[market]
            if len(history) < settings.long_window + 1:
                continue
            signal = strategies[market].evaluate(history)
            pattern_score = score_current_pattern(pattern_model, market, picks[market].strategy, history)
            risk_signal = simulation_risk_signal(settings, pattern_model, market, position, history, picks[market].strategy)
            if (
                signal.action == "sell"
                or trend_hold_exit(history, position, settings)
                or pattern_score.exit_now
                or risk_signal.exit_now
                or market_regime.block_new_entries
            ):
                before_cash = state.cash_krw
                price = latest_prices[market]
                sell(state, market, price, settings.fee_rate)
                pattern_model = record_simulation_exit(pattern_model, open_entries, market, history, price, settings.fee_rate)
                trades.append(
                    {
                        "time": history[-1].candle_date_time_kst,
                        "market": market,
                        "side": "sell",
                        "price": price,
                        "cashAfter": state.cash_krw,
                        "cashDelta": state.cash_krw - before_cash,
                        "patternScore": pattern_score.to_dict(),
                        "risk": risk_signal.to_dict(),
                    }
                )

        deployed = sum(
            position.value(latest_prices.get(market, Decimal("0")))
            for market, position in state.positions.items()
            if position.volume > 0
        )
        current_equity = equity(state, latest_prices)
        deploy_limit = current_equity * settings.allocation_max_deploy_pct * market_regime.deploy_multiplier
        candidates: list[tuple[Decimal, str, Signal, Any, Any]] = []

        for market in updated_markets:
            if state.daily_order_count >= settings.max_daily_orders:
                break
            history = histories[market]
            if len(history) < settings.long_window + 1:
                continue
            position = state.positions.get(market, SimPosition(market=market))
            current_value = position.value(latest_prices.get(market, Decimal("0")))
            target_value = current_equity * settings.allocation_max_position_pct
            if current_value >= target_value:
                continue
            signal = strategies[market].evaluate(history)
            if signal.action != "buy":
                continue
            pick = picks[market]
            pattern_score = score_current_pattern(pattern_model, market, pick.strategy, history)
            risk_signal = simulation_risk_signal(settings, pattern_model, market, position, history, pick.strategy)
            if pattern_score.blocked or risk_signal.block_entry or market_regime.block_new_entries:
                continue
            rank = (
                pick.score
                + signal.strength
                + recent_return_pct(history) * Decimal("0.08")
                + pattern_score.adjustment
                + risk_signal.score_adjustment
                + market_regime.score_adjustment
            )
            if rank < settings.realtime_min_score + settings.risk_min_entry_score_buffer + market_regime.min_score_adjustment:
                continue
            candidates.append((rank, market, signal, pattern_score, risk_signal))

        candidates.sort(key=lambda item: item[0], reverse=True)
        for _, market, _signal, pattern_score, risk_signal in candidates[: settings.realtime_candidate_top_n]:
            if state.daily_order_count >= settings.max_daily_orders or state.cash_krw < settings.min_order_krw:
                break
            current_equity = equity(state, latest_prices)
            price = latest_prices[market]
            position = state.positions.get(market, SimPosition(market=market))
            current_value = position.value(price)
            target_value = current_equity * settings.allocation_max_position_pct
            available_deploy = max(Decimal("0"), deploy_limit - deployed)
            budget = min(
                state.cash_krw,
                current_equity * settings.realtime_max_order_pct,
                target_value - current_value,
                available_deploy,
            )
            budget = budget.quantize(Decimal("1"))
            if budget < settings.min_order_krw:
                continue
            buy(state, market, price, budget, settings.fee_rate)
            record_simulation_entry(open_entries, market, picks[market].strategy, histories[market], price)
            deployed += budget
            trades.append(
                {
                    "time": histories[market][-1].candle_date_time_kst,
                    "market": market,
                    "side": "buy",
                    "price": price,
                    "budgetKrw": budget,
                    "cashAfter": state.cash_krw,
                    "patternScore": pattern_score.to_dict(),
                    "risk": risk_signal.to_dict(),
                }
            )

        current_equity = equity(state, latest_prices)
        peak = max(peak, current_equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, (current_equity - peak) / peak * Decimal("100"))
        if len(curve) == 0 or bar_count % 12 == 0 or timestamp == all_times[-1]:
            curve.append(
                {
                    "time": datetime.fromtimestamp(timestamp / 1000, KST).isoformat(),
                    "equityKrw": current_equity,
                    "cashKrw": state.cash_krw,
                    "openPositions": sum(1 for position in state.positions.values() if position.volume > 0),
                }
            )

    final_equity = equity(state, latest_prices)
    total_return_pct = (final_equity - STARTING_CASH) / STARTING_CASH * Decimal("100")
    open_positions = [
        {
            "market": market,
            "volume": position.volume,
            "avgEntryPrice": position.avg_entry_price,
            "lastPrice": latest_prices.get(market, Decimal("0")),
            "valueKrw": position.value(latest_prices.get(market, Decimal("0"))),
            "pnlPct": (
                (latest_prices.get(market, Decimal("0")) - position.avg_entry_price)
                / position.avg_entry_price
                * Decimal("100")
                if position.avg_entry_price > 0
                else Decimal("0")
            ),
        }
        for market, position in state.positions.items()
        if position.volume > 0
    ]
    open_positions.sort(key=lambda item: item["valueKrw"], reverse=True)

    return {
        "startEquityKrw": STARTING_CASH,
        "finalEquityKrw": final_equity,
        "totalReturnPct": total_return_pct,
        "realizedPnlKrw": state.realized_pnl_krw,
        "feesPaidKrw": state.fees_paid_krw,
        "orderCount": state.order_count,
        "maxDrawdownPct": max_drawdown,
        "openPositions": open_positions,
        "equityCurve": curve[-240:],
        "trades": trades[-200:],
    }


def build_pattern_model_for_picks(
    candles_by_market: dict[str, list[Candle]],
    picks: dict[str, StrategyPick],
    settings: TradingSettings,
) -> dict[str, Any]:
    observations = []
    for market, pick in picks.items():
        candles = candles_by_market.get(market, [])
        observations.extend(simulate_strategy_observations(market, candles, settings, pick.strategy))
    return build_pattern_model(observations)


def main() -> int:
    os.chdir(ROOT)
    settings = load_settings()
    settings = replace(
        settings,
        candle_unit=UNIT,
        paper_cash_krw=STARTING_CASH,
        max_order_krw=STARTING_CASH,
        max_position_krw=STARTING_CASH,
        cooldown_seconds=0,
    )
    client = UpbitClient(settings.base_url, timeout_seconds=15)
    end_kst = datetime.now(KST)

    selected_markets, prior = select_markets(settings, client)
    print(f"range={START_KST.isoformat()}..{end_kst.isoformat()} unit={UNIT}m markets={len(selected_markets)}")
    print("markets=" + ",".join(selected_markets))

    candles_by_market: dict[str, list[Candle]] = {}
    errors: list[dict[str, str]] = []
    for index, market in enumerate(selected_markets, start=1):
        try:
            candles = fetch_range_candles(client, market, UNIT, START_KST, end_kst)
        except Exception as exc:  # noqa: BLE001
            errors.append({"market": market, "message": str(exc)})
            print(f"[{index}/{len(selected_markets)}] {market} fetch error: {exc}")
            continue
        if len(candles) < settings.long_window + 60:
            errors.append({"market": market, "message": f"not enough candles: {len(candles)}"})
            print(f"[{index}/{len(selected_markets)}] {market} skipped candles={len(candles)}")
            continue
        candles_by_market[market] = candles
        print(f"[{index}/{len(selected_markets)}] {market} candles={len(candles)}")

    picks: dict[str, StrategyPick] = {}
    pick_details: dict[str, list[StrategyPick]] = {}
    for index, (market, candles) in enumerate(candles_by_market.items(), start=1):
        pick, all_picks = pick_strategy_for_market(market, candles, settings, prior)
        picks[market] = pick
        pick_details[market] = all_picks
        print(
            f"[pick {index}/{len(candles_by_market)}] {market} {pick.strategy} "
            f"score={decimal_to_str(pick.score)} return={decimal_to_str(pick.total_return_pct)}%"
        )

    pattern_model = build_pattern_model_for_picks(candles_by_market, picks, settings) if picks else {}
    if pattern_model:
        save_pattern_model(settings, pattern_model)
    portfolio = run_portfolio_simulation(candles_by_market, picks, settings, pattern_model) if picks else {}
    result = {
        "generatedAt": datetime.now(KST).isoformat(),
        "range": {
            "startKst": START_KST.isoformat(),
            "endKst": end_kst.isoformat(),
            "candleUnitMinutes": UNIT,
        },
        "universe": {
            "requestedMaxMarkets": MAX_MARKETS,
            "marketCount": len(candles_by_market),
            "markets": list(candles_by_market.keys()),
            "selectionMethod": "prior learning ranking, configured watchlist, then current KRW liquidity",
        },
        "assumptions": {
            "startingCashKrw": STARTING_CASH,
            "feeRate": settings.fee_rate,
            "historicalOrderbookIncluded": False,
            "slippageIncluded": False,
            "marketRegimeIncluded": True,
            "strategyScanStrideCandles": SCAN_STRIDE,
            "historyLimitCandles": HISTORY_LIMIT,
            "maxDailyOrders": settings.max_daily_orders,
            "maxOpenPositions": settings.max_open_positions,
            "maxPositionPct": settings.allocation_max_position_pct,
            "maxDeployPct": settings.allocation_max_deploy_pct,
            "maxOrderPct": settings.realtime_max_order_pct,
        },
        "strategyPicks": [pick.to_dict() for pick in sorted(picks.values(), key=lambda item: item.score, reverse=True)],
        "strategyScanTop3": {
            market: [pick.to_dict() for pick in rows[:3]]
            for market, rows in pick_details.items()
        },
        "patternLearning": {
            "observationCount": pattern_model.get("observationCount", 0) if pattern_model else 0,
            "profitCount": pattern_model.get("profitCount", 0) if pattern_model else 0,
            "lossCount": pattern_model.get("lossCount", 0) if pattern_model else 0,
            "averageProfitPct": pattern_model.get("averageProfitPct", "0") if pattern_model else "0",
            "averageLossPct": pattern_model.get("averageLossPct", "0") if pattern_model else "0",
        },
        "portfolio": portfolio,
        "errors": errors,
    }

    output_path = ROOT / "state" / f"range_simulation_{START_KST:%Y%m%d}_to_{end_kst:%Y%m%d_%H%M}.json"
    output_path.write_text(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={output_path}")
    if portfolio:
        print(
            "summary "
            f"final={decimal_to_str(portfolio['finalEquityKrw'])} "
            f"return={decimal_to_str(portfolio['totalReturnPct'])}% "
            f"fees={decimal_to_str(portfolio['feesPaidKrw'])} "
            f"orders={portfolio['orderCount']} "
            f"mdd={decimal_to_str(portfolio['maxDrawdownPct'])}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
