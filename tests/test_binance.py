from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import hmac
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.binance_client import BinanceFuturesClient, binance_query_string, binance_signature, candle_from_binance
from upbit_autotrader.config import load_settings


class BinanceClientTests(unittest.TestCase):
    def test_signature_matches_hmac_sha256(self) -> None:
        query = binance_query_string({"symbol": "BTCUSDT", "timestamp": 12345})
        expected = hmac.new(b"secret", query.encode("utf-8"), hashlib.sha256).hexdigest()

        self.assertEqual(query, "symbol=BTCUSDT&timestamp=12345")
        self.assertEqual(binance_signature("secret", query), expected)

    def test_candle_from_binance_maps_ohlcv(self) -> None:
        candle = candle_from_binance(
            "BTCUSDT",
            [1000, "10", "13", "9", "12", "2", 0, "24"],
        )

        self.assertEqual(candle.market, "BTCUSDT")
        self.assertEqual(candle.opening_price, Decimal("10"))
        self.assertEqual(candle.high_price, Decimal("13"))
        self.assertEqual(candle.low_price, Decimal("9"))
        self.assertEqual(candle.trade_price, Decimal("12"))
        self.assertEqual(candle.candle_acc_trade_price, Decimal("24"))

    def test_futures_client_uses_usdm_fapi_paths(self) -> None:
        class RecordingClient(BinanceFuturesClient):
            def __init__(self) -> None:
                super().__init__(api_key="key", secret_key="secret")
                self.calls = []

            def _request_json(self, method, path, params=None, signed=False):  # type: ignore[override]
                self.calls.append((method, path, params, signed))
                return {}

        client = RecordingClient()

        client.ping()
        client.ticker_price("BTCUSDT")
        client.ticker_24hr()
        client.klines("BTCUSDT", interval="1d", limit=1500, end_time=123456)
        client.account()

        self.assertEqual(client.calls[0], ("GET", "/fapi/v1/ping", None, False))
        self.assertEqual(client.calls[1], ("GET", "/fapi/v1/ticker/price", {"symbol": "BTCUSDT"}, False))
        self.assertEqual(client.calls[2], ("GET", "/fapi/v1/ticker/24hr", None, False))
        self.assertEqual(
            client.calls[3],
            (
                "GET",
                "/fapi/v1/klines",
                {"symbol": "BTCUSDT", "interval": "1d", "limit": 1500, "startTime": None, "endTime": 123456},
                False,
            ),
        )
        self.assertEqual(client.calls[4], ("GET", "/fapi/v3/account", None, True))

    def test_settings_loads_binance_futures_config(self) -> None:
        env_path = Path(self.id().replace(".", "_") + ".env")
        try:
            env_path.write_text(
                "\n".join(
                    [
                        "BINANCE_FUTURES_BASE_URL=https://demo-fapi.binance.com",
                        "BINANCE_FUTURES_TESTNET_ENABLED=true",
                        "BINANCE_FUTURES_SYMBOLS=btcusdt,ethusdt,btcusdt",
                        "BINANCE_FUTURES_API_KEY=futures-key",
                        "BINANCE_FUTURES_SECRET_KEY=futures-secret",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_settings(env_path)

            self.assertEqual(settings.binance_futures_base_url, "https://demo-fapi.binance.com")
            self.assertTrue(settings.binance_futures_testnet_enabled)
            self.assertEqual(settings.binance_futures_symbols, ("BTCUSDT", "ETHUSDT"))
            self.assertEqual(settings.binance_futures_api_key, "futures-key")
            self.assertEqual(settings.binance_futures_secret_key, "futures-secret")
        finally:
            env_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
