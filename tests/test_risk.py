from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.models import Signal
from upbit_autotrader.risk import RiskManager
from upbit_autotrader.state import PaperState


class RiskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = TradingSettings(
            min_order_krw=Decimal("5000"),
            max_order_krw=Decimal("10000"),
            max_position_krw=Decimal("20000"),
        )
        self.risk = RiskManager(self.settings)

    def test_buy_uses_per_order_cap(self) -> None:
        state = PaperState(cash_krw=Decimal("100000"))
        signal = Signal("buy", "KRW-BTC", Decimal("1000"), "test")
        decision = self.risk.evaluate(signal, state, Decimal("1000"))
        self.assertTrue(decision.approved)
        self.assertIsNotNone(decision.intent)
        self.assertEqual(decision.intent.price, Decimal("10000"))

    def test_buy_rejected_when_remaining_position_is_below_min(self) -> None:
        state = PaperState(
            cash_krw=Decimal("100000"),
            position_volume=Decimal("18"),
            avg_entry_price=Decimal("1000"),
        )
        signal = Signal("buy", "KRW-BTC", Decimal("1000"), "test")
        decision = self.risk.evaluate(signal, state, Decimal("1000"))
        self.assertFalse(decision.approved)

    def test_sell_rejected_without_position(self) -> None:
        state = PaperState(cash_krw=Decimal("100000"))
        signal = Signal("sell", "KRW-BTC", Decimal("1000"), "test")
        decision = self.risk.evaluate(signal, state, Decimal("1000"))
        self.assertFalse(decision.approved)

    def test_sell_approved_with_position(self) -> None:
        state = PaperState(
            cash_krw=Decimal("100000"),
            position_volume=Decimal("0.01"),
            avg_entry_price=Decimal("1000"),
        )
        signal = Signal("sell", "KRW-BTC", Decimal("1000"), "test")
        decision = self.risk.evaluate(signal, state, Decimal("1000"))
        self.assertTrue(decision.approved)
        self.assertEqual(decision.intent.volume, Decimal("0.01"))


if __name__ == "__main__":
    unittest.main()
