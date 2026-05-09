from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.models import Candle
from upbit_autotrader.pattern_learning import (
    PatternObservation,
    build_pattern_model,
    feature_snapshot,
    loss_streak_detail_counts,
    loss_streak_counts,
    record_pattern_entry,
    record_pattern_exit,
    score_current_pattern,
    update_pattern_model_with_observation,
)


def candle(price: str, timestamp: int, trade_value: str = "10000") -> Candle:
    value = Decimal(price)
    return Candle(
        market="KRW-AAA",
        candle_date_time_utc=f"2026-01-01T00:{timestamp:02d}:00",
        candle_date_time_kst=f"2026-01-01T09:{timestamp:02d}:00",
        opening_price=value,
        high_price=value + Decimal("1"),
        low_price=value - Decimal("1"),
        trade_price=value,
        timestamp=timestamp,
        candle_acc_trade_price=Decimal(trade_value),
        candle_acc_trade_volume=Decimal("10"),
    )


class PatternLearningTests(unittest.TestCase):
    def test_loss_pattern_blocks_similar_entry(self) -> None:
        candles = [candle(str(100 + index), index, str(10000 + index * 1000)) for index in range(1, 50)]
        features = feature_snapshot(candles)
        model = build_pattern_model(
            [
                PatternObservation(
                    market="KRW-AAA",
                    strategy="guarded_momentum",
                    entry_time="2026-01-01T09:30:00",
                    exit_time="2026-01-01T09:45:00",
                    entry_price=Decimal("140"),
                    exit_price=Decimal("132"),
                    net_return_pct=Decimal("-6.2"),
                    outcome="loss",
                    features=features,
                )
            ]
        )

        score = score_current_pattern(model, "KRW-AAA", "guarded_momentum", candles)

        self.assertTrue(score.blocked)
        self.assertGreaterEqual(score.loss_similarity, Decimal("0.72"))
        self.assertLess(score.adjustment, Decimal("0"))

    def test_profit_pattern_can_offset_unrelated_loss_pattern(self) -> None:
        profit_candles = [candle(str(100 + index), index, str(10000 + index * 1000)) for index in range(1, 50)]
        loss_candles = [candle(str(150 - index), index, str(90000 - index * 1000)) for index in range(1, 50)]
        model = build_pattern_model(
            [
                PatternObservation(
                    market="KRW-AAA",
                    strategy="guarded_momentum",
                    entry_time="2026-01-01T09:30:00",
                    exit_time="2026-01-01T10:30:00",
                    entry_price=Decimal("120"),
                    exit_price=Decimal("132"),
                    net_return_pct=Decimal("9.8"),
                    outcome="profit",
                    features=feature_snapshot(profit_candles),
                ),
                PatternObservation(
                    market="KRW-AAA",
                    strategy="guarded_momentum",
                    entry_time="2026-01-02T09:30:00",
                    exit_time="2026-01-02T10:30:00",
                    entry_price=Decimal("140"),
                    exit_price=Decimal("130"),
                    net_return_pct=Decimal("-7.3"),
                    outcome="loss",
                    features=feature_snapshot(loss_candles),
                ),
            ]
        )

        score = score_current_pattern(model, "KRW-AAA", "guarded_momentum", profit_candles)

        self.assertFalse(score.blocked)
        self.assertGreater(score.profit_similarity, score.loss_similarity)
        self.assertGreater(score.adjustment, Decimal("0"))

    def test_runtime_trade_outcome_updates_patterns_and_loss_streak(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                markets=("KRW-AAA",),
                market="KRW-AAA",
                state_file=Path(temp_dir) / "paper_state.json",
            )
            candles = [candle(str(100 + index), index, str(10000 + index * 1000)) for index in range(1, 50)]
            model = build_pattern_model([])

            model = record_pattern_entry(
                settings,
                model,
                "KRW-AAA",
                "guarded_momentum",
                Decimal("140"),
                feature_snapshot(candles),
                amount_krw=Decimal("10000"),
            )
            model, observation = record_pattern_exit(
                settings,
                model,
                "KRW-AAA",
                Decimal("130"),
                Decimal("0.0005"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(model["lossCount"], 1)
            self.assertEqual(loss_streak_counts(model, "KRW-AAA")[:2], (1, 1))
            score = score_current_pattern(model, "KRW-AAA", "guarded_momentum", candles)
            self.assertTrue(score.blocked)

    def test_profit_pattern_break_is_remembered_as_negative_evidence(self) -> None:
        candles = [candle(str(100 + index), index, str(10000 + index * 1000)) for index in range(1, 50)]
        features = feature_snapshot(candles)
        profit = PatternObservation(
            market="KRW-AAA",
            strategy="guarded_momentum",
            entry_time="2026-01-01T09:30:00",
            exit_time="2026-01-01T09:45:00",
            entry_price=Decimal("140"),
            exit_price=Decimal("150"),
            net_return_pct=Decimal("7.1"),
            outcome="profit",
            features=features,
        )
        loss = PatternObservation(
            market="KRW-AAA",
            strategy="guarded_momentum",
            entry_time="2026-01-02T09:30:00",
            exit_time="2026-01-02T09:45:00",
            entry_price=Decimal("140"),
            exit_price=Decimal("130"),
            net_return_pct=Decimal("-7.1"),
            outcome="loss",
            features=features,
        )
        model = update_pattern_model_with_observation(build_pattern_model([profit]), loss)

        score = score_current_pattern(model, "KRW-AAA", "guarded_momentum", candles)

        self.assertGreaterEqual(score.broken_profit_similarity, Decimal("0.68"))
        self.assertTrue(score.blocked)
        self.assertLess(score.adjustment, Decimal("0"))

    def test_strategy_and_same_pattern_loss_streaks_are_tracked(self) -> None:
        candles = [candle(str(100 + index), index, str(10000 + index * 1000)) for index in range(1, 50)]
        model = build_pattern_model([])
        model = update_pattern_model_with_observation(
            model,
            PatternObservation(
                market="KRW-AAA",
                strategy="guarded_momentum",
                entry_time="2026-01-01T09:30:00",
                exit_time="2026-01-01T09:45:00",
                entry_price=Decimal("140"),
                exit_price=Decimal("130"),
                net_return_pct=Decimal("-7.1"),
                outcome="loss",
                features=feature_snapshot(candles),
            ),
        )

        market_losses, strategy_losses, pattern_losses, global_losses, _last_loss_at = loss_streak_detail_counts(
            model,
            "KRW-AAA",
            "guarded_momentum",
        )

        self.assertEqual((market_losses, strategy_losses, pattern_losses, global_losses), (1, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
