from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Protocol
import statistics
import time

from .config import TradingSettings
from .learning import load_learning_model
from .maeuknam_strategy import MaeuknamTechniqueSignal, evaluate_maeuknam_techniques
from .market_regime import MarketRegimeSignal, evaluate_market_regime
from .market_risk import evaluate_market_risk
from .models import Candle, OrderIntent, OrderResult, decimal_to_str
from .orderbook import adjust_order_for_orderbook
from .pattern_learning import (
    feature_snapshot,
    load_pattern_model,
    record_pattern_entry,
    record_pattern_exit,
    score_current_pattern,
)
from .broker import PortfolioPaperBroker
from .risk import remaining_cooldown_seconds
from .state import PortfolioState, reset_daily_counters_if_needed
from .trade_levels import ChartTradeLevels, chart_trade_levels


class RealtimeDecisionClient(Protocol):
    def get_ticker(self, markets: str | list[str]) -> list[dict[str, Any]]:
        ...

    def get_minute_candles(
        self,
        market: str,
        unit: int = 1,
        count: int = 60,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def get_orderbook(
        self,
        markets: str | list[str],
        count: int | None = None,
        level: str | int | None = None,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class RealtimeSituation:
    market: str
    label: str
    strategy: str
    action: str
    score: Decimal
    confidence: Decimal
    urgency: Decimal
    current_price: Decimal
    current_value_krw: Decimal
    learned_score: Decimal
    seconds_trend_pct: Decimal
    trend_1m_pct: Decimal
    trend_5m_pct: Decimal
    trend_30m_pct: Decimal
    day_change_pct: Decimal
    volatility_pct: Decimal
    drawdown_pct: Decimal
    volume_ratio: Decimal
    trade_pressure: Decimal
    tags: tuple[str, ...]
    reason: str
    pattern_profit_score: Decimal = Decimal("0")
    pattern_loss_score: Decimal = Decimal("0")
    pattern_adjustment: Decimal = Decimal("0")
    risk_adjustment: Decimal = Decimal("0")
    risk_reason: str = "risk-clear"
    market_regime: str = "neutral"
    pattern_features: dict[str, str] = field(default_factory=dict)
    chart_levels: ChartTradeLevels | None = None
    maeuknam_signal: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "label": self.label,
            "strategy": self.strategy,
            "action": self.action,
            "score": decimal_to_str(self.score),
            "confidence": decimal_to_str(self.confidence),
            "urgency": decimal_to_str(self.urgency),
            "currentPrice": decimal_to_str(self.current_price),
            "currentValueKrw": decimal_to_str(self.current_value_krw),
            "learnedScore": decimal_to_str(self.learned_score),
            "secondsTrendPct": decimal_to_str(self.seconds_trend_pct),
            "trend1mPct": decimal_to_str(self.trend_1m_pct),
            "trend5mPct": decimal_to_str(self.trend_5m_pct),
            "trend30mPct": decimal_to_str(self.trend_30m_pct),
            "dayChangePct": decimal_to_str(self.day_change_pct),
            "volatilityPct": decimal_to_str(self.volatility_pct),
            "drawdownPct": decimal_to_str(self.drawdown_pct),
            "volumeRatio": decimal_to_str(self.volume_ratio),
            "tradePressure": decimal_to_str(self.trade_pressure),
            "tags": list(self.tags),
            "reason": self.reason,
            "patternProfitScore": decimal_to_str(self.pattern_profit_score),
            "patternLossScore": decimal_to_str(self.pattern_loss_score),
            "patternAdjustment": decimal_to_str(self.pattern_adjustment),
            "riskAdjustment": decimal_to_str(self.risk_adjustment),
            "riskReason": self.risk_reason,
            "marketRegime": self.market_regime,
            "patternFeatures": self.pattern_features,
            "chartLevels": self.chart_levels.to_dict() if self.chart_levels is not None else None,
            "maeuknamSignal": self.maeuknam_signal,
            "entryPrice": decimal_to_str(self.chart_levels.entry_price) if self.chart_levels is not None else "0",
            "targetSellPrice": decimal_to_str(self.chart_levels.take_profit_price) if self.chart_levels is not None else "0",
            "stopLossPrice": decimal_to_str(self.chart_levels.stop_loss_price) if self.chart_levels is not None else "0",
            "trailingStopPrice": decimal_to_str(self.chart_levels.trailing_stop_price) if self.chart_levels is not None else "0",
            "riskReward": decimal_to_str(self.chart_levels.risk_reward) if self.chart_levels is not None else "0",
        }


@dataclass(frozen=True)
class RealtimeOrderPlan:
    market: str
    side: str
    amount_krw: Decimal
    volume: Decimal | None
    current_price: Decimal
    reason: str
    intent: OrderIntent
    orderbook: dict[str, Any] | None = None
    strategy: str = ""
    pattern_features: dict[str, str] = field(default_factory=dict)
    chart_levels: ChartTradeLevels | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "side": "매수" if self.side == "bid" else "매도",
            "amountKrw": decimal_to_str(self.amount_krw),
            "volume": decimal_to_str(self.volume) if self.volume is not None else None,
            "currentPrice": decimal_to_str(self.current_price),
            "reason": self.reason,
            "intent": self.intent.to_upbit_body(),
            "orderbook": self.orderbook,
            "strategy": self.strategy,
            "patternFeatures": self.pattern_features,
            "chartLevels": self.chart_levels.to_dict() if self.chart_levels is not None else None,
            "entryPrice": decimal_to_str(self.chart_levels.entry_price) if self.chart_levels is not None else decimal_to_str(self.current_price),
            "targetSellPrice": decimal_to_str(self.chart_levels.take_profit_price) if self.chart_levels is not None else "0",
            "stopLossPrice": decimal_to_str(self.chart_levels.stop_loss_price) if self.chart_levels is not None else "0",
            "trailingStopPrice": decimal_to_str(self.chart_levels.trailing_stop_price) if self.chart_levels is not None else "0",
            "riskReward": decimal_to_str(self.chart_levels.risk_reward) if self.chart_levels is not None else "0",
        }


@dataclass(frozen=True)
class GoalPacePressure:
    enabled: bool
    level: str
    label: str
    equity_krw: Decimal
    today_required_krw: Decimal
    gap_krw: Decimal
    pace_pct: Decimal
    intensity: Decimal
    entry_score_adjustment: Decimal
    deploy_multiplier: Decimal
    max_order_multiplier: Decimal
    position_multiplier: Decimal
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "level": self.level,
            "label": self.label,
            "equityKrw": decimal_to_str(self.equity_krw),
            "todayRequiredKrw": decimal_to_str(self.today_required_krw),
            "gapKrw": decimal_to_str(self.gap_krw),
            "pacePct": decimal_to_str(self.pace_pct),
            "intensity": decimal_to_str(self.intensity),
            "entryScoreAdjustment": decimal_to_str(self.entry_score_adjustment),
            "deployMultiplier": decimal_to_str(self.deploy_multiplier),
            "maxOrderMultiplier": decimal_to_str(self.max_order_multiplier),
            "positionMultiplier": decimal_to_str(self.position_multiplier),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RealtimeDecisionPlan:
    universe_count: int
    evaluated_count: int
    mode: str
    situations: tuple[RealtimeSituation, ...]
    selected: tuple[RealtimeSituation, ...]
    orders: tuple[RealtimeOrderPlan, ...]
    errors: tuple[dict[str, str], ...]
    history: dict[str, list[dict[str, str]]]
    candle_cache: dict[str, Any]
    market_regime: dict[str, Any]
    goal_pressure: GoalPacePressure
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "universeCount": self.universe_count,
            "evaluatedCount": self.evaluated_count,
            "mode": self.mode,
            "situations": [situation.to_dict() for situation in self.situations],
            "selected": [situation.to_dict() for situation in self.selected],
            "orders": [order.to_dict() for order in self.orders],
            "errors": list(self.errors),
            "marketRegime": self.market_regime,
            "goalPressure": self.goal_pressure.to_dict(),
            "message": self.message,
        }


