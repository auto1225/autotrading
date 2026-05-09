from __future__ import annotations

from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable
import json
import sqlite3


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _load_json(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


class SqliteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                self._initialize(connection)

    def append_event(self, event_type: str, payload: dict[str, Any], created_at: str | None = None) -> int:
        created_at = created_at or utc_now_iso()
        market = str(payload.get("market") or "") or None
        with closing(self._connect()) as connection:
            with connection:
                self._initialize(connection)
                cursor = connection.execute(
                    """
                    INSERT INTO events (created_at, type, market, payload_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (created_at, event_type, market, _json(payload)),
                )
                if event_type == "paper_order":
                    self._append_paper_order(connection, created_at, payload)
                return int(cursor.lastrowid)

    def append_portfolio_snapshot(self, payload: dict[str, Any], created_at: str | None = None) -> int:
        created_at = created_at or utc_now_iso()
        with closing(self._connect()) as connection:
            with connection:
                self._initialize(connection)
                cursor = connection.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        created_at,
                        cash_krw,
                        position_value_krw,
                        equity_krw,
                        realized_pnl_krw,
                        fees_paid_krw,
                        order_count,
                        open_positions,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        str(payload.get("cashKrw", "0")),
                        str(payload.get("positionValueKrw", "0")),
                        str(payload.get("equityKrw", "0")),
                        str(payload.get("realizedPnlKrw", "0")),
                        str(payload.get("feesPaidKrw", "0")),
                        int(payload.get("orderCount", 0) or 0),
                        int(payload.get("openPositions", 0) or 0),
                        _json(payload),
                    ),
                )
                return int(cursor.lastrowid)

    def append_backtest_reports(
        self,
        strategy: str,
        reports: Iterable[dict[str, Any]],
        created_at: str | None = None,
    ) -> int:
        created_at = created_at or utc_now_iso()
        rows = [
            (
                created_at,
                strategy,
                str(report.get("market") or ""),
                str(report.get("totalReturnPct", "0")),
                str(report.get("maxDrawdownPct", "0")),
                str(report.get("finalEquityKrw", "0")),
                int(report.get("orderCount", 0) or 0),
                _json(report),
            )
            for report in reports
        ]
        if not rows:
            return 0
        with closing(self._connect()) as connection:
            with connection:
                self._initialize(connection)
                connection.executemany(
                    """
                    INSERT INTO backtest_reports (
                        created_at,
                        strategy,
                        market,
                        total_return_pct,
                        max_drawdown_pct,
                        final_equity_krw,
                        order_count,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
        return len(rows)

    def append_learning_run(self, payload: dict[str, Any], created_at: str | None = None) -> int:
        created_at = created_at or utc_now_iso()
        overall = payload.get("overall") if isinstance(payload.get("overall"), dict) else {}
        ranking = payload.get("ranking") if isinstance(payload.get("ranking"), list) else []
        best = ranking[0] if ranking and isinstance(ranking[0], dict) else {}
        with closing(self._connect()) as connection:
            with connection:
                self._initialize(connection)
                cursor = connection.execute(
                    """
                    INSERT INTO learning_runs (
                        created_at,
                        candle_unit,
                        candle_count,
                        market_count,
                        strategy_count,
                        best_strategy,
                        best_market,
                        score,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        int(payload.get("candleUnit", 0) or 0),
                        int(payload.get("candleCount", 0) or 0),
                        int(payload.get("marketCount", 0) or 0),
                        int(payload.get("strategyCount", 0) or 0),
                        str(overall.get("strategy") or best.get("strategy") or ""),
                        str(best.get("market") or ""),
                        str(overall.get("score") or best.get("score") or "0"),
                        _json(payload),
                    ),
                )
                return int(cursor.lastrowid)

    def latest_learning_run(self) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            self._initialize(connection)
            row = connection.execute(
                """
                SELECT created_at, payload_json
                FROM learning_runs
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return {
            "time": row["created_at"],
            "payload": _load_json(row["payload_json"]),
        }

    def recent_events(self, limit: int = 80) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            self._initialize(connection)
            rows = connection.execute(
                """
                SELECT created_at, type, payload_json
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, limit),),
            ).fetchall()
        rows.reverse()
        return [
            {
                "time": row["created_at"],
                "type": row["type"],
                "payload": _load_json(row["payload_json"]),
            }
            for row in rows
        ]

    def recent_portfolio_snapshots(self, limit: int = 2000) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            self._initialize(connection)
            rows = connection.execute(
                """
                SELECT
                    created_at,
                    cash_krw,
                    position_value_krw,
                    equity_krw,
                    realized_pnl_krw,
                    fees_paid_krw,
                    order_count,
                    open_positions,
                    payload_json
                FROM portfolio_snapshots
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, limit),),
            ).fetchall()
        rows.reverse()
        return [
            {
                "time": row["created_at"],
                "cashKrw": row["cash_krw"],
                "positionValueKrw": row["position_value_krw"],
                "equityKrw": row["equity_krw"],
                "realizedPnlKrw": row["realized_pnl_krw"],
                "feesPaidKrw": row["fees_paid_krw"],
                "orderCount": row["order_count"],
                "openPositions": row["open_positions"],
                "payload": _load_json(row["payload_json"]),
            }
            for row in rows
        ]

    def status(self) -> dict[str, Any]:
        exists = self.path.exists()
        with closing(self._connect()) as connection:
            self._initialize(connection)
            counts = {
                table: int(
                    connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]  # noqa: S608
                )
                for table in ("events", "paper_orders", "portfolio_snapshots", "backtest_reports", "learning_runs")
            }
            last_event_at = self._single_value(connection, "SELECT MAX(created_at) FROM events")
            last_snapshot_at = self._single_value(connection, "SELECT MAX(created_at) FROM portfolio_snapshots")
            last_backtest_at = self._single_value(connection, "SELECT MAX(created_at) FROM backtest_reports")
            last_learning_at = self._single_value(connection, "SELECT MAX(created_at) FROM learning_runs")
        return {
            "path": str(self.path),
            "exists": exists or self.path.exists(),
            "sizeBytes": self.path.stat().st_size if self.path.exists() else 0,
            "counts": counts,
            "lastEventAt": last_event_at,
            "lastSnapshotAt": last_snapshot_at,
            "lastBacktestAt": last_backtest_at,
            "lastLearningAt": last_learning_at,
        }

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                type TEXT NOT NULL,
                market TEXT,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS paper_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT,
                ok INTEGER NOT NULL,
                message TEXT,
                price_krw TEXT,
                volume TEXT,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                cash_krw TEXT NOT NULL,
                position_value_krw TEXT NOT NULL,
                equity_krw TEXT NOT NULL,
                realized_pnl_krw TEXT NOT NULL,
                fees_paid_krw TEXT NOT NULL,
                order_count INTEGER NOT NULL,
                open_positions INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS backtest_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                strategy TEXT NOT NULL,
                market TEXT NOT NULL,
                total_return_pct TEXT NOT NULL,
                max_drawdown_pct TEXT NOT NULL,
                final_equity_krw TEXT NOT NULL,
                order_count INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS learning_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                candle_unit INTEGER NOT NULL,
                candle_count INTEGER NOT NULL,
                market_count INTEGER NOT NULL,
                strategy_count INTEGER NOT NULL,
                best_strategy TEXT NOT NULL,
                best_market TEXT,
                score TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_created_at ON events (created_at);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events (type);
            CREATE INDEX IF NOT EXISTS idx_paper_orders_created_at ON paper_orders (created_at);
            CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON portfolio_snapshots (created_at);
            CREATE INDEX IF NOT EXISTS idx_backtest_reports_created_at ON backtest_reports (created_at);
            CREATE INDEX IF NOT EXISTS idx_learning_runs_created_at ON learning_runs (created_at);
            """
        )

    def _append_paper_order(
        self,
        connection: sqlite3.Connection,
        created_at: str,
        payload: dict[str, Any],
    ) -> None:
        raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
        connection.execute(
            """
            INSERT INTO paper_orders (
                created_at,
                market,
                side,
                ok,
                message,
                price_krw,
                volume,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                str(payload.get("market") or raw.get("market") or ""),
                str(raw.get("side") or ""),
                1 if payload.get("ok") else 0,
                str(payload.get("message") or ""),
                str(raw.get("spent_krw") or raw.get("received_krw") or ""),
                str(raw.get("volume") or ""),
                _json(payload),
            ),
        )

    @staticmethod
    def _single_value(connection: sqlite3.Connection, query: str) -> Any:
        row = connection.execute(query).fetchone()
        if row is None:
            return None
        return row[0]
