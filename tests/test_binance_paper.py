from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.binance_paper import (
    ALEX_FEE_DRAG_MIN_CONFIRMATIONS,
    ALEX_FEE_DRAG_MIN_CARD_SCORE,
    ALEX_FEE_DRAG_MIN_TARGET_MOVE_PCT,
    ALEX_MAX_ENTRY_MARGIN_PCT,
    ALEX_MAX_OPPOSED_TIMEFRAMES,
    ALEX_MIN_ENTRY_MARGIN_PCT,
    ALEX_MIN_STOP_DISTANCE_PCT,
    ALEX_MIN_TARGET_MOVE_PCT,
    ALEX_RUNNER_PROFIT_LOCK_SHARE,
    ALEX_STRATEGY_SIDE,
    ALEX_WATCH_PROBE_MIN_TARGET_MOVE_PCT,
    ALEX_ZERO_FEE_EXPERIMENT,
    AUTO_RELEASED_MANUAL_EXIT_BASIS,
    DEFAULT_LEVERAGE,
    DEFAULT_PAPER_SIDE,
    MAX_OPEN_POSITIONS,
    MAEUKNAM_EXPERIMENT_LEVERAGE,
    MAEUKNAM_EXPERIMENT_MAX_OPEN_POSITIONS,
    MAEUKNAM_FEE_DRAG_MIN_CARD_SCORE,
    MAEUKNAM_FEE_DRAG_MIN_CONFIRMATIONS,
    MAEUKNAM_FEE_DRAG_THROTTLE_PCT,
    MAEUKNAM_MAX_SESSION_ORDER_COUNT,
    MAEUKNAM_MIN_HOLD_SECONDS,
    MAEUKNAM_RELAXED_ENTRY_THRESHOLD,
    MAEUKNAM_TEST_ENTRY_THRESHOLD,
    MAEUKNAM_TEST_MAX_FEE_DRAG_PCT,
    MANUAL_HOLD_EXIT_BASIS,
    FuturesPaperPosition,
    FuturesPaperState,
    FuturesPaperStateStore,
    analyze_futures_symbol,
    futures_paper_status,
    fetch_closed_binance_klines_history,
    futures_paper_candidates,
    manual_futures_paper_trade,
    order_minute_bucket,
    relax_maeuknam_futures_signal,
    reset_futures_paper_state,
    run_futures_paper_cycle,
    scan_futures_paper_candidates,
    state_payload,
)
from upbit_autotrader.alex_strategy import AlexTechniqueSignal
from upbit_autotrader.config import TradingSettings
from upbit_autotrader.maeuknam_strategy import MaeuknamTechniqueSignal
from upbit_autotrader.web import (
    binance_futures_realtime_status_payload,
    exchange_mode_payload,
    load_exchange_mode,
    save_exchange_mode,
)


class FakeFuturesClient:
    def __init__(self, closes: list[Decimal]) -> None:
        self.closes = closes
        self.kline_calls: list[tuple[str, str, int]] = []

    def klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 30,
        start_time: int | None = None,
        end_time: int | None = None,
    ):
        self.kline_calls.append((symbol, interval, limit))
        rows = []
        for index, close in enumerate(self.closes[-limit:]):
            rows.append(
                [
                    index * 60_000,
                    str(close),
                    str(close * Decimal("1.001")),
                    str(close * Decimal("0.999")),
                    str(close),
                    str(Decimal("10") + index),
                    0,
                    str(close * Decimal("10")),
                ]
            )
        return rows

    def ticker_price(self, symbol: str):
        return {"symbol": symbol, "price": str(self.closes[-1])}


class LivePriceFuturesClient(FakeFuturesClient):
    def __init__(self, closes: list[Decimal], live_price: Decimal) -> None:
        super().__init__(closes)
        self.live_price = live_price

    def ticker_price(self, symbol: str):
        return {"symbol": symbol, "price": str(self.live_price)}


class AllSymbolsFuturesClient(FakeFuturesClient):
    def __init__(self, closes: list[Decimal], symbols: tuple[str, ...]) -> None:
        super().__init__(closes)
        self.symbols = symbols

    def exchange_info(self):
        return {
            "symbols": [
                {
                    "symbol": symbol,
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                    "status": "TRADING",
                }
                for symbol in self.symbols
            ]
        }

    def ticker_24hr(self, symbol: str | None = None):
        rows = [
            {
                "symbol": item,
                "lastPrice": str(self.closes[-1]),
                "priceChangePercent": str(Decimal("-0.4") - Decimal(index) * Decimal("0.1")),
                "highPrice": str(self.closes[-1] * Decimal("1.03")),
                "lowPrice": str(self.closes[-1] * Decimal("0.97")),
                "quoteVolume": str(Decimal("20000000") + Decimal(index) * Decimal("1000000")),
                "count": str(Decimal("150000") + Decimal(index) * Decimal("10000")),
            }
            for index, item in enumerate(self.symbols)
        ]
        if symbol:
            return next(row for row in rows if row["symbol"] == symbol)
        return rows


class MaeuknamAllSymbolsFuturesClient(AllSymbolsFuturesClient):
    def ticker_24hr(self, symbol: str | None = None):
        raise AssertionError("Maeuknam futures mode must not use the 24h ticker screen")


class AlexAllSymbolsFuturesClient(AllSymbolsFuturesClient):
    def ticker_24hr(self, symbol: str | None = None):
        raise AssertionError("Alex method futures mode must not use the 24h ticker screen")


def decreasing_prices() -> list[Decimal]:
    return [Decimal("100") - Decimal(index) * Decimal("0.1") for index in range(31)]


def increasing_prices() -> list[Decimal]:
    return [Decimal("100") + Decimal(index) * Decimal("0.1") for index in range(31)]


def maeuknam_signal(
    entry_allowed: bool = True,
    direction: str = "LONG",
    score: Decimal | None = None,
) -> MaeuknamTechniqueSignal:
    short_side = direction.upper() == "SHORT"
    return MaeuknamTechniqueSignal(
        technique_id="resistance_failure_short" if short_side else "support_pullback_long",
        technique_name="resistance failure short" if short_side else "support pullback long",
        direction=direction.upper(),
        score=score if score is not None else Decimal("0.82") if entry_allowed else Decimal("0.61"),
        entry_threshold=Decimal("0.72"),
        watch_threshold=Decimal("0.58"),
        entry_allowed=entry_allowed,
        hard_blocks=() if entry_allowed else ("blocked",),
        entry_price=Decimal("102.9"),
        stop_price=Decimal("103.3") if short_side else Decimal("102.5"),
        target1_price=Decimal("102.1") if short_side else Decimal("103.7"),
        target2_price=Decimal("101.6") if short_side else Decimal("104.2"),
        support_price=Decimal("102.6"),
        resistance_price=Decimal("103.7"),
        risk_pct=Decimal("0.39"),
        reward_risk=Decimal("2.0"),
        features={"structure_score": Decimal("0.8")},
        reason="test maeuknam card",
    )


def alex_signal(
    entry_allowed: bool = True,
    direction: str = "LONG",
    score: Decimal | None = None,
) -> AlexTechniqueSignal:
    short_side = direction.upper() == "SHORT"
    return AlexTechniqueSignal(
        technique_id="alex_liquidity_premium_short" if short_side else "alex_liquidity_discount_long",
        technique_name="Alex liquidity premium short" if short_side else "Alex liquidity discount long",
        direction=direction.upper(),
        score=score if score is not None else Decimal("0.68") if entry_allowed else Decimal("0.43"),
        entry_threshold=Decimal("0.52"),
        watch_threshold=Decimal("0.42"),
        entry_allowed=entry_allowed,
        hard_blocks=() if entry_allowed else ("blocked",),
        entry_price=Decimal("102.9"),
        stop_price=Decimal("103.4") if short_side else Decimal("102.4"),
        target1_price=Decimal("102.1") if short_side else Decimal("103.7"),
        target2_price=Decimal("101.6") if short_side else Decimal("104.2"),
        support_price=Decimal("102.4"),
        resistance_price=Decimal("103.4"),
        risk_pct=Decimal("0.49"),
        reward_risk=Decimal("2.6"),
        features={"value_zone_score": Decimal("0.8")},
        reason="test alex method",
    )


