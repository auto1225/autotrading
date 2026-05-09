from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.learning import save_learning_model
from upbit_autotrader.market_regime import MarketRegimeSignal
from upbit_autotrader.maeuknam_strategy import MaeuknamTechniqueSignal
from upbit_autotrader.models import Candle
from upbit_autotrader.pattern_learning import PatternObservation, build_pattern_model, feature_snapshot, save_pattern_model
from upbit_autotrader.realtime_engine import (
    RealtimeSituation,
    build_realtime_decision_plan,
    execute_realtime_plan,
    neutral_goal_pace_pressure,
    realtime_entry_target_values,
    realtime_goal_pace_pressure,
    realtime_market_universe,
)
from upbit_autotrader.state import PortfolioPosition, PortfolioState


def candle_payload(market: str, price: Decimal, timestamp: int, trade_value: Decimal) -> dict[str, Any]:
    return {
        "market": market,
        "candle_date_time_utc": f"2026-01-01T00:{timestamp:04d}:00",
        "candle_date_time_kst": f"2026-01-01T09:{timestamp:04d}:00",
        "opening_price": str(price),
        "high_price": str(price + Decimal("1")),
        "low_price": str(price - Decimal("1")),
        "trade_price": str(price),
        "timestamp": timestamp,
        "candle_acc_trade_price": str(trade_value),
        "candle_acc_trade_volume": "10",
    }


def upward_candles(market: str, start: str = "100", count: int = 60) -> list[dict[str, Any]]:
    base = Decimal(start)
    rows = [
        candle_payload(market, base + Decimal(index), index, Decimal("100000") + Decimal(index * 8000))
        for index in range(1, count + 1)
    ]
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def crash_candles(market: str, start: str = "200", count: int = 60) -> list[dict[str, Any]]:
    base = Decimal(start)
    rows = [
        candle_payload(market, base - Decimal(index * 2), index, Decimal("250000") + Decimal(index * 10000))
        for index in range(1, count + 1)
    ]
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def flat_candles(market: str, price: str = "100", count: int = 60) -> list[dict[str, Any]]:
    value = Decimal(price)
    rows = [candle_payload(market, value, index, Decimal("200000")) for index in range(1, count + 1)]
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def quiet_candles(market: str, price: str = "100", count: int = 60) -> list[dict[str, Any]]:
    value = Decimal(price)
    rows = []
    for index in range(1, count + 1):
        row = candle_payload(market, value, index, Decimal("200000"))
        row["high_price"] = str(value + Decimal("0.01"))
        row["low_price"] = str(value - Decimal("0.01"))
        rows.append(row)
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def surge_candles(market: str, start: str = "100", count: int = 60) -> list[dict[str, Any]]:
    base = Decimal(start)
    rows = []
    for index in range(1, count + 1):
        price = base + Decimal(index) / Decimal("3")
        trade_value = Decimal("100000")
        if index >= count - 1:
            trade_value = Decimal("2000000")
        rows.append(candle_payload(market, price, index, trade_value))
    return sorted(rows, key=lambda row: int(row["timestamp"]), reverse=True)


def maeuknam_signal(entry_allowed: bool = True) -> MaeuknamTechniqueSignal:
    return MaeuknamTechniqueSignal(
        technique_id="breakout_retest_long",
        technique_name="breakout retest long",
        direction="LONG",
        score=Decimal("0.84") if entry_allowed else Decimal("0.66"),
        entry_threshold=Decimal("0.72"),
        watch_threshold=Decimal("0.58"),
        entry_allowed=entry_allowed,
        hard_blocks=() if entry_allowed else ("blocked",),
        entry_price=Decimal("160"),
        stop_price=Decimal("159"),
        target1_price=Decimal("162"),
        target2_price=Decimal("164"),
        support_price=Decimal("159.5"),
        resistance_price=Decimal("162"),
        risk_pct=Decimal("0.30"),
        reward_risk=Decimal("2.0"),
        features={"structure_score": Decimal("0.8")},
        reason="test maeuknam card",
    )


