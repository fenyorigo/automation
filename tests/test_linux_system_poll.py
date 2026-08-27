import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from poll_devices import DeviceConfig, poll_linux_system, read_linux_cpu_temperature


class LinuxSystemPollTest(unittest.TestCase):
    def test_reads_package_temperature_from_hwmon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hwmon = root / "hwmon" / "hwmon0"
            hwmon.mkdir(parents=True)
            (hwmon / "name").write_text("coretemp\n", encoding="utf-8")
            (hwmon / "temp1_label").write_text("Package id 0\n", encoding="utf-8")
            (hwmon / "temp1_input").write_text("48750\n", encoding="utf-8")
            self.assertEqual(read_linux_cpu_temperature(root), 48.75)

    @patch("poll_devices.read_linux_cpu_temperature", return_value=52.0)
    @patch("poll_devices.os.getloadavg", return_value=(0.25, 0.5, 0.75))
    @patch("poll_devices.socket.gethostname", return_value="think260x")
    def test_polls_temperature_and_load(self, *_mocks) -> None:
        config = DeviceConfig(
            source_system="linux_system",
            hostname="think260x",
            expected_ip="192.168.0.1",
            mac_address="",
            device_id="thinkpad260x",
            local_hostname="think260x",
        )
        result = poll_linux_system(config, 5)
        self.assertTrue(result.success)
        values = {item["sensor_type"]: item["value"] for item in result.measurements}
        self.assertEqual(values["temperature"], 52.0)
        self.assertEqual(values["load_1m"], 0.25)
        self.assertEqual(values["load_5m"], 0.5)
        self.assertEqual(values["load_15m"], 0.75)

    @patch("poll_devices.socket.gethostname", return_value="air-wifi")
    def test_rejects_forced_local_polling_on_the_wrong_host(self, _hostname) -> None:
        config = DeviceConfig(
            source_system="linux_system",
            hostname="think260x",
            expected_ip="192.168.0.1",
            mac_address="",
            device_id="thinkpad260x",
            local_hostname="think260x",
            metrics_transport="local",
        )
        result = poll_linux_system(config, 5)
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "local_host_mismatch")

    @patch("poll_devices.socket.gethostname", return_value="think260x")
    @patch("poll_devices.subprocess.run")
    def test_polls_remote_host_over_restricted_ssh(self, run, _hostname) -> None:
        payload = {
            "schema_version": 1, "hostname": "think220x", "kernel": "test",
            "cpu_count": 4, "cpu_temperature_c": 60.0,
            "load_1m": 0.123, "load_5m": 0.054, "load_15m": 0.008,
        }
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(payload)
        run.return_value.stderr = ""
        config = DeviceConfig(
            source_system="linux_system", hostname="thinkpad220x",
            local_hostname="think220x", expected_ip="192.168.10.2",
            mac_address="", device_id="thinkpad220x", metrics_transport="ssh",
        )
        result = poll_linux_system(config, 5)
        self.assertTrue(result.success)
        self.assertEqual(result.identity["hostname"], "think220x")
        self.assertIn("-T", run.call_args.args[0])
        self.assertNotIn("shell", run.call_args.kwargs)

    @patch("poll_devices.socket.gethostname", return_value="think260x")
    @patch("poll_devices.subprocess.run")
    def test_rejects_wrong_remote_identity(self, run, _hostname) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({
            "schema_version": 1, "hostname": "wrong-host", "kernel": "test",
            "cpu_count": 4, "cpu_temperature_c": 50,
            "load_1m": 0, "load_5m": 0, "load_15m": 0,
        })
        run.return_value.stderr = ""
        config = DeviceConfig(
            source_system="linux_system", hostname="thinkpad220x",
            local_hostname="think220x", expected_ip="192.168.10.2",
            mac_address="", device_id="thinkpad220x", metrics_transport="ssh",
        )
        result = poll_linux_system(config, 5)
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "invalid_response")


if __name__ == "__main__":
    unittest.main()
