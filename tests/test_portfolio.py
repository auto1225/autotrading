from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.broker import PortfolioPaperBroker
from upbit_autotrader.config import TradingSettings, parse_markets
from upbit_autotrader.models import OrderIntent, Signal
from upbit_autotrader.risk import PortfolioRiskManager
from upbit_autotrader.state import PortfolioPosition, PortfolioState


class PortfolioTests(unittest.TestCase):
    def test_parse_markets_deduplicates_and_normalizes(self) -> None:
        self.assertEqual(parse_markets("krw-btc, KRW-ETH,krw-btc"), ("KRW-BTC", "KRW-ETH"))

    def test_portfolio_risk_allows_configured_market_buy(self) -> None:
        settings = TradingSettings(
            markets=("KRW-BTC", "KRW-ETH"),
            min_order_krw=Decimal("5000"),
            max_order_krw=Decimal("10000"),
            max_position_krw=Decimal("20000"),
        )
        state = PortfolioState(cash_krw=Decimal("100000"), positions={})
        signal = Signal("buy", "KRW-ETH", Decimal("1000"), "test")
        decision = PortfolioRiskManager(settings).evaluate(signal, state, Decimal("1000"))

        self.assertTrue(decision.approved)
        self.assertEqual(decision.intent.market, "KRW-ETH")
        self.assertEqual(decision.intent.price, Decimal("10000"))

    def test_portfolio_paper_broker_tracks_positions_by_market(self) -> None:
        state = PortfolioState(cash_krw=Decimal("100000"), positions={})
        broker = PortfolioPaperBroker(state, Decimal("0.001"))
        intent = OrderIntent("KRW-ETH", "bid", "price", "test", price=Decimal("10000"))
        result = broker.execute(intent, Decimal("1000"))

        self.assertTrue(result.ok)
        self.assertEqual(state.cash_krw, Decimal("90000"))
        self.assertEqual(state.position("KRW-ETH").volume, Decimal("9.99"))
        self.assertEqual(state.position("KRW-BTC").volume, Decimal("0"))
        self.assertEqual(state.order_count, 1)
        self.assertEqual(state.daily_order_count, 1)
        self.assertIn("KRW-ETH", state.last_order_by_market)
        self.assertEqual(state.last_order_reason_by_market["KRW-ETH"], "test")

    def test_daily_loss_limit_blocks_new_buy(self) -> None:
        settings = TradingSettings(
            markets=("KRW-BTC", "KRW-ETH"),
            daily_loss_limit_krw=Decimal("50000"),
        )
        state = PortfolioState(
            cash_krw=Decimal("100000"),
            positions={},
            daily_realized_pnl_krw=Decimal("-50000"),
        )
        signal = Signal("buy", "KRW-ETH", Decimal("1000"), "test")
        decision = PortfolioRiskManager(settings).evaluate(signal, state, Decimal("1000"))

        self.assertFalse(decision.approved)
        self.assertIn("일일 실현손실", decision.reason)

    def test_cooldown_blocks_same_market_reentry(self) -> None:
        settings = TradingSettings(markets=("KRW-BTC", "KRW-ETH"), cooldown_seconds=300)
        state = PortfolioState(
            cash_krw=Decimal("100000"),
            positions={},
            last_order_by_market={"KRW-ETH": datetime.now(timezone.utc).isoformat()},
        )
        signal = Signal("buy", "KRW-ETH", Decimal("1000"), "test")
        decision = PortfolioRiskManager(settings).evaluate(signal, state, Decimal("1000"))

        self.assertFalse(decision.approved)
        self.assertIn("재진입 대기", decision.reason)

    def test_max_open_positions_blocks_new_market_buy(self) -> None:
        settings = TradingSettings(
            markets=("KRW-BTC", "KRW-ETH", "KRW-XRP"),
            max_open_positions=2,
        )
        state = PortfolioState(
            cash_krw=Decimal("100000"),
            positions={
                "KRW-BTC": PortfolioPosition(volume=Decimal("1"), avg_entry_price=Decimal("1000")),
                "KRW-ETH": PortfolioPosition(volume=Decimal("1"), avg_entry_price=Decimal("1000")),
            },
        )
        signal = Signal("buy", "KRW-XRP", Decimal("1000"), "test")
        decision = PortfolioRiskManager(settings).evaluate(signal, state, Decimal("1000"))

        self.assertFalse(decision.approved)
        self.assertIn("최대 보유 코인 수", decision.reason)

    def test_protective_signal_converts_loss_to_sell(self) -> None:
        settings = TradingSettings(markets=("KRW-BTC",), stop_loss_pct=Decimal("3"))
        state = PortfolioState(
            cash_krw=Decimal("100000"),
            positions={"KRW-BTC": PortfolioPosition(volume=Decimal("1"), avg_entry_price=Decimal("1000"))},
        )
        signal = Signal("hold", "KRW-BTC", Decimal("960"), "test")
        protected = PortfolioRiskManager(settings).protective_signal(signal, state, Decimal("960"))

        self.assertEqual(protected.action, "sell")
        self.assertIn("손절", protected.reason)


if __name__ == "__main__":
    unittest.main()
