from __future__ import annotations

import unittest
from datetime import datetime

from app.computherm_service import (
    clock_drift_seconds,
    clock_details,
    restore_test,
    set_weekly_program,
    start_test,
    suppress_heat,
    sync_clock,
    validate_weekly_program,
    weekly_program,
)


class FakeThermostat:
    def __init__(self):
        self.state = {"power":1,"active":0,"auto_mode":1,"loop_mode":1,"sensor":0,
                      "room_temp":26.0,"thermostat_temp":19.0,"osv":42,"dif":2,
                      "svh":22,"svl":5,"room_temp_adj":0.0,"fre":0,"poweron":1}
        self.advanced_calls=[]
        self.time_calls=[]
        self.schedule_calls=[]
    def get_full_status(self): return dict(self.state)
    def set_mode(self, auto_mode, loop_mode, sensor):
        self.state.update(auto_mode=auto_mode,loop_mode=loop_mode,sensor=sensor)
    def set_temp(self, value): self.state["thermostat_temp"]=value
    def set_advanced(self, loop_mode,sensor,osv,dif,svh,svl,adj,fre,poweron):
        self.advanced_calls.append(svh)
        self.state.update(loop_mode=loop_mode,sensor=sensor,osv=osv,dif=dif,svh=svh,
                          svl=svl,room_temp_adj=adj,fre=fre,poweron=poweron)
    def set_time(self, hour, minute, second, day):
        self.time_calls.append((hour,minute,second,day))
        self.state.update(hour=hour,min=minute,sec=second,dayofweek=day)
    def set_schedule(self, weekday, weekend):
        self.schedule_calls.append((weekday, weekend))
        self.state.update(weekday=weekday, weekend=weekend)


class ComputhermServiceTest(unittest.TestCase):
    def test_start_temporarily_raises_limit_without_power_change(self):
        device=FakeThermostat(); original,verified=start_test(device,30)
        self.assertEqual(original["svh"],22); self.assertEqual(verified["svh"],30)
        self.assertEqual(verified["power"],1); self.assertEqual(verified["auto_mode"],0)
        self.assertEqual(verified["thermostat_temp"],30)

    def test_suppress_keeps_thermostat_powered(self):
        device=FakeThermostat(); original,_=start_test(device,30)
        verified=suppress_heat(device,original)
        self.assertEqual(verified["power"],1)
        self.assertLess(verified["thermostat_temp"],verified["room_temp"])

    def test_restore_recovers_original_mode_target_and_limit(self):
        device=FakeThermostat(); original,_=start_test(device,30)
        restored=restore_test(device,original)
        self.assertEqual(restored["power"],1); self.assertEqual(restored["auto_mode"],1)
        self.assertEqual(restored["thermostat_temp"],19.0); self.assertEqual(restored["svh"],22)

    def test_start_rejects_powered_off_thermostat(self):
        device=FakeThermostat(); device.state["power"]=0
        with self.assertRaisesRegex(RuntimeError,"ki van kapcsolva"):
            start_test(device,30)

    def test_clock_details_translates_iso_weekday_to_hungarian(self):
        self.assertEqual(
            clock_details({"hour": 7, "min": 5, "sec": 9, "dayofweek": 1}),
            {"time": "07:05:09", "day": 1, "day_name": "Hétfő"},
        )
        self.assertEqual(
            clock_details({"hour": 21, "min": 1, "sec": 2, "dayofweek": 7})["day_name"],
            "Vasárnap",
        )

    def test_sync_clock_sets_and_reads_back_local_time(self):
        device = FakeThermostat()
        requested = datetime(2026, 10, 17, 10, 22, 33)
        _, verified = sync_clock(device, requested)
        self.assertEqual(device.time_calls, [(10, 22, 33, 6)])
        self.assertEqual(clock_details(verified)["time"], "10:22:33")
        self.assertEqual(clock_details(verified)["day_name"], "Szombat")

    def test_sync_clock_rejects_wrong_read_back(self):
        class StaleClock(FakeThermostat):
            def set_time(self, hour, minute, second, day):
                self.time_calls.append((hour, minute, second, day))
                self.state.update(hour=hour, min=minute - 1, sec=second, dayofweek=day)

        with self.assertRaisesRegex(RuntimeError, "nem igazolta vissza"):
            sync_clock(StaleClock(), datetime(2026, 10, 17, 10, 22, 33))

    def test_clock_drift_includes_weekday_and_wraps_week_boundary(self):
        reference = datetime(2026, 10, 19, 0, 2, 0)  # Monday
        self.assertEqual(
            clock_drift_seconds(
                {"dayofweek": 7, "hour": 23, "min": 59, "sec": 0},
                reference,
            ),
            -180,
        )

    def test_clock_drift_returns_none_for_invalid_clock(self):
        self.assertIsNone(
            clock_drift_seconds(
                {"dayofweek": 8, "hour": 12, "min": 0, "sec": 0},
                datetime(2026, 10, 17, 12, 0, 0),
            )
        )

    def test_weekly_program_normalizes_six_plus_two_periods(self):
        state = {
            "weekday": [
                {"start_hour": hour, "start_minute": 5, "temp": 19.5}
                for hour in range(6)
            ],
            "weekend": [
                {"start_hour": 7, "start_minute": 0, "temp": 19.0},
                {"start_hour": 22, "start_minute": 30, "temp": 18.5},
            ],
        }
        program = weekly_program(state)
        self.assertEqual(len(program["weekday"]), 6)
        self.assertEqual(len(program["weekend"]), 2)
        self.assertEqual(
            program["weekday"][0],
            {"time": "00:05", "temperature_c": 19.5},
        )
        self.assertEqual(
            program["weekend"][1],
            {"time": "22:30", "temperature_c": 18.5},
        )

    def test_schedule_rejects_out_of_order_start_times(self):
        weekday = [
            {"start_hour": hour, "start_minute": 0, "temp": 19.0}
            for hour in (5, 7, 6, 12, 18, 22)
        ]
        weekend = [
            {"start_hour": 7, "start_minute": 0, "temp": 19.0},
            {"start_hour": 22, "start_minute": 0, "temp": 19.0},
        ]
        with self.assertRaisesRegex(ValueError, "időrendben"):
            validate_weekly_program(weekday, weekend)

    def test_schedule_rejects_non_half_degree_temperature(self):
        weekday = [
            {"start_hour": hour, "start_minute": 0, "temp": 19.0}
            for hour in (5, 7, 8, 12, 18, 22)
        ]
        weekday[2]["temp"] = 19.2
        weekend = [
            {"start_hour": 7, "start_minute": 0, "temp": 19.0},
            {"start_hour": 22, "start_minute": 0, "temp": 19.0},
        ]
        with self.assertRaisesRegex(ValueError, "0,5"):
            validate_weekly_program(weekday, weekend)

    def test_set_schedule_writes_and_verifies_all_periods(self):
        device = FakeThermostat()
        weekday = [
            {"start_hour": hour, "start_minute": 0, "temp": 19.0}
            for hour in (5, 7, 8, 12, 18, 22)
        ]
        weekend = [
            {"start_hour": 7, "start_minute": 0, "temp": 19.0},
            {"start_hour": 22, "start_minute": 0, "temp": 18.5},
        ]
        _, verified, requested = set_weekly_program(device, weekday, weekend)
        self.assertEqual(len(device.schedule_calls), 1)
        self.assertEqual(weekly_program(verified)["weekend"][1]["temperature_c"], 18.5)
        self.assertEqual(requested["weekday"], weekday)


if __name__ == "__main__": unittest.main()
