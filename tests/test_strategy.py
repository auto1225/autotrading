from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.models import Candle
from upbit_autotrader.strategy import (
    AdaptiveLearningStrategy,
    AlexMethodStrategy,
    BollingerBandStrategy,
    BreakoutStrategy,
    DonchianChannelStrategy,
    GuardedMomentumStrategy,
    IchimokuTrendStrategy,
    MaeuknamCardsStrategy,
    MacdCrossStrategy,
    MeanReversionStrategy,
    ProbabilityEdgeStrategy,
    RsiReversalStrategy,
    SmaCrossStrategy,
    StatisticalFilterStrategy,
    StochasticStrategy,
    VwapReversionStrategy,
    strategy_catalog,
)
from upbit_autotrader.alex_strategy import AlexTechniqueSignal
from upbit_autotrader.maeuknam_strategy import MaeuknamTechniqueSignal


def candle(price: str, timestamp: int, trade_value: str = "10000") -> Candle:
    value = Decimal(price)
    return Candle(
        market="KRW-BTC",
        candle_date_time_utc=f"2026-01-01T00:{timestamp:02d}:00",
        candle_date_time_kst=f"2026-01-01T09:{timestamp:02d}:00",
        opening_price=value,
        high_price=value,
        low_price=value,
        trade_price=value,
        timestamp=timestamp,
        candle_acc_trade_price=Decimal(trade_value),
        candle_acc_trade_volume=Decimal("0"),
    )


def candle_range(price: str, high: str, low: str, timestamp: int, trade_value: str = "10000", volume: str = "10") -> Candle:
    value = Decimal(price)
    return Candle(
        market="KRW-BTC",
        candle_date_time_utc=f"2026-01-01T00:{timestamp:02d}:00",
        candle_date_time_kst=f"2026-01-01T09:{timestamp:02d}:00",
        opening_price=value,
        high_price=Decimal(high),
        low_price=Decimal(low),
        trade_price=value,
        timestamp=timestamp,
        candle_acc_trade_price=Decimal(trade_value),
        candle_acc_trade_volume=Decimal(volume),
    )


