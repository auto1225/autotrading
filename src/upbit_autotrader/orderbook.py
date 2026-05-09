from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_DOWN
from typing import Any, Protocol

from .config import TradingSettings
from .models import OrderIntent, decimal_to_str


PRICE_QUANT = Decimal("0.00000001")


class OrderbookClient(Protocol):
    def get_orderbook(
        self,
        markets: str | list[str],
        count: int | None = None,
        level: str | int | None = None,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class OrderbookLevel:
    ask_price: Decimal
    bid_price: Decimal
    ask_size: Decimal
    bid_size: Decimal


@dataclass(frozen=True)
class SweepResult:
    amount_krw: Decimal
    volume: Decimal
    avg_price: Decimal
    filled_ratio: Decimal
    levels_used: int


@dataclass(frozen=True)
class OrderbookAnalysis:
    market: str
    side: str
    requested_amount_krw: Decimal
    requested_volume: Decimal
    recommended_amount_krw: Decimal
    recommended_volume: Decimal
    best_ask: Decimal
    best_bid: Decimal
    mid_price: Decimal
    spread_pct: Decimal
    bid_ask_depth_ratio: Decimal
    visible_ask_krw: Decimal
    visible_bid_krw: Decimal
    visible_ask_size: Decimal
    visible_bid_size: Decimal
    expected_avg_price: Decimal
    recommended_avg_price: Decimal
    expected_slippage_pct: Decimal
    recommended_slippage_pct: Decimal
    fillable_amount_krw: Decimal
    fillable_volume: Decimal
    fill_ratio: Decimal
    suggested_limit_price: Decimal
    action: str
    action_label: str
    reprice_action: str
    reason: str
    levels_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "side": self.side,
            "requestedAmountKrw": decimal_to_str(self.requested_amount_krw),
            "requestedVolume": decimal_to_str(self.requested_volume),
            "recommendedAmountKrw": decimal_to_str(self.recommended_amount_krw),
            "recommendedVolume": decimal_to_str(self.recommended_volume),
            "bestAsk": decimal_to_str(self.best_ask),
            "bestBid": decimal_to_str(self.best_bid),
            "midPrice": decimal_to_str(self.mid_price),
            "spreadPct": decimal_to_str(self.spread_pct),
            "bidAskDepthRatio": decimal_to_str(self.bid_ask_depth_ratio),
            "visibleAskKrw": decimal_to_str(self.visible_ask_krw),
            "visibleBidKrw": decimal_to_str(self.visible_bid_krw),
            "visibleAskSize": decimal_to_str(self.visible_ask_size),
            "visibleBidSize": decimal_to_str(self.visible_bid_size),
            "expectedAvgPrice": decimal_to_str(self.expected_avg_price),
            "recommendedAvgPrice": decimal_to_str(self.recommended_avg_price),
            "expectedSlippagePct": decimal_to_str(self.expected_slippage_pct),
            "recommendedSlippagePct": decimal_to_str(self.recommended_slippage_pct),
            "fillableAmountKrw": decimal_to_str(self.fillable_amount_krw),
            "fillableVolume": decimal_to_str(self.fillable_volume),
            "fillRatio": decimal_to_str(self.fill_ratio),
            "suggestedLimitPrice": decimal_to_str(self.suggested_limit_price),
            "action": self.action,
            "actionLabel": self.action_label,
            "repriceAction": self.reprice_action,
            "reason": self.reason,
            "levelsUsed": self.levels_used,
        }


@dataclass(frozen=True)
class OrderbookAdjustment:
    analysis: OrderbookAnalysis
    amount_krw: Decimal
    volume: Decimal | None
    current_price: Decimal
    intent: OrderIntent | None
    reason: str
    skipped: bool = False


def fetch_orderbook_payload(
    client: OrderbookClient,
    market: str,
    settings: TradingSettings,
) -> dict[str, Any]:
    rows = client.get_orderbook(market, count=settings.orderbook_depth_levels)
    if not rows:
        raise RuntimeError(f"{market} 호가 응답이 비어 있습니다")
    return rows[0]


