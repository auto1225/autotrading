from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.market_regime import evaluate_market_regime
from upbit_autotrader.models import Candle


def candle(market: str, price: str, timestamp: int) -> Candle:
    value = Decimal(price)
    return Candle(
        market=market,
        candle_date_time_utc=f"2026-01-01T00:{timestamp:02d}:00",
        candle_date_time_kst=f"2026-01-01T09:{timestamp:02d}:00",
        opening_price=value,
        high_price=value + Decimal("1"),
        low_price=value - Decimal("1"),
        trade_price=value,
        timestamp=timestamp,
        candle_acc_trade_price=Decimal("100000000"),
        candle_acc_trade_volume=Decimal("10"),
    )


def series(market: str, start: int, step: int, count: int = 20) -> list[Candle]:
    return [candle(market, str(start + index * step), index) for index in range(count)]


class MarketRegimeTests(unittest.TestCase):
    def test_broad_downtrend_blocks_new_entries(self) -> None:
        settings = TradingSettings(
            risk_regime_min_market_count=3,
            risk_regime_min_positive_ratio=Decimal("0.40"),
            risk_regime_max_crash_ratio=Decimal("0.25"),
            risk_regime_min_avg_trend_pct=Decimal("-1.0"),
        )

        signal = evaluate_market_regime(
            settings,
            {
                "KRW-AAA": series("KRW-AAA", 200, -3),
                "KRW-BBB": series("KRW-BBB", 180, -2),
                "KRW-CCC": series("KRW-CCC", 160, -2),
            },
        )

        self.assertEqual(signal.label, "risk-off")
        self.assertTrue(signal.block_new_entries)
        self.assertEqual(signal.deploy_multiplier, Decimal("0"))

    def test_broad_uptrend_allows_entries(self) -> None:
        settings = TradingSettings(risk_regime_min_market_count=3)

        signal = evaluate_market_regime(
            settings,
            {
                "KRW-AAA": series("KRW-AAA", 100, 2),
                "KRW-BBB": series("KRW-BBB", 200, 1),
                "KRW-CCC": series("KRW-CCC", 300, 1),
            },
        )

        self.assertEqual(signal.label, "risk-on")
        self.assertFalse(signal.block_new_entries)
        self.assertGreater(signal.score_adjustment, Decimal("0"))

    def test_narrow_positive_breadth_blocks_new_entries(self) -> None:
        settings = TradingSettings(
            risk_regime_min_market_count=3,
            risk_regime_min_positive_ratio=Decimal("0.50"),
            risk_regime_min_avg_trend_pct=Decimal("-1.0"),
        )

        signal = evaluate_market_regime(
            settings,
            {
                "KRW-AAA": series("KRW-AAA", 100, 2),
                "KRW-BBB": series("KRW-BBB", 200, 0),
                "KRW-CCC": series("KRW-CCC", 300, 0),
            },
        )

        self.assertEqual(signal.label, "weak")
        self.assertTrue(signal.block_new_entries)
        self.assertEqual(signal.deploy_multiplier, Decimal("0.85"))
        self.assertIn("market-narrow-breadth", signal.tags)


if __name__ == "__main__":
    unittest.main()
