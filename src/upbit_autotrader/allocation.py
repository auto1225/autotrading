from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from decimal import Decimal, ROUND_DOWN
from typing import Any, Protocol
import time

from .broker import PortfolioPaperBroker
from .config import TradingSettings
from .learning import load_learning_model
from .market_regime import MarketRegimeSignal, evaluate_market_regime
from .market_risk import evaluate_market_risk
from .models import Candle, OrderIntent, OrderResult, Signal, decimal_to_str
from .orderbook import adjust_order_for_orderbook
from .pattern_learning import (
    feature_snapshot,
    load_pattern_model,
    record_pattern_entry,
    record_pattern_exit,
    score_current_pattern,
)
from .risk import remaining_cooldown_seconds
from .state import PortfolioState, reset_daily_counters_if_needed
from .strategy import STRATEGY_CATALOG, make_strategy_by_name
from .trade_levels import ChartTradeLevels, chart_trade_levels


PROBABILITY_EDGE_STRATEGY_NAME = "probability_edge"
MAEUKNAM_CARDS_STRATEGY_NAME = "maeuknam_cards"


class AllocationClient(Protocol):
    def get_minute_candles(
        self,
        market: str,
        unit: int = 5,
        count: int = 80,
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
class AllocationCandidate:
    market: str
    label: str
    strategy: str
    score: Decimal
    learned_score: Decimal
    current_price: Decimal
    current_value_krw: Decimal
    target_value_krw: Decimal
    gap_krw: Decimal
    signal: Signal
    trend_pct: Decimal
    volume_ratio: Decimal
    regime: str
    reason: str
    pattern_profit_score: Decimal = Decimal("0")
    pattern_loss_score: Decimal = Decimal("0")
    pattern_adjustment: Decimal = Decimal("0")
    risk_adjustment: Decimal = Decimal("0")
    risk_reason: str = "risk-clear"
    market_regime: str = "neutral"
    pattern_features: dict[str, str] = field(default_factory=dict)
    chart_levels: ChartTradeLevels | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "label": self.label,
            "strategy": self.strategy,
            "score": decimal_to_str(self.score),
            "learnedScore": decimal_to_str(self.learned_score),
            "currentPrice": decimal_to_str(self.current_price),
            "currentValueKrw": decimal_to_str(self.current_value_krw),
            "targetValueKrw": decimal_to_str(self.target_value_krw),
            "gapKrw": decimal_to_str(self.gap_krw),
            "signal": {
                "action": self.signal.action,
                "reason": self.signal.reason,
                "strength": decimal_to_str(self.signal.strength),
            },
            "trendPct": decimal_to_str(self.trend_pct),
            "volumeRatio": decimal_to_str(self.volume_ratio),
            "regime": self.regime,
            "reason": self.reason,
            "patternProfitScore": decimal_to_str(self.pattern_profit_score),
            "patternLossScore": decimal_to_str(self.pattern_loss_score),
            "patternAdjustment": decimal_to_str(self.pattern_adjustment),
            "riskAdjustment": decimal_to_str(self.risk_adjustment),
            "riskReason": self.risk_reason,
            "marketRegime": self.market_regime,
            "patternFeatures": self.pattern_features,
            "chartLevels": self.chart_levels.to_dict() if self.chart_levels is not None else None,
            "entryPrice": decimal_to_str(self.chart_levels.entry_price) if self.chart_levels is not None else "0",
            "targetSellPrice": decimal_to_str(self.chart_levels.take_profit_price) if self.chart_levels is not None else "0",
            "stopLossPrice": decimal_to_str(self.chart_levels.stop_loss_price) if self.chart_levels is not None else "0",
            "trailingStopPrice": decimal_to_str(self.chart_levels.trailing_stop_price) if self.chart_levels is not None else "0",
            "riskReward": decimal_to_str(self.chart_levels.risk_reward) if self.chart_levels is not None else "0",
        }


@dataclass(frozen=True)
class AllocationOrderPlan:
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
class AllocationPlan:
    mode: str
    deploy_limit_krw: Decimal
    equity_krw: Decimal
    cash_krw: Decimal
    selected_count: int
    scanned_count: int
    candidates: tuple[AllocationCandidate, ...]
    selected: tuple[AllocationCandidate, ...]
    orders: tuple[AllocationOrderPlan, ...]
    errors: tuple[dict[str, str], ...]
    market_regime: dict[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "deployLimitKrw": decimal_to_str(self.deploy_limit_krw),
            "equityKrw": decimal_to_str(self.equity_krw),
            "cashKrw": decimal_to_str(self.cash_krw),
            "selectedCount": self.selected_count,
            "scannedCount": self.scanned_count,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected": [candidate.to_dict() for candidate in self.selected],
            "orders": [order.to_dict() for order in self.orders],
            "errors": list(self.errors),
            "marketRegime": self.market_regime,
            "message": self.message,
        }


