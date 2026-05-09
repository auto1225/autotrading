from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import load_settings
from upbit_autotrader.database import SqliteStore


class SqliteStoreTests(unittest.TestCase):
    def test_append_event_records_recent_event_and_paper_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteStore(Path(temp_dir) / "autotrading.sqlite3")

            store.append_event(
                "paper_order",
                {
                    "market": "KRW-BTC",
                    "ok": True,
                    "message": "paper filled",
                    "raw": {"market": "KRW-BTC", "side": "bid", "spent_krw": "5000", "volume": "0.1"},
                },
            )

            events = store.recent_events()
            status = store.status()

            self.assertEqual(events[0]["type"], "paper_order")
            self.assertEqual(events[0]["payload"]["market"], "KRW-BTC")
            self.assertEqual(status["counts"]["events"], 1)
            self.assertEqual(status["counts"]["paper_orders"], 1)

    def test_records_snapshots_and_backtest_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteStore(Path(temp_dir) / "autotrading.sqlite3")

            store.append_portfolio_snapshot(
                {
                    "cashKrw": "1000000",
                    "positionValueKrw": "0",
                    "equityKrw": "1000000",
                    "realizedPnlKrw": "0",
                    "feesPaidKrw": "0",
                    "orderCount": 0,
                    "openPositions": 0,
                }
            )
            stored = store.append_backtest_reports(
                "guarded_momentum",
                [
                    {
                        "market": "KRW-BTC",
                        "totalReturnPct": "1.2",
                        "maxDrawdownPct": "-0.4",
                        "finalEquityKrw": "1012000",
                        "orderCount": 2,
                    }
                ],
            )

            status = store.status()
            snapshots = store.recent_portfolio_snapshots()

            self.assertEqual(stored, 1)
            self.assertEqual(status["counts"]["portfolio_snapshots"], 1)
            self.assertEqual(snapshots[-1]["positionValueKrw"], "0")
            self.assertEqual(snapshots[-1]["payload"]["equityKrw"], "1000000")
            self.assertEqual(status["counts"]["backtest_reports"], 1)
            self.assertTrue(status["exists"])

    def test_records_learning_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteStore(Path(temp_dir) / "autotrading.sqlite3")

            row_id = store.append_learning_run(
                {
                    "candleUnit": 5,
                    "candleCount": 400,
                    "marketCount": 1,
                    "strategyCount": 2,
                    "overall": {"strategy": "sma_cross", "score": "1.2"},
                    "ranking": [{"market": "KRW-BTC", "strategy": "sma_cross", "score": "1.2"}],
                }
            )
            latest = store.latest_learning_run()
            status = store.status()

            self.assertGreater(row_id, 0)
            self.assertIsNotNone(latest)
            self.assertEqual(status["counts"]["learning_runs"], 1)

    def test_settings_loads_database_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("DATABASE_FILE=state/custom.sqlite3\n", encoding="utf-8")

            settings = load_settings(env_path)

            self.assertEqual(settings.database_file, Path("state/custom.sqlite3"))


if __name__ == "__main__":
    unittest.main()
