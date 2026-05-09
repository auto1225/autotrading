from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.allocation import build_dynamic_allocation_plan, execute_allocation_plan, score_allocation_candidate
from upbit_autotrader.config import TradingSettings
from upbit_autotrader.learning import save_learning_model
from upbit_autotrader.models import Candle, Signal
from upbit_autotrader.state import PortfolioPosition, PortfolioState
from upbit_autotrader.web import allocation_status_payload, is_allocation_due, save_allocation_runtime


def candle_payload(market: str, price: Decimal, timestamp: int, trade_value: Decimal) -> dict[str, Any]:
    return {
        "market": market,
        "candle_date_time_utc": f"2026-01-01T00:{timestamp:04d}:00",
        "candle_date_time_kst": f"2026-01-01T09:{timestamp:04d}:00",
        "opening_price": str(price),
        "high_price": str(price + Decimal("0.1")),
        "low_price": str(price - Decimal("0.1")),
        "trade_price": str(price),
        "timestamp": timestamp,
        "candle_acc_trade_price": str(trade_value),
        "candle_acc_trade_volume": "10",
    }


def trend_candles(market: str, start_price: str, count: int = 30) -> list[dict[str, Any]]:
    base = Decimal(start_price)
    rows = [
        candle_payload(market, base + Decimal(index), index, Decimal("100000") + Decimal(index * 5000))
        for index in range(1, count + 1)
    ]
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def flat_candles(market: str, price: str, count: int = 30) -> list[dict[str, Any]]:
    value = Decimal(price)
    rows = [candle_payload(market, value, index, Decimal("100000")) for index in range(1, count + 1)]
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def probability_edge_candles(market: str) -> list[Candle]:
    offsets = [Decimal("0.25"), Decimal("0.25"), Decimal("-0.15"), Decimal("-0.15"), Decimal("-0.15")]
    rows: list[Candle] = []
    for index in range(1, 61):
        price = Decimal("100") + Decimal(index) * Decimal("0.08") + offsets[index % len(offsets)]
        rows.append(
            Candle.from_upbit(
                {
                    "market": market,
                    "candle_date_time_utc": f"2026-01-01T00:{index:04d}:00",
                    "candle_date_time_kst": f"2026-01-01T09:{index:04d}:00",
                    "opening_price": f"{price:.2f}",
                    "high_price": f"{price + Decimal('0.7'):.2f}",
                    "low_price": f"{price - Decimal('0.7'):.2f}",
                    "trade_price": f"{price:.2f}",
                    "timestamp": index,
                    "candle_acc_trade_price": str(10000 + index * 350),
                    "candle_acc_trade_volume": "100",
                }
            )
        )
    return rows