def alex_signal_for_allowed_direction(candles, cards_path=None, allowed_directions=None):
    direction = (allowed_directions or ("LONG",))[0]
    return alex_signal(True, direction)


def maeuknam_timeframe_context(*alignments: str) -> dict[str, dict[str, str]]:
    intervals = ("1d", "1w", "1M")
    selected = alignments or ("aligned", "aligned", "aligned")
    return {
        interval: {
            "interval": interval,
            "count": "1500",
            "alignment": selected[index],
            "alignmentScore": "-1" if selected[index] == "opposed" else "1",
        }
        for index, interval in enumerate(intervals)
    }


class BinanceFuturesPaperTests(unittest.TestCase):
    def test_analyze_futures_symbol_selects_short_on_down_momentum(self) -> None:
        candidate = analyze_futures_symbol(FakeFuturesClient(decreasing_prices()), "BTCUSDT")  # type: ignore[arg-type]

        self.assertEqual(candidate.symbol, "BTCUSDT")
        self.assertEqual(candidate.side, "SHORT")
        self.assertLess(candidate.momentum_5m_pct, Decimal("0"))
        self.assertGreater(candidate.score, Decimal("0"))

    def test_analyze_futures_symbol_selects_long_on_up_momentum(self) -> None:
        candidate = analyze_futures_symbol(FakeFuturesClient(increasing_prices()), "ETHUSDT")  # type: ignore[arg-type]

        self.assertEqual(candidate.symbol, "ETHUSDT")
        self.assertEqual(candidate.side, "LONG")
        self.assertGreater(candidate.momentum_5m_pct, Decimal("0"))

    def test_futures_candidates_use_configured_binance_symbols(self) -> None:
        settings = TradingSettings(binance_futures_symbols=("BTCUSDT", "ETHUSDT"))

        candidates = futures_paper_candidates(settings, FakeFuturesClient(decreasing_prices()))  # type: ignore[arg-type]

        self.assertEqual([candidate.symbol for candidate in candidates], ["BTCUSDT", "ETHUSDT"])
        self.assertTrue(all(candidate.analysis_side == "SHORT" for candidate in candidates))
        self.assertTrue(all(candidate.execution_side == "LONG" for candidate in candidates))
        self.assertTrue(all(candidate.side == "LONG" for candidate in candidates))

    def test_futures_candidates_screen_all_usdt_perpetual_symbols(self) -> None:
        settings = TradingSettings(binance_futures_symbols=("BTCUSDT",))
        client = AllSymbolsFuturesClient(
            decreasing_prices(),
            ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"),
        )

        scan = scan_futures_paper_candidates(settings, client)  # type: ignore[arg-type]

        self.assertEqual(scan.universe_count, 5)
        self.assertEqual(scan.evaluated_count, 5)
        self.assertEqual(scan.universe_source, "binance_exchange_info_usdt_perpetual")
        self.assertEqual({candidate.symbol for candidate in scan.candidates}, set(client.symbols))
        self.assertGreater(scan.deep_analysis_count, 0)
        self.assertTrue(all(candidate.universe_source == "binance_exchange_info_usdt_perpetual" for candidate in scan.candidates))

    def test_run_cycle_bets_long_against_short_analysis_without_live_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            payload = run_futures_paper_cycle(settings, FakeFuturesClient(decreasing_prices()))  # type: ignore[arg-type]

            self.assertTrue(payload["simulated"])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["analysisSide"], "SHORT")
            self.assertEqual(payload["actions"][0]["executionSide"], "LONG")
            self.assertEqual(payload["actions"][0]["side"], "LONG")
            self.assertEqual(payload["positions"][0]["symbol"], "BTCUSDT")
            self.assertEqual(payload["currency"], "USDT")
            self.assertEqual(payload["leverage"], str(DEFAULT_LEVERAGE))
            self.assertEqual(payload["paperSide"], "CONTRARIAN")
            self.assertEqual(payload["strategySide"], "CONTRARIAN")
            self.assertEqual(payload["analysisSide"], "SHORT")
            self.assertEqual(payload["executionSide"], "LONG")
            self.assertGreater(Decimal(payload["usedMarginUsdt"]), Decimal("0"))
            self.assertGreater(Decimal(payload["totalNotionalUsdt"]), Decimal(payload["usedMarginUsdt"]))

    def test_run_cycle_bets_short_against_long_analysis_in_bullish_regime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertTrue(payload["simulated"])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["analysisSide"], "LONG")
            self.assertEqual(payload["actions"][0]["executionSide"], "SHORT")
            self.assertEqual(payload["actions"][0]["side"], "SHORT")
            self.assertEqual(payload["positions"][0]["symbol"], "BTCUSDT")
            self.assertEqual(payload["marketRegime"]["tradeSide"], "LONG")
            self.assertEqual(payload["marketRegime"]["executionSide"], "SHORT")

    def test_maeuknam_futures_mode_uses_only_maeuknam_long_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["paperSide"], "MAEUKNAM_CARDS")
            self.assertEqual(payload["strategySide"], "MAEUKNAM_CARDS")
            self.assertEqual(payload["analysisSide"], "LONG")
            self.assertEqual(payload["executionSide"], "LONG")
            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "LONG")
            self.assertEqual(payload["actions"][0]["leverage"], str(MAEUKNAM_EXPERIMENT_LEVERAGE))
            self.assertEqual(payload["leverage"], str(MAEUKNAM_EXPERIMENT_LEVERAGE))
            self.assertEqual(payload["maxOpenPositions"], MAEUKNAM_EXPERIMENT_MAX_OPEN_POSITIONS)
            self.assertGreater(Decimal(payload["actions"][0]["marginUsdt"]), Decimal("124"))
            self.assertLess(Decimal(payload["actions"][0]["marginUsdt"]), Decimal("126"))
            self.assertEqual(payload["actions"][0]["feeBudgetedMargin"], True)
            self.assertLessEqual(Decimal(payload["actions"][0]["openFeeEquityPct"]), Decimal("0.500001"))
            self.assertEqual(payload["maeuknamEntryPolicy"]["positionSizingMode"], "100x_leverage_with_open_fee_budget")
            self.assertEqual(payload["actions"][0]["analysisSide"], "LONG")
            self.assertEqual(payload["actions"][0]["executionSide"], "LONG")
            self.assertEqual(payload["candidates"][0]["contrarian"], "false")
            self.assertIn("maeuknam-card", payload["actions"][0]["reason"])

    def test_maeuknam_futures_open_uses_latest_ticker_price_for_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = LivePriceFuturesClient(increasing_prices(), Decimal("103.10"))

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
                payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["price"], "103.1")
            self.assertEqual(payload["positions"][0]["entryPrice"], "103.1")
            self.assertNotEqual(payload["actions"][0]["analysisPrice"], payload["actions"][0]["price"])

    def test_maeuknam_futures_mode_uses_card_direction_for_shorts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["paperSide"], "MAEUKNAM_CARDS")
            self.assertEqual(payload["strategySide"], "MAEUKNAM_CARDS")
            self.assertEqual(payload["analysisSide"], "SHORT")
            self.assertEqual(payload["executionSide"], "SHORT")
            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "SHORT")
            self.assertEqual(payload["actions"][0]["analysisSide"], "SHORT")
            self.assertEqual(payload["actions"][0]["executionSide"], "SHORT")
            self.assertEqual(payload["actions"][0]["stopPrice"], "103.3")
            self.assertEqual(payload["actions"][0]["target1Price"], "102.1")
            self.assertEqual(payload["actions"][0]["target2Price"], "101.6")
            self.assertEqual(payload["actions"][0]["exitBasis"], "maeuknam_card")
            self.assertEqual(payload["candidates"][0]["contrarian"], "false")
            self.assertNotIn("contrarian", payload["actions"][0]["reason"].lower())

    def test_maeuknam_futures_mode_compares_long_and_short_cards_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            def evaluator(candles, cards_path=None, allowed_directions=None):  # noqa: ANN001
                side = (allowed_directions or ("LONG",))[0]
                if side == "LONG":
                    return replace(maeuknam_signal(True, "LONG", score=Decimal("0.53")), entry_allowed=False)
                return replace(maeuknam_signal(True, "SHORT", score=Decimal("0.49")), entry_allowed=False)

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", side_effect=evaluator):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "LONG")
            diagnostics = payload["candidates"][0]["directionDiagnostics"]
            self.assertIn("LONG", diagnostics)
            self.assertIn("SHORT", diagnostics)
            self.assertTrue(diagnostics["LONG"]["entryAllowed"])
            self.assertFalse(diagnostics["SHORT"]["entryAllowed"])

    def test_maeuknam_futures_mode_blocks_when_higher_timeframes_oppose_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            safe_inverse_short = replace(
                maeuknam_signal(True, "SHORT"),
                target1_price=Decimal("102.8"),
                target2_price=Decimal("102.4"),
            )
            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=safe_inverse_short):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "agency")
            self.assertEqual(payload["candidates"][0]["entryAllowed"], "false")
            self.assertEqual(payload["candidates"][0]["analysisSide"], "SHORT")
            self.assertEqual(payload["candidates"][0]["executionSide"], "SHORT")
            self.assertIn("higher timeframes oppose", payload["candidates"][0]["entryBlockReason"])

    def test_maeuknam_futures_mode_reports_inverse_entry_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            safe_inverse_long = replace(
                maeuknam_signal(True, "LONG"),
                target1_price=Decimal("103.1"),
            )
            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=safe_inverse_long):
                with patch(
                    "upbit_autotrader.binance_paper.maeuknam_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context("opposed", "opposed", "aligned"),
                ):
                    payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "agency")
            self.assertEqual(payload["candidates"][0]["analysisSide"], "LONG")
            self.assertEqual(payload["candidates"][0]["executionSide"], "LONG")
            self.assertFalse(payload["maeuknamEntryPolicy"]["inverseAgencyEntryEnabled"])
            self.assertEqual(payload["maeuknamEntryPolicy"]["inverseAgencyMinRewardRisk"], "1.2")

    def test_maeuknam_futures_mode_blocks_inverse_when_reward_risk_is_weak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                with patch(
                    "upbit_autotrader.binance_paper.maeuknam_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context("opposed", "opposed", "aligned"),
                ):
                    payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "agency")
            self.assertEqual(payload["candidates"][0]["entryAllowed"], "false")
            self.assertIn("higher timeframes oppose", payload["candidates"][0]["entryBlockReason"])

    def test_maeuknam_futures_execution_proof_blocks_short_when_live_price_rises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = LivePriceFuturesClient([Decimal("102.9")] * 31, Decimal("103.0"))

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "SHORT")):
                with patch(
                    "upbit_autotrader.binance_paper.maeuknam_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context(),
                ):
                    payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "execution_proof")
            self.assertEqual(payload["candidates"][0]["entryAllowed"], "false")
            self.assertIn("live price has not confirmed SHORT", payload["candidates"][0]["entryBlockReason"])
            self.assertTrue(payload["maeuknamEntryPolicy"]["executionProofEnabled"])

    def test_maeuknam_futures_execution_proof_blocks_long_after_target_chase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = LivePriceFuturesClient([Decimal("103.0")] * 31, Decimal("104.3"))

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                with patch(
                    "upbit_autotrader.binance_paper.maeuknam_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context(),
                ):
                    payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "execution_proof")
            self.assertIn("already chased past card target", payload["candidates"][0]["entryBlockReason"])

    def test_maeuknam_futures_mode_relaxes_entry_threshold_for_paper_experiment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            card_signal = replace(
                maeuknam_signal(True, "LONG", score=MAEUKNAM_RELAXED_ENTRY_THRESHOLD + Decimal("0.01")),
                entry_allowed=False,
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=card_signal):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(Decimal(payload["candidates"][0]["maeuknamSignal"]["entryThreshold"]), MAEUKNAM_TEST_ENTRY_THRESHOLD)
            self.assertIn("futures test-trade threshold", payload["candidates"][0]["maeuknamSignal"]["reason"])

    def test_maeuknam_test_trade_mode_allows_weak_card_evidence_to_run(self) -> None:
        weak_short = replace(
            maeuknam_signal(True, "SHORT", score=MAEUKNAM_RELAXED_ENTRY_THRESHOLD + Decimal("0.04")),
            entry_allowed=False,
            card_support_count=1,
            card_confidence=Decimal("0.4691"),
            card_evidence_score=Decimal("0.28"),
            card_evidence_threshold_premium=Decimal("0.0648"),
        )

        relaxed = relax_maeuknam_futures_signal(weak_short)

        self.assertEqual(relaxed.entry_threshold, MAEUKNAM_TEST_ENTRY_THRESHOLD)
        self.assertTrue(relaxed.entry_allowed)
        self.assertIn("futures test-trade threshold", relaxed.reason)

    def test_fetch_closed_binance_klines_history_paginates_backwards(self) -> None:
        class PagingClient:
            def __init__(self) -> None:
                self.rows = [
                    [index * 60_000, "1", "1", "1", "1", "1", 0, "1"]
                    for index in range(1605)
                ]
                self.calls: list[tuple[str, str, int, int | None]] = []

            def klines(
                self,
                symbol: str,
                interval: str = "1m",
                limit: int = 30,
                start_time: int | None = None,
                end_time: int | None = None,
            ):
                self.calls.append((symbol, interval, limit, end_time))
                eligible = self.rows if end_time is None else [row for row in self.rows if row[0] <= end_time]
                return eligible[-limit:]

        client = PagingClient()

        rows = fetch_closed_binance_klines_history(client, "BTCUSDT", "1d", 1600, cache_seconds=0)  # type: ignore[arg-type]

        self.assertEqual(len(rows), 1600)
        self.assertEqual(rows[0][0], 5 * 60_000)
        self.assertEqual(rows[-1][0], 1604 * 60_000)
        self.assertEqual(client.calls[0], ("BTCUSDT", "1d", 1500, None))
        self.assertEqual(client.calls[1], ("BTCUSDT", "1d", 100, (105 * 60_000) - 1))

    def test_maeuknam_futures_mode_uses_btc_only_even_when_other_symbols_are_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("LONG1USDT", "LONG2USDT", "SHORT1USDT", "SHORT2USDT", "SHORT3USDT", "SHORT4USDT"),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual([candidate["symbol"] for candidate in payload["candidates"]], ["BTCUSDT"])
            self.assertEqual(payload["universeCount"], 1)
            self.assertEqual(payload["universeSource"], "maeuknam_cards_btcusdt_only")
            self.assertEqual(payload["openPositions"], MAEUKNAM_EXPERIMENT_MAX_OPEN_POSITIONS)
            self.assertEqual([action["symbol"] for action in payload["actions"]], ["BTCUSDT"])
            self.assertEqual(payload["positions"][0]["leverage"], str(MAEUKNAM_EXPERIMENT_LEVERAGE))
            self.assertEqual(payload["tickerCount"], 0)
            self.assertEqual({action["analysisSide"] for action in payload["actions"]}, {"LONG"})
            self.assertEqual({action["executionSide"] for action in payload["actions"]}, {"LONG"})

    def test_maeuknam_futures_mode_fetches_daily_weekly_monthly_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = FakeFuturesClient(increasing_prices())

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
                payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            intervals = [interval for _, interval, _ in client.kline_calls]
            self.assertEqual(intervals[:4], ["1m", "1d", "1w", "1M"])
            context = payload["candidates"][0]["timeframeContext"]
            self.assertEqual(set(context), {"1d", "1w", "1M"})
            self.assertEqual(context["1d"]["count"], str(len(increasing_prices())))
            self.assertEqual(payload["maeuknamEntryPolicy"]["multiTimeframeIntervals"], ["1d", "1w", "1M"])
            self.assertIn("HTF alignment", payload["candidates"][0]["maeuknamSignal"]["reason"])

    def test_maeuknam_futures_mode_blocks_entry_when_card_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(False)):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["openPositions"], 0)
            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryAllowed"], "false")
            self.assertNotIn("adaptive", payload["candidates"][0]["reason"])

    def test_maeuknam_futures_mode_extends_small_target_to_fee_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            small_target = replace(
                maeuknam_signal(True, "LONG"),
                target1_price=Decimal("103.0"),
                target2_price=Decimal("103.05"),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=small_target):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["candidates"][0]["entryAllowed"], "true")
            self.assertIn("fee-floor target extension", payload["candidates"][0]["entryBlockReason"])
            self.assertEqual(payload["actions"][0]["cardTarget2Price"], "103.05")
            self.assertEqual(payload["actions"][0]["feeFloorTargetExtended"], True)
            self.assertEqual(payload["actions"][0]["exitBasis"], "maeuknam_card_fee_floor")
            self.assertGreaterEqual(
                Decimal(payload["actions"][0]["target2Price"]),
                Decimal(payload["actions"][0]["price"]) * (Decimal("1") + Decimal(payload["maeuknamEntryPolicy"]["requiredTargetMovePct"]) / Decimal("100")),
            )

    def test_maeuknam_futures_mode_blocks_after_session_order_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = FakeFuturesClient(increasing_prices())

            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            state = store.load()
            state.order_count = 999999
            store.save(state)
            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
                payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(MAEUKNAM_MAX_SESSION_ORDER_COUNT, 48)
            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["entryBlockReason"], "session order count 999999 reached cap 48")
            self.assertTrue(payload["maeuknamEntryPolicy"]["sessionOrderLimitEnabled"])

    def test_maeuknam_futures_mode_blocks_fee_drag_in_test_trade_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = FakeFuturesClient(increasing_prices())

            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            state = store.load()
            state.wallet_balance_usdt = Decimal("500")
            state.realized_pnl_usdt = Decimal("-400")
            state.fees_paid_usdt = Decimal("550")
            store.save(state)
            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True)):
                payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertIn("fee drag", payload["entryBlockReason"])
            self.assertEqual(MAEUKNAM_TEST_MAX_FEE_DRAG_PCT, Decimal("10"))
            self.assertEqual(payload["maeuknamEntryPolicy"]["maxFeeDragPct"], "10")
            self.assertTrue(payload["maeuknamEntryPolicy"]["feeDragLimitEnabled"])

    def test_maeuknam_futures_mode_throttles_weak_entries_after_fee_drag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = LivePriceFuturesClient(increasing_prices(), Decimal("103.1"))

            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            state = store.load()
            state.wallet_balance_usdt = Decimal("1000")
            state.fees_paid_usdt = Decimal("160")
            store.save(state)

            with (
                patch(
                    "upbit_autotrader.binance_paper.evaluate_maeuknam_techniques",
                    return_value=maeuknam_signal(True, "LONG", score=Decimal("0.45")),
                ),
                patch(
                    "upbit_autotrader.binance_paper.maeuknam_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context("aligned", "aligned", "aligned"),
                ),
            ):
                payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertIn("fee drag throttle", payload["candidates"][0]["entryBlockReason"])
            self.assertEqual(MAEUKNAM_FEE_DRAG_THROTTLE_PCT, Decimal("5"))
            self.assertEqual(MAEUKNAM_FEE_DRAG_MIN_CARD_SCORE, Decimal("0.60"))
            self.assertEqual(MAEUKNAM_FEE_DRAG_MIN_CONFIRMATIONS, 2)
            self.assertEqual(payload["maeuknamEntryPolicy"]["feeDragThrottlePct"], "5")
            self.assertEqual(payload["maeuknamEntryPolicy"]["feeDragMinCardScore"], "0.6")
            self.assertEqual(payload["maeuknamEntryPolicy"]["feeDragMinConfirmations"], "2")

    def test_maeuknam_futures_mode_reenters_same_card_without_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="maeuknam-card: support pullback long",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis="maeuknam_card",
                            technique_id="support_pullback_long",
                            technique_name="support pullback long",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(False, "LONG")):
                close_payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 30))  # type: ignore[arg-type]
            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                reentry_payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 30))  # type: ignore[arg-type]

            self.assertEqual(close_payload["actions"][0]["type"], "CLOSE")
            self.assertEqual(reentry_payload["actions"][0]["type"], "OPEN")
            self.assertEqual(reentry_payload["candidates"][0]["entryStage"], "entry")
            self.assertEqual(reentry_payload["maeuknamEntryPolicy"]["cooldownMode"], "disabled")
            self.assertEqual(reentry_payload["maeuknamEntryPolicy"]["reentryCooldownSeconds"], 0)

    def test_maeuknam_futures_mode_screens_btcusdt_only_with_cards_only(self) -> None:
        settings = TradingSettings(
            strategy_name="maeuknam_cards",
            binance_futures_symbols=("BTCUSDT",),
        )
        client = MaeuknamAllSymbolsFuturesClient(
            increasing_prices(),
            ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"),
        )

        with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(False)):
            scan = scan_futures_paper_candidates(settings, client)  # type: ignore[arg-type]

        self.assertEqual(scan.universe_count, 1)
        self.assertEqual(scan.evaluated_count, 1)
        self.assertEqual(scan.universe_source, "maeuknam_cards_btcusdt_only")
        self.assertEqual(scan.ticker_count, 0)
        self.assertEqual(scan.deep_analysis_count, 1)
        self.assertEqual([candidate.symbol for candidate in scan.candidates], ["BTCUSDT"])
        self.assertTrue(all(candidate.universe_source == "maeuknam_cards_btcusdt_only" for candidate in scan.candidates))
        self.assertTrue(all(candidate.analysis_depth == "maeuknam_card_1m_htf" for candidate in scan.candidates))
        self.assertTrue(all(candidate.analysis_side == "LONG" for candidate in scan.candidates))
        self.assertTrue(all(candidate.execution_side == "LONG" for candidate in scan.candidates))
        self.assertTrue(all(candidate.contrarian is False for candidate in scan.candidates))
        self.assertTrue(all(candidate.reason.startswith("maeuknam-card") for candidate in scan.candidates))

    def test_alex_futures_mode_screens_btcusdt_only_with_method_only(self) -> None:
        settings = TradingSettings(
            strategy_name="alex_method",
            binance_futures_symbols=("BTCUSDT",),
        )
        client = AlexAllSymbolsFuturesClient(
            increasing_prices(),
            ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"),
        )

        with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", side_effect=alex_signal_for_allowed_direction):
            scan = scan_futures_paper_candidates(settings, client)  # type: ignore[arg-type]

        self.assertEqual(scan.universe_count, 1)
        self.assertEqual(scan.evaluated_count, 1)
        self.assertEqual(scan.universe_source, "alex_method_btcusdt_only")
        self.assertEqual(scan.ticker_count, 0)
        self.assertEqual(scan.deep_analysis_count, 1)
        self.assertEqual([candidate.symbol for candidate in scan.candidates], ["BTCUSDT"])
        self.assertTrue(all(candidate.universe_source == "alex_method_btcusdt_only" for candidate in scan.candidates))
        self.assertTrue(all(candidate.analysis_depth == "alex_method_1m_htf" for candidate in scan.candidates))
        self.assertTrue(all(candidate.alex_signal for candidate in scan.candidates))
        self.assertTrue(all(not candidate.maeuknam_signal for candidate in scan.candidates))
        self.assertTrue(all(candidate.contrarian is False for candidate in scan.candidates))
        self.assertTrue(all(candidate.reason.startswith("alex-method") for candidate in scan.candidates))

    def test_alex_futures_mode_opens_with_alex_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", side_effect=alex_signal_for_allowed_direction):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["paperSide"], ALEX_STRATEGY_SIDE)
            self.assertEqual(payload["strategySide"], ALEX_STRATEGY_SIDE)
            self.assertEqual(payload["universeSource"], "alex_method_btcusdt_only")
            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertTrue(payload["actions"][0]["exitBasis"].startswith("alex_method"))
            self.assertEqual(payload["actions"][0]["feeUsdt"], "0")
            self.assertEqual(payload["actions"][0]["feeRate"], "0")
            self.assertEqual(payload["actions"][0]["zeroFeeExperiment"], True)
            self.assertEqual(payload["actions"][0]["fullDeployMargin"], False)
            self.assertEqual(payload["actions"][0]["feeBudgetedMargin"], False)
            self.assertGreaterEqual(Decimal(payload["actions"][0]["marginCapPct"]), ALEX_MIN_ENTRY_MARGIN_PCT * Decimal("100"))
            self.assertLessEqual(Decimal(payload["actions"][0]["marginCapPct"]), ALEX_MAX_ENTRY_MARGIN_PCT * Decimal("100"))
            self.assertLessEqual(Decimal(payload["actions"][0]["marginUsdt"]), Decimal("300"))
            self.assertEqual(payload["actions"][0]["positionSizingMode"], "100x_leverage_dynamic_10_30_margin")
            self.assertIn("alexEntryPolicy", payload)
            self.assertEqual(payload["alexEntryPolicy"]["positionSizingMode"], "100x_leverage_dynamic_10_30_margin")
            self.assertEqual(payload["alexEntryPolicy"]["smallTargetHandling"], "block_entry_until_target_beats_fee_floor")
            self.assertEqual(payload["alexEntryPolicy"]["zeroFeeExperiment"], ALEX_ZERO_FEE_EXPERIMENT)
            self.assertEqual(payload["alexEntryPolicy"]["feeRate"], "0")
            self.assertTrue(payload["candidates"][0]["alexSignal"])

    def test_alex_futures_mode_does_not_wait_for_live_direction_tick(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            client = LivePriceFuturesClient([Decimal("102.9")] * 31, Decimal("103.0"))

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, client)  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "SHORT")
            self.assertEqual(payload["candidates"][0]["entryStage"], "entry")
            self.assertEqual(payload["alexEntryPolicy"]["liveDirectionConfirmationRequired"], False)

    def test_alex_futures_mode_blocks_when_higher_timeframes_oppose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with (
                patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(True, "SHORT")),
                patch(
                    "upbit_autotrader.binance_paper.alex_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context("opposed", "opposed", "aligned"),
                ),
            ):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "htf_veto")
            self.assertIn("HTF veto", payload["candidates"][0]["entryBlockReason"])
            self.assertEqual(payload["alexEntryPolicy"]["alexMaxOpposedTimeframes"], ALEX_MAX_OPPOSED_TIMEFRAMES)

    def test_alex_futures_mode_blocks_too_tight_stops_as_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            tight_stop = replace(
                alex_signal(True, "SHORT"),
                entry_price=Decimal("102.9"),
                stop_price=Decimal("102.95"),
                target1_price=Decimal("102.1"),
                target2_price=Decimal("101.6"),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=tight_stop):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "stop_noise")
            self.assertIn("below noise floor", payload["candidates"][0]["entryBlockReason"])
            self.assertEqual(payload["alexEntryPolicy"]["alexMinStopDistancePct"], str(ALEX_MIN_STOP_DISTANCE_PCT))

    def test_alex_futures_mode_uses_watch_probe_when_full_entry_is_too_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            watch_long = replace(
                alex_signal(False, "LONG", score=Decimal("0.45")),
                hard_blocks=(),
                entry_allowed=False,
            )
            weak_short = replace(
                alex_signal(False, "SHORT", score=Decimal("0.20")),
                hard_blocks=(),
                entry_allowed=False,
            )

            def watch_signal_for_allowed_direction(candles, cards_path=None, allowed_directions=None):
                direction = (allowed_directions or ("LONG",))[0]
                return watch_long if direction == "LONG" else weak_short

            with (
                patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", side_effect=watch_signal_for_allowed_direction),
                patch(
                    "upbit_autotrader.binance_paper.alex_multi_timeframe_context",
                    return_value=maeuknam_timeframe_context("aligned", "aligned", "aligned"),
                ),
            ):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "LONG")
            self.assertEqual(payload["candidates"][0]["entryStage"], "watch_probe")
            self.assertIn("watch probe", payload["candidates"][0]["entryBlockReason"])
            self.assertEqual(Decimal(payload["actions"][0]["marginCapPct"]), ALEX_MIN_ENTRY_MARGIN_PCT * Decimal("100"))
            self.assertGreaterEqual(Decimal(payload["candidates"][0]["targetMovePct"]), ALEX_WATCH_PROBE_MIN_TARGET_MOVE_PCT)
            self.assertEqual(payload["alexEntryPolicy"]["watchProbeEnabled"], True)

    def test_alex_futures_mode_blocks_ordinary_reentry_after_fee_drag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            state = store.load()
            state.wallet_balance_usdt = Decimal("1000")
            state.fees_paid_usdt = Decimal("60")
            store.save(state)

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "fee_drag_throttle")
            self.assertIn("Alex A+ score", payload["candidates"][0]["entryBlockReason"])
            self.assertEqual(payload["alexEntryPolicy"]["maxFeeDragPct"], "0")
            self.assertEqual(payload["alexEntryPolicy"]["feeDragLimitEnabled"], False)
            self.assertEqual(payload["alexEntryPolicy"]["feeDragMinConfirmations"], str(ALEX_FEE_DRAG_MIN_CONFIRMATIONS))
            self.assertEqual(payload["alexEntryPolicy"]["feeDragMinCardScore"], str(ALEX_FEE_DRAG_MIN_CARD_SCORE))
            self.assertEqual(payload["alexEntryPolicy"]["alexFeeDragMinTargetMovePct"], str(ALEX_FEE_DRAG_MIN_TARGET_MOVE_PCT))
            self.assertEqual(ALEX_FEE_DRAG_MIN_CONFIRMATIONS, 1)

    def test_alex_futures_mode_allows_a_plus_reentry_after_fee_drag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            state = store.load()
            state.wallet_balance_usdt = Decimal("1000")
            state.fees_paid_usdt = Decimal("60")
            store.save(state)

            strong_signal = replace(alex_signal(True, "SHORT"), score=Decimal("0.82"))
            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=strong_signal):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "SHORT")

    def test_alex_futures_mode_blocks_raw_targets_below_fee_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            small_target = replace(
                alex_signal(True, "LONG"),
                target1_price=Decimal("103.0"),
                target2_price=Decimal("103.05"),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=small_target):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["candidates"][0]["entryStage"], "fee_gate")
            self.assertIn("required fee-safe move", payload["candidates"][0]["entryBlockReason"])

    def test_alex_futures_mode_does_not_close_new_capped_position_due_to_entry_fee(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(True, "SHORT")):
                first = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]
                second = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(first["actions"][0]["type"], "OPEN")
            self.assertEqual(first["actions"][0]["marginUsdt"], "300")
            self.assertEqual(second["actions"], [])
            self.assertEqual(second["openPositions"], 1)

    def test_alex_futures_mode_holds_existing_position_on_weak_flat_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("100"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-05-09T00:00:00+00:00",
                            stop_price=Decimal("110"),
                            target1_price=Decimal("95"),
                            target2_price=Decimal("90"),
                            exit_basis="alex_method",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(False, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("100")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "SHORT")

    def test_alex_futures_mode_blocks_same_side_reentry_in_same_one_minute_candle_after_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("100"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-05-09T00:00:00+00:00",
                            stop_price=Decimal("95"),
                            target1_price=Decimal("115"),
                            target2_price=Decimal("120"),
                            exit_basis="alex_method",
                        )
                    },
                )
            )

            same_side = replace(
                alex_signal(True, "LONG"),
                entry_price=Decimal("94"),
                stop_price=Decimal("93"),
                target1_price=Decimal("94.6"),
                target2_price=Decimal("95"),
            )
            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=same_side):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("94")] * 31))  # type: ignore[arg-type]

            self.assertEqual([action["type"] for action in payload["actions"]], ["CLOSE"])
            self.assertEqual(payload["openPositions"], 0)
            self.assertEqual(payload["candidates"][0]["entryStage"], "reentry_candle")
            self.assertIn("same 1m candle re-entry blocked", payload["candidates"][0]["entryBlockReason"])

    def test_alex_futures_mode_switches_opposite_side_atomically_inside_same_candle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("100"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-05-09T00:00:00+00:00",
                            stop_price=Decimal("90"),
                            target1_price=Decimal("115"),
                            target2_price=Decimal("120"),
                            exit_basis="alex_method",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual([action["type"] for action in payload["actions"]], ["CLOSE", "OPEN"])
            self.assertEqual(payload["actions"][1]["side"], "SHORT")
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "SHORT")

    def test_alex_futures_mode_blocks_second_flip_inside_entry_candle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("100"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at=order_minute_bucket(),
                            stop_price=Decimal("90"),
                            target1_price=Decimal("115"),
                            target2_price=Decimal("120"),
                            exit_basis="alex_method",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "LONG")

    def test_alex_futures_mode_extends_profit_at_target_with_runner_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("100"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-05-09T00:00:00+00:00",
                            stop_price=Decimal("95"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis="alex_method",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=alex_signal(False, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.2")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "LONG")
            self.assertEqual(
                Decimal(payload["positions"][0]["stopLossPrice"]),
                Decimal("100") + Decimal("2.2") * ALEX_RUNNER_PROFIT_LOCK_SHARE,
            )

    def test_alex_futures_mode_holds_when_switch_target_cannot_cover_transition_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="alex_method",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("100"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-05-09T00:00:00+00:00",
                            stop_price=Decimal("90"),
                            target1_price=Decimal("115"),
                            target2_price=Decimal("120"),
                            exit_basis="alex_method",
                        )
                    },
                )
            )
            switch_target = replace(
                alex_signal(True, "SHORT"),
                target1_price=Decimal("102.7"),
                target2_price=Decimal("102.64"),
            )

            with patch("upbit_autotrader.binance_paper.evaluate_alex_techniques", return_value=switch_target):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.9")] * 31))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "LONG")

    def test_maeuknam_futures_status_labels_match_cards_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            payload = futures_paper_status(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["paperSide"], "MAEUKNAM_CARDS")
            self.assertEqual(payload["strategySide"], "MAEUKNAM_CARDS")
            self.assertEqual(payload["analysisSide"], "CARD_DIRECTION")
            self.assertEqual(payload["executionSide"], "CARD_DIRECTION")

    def test_binance_realtime_status_prefers_live_ticker_price_for_open_position(self) -> None:
        settings = TradingSettings(strategy_name="maeuknam_cards", binance_futures_symbols=("BTCUSDT",))
        cycle_payload = {
            "strategySide": "MAEUKNAM_CARDS",
            "analysisSide": "SHORT",
            "executionSide": "SHORT",
            "candidates": [
                {
                    "symbol": "BTCUSDT",
                    "side": "SHORT",
                    "analysisSide": "SHORT",
                    "executionSide": "SHORT",
                    "price": "100",
                    "score": "1.2",
                    "entryAllowed": "true",
                    "maeuknamSignal": {"techniqueId": "resistance_failure_short"},
                }
            ],
        }
        status_payload = {
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "side": "SHORT",
                    "currentPrice": "101",
                    "entryPrice": "102",
                    "returnOnMarginPct": "1",
                    "leverage": "100",
                }
            ],
            "leverage": "100",
        }

        payload = binance_futures_realtime_status_payload(settings, cycle_payload, status_payload)

        self.assertEqual(payload["last"]["plan"]["situations"][0]["currentPrice"], "101")

    def test_maeuknam_futures_mode_keeps_existing_short_card_position(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("1"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="maeuknam-card: resistance failure short",
                            stop_price=Decimal("101"),
                            target1_price=Decimal("99"),
                            target2_price=Decimal("98"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            valid_short = replace(
                maeuknam_signal(True, "SHORT"),
                entry_price=Decimal("100"),
                stop_price=Decimal("101"),
                target1_price=Decimal("99"),
                target2_price=Decimal("98"),
            )
            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=valid_short):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("100")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["positions"][0]["side"], "SHORT")
            self.assertEqual(payload["paperSide"], "MAEUKNAM_CARDS")

    def test_maeuknam_futures_mode_closes_inverse_position_when_reward_risk_turns_weak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="maeuknam-card-inverse: resistance failure short failed agency check",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("100.25"),
                            target2_price=Decimal("100.5"),
                            exit_basis="maeuknam_card_fee_floor",
                            technique_id="inverse_agency_resistance_failure_short",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("100.1")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "CLOSE")
            self.assertIn("inverse card reward/risk", payload["actions"][0]["reason"])
            self.assertEqual(payload["openPositions"], 0)

    def test_maeuknam_futures_mode_does_not_take_profit_on_fixed_roe_before_card_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="maeuknam-card: support pullback long",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("100.4")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["takeProfitPrice"], "102")
            self.assertEqual(payload["positions"][0]["stopLossPrice"], "99")
            self.assertEqual(payload["positions"][0]["exitBasis"], "maeuknam_card")
            self.assertEqual(payload["exitBasis"], "maeuknam_card_levels")

    def test_maeuknam_futures_mode_trails_after_first_card_target_before_fee_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="maeuknam-card: support pullback long",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("104"),
                            exit_basis="maeuknam_card_fee_floor",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("101.2")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["stopLossPrice"], "100.66")

    def test_maeuknam_futures_mode_exits_at_card_target_when_card_no_longer_supports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="maeuknam-card: support pullback long",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(False, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.1")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "CLOSE")
            self.assertIn("Maeuknam card target reached", payload["actions"][0]["reason"])
            self.assertEqual(payload["openPositions"], 0)

    def test_maeuknam_futures_mode_extends_profit_when_same_card_stays_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            reason="maeuknam-card: support pullback long",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("102.1")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["stopLossPrice"], "101.155")

    def test_maeuknam_futures_mode_trails_short_profit_when_same_card_stays_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            reason="maeuknam-card: resistance failure short",
                            stop_price=Decimal("101"),
                            target1_price=Decimal("99"),
                            target2_price=Decimal("98"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("97.9")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["stopLossPrice"], "98.845")

    def test_maeuknam_futures_mode_stop_ignores_min_hold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            reason="maeuknam-card: support pullback long",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("98.9")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "CLOSE")
            self.assertIn("Maeuknam card stop reached", payload["actions"][0]["reason"])
            self.assertEqual(payload["openPositions"], 0)

    def test_maeuknam_futures_mode_manual_hold_ignores_stop_and_signal_flip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            reason="manual LONG hold until switch",
                            stop_price=Decimal("99"),
                            target1_price=Decimal("101"),
                            target2_price=Decimal("102"),
                            exit_basis=MANUAL_HOLD_EXIT_BASIS,
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "SHORT")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("98.5")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["exitBasis"], MANUAL_HOLD_EXIT_BASIS)

    def test_manual_futures_paper_trade_opens_full_equity_long_hold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            payload = manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("100")] * 31), "LONG")  # type: ignore[arg-type]

            self.assertEqual(payload["manualAction"], "LONG")
            self.assertEqual(payload["actions"][0]["type"], "OPEN")
            self.assertEqual(payload["actions"][0]["side"], "LONG")
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "LONG")
            self.assertEqual(payload["positions"][0]["leverage"], str(MAEUKNAM_EXPERIMENT_LEVERAGE))
            self.assertEqual(payload["positions"][0]["exitBasis"], MANUAL_HOLD_EXIT_BASIS)
            self.assertLess(Decimal(payload["availableBalanceUsdt"]), Decimal("0.0000001"))

    def test_manual_futures_paper_trade_uses_requested_margin_amount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            payload = manual_futures_paper_trade(
                settings,
                FakeFuturesClient([Decimal("100")] * 31),  # type: ignore[arg-type]
                "LONG",
                margin_usdt=Decimal("123.45"),
            )

            self.assertEqual(payload["actions"][0]["marginUsdt"], "123.45")
            self.assertEqual(payload["actions"][0]["requestedMarginUsdt"], "123.45")
            self.assertEqual(payload["positions"][0]["marginUsdt"], "123.45")
            self.assertGreater(Decimal(payload["availableBalanceUsdt"]), Decimal("0"))

    def test_manual_futures_paper_trade_uses_requested_margin_percent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            payload = manual_futures_paper_trade(
                settings,
                FakeFuturesClient([Decimal("100")] * 31),  # type: ignore[arg-type]
                "SHORT",
                margin_percent=Decimal("50"),
            )

            self.assertEqual(payload["actions"][0]["marginPercent"], "50")
            self.assertAlmostEqual(
                Decimal(payload["actions"][0]["marginUsdt"]),
                Decimal("480.7692307692307692307692308"),
            )
            self.assertEqual(payload["positions"][0]["side"], "SHORT")

    def test_manual_futures_paper_trade_switches_short_to_long(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            exit_basis=MANUAL_HOLD_EXIT_BASIS,
                        )
                    },
                )
            )

            payload = manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("99")] * 31), "LONG")  # type: ignore[arg-type]

            self.assertEqual([action["type"] for action in payload["actions"]], ["CLOSE", "OPEN"])
            self.assertEqual(payload["actions"][0]["side"], "SHORT")
            self.assertEqual(payload["actions"][1]["side"], "LONG")
            self.assertEqual(payload["positions"][0]["side"], "LONG")
            self.assertEqual(payload["positions"][0]["exitBasis"], MANUAL_HOLD_EXIT_BASIS)

    def test_manual_futures_paper_trade_same_side_keeps_position_without_churn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            exit_basis=MANUAL_HOLD_EXIT_BASIS,
                        )
                    },
                )
            )

            payload = manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("100")] * 31), "LONG")  # type: ignore[arg-type]

            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["orderCount"], 0)
            self.assertEqual(payload["positions"][0]["quantity"], "10")
            self.assertEqual(payload["manualAction"], "LONG")

    def test_manual_futures_paper_trade_same_side_resizes_when_amount_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            exit_basis=MANUAL_HOLD_EXIT_BASIS,
                        )
                    },
                    manual_action="LONG",
                )
            )

            payload = manual_futures_paper_trade(
                settings,
                FakeFuturesClient([Decimal("101")] * 31),  # type: ignore[arg-type]
                "LONG",
                margin_usdt=Decimal("25"),
            )

            self.assertEqual([action["type"] for action in payload["actions"]], ["CLOSE", "OPEN"])
            self.assertEqual(payload["actions"][0]["side"], "LONG")
            self.assertEqual(payload["actions"][1]["side"], "LONG")
            self.assertEqual(payload["positions"][0]["marginUsdt"], "25")
            self.assertEqual(payload["manualAction"], "LONG")

    def test_manual_futures_paper_trade_stop_closes_without_reopening(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            exit_basis=MANUAL_HOLD_EXIT_BASIS,
                        )
                    },
                )
            )

            payload = manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("101")] * 31), "STOP")  # type: ignore[arg-type]

            self.assertEqual(payload["manualAction"], "STOP")
            self.assertEqual(payload["actions"][0]["type"], "CLOSE")
            self.assertEqual(payload["openPositions"], 0)
            self.assertEqual(payload["executionSide"], "FLAT")

    def test_manual_futures_paper_stop_blocks_automatic_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )

            manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("100")] * 31), "STOP")  # type: ignore[arg-type]
            payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["manualAction"], "STOP")
            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 0)
            self.assertIn("automatic entries skipped", payload["message"])

    def test_manual_futures_paper_auto_clears_manual_mode_without_closing_position(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("100")] * 31), "LONG")  # type: ignore[arg-type]

            payload = manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("101")] * 31), "AUTO")  # type: ignore[arg-type]

            self.assertFalse(payload["manualMode"])
            self.assertIsNone(payload["manualAction"])
            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["exitBasis"], AUTO_RELEASED_MANUAL_EXIT_BASIS)

    def test_manual_futures_paper_manual_freezes_existing_position(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            exit_basis="maeuknam_card_levels",
                            stop_price=Decimal("101"),
                            target1_price=Decimal("99"),
                            target2_price=Decimal("98"),
                        )
                    },
                )
            )

            payload = manual_futures_paper_trade(settings, FakeFuturesClient([Decimal("100")] * 31), "MANUAL")  # type: ignore[arg-type]

            self.assertTrue(payload["manualMode"])
            self.assertEqual(payload["manualAction"], "SHORT")
            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["positions"][0]["exitBasis"], MANUAL_HOLD_EXIT_BASIS)

    def test_maeuknam_futures_mode_respects_min_hold_before_signal_flip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                strategy_name="maeuknam_cards",
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("10"),
                            entry_price=Decimal("100"),
                            leverage=MAEUKNAM_EXPERIMENT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2999-01-01T00:00:00+00:00",
                            reason="maeuknam-card: resistance failure short",
                            stop_price=Decimal("200"),
                            target1_price=Decimal("50"),
                            target2_price=Decimal("40"),
                            exit_basis="maeuknam_card",
                        )
                    },
                )
            )

            with patch("upbit_autotrader.binance_paper.evaluate_maeuknam_techniques", return_value=maeuknam_signal(True, "LONG")):
                payload = run_futures_paper_cycle(settings, FakeFuturesClient(increasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(MAEUKNAM_MIN_HOLD_SECONDS, Decimal("120"))
            self.assertEqual(payload["actions"], [])
            self.assertEqual(payload["openPositions"], 1)
            self.assertEqual(payload["positions"][0]["side"], "SHORT")
            self.assertEqual(payload["maeuknamEntryPolicy"]["minHoldSeconds"], "120")

    def test_existing_long_is_closed_when_short_only_mode_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="LONG",
                            quantity=Decimal("1"),
                            entry_price=Decimal("100"),
                            leverage=Decimal("6"),
                            margin_usdt=Decimal("200"),
                            opened_at="2026-01-01T00:00:00+00:00",
                        )
                    },
                )
            )

            payload = run_futures_paper_cycle(settings, FakeFuturesClient(decreasing_prices()))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "CLOSE")
            self.assertIn("leverage changed", payload["actions"][0]["reason"])
            self.assertEqual(payload["actions"][1]["type"], "OPEN")
            self.assertEqual(payload["actions"][1]["analysisSide"], "SHORT")
            self.assertEqual(payload["actions"][1]["executionSide"], "LONG")
            self.assertEqual(payload["openPositions"], 1)
            self.assertIsNone(payload["entryBlockReason"])

    def test_run_cycle_opens_multiple_aggressive_positions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"),
            )

            payload = run_futures_paper_cycle(settings, FakeFuturesClient(decreasing_prices()))  # type: ignore[arg-type]

            self.assertTrue(payload["simulated"])
            self.assertEqual(payload["openPositions"], MAX_OPEN_POSITIONS)
            self.assertEqual(len([action for action in payload["actions"] if action["type"] == "OPEN"]), MAX_OPEN_POSITIONS)
            self.assertEqual(payload["currency"], "USDT")
            self.assertGreater(Decimal(payload["usedMarginUsdt"]), Decimal("995"))
            self.assertGreaterEqual(Decimal(payload["availableBalanceUsdt"]), Decimal("-0.000001"))
            self.assertLess(Decimal(payload["availableBalanceUsdt"]), Decimal("1"))
            self.assertGreater(Decimal(payload["totalNotionalUsdt"]), Decimal("9950"))

    def test_realtime_status_payload_uses_binance_futures_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT", "ETHUSDT"),
            )
            cycle = run_futures_paper_cycle(settings, FakeFuturesClient(decreasing_prices()))  # type: ignore[arg-type]

            payload = binance_futures_realtime_status_payload(settings, cycle, cycle)
            plan = payload["last"]["plan"]

            self.assertEqual(payload["scope"], "binance_usdm_futures")
            self.assertEqual(plan["scopeLabel"], "바이낸스 USD-M 선물 실시간 분석")
            self.assertEqual(plan["strategySide"], "CONTRARIAN")
            self.assertEqual(plan["analysisSide"], "SHORT")
            self.assertEqual(plan["executionSide"], "LONG")
            self.assertEqual(plan["evaluatedCount"], 2)
            self.assertEqual(plan["situations"][0]["exchangeMode"], "binance_futures_paper")
            self.assertIn(plan["situations"][0]["action"], {"short", "long", "hold", "watch"})

    def test_realtime_status_payload_labels_maeuknam_cards_without_runtime_cycle(self) -> None:
        settings = TradingSettings(strategy_name="maeuknam_cards")

        payload = binance_futures_realtime_status_payload(
            settings,
            {},
            {
                "strategySide": "MAEUKNAM_CARDS",
                "analysisSide": "CARD_DIRECTION",
                "executionSide": "CARD_DIRECTION",
                "positions": [],
            },
        )
        plan = payload["last"]["plan"]

        self.assertIn("Maeuknam Cards", payload["last"]["mode"])
        self.assertEqual(plan["strategySide"], "MAEUKNAM_CARDS")
        self.assertEqual(plan["analysisSide"], "CARD_DIRECTION")
        self.assertEqual(plan["executionSide"], "CARD_DIRECTION")

    def test_realtime_status_payload_labels_alex_method_without_runtime_cycle(self) -> None:
        settings = TradingSettings(strategy_name="alex_method")

        payload = binance_futures_realtime_status_payload(
            settings,
            {},
            {
                "strategySide": ALEX_STRATEGY_SIDE,
                "analysisSide": "CARD_DIRECTION",
                "executionSide": "CARD_DIRECTION",
                "positions": [],
            },
        )
        plan = payload["last"]["plan"]

        self.assertIn("Alex Method", payload["last"]["mode"])
        self.assertEqual(plan["strategySide"], ALEX_STRATEGY_SIDE)
        self.assertEqual(plan["analysisSide"], "CARD_DIRECTION")
        self.assertEqual(plan["executionSide"], "CARD_DIRECTION")

    def test_realtime_status_payload_uses_all_symbol_universe_count(self) -> None:
        settings = TradingSettings(binance_futures_symbols=("BTCUSDT",))
        client = AllSymbolsFuturesClient(
            decreasing_prices(),
            ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"),
        )
        scan = scan_futures_paper_candidates(settings, client)  # type: ignore[arg-type]
        cycle = {
            "candidates": [candidate.to_dict() for candidate in scan.candidates],
            "actions": [],
            "universeCount": scan.universe_count,
            "evaluatedCount": scan.evaluated_count,
            "universeSource": scan.universe_source,
            "tickerCount": scan.ticker_count,
            "deepAnalysisCount": scan.deep_analysis_count,
        }

        payload = binance_futures_realtime_status_payload(settings, cycle, {"positions": []})
        plan = payload["last"]["plan"]

        self.assertEqual(payload["watchTopN"], 5)
        self.assertEqual(plan["universeCount"], 5)
        self.assertEqual(plan["evaluatedCount"], 5)
        self.assertEqual(plan["universeSource"], "binance_exchange_info_usdt_perpetual")

    def test_flat_regime_closes_positions_instead_of_repeated_topups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        symbol: FuturesPaperPosition(
                            symbol=symbol,
                            side="SHORT",
                            quantity=Decimal("5"),
                            entry_price=Decimal("100"),
                            leverage=DEFAULT_LEVERAGE,
                            margin_usdt=Decimal("100"),
                            opened_at="2026-01-01T00:00:00+00:00",
                        )
                        for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
                    },
                )
            )

            payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("100")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["openPositions"], 0)
            self.assertEqual(len([action for action in payload["actions"] if action["type"] == "CLOSE"]), MAX_OPEN_POSITIONS)
            self.assertEqual(len([action for action in payload["actions"] if action["type"] == "INCREASE"]), 0)
            self.assertEqual(payload["marketRegime"]["tradeSide"], "FLAT")

    def test_short_pnl_and_roe_follow_binance_linear_futures_formula(self) -> None:
        state = FuturesPaperState(
            wallet_balance_usdt=Decimal("1000"),
            positions={
                "BTCUSDT": FuturesPaperPosition(
                    symbol="BTCUSDT",
                    side="SHORT",
                    quantity=Decimal("50"),
                    entry_price=Decimal("100"),
                    leverage=Decimal("5"),
                    margin_usdt=Decimal("1000"),
                    opened_at="2026-01-01T00:00:00+00:00",
                )
            },
        )

        payload = state_payload(state, {"BTCUSDT": Decimal("99")})
        position = payload["positions"][0]

        self.assertEqual(position["priceMovePct"], "1")
        self.assertEqual(position["unrealizedPnlUsdt"], "50")
        self.assertEqual(position["returnOnMarginPct"], "5")
        self.assertEqual(payload["usedMarginUsdt"], "1000")
        self.assertEqual(payload["totalNotionalUsdt"], "4950")

    def test_reset_futures_paper_state_starts_from_requested_usdt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(state_file=Path(tmp) / "paper_state.json")

            state = reset_futures_paper_state(settings, Decimal("1000"))

            self.assertEqual(state.wallet_balance_usdt, Decimal("1000"))
            self.assertEqual(state.positions, {})

    def test_profitable_short_is_closed_before_new_cycle_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(
                state_file=Path(tmp) / "paper_state.json",
                binance_futures_symbols=("BTCUSDT",),
            )
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "BTCUSDT": FuturesPaperPosition(
                            symbol="BTCUSDT",
                            side="SHORT",
                            quantity=Decimal("20"),
                            entry_price=Decimal("100"),
                            leverage=Decimal("3"),
                            margin_usdt=Decimal("666.6666666667"),
                            opened_at="2026-01-01T00:00:00+00:00",
                            reason="test",
                        )
                    },
                )
            )

            payload = run_futures_paper_cycle(settings, FakeFuturesClient([Decimal("99")] * 30))  # type: ignore[arg-type]

            self.assertEqual(payload["actions"][0]["type"], "CLOSE")
            self.assertEqual(payload["actions"][0]["side"], "SHORT")
            self.assertGreater(Decimal(payload["actions"][0]["realizedAfterFeeUsdt"]), Decimal("0"))

    def test_exchange_mode_defaults_to_futures_paper_when_position_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(state_file=Path(tmp) / "paper_state.json")
            store = FuturesPaperStateStore(Path(tmp) / "binance_futures_paper_state.json")
            store.save(
                FuturesPaperState(
                    wallet_balance_usdt=Decimal("1000"),
                    positions={
                        "ETHUSDT": FuturesPaperPosition(
                            symbol="ETHUSDT",
                            side="LONG",
                            quantity=Decimal("1"),
                            entry_price=Decimal("2000"),
                            leverage=Decimal("3"),
                            margin_usdt=Decimal("500"),
                            opened_at="2026-01-01T00:00:00+00:00",
                        )
                    },
                )
            )

            self.assertEqual(load_exchange_mode(settings), "binance_futures_paper")
            payload = exchange_mode_payload(settings)
            self.assertEqual(payload["active"], "binance_futures_paper")

    def test_saved_exchange_mode_overrides_default_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = TradingSettings(state_file=Path(tmp) / "paper_state.json")

            save_exchange_mode(settings, "binance_spot")

            self.assertEqual(load_exchange_mode(settings), "binance_spot")


if __name__ == "__main__":
    unittest.main()
