from __future__ import annotations

from pathlib import Path
import base64
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.config import TradingSettings, load_settings
from upbit_autotrader.web import (
    is_auth_exempt_path,
    is_basic_auth_valid,
    load_selected_strategy_auto_select,
    load_selected_strategy_name,
    load_strategy_selection,
    save_selected_strategy_name,
    save_selected_strategy_selection,
    settings_for_strategy_name,
)


def basic_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


class DashboardAuthTests(unittest.TestCase):
    def test_basic_auth_accepts_matching_credentials(self) -> None:
        settings = TradingSettings(
            dashboard_auth_enabled=True,
            dashboard_username="admin",
            dashboard_password="strong-password",
        )

        self.assertTrue(is_basic_auth_valid(basic_header("admin", "strong-password"), settings))

    def test_basic_auth_rejects_invalid_credentials(self) -> None:
        settings = TradingSettings(
            dashboard_auth_enabled=True,
            dashboard_username="admin",
            dashboard_password="strong-password",
        )

        self.assertFalse(is_basic_auth_valid(basic_header("admin", "wrong-password"), settings))
        self.assertFalse(is_basic_auth_valid("Bearer token", settings))
        self.assertFalse(is_basic_auth_valid("Basic !!!", settings))
        self.assertFalse(
            is_basic_auth_valid(
                "Basic " + base64.b64encode("missing-separator".encode("utf-8")).decode("ascii"),
                settings,
            )
        )

    def test_health_check_is_auth_exempt(self) -> None:
        self.assertTrue(is_auth_exempt_path("/api/health"))
        self.assertFalse(is_auth_exempt_path("/api/status"))
        self.assertFalse(is_auth_exempt_path("/"))

    def test_enabled_dashboard_auth_requires_password(self) -> None:
        settings = TradingSettings(dashboard_auth_enabled=True, dashboard_password="")

        with self.assertRaises(ValueError):
            settings.validate()

    def test_settings_load_dashboard_auth_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "DASHBOARD_AUTH_ENABLED=true",
                        "DASHBOARD_USERNAME=desk",
                        "DASHBOARD_PASSWORD=secret",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                settings = load_settings(env_path)

            self.assertTrue(settings.dashboard_auth_enabled)
            self.assertEqual(settings.dashboard_username, "desk")
            self.assertEqual(settings.dashboard_password, "secret")

    def test_settings_for_strategy_name_applies_supported_strategy(self) -> None:
        settings = settings_for_strategy_name(TradingSettings(), "breakout")

        self.assertEqual(settings.strategy_name, "breakout")

    def test_settings_for_strategy_name_rejects_unknown_strategy(self) -> None:
        with self.assertRaises(Exception):
            settings_for_strategy_name(TradingSettings(), "martingale")

    def test_selected_strategy_is_persisted_to_state_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                strategy_name="mean_reversion",
                state_file=Path(temp_dir) / "paper_state.json",
            )

            save_selected_strategy_name(settings)

            self.assertEqual(load_selected_strategy_name(TradingSettings(state_file=settings.state_file)), "mean_reversion")

    def test_strategy_selection_defaults_to_auto_adaptive_learning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(state_file=Path(temp_dir) / "paper_state.json")

            self.assertEqual(load_selected_strategy_name(settings), "adaptive_learning")
            self.assertTrue(load_selected_strategy_auto_select(settings))

    def test_strategy_auto_selection_is_persisted_to_state_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = TradingSettings(
                strategy_name="adaptive_learning",
                state_file=Path(temp_dir) / "paper_state.json",
            )

            save_selected_strategy_selection(settings, True)

            selection = load_strategy_selection(TradingSettings(state_file=settings.state_file))
            self.assertEqual(selection["strategyName"], "adaptive_learning")
            self.assertTrue(selection["autoSelect"])


if __name__ == "__main__":
    unittest.main()
