from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from electricity_prices import calculate_dynamic_electricity_price  # noqa: E402


class DynamicElectricityPriceTest(unittest.TestCase):
    def test_mvm_dynamic_price_formula_and_rounding(self) -> None:
        price = calculate_dynamic_electricity_price(
            Decimal("247.3789"),
            Decimal("364.82"),
            Decimal("13.7000"),
            Decimal("27"),
        )
        self.assertEqual(price.market_net_huf_kwh, Decimal("90.25"))
        self.assertEqual(price.dynamic_net_huf_kwh, Decimal("103.9500"))
        self.assertEqual(price.dynamic_gross_huf_kwh, Decimal("132.02"))

    def test_negative_hupx_price_is_supported(self) -> None:
        price = calculate_dynamic_electricity_price(
            Decimal("-10"), Decimal("400"), Decimal("13.70"), Decimal("27")
        )
        self.assertEqual(price.market_net_huf_kwh, Decimal("-4.00"))
        self.assertEqual(price.dynamic_net_huf_kwh, Decimal("9.70"))
        self.assertEqual(price.dynamic_gross_huf_kwh, Decimal("12.32"))


if __name__ == "__main__":
    unittest.main()
