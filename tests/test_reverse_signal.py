from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings
from upbit_autotrader.reverse_signal import reverse_signal_report, reverse_signal_report_from_events


def paper_order(time: str, side: str, market: str, raw: dict[str, str]) -> dict[str, object]:
    return {
        "time": time,
        "type": "paper_order",
        "payload": {
            "ok": True,
            "market": market,
            "raw": {
                "side": side,
                "market": market,
                **raw,
            },
        },
    }


class ReverseSignalTests(unittest.TestCase):
    def test_reverse_signal_report_replays_closed_longs_as_inverse_shorts(self) -> None:
        events = [
            paper_order(
                "2026-05-06T00:00:00+00:00",
                "bid",
                "KRW-AAA",
                {
                    "spent_krw": "1000",
                    "fee_krw": "0.5",
                    "fill_price": "100",
                    "volume": "9.995",
                },
            ),
            paper_order(
                "2026-05-06T00:01:00+00:00",
                "ask",
                "KRW-AAA",
                {
                    "received_krw": "899.100225",
                    "fee_krw": "0.449775",
                    "fill_price": "90",
                    "volume": "9.995",
                    "realized_pnl_krw": "-100.899775",
                },
            ),
        ]

        report = reverse_signal_report_from_events(events)

        self.assertEqual(report.trade_count, 1)
        self.assertEqual(report.long_losses, 1)
        self.assertEqual(report.reverse_wins, 1)
        self.assertEqual(report.long_equity_total_pnl_krw, Decimal("-100.899775"))
        self.assertEqual(report.reverse_total_pnl_krw, Decimal("99.0500"))
        self.assertEqual(report.price_down_count, 1)
        self.assertEqual(report.verdict, "reverse-outperformed")

        payload = report.to_dict()
        self.assertEqual(payload["longEquityTotalPnlKrw"], "-101")
        self.assertEqual(payload["reverseTotalPnlKrw"], "99")
        self.assertEqual(payload["reverseWinRatePct"], "100.00")

    def test_reverse_signal_report_keeps_open_unclosed_entries(self) -> None:
        events = [
            paper_order(
                "2026-05-06T00:00:00+00:00",
                "bid",
                "KRW-OPEN",
                {
                    "spent_krw": "2000",
                    "fee_krw": "1",
                    "fill_price": "50",
                    "volume": "39.98",
                },
            ),
        ]

        report = reverse_signal_report_from_events(events)

        self.assertEqual(report.trade_count, 0)
        self.assertEqual(report.open_signal_count, 1)
        self.assertEqual(report.open_signals[0].market, "KRW-OPEN")
        self.assertFalse(report.to_dict()["ok"])

    def test_reverse_signal_report_loads_events_from_settings_state_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            events_file = state_file.parent / "events.jsonl"
            events = [
                paper_order(
                    "2026-05-06T00:00:00+00:00",
                    "bid",
                    "KRW-AAA",
                    {
                        "spent_krw": "1000",
                        "fee_krw": "0.5",
                        "fill_price": "100",
                        "volume": "9.995",
                    },
                ),
                paper_order(
                    "2026-05-06T00:02:00+00:00",
                    "ask",
                    "KRW-AAA",
                    {
                        "received_krw": "1098.90055",
                        "fee_krw": "0.54945",
                        "fill_price": "110",
                        "volume": "9.995",
                        "realized_pnl_krw": "99.45055",
                    },
                ),
            ]
            events_file.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

            report = reverse_signal_report(TradingSettings(state_file=state_file))

        self.assertEqual(report.trade_count, 1)
        self.assertEqual(report.long_wins, 1)
        self.assertEqual(report.reverse_losses, 1)
        self.assertEqual(report.price_up_count, 1)


if __name__ == "__main__":
    unittest.main()
