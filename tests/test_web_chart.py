from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.models import Candle
from upbit_autotrader.config import TradingSettings
from upbit_autotrader.backtest import run_backtest
from upbit_autotrader.state import PortfolioPosition, PortfolioState
from upbit_autotrader.web import (
    chart_payload,
    chart_frame_label,
    complete_portfolio_prices,
    fetch_chart_candles,
    latest_range_simulation_payload,
    load_market_preferences,
    load_recommended_markets,
    market_rows_payload,
    normalize_chart_count,
    normalize_chart_frame,
    normalize_recommended_market,
    portfolio_chart_payload,
    portfolio_display_markets,
    price_map,
    realtime_decision_candidate_markets,
    recommended_investment_markets,
    recommendation_payload,
    save_market_preferences,
    save_recommended_markets,
    simulation_playback_payload,
)


def candle(price: str, timestamp: int) -> Candle:
    value = Decimal(price)
    return Candle(
        market="KRW-BTC",
        candle_date_time_utc=f"2026-01-01T00:{timestamp:02d}:00",
        candle_date_time_kst=f"2026-01-01T09:{timestamp:02d}:00",
        opening_price=value - Decimal("1"),
        high_price=value + Decimal("2"),
        low_price=value - Decimal("2"),
        trade_price=value,
        timestamp=timestamp,
        candle_acc_trade_price=value * Decimal("10"),
        candle_acc_trade_volume=Decimal("10"),
    )


def upbit_candle(price: str, timestamp: int = 1) -> dict[str, object]:
    value = Decimal(price)
    return {
        "market": "KRW-BTC",
        "candle_date_time_utc": f"2026-01-01T00:{timestamp:02d}:00",
        "candle_date_time_kst": f"2026-01-01T09:{timestamp:02d}:00",
        "opening_price": str(value - Decimal("1")),
        "high_price": str(value + Decimal("2")),
        "low_price": str(value - Decimal("2")),
        "trade_price": str(value),
        "timestamp": timestamp,
        "candle_acc_trade_price": str(value * Decimal("10")),
        "candle_acc_trade_volume": "10",
    }


class FakeChartClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def get_minute_candles(self, market: str, unit: int, count: int, to: str | None = None) -> list[dict[str, object]]:
        self.calls.append((f"minute-{unit}", market, count))
        return [upbit_candle("100")]

    def get_day_candles(self, market: str, count: int, to: str | None = None) -> list[dict[str, object]]:
        self.calls.append(("day", market, count))
        return [upbit_candle("101")]

    def get_week_candles(self, market: str, count: int, to: str | None = None) -> list[dict[str, object]]:
        self.calls.append(("week", market, count))
        return [upbit_candle("102")]

    def get_month_candles(self, market: str, count: int, to: str | None = None) -> list[dict[str, object]]:
        self.calls.append(("month", market, count))
        return [upbit_candle("103")]

    def get_year_candles(self, market: str, count: int, to: str | None = None) -> list[dict[str, object]]:
        self.calls.append(("year", market, count))
        return [upbit_candle("104")]