def build_dynamic_allocation_plan(
    settings: TradingSettings,
    client: AllocationClient,
    state: PortfolioState,
    markets: tuple[str, ...] | None = None,
    pause_seconds: float = 0.12,
) -> AllocationPlan:
    reset_daily_counters_if_needed(state)
    model = load_learning_model(settings)
    pattern_model = load_pattern_model(settings)
    learned_markets = model.get("markets") if isinstance(model.get("markets"), dict) else {}
    maeuknam_only = settings.strategy_name == MAEUKNAM_CARDS_STRATEGY_NAME
    scan_markets = tuple(markets) if markets is not None else tuple(settings.markets if maeuknam_only else learned_markets.keys() or settings.markets)
    errors: list[dict[str, str]] = []
    candidates: list[AllocationCandidate] = []
    prices: dict[str, Decimal] = {}
    candle_map: dict[str, list[Candle]] = {}
    recommendations: dict[str, dict[str, Any]] = {}

    for index, market in enumerate(scan_markets):
        recommendation = learned_markets.get(market)
        if not isinstance(recommendation, dict) and not maeuknam_only:
            continue
        if not isinstance(recommendation, dict):
            recommendation = {"market": market, "label": market, "bestStrategy": MAEUKNAM_CARDS_STRATEGY_NAME, "score": "0"}
        try:
            raw = fetch_allocation_candles(settings, client, market)
            candles = [Candle.from_upbit(item) for item in raw]
            candle_map[market] = candles
            recommendations[market] = recommendation
        except Exception as exc:
            errors.append({"market": market, "message": str(exc)})
        if index < len(scan_markets) - 1:
            time.sleep(pause_seconds)

    market_regime = evaluate_market_regime(settings, candle_map)
    entry_floor = allocation_entry_score_floor(settings, market_regime)
    for market, candles in candle_map.items():
        recommendation = recommendations.get(market)
        if not isinstance(recommendation, dict) and not maeuknam_only:
            continue
        if not isinstance(recommendation, dict):
            recommendation = {"market": market, "label": market, "bestStrategy": MAEUKNAM_CARDS_STRATEGY_NAME, "score": "0"}
        try:
            candidate = score_allocation_candidate(settings, state, candles, recommendation, pattern_model, market_regime)
            prices[market] = candidate.current_price
            entry_signal_ok = (
                candidate.current_value_krw >= settings.min_order_krw
                or candidate.signal.action == "buy"
            )
            if candidate.score >= entry_floor and candidate.signal.action != "sell" and entry_signal_ok:
                candidates.append(candidate)
        except Exception as exc:
            errors.append({"market": market, "message": str(exc)})

    for market, position in state.positions.items():
        if position.volume <= 0 or market in prices:
            continue
        try:
            raw = fetch_allocation_candles(settings, client, market)
            candles = [Candle.from_upbit(item) for item in raw]
            if candles:
                prices[market] = candles[0].trade_price
        except Exception:
            prices[market] = Decimal("0")

    equity = state.equity(prices)
    deploy_limit = equity * settings.allocation_max_deploy_pct * market_regime.deploy_multiplier
    selected = select_allocation_candidates(candidates, settings)
    selected_with_targets = assign_targets(settings, state, selected, deploy_limit)
    selected_markets = {candidate.market for candidate in selected_with_targets}
    orders = build_rebalance_orders(settings, state, selected_with_targets, selected_markets, prices)
    orders = apply_orderbook_to_allocation_orders(settings, client, orders, errors)
    mode = "집중" if len(selected_with_targets) <= settings.allocation_focus_top_n else "분산"
    message = (
        f"{mode} 배분 후보 {len(selected_with_targets)}개, 주문 후보 {len(orders)}개"
        if selected_with_targets
        else "동적 배분 조건을 통과한 코인이 없습니다"
    )

    return AllocationPlan(
        mode=mode,
        deploy_limit_krw=deploy_limit,
        equity_krw=equity,
        cash_krw=state.cash_krw,
        selected_count=len(selected_with_targets),
        scanned_count=len(scan_markets),
        candidates=tuple(sorted(candidates, key=lambda item: item.score, reverse=True)[:30]),
        selected=tuple(selected_with_targets),
        orders=tuple(orders[: settings.allocation_max_orders_per_run]),
        errors=tuple(errors),
        market_regime=market_regime.to_dict(),
        message=message,
    )


