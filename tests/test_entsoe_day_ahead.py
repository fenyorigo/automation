from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from entsoe_day_ahead import (  # noqa: E402
    EntsoeNoData,
    collection_due,
    delivery_window_utc,
    parse_price_document,
    parse_hupx_price_document,
)
from dashboard import classify_day_ahead_price_windows  # noqa: E402


PRICE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <mRID>sample-document</mRID>
  <revisionNumber>2</revisionNumber>
  <TimeSeries>
    <currency_Unit.name>EUR</currency_Unit.name>
    <price_Measure_Unit.name>MWH</price_Measure_Unit.name>
    <Period>
      <timeInterval><start>2026-10-09T22:00Z</start><end>2026-10-09T23:00Z</end></timeInterval>
      <resolution>PT15M</resolution>
      <Point><position>1</position><price.amount>81.25</price.amount></Point>
      <Point><position>2</position><price.amount>82.50</price.amount></Point>
      <Point><position>3</position><price.amount>79.00</price.amount></Point>
      <Point><position>4</position><price.amount>77.125</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""

HUPX_JSON = b'''{"message":"Success","data":[
  {"DeliveryDay":"2026-10-10T00:00:00Z","Price":317.2,"ProductQH":"1","Region":"HU","Status":"final"},
  {"DeliveryDay":"2026-10-10T00:00:00Z","Price":311.17,"ProductQH":"2","Region":"HU","Status":"final"},
  {"DeliveryDay":"2026-10-10T00:00:00Z","Price":301.22,"ProductQH":"3","Region":"HU","Status":"final"},
  {"DeliveryDay":"2026-10-10T00:00:00Z","Price":282.77,"ProductQH":"4","Region":"HU","Status":"final"}
]}'''