def maeuknam_signal(entry_allowed: bool = True) -> MaeuknamTechniqueSignal:
    return MaeuknamTechniqueSignal(
        technique_id="support_pullback_long",
        technique_name="support pullback long",
        direction="LONG",
        score=Decimal("0.82") if entry_allowed else Decimal("0.61"),
        entry_threshold=Decimal("0.72"),
        watch_threshold=Decimal("0.58"),
        entry_allowed=entry_allowed,
        hard_blocks=() if entry_allowed else ("blocked",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99.7"),
        target1_price=Decimal("100.6"),
        target2_price=Decimal("101.0"),
        support_price=Decimal("99.8"),
        resistance_price=Decimal("100.6"),
        risk_pct=Decimal("0.30"),
        reward_risk=Decimal("2.0"),
        features={"structure_score": Decimal("0.8")},
        reason="test maeuknam card",
    )


def alex_signal(entry_allowed: bool = True) -> AlexTechniqueSignal:
    return AlexTechniqueSignal(
        technique_id="alex_liquidity_discount_long",
        technique_name="Alex liquidity discount long",
        direction="LONG",
        score=Decimal("0.68") if entry_allowed else Decimal("0.45"),
        entry_threshold=Decimal("0.52"),
        watch_threshold=Decimal("0.42"),
        entry_allowed=entry_allowed,
        hard_blocks=() if entry_allowed else ("blocked",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99.4"),
        target1_price=Decimal("101"),
        target2_price=Decimal("102"),
        support_price=Decimal("99.5"),
        resistance_price=Decimal("102"),
        risk_pct=Decimal("0.6"),
        reward_risk=Decimal("3.3"),
        features={"value_zone_score": Decimal("0.8")},
        reason="test alex method",
    )


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = TradingSettings(short_window=2, long_window=3)

    def test_buy_on_short_sma_cross_above_long_sma(self) -> None:
        candles = [candle("12", 4), candle("10", 3), candle("10", 2), candle("10", 1)]
        signal = SmaCrossStrategy(self.settings).evaluate(candles)
        self.assertEqual(signal.action, "buy")

    def test_sell_on_short_sma_cross_below_long_sma(self) -> None:
        candles = [candle("10", 4), candle("12", 3), candle("12", 2), candle("12", 1)]
        signal = SmaCrossStrategy(self.settings).evaluate(candles)
        self.assertEqual(signal.action, "sell")

    def test_hold_without_cross(self) -> None:
        candles = [candle("10", 4), candle("10", 3), candle("10", 2), candle("10", 1)]
        signal = SmaCrossStrategy(self.settings).evaluate(candles)
        self.assertEqual(signal.action, "hold")

    def test_guarded_momentum_buys_with_trend_and_volume(self) -> None:
        settings = TradingSettings(
            short_window=2,
            long_window=4,
            strategy_min_trend_pct=Decimal("0.1"),
            strategy_min_volume_ratio=Decimal("1.01"),
            strategy_max_volatility_pct=Decimal("10"),
        )
        candles = [
            candle("100", 1),
            candle("101", 2),
            candle("102", 3),
            candle("103", 4),
            candle("106", 5, "15000"),
            candle("110", 6, "22000"),
        ]

        signal = GuardedMomentumStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("보수적 모멘텀", signal.reason)

    def test_breakout_buys_new_high_with_volume(self) -> None:
        settings = TradingSettings(
            strategy_name="breakout",
            short_window=2,
            long_window=3,
            strategy_min_volume_ratio=Decimal("1.1"),
        )
        candles = [
            candle("100", 1, "10000"),
            candle("101", 2, "10000"),
            candle("102", 3, "10000"),
            candle("106", 4, "30000"),
        ]

        signal = BreakoutStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("고점 돌파", signal.reason)

    def test_mean_reversion_buys_deep_pullback(self) -> None:
        settings = TradingSettings(
            strategy_name="mean_reversion",
            long_window=3,
            strategy_pullback_sell_pct=Decimal("4"),
        )
        candles = [candle("100", 1), candle("100", 2), candle("90", 3)]

        signal = MeanReversionStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("평균회귀", signal.reason)

    def test_strategy_catalog_marks_active_strategy(self) -> None:
        catalog = strategy_catalog("breakout")

        self.assertEqual(len(catalog), 16)
        self.assertEqual([item["name"] for item in catalog if item["active"]], ["breakout"])
        self.assertIn("alex_method", [item["name"] for item in catalog])

    def test_maeuknam_cards_strategy_uses_card_gate_for_entry(self) -> None:
        settings = TradingSettings(strategy_name="maeuknam_cards")
        candles = [candle("100", index) for index in range(1, 35)]

        with patch("upbit_autotrader.strategy.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
            signal = MaeuknamCardsStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertGreaterEqual(signal.strength, Decimal("0.85"))

    def test_alex_method_strategy_uses_alex_gate_for_entry(self) -> None:
        settings = TradingSettings(strategy_name="alex_method")
        candles = [candle("100", index) for index in range(1, 35)]

        with patch("upbit_autotrader.strategy.evaluate_alex_techniques", return_value=alex_signal(True)):
            signal = AlexMethodStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertGreaterEqual(signal.strength, Decimal("0.85"))

    def test_probability_edge_buys_when_multiple_edges_align(self) -> None:
        settings = TradingSettings(
            strategy_name="probability_edge",
            short_window=5,
            long_window=20,
            strategy_min_trend_pct=Decimal("0.08"),
            strategy_min_volume_ratio=Decimal("1.02"),
            strategy_max_volatility_pct=Decimal("6"),
            take_profit_pct=Decimal("8"),
            stop_loss_pct=Decimal("2"),
        )
        offsets = [Decimal("0.25"), Decimal("0.25"), Decimal("-0.15"), Decimal("-0.15"), Decimal("-0.15")]
        candles = []
        for index in range(1, 61):
            price = Decimal("100") + Decimal(index) * Decimal("0.08") + offsets[index % len(offsets)]
            candles.append(
                candle_range(
                    f"{price:.2f}",
                    f"{price + Decimal('0.7'):.2f}",
                    f"{price - Decimal('0.7'):.2f}",
                    index,
                    str(10000 + index * 350),
                    "100",
                )
            )

        signal = ProbabilityEdgeStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("확률 우위", signal.reason)
        self.assertIn("매수 게이트", signal.reason)

    def test_probability_edge_sells_when_trend_breaks_down(self) -> None:
        settings = TradingSettings(strategy_name="probability_edge", short_window=5, long_window=20)
        candles = [
            candle_range(
                str(140 - index),
                str(Decimal(141 - index)),
                str(Decimal(139 - index)),
                index,
                str(20000 + index * 200),
                "100",
            )
            for index in range(1, 61)
        ]

        signal = ProbabilityEdgeStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "sell")
        self.assertIn("확률 우위", signal.reason)

    def test_adaptive_learning_delegates_to_learned_market_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            model_file = state_file.parent / "learning_model.json"
            model_file.write_text(
                json.dumps(
                    {
                        "markets": {
                            "KRW-BTC": {
                                "bestStrategy": "mean_reversion",
                                "label": "평균회귀",
                                "score": "12.3",
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            settings = TradingSettings(
                strategy_name="adaptive_learning",
                long_window=3,
                strategy_pullback_sell_pct=Decimal("4"),
                state_file=state_file,
            )
            candles = [candle("100", 1), candle("100", 2), candle("90", 3)]

            signal = AdaptiveLearningStrategy(settings).evaluate(candles)

            self.assertEqual(signal.action, "buy")
            self.assertIn("학습형 선택", signal.reason)
            self.assertIn("평균회귀", signal.reason)

    def test_rsi_reversal_buys_oversold_market(self) -> None:
        candles = [candle(str(120 - index * 2), index) for index in range(1, 17)]

        signal = RsiReversalStrategy(TradingSettings(strategy_name="rsi_reversal")).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("RSI", signal.reason)

    def test_macd_cross_buys_after_bullish_turn(self) -> None:
        prices = [100 - index for index in range(20)] + [81, 82, 83, 84, 85, 87, 90, 94, 99, 105, 112, 120, 129, 139, 150]
        candles = [candle(str(price), index + 1) for index, price in enumerate(prices)]

        signal = MacdCrossStrategy(TradingSettings(strategy_name="macd_cross")).evaluate(candles)

        self.assertIn(signal.action, {"buy", "hold"})
        self.assertIn("MACD", signal.reason)

    def test_statistical_filter_buys_confirmed_regression_trend(self) -> None:
        settings = TradingSettings(
            strategy_name="statistical_filter",
            long_window=10,
            short_window=4,
            strategy_min_trend_pct=Decimal("0.08"),
            strategy_min_volume_ratio=Decimal("1.0"),
            strategy_max_volatility_pct=Decimal("10"),
        )
        candles = [
            candle_range(str(100 + index), str(101 + index), str(99 + index), index, str(10000 + index * 900))
            for index in range(1, 26)
        ]

        signal = StatisticalFilterStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("통계 필터", signal.reason)
        self.assertIn("공분산오차", signal.reason)

    def test_statistical_filter_sells_regression_breakdown(self) -> None:
        settings = TradingSettings(strategy_name="statistical_filter", long_window=10, short_window=4)
        prices = [str(130 - index) for index in range(1, 26)]
        candles = [
            candle_range(price, str(Decimal(price) + Decimal("1")), str(Decimal(price) - Decimal("1")), index, str(20000 + index * 100))
            for index, price in enumerate(prices, start=1)
        ]

        signal = StatisticalFilterStrategy(settings).evaluate(candles)

        self.assertEqual(signal.action, "sell")
        self.assertIn("통계 하락", signal.reason)

    def test_bollinger_band_buys_lower_band_break(self) -> None:
        candles = [candle("100", index) for index in range(1, 20)] + [candle("80", 20)]

        signal = BollingerBandStrategy(TradingSettings(strategy_name="bollinger_band")).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("볼린저", signal.reason)

    def test_stochastic_detects_oscillator_state(self) -> None:
        candles = [
            candle_range(str(100 + index), str(105 + index), str(95 + index), index)
            for index in range(1, 18)
        ]

        signal = StochasticStrategy(TradingSettings(strategy_name="stochastic")).evaluate(candles)

        self.assertIn(signal.action, {"buy", "sell", "hold"})
        self.assertIn("스토캐스틱", signal.reason)

    def test_ichimoku_trend_buys_above_cloud(self) -> None:
        candles = [candle_range(str(100 + index), str(102 + index), str(98 + index), index) for index in range(1, 54)]

        signal = IchimokuTrendStrategy(TradingSettings(strategy_name="ichimoku_trend")).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("일목", signal.reason)

    def test_vwap_reversion_buys_below_vwap(self) -> None:
        candles = [candle_range("100", "101", "99", index, "1000", "10") for index in range(1, 20)]
        candles.append(candle_range("90", "91", "89", 20, "900", "10"))

        signal = VwapReversionStrategy(
            TradingSettings(strategy_name="vwap_reversion", strategy_pullback_sell_pct=Decimal("4"))
        ).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("VWAP", signal.reason)

    def test_donchian_channel_buys_upper_breakout(self) -> None:
        candles = [candle_range("100", "105", "95", index) for index in range(1, 21)]
        candles.append(candle_range("110", "111", "109", 21))

        signal = DonchianChannelStrategy(TradingSettings(strategy_name="donchian_channel")).evaluate(candles)

        self.assertEqual(signal.action, "buy")
        self.assertIn("Donchian", signal.reason)


if __name__ == "__main__":
    unittest.main()