def analyze_orderbook(
    settings: TradingSettings,
    payload: dict[str, Any],
    side: str,
    amount_krw: Decimal | None = None,
    volume: Decimal | None = None,
    reference_price: Decimal | None = None,
) -> OrderbookAnalysis:
    side = normalize_side(side)
    market = str(payload.get("market") or payload.get("code") or payload.get("cd") or "")
    levels = parse_orderbook_levels(payload)[: settings.orderbook_depth_levels]
    if not levels:
        return unavailable_analysis(market, side, amount_krw, volume, reference_price)

    asks = sorted((level for level in levels if level.ask_price > 0 and level.ask_size > 0), key=lambda item: item.ask_price)
    bids = sorted((level for level in levels if level.bid_price > 0 and level.bid_size > 0), key=lambda item: item.bid_price, reverse=True)
    if not asks or not bids:
        return unavailable_analysis(market, side, amount_krw, volume, reference_price)

    best_ask = asks[0].ask_price
    best_bid = bids[0].bid_price
    mid_price = (best_ask + best_bid) / Decimal("2") if best_ask > 0 and best_bid > 0 else Decimal("0")
    reference = reference_price if reference_price and reference_price > 0 else (best_ask if side == "bid" else best_bid)
    spread_pct = pct(best_ask - best_bid, mid_price)
    visible_ask_size = sum((level.ask_size for level in asks), Decimal("0"))
    visible_bid_size = sum((level.bid_size for level in bids), Decimal("0"))
    visible_ask_krw = sum((level.ask_price * level.ask_size for level in asks), Decimal("0"))
    visible_bid_krw = sum((level.bid_price * level.bid_size for level in bids), Decimal("0"))
    depth_ratio = visible_bid_krw / visible_ask_krw if visible_ask_krw > 0 else Decimal("0")

    if side == "bid":
        requested_amount = floor_krw(amount_krw or settings.min_order_krw)
        requested_sweep = sweep_buy(asks, requested_amount)
        requested_volume = requested_sweep.volume
        fillable_amount = min(requested_amount, visible_ask_krw)
        fillable_volume = requested_sweep.volume
        fill_ratio = requested_sweep.filled_ratio
        slippage = adverse_slippage(side, requested_sweep.avg_price, reference)
        liquidity_limit = floor_krw(visible_ask_krw * settings.orderbook_liquidity_use_pct)
        slippage_limit = floor_krw(buy_amount_within_slippage(asks, reference, requested_amount, settings.orderbook_max_slippage_pct))
        recommended_amount = min(requested_amount, liquidity_limit, slippage_limit)
        recommended_sweep = sweep_buy(asks, recommended_amount)
        recommended_volume = recommended_sweep.volume
        recommended_avg = recommended_sweep.avg_price
        recommended_slippage = adverse_slippage(side, recommended_avg, reference)
    else:
        requested_volume = volume if volume is not None else volume_from_amount(amount_krw, reference)
        requested_sweep = sweep_sell(bids, requested_volume)
        requested_amount = requested_sweep.amount_krw
        fillable_amount = requested_sweep.amount_krw
        fillable_volume = min(requested_volume, visible_bid_size)
        fill_ratio = requested_sweep.filled_ratio
        slippage = adverse_slippage(side, requested_sweep.avg_price, reference)
        liquidity_limit_volume = visible_bid_size * settings.orderbook_liquidity_use_pct
        slippage_limit_volume = sell_volume_within_slippage(bids, reference, requested_volume, settings.orderbook_max_slippage_pct)
        recommended_volume = min(requested_volume, liquidity_limit_volume, slippage_limit_volume)
        recommended_sweep = sweep_sell(bids, recommended_volume)
        recommended_amount = floor_krw(recommended_sweep.amount_krw)
        recommended_avg = recommended_sweep.avg_price
        recommended_slippage = adverse_slippage(side, recommended_avg, reference)

    action, reason_parts = classify_orderbook_action(
        settings=settings,
        side=side,
        requested_amount=requested_amount,
        requested_volume=requested_volume,
        recommended_amount=recommended_amount,
        recommended_volume=recommended_volume,
        spread_pct=spread_pct,
        slippage_pct=slippage,
        fill_ratio=fill_ratio,
        depth_ratio=depth_ratio,
        visible_ask_krw=visible_ask_krw,
        visible_bid_krw=visible_bid_krw,
    )
    suggested_limit_price = suggested_limit(side, best_ask, best_bid, settings)
    reprice_action = reprice_action_for(action, side)
    reason_parts.append(f"예상 슬리피지 {slippage.quantize(Decimal('0.0001'))}%")
    reason_parts.append(f"매수/매도 잔량비 {depth_ratio.quantize(Decimal('0.0001'))}배")

    return OrderbookAnalysis(
        market=market,
        side=side,
        requested_amount_krw=requested_amount,
        requested_volume=requested_volume,
        recommended_amount_krw=floor_krw(recommended_amount),
        recommended_volume=recommended_volume,
        best_ask=best_ask,
        best_bid=best_bid,
        mid_price=mid_price,
        spread_pct=spread_pct,
        bid_ask_depth_ratio=depth_ratio,
        visible_ask_krw=visible_ask_krw,
        visible_bid_krw=visible_bid_krw,
        visible_ask_size=visible_ask_size,
        visible_bid_size=visible_bid_size,
        expected_avg_price=requested_sweep.avg_price,
        recommended_avg_price=recommended_avg,
        expected_slippage_pct=slippage,
        recommended_slippage_pct=recommended_slippage,
        fillable_amount_krw=fillable_amount,
        fillable_volume=fillable_volume,
        fill_ratio=fill_ratio,
        suggested_limit_price=suggested_limit_price,
        action=action,
        action_label=action_label(action),
        reprice_action=reprice_action,
        reason=" · ".join(reason_parts),
        levels_used=requested_sweep.levels_used,
    )


