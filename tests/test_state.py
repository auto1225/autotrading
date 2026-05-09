from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.state import JsonPortfolioStateStore, JsonStateStore, PortfolioState


class StateStoreTests(unittest.TestCase):
    def test_portfolio_store_recovers_from_empty_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            state_file.write_text("", encoding="utf-8")

            state = JsonPortfolioStateStore(state_file).load(Decimal("1000000"))

        self.assertEqual(state.cash_krw, Decimal("1000000"))
        self.assertEqual(state.positions, {})

    def test_portfolio_store_saves_valid_json_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            store = JsonPortfolioStateStore(state_file)

            store.save(PortfolioState(cash_krw=Decimal("12345"), positions={}))
            state = store.load(Decimal("1000000"))

        self.assertEqual(state.cash_krw, Decimal("12345"))

    def test_legacy_store_recovers_from_invalid_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "paper_state.json"
            state_file.write_text("{", encoding="utf-8")

            state = JsonStateStore(state_file).load(Decimal("1000000"))

        self.assertEqual(state.cash_krw, Decimal("1000000"))


if __name__ == "__main__":
    unittest.main()
