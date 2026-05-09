from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

from .config import TradingSettings
from .models import OrderIntent, RiskDecision, Signal
from .state import PaperState, PortfolioState, reset_daily_counters_if_needed


def floor_krw(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)


@dataclass(frozen=True)
class RiskManager:
    settings: TradingSettings

    def evaluate(self, signal: Signal, state: PaperState, current_price: Decimal) -> RiskDecision:
        if signal.action == "hold":
            return RiskDecision(False, signal.reason)
        if current_price <= 0:
            return RiskDecision(False, "현재가는 0보다 커야 합니다")
        if signal.market != self.settings.market:
            return RiskDecision(False, f"신호 마켓 {signal.market}은 허용된 마켓이 아닙니다")

        if signal.action == "buy":
            return self._buy_decision(signal, state, current_price)
        if signal.action == "sell":
            return self._sell_decision(signal, state)
        return RiskDecision(False, f"지원하지 않는 신호입니다: {signal.action}")

    def _buy_decision(
        self,
        signal: Signal,
        state: PaperState,
        current_price: Decimal,
    ) -> RiskDecision:
        current_position_krw = state.position_value(current_price)
        remaining_position_krw = self.settings.max_position_krw - current_position_krw
        budget = min(self.settings.max_order_krw, remaining_position_krw, state.cash_krw)
        budget = floor_krw(budget)

        if budget < self.settings.min_order_krw:
            return RiskDecision(
                False,
                f"매수 거절: 주문 가능 금액 {budget}원이 최소 주문 금액 {self.settings.min_order_krw}원보다 작습니다",
            )

        return RiskDecision(
            True,
            "매수 승인",
            OrderIntent(
                market=signal.market,
                side="bid",
                ord_type="price",
                price=budget,
                reason=signal.reason,
            ),
        )

    def _sell_decision(self, signal: Signal, state: PaperState) -> RiskDecision:
        if state.position_volume <= 0:
            return RiskDecision(False, "매도 거절: 페이퍼 보유 수량이 없습니다")

        return RiskDecision(
            True,
            "매도 승인",
            OrderIntent(
                market=signal.market,
                side="ask",
                ord_type="market",
                volume=state.position_volume,
                reason=signal.reason,
            ),
        )


@dataclass(frozen=True)
class PortfolioRiskManager:
    settings: TradingSettings

    def protective_signal(
        self,
        signal: Signal,
        state: PortfolioState,
        current_price: Decimal,
    ) -> Signal:
        if current_price <= 0:
            return signal

        position = state.position(signal.market)
        if position.volume <= 0 or position.avg_entry_price <= 0:
            return signal

        pnl_pct = (current_price - position.avg_entry_price) / position.avg_entry_price * Decimal("100")
        if pnl_pct <= -self.settings.stop_loss_pct:
            return Signal(
                "sell",
                signal.market,
                current_price,
                f"손절 기준 도달: 진입가 대비 {pnl_pct:.2f}% (기준 -{self.settings.stop_loss_pct}%)",
            )
        if pnl_pct >= self.settings.take_profit_pct:
            return Signal(
                "sell",
                signal.market,
                current_price,
                f"익절 기준 도달: 진입가 대비 +{pnl_pct:.2f}% (기준 +{self.settings.take_profit_pct}%)",
            )
        return signal

    def evaluate(
        self,
        signal: Signal,
        state: PortfolioState,
        current_price: Decimal,
    ) -> RiskDecision:
        reset_daily_counters_if_needed(state)
        if signal.action == "hold":
            return RiskDecision(False, signal.reason)
        if current_price <= 0:
            return RiskDecision(False, "현재가는 0보다 커야 합니다")
        if signal.market not in self.settings.markets:
            return RiskDecision(False, f"신호 마켓 {signal.market}은 감시 목록에 없습니다")

        if signal.action == "buy":
            return self._buy_decision(signal, state, current_price)
        if signal.action == "sell":
            return self._sell_decision(signal, state)
        return RiskDecision(False, f"지원하지 않는 신호입니다: {signal.action}")

    def _buy_decision(
        self,
        signal: Signal,
        state: PortfolioState,
        current_price: Decimal,
    ) -> RiskDecision:
        daily_loss_floor = -self.settings.daily_loss_limit_krw
        if state.daily_realized_pnl_krw <= daily_loss_floor:
            return RiskDecision(
                False,
                f"매수 거절: 일일 실현손실 {state.daily_realized_pnl_krw}원이 한도 -{self.settings.daily_loss_limit_krw}원에 도달했습니다",
            )
        if state.daily_order_count >= self.settings.max_daily_orders:
            return RiskDecision(
                False,
                f"매수 거절: 일일 주문 수 {state.daily_order_count}회가 한도 {self.settings.max_daily_orders}회에 도달했습니다",
            )
        cooldown_left = remaining_cooldown_seconds(state, signal.market, self.settings.cooldown_seconds)
        if cooldown_left > 0:
            return RiskDecision(False, f"매수 거절: {signal.market} 재진입 대기 {cooldown_left}초 남음")

        position = state.position(signal.market)
        open_positions = sum(1 for item in state.positions.values() if item.volume > 0)
        if position.volume <= 0 and open_positions >= self.settings.max_open_positions:
            return RiskDecision(
                False,
                f"매수 거절: 최대 보유 코인 수 {self.settings.max_open_positions}개에 도달했습니다",
            )

        current_position_krw = state.position_value(signal.market, current_price)
        remaining_position_krw = self.settings.max_position_krw - current_position_krw
        budget = min(self.settings.max_order_krw, remaining_position_krw, state.cash_krw)
        budget = floor_krw(budget)

        if budget < self.settings.min_order_krw:
            return RiskDecision(
                False,
                f"매수 거절: {signal.market} 주문 가능 금액 {budget}원이 최소 주문 금액 {self.settings.min_order_krw}원보다 작습니다",
            )

        return RiskDecision(
            True,
            "매수 승인",
            OrderIntent(
                market=signal.market,
                side="bid",
                ord_type="price",
                price=budget,
                reason=signal.reason,
            ),
        )

    def _sell_decision(self, signal: Signal, state: PortfolioState) -> RiskDecision:
        position = state.position(signal.market)
        if position.volume <= 0:
            return RiskDecision(False, f"매도 거절: {signal.market} 페이퍼 보유 수량이 없습니다")

        return RiskDecision(
            True,
            "매도 승인",
            OrderIntent(
                market=signal.market,
                side="ask",
                ord_type="market",
                volume=position.volume,
                reason=signal.reason,
            ),
        )


def remaining_cooldown_seconds(state: PortfolioState, market: str, cooldown_seconds: int) -> int:
    if cooldown_seconds <= 0 or not state.last_order_by_market:
        return 0
    last_order_at = state.last_order_by_market.get(market)
    if not last_order_at:
        return 0
    try:
        parsed = datetime.fromisoformat(last_order_at)
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return max(0, int(cooldown_seconds - elapsed))