def fetch_allocation_candles(
    settings: TradingSettings,
    client: AllocationClient,
    market: str,
    retry_count: int = 2,
) -> list[dict[str, Any]]:
    count = max(settings.candle_count, settings.long_window + 5)
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return client.get_minute_candles(market=market, unit=settings.candle_unit, count=count)
        except Exception as exc:
            last_error = exc
            message = str(exc)
            if "429" not in message and "too_many_requests" not in message:
                raise
            if attempt < retry_count:
                time.sleep(0.8 + attempt * 0.4)
    if last_error is not None:
        raise last_error
    return []


def score_allocation_candidate(
    settings: TradingSettings,
    state: PortfolioState,
    candles: list[Candle],
    recommendation: dict[str, Any],
    pattern_model: dict[str, Any] | None = None,
    market_regime: MarketRegimeSignal | None = None,
) -> AllocationCandidate:
    if not candles:
        market = str(recommendation.get("market") or settings.market)
        return AllocationCandidate(
            market=market,
            label=str(recommendation.get("label") or market),
            strategy=str(recommendation.get("bestStrategy") or "guarded_momentum"),
            score=Decimal("0"),
            learned_score=Decimal("0"),
            current_price=Decimal("0"),
            current_value_krw=Decimal("0"),
            target_value_krw=Decimal("0"),
            gap_krw=Decimal("0"),
            signal=Signal("hold", market, Decimal("0"), "캔들 데이터 없음"),
            trend_pct=Decimal("0"),
            volume_ratio=Decimal("0"),
            regime=str(recommendation.get("regime") or ""),
            reason="캔들 데이터 없음",
        )

    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    latest = ordered[-1]
    maeuknam_only = settings.strategy_name == MAEUKNAM_CARDS_STRATEGY_NAME
    strategy_name = MAEUKNAM_CARDS_STRATEGY_NAME if maeuknam_only else str(recommendation.get("bestStrategy") or "guarded_momentum")
    if strategy_name not in STRATEGY_CATALOG or strategy_name == "adaptive_learning":
        strategy_name = "guarded_momentum"
    market_settings = replace(settings, market=latest.market, markets=(latest.market,), strategy_name=strategy_name)
    signal = make_strategy_by_name(market_settings, strategy_name).evaluate(candles)
    current_value = state.position_value(latest.market, latest.trade_price)
    edge_override_bonus = Decimal("0")
    if not maeuknam_only and strategy_name != PROBABILITY_EDGE_STRATEGY_NAME:
        edge_settings = replace(
            settings,
            market=latest.market,
            markets=(latest.market,),
            strategy_name=PROBABILITY_EDGE_STRATEGY_NAME,
        )
        edge_signal = make_strategy_by_name(edge_settings, PROBABILITY_EDGE_STRATEGY_NAME).evaluate(candles)
        if edge_signal.action == "buy" and (signal.action != "buy" or edge_signal.strength >= signal.strength):
            strategy_name = PROBABILITY_EDGE_STRATEGY_NAME
            signal = edge_signal
            edge_override_bonus = Decimal("0.18")
        elif edge_signal.action == "sell" and (current_value >= settings.min_order_krw or signal.action != "buy"):
            strategy_name = PROBABILITY_EDGE_STRATEGY_NAME
            signal = edge_signal
    trend_pct = recent_trend_pct(ordered, 12)
    trend_1m = recent_trend_pct(ordered, 1)
    trend_5m = recent_trend_pct(ordered, 5)
    volatility = recent_volatility_pct(ordered, 12)
    drawdown = recent_drawdown_pct(ordered, 30)
    range_position = recent_range_position_pct(ordered, 30)
    volume_ratio = recent_volume_ratio(ordered, 20)
    learned_score = Decimal(str(recommendation.get("score") or "0"))
    learned_component = allocation_learned_score_component(learned_score)
    score = (
        signal.strength
        if maeuknam_only and signal.action == "buy"
        else Decimal("-1")
        if maeuknam_only
        else learned_component + signal_bonus(signal) + trend_bonus(trend_pct) + volume_bonus(volume_ratio) + edge_override_bonus
    )
    pattern_score = score_current_pattern(pattern_model, latest.market, strategy_name, ordered)
    pattern_features = feature_snapshot(ordered).to_dict()
    market_regime = market_regime or MarketRegimeSignal()
    risk_signal = evaluate_market_risk(
        settings=settings,
        pattern_model=pattern_model,
        market=latest.market,
        held=current_value >= settings.min_order_krw,
        trend_1m_pct=trend_1m,
        trend_5m_pct=trend_5m,
        trend_30m_pct=trend_pct,
        volatility_pct=volatility,
        drawdown_pct=drawdown,
        volume_ratio=volume_ratio,
        day_change_pct=Decimal("0"),
        range_position_pct=range_position,
        latest_candle_trade_value_krw=latest.candle_acc_trade_price,
        strategy=strategy_name,
    )
    levels = chart_trade_levels(
        settings=settings,
        candles=ordered,
        current_price=latest.trade_price,
        avg_entry_price=state.position(latest.market).avg_entry_price,
        held=current_value >= settings.min_order_krw,
    )
    if not maeuknam_only:
        score += pattern_score.adjustment
    score += risk_signal.score_adjustment
    score += market_regime.score_adjustment
    if levels.risk_reward >= Decimal("1.45"):
        score += Decimal("0.08")
    elif current_value < settings.min_order_krw and levels.risk_reward < Decimal("1.05"):
        score -= Decimal("0.22")
    if pattern_score.blocked and not maeuknam_only:
        score -= Decimal("1")
    if risk_signal.block_entry and current_value < settings.min_order_krw:
        score -= Decimal("1")
    if market_regime.block_new_entries and current_value < settings.min_order_krw:
        score -= Decimal("1")
    if risk_signal.exit_now and current_value >= settings.min_order_krw:
        signal = Signal("sell", latest.market, latest.trade_price, f"risk exit: {risk_signal.reason}")
    if current_value >= settings.min_order_krw and levels.stop_loss_price > 0 and latest.trade_price <= levels.stop_loss_price:
        signal = Signal("sell", latest.market, latest.trade_price, f"chart stop exit: {levels.reason}")
    if current_value >= settings.min_order_krw and levels.take_profit_price > 0 and latest.trade_price >= levels.take_profit_price:
        signal = Signal("sell", latest.market, latest.trade_price, f"chart target exit: {levels.reason}")
    if market_regime.block_new_entries and current_value >= settings.min_order_krw:
        signal = Signal("sell", latest.market, latest.trade_price, f"market regime exit: {market_regime.reason}")
    label = str(
        STRATEGY_CATALOG[strategy_name]["label"]
        if strategy_name == PROBABILITY_EDGE_STRATEGY_NAME
        else recommendation.get("label") or STRATEGY_CATALOG[strategy_name]["label"]
    )
    if maeuknam_only:
        reason = (
            f"{label} 전용 신호 {signal.action}, 강도 {signal.strength:.3f}, "
            f"1시간 추세 {trend_pct:.2f}%, 거래대금 {volume_ratio:.2f}배, {signal.reason}"
        )
    else:
        reason = (
            f"{label} 학습점수 {learned_score:.3f}/적용 {learned_component:.3f}, 1시간 추세 {trend_pct:.2f}%, "
            f"거래대금 {volume_ratio:.2f}배, {pattern_score.reason}"
        )

    entry_floor = allocation_entry_score_floor(settings, market_regime)
    reason = f"{reason} 쨌 {levels.reason} risk={risk_signal.reason} market={market_regime.reason} entryFloor={entry_floor:.2f}"
    return AllocationCandidate(
        market=latest.market,
        label=label,
        strategy=strategy_name,
        score=score,
        learned_score=learned_score,
        current_price=latest.trade_price,
        current_value_krw=current_value,
        target_value_krw=Decimal("0"),
        gap_krw=Decimal("0"),
        signal=signal,
        trend_pct=trend_pct,
        volume_ratio=volume_ratio,
        regime=str(recommendation.get("regime") or ""),
        reason=reason,
        pattern_profit_score=pattern_score.profit_similarity,
        pattern_loss_score=pattern_score.loss_similarity,
        pattern_adjustment=pattern_score.adjustment,
        risk_adjustment=risk_signal.score_adjustment,
        risk_reason=risk_signal.reason,
        market_regime=market_regime.label,
        pattern_features=pattern_features,
        chart_levels=levels,
    )


