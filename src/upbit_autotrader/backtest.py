from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .broker import PaperBroker
from .config import TradingSettings
from .models import Candle, decimal_to_str
from .risk import RiskManager
from .state import PaperState
from .strategy import make_strategy


@dataclass(frozen=True)
class BacktestPoint:
    time: str
    equity_krw: Decimal
    price: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "time": self.time,
            "equityKrw": decimal_to_str(self.equity_krw),
            "price": decimal_to_str(self.price),
        }


@dataclass(frozen=True)
class BacktestReport:
    market: str
    start_equity_krw: Decimal
    final_equity_krw: Decimal
    realized_pnl_krw: Decimal
    fees_paid_krw: Decimal
    order_count: int
    last_price: Decimal
    max_drawdown_pct: Decimal
    best_equity_krw: Decimal
    worst_equity_krw: Decimal
    equity_curve: tuple[BacktestPoint, ...]

    @property
    def total_return_pct(self) -> Decimal:
        if self.start_equity_krw == 0:
            return Decimal("0")
        return (self.final_equity_krw - self.start_equity_krw) / self.start_equity_krw * Decimal("100")

    def to_dict(self) -> dict[str, object]:
        return {
            "market": self.market,
            "startEquityKrw": decimal_to_str(self.start_equity_krw),
            "finalEquityKrw": decimal_to_str(self.final_equity_krw),
            "realizedPnlKrw": decimal_to_str(self.realized_pnl_krw),
            "feesPaidKrw": decimal_to_str(self.fees_paid_krw),
            "orderCount": self.order_count,
            "lastPrice": decimal_to_str(self.last_price),
            "totalReturnPct": decimal_to_str(self.total_return_pct),
            "maxDrawdownPct": decimal_to_str(self.max_drawdown_pct),
            "bestEquityKrw": decimal_to_str(self.best_equity_krw),
            "worstEquityKrw": decimal_to_str(self.worst_equity_krw),
            "equityCurve": [point.to_dict() for point in self.equity_curve],
        }


def run_backtest(candles: list[Candle], settings: TradingSettings) -> BacktestReport:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    state = PaperState(cash_krw=settings.paper_cash_krw)
    strategy = make_strategy(settings)
    risk = RiskManager(settings)
    broker = PaperBroker(state, settings.fee_rate)
    equity_curve: list[BacktestPoint] = []
    peak_equity = settings.paper_cash_krw
    max_drawdown_pct = Decimal("0")

    for index in range(settings.long_window + 1, len(ordered)):
        window = ordered[: index + 1]
        current_price = window[-1].trade_price
        signal = strategy.evaluate(window)
        decision = risk.evaluate(signal, state, current_price)
        if decision.approved and decision.intent is not None:
            broker.execute(decision.intent, current_price)
        equity = state.equity(current_price)
        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            drawdown_pct = (equity - peak_equity) / peak_equity * Decimal("100")
            max_drawdown_pct = min(max_drawdown_pct, drawdown_pct)
        if index == settings.long_window + 1 or index == len(ordered) - 1 or index % 5 == 0:
            equity_curve.append(
                BacktestPoint(
                    time=window[-1].candle_date_time_kst,
                    equity_krw=equity,
                    price=current_price,
                )
            )

    last_price = ordered[-1].trade_price if ordered else Decimal("0")
    final_equity = state.equity(last_price)
    equities = [point.equity_krw for point in equity_curve] or [final_equity]
    return BacktestReport(
        market=settings.market,
        start_equity_krw=settings.paper_cash_krw,
        final_equity_krw=final_equity,
        realized_pnl_krw=state.realized_pnl_krw,
        fees_paid_krw=state.fees_paid_krw,
        order_count=state.order_count,
        last_price=last_price,
        max_drawdown_pct=max_drawdown_pct,
        best_equity_krw=max(equities),
        worst_equity_krw=min(equities),
        equity_curve=tuple(equity_curve[-80:]),
    )
