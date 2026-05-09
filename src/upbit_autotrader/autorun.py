from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AutoRunSnapshot:
    running: bool
    intervalSeconds: int
    iterations: int
    lastStartedAt: str | None
    lastRunAt: str | None
    lastFinishedAt: str | None
    lastResultCount: int
    lastError: str | None


class AutoRunController:
    def __init__(self, scan_once: Callable[[], Sequence[dict[str, Any]]], interval_seconds: int) -> None:
        self.scan_once = scan_once
        self.interval_seconds = max(5, interval_seconds)
        self.iterations = 0
        self.last_started_at: str | None = None
        self.last_run_at: str | None = None
        self.last_finished_at: str | None = None
        self.last_result_count = 0
        self.last_error: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self.last_started_at = utc_now_iso()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="autotrading-autorun")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    def snapshot(self) -> dict[str, Any]:
        running = bool(self._task and not self._task.done())
        return AutoRunSnapshot(
            running=running,
            intervalSeconds=self.interval_seconds,
            iterations=self.iterations,
            lastStartedAt=self.last_started_at,
            lastRunAt=self.last_run_at,
            lastFinishedAt=self.last_finished_at,
            lastResultCount=self.last_result_count,
            lastError=self.last_error,
        ).__dict__

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.last_run_at = utc_now_iso()
            try:
                result = await asyncio.to_thread(self.scan_once)
                self.iterations += 1
                self.last_result_count = len(result)
                self.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                self.last_finished_at = utc_now_iso()

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
