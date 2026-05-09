from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.learning import (
    fetch_historical_candles,
    krw_market_codes,
    load_learning_model,
    run_historical_learning,
    save_learning_model,
)


def candle_payload(price: str, timestamp: int, market: str = "KRW-BTC") -> dict[str, Any]:
    value = Decimal(price)
    return {
        "market": market,
        "candle_date_time_utc": f"2026-01-01T00:{timestamp:04d}:00",
        "candle_date_time_kst": f"2026-01-01T09:{timestamp:04d}:00",
        "opening_price": str(value),
        "high_price": str(value + Decimal("1")),
        "low_price": str(value - Decimal("1")),
        "trade_price": str(value),
        "timestamp": timestamp,
        "candle_acc_trade_price": str(value * Decimal("10")),
        "candle_acc_trade_volume": "10",
    }


class FakeCandleClient:
    def __init__(self, candles: list[dict[str, Any]]) -> None:
        self.candles = sorted(candles, key=lambda row: int(row["timestamp"]), reverse=True)

    def get_markets(self, is_details: bool = False) -> list[dict[str, Any]]:
        return [
            {"market": "KRW-BTC", "market_event": {"warning": False, "caution": {}}},
            {"market": "KRW-WARN", "market_event": {"warning": True, "caution": {}}},
            {"market": "BTC-ETH", "market_event": {"warning": False, "caution": {}}},
            {"market": "KRW-XRP", "market_event": {"warning": False, "caution": {}}},
        ]

    def get_minute_candles(
        self,
        market: str,
        unit: int = 5,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = [row for row in self.candles if row["market"] == market]
        if to is not None:
            rows = [row for row in rows if str(row["candle_date_time_utc"]) < to]
        return rows[:count]


class LearningTests(unittest.TestCase):
    def test_fetch_historical_candles_deduplicates_and_orders_recent_first(self) -> None:
        settings = TradingSettings(short_window=2, long_window=5, learning_candle_count=60)
        client = FakeCandleClient([candle_payload(str(100 + index), index) for index in range(1, 31)])

        candles = fetch_historical_candles(client, settings, "KRW-BTC", 20, pause_seconds=0)

        self.assertEqual(len(candles), 20)
        self.assertGreater(candles[0].timestamp, candles[-1].timestamp)

    def test_krw_market_codes_can_exclude_warning_markets_and_limit_count(self) -> None:
        client = FakeCandleClient([])

        markets = krw_market_codes(client, exclude_warnings=True, max_markets=1)

        self.assertEqual(markets, ("KRW-BTC",))

    def test_historical_learning_builds_market_recommendation_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                short_window=2,
                long_window=5,
                markets=("KRW-BTC",),
                market="KRW-BTC",
                state_file=Path(temp_dir) / "paper_state.json",
                learning_candle_count=60,
            )
            client = FakeCandleClient([candle_payload(str(100 + index), index) for index in range(1, 61)])

            result = run_historical_learning(
                settings,
                client,
                count=60,
                strategy_names=("sma_cross", "guarded_momentum"),
            )
            model = result.to_model()
            save_learning_model(settings, model)

            self.assertEqual(model["marketCount"], 1)
            self.assertEqual(model["scope"], "watchlist")
            self.assertEqual(model["requestedMarketCount"], 1)
            self.assertIn("KRW-BTC", model["markets"])
            self.assertIn(model["markets"]["KRW-BTC"]["bestStrategy"], {"sma_cross", "guarded_momentum"})
            self.assertEqual(load_learning_model(settings)["version"], 1)


if __name__ == "__main__":
    unittest.main()
