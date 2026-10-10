import unittest
from datetime import UTC, datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from analyze_weather_forecasts import pair_forecasts_with_observations, summarize_errors
from dashboard import summarize_weather_forecast_days
from outdoor_weather import forecast_points


class WeatherForecastTest(unittest.TestCase):
    def test_rolling_comparison_pairs_nearest_local_observations(self) -> None:
        forecasts = [
            (datetime(2026, 10, 8, 10, 0), 1.0, 15.0),
            (datetime(2026, 10, 8, 11, 0), 1.0, 16.0),
        ]
        observations = [
            (datetime(2026, 10, 8, 9, 55), 14.5),
            (datetime(2026, 10, 8, 11, 8), 15.2),
        ]
        points = pair_forecasts_with_observations(forecasts, observations, 15)
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["actual_temperature_c"], 14.5)
        self.assertAlmostEqual(points[1]["difference_c"], 0.8)

    def test_open_meteo_parallel_arrays_are_normalized(self) -> None:
        payload = {
            "hourly": {
                "time": ["2026-10-08T10:00", "2026-10-08T11:00"],
                "temperature_2m": [15.0, 16.0],
                "apparent_temperature": [14.0, 15.0],
                "cloud_cover": [10, 20],
                "shortwave_radiation": [300, 400],
                "wind_speed_10m": [5.0, 6.0],
                "precipitation": [0.0, 0.1],
                "weather_code": [1, 2],
            }
        }

        points = forecast_points(payload, datetime(2026, 10, 8, 9, 30, tzinfo=UTC))

        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["valid_at"], datetime(2026, 10, 8, 10, 0))
        self.assertEqual(points[0]["lead_hours"], 0.5)
        self.assertEqual(points[1]["shortwave_radiation"], 400)

    def test_accuracy_summary_reports_mae_bias_and_rmse(self) -> None:
        summary = summarize_errors([1.0, -2.0, 1.0])

        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["mae_c"], 1.333)
        self.assertEqual(summary["bias_c"], 0.0)
        self.assertEqual(summary["rmse_c"], 1.414)

    def test_daily_summary_uses_local_calendar_days(self) -> None:
        points = [
            {
                "valid_at": datetime(2026, 10, 8, 21, 0),
                "temperature_c": 10.0,
                "cloud_cover_percent": 20,
                "shortwave_radiation_wm2": 0,
                "precipitation_mm": 0.2,
            },
            {
                "valid_at": datetime(2026, 10, 8, 22, 0),
                "temperature_c": 8.0,
                "cloud_cover_percent": 40,
                "shortwave_radiation_wm2": 300,
                "precipitation_mm": 0.3,
            },
        ]

        days = summarize_weather_forecast_days(points)

        self.assertEqual(len(days), 2)
        self.assertEqual(str(days[0]["date"]), "2026-10-08")
        self.assertEqual(str(days[1]["date"]), "2026-10-09")
        self.assertEqual(days[1]["minimum_c"], 8.0)
        self.assertEqual(days[1]["peak_radiation_wm2"], 300)
        self.assertEqual(days[1]["precipitation_mm"], 0.3)

    def test_forecast_page_is_linked_from_dashboard(self) -> None:
        templates = ROOT / "app" / "templates"
        dashboard = (templates / "dashboard.html").read_text(encoding="utf-8")
        forecast = (templates / "weather_forecast.html").read_text(encoding="utf-8")

        self.assertIn("weather_forecast", dashboard)
        self.assertIn("Időjárás-előrejelzés", dashboard)
        self.assertIn("Napi összefoglaló", forecast)
        self.assertIn("Open-Meteo és a helyi hőmérő eltérése", forecast)


if __name__ == "__main__":
    unittest.main()
