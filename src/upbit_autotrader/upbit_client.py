from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import base64
import hashlib
import hmac
import json
import uuid


def _value_to_str(value: Any) -> str:
    if isinstance(value, Decimal):
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    return str(value)


def build_query_string(params: Mapping[str, Any] | None) -> str:
    if not params:
        return ""

    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            pairs.extend((key, _value_to_str(item)) for item in value)
        else:
            pairs.append((key, _value_to_str(value)))
    return unquote(urlencode(pairs))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_jwt(
    access_key: str,
    secret_key: str,
    query_string: str = "",
    nonce: str | None = None,
) -> str:
    payload: dict[str, str] = {
        "access_key": access_key,
        "nonce": nonce or str(uuid.uuid4()),
    }
    if query_string:
        payload["query_hash"] = hashlib.sha512(query_string.encode("utf-8")).hexdigest()
        payload["query_hash_alg"] = "SHA512"

    header = {"alg": "HS512", "typ": "JWT"}
    header_part = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha512).digest()
    return f"{header_part}.{payload_part}.{_b64url(signature)}"


class UpbitAPIError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"Upbit API error {status}: {body}")
        self.status = status
        self.body = body


class UpbitClient:
    def __init__(
        self,
        base_url: str = "https://api.upbit.com",
        access_key: str = "",
        secret_key: str = "",
        timeout_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_key = access_key
        self.secret_key = secret_key
        self.timeout_seconds = timeout_seconds

    def _auth_header(self, query_string: str = "") -> str:
        if not self.access_key or not self.secret_key:
            raise ValueError("UPBIT_ACCESS_KEY와 UPBIT_SECRET_KEY가 필요합니다")
        token = create_jwt(self.access_key, self.secret_key, query_string)
        return f"Bearer {token}"

    def _request_json(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        auth: bool = False,
    ) -> Any:
        method = method.upper()
        query_string = build_query_string(body if body is not None else params)
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{build_query_string(params)}"

        data = None
        headers = {
            "Accept": "application/json",
            "User-Agent": "upbit-autotrader/0.1",
        }
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = self._auth_header(query_string)

        request = Request(url=url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise UpbitAPIError(exc.code, error_body) from exc

        if not response_body:
            return None
        return json.loads(response_body)

    def get_markets(self, is_details: bool = False) -> list[dict[str, Any]]:
        return self._request_json(
            "GET",
            "/v1/market/all",
            params={"is_details": str(is_details).lower()},
        )

    def get_ticker(self, markets: str | list[str]) -> list[dict[str, Any]]:
        market_text = ",".join(markets) if isinstance(markets, list) else markets
        return self._request_json("GET", "/v1/ticker", params={"markets": market_text})

    def get_orderbook(
        self,
        markets: str | list[str],
        count: int | None = None,
        level: str | int | None = None,
    ) -> list[dict[str, Any]]:
        market_text = ",".join(markets) if isinstance(markets, list) else markets
        params: dict[str, Any] = {"markets": market_text}
        if count is not None:
            params["count"] = count
        if level is not None:
            params["level"] = level
        return self._request_json("GET", "/v1/orderbook", params=params)

    def get_minute_candles(
        self,
        market: str,
        unit: int = 5,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"market": market, "count": count}
        if to:
            params["to"] = to
        return self._request_json("GET", f"/v1/candles/minutes/{unit}", params=params)

    def get_day_candles(
        self,
        market: str,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._get_period_candles("days", market, count, to)

    def get_week_candles(
        self,
        market: str,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._get_period_candles("weeks", market, count, to)

    def get_month_candles(
        self,
        market: str,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._get_period_candles("months", market, count, to)

    def get_year_candles(
        self,
        market: str,
        count: int = 80,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._get_period_candles("years", market, count, to)

    def _get_period_candles(
        self,
        period: str,
        market: str,
        count: int,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"market": market, "count": count}
        if to:
            params["to"] = to
        return self._request_json("GET", f"/v1/candles/{period}", params=params)

    def get_accounts(self) -> list[dict[str, Any]]:
        return self._request_json("GET", "/v1/accounts", auth=True)

    def get_order_chance(self, market: str) -> dict[str, Any]:
        return self._request_json("GET", "/v1/orders/chance", params={"market": market}, auth=True)

    def create_order(self, order_body: Mapping[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/v1/orders", body=order_body, auth=True)

    def test_order(self, order_body: Mapping[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/v1/orders/test", body=order_body, auth=True)