class FakeAllocationClient:
    def __init__(self, candles_by_market: dict[str, list[dict[str, Any]]]) -> None:
        self.candles_by_market = candles_by_market

    def get_minute_candles(
        self,
        market: str,
        unit: int = 5,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        return list(self.candles_by_market[market])[:count]


class FakeBuyStrategy:
    def evaluate(self, candles: list[Candle]) -> Signal:
        latest = sorted(candles, key=lambda candle: candle.timestamp)[-1]
        return Signal("buy", latest.market, latest.trade_price, "fake maeuknam card", Decimal("0.90"))


def allocation_settings(temp_dir: str) -> TradingSettings:
    return TradingSettings(
        markets=("KRW-AAA", "KRW-BBB", "KRW-CCC", "KRW-OLD"),
        market="KRW-AAA",
        state_file=Path(temp_dir) / "paper_state.json",
        short_window=3,
        long_window=8,
        candle_count=30,
        allocation_top_n=2,
        allocation_focus_top_n=1,
        allocation_focus_score_gap=Decimal("0.20"),
        allocation_min_score=Decimal("0.01"),
        allocation_max_deploy_pct=Decimal("0.8"),
        allocation_max_position_pct=Decimal("0.5"),
        allocation_max_orders_per_run=10,
        min_order_krw=Decimal("5000"),
        max_order_krw=Decimal("500000"),
        max_position_krw=Decimal("500000"),
        cooldown_seconds=0,
        max_open_positions=20,
        max_daily_orders=20,
        risk_min_candle_trade_value_krw=Decimal("0"),
        risk_market_min_trade_value_24h_krw=Decimal("0"),
        orderbook_min_visible_ask_krw=Decimal("0"),
        orderbook_min_visible_bid_krw=Decimal("0"),
    )


def save_model(settings: TradingSettings) -> None:
    save_learning_model(
        settings,
        {
            "version": 1,
            "markets": {
                "KRW-AAA": {
                    "market": "KRW-AAA",
                    "bestStrategy": "guarded_momentum",
                    "label": "Alpha",
                    "score": "0.50",
                    "regime": "상승 추세",
                },
                "KRW-BBB": {
                    "market": "KRW-BBB",
                    "bestStrategy": "guarded_momentum",
                    "label": "Beta",
                    "score": "0.45",
                    "regime": "상승 추세",
                },
                "KRW-CCC": {
                    "market": "KRW-CCC",
                    "bestStrategy": "guarded_momentum",
                    "label": "Gamma",
                    "score": "-0.50",
                    "regime": "횡보",
                },
            },
        },
    )


class DynamicAllocationTests(unittest.TestCase):
    def test_builds_distributed_buy_orders_from_hourly_ranked_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            save_model(settings)
            client = FakeAllocationClient(
                {
                    "KRW-AAA": trend_candles("KRW-AAA", "100"),
                    "KRW-BBB": trend_candles("KRW-BBB", "200"),
                    "KRW-CCC": flat_candles("KRW-CCC", "300"),
                }
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_dynamic_allocation_plan(settings, client, state, pause_seconds=0)

            self.assertEqual(plan.mode, "분산")
            self.assertEqual({candidate.market for candidate in plan.selected}, {"KRW-AAA", "KRW-BBB"})
            self.assertEqual([order.side for order in plan.orders], ["bid", "bid"])
            self.assertGreater(sum(order.amount_krw for order in plan.orders), Decimal("500000"))

            results = execute_allocation_plan(plan, state, Decimal("0.0005"))

            self.assertTrue(all(result["ok"] for result in results))
            self.assertLess(state.cash_krw, Decimal("1000000"))
            self.assertGreater(state.position("KRW-AAA").volume, Decimal("0"))
            self.assertGreater(state.position("KRW-BBB").volume, Decimal("0"))

    def test_sells_held_market_when_it_is_no_longer_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            save_model(settings)
            client = FakeAllocationClient(
                {
                    "KRW-AAA": trend_candles("KRW-AAA", "100"),
                    "KRW-BBB": trend_candles("KRW-BBB", "200"),
                    "KRW-CCC": flat_candles("KRW-CCC", "300"),
                    "KRW-OLD": trend_candles("KRW-OLD", "10000"),
                }
            )
            state = PortfolioState(
                cash_krw=Decimal("100000"),
                positions={"KRW-OLD": PortfolioPosition(volume=Decimal("10"), avg_entry_price=Decimal("9000"))},
            )

            plan = build_dynamic_allocation_plan(settings, client, state, pause_seconds=0)

            sell_orders = [order for order in plan.orders if order.side == "ask"]
            self.assertEqual(len(sell_orders), 1)
            self.assertEqual(sell_orders[0].market, "KRW-OLD")

    def test_weak_regime_still_uses_most_capital_for_goal_pursuit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                allocation_settings(temp_dir),
                allocation_max_deploy_pct=Decimal("1"),
                risk_regime_min_positive_ratio=Decimal("0.90"),
                risk_regime_soft_positive_ratio=Decimal("0.95"),
                risk_regime_min_avg_trend_pct=Decimal("-99"),
            )
            save_model(settings)
            client = FakeAllocationClient(
                {
                    "KRW-AAA": trend_candles("KRW-AAA", "100"),
                    "KRW-BBB": trend_candles("KRW-BBB", "200"),
                    "KRW-CCC": flat_candles("KRW-CCC", "300"),
                }
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_dynamic_allocation_plan(settings, client, state, pause_seconds=0)

            self.assertEqual(plan.market_regime["label"], "weak")
            self.assertEqual(plan.market_regime["deployMultiplier"], "0.85")
            self.assertGreater(plan.deploy_limit_krw, Decimal("800000"))

    def test_manual_recommended_market_scope_limits_new_allocation_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            save_model(settings)
            client = FakeAllocationClient(
                {
                    "KRW-AAA": trend_candles("KRW-AAA", "100"),
                    "KRW-BBB": trend_candles("KRW-BBB", "200"),
                }
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_dynamic_allocation_plan(settings, client, state, markets=("KRW-BBB",), pause_seconds=0)

            self.assertEqual({candidate.market for candidate in plan.selected}, {"KRW-BBB"})
            self.assertTrue(all(order.market == "KRW-BBB" for order in plan.orders))

    def test_high_learning_score_without_buy_signal_does_not_create_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Flat",
                            "score": "50.00",
                        }
                    },
                },
            )
            client = FakeAllocationClient({"KRW-AAA": flat_candles("KRW-AAA", "100")})
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_dynamic_allocation_plan(settings, client, state, pause_seconds=0)

            self.assertEqual(plan.selected, ())
            self.assertEqual(plan.orders, ())

    def test_daily_loss_limit_blocks_new_allocation_buys_but_keeps_exits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            save_model(settings)
            client = FakeAllocationClient(
                {
                    "KRW-AAA": trend_candles("KRW-AAA", "100"),
                    "KRW-BBB": trend_candles("KRW-BBB", "200"),
                    "KRW-CCC": flat_candles("KRW-CCC", "300"),
                    "KRW-OLD": trend_candles("KRW-OLD", "10000"),
                }
            )
            state = PortfolioState(
                cash_krw=Decimal("1000000"),
                daily_realized_pnl_krw=-settings.daily_loss_limit_krw,
                positions={"KRW-OLD": PortfolioPosition(volume=Decimal("10"), avg_entry_price=Decimal("9000"))},
            )

            plan = build_dynamic_allocation_plan(settings, client, state, pause_seconds=0)

            self.assertTrue(all(order.side == "ask" for order in plan.orders))
            self.assertEqual([order.market for order in plan.orders], ["KRW-OLD"])

    def test_probability_edge_overrides_learning_strategy_before_next_learning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                allocation_settings(temp_dir),
                short_window=5,
                long_window=20,
                strategy_min_trend_pct=Decimal("0.08"),
                strategy_min_volume_ratio=Decimal("1.02"),
                strategy_max_volatility_pct=Decimal("6"),
                realtime_low_volatility_pct=Decimal("0.20"),
                take_profit_pct=Decimal("8"),
                stop_loss_pct=Decimal("2"),
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            candidate = score_allocation_candidate(
                settings,
                state,
                probability_edge_candles("KRW-AAA"),
                {"market": "KRW-AAA", "bestStrategy": "mean_reversion", "label": "Old", "score": "0"},
            )

            self.assertEqual(candidate.strategy, "probability_edge")
            self.assertEqual(candidate.signal.action, "buy")
            self.assertGreater(candidate.score, Decimal("0.2"))

    def test_maeuknam_allocation_mode_does_not_probe_probability_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                allocation_settings(temp_dir),
                strategy_name="maeuknam_cards",
                risk_regime_guard_enabled=False,
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})
            strategy_calls: list[str] = []

            def fake_make_strategy(strategy_settings: TradingSettings, strategy_name: str) -> FakeBuyStrategy:
                strategy_calls.append(strategy_name)
                return FakeBuyStrategy()

            with patch("upbit_autotrader.allocation.make_strategy_by_name", side_effect=fake_make_strategy):
                candidate = score_allocation_candidate(
                    settings,
                    state,
                    probability_edge_candles("KRW-AAA"),
                    {"market": "KRW-AAA", "bestStrategy": "mean_reversion", "label": "Old", "score": "99"},
                )

            self.assertEqual(candidate.strategy, "maeuknam_cards")
            self.assertEqual(candidate.signal.action, "buy")
            self.assertEqual(strategy_calls, ["maeuknam_cards"])

    def test_empty_manual_scope_does_not_fall_back_to_allocation_universe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            save_model(settings)
            client = FakeAllocationClient({"KRW-AAA": trend_candles("KRW-AAA", "100")})
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_dynamic_allocation_plan(settings, client, state, markets=(), pause_seconds=0)

            self.assertEqual(plan.scanned_count, 0)
            self.assertEqual(plan.selected, ())
            self.assertEqual(plan.orders, ())

    def test_preview_runtime_does_not_delay_next_hourly_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = allocation_settings(temp_dir)
            now = datetime.now(timezone.utc).isoformat()

            save_allocation_runtime(settings, {"updatedAt": now, "previewedAt": now, "executed": False})

            self.assertTrue(is_allocation_due(settings))
            self.assertTrue(allocation_status_payload(settings)["due"])

            save_allocation_runtime(settings, {"updatedAt": now, "executedAt": now, "executed": True})

            self.assertFalse(is_allocation_due(settings))
            self.assertFalse(allocation_status_payload(settings)["due"])


if __name__ == "__main__":
    unittest.main()
