from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from mnb_exchange_rate import collection_due, parse_current_exchange_rates  # noqa: E402


MNB_SOAP = b"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <GetCurrentExchangeRatesResponse xmlns="http://www.mnb.hu/webservices/">
      <GetCurrentExchangeRatesResult>&lt;MNBCurrentExchangeRates&gt;&lt;Day date="2026-10-09"&gt;&lt;Rate unit="1" curr="EUR"&gt;364,82&lt;/Rate&gt;&lt;Rate unit="100" curr="JPY"&gt;205,71&lt;/Rate&gt;&lt;/Day&gt;&lt;/MNBCurrentExchangeRates&gt;</GetCurrentExchangeRatesResult>
    </GetCurrentExchangeRatesResponse>
  </s:Body>
</s:Envelope>"""


class MnbExchangeRateTest(unittest.TestCase):
    def test_parse_current_eur_rate(self) -> None:
        rate = parse_current_exchange_rates(MNB_SOAP)
        self.assertEqual(rate.rate_date.isoformat(), "2026-10-09")
        self.assertEqual(rate.currency, "EUR")
        self.assertEqual(rate.unit, 1)
        self.assertEqual(rate.rate_huf, Decimal("364.82"))

    def test_missing_currency_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no USD rate"):
            parse_current_exchange_rates(MNB_SOAP, "USD")

    def test_collection_runs_once_after_publication_time(self) -> None:
        budapest = ZoneInfo("Europe/Budapest")
        before = datetime(2026, 10, 10, 11, 34, tzinfo=budapest)
        after = datetime(2026, 10, 10, 11, 35, tzinfo=budapest)
        previous_utc = datetime(2026, 10, 9, 10, 0)
        current_utc = datetime(2026, 10, 10, 10, 0)
        self.assertFalse(collection_due(before, None))
        self.assertTrue(collection_due(after, None))
        self.assertTrue(collection_due(after, (previous_utc, True)))
        self.assertFalse(collection_due(after, (current_utc, True)))
        failed_recently = datetime(2026, 10, 10, 9, 20)
        failed_long_ago = datetime(2026, 10, 10, 9, 0)
        self.assertFalse(collection_due(after, (failed_recently, False)))
        self.assertTrue(collection_due(after, (failed_long_ago, False)))


if __name__ == "__main__":
    unittest.main()