def recent_trend_pct(ordered: list[Candle], window: int) -> Decimal:
    if len(ordered) < 2:
        return Decimal("0")
    start_index = max(0, len(ordered) - window - 1)
    start = ordered[start_index].trade_price
    end = ordered[-1].trade_price
    if start <= 0:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def recent_volatility_pct(ordered: list[Candle], window: int) -> Decimal:
    subset = ordered[-window:]
    ranges = [
        (candle.high_price - candle.low_price) / candle.trade_price * Decimal("100")
        for candle in subset
        if candle.trade_price > 0
    ]
    if not ranges:
        return Decimal("0")
    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def recent_drawdown_pct(ordered: list[Candle], window: int) -> Decimal:
    subset = ordered[-window:]
    if not subset:
        return Decimal("0")
    high = max(candle.high_price for candle in subset)
    if high <= 0:
        return Decimal("0")
    return (subset[-1].trade_price - high) / high * Decimal("100")


def recent_range_position_pct(ordered: list[Candle], window: int) -> Decimal:
    subset = ordered[-window:]
    if not subset:
        return Decimal("50")
    high = max(candle.high_price for candle in subset)
    low = min(candle.low_price for candle in subset)
    if high <= low:
        return Decimal("50")
    return (subset[-1].trade_price - low) / (high - low) * Decimal("100")