def adjust_order_for_orderbook(
    settings: TradingSettings,
    client: OrderbookClient,
    market: str,
    side: str,
    amount_krw: Decimal,
    volume: Decimal | None,
    current_price: Decimal,
    intent: OrderIntent,
) -> OrderbookAdjustment | None:
    if not settings.orderbook_analysis_enabled:
        return None
    payload = fetch_orderbook_payload(client, market, settings)
    analysis = analyze_orderbook(
        settings=settings,
        payload=payload,
        side=side,
        amount_krw=amount_krw,
        volume=volume,
        reference_price=current_price,
    )
    if analysis.action == "skip":
        return OrderbookAdjustment(
            analysis=analysis,
            amount_krw=amount_krw,
            volume=volume,
            current_price=current_price,
            intent=None,
            reason=f"{intent.reason} · 호가 분석: {analysis.reason}",
            skipped=True,
        )

    if side == "bid":
        adjusted_amount = analysis.recommended_amount_krw if analysis.recommended_amount_krw >= settings.min_order_krw else amount_krw
        adjusted_intent = replace(intent, price=adjusted_amount)
        adjusted_price = analysis.recommended_avg_price if analysis.recommended_avg_price > 0 else current_price
        adjusted_volume = None
        adjusted_amount_krw = adjusted_amount
    else:
        adjusted_volume = analysis.recommended_volume if analysis.recommended_volume > 0 else volume
        adjusted_intent = replace(intent, volume=adjusted_volume)
        adjusted_price = analysis.recommended_avg_price if analysis.recommended_avg_price > 0 else current_price
        adjusted_amount_krw = adjusted_volume * adjusted_price if adjusted_volume is not None else amount_krw

    reason = f"{intent.reason} · 호가 {analysis.action_label}: {analysis.reason}"
    return OrderbookAdjustment(
        analysis=analysis,
        amount_krw=adjusted_amount_krw,
        volume=adjusted_volume,
        current_price=adjusted_price,
        intent=adjusted_intent,
        reason=reason,
    )


