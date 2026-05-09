from __future__ import annotations

import asyncio
import json
from collections import deque
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


UPBIT_PUBLIC_WEBSOCKET_URL = "wss://api.upbit.com/websocket/v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RealtimeMarketCache:
    markets: tuple[str, ...]
    ticker_by_market: dict[str, dict[str, Any]] = field(default_factory=dict)
    trades_by_market: dict[str, deque[dict[str, Any]]] = field(default_factory=dict)
    connected: bool = False
    reconnects: int = 0
    last_error: str | None = None
    last_message_at: str | None = None
    started_at: str | None = None

    def update(self, payload: dict[str, Any]) -> None:
        message_type = str(payload.get("type") or payload.get("ty") or "")
        if message_type == "ticker":
            ticker = normalize_ticker(payload)
            if ticker["market"]:
                self.ticker_by_market[ticker["market"]] = ticker
                self.last_message_at = utc_now_iso()
                self.last_error = None
        elif message_type == "trade":
            trade = normalize_trade(payload)
            if trade["market"]:
                bucket = self.trades_by_market.setdefault(trade["market"], deque(maxlen=30))
                bucket.appendleft(trade)
                self.last_message_at = utc_now_iso()
                self.last_error = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "reconnects": self.reconnects,
            "lastError": self.last_error,
            "lastMessageAt": self.last_message_at,
            "startedAt": self.started_at,
            "tickers": {market: self.ticker_by_market.get(market, {}) for market in self.markets},
            "trades": {market: list(self.trades_by_market.get(market, []))[:10] for market in self.markets},
        }


class UpbitRealtimeService:
    def __init__(
        self,
        markets: Iterable[str],
        endpoint: str = UPBIT_PUBLIC_WEBSOCKET_URL,
        reconnect_delay_seconds: float = 3,
    ) -> None:
        self.markets = tuple(dict.fromkeys(market.upper() for market in markets))
        self.endpoint = endpoint
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.cache = RealtimeMarketCache(self.markets)
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self.cache.started_at = utc_now_iso()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="upbit-realtime")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self.cache.connected = False

    def snapshot(self) -> dict[str, Any]:
        return self.cache.snapshot()

    async def _run(self) -> None:
        import websockets

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self.endpoint,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                    max_queue=1024,
                ) as websocket:
                    self.cache.connected = True
                    self.cache.last_error = None
                    await websocket.send(json.dumps(subscription_payload(self.markets)))
                    async for message in websocket:
                        if self._stop_event.is_set():
                            break
                        for payload in decode_websocket_message(message):
                            self.cache.update(payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # Reconnect in the background without crashing FastAPI.
                self.cache.last_error = str(exc)
            finally:
                self.cache.connected = False

            if not self._stop_event.is_set():
                self.cache.reconnects += 1
                await asyncio.sleep(self.reconnect_delay_seconds)


def subscription_payload(markets: Iterable[str]) -> list[dict[str, Any]]:
    codes = list(dict.fromkeys(market.upper() for market in markets))
    return [
        {"ticket": "upbit-autotrader"},
        {"type": "ticker", "codes": codes, "is_only_realtime": True},
        {"type": "trade", "codes": codes, "is_only_realtime": True},
    ]


def decode_websocket_message(message: str | bytes) -> list[dict[str, Any]]:
    text = message.decode("utf-8") if isinstance(message, bytes) else message
    payload = json.loads(text)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def normalize_ticker(payload: dict[str, Any]) -> dict[str, Any]:
    market = str(payload.get("code") or payload.get("market") or payload.get("cd") or "")
    return {
        "market": market,
        "tradePrice": payload.get("trade_price", payload.get("tp")),
        "change": payload.get("change", payload.get("c", "EVEN")),
        "changeRate": payload.get("change_rate", payload.get("cr", 0)),
        "signedChangeRate": payload.get("signed_change_rate", payload.get("scr", 0)),
        "tradeVolume": payload.get("trade_volume", payload.get("tv", 0)),
        "tradeValue24h": payload.get("acc_trade_price_24h", payload.get("atp24h", 0)),
        "timestamp": payload.get("timestamp", payload.get("tms")),
        "streamType": payload.get("stream_type", payload.get("st")),
        "source": "websocket",
    }


def normalize_trade(payload: dict[str, Any]) -> dict[str, Any]:
    market = str(payload.get("code") or payload.get("market") or payload.get("cd") or "")
    return {
        "market": market,
        "tradePrice": payload.get("trade_price", payload.get("tp")),
        "tradeVolume": payload.get("trade_volume", payload.get("tv")),
        "askBid": payload.get("ask_bid", payload.get("ab")),
        "timestamp": payload.get("timestamp", payload.get("tms")),
        "tradeTimestamp": payload.get("trade_timestamp", payload.get("ttms")),
        "sequentialId": payload.get("sequential_id", payload.get("sid")),
        "streamType": payload.get("stream_type", payload.get("st")),
    }