class FakeKrwMarketClient:
    def get_markets(self, is_details: bool = False) -> list[dict[str, object]]:
        return [
            {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
            {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
            {"market": "KRW-XRP", "korean_name": "리플", "english_name": "XRP"},
            {"market": "KRW-DOGE", "korean_name": "도지코인", "english_name": "Dogecoin"},
            {"market": "BTC-USDT", "korean_name": "테더", "english_name": "Tether"},
        ]


class WebChartTests(unittest.TestCase):
    def test_chart_payload_contains_ohlcv_and_moving_averages(self) -> None:
        payload = chart_payload([candle(str(value), value) for value in range(1, 6)], 2, 3)

        self.assertEqual(payload[-1]["open"], "4")
        self.assertEqual(payload[-1]["high"], "7")
        self.assertEqual(payload[-1]["low"], "3")
        self.assertEqual(payload[-1]["close"], "5")
        self.assertEqual(payload[-1]["volume"], "10")
        self.assertEqual(payload[-1]["maShort"], "4.5")
        self.assertEqual(payload[-1]["maLong"], "4")

    def test_chart_payload_keeps_full_history_for_pan(self) -> None:
        payload = chart_payload([candle(str(value), value) for value in range(1, 121)], 5, 20)

        self.assertEqual(len(payload), 120)
        self.assertEqual(payload[0]["close"], "1")
        self.assertEqual(payload[-1]["close"], "120")

    def test_portfolio_chart_payload_buckets_total_equity_like_candles(self) -> None:
        snapshots = [
            {
                "time": "2026-05-05T00:00:10+00:00",
                "positionValueKrw": "100000",
                "cashKrw": "900000",
                "equityKrw": "1000000",
                "realizedPnlKrw": "0",
                "feesPaidKrw": "0",
                "pricePnlKrw": "0",
                "openFeesPaidKrw": "0",
                "closeFeesPaidKrw": "0",
                "orderCount": 1,
                "openPositions": 1,
                "payload": {"source": "realtime_decision"},
            },
            {
                "time": "2026-05-05T00:00:40+00:00",
                "positionValueKrw": "140000",
                "cashKrw": "860000",
                "equityKrw": "1010000",
                "realizedPnlKrw": "0",
                "feesPaidKrw": "0",
                "pricePnlKrw": "10000",
                "openFeesPaidKrw": "4",
                "closeFeesPaidKrw": "0",
                "orderCount": 2,
                "openPositions": 1,
                "payload": {"source": "realtime_decision"},
            },
            {
                "time": "2026-05-05T00:01:05+00:00",
                "positionValueKrw": "130000",
                "cashKrw": "875000",
                "equityKrw": "1005000",
                "realizedPnlKrw": "1000",
                "feesPaidKrw": "10",
                "pricePnlKrw": "1200",
                "openFeesPaidKrw": "6",
                "closeFeesPaidKrw": "4",
                "orderCount": 3,
                "openPositions": 2,
                "payload": {"source": "dynamic_allocation"},
            },
        ]

        payload = portfolio_chart_payload(snapshots, "1", short_window=2, long_window=3, count=10)

        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["open"], "1000000")
        self.assertEqual(payload[0]["high"], "1010000")
        self.assertEqual(payload[0]["low"], "1000000")
        self.assertEqual(payload[0]["close"], "1010000")
        self.assertEqual(payload[0]["volume"], "10000")
        self.assertEqual(payload[0]["positionValueKrw"], "140000")
        self.assertEqual(payload[1]["close"], "1005000")
        self.assertEqual(payload[1]["volume"], "5000")
        self.assertEqual(payload[1]["equityKrw"], "1005000")
        self.assertEqual(payload[1]["cashKrw"], "875000")
        self.assertEqual(payload[1]["realizedPnlKrw"], "1000")
        self.assertEqual(payload[1]["pricePnlKrw"], "1200")
        self.assertEqual(payload[1]["openFeesPaidKrw"], "6")
        self.assertEqual(payload[1]["closeFeesPaidKrw"], "4")
        self.assertEqual(payload[1]["feesPaidKrw"], "10")
        self.assertEqual(payload[1]["openPositions"], "2")
        self.assertEqual(payload[1]["source"], "dynamic_allocation")

    def test_complete_portfolio_prices_uses_entry_price_when_snapshot_price_is_missing(self) -> None:
        state = PortfolioState(
            cash_krw=Decimal("500000"),
            positions={"KRW-AAA": PortfolioPosition(volume=Decimal("10"), avg_entry_price=Decimal("123"))},
        )

        with patch("upbit_autotrader.web.make_client", side_effect=RuntimeError("offline")):
            prices = complete_portfolio_prices(TradingSettings(), state, {})

        self.assertEqual(prices["KRW-AAA"], Decimal("123"))

    def test_chart_frame_normalization_supports_upbit_periods(self) -> None:
        self.assertEqual(normalize_chart_frame("5"), "5")
        self.assertEqual(normalize_chart_frame("15m"), "15")
        self.assertEqual(normalize_chart_frame("day"), "day")
        self.assertEqual(normalize_chart_frame("weeks"), "week")
        self.assertEqual(normalize_chart_frame("월봉"), "month")
        self.assertEqual(normalize_chart_frame("years"), "year")
        self.assertEqual(chart_frame_label("240"), "4시간")
        self.assertEqual(chart_frame_label("year"), "년")
        self.assertEqual(normalize_chart_count(None, "year", 80), 40)
        self.assertEqual(normalize_chart_count(None, "day", 80), 3650)
        self.assertEqual(normalize_chart_count(999, "day", 80), 3650)
        self.assertEqual(normalize_chart_count(9999, "day", 80), 5000)

    def test_fetch_chart_candles_routes_to_selected_upbit_endpoint(self) -> None:
        client = FakeChartClient()

        minute = fetch_chart_candles(client, "KRW-BTC", "15", 120)
        day = fetch_chart_candles(client, "KRW-BTC", "day", 140)
        week = fetch_chart_candles(client, "KRW-BTC", "week", 100)
        month = fetch_chart_candles(client, "KRW-BTC", "month", 80)
        year = fetch_chart_candles(client, "KRW-BTC", "year", 60)

        self.assertEqual(client.calls, [
            ("minute-15", "KRW-BTC", 120),
            ("day", "KRW-BTC", 140),
            ("week", "KRW-BTC", 100),
            ("month", "KRW-BTC", 80),
            ("year", "KRW-BTC", 60),
        ])
        self.assertEqual([item.trade_price for item in [minute[0], day[0], week[0], month[0], year[0]]], [
            Decimal("100"),
            Decimal("101"),
            Decimal("102"),
            Decimal("103"),
            Decimal("104"),
        ])

    def test_backtest_report_contains_drawdown_and_curve(self) -> None:
        settings = TradingSettings(
            strategy_name="sma_cross",
            short_window=2,
            long_window=3,
            paper_cash_krw=Decimal("100000"),
        )
        report = run_backtest([candle(str(value), value) for value in [10, 11, 12, 11, 10, 13, 14]], settings)
        payload = report.to_dict()

        self.assertIn("maxDrawdownPct", payload)
        self.assertIn("equityCurve", payload)
        self.assertGreaterEqual(len(payload["equityCurve"]), 1)

    def test_default_settings_match_verified_trading_limits(self) -> None:
        settings = TradingSettings()

        self.assertEqual(settings.max_daily_orders, 80)
        self.assertEqual(settings.allocation_max_deploy_pct, Decimal("1"))
        self.assertEqual(settings.allocation_max_position_pct, Decimal("1"))
        self.assertEqual(settings.realtime_max_order_pct, Decimal("1"))
        self.assertEqual(settings.allocation_max_orders_per_run, 3)
        self.assertEqual(settings.allocation_interval_seconds, 300)
        self.assertEqual(settings.cooldown_seconds, 900)
        self.assertEqual(settings.max_order_krw, Decimal("100000000"))
        self.assertEqual(settings.max_position_krw, Decimal("100000000"))

    def test_latest_simulation_payload_reports_current_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            settings = TradingSettings(state_file=state_file)
            simulation_file = state_file.parent / "range_simulation_old.json"
            simulation_file.write_text(
                json.dumps(
                    {
                        "generatedAt": "2026-05-05T00:00:00+09:00",
                        "range": {
                            "startKst": "2026-04-04T00:00:00+09:00",
                            "endKst": "2026-05-05T00:00:00+09:00",
                        },
                        "universe": {"marketCount": 2, "requestedMaxMarkets": 2, "selectionMethod": "test"},
                        "assumptions": {
                            "feeRate": "0.0005",
                            "maxDailyOrders": 30,
                            "maxPositionPct": "0.25",
                            "maxDeployPct": "0.8",
                            "maxOrderPct": "0.08",
                        },
                        "portfolio": {
                            "startEquityKrw": "1000000",
                            "finalEquityKrw": "1000000",
                            "totalReturnPct": "0",
                            "realizedPnlKrw": "0",
                            "feesPaidKrw": "0",
                            "orderCount": 0,
                            "maxDrawdownPct": "0",
                            "openPositions": [],
                        },
                        "strategyPicks": [],
                    }
                ),
                encoding="utf-8",
            )

            payload = latest_range_simulation_payload(settings)

        drift_keys = {row["key"] for row in payload["settingsDrift"]}
        self.assertEqual(payload["currentModeLabel"], "최근 시뮬레이션")
        self.assertEqual(payload["currentSettings"]["maxDailyOrders"], 80)
        self.assertEqual(payload["currentSettings"]["maxDeployPct"], "1")
        self.assertEqual(drift_keys, {"maxDailyOrders", "maxPositionPct", "maxDeployPct", "maxOrderPct"})

    def test_simulation_playback_payload_uses_latest_equity_curve(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            settings = TradingSettings(state_file=state_file)
            simulation_file = state_file.parent / "day_walkforward_aggressive_20260401.json"
            simulation_file.write_text(
                json.dumps(
                    {
                        "generatedAt": "2026-05-05T00:00:00+09:00",
                        "mode": "walk_forward_aggressive_no_lookahead",
                        "range": {
                            "testStartKst": "2026-04-01T00:00:00+09:00",
                            "testEndKst": "2026-05-01T00:00:00+09:00",
                        },
                        "universe": {"marketCount": 2, "requestedMaxMarkets": 80},
                        "assumptions": {"startingCashKrw": "1000000"},
                        "portfolio": {
                            "startEquityKrw": "1000000",
                            "finalEquityKrw": "1010000",
                            "totalReturnPct": "1",
                            "feesPaidKrw": "500",
                            "orderCount": 2,
                            "maxDrawdownPct": "-0.2",
                            "equityCurve": [
                                {"time": "2026-04-01T00:00:00+09:00", "equityKrw": "1000000", "cashKrw": "1000000", "openPositions": 0},
                                {"time": "2026-04-01T01:00:00+09:00", "equityKrw": "1010000", "cashKrw": "0", "openPositions": 1},
                            ],
                            "trades": [
                                {"time": "2026-04-01T00:30:00", "market": "KRW-BTC", "side": "buy", "price": "100", "budgetKrw": "1000000"}
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = simulation_playback_payload(settings)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["fileName"], "day_walkforward_aggressive_20260401.json")
        self.assertEqual(len(payload["frames"]), 2)
        self.assertEqual(payload["frames"][-1]["equityKrw"], "1010000")
        self.assertEqual(payload["trades"][0]["market"], "KRW-BTC")

    def test_status_markets_include_dynamic_allocation_positions(self) -> None:
        settings = TradingSettings(markets=("KRW-BTC",), market="KRW-BTC")
        state = PortfolioState(
            cash_krw=Decimal("100000"),
            positions={"KRW-ZBT": PortfolioPosition(volume=Decimal("10"), avg_entry_price=Decimal("100"))},
        )
        markets = portfolio_display_markets(settings, state)
        tickers = {
            "KRW-BTC": {"market": "KRW-BTC", "trade_price": "1000"},
            "KRW-ZBT": {"market": "KRW-ZBT", "trade_price": "120"},
        }

        prices = price_map(markets, tickers)
        rows = market_rows_payload(markets, settings, tickers, state, prices)

        self.assertEqual(markets, ("KRW-BTC", "KRW-ZBT"))
        self.assertEqual(prices["KRW-ZBT"], Decimal("120"))
        self.assertEqual(rows[-1]["market"], "KRW-ZBT")
        self.assertEqual(rows[-1]["status"], "보유")
        self.assertEqual(rows[-1]["positionValueKrw"], "1200")
        self.assertEqual(rows[-1]["avgEntryPrice"], "100")
        self.assertEqual(rows[-1]["targetSellPrice"], "106")
        self.assertEqual(rows[-1]["stopLossPrice"], "97")
        self.assertIn("analysis", rows[-1])
        self.assertIn("목표가", rows[-1]["analysis"]["narrative"])

    def test_recommended_markets_are_persisted_and_marked_in_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-BTC", "KRW-ETH"),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
            )
            saved = save_recommended_markets(settings, ["btc", "KRW-ETH", "KRW-BTC"])

            self.assertEqual(saved, ("KRW-BTC", "KRW-ETH"))
            self.assertEqual(load_recommended_markets(settings), saved)
            self.assertEqual(normalize_recommended_market("xrp"), "KRW-XRP")
            self.assertTrue(recommendation_payload(settings)["active"])

            state = PortfolioState(cash_krw=Decimal("0"), positions={})
            rows = market_rows_payload(
                ("KRW-BTC", "KRW-ETH"),
                settings,
                {},
                state,
                {"KRW-BTC": Decimal("100"), "KRW-ETH": Decimal("200")},
                recommended_markets=saved,
            )

            self.assertTrue(all(row["recommended"] for row in rows))
            self.assertFalse(any(row["excluded"] for row in rows))

    def test_market_preferences_persist_excluded_and_recommend_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-BTC", "KRW-ETH", "KRW-XRP"),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
            )

            saved = save_market_preferences(
                settings,
                markets=["KRW-BTC", "eth"],
                excluded_markets=["KRW-XRP", "KRW-BTC"],
                recommend_only=True,
            )
            loaded = load_market_preferences(settings)

            self.assertEqual(saved["markets"], ("KRW-BTC", "KRW-ETH"))
            self.assertEqual(saved["excludedMarkets"], ("KRW-XRP",))
            self.assertTrue(saved["recommendOnly"])
            self.assertEqual(loaded, saved)

            state = PortfolioState(cash_krw=Decimal("0"), positions={})
            rows = market_rows_payload(
                ("KRW-BTC", "KRW-ETH", "KRW-XRP"),
                settings,
                {},
                state,
                {"KRW-BTC": Decimal("100"), "KRW-ETH": Decimal("200"), "KRW-XRP": Decimal("300")},
                recommended_markets=saved["markets"],
                excluded_markets=saved["excludedMarkets"],
            )

            by_market = {row["market"]: row for row in rows}
            self.assertTrue(by_market["KRW-BTC"]["recommended"])
            self.assertTrue(by_market["KRW-XRP"]["excluded"])
            payload = recommendation_payload(settings, saved)
            self.assertTrue(payload["recommendOnly"])
            self.assertEqual(payload["excludedCount"], 1)

    def test_recommended_investment_markets_keeps_held_positions_for_exit_management(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-BTC",),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
            )
            state = PortfolioState(
                cash_krw=Decimal("0"),
                positions={"KRW-OLD": PortfolioPosition(volume=Decimal("2"), avg_entry_price=Decimal("100"))}
            )

            markets = recommended_investment_markets(settings, state, ("KRW-BTC",))

        self.assertEqual(markets, ("KRW-BTC", "KRW-OLD"))

    def test_preference_candidates_exclude_blocked_markets_unless_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-BTC", "KRW-ETH", "KRW-XRP"),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
            )
            state = PortfolioState(
                cash_krw=Decimal("0"),
                positions={"KRW-XRP": PortfolioPosition(volume=Decimal("2"), avg_entry_price=Decimal("100"))},
            )

            markets = recommended_investment_markets(
                settings,
                state,
                {"markets": (), "excludedMarkets": ("KRW-ETH", "KRW-XRP"), "recommendOnly": False},
            )

            self.assertEqual(markets, ("KRW-BTC", "KRW-XRP"))

    def test_recommend_priority_without_recommendations_uses_default_universe(self) -> None:
        settings = TradingSettings(markets=("KRW-BTC", "KRW-ETH"), market="KRW-BTC")
        state = PortfolioState(cash_krw=Decimal("0"), positions={})

        markets = recommended_investment_markets(
            settings,
            state,
            {"markets": (), "excludedMarkets": (), "recommendOnly": True},
        )

        self.assertIsNone(markets)

    def test_recommend_priority_keeps_full_universe_for_better_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-BTC", "KRW-ETH", "KRW-XRP"),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
            )
            state = PortfolioState(
                cash_krw=Decimal("0"),
                positions={"KRW-OLD": PortfolioPosition(volume=Decimal("2"), avg_entry_price=Decimal("100"))},
            )

            markets = recommended_investment_markets(
                settings,
                state,
                {"markets": ("KRW-ETH",), "excludedMarkets": (), "recommendOnly": True},
            )

        self.assertEqual(markets, ("KRW-ETH", "KRW-BTC", "KRW-XRP", "KRW-OLD"))

    def test_realtime_decision_candidates_use_all_krw_markets_not_watch_top_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-BTC",),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
                realtime_watch_top_n=1,
            )
            state = PortfolioState(
                cash_krw=Decimal("0"),
                positions={"KRW-OLD": PortfolioPosition(volume=Decimal("2"), avg_entry_price=Decimal("100"))},
            )

            markets = realtime_decision_candidate_markets(
                settings,
                FakeKrwMarketClient(),
                state,
                {"markets": ("KRW-ETH",), "excludedMarkets": ("KRW-XRP",), "recommendOnly": True},
            )

        self.assertEqual(markets, ("KRW-ETH", "KRW-BTC", "KRW-DOGE", "KRW-OLD"))


if __name__ == "__main__":
    unittest.main()