def parse_orderbook_levels(payload: dict[str, Any]) -> list[OrderbookLevel]:
    raw_units = payload.get("orderbook_units") or payload.get("obu") or []
    levels: list[OrderbookLevel] = []
    if not isinstance(raw_units, list):
        return levels
    for row in raw_units:
        if not isinstance(row, dict):
            continue
        levels.append(
            OrderbookLevel(
                ask_price=to_decimal(row.get("ask_price", row.get("ap", "0"))),
                bid_price=to_decimal(row.get("bid_price", row.get("bp", "0"))),
                ask_size=to_decimal(row.get("ask_size", row.get("as", "0"))),
                bid_size=to_decimal(row.get("bid_size", row.get("bs", "0"))),
            )
        )
    return levels


def sweep_buy(asks: list[OrderbookLevel], target_amount: Decimal) -> SweepResult:
    if target_amount <= 0:
        return SweepResult(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), 0)
    remaining = target_amount
    spent = Decimal("0")
    volume = Decimal("0")
    levels_used = 0
    for level in asks:
        available_krw = level.ask_price * level.ask_size
        if available_krw <= 0:
            continue
        take_krw = min(remaining, available_krw)
        spent += take_krw
        volume += take_krw / level.ask_price
        remaining -= take_krw
        levels_used += 1
        if remaining <= 0:
            break
    avg_price = spent / volume if volume > 0 else Decimal("0")
    return SweepResult(spent, volume, avg_price, filled_ratio(spent, target_amount), levels_used)


def sweep_sell(bids: list[OrderbookLevel], target_volume: Decimal) -> SweepResult:
    if target_volume <= 0:
        return SweepResult(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), 0)
    remaining = target_volume
    received = Decimal("0")
    volume = Decimal("0")
    levels_used = 0
    for level in bids:
        if level.bid_price <= 0 or level.bid_size <= 0:
            continue
        take_volume = min(remaining, level.bid_size)
        received += take_volume * level.bid_price
        volume += take_volume
        remaining -= take_volume
        levels_used += 1
        if remaining <= 0:
            break
    avg_price = received / volume if volume > 0 else Decimal("0")
    return SweepResult(received, volume, avg_price, filled_ratio(volume, target_volume), levels_used)


def buy_amount_within_slippage(
    asks: list[OrderbookLevel],
    reference_price: Decimal,
    max_amount: Decimal,
    max_slippage_pct: Decimal,
) -> Decimal:
    allowed = Decimal("0")
    spent = Decimal("0")
    volume = Decimal("0")
    remaining = max_amount
    for level in asks:
        available_krw = level.ask_price * level.ask_size
        if available_krw <= 0:
            continue
        take_krw = min(remaining, available_krw)
        next_spent = spent + take_krw
        next_volume = volume + take_krw / level.ask_price
        next_avg = next_spent / next_volume if next_volume > 0 else Decimal("0")
        if adverse_slippage("bid", next_avg, reference_price) <= max_slippage_pct:
            spent = next_spent
            volume = next_volume
            allowed = spent
            remaining -= take_krw
            if remaining <= 0:
                break
        else:
            break
    return allowed


def sell_volume_within_slippage(
    bids: list[OrderbookLevel],
    reference_price: Decimal,
    max_volume: Decimal,
    max_slippage_pct: Decimal,
) -> Decimal:
    allowed = Decimal("0")
    received = Decimal("0")
    volume = Decimal("0")
    remaining = max_volume
    for level in bids:
        if level.bid_price <= 0 or level.bid_size <= 0:
            continue
        take_volume = min(remaining, level.bid_size)
        next_received = received + take_volume * level.bid_price
        next_volume = volume + take_volume
        next_avg = next_received / next_volume if next_volume > 0 else Decimal("0")
        if adverse_slippage("ask", next_avg, reference_price) <= max_slippage_pct:
            received = next_received
            volume = next_volume
            allowed = volume
            remaining -= take_volume
            if remaining <= 0:
                break
        else:
            break
    return allowed


