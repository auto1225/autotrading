from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.alerts import alert_summary, evaluate_alerts
from upbit_autotrader.config import TradingSettings
from upbit_autotrader.live import live_runtime_payload


class AlertTests(unittest.TestCase):
    def test_daily_loss_limit_creates_critical_alert(self) -> None:
        settings = TradingSettings(daily_loss_limit_krw=Decimal("50000"))

        alerts = evaluate_alerts(
            settings,
            {"realtime": {"connected": True}, "autorun": {"running": False}},
            {"dailyRealizedPnlKrw": "-50000", "dailyOrderCount": 0},
            live_runtime_payload(settings),
            emergency_stopped=False,
            host="127.0.0.1",
        )

        self.assertEqual(alerts[0].code, "daily_loss_limit")
        self.assertEqual(alert_summary(alerts)["level"], "critical")

    def test_lan_without_dashboard_auth_warns(self) -> None:
        settings = TradingSettings(dashboard_auth_enabled=False)

        alerts = evaluate_alerts(
            settings,
            {"realtime": {"connected": True}, "autorun": {"running": False}},
            {"dailyRealizedPnlKrw": "0", "dailyOrderCount": 0},
            live_runtime_payload(settings),
            emergency_stopped=False,
            host="0.0.0.0",
        )

        self.assertEqual([alert.code for alert in alerts], ["lan_without_auth"])
        self.assertEqual(alert_summary(alerts)["level"], "warning")

    def test_disabled_alerts_return_empty_list(self) -> None:
        settings = TradingSettings(ops_alerts_enabled=False)

        alerts = evaluate_alerts(
            settings,
            {"realtime": {"connected": False}, "autorun": {"running": False}},
            {"dailyRealizedPnlKrw": "-999999", "dailyOrderCount": 999},
            {"webArmed": True},
            emergency_stopped=True,
            host="0.0.0.0",
        )

        self.assertEqual(alerts, [])

    def test_live_test_order_payload_requires_extra_lock(self) -> None:
        settings = TradingSettings(
            live_trading_enabled=True,
            live_test_order_enabled=True,
            live_order_confirmation="LIVE-RISK-ACCEPTED",
        )

        live = live_runtime_payload(settings)

        self.assertTrue(live["armed"])
        self.assertTrue(live["testOrderArmed"])
        self.assertFalse(live["webArmed"])


if __name__ == "__main__":
    unittest.main()
