from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.investment_agency import build_investment_agency_report


class InvestmentAgencyTests(unittest.TestCase):
    def test_agency_rejects_without_higher_timeframe_data(self) -> None:
        plan = {
            "situations": [
                {
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "entryAllowed": "true",
                    "closedCandleCount": "30",
                    "timeframeContext": {},
                    "maeuknamSignal": {"entryAllowed": True, "score": "0.82", "direction": "LONG"},
                }
            ],
            "maeuknamEntryPolicy": {
                "closedCandleLimit": 1440,
                "fetchLimit": 1500,
                "openCandleExcluded": True,
                "multiTimeframeIntervals": ["1d", "1w", "1M"],
            },
            "orders": [],
        }

        report = build_investment_agency_report(plan, {}, {})

        self.assertEqual(report["verdict"], "REJECT")
        self.assertFalse(report["entryGate"])
        self.assertEqual(report["dataChecks"][0]["level"], "critical")

    def test_agency_approves_clean_card_with_complete_data_and_order(self) -> None:
        plan = {
            "strategySide": "MAEUKNAM_CARDS",
            "universeSource": "maeuknam_cards_btcusdt_only",
            "situations": [
                {
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "entryAllowed": "true",
                    "closedCandleCount": "1440",
                    "timeframeContext": {
                        "1d": {"count": "1499", "alignment": "aligned", "alignmentScore": "1"},
                        "1w": {"count": "348", "alignment": "aligned", "alignmentScore": "1"},
                        "1M": {"count": "80", "alignment": "neutral", "alignmentScore": "0"},
                    },
                    "maeuknamSignal": {
                        "entryAllowed": True,
                        "score": "0.84",
                        "direction": "LONG",
                        "techniqueId": "support_pullback_long",
                        "hardBlocks": [],
                    },
                }
            ],
            "maeuknamEntryPolicy": {
                "closedCandleLimit": 1440,
                "fetchLimit": 1500,
                "openCandleExcluded": True,
                "multiTimeframeIntervals": ["1d", "1w", "1M"],
            },
            "orders": [{"type": "OPEN", "symbol": "BTCUSDT"}],
        }

        report = build_investment_agency_report(plan, {"positions": []}, {"updatedAt": "2026-05-07T00:00:00+00:00"})

        self.assertEqual(report["verdict"], "APPROVE")
        self.assertTrue(report["entryGate"])
        self.assertEqual(report["counts"]["approve"], 6)

    def test_agency_uses_alex_policy_and_signal_for_alex_method(self) -> None:
        plan = {
            "strategySide": "ALEX_METHOD",
            "universeSource": "alex_method_btcusdt_only",
            "situations": [
                {
                    "symbol": "BTCUSDT",
                    "side": "SHORT",
                    "entryAllowed": "false",
                    "entryBlockReason": "Alex HTF veto: 3/3 higher timeframes oppose entry direction",
                    "closedCandleCount": "1440",
                    "timeframeContext": {
                        "12h": {"count": "4870", "alignment": "opposed", "alignmentScore": "-1"},
                        "30m": {"count": "5000", "alignment": "opposed", "alignmentScore": "-1"},
                        "1d": {"count": "2435", "alignment": "opposed", "alignmentScore": "-1"},
                    },
                    "alexSignal": {
                        "entryAllowed": True,
                        "score": "0.5915",
                        "direction": "SHORT",
                        "techniqueId": "alex_liquidity_premium_short",
                        "hardBlocks": [],
                    },
                }
            ],
            "maeuknamEntryPolicy": {
                "closedCandleLimit": 1440,
                "fetchLimit": 1500,
                "openCandleExcluded": False,
                "multiTimeframeIntervals": ["1d", "1w", "1M"],
            },
            "alexEntryPolicy": {
                "closedCandleLimit": 1440,
                "fetchLimit": 1500,
                "openCandleExcluded": True,
                "multiTimeframeIntervals": ["12h", "30m", "1d"],
            },
            "orders": [],
        }

        report = build_investment_agency_report(plan, {"positions": []}, {"updatedAt": "2026-05-07T00:00:00+00:00"})

        self.assertEqual(report["dataChecks"][1]["value"], "excluded")
        self.assertEqual([check["title"] for check in report["dataChecks"][2:]], [
            "12h higher timeframe history",
            "30m higher timeframe history",
            "1d higher timeframe history",
        ])
        self.assertEqual(report["members"][1]["id"], "alex_strategist")
        self.assertIn("12h/30m/1d alignment", report["members"][2]["body"])


if __name__ == "__main__":
    unittest.main()