class EntsoeDayAheadTest(unittest.TestCase):
    def test_price_windows_require_one_hour_and_use_average_bands(self) -> None:
        started_at = datetime(2026, 10, 9, 22, 0)
        prices = [90.0] * 4 + [105.0] * 4 + [120.0] * 4
        points = [
            {
                "interval_start": started_at + timedelta(minutes=15 * index),
                "interval_end": started_at + timedelta(minutes=15 * (index + 1)),
                "price_eur_mwh": price,
            }
            for index, price in enumerate(prices)
        ]

        classified, windows, secondary_limit = classify_day_ahead_price_windows(
            points, 100.0
        )

        self.assertEqual(secondary_limit, 110.0)
        self.assertEqual(
            [point["price_tier"] for point in classified],
            ["primary"] * 4 + ["secondary"] * 4 + ["other"] * 4,
        )
        self.assertEqual(
            [(window["tier"], window["duration_minutes"]) for window in windows],
            [("primary", 60), ("secondary", 60), ("other", 60)],
        )

    def test_price_windows_can_use_dynamic_tariff_values(self) -> None:
        started_at = datetime(2026, 10, 9, 22, 0)
        points = [
            {
                "interval_start": started_at + timedelta(minutes=15 * index),
                "interval_end": started_at + timedelta(minutes=15 * (index + 1)),
                "price_eur_mwh": 100 + index,
                "dynamic_gross_huf_kwh": price,
            }
            for index, price in enumerate([80.0] * 4 + [100.0] * 4)
        ]
        classified, _windows, _limit = classify_day_ahead_price_windows(
            points, 90.0, price_key="dynamic_gross_huf_kwh"
        )
        self.assertEqual(
            [point["price_tier"] for point in classified],
            ["primary"] * 4 + ["other"] * 4,
        )

    def test_price_page_contains_chart_above_table(self) -> None:
        template = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "templates"
            / "day_ahead_prices.html"
        ).read_text(encoding="utf-8")
        self.assertIn("day_ahead_prices_chart", template)
        self.assertLess(template.index("chart-frame"), template.index("day-ahead-table"))

    def test_parse_quarter_hour_price_document(self) -> None:
        document = parse_price_document(PRICE_XML)
        self.assertEqual(document.document_mrid, "sample-document")
        self.assertEqual(document.revision_number, 2)
        self.assertEqual(document.currency, "EUR")
        self.assertEqual(document.price_unit, "MWH")
        self.assertEqual(len(document.points), 4)
        self.assertEqual(
            document.points[1].interval_start,
            datetime(2026, 10, 9, 22, 15, tzinfo=UTC),
        )
        self.assertEqual(
            document.points[1].interval_end,
            datetime(2026, 10, 9, 22, 30, tzinfo=UTC),
        )
        self.assertEqual(document.points[1].price_eur_mwh, Decimal("82.50"))

    def test_no_matching_data_acknowledgement_is_retryable(self) -> None:
        payload = b"""<Acknowledgement_MarketDocument xmlns="urn:test">
          <Reason><code>999</code><text>No matching data found for Data item day ahead prices</text></Reason>
        </Acknowledgement_MarketDocument>"""
        with self.assertRaises(EntsoeNoData) as raised:
            parse_price_document(payload)
        self.assertEqual(raised.exception.code, "no_data_yet")

    def test_parse_hupx_final_quarter_hours(self) -> None:
        # A four-point payload is valid for this focused parser test when the
        # expected delivery window is patched to one hour.
        import entsoe_day_ahead
        original = entsoe_day_ahead.delivery_window_utc
        entsoe_day_ahead.delivery_window_utc = lambda value: (
            datetime(2026, 10, 9, 22, 0, tzinfo=UTC),
            datetime(2026, 10, 9, 23, 0, tzinfo=UTC),
        )
        try:
            document = parse_hupx_price_document(HUPX_JSON, date(2026, 10, 10))
        finally:
            entsoe_day_ahead.delivery_window_utc = original
        self.assertEqual(len(document.points), 4)
        self.assertEqual(document.points[1].price_eur_mwh, Decimal("311.17"))
        self.assertEqual(document.points[1].interval_start.minute, 15)
        self.assertEqual(document.currency, "EUR")

    def test_delivery_window_tracks_budapest_dst_days(self) -> None:
        spring_start, spring_end = delivery_window_utc(date(2026, 3, 29))
        autumn_start, autumn_end = delivery_window_utc(date(2026, 10, 25))
        self.assertEqual(spring_end - spring_start, timedelta(hours=23))
        self.assertEqual(autumn_end - autumn_start, timedelta(hours=25))

    def test_collection_due_retries_and_checks_revisions(self) -> None:
        from zoneinfo import ZoneInfo
        budapest = ZoneInfo("Europe/Budapest")
        # 13:05 CET is 14:05 in Budapest while daylight saving time is active.
        before_publication = datetime(2026, 10, 9, 14, 4, tzinfo=budapest)
        now = datetime(2026, 10, 9, 14, 5, tzinfo=budapest)
        self.assertFalse(collection_due(before_publication, None))
        self.assertTrue(collection_due(now, None))
        self.assertFalse(collection_due(now, (datetime(2026, 10, 9, 11, 55), False)))
        self.assertTrue(collection_due(now, (datetime(2026, 10, 9, 11, 45), False)))
        self.assertTrue(collection_due(now, (datetime(2026, 10, 9, 11, 5), True)))
        self.assertFalse(collection_due(now, (datetime(2026, 10, 9, 11, 35), True)))

    def test_winter_publication_uses_same_cet_clock(self) -> None:
        from zoneinfo import ZoneInfo
        budapest = ZoneInfo("Europe/Budapest")
        self.assertFalse(collection_due(datetime(2026, 12, 9, 13, 4, tzinfo=budapest), None))
        self.assertTrue(collection_due(datetime(2026, 12, 9, 13, 5, tzinfo=budapest), None))


if __name__ == "__main__":
    unittest.main()
