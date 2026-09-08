from __future__ import annotations

import unittest

from app.computherm_service import restore_test, start_test, suppress_heat


class FakeThermostat:
    def __init__(self):
        self.state = {"power":1,"active":0,"auto_mode":1,"loop_mode":1,"sensor":0,
                      "room_temp":26.0,"thermostat_temp":19.0,"osv":42,"dif":2,
                      "svh":22,"svl":5,"room_temp_adj":0.0,"fre":0,"poweron":1}
        self.advanced_calls=[]
    def get_full_status(self): return dict(self.state)
    def set_mode(self, auto_mode, loop_mode, sensor):
        self.state.update(auto_mode=auto_mode,loop_mode=loop_mode,sensor=sensor)
    def set_temp(self, value): self.state["thermostat_temp"]=value
    def set_advanced(self, loop_mode,sensor,osv,dif,svh,svl,adj,fre,poweron):
        self.advanced_calls.append(svh)
        self.state.update(loop_mode=loop_mode,sensor=sensor,osv=osv,dif=dif,svh=svh,
                          svl=svl,room_temp_adj=adj,fre=fre,poweron=poweron)


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


if __name__ == "__main__": unittest.main()
