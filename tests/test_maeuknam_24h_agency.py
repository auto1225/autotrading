from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "maeuknam_24h_agency.py"
SPEC = importlib.util.spec_from_file_location("maeuknam_24h_agency", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
agency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agency)


class Maeuknam24hAgencyTests(unittest.TestCase):
    def test_should_reset_when_equity_is_depleted(self) -> None:
        should_reset, reason = agency.should_reset_paper_account(
            {"equityUsdt": "9.99", "walletBalanceUsdt": "9.99", "openPositions": 0},
            Decimal("10"),
        )

        self.assertTrue(should_reset)
        self.assertIn("equity", reason)

    def test_should_not_reset_healthy_account(self) -> None:
        should_reset, reason = agency.should_reset_paper_account(
            {"equityUsdt": "1000", "walletBalanceUsdt": "1000", "openPositions": 0},
            Decimal("10"),
        )

        self.assertFalse(should_reset)
        self.assertEqual(reason, "not depleted")

    def test_should_reset_operational_halt_when_fee_cap_deadlocks(self) -> None:
        should_reset, reason = agency.should_reset_operational_halt(
            {
                "entryBlockReason": "fee drag 10.5% reached cap 10%",
                "actions": [],
                "paper": {"openPositions": 0, "secondsSinceLastOrder": 3600},
            },
            1800,
        )

        self.assertTrue(should_reset)
        self.assertIn("fee cap operational halt", reason)

    def test_should_not_reset_operational_halt_when_disabled(self) -> None:
        should_reset, reason = agency.should_reset_operational_halt(
            {
                "entryBlockReason": "fee drag 10.5% reached cap 10%",
                "actions": [],
                "paper": {"openPositions": 0, "secondsSinceLastOrder": 3600},
            },
            0,
        )

        self.assertFalse(should_reset)
        self.assertEqual(reason, "fee cap reset disabled")

    def test_observation_flags_inverse_risk_from_higher_timeframes(self) -> None:
        status = {
            "binanceFuturesPaper": {
                "walletBalanceUsdt": "1000",
                "equityUsdt": "1000",
                "feesPaidUsdt": "0",
                "openPositions": 0,
                "orderCount": 0,
            }
        }
        realtime = {
            "last": {
                "plan": {
                    "situations": [
                        {
                            "symbol": "BTCUSDT",
                            "side": "SHORT",
                            "entryStage": "agency",
                            "entryAllowed": False,
                            "entryBlockReason": "investment agency veto",
                            "timeframeContext": {
                                "1d": {"alignment": "opposed"},
                                "1w": {"alignment": "aligned"},
                                "1M": {"alignment": "opposed"},
                            },
                            "maeuknamSignal": {"techniqueId": "resistance_failure_short", "score": "0.5"},
                        }
                    ],
                    "actions": [],
                }
            }
        }

        observation = agency.build_observation(status, realtime)

        codes = {issue["code"] for issue in observation["issues"]}
        self.assertIn("agency_veto", codes)
        self.assertIn("inverse_risk", codes)
        self.assertEqual(observation["candidate"]["htf"]["opposed"], 2)

    def test_observation_surfaces_global_entry_block_reason(self) -> None:
        status = {
            "binanceFuturesPaper": {
                "walletBalanceUsdt": "715",
                "equityUsdt": "715",
                "feesPaidUsdt": "388",
                "openPositions": 0,
                "orderCount": 60,
                "lastOrderAt": datetime.now(timezone.utc).isoformat(),
            }
        }
        realtime = {
            "last": {
                "plan": {
                    "entryBlockReason": "fee drag 54% reached cap 25%",
                    "situations": [
                        {
                            "symbol": "BTCUSDT",
                            "side": "LONG",
                            "entryStage": "inverse_agency",
                            "entryAllowed": True,
                            "entryBlockReason": "inverse agency entry allowed",
                            "maeuknamSignal": {"techniqueId": "inverse_agency_resistance_failure_short", "score": "0.52"},
                        }
                    ],
                    "actions": [],
                }
            }
        }

        observation = agency.build_observation(status, realtime)

        codes = {issue["code"] for issue in observation["issues"]}
        self.assertEqual(observation["entryBlockReason"], "fee drag 54% reached cap 25%")
        self.assertIn("entry_block", codes)
        self.assertIn("fee_drag", codes)

    def test_observation_flags_no_trade_deadlock_when_fee_block_persists(self) -> None:
        status = {
            "binanceFuturesPaper": {
                "walletBalanceUsdt": "715",
                "equityUsdt": "715",
                "feesPaidUsdt": "388",
                "openPositions": 0,
                "orderCount": 60,
                "lastOrderAt": (datetime.now(timezone.utc) - timedelta(seconds=1900)).isoformat(),
            }
        }
        realtime = {
            "last": {
                "plan": {
                    "entryBlockReason": "fee drag 54% reached cap 25%",
                    "situations": [
                        {
                            "symbol": "BTCUSDT",
                            "side": "LONG",
                            "entryStage": "entry",
                            "entryAllowed": True,
                            "entryBlockReason": "card-only entry allowed",
                            "maeuknamSignal": {"techniqueId": "breakout_retest_long", "score": "0.8"},
                        }
                    ],
                    "actions": [],
                }
            }
        }

        observation = agency.build_observation(status, realtime)

        codes = {issue["code"] for issue in observation["issues"]}
        self.assertIn("no_trade_deadlock", codes)
        self.assertGreaterEqual(observation["paper"]["secondsSinceLastOrder"], 1800)

    def test_observation_uses_reset_action_code(self) -> None:
        status = {
            "binanceFuturesPaper": {
                "walletBalanceUsdt": "1000",
                "equityUsdt": "1000",
                "feesPaidUsdt": "0",
                "openPositions": 0,
                "orderCount": 0,
            }
        }
        realtime = {"last": {"plan": {"situations": [], "actions": []}}}

        observation = agency.build_observation(
            status,
            realtime,
            reset_action={"code": "operational_reset", "reason": "fee cap operational halt"},
        )

        codes = {issue["code"] for issue in observation["issues"]}
        self.assertIn("operational_reset", codes)
        self.assertNotIn("depleted_reset", codes)

    def test_observation_flags_protective_wait_when_candidate_veto_persists(self) -> None:
        status = {
            "binanceFuturesPaper": {
                "walletBalanceUsdt": "967",
                "equityUsdt": "967",
                "feesPaidUsdt": "29",
                "openPositions": 0,
                "orderCount": 6,
                "lastOrderAt": (datetime.now(timezone.utc) - timedelta(seconds=3600)).isoformat(),
            }
        }
        realtime = {
            "last": {
                "plan": {
                    "situations": [
                        {
                            "symbol": "BTCUSDT",
                            "side": "SHORT",
                            "entryStage": "agency",
                            "entryAllowed": False,
                            "entryBlockReason": "investment agency veto: 2/3 higher timeframes oppose card direction",
                            "maeuknamSignal": {"techniqueId": "resistance_failure_short", "score": "0.62"},
                        }
                    ],
                    "actions": [],
                }
            }
        }

        observation = agency.build_observation(status, realtime)

        codes = {issue["code"] for issue in observation["issues"]}
        self.assertIn("agency_veto", codes)
        self.assertIn("protective_wait", codes)
        self.assertNotIn("no_trade_deadlock", codes)
        self.assertTrue(any("candidate entry block" in issue["message"] for issue in observation["issues"]))

    def test_update_report_writes_status_events_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            observation = {
                "observedAt": "2026-01-01T00:00:00+00:00",
                "paper": {"walletBalanceUsdt": "1000", "equityUsdt": "1000"},
                "candidate": {"symbol": "BTCUSDT", "side": "LONG", "entryStage": "entry"},
                "entryBlockReason": "",
                "issues": [{"code": "sample", "level": "warning", "message": "sample issue"}],
                "actions": [],
                "resetAction": None,
                "fingerprint": "sample",
            }

            status = agency.update_report(
                report_dir,
                observation,
                started_at="2026-01-01T00:00:00+00:00",
                ends_at="2026-01-02T00:00:00+00:00",
            )

            self.assertEqual(status["counters"]["cycles"], 1)
            self.assertTrue((report_dir / "status.json").exists())
            self.assertTrue((report_dir / "events.jsonl").exists())
            self.assertTrue((report_dir / "report.md").exists())

    def test_update_report_starts_new_window_after_previous_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            observation = {
                "observedAt": "2026-01-03T00:01:00+00:00",
                "paper": {"walletBalanceUsdt": "1000", "equityUsdt": "1000"},
                "candidate": {"symbol": "BTCUSDT", "side": "SHORT", "entryStage": "card"},
                "entryBlockReason": "",
                "issues": [{"code": "sample", "level": "warning", "message": "sample issue"}],
                "actions": [],
                "resetAction": None,
                "fingerprint": "sample",
            }
            previous = {
                "startedAt": "2026-01-01T00:00:00+00:00",
                "endsAt": "2026-01-02T00:00:00+00:00",
                "lastFingerprint": "sample",
                "counters": {"cycles": 99, "issueCounts": {"old": 3}},
                "latestObservation": observation,
            }
            agency.write_json(report_dir / "status.json", previous)

            status = agency.update_report(
                report_dir,
                observation,
                started_at="2026-01-03T00:00:00+00:00",
                ends_at="2026-01-04T00:00:00+00:00",
            )

            self.assertEqual(status["startedAt"], "2026-01-03T00:00:00+00:00")
            self.assertEqual(status["endsAt"], "2026-01-04T00:00:00+00:00")
            self.assertEqual(status["counters"]["cycles"], 1)
            self.assertNotIn("old", status["counters"]["issueCounts"])


if __name__ == "__main__":
    unittest.main()