class FakeRealtimeClient:
    def __init__(self, tickers: dict[str, dict[str, Any]], candles: dict[str, list[dict[str, Any]]]) -> None:
        self.tickers = tickers
        self.candles = candles
        self.candle_requests: list[str] = []

    def get_ticker(self, markets: str | list[str]) -> list[dict[str, Any]]:
        market_list = markets.split(",") if isinstance(markets, str) else markets
        return [self.tickers[market] for market in market_list if market in self.tickers]

    def get_minute_candles(
        self,
        market: str,
        unit: int = 1,
        count: int = 60,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        self.candle_requests.append(market)
        return list(self.candles.get(market, []))[:count]


def settings_for(temp_dir: str) -> TradingSettings:
    return TradingSettings(
        markets=("KRW-AAA", "KRW-BBB"),
        market="KRW-AAA",
        state_file=Path(temp_dir) / "paper_state.json",
        realtime_decision_interval_seconds=5,
        realtime_watch_top_n=10,
        realtime_candle_top_n=4,
        realtime_candidate_top_n=3,
        realtime_min_score=Decimal("0.12"),
        realtime_max_order_pct=Decimal("0.1"),
        allocation_max_deploy_pct=Decimal("0.8"),
        allocation_max_position_pct=Decimal("0.3"),
        min_order_krw=Decimal("5000"),
        max_order_krw=Decimal("10000"),
        max_position_krw=Decimal("500000"),
        cooldown_seconds=0,
        max_open_positions=10,
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
                    "score": "0.30",
                    "regime": "상승 추세",
                },
                "KRW-BBB": {
                    "market": "KRW-BBB",
                    "bestStrategy": "guarded_momentum",
                    "label": "Beta",
                    "score": "0.20",
                    "regime": "횡보",
                },
            },
        },
    )


