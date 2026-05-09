from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.broker import PaperBroker, UpbitLiveBroker
from upbit_autotrader.config import TradingSettings
from upbit_autotrader.live import LIVE_CONFIRMATION_CODE, LIVE_CONFIRMATION_PHRASE
from upbit_autotrader.models import OrderIntent
from upbit_autotrader.state import PaperState


class FakeLiveClient:
    def __init__(self) -> None:
        self.orders: list[dict[str, str]] = []

    def create_order(self, order_body: dict[str, str]) -> dict[str, str]:
        self.orders.append(order_body)
        return {"uuid": "fake-order", **order_body}


class PaperBrokerTests(unittest.TestCase):
    def test_market_buy_updates_cash_and_position(self) -> None:
        state = PaperState(cash_krw=Decimal("100000"))
        broker = PaperBroker(state, Decimal("0.001"))
        intent = OrderIntent("KRW-BTC", "bid", "price", "test", price=Decimal("10000"))
        result = broker.execute(intent, Decimal("1000"))

        self.assertTrue(result.ok)
        self.assertEqual(state.cash_krw, Decimal("90000"))
        self.assertEqual(state.position_volume, Decimal("9.99"))
        self.assertEqual(state.avg_entry_price, Decimal("1000"))
        self.assertEqual(state.order_count, 1)

    def test_market_sell_updates_cash_and_realized_pnl(self) -> None:
        state = PaperState(
            cash_krw=Decimal("90000"),
            position_volume=Decimal("10"),
            avg_entry_price=Decimal("1000"),
        )
        broker = PaperBroker(state, Decimal("0.001"))
        intent = OrderIntent("KRW-BTC", "ask", "market", "test", volume=Decimal("10"))
        result = broker.execute(intent, Decimal("1100"))

        self.assertTrue(result.ok)
        self.assertEqual(state.position_volume, Decimal("0"))
        self.assertEqual(state.cash_krw, Decimal("100989.000"))
        self.assertEqual(state.realized_pnl_krw, Decimal("989.000"))
        self.assertEqual(state.order_count, 1)

    def test_live_broker_requires_confirmation_phrase(self) -> None:
        client = FakeLiveClient()
        settings = TradingSettings(live_trading_enabled=True)
        broker = UpbitLiveBroker(client, settings)  # type: ignore[arg-type]
        intent = OrderIntent("KRW-BTC", "bid", "price", "test", price=Decimal("5000"))

        result = broker.execute(intent, Decimal("1000"))

        self.assertFalse(result.ok)
        self.assertEqual(client.orders, [])

    def test_live_broker_submits_when_fully_armed(self) -> None:
        client = FakeLiveClient()
        settings = TradingSettings(
            live_trading_enabled=True,
            live_order_confirmation=LIVE_CONFIRMATION_PHRASE,
        )
        broker = UpbitLiveBroker(client, settings)  # type: ignore[arg-type]
        intent = OrderIntent("KRW-BTC", "bid", "price", "test", price=Decimal("5000"))

        result = broker.execute(intent, Decimal("1000"))

        self.assertTrue(result.ok)
        self.assertEqual(client.orders[0]["market"], "KRW-BTC")
        self.assertEqual(client.orders[0]["ord_type"], "price")

    def test_live_broker_accepts_ascii_confirmation_code(self) -> None:
        client = FakeLiveClient()
        settings = TradingSettings(
            live_trading_enabled=True,
            live_order_confirmation=LIVE_CONFIRMATION_CODE,
        )
        broker = UpbitLiveBroker(client, settings)  # type: ignore[arg-type]
        intent = OrderIntent("KRW-BTC", "bid", "price", "test", price=Decimal("5000"))

        result = broker.execute(intent, Decimal("1000"))

        self.assertTrue(result.ok)
        self.assertEqual(client.orders[0]["market"], "KRW-BTC")


if __name__ == "__main__":
    unittest.main()
