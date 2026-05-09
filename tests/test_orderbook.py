from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.models import OrderIntent
from upbit_autotrader.orderbook import adjust_order_for_orderbook, analyze_orderbook
from upbit_autotrader.realtime_engine import RealtimeOrderPlan, apply_orderbook_to_realtime_orders


def settings_for(temp_dir: str, **overrides: Any) -> TradingSettings:
    values = {
        "markets": ("KRW-AAA",),
        "market": "KRW-AAA",
        "state_file": Path(temp_dir) / "paper_state.json",
        "min_order_krw": Decimal("5000"),
        "orderbook_analysis_enabled": True,
        "orderbook_depth_levels": 15,
        "orderbook_max_slippage_pct": Decimal("10"),
        "orderbook_min_fill_ratio": Decimal("0.95"),
        "orderbook_min_depth_ratio": Decimal("0"),
        "orderbook_liquidity_use_pct": Decimal("1"),
        "orderbook_reprice_spread_pct": Decimal("10"),
        "orderbook_hard_max_spread_pct": Decimal("10"),
        "orderbook_min_visible_ask_krw": Decimal("0"),
        "orderbook_min_visible_bid_krw": Decimal("0"),
    }
    values.update(overrides)
    return TradingSettings(**values)


def orderbook_payload() -> dict[str, Any]:
    return {
        "market": "KRW-AAA",
        "orderbook_units": [
            {"ask_price": "100", "ask_size": "50", "bid_price": "99.9", "bid_size": "80"},
            {"ask_price": "110", "ask_size": "100", "bid_price": "99.8", "bid_size": "100"},
            {"ask_price": "120", "ask_size": "200", "bid_price": "99.7", "bid_size": "200"},
        ],
    }


def tight_recoverable_spread_payload() -> dict[str, Any]:
    return {
        "market": "KRW-AAA",
        "orderbook_units": [
            {"ask_price": "100.3", "ask_size": "100", "bid_price": "99.8", "bid_size": "100"},
            {"ask_price": "100.4", "ask_size": "100", "bid_price": "99.7", "bid_size": "100"},
        ],
    }


def small_visible_liquidity_payload() -> dict[str, Any]:
    return {
        "market": "KRW-AAA",
        "orderbook_units": [
            {"ask_price": "100", "ask_size": "200", "bid_price": "99.9", "bid_size": "200"},
        ],
    }


class FakeOrderbookClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def get_orderbook(
        self,
        markets: str | list[str],
        count: int | None = None,
        level: str | int | None = None,
    ) -> list[dict[str, Any]]:
        return [self.payload]


class OrderbookAnalysisTests(unittest.TestCase):
    def test_buy_analysis_sweeps_cumulative_asks_for_expected_fill_price(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)

            analysis = analyze_orderbook(settings, orderbook_payload(), "bid", amount_krw=Decimal("10000"), reference_price=Decimal("100"))

            self.assertEqual(analysis.side, "bid")
            self.assertEqual(analysis.levels_used, 2)
            self.assertGreater(analysis.expected_avg_price, Decimal("100"))
            self.assertEqual(analysis.recommended_amount_krw, Decimal("10000"))
            self.assertIn(analysis.action, {"use", "reprice"})

    def test_buy_analysis_reduces_when_visible_depth_cap_is_smaller_than_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir, orderbook_liquidity_use_pct=Decimal("0.35"))

            analysis = analyze_orderbook(settings, orderbook_payload(), "bid", amount_krw=Decimal("50000"), reference_price=Decimal("100"))

            self.assertEqual(analysis.action, "reduce")
            self.assertLess(analysis.recommended_amount_krw, Decimal("50000"))
            self.assertGreaterEqual(analysis.recommended_amount_krw, settings.min_order_krw)

    def test_recoverable_wide_spread_reprices_instead_of_dropping_small_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(
                temp_dir,
                orderbook_hard_max_spread_pct=Decimal("0.30"),
                orderbook_reprice_spread_pct=Decimal("0.12"),
                orderbook_max_slippage_pct=Decimal("0.35"),
            )

            analysis = analyze_orderbook(
                settings,
                tight_recoverable_spread_payload(),
                "bid",
                amount_krw=Decimal("10000"),
                reference_price=Decimal("100.3"),
            )

            self.assertEqual(analysis.action, "reprice")
            self.assertIn("spread hard limit exceeded", analysis.reason)
            self.assertGreaterEqual(analysis.recommended_amount_krw, settings.min_order_krw)

    def test_visible_liquidity_floor_scales_to_order_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(
                temp_dir,
                orderbook_min_visible_ask_krw=Decimal("1000000"),
                orderbook_min_visible_bid_krw=Decimal("1000000"),
            )

            analysis = analyze_orderbook(
                settings,
                small_visible_liquidity_payload(),
                "bid",
                amount_krw=Decimal("10000"),
                reference_price=Decimal("100"),
            )

            self.assertNotEqual(analysis.action, "skip")
            self.assertEqual(analysis.recommended_amount_krw, Decimal("10000"))

    def test_sell_analysis_sweeps_cumulative_bids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir, orderbook_max_slippage_pct=Decimal("3"))

            analysis = analyze_orderbook(settings, orderbook_payload(), "ask", volume=Decimal("50"), reference_price=Decimal("100"))

            self.assertEqual(analysis.side, "ask")
            self.assertEqual(analysis.levels_used, 1)
            self.assertLess(analysis.expected_avg_price, Decimal("100"))
            self.assertEqual(analysis.recommended_volume, Decimal("50"))

    def test_adjust_order_for_orderbook_reprices_paper_execution_price(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            intent = OrderIntent("KRW-AAA", "bid", "price", "test", price=Decimal("10000"))

            adjustment = adjust_order_for_orderbook(
                settings,
                FakeOrderbookClient(orderbook_payload()),
                "KRW-AAA",
                "bid",
                Decimal("10000"),
                None,
                Decimal("100"),
                intent,
            )

            self.assertIsNotNone(adjustment)
            assert adjustment is not None
            self.assertFalse(adjustment.skipped)
            self.assertGreater(adjustment.current_price, Decimal("100"))
            self.assertEqual(adjustment.intent.price, Decimal("10000"))

    def test_realtime_orderbook_adjustment_drops_unfillable_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(
                temp_dir,
                orderbook_liquidity_use_pct=Decimal("0.01"),
                orderbook_max_slippage_pct=Decimal("0.01"),
            )
            intent = OrderIntent("KRW-AAA", "bid", "price", "test", price=Decimal("10000"))
            order = RealtimeOrderPlan("KRW-AAA", "bid", Decimal("10000"), None, Decimal("90"), "test", intent)
            errors: list[dict[str, str]] = []

            adjusted = apply_orderbook_to_realtime_orders(settings, FakeOrderbookClient(orderbook_payload()), [order], errors)

            self.assertEqual(adjusted, [])
            self.assertEqual(errors[0]["market"], "KRW-AAA")


if __name__ == "__main__":
    unittest.main()