def recent_volume_ratio(ordered: list[Candle], window: int) -> Decimal:
    if len(ordered) < 2:
        return Decimal("1")
    recent = ordered[-1].candle_acc_trade_price
    baseline_items = ordered[max(0, len(ordered) - window - 1) : -1]
    if not baseline_items:
        return Decimal("1")
    baseline = sum((item.candle_acc_trade_price for item in baseline_items), Decimal("0")) / Decimal(len(baseline_items))
    if baseline <= 0:
        return Decimal("1")
    return recent / baseline


def signal_bonus(signal: Signal) -> Decimal:
    if signal.action == "buy":
        return Decimal("0.14") * signal.strength
    if signal.action == "sell":
        return Decimal("-0.3")
    return Decimal("0")


def trend_bonus(trend_pct: Decimal) -> Decimal:
    if trend_pct <= 0:
        return max(Decimal("-0.12"), trend_pct / Decimal("25"))
    return min(Decimal("0.18"), trend_pct / Decimal("18"))


def volume_bonus(volume_ratio: Decimal) -> Decimal:
    if volume_ratio >= Decimal("1.5"):
        return Decimal("0.08")
    if volume_ratio >= Decimal("1.15"):
        return Decimal("0.04")
    if volume_ratio <= Decimal("0.55"):
        return Decimal("-0.04")
    return Decimal("0")


def allocation_learned_score_component(learned_score: Decimal) -> Decimal:
    return max(Decimal("-1.5"), min(Decimal("1.8"), learned_score))


def allocation_entry_score_floor(settings: TradingSettings, market_regime: MarketRegimeSignal) -> Decimal:
    return settings.allocation_min_score + settings.risk_min_entry_score_buffer + market_regime.min_score_adjustment


def select_allocation_candidates(
    candidates: list[AllocationCandidate],
    settings: TradingSettings,
) -> list[AllocationCandidate]:
    ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
    if not ranked:
        return []
    if len(ranked) > settings.allocation_focus_top_n:
        score_gap = ranked[0].score - ranked[settings.allocation_focus_top_n].score
        if score_gap >= settings.allocation_focus_score_gap:
            return ranked[: settings.allocation_focus_top_n]
    return ranked[: settings.allocation_top_n]


def assign_targets(
    settings: TradingSettings,
    state: PortfolioState,
    selected: list[AllocationCandidate],
    deploy_limit: Decimal,
) -> list[AllocationCandidate]:
    if not selected or deploy_limit <= 0:
        return []
    positive_scores = [max(candidate.score, Decimal("0.01")) for candidate in selected]
    total_score = sum(positive_scores, Decimal("0"))
    max_position_value = deploy_limit * settings.allocation_max_position_pct
    assigned: list[AllocationCandidate] = []
    for candidate, score in zip(selected, positive_scores):
        target = deploy_limit * score / total_score if total_score > 0 else deploy_limit / Decimal(len(selected))
        target = min(target, max_position_value)
        if target < settings.min_order_krw and candidate.current_value_krw <= 0:
            continue
        assigned.append(
            AllocationCandidate(
                market=candidate.market,
                label=candidate.label,
                strategy=candidate.strategy,
                score=candidate.score,
                learned_score=candidate.learned_score,
                current_price=candidate.current_price,
                current_value_krw=candidate.current_value_krw,
                target_value_krw=target,
                gap_krw=target - candidate.current_value_krw,
                signal=candidate.signal,
                trend_pct=candidate.trend_pct,
                volume_ratio=candidate.volume_ratio,
                regime=candidate.regime,
                reason=candidate.reason,
                pattern_profit_score=candidate.pattern_profit_score,
                pattern_loss_score=candidate.pattern_loss_score,
                pattern_adjustment=candidate.pattern_adjustment,
                risk_adjustment=candidate.risk_adjustment,
                risk_reason=candidate.risk_reason,
                market_regime=candidate.market_regime,
                pattern_features=candidate.pattern_features,
                chart_levels=candidate.chart_levels,
            )
        )
    return assigned


