from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from .config import TradingSettings
from .live import is_live_trading_armed
from .models import OrderIntent, OrderResult, decimal_to_str
from .state import PaperState, PortfolioState, reset_daily_counters_if_needed
from .upbit_client import UpbitClient


class PaperBroker:
    def __init__(self, state: PaperState, fee_rate: Decimal) -> None:
        self.state = state
        self.fee_rate = fee_rate

    def execute(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        if current_price <= 0:
            return OrderResult(False, "paper", "현재가는 0보다 커야 합니다", {})
        if intent.side == "bid" and intent.ord_type == "price":
            return self._market_buy(intent, current_price)
        if intent.side == "ask" and intent.ord_type == "market":
            return self._market_sell(intent, current_price)
        return OrderResult(False, "paper", "페이퍼 브로커는 시장가 매수/매도만 지원합니다", {})

    def _market_buy(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        if intent.price is None or intent.price <= 0:
            return OrderResult(False, "paper", "시장가 매수에는 KRW 주문 총액이 필요합니다", {})
        if intent.price > self.state.cash_krw:
            return OrderResult(False, "paper", "페이퍼 현금이 부족합니다", {})

        gross_krw = intent.price
        fee_krw = gross_krw * self.fee_rate
        net_krw = gross_krw - fee_krw
        bought_volume = net_krw / current_price

        old_cost = self.state.position_volume * self.state.avg_entry_price
        new_volume = self.state.position_volume + bought_volume
        self.state.avg_entry_price = (old_cost + net_krw) / new_volume
        self.state.position_volume = new_volume
        self.state.cash_krw -= gross_krw
        self._record_order(fee_krw)

        return OrderResult(
            True,
            "paper",
            "페이퍼 시장가 매수 체결",
            {
                "market": intent.market,
                "side": intent.side,
                "spent_krw": decimal_to_str(gross_krw),
                "fee_krw": decimal_to_str(fee_krw),
                "volume": decimal_to_str(bought_volume),
                "fill_price": decimal_to_str(current_price),
            },
        )

    def _market_sell(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        if intent.volume is None or intent.volume <= 0:
            return OrderResult(False, "paper", "시장가 매도에는 수량이 필요합니다", {})
        if intent.volume > self.state.position_volume:
            return OrderResult(False, "paper", "페이퍼 보유 수량이 부족합니다", {})

        volume = intent.volume
        gross_krw = volume * current_price
        fee_krw = gross_krw * self.fee_rate
        proceeds_krw = gross_krw - fee_krw
        cost_basis = volume * self.state.avg_entry_price
        realized_pnl = proceeds_krw - cost_basis

        self.state.cash_krw += proceeds_krw
        self.state.position_volume -= volume
        if self.state.position_volume == 0:
            self.state.avg_entry_price = Decimal("0")
        self.state.realized_pnl_krw += realized_pnl
        self._record_order(fee_krw)

        return OrderResult(
            True,
            "paper",
            "페이퍼 시장가 매도 체결",
            {
                "market": intent.market,
                "side": intent.side,
                "received_krw": decimal_to_str(proceeds_krw),
                "fee_krw": decimal_to_str(fee_krw),
                "volume": decimal_to_str(volume),
                "fill_price": decimal_to_str(current_price),
                "realized_pnl_krw": decimal_to_str(realized_pnl),
            },
        )

    def _record_order(self, fee_krw: Decimal) -> None:
        self.state.fees_paid_krw += fee_krw
        self.state.order_count += 1
        self.state.last_order_at = datetime.now(timezone.utc).isoformat()


class UpbitLiveBroker:
    def __init__(self, client: UpbitClient, settings: TradingSettings) -> None:
        self.client = client
        self.settings = settings

    def execute(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        if not is_live_trading_armed(self.settings):
            return OrderResult(False, "live", "실거래 이중 잠금이 해제되지 않았습니다", {})

        live_intent = OrderIntent(
            market=intent.market,
            side=intent.side,
            ord_type=intent.ord_type,
            price=intent.price,
            volume=intent.volume,
            reason=intent.reason,
            identifier=intent.identifier or f"codex-{uuid4().hex[:24]}",
            time_in_force=intent.time_in_force,
            smp_type=intent.smp_type,
        )
        body = live_intent.to_upbit_body()
        response = self.client.create_order(body)
        return OrderResult(True, "live", "실거래 주문 제출 완료", response)


class PortfolioPaperBroker:
    def __init__(self, state: PortfolioState, fee_rate: Decimal) -> None:
        self.state = state
        self.fee_rate = fee_rate

    def execute(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        if current_price <= 0:
            return OrderResult(False, "paper", "현재가는 0보다 커야 합니다", {})
        if intent.side == "bid" and intent.ord_type == "price":
            return self._market_buy(intent, current_price)
        if intent.side == "ask" and intent.ord_type == "market":
            return self._market_sell(intent, current_price)
        return OrderResult(False, "paper", "포트폴리오 페이퍼 브로커는 시장가 매수/매도만 지원합니다", {})

    def _market_buy(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        reset_daily_counters_if_needed(self.state)
        if intent.price is None or intent.price <= 0:
            return OrderResult(False, "paper", "시장가 매수에는 KRW 주문 총액이 필요합니다", {})
        if intent.price > self.state.cash_krw:
            return OrderResult(False, "paper", "페이퍼 현금이 부족합니다", {})

        position = self.state.position(intent.market)
        gross_krw = intent.price
        fee_krw = gross_krw * self.fee_rate
        net_krw = gross_krw - fee_krw
        bought_volume = net_krw / current_price

        old_cost = position.volume * position.avg_entry_price
        new_volume = position.volume + bought_volume
        position.avg_entry_price = (old_cost + net_krw) / new_volume
        position.volume = new_volume
        self.state.cash_krw -= gross_krw
        self._record_order(intent.market, fee_krw, intent.reason)

        return OrderResult(
            True,
            "paper",
            f"{intent.market} 페이퍼 시장가 매수 체결",
            {
                "market": intent.market,
                "side": intent.side,
                "spent_krw": decimal_to_str(gross_krw),
                "fee_krw": decimal_to_str(fee_krw),
                "volume": decimal_to_str(bought_volume),
                "fill_price": decimal_to_str(current_price),
            },
        )

    def _market_sell(self, intent: OrderIntent, current_price: Decimal) -> OrderResult:
        reset_daily_counters_if_needed(self.state)
        if intent.volume is None or intent.volume <= 0:
            return OrderResult(False, "paper", "시장가 매도에는 수량이 필요합니다", {})

        position = self.state.position(intent.market)
        if intent.volume > position.volume:
            return OrderResult(False, "paper", "페이퍼 보유 수량이 부족합니다", {})

        volume = intent.volume
        gross_krw = volume * current_price
        fee_krw = gross_krw * self.fee_rate
        proceeds_krw = gross_krw - fee_krw
        cost_basis = volume * position.avg_entry_price
        realized_pnl = proceeds_krw - cost_basis

        self.state.cash_krw += proceeds_krw
        position.volume -= volume
        if position.volume == 0:
            position.avg_entry_price = Decimal("0")
        self.state.realized_pnl_krw += realized_pnl
        self.state.daily_realized_pnl_krw += realized_pnl
        if self.state.realized_pnl_by_market is None:
            self.state.realized_pnl_by_market = {}
        self.state.realized_pnl_by_market[intent.market] = (
            self.state.realized_pnl_by_market.get(intent.market, Decimal("0")) + realized_pnl
        )
        self._record_order(intent.market, fee_krw, intent.reason)

        return OrderResult(
            True,
            "paper",
            f"{intent.market} 페이퍼 시장가 매도 체결",
            {
                "market": intent.market,
                "side": intent.side,
                "received_krw": decimal_to_str(proceeds_krw),
                "fee_krw": decimal_to_str(fee_krw),
                "volume": decimal_to_str(volume),
                "fill_price": decimal_to_str(current_price),
                "realized_pnl_krw": decimal_to_str(realized_pnl),
            },
        )

    def _record_order(self, market: str, fee_krw: Decimal, reason: str | None = None) -> None:
        reset_daily_counters_if_needed(self.state)
        now = datetime.now(timezone.utc).isoformat()
        self.state.fees_paid_krw += fee_krw
        self.state.order_count += 1
        self.state.daily_order_count += 1
        self.state.last_order_at = now
        if self.state.last_order_by_market is None:
            self.state.last_order_by_market = {}
        self.state.last_order_by_market[market] = now
        if self.state.last_order_reason_by_market is None:
            self.state.last_order_reason_by_market = {}
        if reason:
            self.state.last_order_reason_by_market[market] = reason
