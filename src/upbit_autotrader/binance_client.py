from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import hashlib
import hmac
import json
import time

from .models import Candle, to_decimal


class BinanceAPIError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"Binance API error {status}: {body}")
        self.status = status
        self.body = body


def binance_query_string(params: Mapping[str, Any] | None) -> str:
    if not params:
        return ""
    return urlencode([(key, str(value)) for key, value in params.items() if value is not None])


def binance_signature(secret_key: str, query_string: str) -> str:
    return hmac.new(secret_key.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()


class BinanceSpotClient:
    def __init__(
        self,
        base_url: str = "https://api.binance.com",
        api_key: str = "",
        secret_key: str = "",
        timeout_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key
        self.timeout_seconds = timeout_seconds

    def _request_json(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        signed: bool = False,
    ) -> Any:
        params_dict = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": "upbit-autotrader/0.1"}
        if signed:
            if not self.api_key or not self.secret_key:
                raise ValueError("BINANCE_API_KEY와 BINANCE_SECRET_KEY가 필요합니다")
            params_dict.setdefault("timestamp", int(time.time() * 1000))
            query = binance_query_string(params_dict)
            params_dict["signature"] = binance_signature(self.secret_key, query)
            headers["X-MBX-APIKEY"] = self.api_key

        query_string = binance_query_string(params_dict)
        url = f"{self.base_url}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        request = Request(url=url, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise BinanceAPIError(exc.code, error_body) from exc
        return json.loads(body) if body else None

    def ping(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v3/ping")

    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        params = {"symbol": symbol} if symbol else None
        return self._request_json("GET", "/api/v3/exchangeInfo", params=params)

    def ticker_price(self, symbol: str) -> dict[str, Any]:
        return self._request_json("GET", "/api/v3/ticker/price", params={"symbol": symbol})

    def klines(
        self,
        symbol: str,
        interval: str = "5m",
        limit: int = 80,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list[Any]]:
        return self._request_json(
            "GET",
            "/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

    def account(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v3/account", signed=True)


class BinanceFuturesClient:
    def __init__(
        self,
        base_url: str = "https://fapi.binance.com",
        api_key: str = "",
        secret_key: str = "",
        timeout_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key
        self.timeout_seconds = timeout_seconds

    def _request_json(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        signed: bool = False,
    ) -> Any:
        params_dict = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": "upbit-autotrader/0.1"}
        if signed:
            if not self.api_key or not self.secret_key:
                raise ValueError("BINANCE_FUTURES_API_KEY and BINANCE_FUTURES_SECRET_KEY are required")
            params_dict.setdefault("timestamp", int(time.time() * 1000))
            params_dict.setdefault("recvWindow", 5000)
            query = binance_query_string(params_dict)
            params_dict["signature"] = binance_signature(self.secret_key, query)
            headers["X-MBX-APIKEY"] = self.api_key

        query_string = binance_query_string(params_dict)
        url = f"{self.base_url}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        request = Request(url=url, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise BinanceAPIError(exc.code, error_body) from exc
        return json.loads(body) if body else None

    def ping(self) -> dict[str, Any]:
        return self._request_json("GET", "/fapi/v1/ping")

    def server_time(self) -> dict[str, Any]:
        return self._request_json("GET", "/fapi/v1/time")

    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        params = {"symbol": symbol} if symbol else None
        return self._request_json("GET", "/fapi/v1/exchangeInfo", params=params)

    def ticker_price(self, symbol: str) -> dict[str, Any]:
        return self._request_json("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})

    def ticker_24hr(self, symbol: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        params = {"symbol": symbol} if symbol else None
        return self._request_json("GET", "/fapi/v1/ticker/24hr", params=params)

    def klines(
        self,
        symbol: str,
        interval: str = "5m",
        limit: int = 80,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list[Any]]:
        return self._request_json(
            "GET",
            "/fapi/v1/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

    def account(self) -> dict[str, Any]:
        return self._request_json("GET", "/fapi/v3/account", signed=True)

    def balance(self) -> list[dict[str, Any]]:
        return self._request_json("GET", "/fapi/v3/balance", signed=True)


def candle_from_binance(symbol: str, row: list[Any]) -> Candle:
    open_time = int(row[0])
    open_price = to_decimal(row[1])
    high_price = to_decimal(row[2])
    low_price = to_decimal(row[3])
    close_price = to_decimal(row[4])
    volume = to_decimal(row[5])
    trade_value = to_decimal(row[7])
    return Candle(
        market=symbol,
        candle_date_time_utc=str(open_time),
        candle_date_time_kst=str(open_time),
        opening_price=open_price,
        high_price=high_price,
        low_price=low_price,
        trade_price=close_price,
        timestamp=open_time,
        candle_acc_trade_price=trade_value,
        candle_acc_trade_volume=volume,
    )
