from __future__ import annotations

from decimal import Decimal
import unittest

from upbit_autotrader.price_units import (
    krw_tick_size,
    round_krw_price,
    stop_price_below,
    target_price_above,
)


class PriceUnitsTests(unittest.TestCase):
    def test_krw_tick_size_matches_upbit_price_bands(self) -> None:
        self.assertEqual(krw_tick_size(Decimal("200")), Decimal("1"))
        self.assertEqual(krw_tick_size(Decimal("44.75")), Decimal("0.1"))
        self.assertEqual(krw_tick_size(Decimal("9.894")), Decimal("0.01"))
        self.assertEqual(krw_tick_size(Decimal("0.0108642857")), Decimal("0.0001"))

    def test_price_rounding_uses_orderable_ticks(self) -> None:
        self.assertEqual(round_krw_price(Decimal("201.714285714"), "floor"), Decimal("201"))
        self.assertEqual(round_krw_price(Decimal("44.757142857"), "floor"), Decimal("44.7"))
        self.assertEqual(round_krw_price(Decimal("9.894"), "ceil"), Decimal("9.90"))
        self.assertEqual(round_krw_price(Decimal("0.0108642857"), "ceil"), Decimal("0.0109"))

    def test_stop_and_target_stay_on_the_correct_side_of_current_price(self) -> None:
        self.assertEqual(stop_price_below(Decimal("44.174"), Decimal("44.3")), Decimal("44.2"))
        self.assertEqual(target_price_above(Decimal("44.757"), Decimal("44.3")), Decimal("44.8"))
        self.assertEqual(stop_price_below(Decimal("200.5"), Decimal("200")), Decimal("199"))
        self.assertEqual(target_price_above(Decimal("199.5"), Decimal("200")), Decimal("201"))


if __name__ == "__main__":
    unittest.main()
