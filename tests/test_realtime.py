from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.realtime import (
    RealtimeMarketCache,
    decode_websocket_message,
    subscription_payload,
)


class RealtimeTests(unittest.TestCase):
    def test_subscription_payload_requests_ticker_and_trade(self) -> None:
        payload = subscription_payload(["krw-btc", "KRW-ETH", "KRW-BTC"])

        self.assertEqual(payload[1]["type"], "ticker")
        self.assertEqual(payload[1]["codes"], ["KRW-BTC", "KRW-ETH"])
        self.assertTrue(payload[1]["is_only_realtime"])
        self.assertEqual(payload[2]["type"], "trade")

    def test_cache_normalizes_ticker_and_trade_messages(self) -> None:
        cache = RealtimeMarketCache(("KRW-BTC",))
        cache.update(
            {
                "type": "ticker",
                "code": "KRW-BTC",
                "trade_price": 1000,
                "signed_change_rate": -0.01,
                "acc_trade_price_24h": 123456,
            }
        )
        cache.update(
            {
                "type": "trade",
                "code": "KRW-BTC",
                "trade_price": 990,
                "trade_volume": 0.5,
                "ask_bid": "ASK",
            }
        )
        snapshot = cache.snapshot()

        self.assertEqual(snapshot["tickers"]["KRW-BTC"]["tradePrice"], 1000)
        self.assertEqual(snapshot["tickers"]["KRW-BTC"]["signedChangeRate"], -0.01)
        self.assertEqual(snapshot["trades"]["KRW-BTC"][0]["tradePrice"], 990)
        self.assertEqual(snapshot["trades"]["KRW-BTC"][0]["askBid"], "ASK")

    def test_decode_websocket_message_accepts_bytes(self) -> None:
        encoded = json.dumps({"type": "ticker", "code": "KRW-BTC"}).encode("utf-8")

        self.assertEqual(decode_websocket_message(encoded)[0]["code"], "KRW-BTC")


if __name__ == "__main__":
    unittest.main()