def classify_orderbook_action(
    settings: TradingSettings,
    side: str,
    requested_amount: Decimal,
    requested_volume: Decimal,
    recommended_amount: Decimal,
    recommended_volume: Decimal,
    spread_pct: Decimal,
    slippage_pct: Decimal,
    fill_ratio: Decimal,
    depth_ratio: Decimal,
    visible_ask_krw: Decimal,
    visible_bid_krw: Decimal,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    spread_hard_exceeded = settings.orderbook_hard_max_spread_pct > 0 and spread_pct > settings.orderbook_hard_max_spread_pct
    if spread_hard_exceeded:
        reasons.append("spread hard limit exceeded")
    min_visible_ask_krw = effective_visible_liquidity_floor(
        settings.orderbook_min_visible_ask_krw,
        requested_amount,
        settings.min_order_krw,
    )
    min_visible_bid_krw = effective_visible_liquidity_floor(
        settings.orderbook_min_visible_bid_krw,
        requested_amount,
        settings.min_order_krw,
    )
    visible_ask_too_thin = side == "bid" and visible_ask_krw < min_visible_ask_krw
    visible_bid_too_thin = side == "ask" and visible_bid_krw < min_visible_bid_krw
    if visible_ask_too_thin:
        reasons.append("visible ask liquidity too thin")
    if visible_bid_too_thin:
        reasons.append("visible bid liquidity too thin")
    spread_can_be_resized = spread_hard_exceeded and recoverable_wide_spread(
        settings=settings,
        side=side,
        requested_amount=requested_amount,
        requested_volume=requested_volume,
        recommended_amount=recommended_amount,
        recommended_volume=recommended_volume,
        spread_pct=spread_pct,
        slippage_pct=slippage_pct,
        fill_ratio=fill_ratio,
    )
    if visible_ask_too_thin or visible_bid_too_thin or (spread_hard_exceeded and not spread_can_be_resized):
        recommended_amount = Decimal("0")
        recommended_volume = Decimal("0")
    if fill_ratio < settings.orderbook_min_fill_ratio:
        reasons.append("누적 호가 내 체결 가능 물량 부족")
    if slippage_pct > settings.orderbook_max_slippage_pct:
        reasons.append("허용 슬리피지 초과")
    if spread_pct > settings.orderbook_reprice_spread_pct:
        reasons.append("스프레드 확대")
    if depth_ratio < settings.orderbook_min_depth_ratio:
        reasons.append("매수 잔량이 매도 잔량보다 약함")

    if side == "bid":
        if recommended_amount < settings.min_order_krw:
            return "skip", reasons or ["권장 매수 금액이 최소 주문금액보다 작음"]
        if recommended_amount < requested_amount:
            return "reduce", reasons or ["호가 잔량 기준 매수 금액 축소"]
    else:
        if recommended_volume <= 0 or recommended_amount < settings.min_order_krw:
            return "skip", reasons or ["권장 매도 금액이 최소 주문금액보다 작음"]
        if recommended_volume < requested_volume:
            return "reduce", reasons or ["호가 잔량 기준 매도 수량 축소"]

    if spread_pct > settings.orderbook_reprice_spread_pct or depth_ratio < settings.orderbook_min_depth_ratio:
        return "reprice", reasons or ["호가 위치 조정 권장"]
    return "use", reasons or ["누적 호가 통과"]


def effective_visible_liquidity_floor(configured_floor: Decimal, requested_amount: Decimal, min_order_krw: Decimal) -> Decimal:
    if configured_floor <= 0:
        return Decimal("0")
    scaled_floor = max(min_order_krw * Decimal("3"), requested_amount * Decimal("2"))
    return min(configured_floor, scaled_floor)


def recoverable_wide_spread(
    settings: TradingSettings,
    side: str,
    requested_amount: Decimal,
    requested_volume: Decimal,
    recommended_amount: Decimal,
    recommended_volume: Decimal,
    spread_pct: Decimal,
    slippage_pct: Decimal,
    fill_ratio: Decimal,
) -> bool:
    if fill_ratio < settings.orderbook_min_fill_ratio or slippage_pct > settings.orderbook_max_slippage_pct:
        return False
    if spread_pct > settings.orderbook_hard_max_spread_pct * Decimal("2.5"):
        return False
    if side == "bid":
        return requested_amount >= settings.min_order_krw and recommended_amount >= settings.min_order_krw
    requested_sell_amount = requested_amount if requested_amount > 0 else recommended_amount
    return (
        requested_sell_amount >= settings.min_order_krw
        and recommended_amount >= settings.min_order_krw
        and recommended_volume > 0
        and recommended_volume <= requested_volume
    )


def unavailable_analysis(
    market: str,
    side: str,
    amount_krw: Decimal | None,
    volume: Decimal | None,
    reference_price: Decimal | None,
) -> OrderbookAnalysis:
    return OrderbookAnalysis(
        market=market,
        side=side,
        requested_amount_krw=amount_krw or Decimal("0"),
        requested_volume=volume or Decimal("0"),
        recommended_amount_krw=Decimal("0"),
        recommended_volume=Decimal("0"),
        best_ask=Decimal("0"),
        best_bid=Decimal("0"),
        mid_price=reference_price or Decimal("0"),
        spread_pct=Decimal("0"),
        bid_ask_depth_ratio=Decimal("0"),
        visible_ask_krw=Decimal("0"),
        visible_bid_krw=Decimal("0"),
        visible_ask_size=Decimal("0"),
        visible_bid_size=Decimal("0"),
        expected_avg_price=reference_price or Decimal("0"),
        recommended_avg_price=reference_price or Decimal("0"),
        expected_slippage_pct=Decimal("0"),
        recommended_slippage_pct=Decimal("0"),
        fillable_amount_krw=Decimal("0"),
        fillable_volume=Decimal("0"),
        fill_ratio=Decimal("0"),
        suggested_limit_price=Decimal("0"),
        action="unavailable",
        action_label=action_label("unavailable"),
        reprice_action="wait",
        reason="호가 데이터가 부족합니다",
        levels_used=0,
    )


def normalize_side(side: str) -> str:
    cleaned = side.strip().lower()
    if cleaned in {"bid", "buy", "매수"}:
        return "bid"
    if cleaned in {"ask", "sell", "매도"}:
        return "ask"
    raise ValueError(f"지원하지 않는 호가 분석 방향입니다: {side}")


def action_label(action: str) -> str:
    return {
        "use": "통과",
        "reprice": "호가 조정",
        "reduce": "수량 축소",
        "skip": "주문 제외",
        "unavailable": "호가 없음",
    }.get(action, action)


def reprice_action_for(action: str, side: str) -> str:
    if action == "skip":
        return "cancel"
    if action == "reduce":
        return "resize_then_join_best"
    if action == "reprice":
        return "join_best_ask" if side == "bid" else "join_best_bid"
    return "keep_or_join_best"


def suggested_limit(side: str, best_ask: Decimal, best_bid: Decimal, settings: TradingSettings) -> Decimal:
    step = settings.orderbook_price_step_bps / Decimal("10000")
    if side == "bid":
        price = best_ask * (Decimal("1") + step)
    else:
        price = best_bid * (Decimal("1") - step)
    return price.quantize(PRICE_QUANT, rounding=ROUND_DOWN)


def adverse_slippage(side: str, avg_price: Decimal, reference_price: Decimal) -> Decimal:
    if avg_price <= 0 or reference_price <= 0:
        return Decimal("0")
    if side == "bid":
        return max(Decimal("0"), (avg_price - reference_price) / reference_price * Decimal("100"))
    return max(Decimal("0"), (reference_price - avg_price) / reference_price * Decimal("100"))


def pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return numerator / denominator * Decimal("100")


def filled_ratio(filled: Decimal, requested: Decimal) -> Decimal:
    if requested <= 0:
        return Decimal("0")
    return min(Decimal("1"), filled / requested)


def volume_from_amount(amount_krw: Decimal | None, reference_price: Decimal) -> Decimal:
    if amount_krw is None or amount_krw <= 0 or reference_price <= 0:
        return Decimal("0")
    return amount_krw / reference_price


def floor_krw(value: Decimal) -> Decimal:
    if value <= 0:
        return Decimal("0")
    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)


def min_nonzero(*values: Decimal) -> Decimal:
    positives = [value for value in values if value > 0]
    return min(positives) if positives else Decimal("0")


def to_decimal(value: Any) -> Decimal:
    return Decimal(str(value or "0"))
