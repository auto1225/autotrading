from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.live import (
    LIVE_CONFIRMATION_CODE,
    LIVE_CONFIRMATION_PHRASE,
    account_market,
    is_confirmation_accepted,
    is_live_trading_armed,
    is_web_live_trading_armed,
    live_portfolio_state,
    mask_key,
    order_chance_payload,
    summarize_accounts,
)


class LiveSafetyTests(unittest.TestCase):
    def test_live_arming_requires_flag_and_confirmation_phrase(self) -> None:
        self.assertFalse(is_live_trading_armed(TradingSettings(live_trading_enabled=True)))
        self.assertTrue(
            is_live_trading_armed(
                TradingSettings(
                    live_trading_enabled=True,
                    live_order_confirmation=LIVE_CONFIRMATION_PHRASE,
                )
            )
        )
        self.assertTrue(is_confirmation_accepted(LIVE_CONFIRMATION_CODE))
        self.assertTrue(
            is_live_trading_armed(
                TradingSettings(
                    live_trading_enabled=True,
                    live_order_confirmation=LIVE_CONFIRMATION_CODE,
                )
            )
        )
        self.assertTrue(
            is_web_live_trading_armed(
                TradingSettings(
                    live_trading_enabled=True,
                    web_live_trading_enabled=True,
                    live_order_confirmation=LIVE_CONFIRMATION_PHRASE,
                )
            )
        )

    def test_mask_key_keeps_only_edges(self) -> None:
        self.assertEqual(mask_key("abcd1234wxyz"), "abcd...wxyz")
        self.assertEqual(mask_key("short"), "*****")

    def test_live_portfolio_state_uses_krw_cash_and_watched_assets(self) -> None:
        accounts = [
            {"currency": "KRW", "balance": "700000", "locked": "1000"},
            {"currency": "BTC", "unit_currency": "KRW", "balance": "0.01", "avg_buy_price": "100000000"},
            {"currency": "ETH", "unit_currency": "KRW", "balance": "1", "avg_buy_price": "3000000"},
        ]
        settings = TradingSettings(markets=("KRW-BTC",))

        state = live_portfolio_state(accounts, settings)
        summary = summarize_accounts(accounts, settings)

        self.assertEqual(state.cash_krw, Decimal("700000"))
        self.assertEqual(state.position("KRW-BTC").volume, Decimal("0.01"))
        self.assertEqual(state.position("KRW-ETH").volume, Decimal("0"))
        self.assertEqual(summary["cashKrw"], "700000")
        self.assertEqual(summary["lockedKrw"], "1000")
        self.assertEqual(account_market(accounts[1]), "KRW-BTC")

    def test_order_chance_payload_extracts_supported_types(self) -> None:
        payload = order_chance_payload(
            {
                "bid_fee": "0.0005",
                "ask_fee": "0.0005",
                "market": {
                    "bid_types": ["limit", "price"],
                    "ask_types": ["limit", "market"],
                    "bid": {"min_total": "5000"},
                    "ask": {"min_total": "5000"},
                },
            }
        )

        self.assertEqual(payload["bidTypes"], ["limit", "price"])
        self.assertEqual(payload["askTypes"], ["limit", "market"])
        self.assertEqual(payload["minBidTotal"], "5000")


if __name__ == "__main__":
    unittest.main()