def realtime_market_universe(
    settings: TradingSettings,
    state: PortfolioState | None = None,
    model: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    if settings.strategy_name == "maeuknam_cards":
        held = []
        if state is not None:
            held = [market for market, position in state.positions.items() if position.volume > 0]
        return tuple(dict.fromkeys([*settings.markets, *held]))
    model = model if model is not None else load_learning_model(settings)
    learned_markets = model.get("markets") if isinstance(model.get("markets"), dict) else {}
    ranked = sorted(
        (
            (str(market), Decimal(str(row.get("score") or "0")))
            for market, row in learned_markets.items()
            if isinstance(row, dict)
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    held = []
    if state is not None:
        held = [market for market, position in state.positions.items() if position.volume > 0]
    learned = [market for market, _score in ranked]
    return tuple(dict.fromkeys([*settings.markets, *held, *learned]))


def build_realtime_decision_plan(
    settings: TradingSettings,
    client: RealtimeDecisionClient,
    state: PortfolioState,
    realtime: dict[str, Any] | None = None,
    previous_runtime: dict[str, Any] | None = None,
    candidate_markets: tuple[str, ...] | None = None,
) -> RealtimeDecisionPlan:
    reset_daily_counters_if_needed(state)
    model = load_learning_model(settings)
    pattern_model = load_pattern_model(settings)
    learned_markets = model.get("markets") if isinstance(model.get("markets"), dict) else {}
    universe = (
        tuple(dict.fromkeys(candidate_markets))
        if candidate_markets is not None
        else realtime_market_universe(settings, state, model)
    )
    realtime = realtime or {}
    previous_runtime = previous_runtime or {}
    errors: list[dict[str, str]] = []

    tickers = fetch_realtime_tickers(client, universe, errors)
    tickers = merge_realtime_ticker_snapshot(tickers, realtime)
    history = update_price_history(previous_runtime.get("history", {}), tickers)
    maeuknam_only = settings.strategy_name == "maeuknam_cards"
    if maeuknam_only:
        candle_markets = tuple(dict.fromkeys([*held_markets(state), *universe]))
    else:
        coarse = rank_coarse_candidates(settings, state, universe, learned_markets, tickers, history)
        momentum_leaders = rank_momentum_leaders(settings, state, universe, tickers, history)
        leader_limit = min(max(10, settings.realtime_candle_top_n // 2), 30)
        candle_budget = min(len(universe), settings.realtime_candle_top_n + leader_limit + len(held_markets(state)))
        candle_markets = tuple(
            dict.fromkeys(
                [
                    *held_markets(state),
                    *momentum_leaders[:leader_limit],
                    *coarse[: settings.realtime_candle_top_n],
                ]
            )
        )[:candle_budget]
    candle_map, candle_cache = fetch_candle_map(settings, client, candle_markets, errors, previous_runtime)
    market_regime = evaluate_market_regime(settings, candle_map)
    current_prices = {
        market: price
        for market, ticker in tickers.items()
        if (price := ticker_price(ticker)) > 0
    }
    goal_pressure = realtime_goal_pace_pressure(settings, state.equity(current_prices))

    situations: list[RealtimeSituation] = []
    for market in universe:
        ticker = tickers.get(market, {})
        price = ticker_price(ticker)
        if price <= 0:
            continue
        recommendation = learned_markets.get(market) if isinstance(learned_markets.get(market), dict) else {}
        situation = evaluate_realtime_situation(
            settings=settings,
            state=state,
            market=market,
            ticker=ticker,
            recommendation=recommendation,
            history=history.get(market, []),
            candles=candle_map.get(market, []),
            pattern_model=pattern_model,
            market_regime=market_regime,
            goal_pressure=goal_pressure,
        )
        situations.append(situation)

    ranked_situations = sorted(situations, key=lambda item: item.score, reverse=True)
    entry_floor = realtime_entry_score_floor(settings, market_regime, goal_pressure)
    selected = tuple(
        situation
        for situation in ranked_situations
        if situation.action == "buy" and situation.score >= entry_floor
    )[: settings.realtime_candidate_top_n]
    if not selected:
        selected = paper_extreme_volatility_probe_selected(settings, state, ranked_situations, entry_floor)
        if selected:
            forced = {situation.market: situation for situation in selected}
            ranked_situations = [forced.get(situation.market, situation) for situation in ranked_situations]
    orders = build_realtime_orders(settings, state, ranked_situations, selected, market_regime, goal_pressure)
    orders = apply_orderbook_to_realtime_orders(settings, client, orders, errors)
    mode = classify_realtime_mode(ranked_situations, selected, orders)
    message = realtime_message(mode, ranked_situations, selected, orders)

    return RealtimeDecisionPlan(
        universe_count=len(universe),
        evaluated_count=len(situations),
        mode=mode,
        situations=tuple(ranked_situations),
        selected=selected,
        orders=tuple(orders),
        errors=tuple(errors),
        history=history,
        candle_cache=candle_cache,
        market_regime=market_regime.to_dict(),
        goal_pressure=goal_pressure,
        message=message,
    )


def fetch_realtime_tickers(
    client: RealtimeDecisionClient,
    universe: tuple[str, ...],
    errors: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    tickers: dict[str, dict[str, Any]] = {}
    for chunk in chunks(list(universe), 90):
        for attempt in range(3):
            try:
                for row in client.get_ticker(chunk):
                    market = str(row.get("market") or "")
                    if market:
                        tickers[market] = row
                break
            except Exception as exc:
                if is_rate_limit_error(exc) and attempt < 2:
                    time.sleep(rate_limit_backoff_seconds(attempt))
                    continue
                errors.append({"market": ",".join(chunk[:3]), "message": f"현재가 묶음 조회 실패: {exc}"})
                break
        time.sleep(0.05)
    return tickers


def is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "too_many_requests" in message or "too many requests" in message


def rate_limit_backoff_seconds(attempt: int) -> float:
    return 0.8 + attempt * 0.7


def merge_realtime_ticker_snapshot(
    tickers: dict[str, dict[str, Any]],
    realtime: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    merged = {market: dict(ticker) for market, ticker in tickers.items()}
    realtime_tickers = realtime.get("tickers", {})
    if not isinstance(realtime_tickers, dict):
        realtime_tickers = {}
    for market, ticker in realtime_tickers.items():
        if not isinstance(ticker, dict) or not ticker:
            continue
        row = dict(merged.get(str(market), {"market": str(market)}))
        if ticker.get("tradePrice") is not None:
            row["trade_price"] = ticker["tradePrice"]
        if ticker.get("signedChangeRate") is not None:
            row["signed_change_rate"] = ticker["signedChangeRate"]
        elif ticker.get("changeRate") is not None:
            row["signed_change_rate"] = ticker["changeRate"]
        if ticker.get("tradeValue24h") is not None:
            row["acc_trade_price_24h"] = ticker["tradeValue24h"]
        row["source"] = "websocket"
        merged[str(market)] = row
    realtime_trades = realtime.get("trades", {})
    if isinstance(realtime_trades, dict):
        for market, trades in realtime_trades.items():
            if not isinstance(trades, list):
                continue
            row = dict(merged.get(str(market), {"market": str(market)}))
            row["trade_pressure"] = trade_pressure_from_trades(trades)
            merged[str(market)] = row
    return merged


def update_price_history(
    previous_history: Any,
    tickers: dict[str, dict[str, Any]],
    max_rows: int = 120,
) -> dict[str, list[dict[str, str]]]:
    history: dict[str, list[dict[str, str]]] = {}
    now = datetime.now(timezone.utc).isoformat()
    source = previous_history if isinstance(previous_history, dict) else {}
    for market, ticker in tickers.items():
        price = ticker_price(ticker)
        if price <= 0:
            continue
        rows = [
            {"time": str(row.get("time")), "price": str(row.get("price"))}
            for row in source.get(market, [])
            if isinstance(row, dict) and row.get("time") and row.get("price") is not None
        ][-max_rows + 1 :]
        rows.append({"time": now, "price": decimal_to_str(price)})
        history[market] = rows
    return history


def rank_coarse_candidates(
    settings: TradingSettings,
    state: PortfolioState,
    universe: tuple[str, ...],
    learned_markets: dict[str, Any],
    tickers: dict[str, dict[str, Any]],
    history: dict[str, list[dict[str, str]]] | None = None,
) -> list[str]:
    ranked: list[tuple[str, Decimal]] = []
    history = history or {}
    for market in universe:
        ticker = tickers.get(market, {})
        if ticker_price(ticker) <= 0:
            continue
        recommendation = learned_markets.get(market) if isinstance(learned_markets.get(market), dict) else {}
        learned_score = Decimal(str(recommendation.get("score") or "0")) if isinstance(recommendation, dict) else Decimal("0")
        learned_component = realtime_learned_score_component(learned_score)
        day_change = ticker_day_change_pct(ticker)
        trade_value = ticker_trade_value(ticker)
        live_trend = history_trend_pct(history.get(market, []), settings.realtime_decision_interval_seconds * 6)
        position_bonus = Decimal("0.3") if state.position(market).volume > 0 else Decimal("0")
        leader_rank_score = realtime_momentum_leader_rank_score(day_change, trade_value, live_trend)
        coarse_score = learned_component + clamp(day_change / Decimal("20"), Decimal("-0.25"), Decimal("0.35")) + position_bonus
        coarse_score += clamp(live_trend / Decimal("3"), Decimal("-0.20"), Decimal("0.35"))
        coarse_score += clamp(leader_rank_score / Decimal("6"), Decimal("-0.10"), Decimal("0.55"))
        if trade_value > 0:
            coarse_score += min(Decimal("0.15"), trade_value.log10() / Decimal("100"))
        ranked.append((market, coarse_score))
    return [market for market, _score in sorted(ranked, key=lambda item: item[1], reverse=True)]


def rank_momentum_leaders(
    settings: TradingSettings,
    state: PortfolioState,
    universe: tuple[str, ...],
    tickers: dict[str, dict[str, Any]],
    history: dict[str, list[dict[str, str]]] | None = None,
) -> list[str]:
    ranked: list[tuple[str, Decimal]] = []
    history = history or {}
    for market in universe:
        ticker = tickers.get(market, {})
        if ticker_price(ticker) <= 0:
            continue
        day_change = ticker_day_change_pct(ticker)
        live_trend = history_trend_pct(history.get(market, []), settings.realtime_decision_interval_seconds * 6)
        if day_change <= 0 and live_trend <= 0:
            continue
        trade_value = ticker_trade_value(ticker)
        score = realtime_momentum_leader_rank_score(day_change, trade_value, live_trend)
        if state.position(market).volume > 0:
            score += Decimal("0.20")
        if score > 0:
            ranked.append((market, score))
    return [market for market, _score in sorted(ranked, key=lambda item: item[1], reverse=True)]


def realtime_momentum_leader_rank_score(
    day_change: Decimal,
    trade_value_24h: Decimal,
    live_trend: Decimal = Decimal("0"),
) -> Decimal:
    score = clamp(day_change / Decimal("3"), Decimal("-0.40"), Decimal("2.40"))
    score += clamp(live_trend / Decimal("1.5"), Decimal("-0.35"), Decimal("1.20"))
    if trade_value_24h >= Decimal("10000000000"):
        score += Decimal("0.65")
    elif trade_value_24h >= Decimal("3000000000"):
        score += Decimal("0.42")
    elif trade_value_24h >= Decimal("1000000000"):
        score += Decimal("0.24")
    elif trade_value_24h < Decimal("300000000"):
        score -= Decimal("0.35")
    return score


def realtime_learned_score_component(learned_score: Decimal) -> Decimal:
    return clamp(learned_score, Decimal("-1.5"), Decimal("1.8"))


def fetch_candle_map(
    settings: TradingSettings,
    client: RealtimeDecisionClient,
    markets: tuple[str, ...],
    errors: list[dict[str, str]],
    previous_runtime: dict[str, Any],
) -> tuple[dict[str, list[Candle]], dict[str, Any]]:
    candles_by_market: dict[str, list[Candle]] = {}
    cache: dict[str, Any] = {}
    previous_cache = previous_runtime.get("candleCache", {})
    if not isinstance(previous_cache, dict):
        previous_cache = {}
    for index, market in enumerate(markets):
        cached_entry = fresh_cached_candle_entry(settings, previous_cache.get(market))
        if cached_entry is not None:
            rows = cached_entry["rows"]
            candles_by_market[market] = [Candle.from_upbit(row) for row in rows]
            cache[market] = cached_entry
            continue
        try:
            raw = fetch_realtime_candles(client, market, count=60)
            candles_by_market[market] = [Candle.from_upbit(row) for row in raw]
            cache[market] = {"fetchedAt": datetime.now(timezone.utc).isoformat(), "rows": raw}
        except Exception as exc:
            errors.append({"market": market, "message": f"1분봉 조회 실패: {exc}"})
        if index < len(markets) - 1:
            time.sleep(0.08)
    return candles_by_market, cache


def fresh_cached_candle_entry(settings: TradingSettings, entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    fetched_at = entry.get("fetchedAt")
    rows = entry.get("rows")
    if not isinstance(fetched_at, str) or not isinstance(rows, list) or not rows:
        return None
    parsed = parse_iso(fetched_at)
    if parsed is None:
        return None
    age = (datetime.now(timezone.utc) - parsed).total_seconds()
    if age > settings.realtime_candle_refresh_seconds:
        return None
    return {"fetchedAt": fetched_at, "rows": rows}


def fetch_realtime_candles(
    client: RealtimeDecisionClient,
    market: str,
    count: int = 60,
    retry_count: int = 2,
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return client.get_minute_candles(market=market, unit=1, count=count)
        except Exception as exc:
            last_error = exc
            if not is_rate_limit_error(exc):
                raise
            if attempt < retry_count:
                time.sleep(rate_limit_backoff_seconds(attempt))
    if last_error is not None:
        raise last_error
    return []


def evaluate_realtime_situation(
    settings: TradingSettings,
    state: PortfolioState,
    market: str,
    ticker: dict[str, Any],
    recommendation: dict[str, Any],
    history: list[dict[str, str]],
    candles: list[Candle],
    pattern_model: dict[str, Any] | None = None,
    market_regime: MarketRegimeSignal | None = None,
    goal_pressure: GoalPacePressure | None = None,
) -> RealtimeSituation:
    price = ticker_price(ticker)
    maeuknam_only = settings.strategy_name == "maeuknam_cards"
    learned_score = Decimal(str(recommendation.get("score") or "0")) if recommendation else Decimal("0")
    learned_component = Decimal("0") if maeuknam_only else realtime_learned_score_component(learned_score)
    label = str(recommendation.get("label") or market)
    strategy = "maeuknam_cards" if maeuknam_only else str(recommendation.get("bestStrategy") or "unknown")
    seconds_trend = history_trend_pct(history, settings.realtime_decision_interval_seconds * 6)
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    trend_1m = candle_trend_pct(ordered, 1)
    trend_5m = candle_trend_pct(ordered, 5)
    trend_30m = candle_trend_pct(ordered, 30)
    volatility = candle_volatility_pct(ordered, 12)
    drawdown = candle_drawdown_pct(ordered, 30)
    volume_ratio = candle_volume_ratio(ordered, 20)
    range_position = candle_range_position_pct(ordered, 30)
    day_change = ticker_day_change_pct(ticker)
    trade_value_24h = ticker_trade_value(ticker)
    trade_pressure = realtime_trade_pressure(market, ticker)
    position = state.position(market)
    current_value = position.value(price)
    pattern_score = score_current_pattern(pattern_model, market, strategy, ordered)
    pattern_features = feature_snapshot(ordered).to_dict() if ordered else {}
    held = current_value >= settings.min_order_krw
    daily_buy_lock = state.daily_realized_pnl_krw <= -settings.daily_loss_limit_krw
    market_regime = market_regime or MarketRegimeSignal()
    risk_signal = evaluate_market_risk(
        settings=settings,
        pattern_model=pattern_model,
        market=market,
        held=held,
        trend_1m_pct=trend_1m,
        trend_5m_pct=trend_5m,
        trend_30m_pct=trend_30m,
        volatility_pct=volatility,
        drawdown_pct=drawdown,
        volume_ratio=volume_ratio,
        day_change_pct=day_change,
        range_position_pct=range_position,
        trade_value_24h_krw=trade_value_24h,
        latest_candle_trade_value_krw=ordered[-1].candle_acc_trade_price if ordered else None,
        trade_pressure=trade_pressure,
        strategy=strategy,
    )

    tags: list[str] = []
    if seconds_trend >= Decimal("0.5") or trend_1m >= Decimal("0.8"):
        tags.append("급등")
    if seconds_trend <= Decimal("-0.8") or trend_1m <= Decimal("-1.2") or trend_5m <= Decimal("-2.5"):
        tags.append("급락")
    if trend_5m >= Decimal("1") and trend_30m >= Decimal("0"):
        tags.append("상승 추세")
    if trend_5m <= Decimal("-1") and trend_30m <= Decimal("0"):
        tags.append("하락 추세")
    if volume_ratio >= Decimal("1.5"):
        tags.append("거래대금 증가")
    if volatility >= settings.strategy_max_volatility_pct:
        tags.append("변동성 과열")
    has_candle_context = len(ordered) >= 12
    low_volatility_stalled = (
        has_candle_context
        and volatility <= settings.realtime_low_volatility_pct
        and abs(trend_5m) <= settings.realtime_stagnation_trend_pct
        and abs(trend_30m) <= settings.realtime_stagnation_trend_pct
        and volume_ratio <= settings.realtime_stagnation_volume_ratio
    )
    if low_volatility_stalled:
        tags.append("저변동 정체")
    if trend_30m > 0 and Decimal("-0.7") <= trend_1m < 0:
        tags.append("상승 중 눌림")
    if day_change >= Decimal("15") and trend_1m < 0:
        tags.append("일봉 과열 둔화")
    if daily_buy_lock and not held:
        tags.append("일일 손실 한도")
    leader_bonus = realtime_momentum_leader_bonus(
        settings=settings,
        day_change=day_change,
        trend_1m=trend_1m,
        trend_5m=trend_5m,
        trend_30m=trend_30m,
        volume_ratio=volume_ratio,
        trade_value_24h=trade_value_24h,
        trade_pressure=trade_pressure,
        drawdown=drawdown,
        range_position=range_position,
    )
    if leader_bonus > 0:
        tags.append("상승 리더")
    if pattern_score.loss_similarity >= Decimal("0.60"):
        tags.append("loss-pattern")
    if pattern_score.profit_similarity >= Decimal("0.55"):
        tags.append("profit-pattern")
    tags.extend(risk_signal.tags)
    tags.extend(market_regime.tags)

    levels = chart_trade_levels(
        settings=settings,
        candles=ordered,
        current_price=price,
        avg_entry_price=position.avg_entry_price,
        held=held,
    )
    maeuknam_signal = evaluate_maeuknam_techniques(ordered, allowed_directions=("LONG",)) if maeuknam_only else None
    target_sell_price = levels.take_profit_price
    stop_loss_price = levels.stop_loss_price
    trailing_stop_price = levels.trailing_stop_price
    hard_stop_price = Decimal("0")
    hard_target_price = Decimal("0")
    return_pct = Decimal("0")
    holding_seconds = holding_age_seconds(state, market) if held else None
    if held and position.avg_entry_price > 0:
        return_pct = (price - position.avg_entry_price) / position.avg_entry_price * Decimal("100")
        hard_stop_price = position.avg_entry_price * (Decimal("1") - settings.stop_loss_pct / Decimal("100"))
        hard_target_price = position.avg_entry_price * (Decimal("1") + settings.take_profit_pct / Decimal("100"))
        if price <= stop_loss_price:
            tags.append("손절선 도달")
        elif price >= target_sell_price:
            tags.append("목표가 도달")
    if held and hard_stop_price > 0 and price <= hard_stop_price and "손절선 도달" not in tags:
        tags.append("손절선 도달")
    if held and hard_target_price > 0 and price >= hard_target_price and "목표가 도달" not in tags:
        tags.append("목표가 도달")
        tags.append("\ubaa9\ud45c\uac00 \ub3c4\ub2ec")
    if levels.risk_reward >= Decimal("1.45"):
        tags.append("chart-rr-ok")
    elif not held and levels.risk_reward < Decimal("1.05"):
        tags.append("chart-rr-low")

    stagnant_exit = (
        held
        and low_volatility_stalled
        and holding_seconds is not None
        and holding_seconds >= settings.realtime_stagnation_exit_seconds
        and return_pct < settings.take_profit_pct
    )
    if stagnant_exit:
        tags.append("저변동 장기 보유 정리")
    idle_exit = (
        held
        and holding_seconds is not None
        and holding_seconds >= settings.realtime_idle_exit_seconds
        and return_pct <= settings.realtime_idle_exit_return_pct
        and abs(trend_5m) <= settings.realtime_idle_exit_trend_pct
        and trend_30m <= settings.realtime_idle_exit_trend_pct
        and (market_regime.block_new_entries or risk_signal.block_entry)
        and target_sell_price > 0
        and price < target_sell_price
    )
    if idle_exit:
        tags.append("기회비용 시간정리")

    score = learned_component
    if not maeuknam_only:
        score += clamp(seconds_trend / Decimal("2.5"), Decimal("-0.18"), Decimal("0.22"))
        score += clamp(trend_1m / Decimal("3"), Decimal("-0.25"), Decimal("0.30"))
        score += clamp(trend_5m / Decimal("7"), Decimal("-0.25"), Decimal("0.35"))
        score += clamp(trend_30m / Decimal("20"), Decimal("-0.15"), Decimal("0.20"))
        score += volume_score(volume_ratio)
        score += clamp(trade_pressure / Decimal("8"), Decimal("-0.08"), Decimal("0.08"))
        score += leader_bonus
        if "변동성 과열" in tags and "거래대금 증가" not in tags:
            score -= Decimal("0.12")
        if "급락" in tags:
            score -= Decimal("0.45")
        if "일봉 과열 둔화" in tags:
            score -= Decimal("0.15")
        if low_volatility_stalled:
            score -= Decimal("0.18")
        score += pattern_score.adjustment
    score += risk_signal.score_adjustment
    score += market_regime.score_adjustment
    if daily_buy_lock and not held:
        score -= Decimal("0.80")
    entry_floor = realtime_entry_score_floor(settings, market_regime, goal_pressure)
    entry_allowed = realtime_entry_allowed(
        settings=settings,
        market_regime=market_regime,
        score=score,
        entry_floor=entry_floor,
        tags=tuple(tags),
        risk_blocked=risk_signal.block_entry,
        pattern_blocked=pattern_score.blocked,
        volume_ratio=volume_ratio,
        trade_pressure=trade_pressure,
        trend_1m=trend_1m,
        trend_5m=trend_5m,
    )
    if maeuknam_only:
        score, entry_allowed = maeuknam_realtime_entry_gate(
            settings=settings,
            signal=maeuknam_signal,
            held=held,
            entry_floor=entry_floor,
            daily_buy_lock=daily_buy_lock,
            risk_blocked=risk_signal.block_entry,
            market_regime=market_regime,
            tags=tags,
        )
    if daily_buy_lock and not held:
        entry_allowed = False
    recovery_scout_entry = False if daily_buy_lock or maeuknam_only else realtime_goal_recovery_scout_allowed(
        settings=settings,
        goal_pressure=goal_pressure,
        market_regime=market_regime,
        held=held,
        score=score,
        entry_floor=entry_floor,
        tags=tuple(tags),
        risk_blocked=risk_signal.block_entry,
        pattern_blocked=pattern_score.blocked,
        pattern_loss_score=pattern_score.loss_similarity,
        pattern_profit_score=pattern_score.profit_similarity,
        volume_ratio=volume_ratio,
        trade_pressure=trade_pressure,
        trend_1m=trend_1m,
        trend_5m=trend_5m,
        trend_30m=trend_30m,
        low_volatility_stalled=low_volatility_stalled,
    )
    if recovery_scout_entry:
        entry_allowed = True
        tags.append("목표복구 스카우트")
    if entry_allowed and market_regime.block_new_entries:
        tags.append("약세장 예외 돌파")
    strong_score_entry = (
        not held
        and score >= entry_floor + Decimal("0.35")
        and not risk_signal.block_entry
        and entry_allowed
        and not pattern_score.blocked
        and trend_1m >= Decimal("-0.5")
        and trend_5m >= Decimal("-1.0")
        and "급락" not in tags
        and "일봉 과열 둔화" not in tags
        and not low_volatility_stalled
    )
    if strong_score_entry:
        tags.append("강한 점수 후보")

    if held and ((stop_loss_price > 0 and price <= stop_loss_price) or (hard_stop_price > 0 and price <= hard_stop_price)):
        action = "sell"
        urgency = Decimal("1")
    elif risk_signal.exit_now and held:
        action = "sell"
        urgency = Decimal("0.95")
    elif held and trailing_stop_price > 0 and price <= trailing_stop_price and return_pct > 0:
        action = "sell"
        urgency = Decimal("0.88")
    elif held and ((target_sell_price > 0 and price >= target_sell_price) or (hard_target_price > 0 and price >= hard_target_price)):
        action = "sell"
        urgency = Decimal("0.90")
    elif pattern_score.exit_now and held:
        action = "sell"
        urgency = Decimal("0.85")
    elif stagnant_exit:
        action = "sell"
        urgency = Decimal("0.68")
    elif idle_exit:
        action = "sell"
        urgency = Decimal("0.64")
    elif recovery_scout_entry:
        action = "buy"
        urgency = Decimal("0.42") + clamp((goal_pressure.intensity if goal_pressure else Decimal("0")) / Decimal("5"), Decimal("0"), Decimal("0.18"))
    elif maeuknam_only and entry_allowed and not held:
        action = "buy"
        urgency = Decimal("0.62")
    elif risk_signal.block_entry and not held and not entry_allowed:
        action = "avoid"
        urgency = Decimal("0.1")
    elif pattern_score.blocked and not held:
        action = "avoid"
        urgency = Decimal("0.1")
    elif "급락" in tags:
        action = "sell" if held else "avoid"
        urgency = Decimal("1")
    elif held and "하락 추세" in tags and score < Decimal("0.05"):
        action = "sell"
        urgency = Decimal("0.75")
    elif market_regime.block_new_entries and not entry_allowed:
        action = "hold" if held else "avoid"
        urgency = Decimal("0.20") if held else Decimal("0.1")
    elif (
        score >= entry_floor
        and entry_allowed
        and ("상승 추세" in tags or "급등" in tags or "상승 중 눌림" in tags or "상승 리더" in tags)
        and "일봉 과열 둔화" not in tags
        and not low_volatility_stalled
    ):
        action = "buy"
        urgency = Decimal("0.7") if "급등" in tags else Decimal("0.45")
    elif strong_score_entry:
        action = "buy"
        urgency = Decimal("0.35")
    elif low_volatility_stalled and not held:
        action = "avoid"
        urgency = Decimal("0.1")
    elif held:
        action = "hold"
        urgency = Decimal("0.25")
    else:
        action = "avoid" if score < Decimal("0") else "watch"
        urgency = Decimal("0.15")

    confidence = clamp(abs(score) + Decimal("0.25"), Decimal("0"), Decimal("1"))
    if maeuknam_only:
        reason = (
            f"{', '.join(tags) if tags else '중립'} · 매억남 카드 전용 · "
            f"{format_maeuknam_realtime_reason(maeuknam_signal)} · "
            f"일중 {day_change:.2f}% · 1분 {trend_1m:.2f}% · 5분 {trend_5m:.2f}% · "
            f"30분 {trend_30m:.2f}% · 거래대금 {volume_ratio:.2f}배"
        )
    else:
        reason = (
            f"{', '.join(tags) if tags else '중립'} · 학습 {learned_score:.3f}/적용 {learned_component:.3f} · "
            f"일중 {day_change:.2f}% · 초단기 {seconds_trend:.2f}% · 1분 {trend_1m:.2f}% · "
            f"5분 {trend_5m:.2f}% · 30분 {trend_30m:.2f}% · 거래대금 {volume_ratio:.2f}배 · "
            f"리더 {leader_bonus:.2f} · {pattern_score.reason}"
        )
    if held and position.avg_entry_price > 0:
        holding_text = f" · 보유시간 {format_duration_seconds(holding_seconds)}" if holding_seconds is not None else ""
        reason = (
            f"{reason} · 보유 매수가 {position.avg_entry_price:.8g} · 현재가 {price:.8g} · "
            f"목표가 {target_sell_price:.8g} · 손절가 {stop_loss_price:.8g} · 보유수익률 {return_pct:.2f}%{holding_text}"
        )
    if goal_pressure is not None and goal_pressure.enabled and goal_pressure.intensity > 0:
        reason = f"{reason} · 목표페이스 {goal_pressure.pace_pct:.1f}% {goal_pressure.label}"
    reason = f"{reason} 쨌 {levels.reason} risk={risk_signal.reason} market={market_regime.reason} entryFloor={entry_floor:.2f}"
    return RealtimeSituation(
        market=market,
        label=label,
        strategy=strategy,
        action=action,
        score=score,
        confidence=confidence,
        urgency=urgency,
        current_price=price,
        current_value_krw=current_value,
        learned_score=learned_score,
        seconds_trend_pct=seconds_trend,
        trend_1m_pct=trend_1m,
        trend_5m_pct=trend_5m,
        trend_30m_pct=trend_30m,
        day_change_pct=day_change,
        volatility_pct=volatility,
        drawdown_pct=drawdown,
        volume_ratio=volume_ratio,
        trade_pressure=trade_pressure,
        tags=tuple(tags),
        reason=reason,
        pattern_profit_score=pattern_score.profit_similarity,
        pattern_loss_score=pattern_score.loss_similarity,
        pattern_adjustment=pattern_score.adjustment,
        risk_adjustment=risk_signal.score_adjustment,
        risk_reason=risk_signal.reason,
        market_regime=market_regime.label,
        pattern_features=pattern_features,
        chart_levels=levels,
        maeuknam_signal=maeuknam_signal.to_dict() if maeuknam_signal is not None else None,
    )


def build_realtime_orders(
    settings: TradingSettings,
    state: PortfolioState,
    situations: list[RealtimeSituation],
    selected: tuple[RealtimeSituation, ...],
    market_regime: MarketRegimeSignal | None = None,
    goal_pressure: GoalPacePressure | None = None,
) -> list[RealtimeOrderPlan]:
    reset_daily_counters_if_needed(state)
    remaining_order_slots = settings.max_daily_orders - state.daily_order_count
    if remaining_order_slots <= 0:
        return []
    prices = {situation.market: situation.current_price for situation in situations}
    equity = state.equity(prices)
    active_regime = market_regime or MarketRegimeSignal()
    regime_multiplier = active_regime.deploy_multiplier
    pressure = goal_pressure or realtime_goal_pace_pressure(settings, equity)
    if paper_extreme_mode_enabled(settings):
        deploy_pct = Decimal("1")
    else:
        deploy_pct = min(settings.allocation_max_deploy_pct, settings.allocation_max_deploy_pct * regime_multiplier * pressure.deploy_multiplier)
    deploy_limit = equity * deploy_pct
    max_order_krw = min(settings.max_order_krw, equity * settings.realtime_max_order_pct * pressure.max_order_multiplier)
    entry_floor = realtime_entry_score_floor(settings, active_regime, pressure)
    orders: list[RealtimeOrderPlan] = []
    planned_sell_markets: set[str] = set()
    planned_cash = state.cash_krw

    for situation in sorted(situations, key=lambda item: item.urgency, reverse=True):
        if situation.action != "sell" or situation.current_value_krw < settings.min_order_krw:
            continue
        if situation.market in planned_sell_markets:
            continue
        position = state.position(situation.market)
        intent = OrderIntent(
            market=situation.market,
            side="ask",
            ord_type="market",
            volume=position.volume,
            reason=f"실시간 상황 청산: {situation.reason}",
        )
        orders.append(
            RealtimeOrderPlan(
                market=situation.market,
                side="ask",
                amount_krw=situation.current_value_krw,
                volume=position.volume,
                current_price=situation.current_price,
                reason=intent.reason,
                intent=intent,
                strategy=situation.strategy,
                pattern_features=situation.pattern_features,
                chart_levels=situation.chart_levels,
            )
        )
        planned_sell_markets.add(situation.market)
        planned_cash += situation.current_value_krw
        if len(orders) >= min(settings.realtime_candidate_top_n, remaining_order_slots, settings.allocation_max_orders_per_run):
            return orders

    if state.daily_realized_pnl_krw <= -settings.daily_loss_limit_krw and not paper_extreme_mode_enabled(settings):
        return orders

    selected_markets = {situation.market for situation in selected}
    if active_regime.block_new_entries and not realtime_regime_order_exception(settings, active_regime, selected):
        return orders

    if selected and planned_cash < settings.min_order_krw:
        best_entry_score = max((situation.score for situation in selected), default=Decimal("0"))
        held_rotation_candidates = sorted(
            (
                situation
                for situation in situations
                if situation.current_value_krw >= settings.min_order_krw
                and situation.market not in selected_markets
                and situation.market not in planned_sell_markets
                and situation.current_value_krw >= settings.min_order_krw
                and (situation.score < entry_floor or best_entry_score >= situation.score + Decimal("0.08"))
            ),
            key=lambda item: item.score,
        )
        for situation in held_rotation_candidates:
            position = state.position(situation.market)
            intent = OrderIntent(
                market=situation.market,
                side="ask",
                ord_type="market",
                volume=position.volume,
                reason=f"실시간 후보 교체: 더 강한 진입 후보 발견 · {situation.reason}",
            )
            orders.append(
                RealtimeOrderPlan(
                    market=situation.market,
                    side="ask",
                    amount_krw=situation.current_value_krw,
                    volume=position.volume,
                    current_price=situation.current_price,
                    reason=intent.reason,
                    intent=intent,
                    strategy=situation.strategy,
                    pattern_features=situation.pattern_features,
                    chart_levels=situation.chart_levels,
                )
            )
            planned_sell_markets.add(situation.market)
            planned_cash += situation.current_value_krw
            if planned_cash >= settings.min_order_krw:
                break
            if len(orders) >= min(settings.realtime_candidate_top_n, remaining_order_slots, settings.allocation_max_orders_per_run):
                return orders

    available_cash = planned_cash
    target_values = realtime_entry_target_values(settings, selected, deploy_limit, active_regime, pressure)
    for situation in selected:
        if remaining_cooldown_seconds(state, situation.market, settings.cooldown_seconds) > 0:
            continue
        target_value = target_values.get(situation.market, Decimal("0"))
        target_gap = target_value - situation.current_value_krw
        fee_buffer = Decimal("1") + settings.fee_rate
        cash_budget = (available_cash / fee_buffer).quantize(Decimal("1"), rounding=ROUND_DOWN)
        budget = min(target_gap, cash_budget, max_order_krw).quantize(Decimal("1"), rounding=ROUND_DOWN)
        if budget < settings.min_order_krw:
            continue
        intent = OrderIntent(
            market=situation.market,
            side="bid",
            ord_type="price",
            price=budget,
            reason=f"실시간 상황 진입: {situation.reason}",
        )
        orders.append(
            RealtimeOrderPlan(
                market=situation.market,
                side="bid",
                amount_krw=budget,
                volume=None,
                current_price=situation.current_price,
                reason=intent.reason,
                intent=intent,
                strategy=situation.strategy,
                pattern_features=situation.pattern_features,
                chart_levels=situation.chart_levels,
            )
        )
        available_cash -= budget
        if len(orders) >= min(remaining_order_slots, settings.allocation_max_orders_per_run):
            break
    return orders


def realtime_entry_target_values(
    settings: TradingSettings,
    selected: tuple[RealtimeSituation, ...],
    deploy_limit: Decimal,
    market_regime: MarketRegimeSignal,
    goal_pressure: GoalPacePressure | None = None,
) -> dict[str, Decimal]:
    if not selected or deploy_limit <= 0:
        return {}
    pressure = goal_pressure or neutral_goal_pace_pressure(deploy_limit)
    entry_floor = realtime_entry_score_floor(settings, market_regime, pressure)
    weights = [
        max(situation.score - entry_floor, Decimal("0.01")) + situation.urgency
        for situation in selected
    ]
    total_weight = sum(weights, Decimal("0"))
    if total_weight <= 0:
        total_weight = Decimal(len(selected))
        weights = [Decimal("1") for _ in selected]
    hard_cap = deploy_limit * settings.allocation_max_position_pct
    if paper_extreme_mode_enabled(settings):
        dynamic_pct = Decimal("1")
    else:
        dynamic_pct = realtime_dynamic_position_pct(len(selected), selected[0].score - entry_floor)
        if market_regime.block_new_entries:
            dynamic_pct = min(dynamic_pct, settings.realtime_recovery_scout_max_position_pct)
        else:
            dynamic_pct = min(Decimal("1"), dynamic_pct * pressure.position_multiplier)
    dynamic_cap = deploy_limit * dynamic_pct
    max_per_market = min(hard_cap, dynamic_cap)
    return {
        situation.market: min(max_per_market, deploy_limit * weight / total_weight)
        for situation, weight in zip(selected, weights)
    }


def realtime_dynamic_position_pct(candidate_count: int, top_score_edge: Decimal) -> Decimal:
    if candidate_count <= 1:
        if top_score_edge >= Decimal("0.55"):
            return Decimal("1")
        if top_score_edge >= Decimal("0.25"):
            return Decimal("0.65")
        return Decimal("0.35")
    if candidate_count == 2:
        return Decimal("0.55")
    if candidate_count == 3:
        return Decimal("0.40")
    if candidate_count <= 5:
        return Decimal("0.30")
    return Decimal("0.22")


def paper_extreme_mode_enabled(settings: TradingSettings) -> bool:
    return (
        settings.paper_extreme_mode
        and not settings.live_trading_enabled
        and not settings.web_live_trading_enabled
    )


def paper_extreme_volatility_probe_selected(
    settings: TradingSettings,
    state: PortfolioState,
    situations: list[RealtimeSituation],
    entry_floor: Decimal,
) -> tuple[RealtimeSituation, ...]:
    if not paper_extreme_mode_enabled(settings) or state.cash_krw < settings.min_order_krw:
        return ()
    open_positions = sum(1 for position in state.positions.values() if position.volume > 0)
    remaining_positions = max(0, settings.max_open_positions - open_positions)
    if remaining_positions <= 0:
        return ()
    candidate_limit = min(
        max(1, settings.realtime_candidate_top_n),
        max(1, settings.allocation_max_orders_per_run),
        remaining_positions,
        3,
    )
    ranked = [
        (paper_extreme_volatility_probe_rank(situation), situation)
        for situation in situations
        if paper_extreme_volatility_probe_allowed(settings, state, situation, entry_floor)
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected: list[RealtimeSituation] = []
    for _rank, situation in ranked[:candidate_limit]:
        tags = tuple(dict.fromkeys([*situation.tags, "volatility-probe", "paper-extreme"]))
        selected.append(
            replace(
                situation,
                action="buy",
                urgency=max(situation.urgency, Decimal("0.74")),
                tags=tags,
                reason=f"paper-extreme volatility probe · {situation.reason}",
            )
        )
    return tuple(selected)


def paper_extreme_volatility_probe_allowed(
    settings: TradingSettings,
    state: PortfolioState,
    situation: RealtimeSituation,
    entry_floor: Decimal,
) -> bool:
    if situation.current_price <= 0 or situation.current_value_krw >= settings.min_order_krw:
        return False
    if state.position(situation.market).volume > 0:
        return False
    if situation.action == "sell":
        return False
    hard_block_tags = {
        "crash-guard",
        "overheat-guard",
        "chase-guard",
        "microstructure-guard",
        "same-pattern-loss-guard",
    }
    if hard_block_tags.intersection(situation.tags):
        return False
    if situation.trend_1m_pct <= Decimal("-1.2") or situation.trend_5m_pct <= Decimal("-2.5"):
        return False
    if situation.day_change_pct >= Decimal("15") and situation.trend_1m_pct < 0:
        return False
    if situation.volatility_pct >= settings.strategy_max_volatility_pct and situation.volume_ratio < Decimal("1.5"):
        return False

    live_impulse = max(situation.seconds_trend_pct, situation.trend_1m_pct, situation.trend_5m_pct)
    has_volatility = (
        situation.volatility_pct >= settings.realtime_low_volatility_pct
        or abs(situation.seconds_trend_pct) >= Decimal("0.25")
        or abs(situation.trend_1m_pct) >= Decimal("0.25")
        or situation.volume_ratio >= Decimal("1.15")
        or situation.day_change_pct >= Decimal("3")
    )
    has_positive_flow = (
        live_impulse > 0
        or situation.trade_pressure > 0
        or (situation.day_change_pct > 0 and situation.volume_ratio >= Decimal("1"))
    )
    if not has_volatility or not has_positive_flow:
        return False
    if (
        situation.score < entry_floor - Decimal("0.85")
        and situation.volume_ratio < Decimal("2")
        and live_impulse < Decimal("0.5")
    ):
        return False
    return True


def paper_extreme_volatility_probe_rank(situation: RealtimeSituation) -> Decimal:
    live_impulse = max(situation.seconds_trend_pct, situation.trend_1m_pct, situation.trend_5m_pct)
    rank = situation.score
    rank += clamp(situation.volatility_pct / Decimal("1.5"), Decimal("0"), Decimal("1.4"))
    rank += clamp(live_impulse / Decimal("1.5"), Decimal("-0.3"), Decimal("1.2"))
    rank += clamp(situation.volume_ratio - Decimal("1"), Decimal("0"), Decimal("1.0"))
    rank += clamp(situation.trade_pressure / Decimal("4"), Decimal("-0.2"), Decimal("0.8"))
    rank += clamp(situation.day_change_pct / Decimal("20"), Decimal("-0.2"), Decimal("0.45"))
    return rank


def apply_orderbook_to_realtime_orders(
    settings: TradingSettings,
    client: RealtimeDecisionClient,
    orders: list[RealtimeOrderPlan],
    errors: list[dict[str, str]],
) -> list[RealtimeOrderPlan]:
    if not settings.orderbook_analysis_enabled or not hasattr(client, "get_orderbook"):
        return orders

    adjusted_orders: list[RealtimeOrderPlan] = []
    for order in orders:
        try:
            adjustment = adjust_order_for_orderbook(
                settings=settings,
                client=client,
                market=order.market,
                side=order.side,
                amount_krw=order.amount_krw,
                volume=order.volume,
                current_price=order.current_price,
                intent=order.intent,
            )
        except Exception as exc:
            errors.append({"market": order.market, "message": f"호가 분석 실패: {exc}"})
            adjusted_orders.append(order)
            continue
        if adjustment is None:
            adjusted_orders.append(order)
            continue
        if adjustment.skipped or adjustment.intent is None:
            errors.append({"market": order.market, "message": f"호가 분석으로 주문 제외: {adjustment.analysis.reason}"})
            continue
        adjusted_orders.append(
            replace(
                order,
                amount_krw=adjustment.amount_krw,
                volume=adjustment.volume,
                current_price=adjustment.current_price,
                reason=adjustment.reason,
                intent=adjustment.intent,
                orderbook=adjustment.analysis.to_dict(),
            )
        )
    return adjusted_orders


def execute_realtime_plan(
    plan: RealtimeDecisionPlan,
    state: PortfolioState,
    fee_rate: Decimal,
    settings: TradingSettings | None = None,
) -> list[dict[str, Any]]:
    broker = PortfolioPaperBroker(state, fee_rate)
    results: list[dict[str, Any]] = []
    pattern_model = load_pattern_model(settings) if settings is not None else None
    for order in plan.orders:
        result: OrderResult = broker.execute(order.intent, order.current_price)
        if result.ok and settings is not None:
            if order.side == "bid":
                pattern_model = record_pattern_entry(
                    settings=settings,
                    model=pattern_model,
                    market=order.market,
                    strategy=order.strategy,
                    entry_price=order.current_price,
                    features=order.pattern_features,
                    amount_krw=order.amount_krw,
                )
            elif order.side == "ask" and state.position(order.market).volume <= 0:
                pattern_model, _observation = record_pattern_exit(
                    settings=settings,
                    model=pattern_model,
                    market=order.market,
                    exit_price=order.current_price,
                    fee_rate=fee_rate,
                )
        results.append(
            {
                "market": order.market,
                "ok": result.ok,
                "message": result.message,
                "raw": result.raw,
                "side": order.side,
                "amountKrw": decimal_to_str(order.amount_krw),
            }
        )
    return results


def classify_realtime_mode(
    situations: list[RealtimeSituation],
    selected: tuple[RealtimeSituation, ...],
    orders: list[RealtimeOrderPlan],
) -> str:
    if any("volatility-probe" in situation.tags for situation in selected) and not any(order.side == "ask" for order in orders):
        return "변동성 정찰"
    if any(order.side == "ask" for order in orders):
        return "위험 회피"
    if selected:
        return "순간 진입"
    if any(situation.current_value_krw > 0 and situation.action == "hold" for situation in situations):
        return "추세 보유"
    return "감시"


def realtime_message(
    mode: str,
    situations: list[RealtimeSituation],
    selected: tuple[RealtimeSituation, ...],
    orders: list[RealtimeOrderPlan],
) -> str:
    top = situations[0] if situations else None
    top_text = f"{top.market} {top.reason}" if top else "평가 대상 없음"
    return f"{mode}: 후보 {len(selected)}개, 주문 {len(orders)}개 · {top_text}"


def held_markets(state: PortfolioState) -> list[str]:
    return [market for market, position in state.positions.items() if position.volume > 0]


def holding_age_seconds(state: PortfolioState, market: str) -> int | None:
    last_order_at = (state.last_order_by_market or {}).get(market)
    if not last_order_at:
        return None
    try:
        parsed = datetime.fromisoformat(last_order_at)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return max(0, int(elapsed))


def format_duration_seconds(seconds: int | None) -> str:
    if seconds is None:
        return "알 수 없음"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes == 0:
        return f"{hours}시간"
    return f"{hours}시간 {remaining_minutes}분"


def ticker_price(ticker: dict[str, Any]) -> Decimal:
    value = ticker.get("trade_price", ticker.get("tradePrice", 0))
    return Decimal(str(value or "0"))


def ticker_day_change_pct(ticker: dict[str, Any]) -> Decimal:
    value = ticker.get("signed_change_rate", ticker.get("change_rate", ticker.get("signedChangeRate", "0")))
    return Decimal(str(value or "0")) * Decimal("100")


def ticker_trade_value(ticker: dict[str, Any]) -> Decimal:
    value = ticker.get("acc_trade_price_24h", ticker.get("tradeValue24h", "0"))
    return Decimal(str(value or "0"))


def history_trend_pct(history: list[dict[str, str]], seconds: int) -> Decimal:
    if len(history) < 2:
        return Decimal("0")
    latest = history[-1]
    latest_time = parse_iso(latest.get("time", ""))
    latest_price = Decimal(str(latest.get("price") or "0"))
    if latest_time is None or latest_price <= 0:
        return Decimal("0")
    baseline = history[0]
    for row in reversed(history[:-1]):
        parsed = parse_iso(row.get("time", ""))
        if parsed is None:
            continue
        if (latest_time - parsed).total_seconds() >= seconds:
            baseline = row
            break
    baseline_price = Decimal(str(baseline.get("price") or "0"))
    if baseline_price <= 0:
        return Decimal("0")
    return (latest_price - baseline_price) / baseline_price * Decimal("100")


def parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def candle_trend_pct(ordered: list[Candle], minutes: int) -> Decimal:
    if len(ordered) < 2:
        return Decimal("0")
    index = max(0, len(ordered) - minutes - 1)
    start = ordered[index].trade_price
    end = ordered[-1].trade_price
    if start <= 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def candle_volatility_pct(ordered: list[Candle], window: int) -> Decimal:
    subset = ordered[-window:]
    closes = [float(candle.trade_price) for candle in subset if candle.trade_price > 0]
    if len(closes) < 2:
        return Decimal("0")
    average = sum(closes) / len(closes)
    if average <= 0:
        return Decimal("0")
    return Decimal(str(statistics.pstdev(closes) / average * 100))


def candle_drawdown_pct(ordered: list[Candle], window: int) -> Decimal:
    subset = ordered[-window:]
    if not subset:
        return Decimal("0")
    high = max(candle.high_price for candle in subset)
    latest = subset[-1].trade_price
    if high <= 0:
        return Decimal("0")
    return (latest - high) / high * Decimal("100")


def candle_range_position_pct(ordered: list[Candle], window: int) -> Decimal:
    subset = ordered[-window:]
    if not subset:
        return Decimal("50")
    high = max(candle.high_price for candle in subset)
    low = min(candle.low_price for candle in subset)
    latest = subset[-1].trade_price
    if high <= low:
        return Decimal("50")
    return (latest - low) / (high - low) * Decimal("100")


def candle_volume_ratio(ordered: list[Candle], window: int) -> Decimal:
    if len(ordered) < 2:
        return Decimal("1")
    latest = ordered[-1].candle_acc_trade_price
    previous = ordered[max(0, len(ordered) - window - 1) : -1]
    if not previous:
        return Decimal("1")
    baseline = sum((candle.candle_acc_trade_price for candle in previous), Decimal("0")) / Decimal(len(previous))
    if baseline <= 0:
        return Decimal("1")
    return latest / baseline


def realtime_trade_pressure(market: str, ticker: dict[str, Any]) -> Decimal:
    # REST ticker has no side-level pressure; merge_realtime_ticker_snapshot enriches
    # it from recent WebSocket trades when those trades are available.
    pressure = ticker.get("trade_pressure", 0)
    return Decimal(str(pressure or "0"))


def trade_pressure_from_trades(trades: list[Any]) -> str:
    bid = 0
    ask = 0
    for trade in trades[:20]:
        if not isinstance(trade, dict):
            continue
        side = str(trade.get("askBid") or trade.get("ask_bid") or "").upper()
        if side == "BID":
            bid += 1
        elif side == "ASK":
            ask += 1
    total = bid + ask
    if total == 0:
        return "0"
    return decimal_to_str((Decimal(bid) - Decimal(ask)) / Decimal(total) * Decimal("4"))


def volume_score(volume_ratio: Decimal) -> Decimal:
    if volume_ratio >= Decimal("3"):
        return Decimal("0.16")
    if volume_ratio >= Decimal("1.5"):
        return Decimal("0.10")
    if volume_ratio >= Decimal("1.15"):
        return Decimal("0.04")
    if volume_ratio <= Decimal("0.5"):
        return Decimal("-0.06")
    return Decimal("0")


def realtime_momentum_leader_bonus(
    settings: TradingSettings,
    day_change: Decimal,
    trend_1m: Decimal,
    trend_5m: Decimal,
    trend_30m: Decimal,
    volume_ratio: Decimal,
    trade_value_24h: Decimal,
    trade_pressure: Decimal,
    drawdown: Decimal,
    range_position: Decimal,
) -> Decimal:
    liquidity_floor = max(settings.risk_market_min_trade_value_24h_krw, Decimal("300000000"))
    if day_change < Decimal("1.5") or trade_value_24h < liquidity_floor:
        return Decimal("0")
    if trend_5m < Decimal("-0.25") or trend_30m < Decimal("-1.5") or drawdown < Decimal("-5"):
        return Decimal("0")

    score = Decimal("0")
    score += clamp(day_change / Decimal("8"), Decimal("0.12"), Decimal("0.85"))
    if trade_value_24h >= Decimal("10000000000"):
        score += Decimal("0.25")
    elif trade_value_24h >= Decimal("3000000000"):
        score += Decimal("0.16")
    if volume_ratio >= Decimal("3"):
        score += Decimal("0.24")
    elif volume_ratio >= Decimal("1.5"):
        score += Decimal("0.16")
    elif volume_ratio >= Decimal("1.1"):
        score += Decimal("0.08")
    if trend_5m >= Decimal("1"):
        score += Decimal("0.22")
    elif trend_5m >= Decimal("0.35"):
        score += Decimal("0.12")
    if trend_30m >= Decimal("1.5"):
        score += Decimal("0.18")
    elif trend_30m >= 0:
        score += Decimal("0.08")
    if trade_pressure > 0:
        score += Decimal("0.08")
    if trend_1m < Decimal("-0.6"):
        score -= Decimal("0.45")
    if day_change >= Decimal("8") and range_position >= Decimal("90") and trend_1m < 0:
        score -= Decimal("0.35")
    return clamp(score, Decimal("0"), Decimal("1.35"))


def realtime_goal_pace_pressure(settings: TradingSettings, equity: Decimal) -> GoalPacePressure:
    equity = max(equity, Decimal("1"))
    start = max(settings.goal_start_krw, Decimal("1"))
    target = max(settings.goal_target_krw, start)
    days = max(settings.goal_days, 1)
    stretch_target = target * Decimal("1.08")
    multiplier = decimal_power(stretch_target / start, 1 / days)
    today_required = start * (multiplier if multiplier > 0 else Decimal("1"))
    pace_pct = equity / today_required * Decimal("100") if today_required > 0 else Decimal("100")
    gap_krw = max(today_required - equity, Decimal("0"))

    if not settings.goal_scheduler_trading_enabled:
        return GoalPacePressure(
            enabled=False,
            level="disabled",
            label="목표 페이스 매매 반영 꺼짐",
            equity_krw=equity,
            today_required_krw=today_required,
            gap_krw=gap_krw,
            pace_pct=pace_pct,
            intensity=Decimal("0"),
            entry_score_adjustment=Decimal("0"),
            deploy_multiplier=Decimal("1"),
            max_order_multiplier=Decimal("1"),
            position_multiplier=Decimal("1"),
            reason="goal-scheduler-disabled",
        )

    deficit_pct = max(Decimal("100") - pace_pct, Decimal("0"))
    intensity = clamp(deficit_pct / Decimal("25"), Decimal("0"), Decimal("1"))
    if Decimal("90") <= pace_pct < Decimal("100"):
        intensity = max(intensity, Decimal("0.25"))
    elif pace_pct < Decimal("90"):
        intensity = max(intensity, Decimal("0.55"))

    if pace_pct >= Decimal("108"):
        level = "ahead"
        label = "초과 페이스"
    elif pace_pct >= Decimal("100"):
        level = "on_pace"
        label = "필수 페이스 충족"
    elif pace_pct >= Decimal("90"):
        level = "catch_up"
        label = "추격 필요"
    elif pace_pct >= Decimal("75"):
        level = "recovery"
        label = "강제 복구"
    else:
        level = "critical"
        label = "긴급 복구"

    entry_score_adjustment = -(settings.goal_scheduler_max_entry_relief * intensity)
    deploy_multiplier = Decimal("1") + settings.goal_scheduler_max_deploy_boost * intensity
    max_order_multiplier = Decimal("1") + settings.goal_scheduler_max_order_boost * intensity
    position_multiplier = Decimal("1") + settings.goal_scheduler_max_position_boost * intensity
    reason = (
        f"goal pace={pace_pct:.2f}% gap={gap_krw:.0f} "
        f"entryAdjust={entry_score_adjustment:.3f} deployX={deploy_multiplier:.2f}"
    )
    return GoalPacePressure(
        enabled=True,
        level=level,
        label=label,
        equity_krw=equity,
        today_required_krw=today_required,
        gap_krw=gap_krw,
        pace_pct=pace_pct,
        intensity=intensity,
        entry_score_adjustment=entry_score_adjustment,
        deploy_multiplier=deploy_multiplier,
        max_order_multiplier=max_order_multiplier,
        position_multiplier=position_multiplier,
        reason=reason,
    )


def neutral_goal_pace_pressure(equity: Decimal = Decimal("0")) -> GoalPacePressure:
    return GoalPacePressure(
        enabled=False,
        level="neutral",
        label="목표 페이스 중립",
        equity_krw=equity,
        today_required_krw=equity,
        gap_krw=Decimal("0"),
        pace_pct=Decimal("100"),
        intensity=Decimal("0"),
        entry_score_adjustment=Decimal("0"),
        deploy_multiplier=Decimal("1"),
        max_order_multiplier=Decimal("1"),
        position_multiplier=Decimal("1"),
        reason="goal-pressure-neutral",
    )


def decimal_power(base: Decimal, exponent: float) -> Decimal:
    if base <= 0:
        return Decimal("0")
    try:
        return Decimal(str(float(base) ** exponent))
    except (OverflowError, ValueError):
        return Decimal("0")


def maeuknam_realtime_entry_gate(
    settings: TradingSettings,
    signal: MaeuknamTechniqueSignal | None,
    held: bool,
    entry_floor: Decimal,
    daily_buy_lock: bool,
    risk_blocked: bool,
    market_regime: MarketRegimeSignal,
    tags: list[str],
) -> tuple[Decimal, bool]:
    if signal is None:
        tags.append("매억남 카드 없음")
        return Decimal("-1"), False

    tags.append("매억남 카드")
    tags.append(signal.technique_name)
    for block in signal.hard_blocks:
        tags.append(f"매억남 차단: {block}")

    if signal.entry_allowed:
        score = entry_floor + Decimal("0.10") + max(Decimal("0"), signal.score - signal.entry_threshold)
    elif signal.score >= signal.watch_threshold:
        score = min(entry_floor - Decimal("0.01"), settings.realtime_min_score + (signal.score - signal.watch_threshold) / Decimal("2"))
    else:
        score = signal.score - signal.entry_threshold

    if held:
        return score, False
    if daily_buy_lock:
        tags.append("매억남 차단: 일일 손실 한도")
        return score, False
    if risk_blocked:
        tags.append("매억남 차단: 리스크 가드")
        return score, False
    if market_regime.block_new_entries:
        tags.append("매억남 차단: 약세장 신규 진입 금지")
        return score, False
    return score, signal.entry_allowed


def format_maeuknam_realtime_reason(signal: MaeuknamTechniqueSignal | None) -> str:
    if signal is None:
        return "전략 카드 또는 캔들 수 부족으로 매억남 신호 없음"
    blocks = ", ".join(signal.hard_blocks) if signal.hard_blocks else "없음"
    return (
        f"{signal.technique_name} 점수 {signal.score:.3f}/{signal.entry_threshold:.2f}, "
        f"지지 {signal.support_price:.8g}, 저항 {signal.resistance_price:.8g}, "
        f"손절 {signal.stop_price:.8g}, 1차목표 {signal.target1_price:.8g}, "
        f"RR {signal.reward_risk:.2f}, 차단 {blocks}"
    )


def realtime_entry_score_floor(
    settings: TradingSettings,
    market_regime: MarketRegimeSignal,
    goal_pressure: GoalPacePressure | None = None,
) -> Decimal:
    floor = settings.realtime_min_score + settings.risk_min_entry_score_buffer + market_regime.min_score_adjustment
    if goal_pressure is not None and goal_pressure.enabled:
        floor += goal_pressure.entry_score_adjustment
    return max(settings.realtime_min_score, floor)


def realtime_entry_allowed(
    settings: TradingSettings,
    market_regime: MarketRegimeSignal,
    score: Decimal,
    entry_floor: Decimal,
    tags: tuple[str, ...],
    risk_blocked: bool,
    pattern_blocked: bool,
    volume_ratio: Decimal,
    trade_pressure: Decimal,
    trend_1m: Decimal,
    trend_5m: Decimal,
) -> bool:
    if not market_regime.block_new_entries:
        return True
    if not settings.realtime_weak_breakout_enabled or market_regime.label == "risk-off":
        return False
    if pattern_blocked:
        return False
    hard_block_tags = {
        "급락",
        "하락 추세",
        "일봉 과열 둔화",
        "저변동 정체",
        "crash-guard",
        "overheat-guard",
        "chase-guard",
        "microstructure-guard",
        "same-pattern-loss-guard",
    }
    if any(tag in tags for tag in hard_block_tags):
        return False
    momentum_tags = {"급등", "상승 추세", "거래대금 증가", "상승 중 눌림", "상승 리더", "profit-pattern"}
    if not any(tag in momentum_tags for tag in tags):
        return False
    if risk_blocked:
        if not settings.realtime_recovery_scout_enabled:
            return False
        allowed_soft_risk_tags = {"loss-streak-guard", "liquidity-guard", "market-weak", "market-narrow-breadth", "loss-pattern", "profit-pattern"}
        if any(tag.endswith("-guard") and tag not in allowed_soft_risk_tags for tag in tags):
            return False
        if volume_ratio < Decimal("1.5") or trade_pressure <= 0:
            return False
        if trend_1m < 0 and trend_5m < 0:
            return False
    return score >= entry_floor + settings.realtime_weak_breakout_score_buffer


def realtime_goal_recovery_scout_allowed(
    settings: TradingSettings,
    goal_pressure: GoalPacePressure | None,
    market_regime: MarketRegimeSignal,
    held: bool,
    score: Decimal,
    entry_floor: Decimal,
    tags: tuple[str, ...],
    risk_blocked: bool,
    pattern_blocked: bool,
    pattern_loss_score: Decimal,
    pattern_profit_score: Decimal,
    volume_ratio: Decimal,
    trade_pressure: Decimal,
    trend_1m: Decimal,
    trend_5m: Decimal,
    trend_30m: Decimal,
    low_volatility_stalled: bool,
) -> bool:
    if held or goal_pressure is None or not goal_pressure.enabled:
        return False
    if not settings.realtime_recovery_scout_enabled or goal_pressure.intensity < Decimal("0.5"):
        return False
    if market_regime.label == "risk-off":
        return False
    hard_block_tags = {
        "급락",
        "하락 추세",
        "일봉 과열 둔화",
        "변동성 과열",
        "crash-guard",
        "overheat-guard",
        "chase-guard",
        "microstructure-guard",
    }
    if any(tag in tags for tag in hard_block_tags) or low_volatility_stalled:
        return False
    if "same-pattern-loss-guard" in tags:
        strong_loss_retest = (
            volume_ratio >= Decimal("3")
            and trade_pressure >= 0
            and trend_1m >= 0
            and trend_5m >= 0
            and pattern_loss_score < Decimal("0.85")
        )
        if not strong_loss_retest:
            return False
    if risk_blocked and not {"liquidity-guard", "loss-streak-guard", "market-weak", "market-narrow-breadth"}.intersection(tags):
        return False
    if pattern_blocked and pattern_loss_score >= Decimal("0.82") and pattern_profit_score < Decimal("0.55"):
        return False
    if volume_ratio < Decimal("1.2"):
        return False
    pressure_confirmed = trade_pressure > 0 or (
        trade_pressure > Decimal("-1")
        and volume_ratio >= Decimal("2")
        and trend_1m >= 0
        and trend_5m >= Decimal("0.5")
    ) or (
        trade_pressure >= 0
        and volume_ratio >= Decimal("3")
        and trend_1m >= 0
        and (trend_5m >= Decimal("0.35") or trend_30m >= Decimal("1"))
    )
    if not pressure_confirmed:
        return False
    trend_confirmed = (
        trend_1m >= 0
        and trend_5m > 0
        and trend_30m >= Decimal("-0.5")
    ) or (
        volume_ratio >= Decimal("3")
        and trade_pressure >= 0
        and trend_1m >= 0
        and (trend_5m >= Decimal("0.35") or trend_30m >= Decimal("1"))
    )
    if not trend_confirmed:
        return False
    return score >= entry_floor + Decimal("0.15")


def realtime_regime_order_exception(
    settings: TradingSettings,
    market_regime: MarketRegimeSignal,
    selected: tuple[RealtimeSituation, ...],
) -> bool:
    if paper_extreme_mode_enabled(settings) and bool(selected):
        return True
    return (
        settings.realtime_weak_breakout_enabled
        and bool(selected)
        and market_regime.block_new_entries
        and market_regime.label != "risk-off"
    )


def clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]