class RealtimeEngineTests(unittest.TestCase):
    def test_realtime_universe_keeps_all_learned_markets_without_watch_top_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-AAA",),
                market="KRW-AAA",
                state_file=Path(temp_dir) / "paper_state.json",
                realtime_watch_top_n=1,
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-BBB": {"market": "KRW-BBB", "score": "0.90"},
                        "KRW-CCC": {"market": "KRW-CCC", "score": "0.10"},
                    },
                },
            )
            state = PortfolioState(cash_krw=Decimal("0"), positions={})

            universe = realtime_market_universe(settings, state)

        self.assertEqual(universe, ("KRW-AAA", "KRW-BBB", "KRW-CCC"))

    def test_maeuknam_universe_ignores_learned_markets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                markets=("KRW-AAA",),
                market="KRW-AAA",
                state_file=Path(temp_dir) / "paper_state.json",
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-BBB": {"market": "KRW-BBB", "score": "99.00"},
                    },
                },
            )
            state = PortfolioState(
                cash_krw=Decimal("0"),
                positions={"KRW-HELD": PortfolioPosition(volume=Decimal("1"), avg_entry_price=Decimal("100"))},
            )

            universe = realtime_market_universe(settings, state)

        self.assertEqual(universe, ("KRW-AAA", "KRW-HELD"))

    def test_realtime_plan_returns_every_evaluated_situation_for_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            markets = tuple(f"KRW-T{i}" for i in range(1, 8))
            client = FakeRealtimeClient(
                {
                    market: {
                        "market": market,
                        "trade_price": str(100 + index),
                        "signed_change_rate": "0.01",
                        "acc_trade_price_24h": "1000000000",
                    }
                    for index, market in enumerate(markets, start=1)
                },
                {},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, candidate_markets=markets)

            self.assertEqual(plan.evaluated_count, len(markets))
            self.assertEqual(len(plan.situations), len(markets))
            self.assertEqual({situation.market for situation in plan.situations}, set(markets))

    def test_realtime_engine_buys_when_learning_and_live_trend_agree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "100",
                        "signed_change_rate": "0.01",
                        "acc_trade_price_24h": "2000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA"), "KRW-BBB": upward_candles("KRW-BBB", "90")},
            )
            now = datetime.now(timezone.utc)
            previous = {
                "history": {
                    "KRW-AAA": [
                        {"time": (now - timedelta(seconds=40)).isoformat(), "price": "150"},
                    ]
                }
            }
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, previous_runtime=previous)

            self.assertEqual(plan.selected[0].market, "KRW-AAA")
            self.assertEqual(plan.orders[0].side, "bid")
            self.assertIn("상승", plan.selected[0].reason)

            results = execute_realtime_plan(plan, state, Decimal("0.0005"))
            self.assertTrue(results[0]["ok"])
            self.assertGreater(state.position("KRW-AAA").volume, Decimal("0"))

    def test_maeuknam_mode_buys_only_when_card_allows_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                strategy_name="maeuknam_cards",
                goal_scheduler_trading_enabled=False,
                risk_regime_guard_enabled=False,
                realtime_recovery_scout_enabled=True,
                realtime_weak_breakout_enabled=True,
            )
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": upward_candles("KRW-AAA")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            with patch("upbit_autotrader.realtime_engine.evaluate_maeuknam_techniques", return_value=maeuknam_signal(False)):
                blocked_plan = build_realtime_decision_plan(settings, client, state, candidate_markets=("KRW-AAA",))

            with patch("upbit_autotrader.realtime_engine.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
                allowed_plan = build_realtime_decision_plan(settings, client, state, candidate_markets=("KRW-AAA",))

            self.assertEqual(blocked_plan.selected, ())
            self.assertFalse([order for order in blocked_plan.orders if order.side == "bid"])
            self.assertEqual(blocked_plan.situations[0].strategy, "maeuknam_cards")
            self.assertFalse(blocked_plan.situations[0].maeuknam_signal["entryAllowed"])
            self.assertEqual(allowed_plan.selected[0].strategy, "maeuknam_cards")
            self.assertEqual(allowed_plan.orders[0].side, "bid")
            self.assertTrue(allowed_plan.selected[0].maeuknam_signal["entryAllowed"])

    def test_realtime_engine_forces_rising_leader_into_candle_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                realtime_candle_top_n=1,
                realtime_candidate_top_n=2,
                risk_regime_guard_enabled=False,
                risk_min_entry_score_buffer=Decimal("0"),
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-FLAT": {
                            "market": "KRW-FLAT",
                            "bestStrategy": "guarded_momentum",
                            "label": "Flat",
                            "score": "50.00",
                        },
                        "KRW-MOMO": {
                            "market": "KRW-MOMO",
                            "bestStrategy": "guarded_momentum",
                            "label": "Momentum",
                            "score": "0",
                        },
                    },
                },
            )
            markets = ("KRW-FLAT", "KRW-LOW1", "KRW-LOW2", "KRW-LOW3", "KRW-MOMO")
            client = FakeRealtimeClient(
                {
                    "KRW-FLAT": {
                        "market": "KRW-FLAT",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-LOW1": {
                        "market": "KRW-LOW1",
                        "trade_price": "100",
                        "signed_change_rate": "-0.01",
                        "acc_trade_price_24h": "1000000000",
                    },
                    "KRW-LOW2": {
                        "market": "KRW-LOW2",
                        "trade_price": "100",
                        "signed_change_rate": "-0.02",
                        "acc_trade_price_24h": "1000000000",
                    },
                    "KRW-LOW3": {
                        "market": "KRW-LOW3",
                        "trade_price": "100",
                        "signed_change_rate": "-0.01",
                        "acc_trade_price_24h": "1000000000",
                    },
                    "KRW-MOMO": {
                        "market": "KRW-MOMO",
                        "trade_price": "130",
                        "signed_change_rate": "0.06",
                        "acc_trade_price_24h": "20000000000",
                        "trade_pressure": "2",
                    },
                },
                {"KRW-FLAT": flat_candles("KRW-FLAT", "100"), "KRW-MOMO": surge_candles("KRW-MOMO", "110")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, candidate_markets=markets)

            self.assertIn("KRW-MOMO", client.candle_requests)
            self.assertEqual(plan.selected[0].market, "KRW-MOMO")
            self.assertIn("상승 리더", plan.selected[0].tags)
            self.assertEqual(plan.orders[0].side, "bid")

    def test_goal_scheduler_pressure_is_attached_to_realtime_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(settings_for(temp_dir), risk_regime_guard_enabled=False)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": upward_candles("KRW-AAA")},
            )
            state = PortfolioState(cash_krw=Decimal("900000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state)
            payload = plan.to_dict()["goalPressure"]

            self.assertTrue(payload["enabled"])
            self.assertLess(Decimal(payload["entryScoreAdjustment"]), Decimal("0"))
            self.assertGreater(Decimal(payload["deployMultiplier"]), Decimal("1"))
            self.assertIn("목표페이스", plan.selected[0].reason)

    def test_goal_scheduler_pressure_can_be_disabled(self) -> None:
        settings = replace(TradingSettings(), goal_scheduler_trading_enabled=False)

        pressure = realtime_goal_pace_pressure(settings, Decimal("900000"))

        self.assertFalse(pressure.enabled)
        self.assertEqual(pressure.entry_score_adjustment, Decimal("0"))
        self.assertEqual(pressure.deploy_multiplier, Decimal("1"))

    def test_goal_recovery_scout_promotes_small_candidate_when_pace_is_behind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                realtime_weak_breakout_enabled=True,
                realtime_recovery_scout_enabled=True,
                risk_regime_guard_enabled=True,
                risk_regime_min_market_count=2,
                risk_regime_min_positive_ratio=Decimal("0.75"),
                risk_regime_soft_positive_ratio=Decimal("0.85"),
                risk_regime_min_avg_trend_pct=Decimal("-99"),
                risk_market_min_trade_value_24h_krw=Decimal("999999999999"),
                risk_min_candle_trade_value_krw=Decimal("999999999999"),
                risk_strategy_max_consecutive_losses=10,
                risk_same_pattern_max_consecutive_losses=10,
                risk_global_max_consecutive_losses=10,
                risk_min_trade_pressure=Decimal("-4"),
                risk_chase_5m_rise_pct=Decimal("10"),
                risk_chase_30m_rise_pct=Decimal("20"),
                max_order_krw=Decimal("1000000"),
                realtime_max_order_pct=Decimal("1"),
                allocation_max_deploy_pct=Decimal("1"),
                allocation_max_position_pct=Decimal("1"),
            )
            raw_candles = surge_candles("KRW-AAA")
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Alpha",
                            "score": "1.80",
                        }
                    },
                },
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "120",
                        "signed_change_rate": "0.03",
                        "acc_trade_price_24h": "10000000000",
                        "trade_pressure": "-0.5",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                },
                {"KRW-AAA": raw_candles, "KRW-BBB": flat_candles("KRW-BBB", "100")},
            )
            state = PortfolioState(cash_krw=Decimal("900000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.market_regime["label"], "weak")
            self.assertEqual(plan.selected[0].market, "KRW-AAA")
            self.assertEqual(plan.orders[0].side, "bid")
            self.assertIn("목표복구 스카우트", plan.selected[0].tags)
            self.assertGreaterEqual(plan.orders[0].amount_krw, Decimal("300000"))
            self.assertLessEqual(plan.orders[0].amount_krw, Decimal("315000"))

    def test_realtime_engine_promotes_strong_risk_clear_score_without_trend_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(settings_for(temp_dir), risk_regime_guard_enabled=False)
            settings = replace(settings, realtime_stagnation_volume_ratio=Decimal("0"))
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Alpha",
                            "score": "1.20",
                        }
                    },
                },
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": flat_candles("KRW-AAA", "100")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.selected[0].market, "KRW-AAA")
            self.assertEqual(plan.orders[0].side, "bid")
            self.assertIn("강한 점수 후보", plan.selected[0].tags)

    def test_realtime_engine_blocks_new_bids_during_weak_regime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                risk_regime_min_market_count=2,
                risk_regime_min_positive_ratio=Decimal("0.75"),
                risk_regime_soft_positive_ratio=Decimal("0.85"),
                risk_regime_min_avg_trend_pct=Decimal("-99"),
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Alpha",
                            "score": "1.20",
                        }
                    },
                },
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA"), "KRW-BBB": flat_candles("KRW-BBB", "100")},
            )
            now = datetime.now(timezone.utc)
            previous = {
                "history": {
                    "KRW-AAA": [
                        {"time": (now - timedelta(seconds=40)).isoformat(), "price": "150"},
                    ]
                }
            }
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, previous_runtime=previous)

            self.assertEqual(plan.market_regime["label"], "weak")
            self.assertTrue(plan.market_regime["blockNewEntries"])
            self.assertEqual(plan.selected, ())
            self.assertFalse([order for order in plan.orders if order.side == "bid"])

    def test_realtime_engine_allows_exceptional_breakout_when_weak_regime_override_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                realtime_weak_breakout_enabled=True,
                realtime_weak_breakout_score_buffer=Decimal("0.20"),
                risk_regime_min_market_count=2,
                risk_regime_min_positive_ratio=Decimal("0.75"),
                risk_regime_soft_positive_ratio=Decimal("0.85"),
                risk_regime_min_avg_trend_pct=Decimal("-99"),
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Alpha",
                            "score": "1.20",
                        }
                    },
                },
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA"), "KRW-BBB": flat_candles("KRW-BBB", "100")},
            )
            now = datetime.now(timezone.utc)
            previous = {
                "history": {
                    "KRW-AAA": [
                        {"time": (now - timedelta(seconds=40)).isoformat(), "price": "150"},
                    ]
                }
            }
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, previous_runtime=previous)

            self.assertEqual(plan.market_regime["label"], "weak")
            self.assertEqual(plan.selected[0].market, "KRW-AAA")
            self.assertEqual(plan.orders[0].side, "bid")
            self.assertIn("약세장 예외 돌파", plan.selected[0].tags)

    def test_realtime_engine_sells_held_position_on_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "80",
                        "signed_change_rate": "-0.12",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": crash_candles("KRW-AAA")},
            )
            now = datetime.now(timezone.utc)
            previous = {
                "history": {
                    "KRW-AAA": [
                        {"time": (now - timedelta(seconds=40)).isoformat(), "price": "95"},
                    ]
                }
            }
            state = PortfolioState(
                cash_krw=Decimal("100000"),
                positions={"KRW-AAA": PortfolioPosition(volume=Decimal("100"), avg_entry_price=Decimal("100"))},
            )

            plan = build_realtime_decision_plan(settings, client, state, previous_runtime=previous)

            self.assertEqual(plan.mode, "위험 회피")
            self.assertEqual(plan.orders[0].side, "ask")
            self.assertIn("급락", plan.situations[0].tags)

    def test_realtime_engine_sells_held_position_at_stop_loss_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "96",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": flat_candles("KRW-AAA", "100")},
            )
            state = PortfolioState(
                cash_krw=Decimal("100000"),
                positions={"KRW-AAA": PortfolioPosition(volume=Decimal("100"), avg_entry_price=Decimal("100"))},
            )

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.orders[0].side, "ask")
            self.assertIn("손절선 도달", plan.situations[0].tags)

    def test_realtime_engine_sells_held_position_at_take_profit_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "106",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": flat_candles("KRW-AAA", "100")},
            )
            state = PortfolioState(
                cash_krw=Decimal("100000"),
                positions={"KRW-AAA": PortfolioPosition(volume=Decimal("100"), avg_entry_price=Decimal("100"))},
            )

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.orders[0].side, "ask")
            self.assertIn("목표가 도달", plan.situations[0].tags)

    def test_realtime_daily_loss_limit_blocks_new_bids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": upward_candles("KRW-AAA")},
            )
            state = PortfolioState(
                cash_krw=Decimal("1000000"),
                positions={},
                daily_realized_pnl_krw=-settings.daily_loss_limit_krw,
            )

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.selected, ())
            self.assertFalse([order for order in plan.orders if order.side == "bid"])
            self.assertIn("일일 손실 한도", plan.situations[0].tags)

    def test_realtime_engine_never_plans_more_than_remaining_daily_order_slots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "110",
                        "signed_change_rate": "0.07",
                        "acc_trade_price_24h": "9000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA"), "KRW-BBB": upward_candles("KRW-BBB", "50")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={}, daily_order_count=settings.max_daily_orders - 1)

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertLessEqual(len(plan.orders), 1)

    def test_realtime_engine_rotates_out_weaker_holding_to_fund_better_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "12000000000",
                    },
                },
                {"KRW-AAA": flat_candles("KRW-AAA", "100"), "KRW-BBB": upward_candles("KRW-BBB", "90")},
            )
            now = datetime.now(timezone.utc)
            previous = {
                "history": {
                    "KRW-BBB": [
                        {"time": (now - timedelta(seconds=40)).isoformat(), "price": "145"},
                    ]
                }
            }
            state = PortfolioState(
                cash_krw=Decimal("0"),
                positions={"KRW-AAA": PortfolioPosition(volume=Decimal("1000"), avg_entry_price=Decimal("100"))},
            )

            plan = build_realtime_decision_plan(settings, client, state, previous_runtime=previous)

            self.assertEqual([order.side for order in plan.orders[:2]], ["ask", "bid"])
            self.assertEqual(plan.orders[0].market, "KRW-AAA")
            self.assertEqual(plan.orders[1].market, "KRW-BBB")
            self.assertIn("후보 교체", plan.orders[0].reason)

    def test_realtime_engine_splits_budget_across_multiple_live_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                risk_regime_guard_enabled=False,
                realtime_candidate_top_n=2,
                allocation_max_deploy_pct=Decimal("1"),
                allocation_max_position_pct=Decimal("1"),
                max_order_krw=Decimal("1000000"),
                realtime_max_order_pct=Decimal("1"),
                risk_min_entry_score_buffer=Decimal("0"),
            )
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "150",
                        "signed_change_rate": "0.07",
                        "acc_trade_price_24h": "9000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA"), "KRW-BBB": upward_candles("KRW-BBB", "90")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state)

            bid_orders = [order for order in plan.orders if order.side == "bid"]
            self.assertEqual(len(bid_orders), 2)
            self.assertLess(max(order.amount_krw for order in bid_orders), Decimal("900000"))
            self.assertLessEqual(sum(order.amount_krw for order in bid_orders), Decimal("1000000"))

    def test_paper_extreme_mode_targets_full_deploy_for_top_candidate(self) -> None:
        situation = RealtimeSituation(
            market="KRW-AAA",
            label="Alpha",
            strategy="guarded_momentum",
            action="buy",
            score=Decimal("0.70"),
            confidence=Decimal("1"),
            urgency=Decimal("0.10"),
            current_price=Decimal("100"),
            current_value_krw=Decimal("0"),
            learned_score=Decimal("0.50"),
            seconds_trend_pct=Decimal("0"),
            trend_1m_pct=Decimal("0.5"),
            trend_5m_pct=Decimal("1"),
            trend_30m_pct=Decimal("1"),
            day_change_pct=Decimal("2"),
            volatility_pct=Decimal("1"),
            drawdown_pct=Decimal("0"),
            volume_ratio=Decimal("3"),
            trade_pressure=Decimal("2"),
            tags=("profit-pattern",),
            reason="test",
        )
        weak_regime = MarketRegimeSignal(
            label="weak",
            block_new_entries=True,
            min_score_adjustment=Decimal("0.2"),
            deploy_multiplier=Decimal("0.7"),
        )
        settings = TradingSettings(
            allocation_max_deploy_pct=Decimal("1"),
            allocation_max_position_pct=Decimal("1"),
            paper_extreme_mode=True,
        )

        targets = realtime_entry_target_values(
            settings,
            (situation,),
            Decimal("1000000"),
            weak_regime,
            neutral_goal_pace_pressure(),
        )

        self.assertEqual(targets["KRW-AAA"], Decimal("1000000"))

    def test_paper_extreme_mode_is_ignored_when_live_flags_are_enabled(self) -> None:
        situation = RealtimeSituation(
            market="KRW-AAA",
            label="Alpha",
            strategy="guarded_momentum",
            action="buy",
            score=Decimal("0.70"),
            confidence=Decimal("1"),
            urgency=Decimal("0.10"),
            current_price=Decimal("100"),
            current_value_krw=Decimal("0"),
            learned_score=Decimal("0.50"),
            seconds_trend_pct=Decimal("0"),
            trend_1m_pct=Decimal("0.5"),
            trend_5m_pct=Decimal("1"),
            trend_30m_pct=Decimal("1"),
            day_change_pct=Decimal("2"),
            volatility_pct=Decimal("1"),
            drawdown_pct=Decimal("0"),
            volume_ratio=Decimal("3"),
            trade_pressure=Decimal("2"),
            tags=("profit-pattern",),
            reason="test",
        )
        settings = TradingSettings(
            allocation_max_deploy_pct=Decimal("1"),
            allocation_max_position_pct=Decimal("1"),
            paper_extreme_mode=True,
            live_trading_enabled=True,
        )

        targets = realtime_entry_target_values(
            settings,
            (situation,),
            Decimal("1000000"),
            MarketRegimeSignal(),
            neutral_goal_pace_pressure(),
        )

        self.assertEqual(targets["KRW-AAA"], Decimal("650000.00"))

    def test_paper_extreme_mode_forces_volatility_probe_when_guards_leave_no_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                paper_extreme_mode=True,
                realtime_weak_breakout_enabled=False,
                realtime_recovery_scout_enabled=False,
                risk_regime_guard_enabled=True,
                risk_regime_min_market_count=2,
                risk_regime_min_positive_ratio=Decimal("0.75"),
                risk_regime_soft_positive_ratio=Decimal("0.85"),
                risk_regime_min_avg_trend_pct=Decimal("-99"),
                risk_market_min_trade_value_24h_krw=Decimal("999999999999"),
                risk_min_candle_trade_value_krw=Decimal("999999999999"),
                risk_min_trade_pressure=Decimal("-4"),
                risk_chase_5m_rise_pct=Decimal("10"),
                risk_chase_30m_rise_pct=Decimal("20"),
                max_order_krw=Decimal("1000000"),
                realtime_max_order_pct=Decimal("1"),
                allocation_max_deploy_pct=Decimal("1"),
                allocation_max_position_pct=Decimal("1"),
                allocation_max_orders_per_run=3,
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Alpha",
                            "score": "2.20",
                        }
                    },
                },
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "120",
                        "signed_change_rate": "0.03",
                        "acc_trade_price_24h": "10000000000",
                        "trade_pressure": "3",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                },
                {"KRW-AAA": surge_candles("KRW-AAA"), "KRW-BBB": flat_candles("KRW-BBB", "100")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.selected[0].market, "KRW-AAA")
            self.assertEqual(plan.selected[0].action, "buy")
            self.assertIn("volatility-probe", plan.selected[0].tags)
            self.assertEqual(plan.orders[0].side, "bid")
            self.assertEqual(plan.orders[0].amount_krw, Decimal("999500"))
            self.assertIn("volatility probe", plan.orders[0].reason)

    def test_realtime_engine_exits_stagnant_low_volatility_holding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                risk_regime_guard_enabled=False,
                realtime_low_volatility_pct=Decimal("0.05"),
                realtime_stagnation_exit_seconds=60,
            )
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": quiet_candles("KRW-AAA", "100")},
            )
            state = PortfolioState(
                cash_krw=Decimal("100000"),
                positions={"KRW-AAA": PortfolioPosition(volume=Decimal("100"), avg_entry_price=Decimal("100"))},
                last_order_by_market={
                    "KRW-AAA": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
                },
            )

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.orders[0].side, "ask")
            self.assertIn("저변동 장기 보유 정리", plan.situations[0].tags)

    def test_realtime_engine_exits_idle_holding_when_profit_is_too_small(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                risk_regime_guard_enabled=False,
                realtime_idle_exit_seconds=60,
                realtime_idle_exit_return_pct=Decimal("0.30"),
                realtime_idle_exit_trend_pct=Decimal("0.50"),
                risk_market_min_trade_value_24h_krw=Decimal("999999999999"),
            )
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "100.1",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": quiet_candles("KRW-AAA", "100.1")},
            )
            state = PortfolioState(
                cash_krw=Decimal("100000"),
                positions={"KRW-AAA": PortfolioPosition(volume=Decimal("100"), avg_entry_price=Decimal("100"))},
                last_order_by_market={
                    "KRW-AAA": (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat()
                },
            )

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.orders[0].side, "ask")
            self.assertIn("기회비용 시간정리", plan.situations[0].tags)

    def test_realtime_engine_allows_small_recovery_scout_after_global_loss_streak(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = replace(
                settings_for(temp_dir),
                realtime_weak_breakout_enabled=True,
                realtime_recovery_scout_enabled=True,
                realtime_recovery_scout_max_position_pct=Decimal("0.12"),
                realtime_weak_breakout_score_buffer=Decimal("0.10"),
                risk_regime_guard_enabled=True,
                risk_regime_min_market_count=2,
                risk_regime_min_positive_ratio=Decimal("0.75"),
                risk_regime_soft_positive_ratio=Decimal("0.85"),
                risk_regime_min_avg_trend_pct=Decimal("-99"),
                risk_market_min_trade_value_24h_krw=Decimal("999999999999"),
                risk_min_candle_trade_value_krw=Decimal("999999999999"),
                risk_min_trade_pressure=Decimal("-4"),
                risk_chase_5m_rise_pct=Decimal("10"),
                risk_chase_30m_rise_pct=Decimal("20"),
                max_order_krw=Decimal("1000000"),
                realtime_max_order_pct=Decimal("1"),
                allocation_max_deploy_pct=Decimal("1"),
                allocation_max_position_pct=Decimal("1"),
            )
            save_learning_model(
                settings,
                {
                    "version": 1,
                    "markets": {
                        "KRW-AAA": {
                            "market": "KRW-AAA",
                            "bestStrategy": "guarded_momentum",
                            "label": "Alpha",
                            "score": "2.20",
                        }
                    },
                },
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "120",
                        "signed_change_rate": "0.03",
                        "acc_trade_price_24h": "10000000000",
                        "trade_pressure": "3",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "100",
                        "signed_change_rate": "0",
                        "acc_trade_price_24h": "10000000000",
                    },
                },
                {"KRW-AAA": surge_candles("KRW-AAA"), "KRW-BBB": flat_candles("KRW-BBB", "100")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state)

            self.assertEqual(plan.selected[0].market, "KRW-AAA")
            self.assertEqual(plan.orders[0].side, "bid")
            self.assertLessEqual(plan.orders[0].amount_krw, Decimal("120000"))
            self.assertIn("약세장 예외 돌파", plan.selected[0].tags)

    def test_manual_recommended_market_scope_limits_realtime_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                    "KRW-BBB": {
                        "market": "KRW-BBB",
                        "trade_price": "110",
                        "signed_change_rate": "0.07",
                        "acc_trade_price_24h": "9000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA"), "KRW-BBB": upward_candles("KRW-BBB", "50")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, candidate_markets=("KRW-BBB",))

            self.assertEqual({situation.market for situation in plan.situations}, {"KRW-BBB"})
            self.assertTrue(all(order.market == "KRW-BBB" for order in plan.orders))

    def test_empty_manual_scope_does_not_fall_back_to_realtime_universe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    },
                },
                {"KRW-AAA": upward_candles("KRW-AAA")},
            )
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, candidate_markets=())

            self.assertEqual(plan.universe_count, 0)
            self.assertEqual(plan.evaluated_count, 0)
            self.assertEqual(plan.orders, ())

    def test_realtime_engine_avoids_entry_matching_loss_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = settings_for(temp_dir)
            save_model(settings)
            raw_candles = upward_candles("KRW-AAA")
            candles = [Candle.from_upbit(row) for row in raw_candles]
            save_pattern_model(
                settings,
                build_pattern_model(
                    [
                        PatternObservation(
                            market="KRW-AAA",
                            strategy="guarded_momentum",
                            entry_time="2026-01-01T09:30:00",
                            exit_time="2026-01-01T09:45:00",
                            entry_price=Decimal("145"),
                            exit_price=Decimal("135"),
                            net_return_pct=Decimal("-7.1"),
                            outcome="loss",
                            features=feature_snapshot(candles),
                        )
                    ]
                ),
            )
            client = FakeRealtimeClient(
                {
                    "KRW-AAA": {
                        "market": "KRW-AAA",
                        "trade_price": "160",
                        "signed_change_rate": "0.08",
                        "acc_trade_price_24h": "10000000000",
                    }
                },
                {"KRW-AAA": raw_candles},
            )
            now = datetime.now(timezone.utc)
            previous = {
                "history": {
                    "KRW-AAA": [
                        {"time": (now - timedelta(seconds=40)).isoformat(), "price": "150"},
                    ]
                }
            }
            state = PortfolioState(cash_krw=Decimal("1000000"), positions={})

            plan = build_realtime_decision_plan(settings, client, state, previous_runtime=previous)

            self.assertEqual(plan.selected, ())
            self.assertEqual(plan.orders, ())
            self.assertIn("loss-pattern", plan.situations[0].tags)


if __name__ == "__main__":
    unittest.main()
