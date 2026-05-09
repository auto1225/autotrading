from __future__ import annotations

from decimal import Decimal
from typing import Any

from .config import TradingSettings
from .models import decimal_to_str
from .state import PortfolioPosition, PortfolioState


LIVE_CONFIRMATION_PHRASE = "실거래 손실 동의"
LIVE_CONFIRMATION_CODE = "LIVE-RISK-ACCEPTED"


def is_confirmation_accepted(value: str) -> bool:
    return value.strip() in {LIVE_CONFIRMATION_PHRASE, LIVE_CONFIRMATION_CODE}


def is_live_trading_armed(settings: TradingSettings) -> bool:
    return settings.live_trading_enabled and is_confirmation_accepted(settings.live_order_confirmation)


def is_web_live_trading_armed(settings: TradingSettings) -> bool:
    return settings.web_live_trading_enabled and is_live_trading_armed(settings)


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def live_runtime_payload(settings: TradingSettings) -> dict[str, Any]:
    live_armed = is_live_trading_armed(settings)
    return {
        "keyConfigured": bool(settings.access_key and settings.secret_key),
        "accessKeyMasked": mask_key(settings.access_key),
        "liveTradingEnabled": settings.live_trading_enabled,
        "webLiveTradingEnabled": settings.web_live_trading_enabled,
        "testOrderEnabled": settings.live_test_order_enabled,
        "confirmationArmed": is_confirmation_accepted(settings.live_order_confirmation),
        "armed": live_armed,
        "webArmed": is_web_live_trading_armed(settings),
        "testOrderArmed": settings.live_test_order_enabled and live_armed,
        "confirmationPhrase": LIVE_CONFIRMATION_PHRASE,
        "confirmationCode": LIVE_CONFIRMATION_CODE,
    }


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    return Decimal(str(value))


def account_market(account: dict[str, Any]) -> str | None:
    currency = str(account.get("currency") or "").upper()
    if not currency or currency == "KRW":
        return None
    unit_currency = str(account.get("unit_currency") or "KRW").upper()
    return f"{unit_currency}-{currency}"


def live_portfolio_state(accounts: list[dict[str, Any]], settings: TradingSettings) -> PortfolioState:
    cash_krw = Decimal("0")
    positions: dict[str, PortfolioPosition] = {}
    watched_markets = set(settings.markets)

    for account in accounts:
        currency = str(account.get("currency") or "").upper()
        balance = _decimal(account.get("balance"))
        if currency == "KRW":
            cash_krw = balance
            continue

        market = account_market(account)
        if not market or market not in watched_markets:
            continue
        positions[market] = PortfolioPosition(
            volume=balance,
            avg_entry_price=_decimal(account.get("avg_buy_price")),
        )

    return PortfolioState(cash_krw=cash_krw, positions=positions)


def summarize_accounts(accounts: list[dict[str, Any]], settings: TradingSettings) -> dict[str, Any]:
    watched_markets = set(settings.markets)
    rows: list[dict[str, Any]] = []
    cash_krw = Decimal("0")
    locked_krw = Decimal("0")

    for account in accounts:
        currency = str(account.get("currency") or "").upper()
        balance = _decimal(account.get("balance"))
        locked = _decimal(account.get("locked"))
        if currency == "KRW":
            cash_krw = balance
            locked_krw = locked

        market = account_market(account)
        rows.append(
            {
                "currency": currency,
                "market": market,
                "balance": decimal_to_str(balance),
                "locked": decimal_to_str(locked),
                "avgBuyPrice": decimal_to_str(_decimal(account.get("avg_buy_price"))),
                "unitCurrency": account.get("unit_currency") or ("KRW" if currency != "KRW" else None),
                "watched": market in watched_markets if market else currency == "KRW",
            }
        )

    return {
        "cashKrw": decimal_to_str(cash_krw),
        "lockedKrw": decimal_to_str(locked_krw),
        "accountCount": len(accounts),
        "accounts": rows,
    }


def order_chance_payload(raw: dict[str, Any]) -> dict[str, Any]:
    market = raw.get("market") or {}
    bid = market.get("bid") or {}
    ask = market.get("ask") or {}
    return {
        "bidFee": str(raw.get("bid_fee", "")),
        "askFee": str(raw.get("ask_fee", "")),
        "makerBidFee": str(raw.get("maker_bid_fee", "")),
        "makerAskFee": str(raw.get("maker_ask_fee", "")),
        "bidTypes": list(market.get("bid_types") or []),
        "askTypes": list(market.get("ask_types") or []),
        "minBidTotal": str(bid.get("min_total", "")),
        "maxBidTotal": str(bid.get("max_total", "")),
        "minAskTotal": str(ask.get("min_total", "")),
        "maxAskTotal": str(ask.get("max_total", "")),
        "raw": raw,
    }
