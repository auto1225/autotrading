from __future__ import annotations

from decimal import Decimal
import unittest

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.models import Candle
from upbit_autotrader.trade_levels import chart_trade_levels


def candle(market: str, index: int, price: Decimal, low: Decimal | None = None, high: Decimal | None = None) -> Candle:
    low = low if low is not None else price - Decimal("1")
    high = high if high is not None else price + Decimal("1")
    return Candle(
        market=market,
        candle_date_time_utc=f"2026-01-01T00:{index:02d}:00",
        candle_date_time_kst=f"2026-01-01T09:{index:02d}:00",
        opening_price=price - Decimal("0.4"),
        high_price=high,
        low_price=low,
        trade_price=price,
        timestamp=index,
        candle_acc_trade_price=Decimal("10000000") + Decimal(index * 100000),
        candle_acc_trade_volume=Decimal("1000") + Decimal(index),
    )


class TradeLevelsTests(unittest.TestCase):
    def test_levels_use_chart_support_resistance_and_atr(self) -> None:
        settings = TradingSettings(stop_loss_pct=Decimal("3"), take_profit_pct=Decimal("6"))
        candles = [
            candle("KRW-AAA", index, Decimal("100") + Decimal(index) / Decimal("5"))
            for index in range(1, 50)
        ]
        candles[-6] = candle("KRW-AAA", 44, Decimal("106"), low=Decimal("96"), high=Decimal("107"))
        candles[-1] = candle("KRW-AAA", 49, Decimal("110"), low=Decimal("108"), high=Decimal("112"))

        levels = chart_trade_levels(settings, candles, current_price=Decimal("110"), avg_entry_price=Decimal("100"), held=True)

        self.assertEqual(levels.market, "KRW-AAA")
        self.assertGreater(levels.take_profit_price, Decimal("110"))
        self.assertLess(levels.stop_loss_price, Decimal("110"))
        self.assertGreater(levels.risk_reward, Decimal("1"))
        self.assertEqual(levels.method, "chart_atr_vwap_sr")

    def test_empty_levels_fall_back_to_fixed_percentages(self) -> None:
        settings = TradingSettings(stop_loss_pct=Decimal("3"), take_profit_pct=Decimal("6"))

        levels = chart_trade_levels(settings, [], current_price=Decimal("100"), avg_entry_price=Decimal("100"), held=True)

        self.assertEqual(levels.stop_loss_price, Decimal("97"))
        self.assertEqual(levels.take_profit_price, Decimal("106"))
        self.assertEqual(levels.method, "fixed_fallback")


if __name__ == "__main__":
    unittest.main()