def build_rebalance_orders(
    settings: TradingSettings,
    state: PortfolioState,
    selected: list[AllocationCandidate],
    selected_markets: set[str],
    prices: dict[str, Decimal],
) -> list[AllocationOrderPlan]:
    orders: list[AllocationOrderPlan] = []
    reset_daily_counters_if_needed(state)
    remaining_order_slots = settings.max_daily_orders - state.daily_order_count
    max_orders_this_run = min(settings.allocation_max_orders_per_run, remaining_order_slots)
    if max_orders_this_run <= 0:
        return orders

    for market, position in sorted(state.positions.items()):
        if position.volume <= 0:
            continue
        price = prices.get(market, Decimal("0"))
        if price <= 0:
            continue
        selected_candidate = next((candidate for candidate in selected if candidate.market == market), None)
        current_value = position.value(price)
        target_value = selected_candidate.target_value_krw if selected_candidate else Decimal("0")
        excess = current_value - target_value
        rebalance_floor = max(settings.min_order_krw * Decimal("3"), current_value * Decimal("0.15"))
        if market in selected_markets and excess < rebalance_floor:
            continue
        volume = position.volume if target_value <= 0 else min(position.volume, excess / price)
        if volume <= 0:
            continue
        amount = volume * price
        if amount < settings.min_order_krw:
            continue
        intent = OrderIntent(
            market=market,
            side="ask",
            ord_type="market",
            volume=volume,
            reason="동적 배분 리밸런싱: 목표 비중 축소",
        )
        strategy = selected_candidate.strategy if selected_candidate else ""
        pattern_features = selected_candidate.pattern_features if selected_candidate else {}
        orders.append(
            AllocationOrderPlan(
                market,
                "ask",
                amount,
                volume,
                price,
                intent.reason,
                intent,
                strategy=strategy,
                pattern_features=pattern_features,
                chart_levels=selected_candidate.chart_levels if selected_candidate else None,
            )
        )
        if len(orders) >= max_orders_this_run:
            return orders

    if state.daily_realized_pnl_krw <= -settings.daily_loss_limit_krw:
        return orders

    available_cash = state.cash_krw
    for candidate in selected:
        entry_gap_floor = settings.min_order_krw
        if candidate.current_value_krw >= settings.min_order_krw:
            entry_gap_floor = max(settings.min_order_krw * Decimal("3"), candidate.target_value_krw * Decimal("0.15"))
        if candidate.gap_krw < entry_gap_floor:
            continue
        if remaining_cooldown_seconds(state, candidate.market, settings.cooldown_seconds) > 0:
            continue
        budget = min(candidate.gap_krw, available_cash)
        budget = budget.quantize(Decimal("1"), rounding=ROUND_DOWN)
        if budget < settings.min_order_krw:
            continue
        intent = OrderIntent(
            market=candidate.market,
            side="bid",
            ord_type="price",
            price=budget,
            reason=f"동적 배분 진입: {candidate.reason}",
        )
        orders.append(
            AllocationOrderPlan(
                candidate.market,
                "bid",
                budget,
                None,
                candidate.current_price,
                intent.reason,
                intent,
                strategy=candidate.strategy,
                pattern_features=candidate.pattern_features,
                chart_levels=candidate.chart_levels,
            )
        )
        available_cash -= budget
        if len(orders) >= max_orders_this_run:
            break
    return orders


def apply_orderbook_to_allocation_orders(
    settings: TradingSettings,
    client: AllocationClient,
    orders: list[AllocationOrderPlan],
    errors: list[dict[str, str]],
) -> list[AllocationOrderPlan]:
    if not settings.orderbook_analysis_enabled or not hasattr(client, "get_orderbook"):
        return orders

    adjusted_orders: list[AllocationOrderPlan] = []
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


def execute_allocation_plan(
    plan: AllocationPlan,
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
