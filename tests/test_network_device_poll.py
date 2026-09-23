import unittest
from unittest.mock import MagicMock, patch

from poll_devices import DeviceConfig, poll_network_device


def config() -> DeviceConfig:
    return DeviceConfig(
        source_system="network_device",
        hostname="printer.home",
        expected_ip="192.0.2.60",
        mac_address="",
        device_id="printer",
    )


class NetworkDevicePollTest(unittest.TestCase):
    @patch("poll_devices.urllib.request.urlopen")
    @patch("poll_devices.subprocess.run")
    @patch("poll_devices.socket.getaddrinfo")
    def test_records_ping_and_http_availability(self, getaddrinfo, run, urlopen) -> None:
        getaddrinfo.return_value = [(2, 1, 6, "", ("192.0.2.60", 80))]
        run.return_value.returncode = 0
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        urlopen.return_value = response

        result = poll_network_device(config(), 5)

        self.assertTrue(result.success)
        self.assertTrue(result.state["raw"]["ping_ok"])
        self.assertTrue(result.state["raw"]["http_ok"])
        self.assertEqual(result.state["raw"]["http_status"], 200)
        self.assertEqual(result.state["raw"]["resolved_ip"], "192.0.2.60")
        self.assertEqual(result.state["raw"]["check_mode"], "http")

    @patch("poll_devices.subprocess.run")
    @patch("poll_devices.socket.getaddrinfo")
    def test_ping_only_device_does_not_require_http(self, getaddrinfo, run) -> None:
        getaddrinfo.return_value = [(2, 1, 6, "", ("192.0.2.61", 80))]
        run.return_value.returncode = 0
        ping_config = DeviceConfig(
            source_system="network_device",
            hostname="mesh-node.home",
            expected_ip="192.0.2.61",
            mac_address="02:00:00:00:00:61",
            device_id="mesh-node",
            network_check_mode="ping",
            network_device_kind="deco",
        )

        result = poll_network_device(ping_config, 5)

        self.assertTrue(result.success)
        self.assertTrue(result.state["raw"]["ping_ok"])
        self.assertIsNone(result.state["raw"]["http_ok"])
        self.assertEqual(result.state["raw"]["check_mode"], "ping")

    @patch("poll_devices.subprocess.run")
    @patch("poll_devices.socket.getaddrinfo")
    def test_ping_only_failure_is_reported(self, getaddrinfo, run) -> None:
        getaddrinfo.return_value = [(2, 1, 6, "", ("192.0.2.61", 80))]
        run.return_value.returncode = 1
        ping_config = DeviceConfig(
            source_system="network_device",
            hostname="mesh-node.home",
            expected_ip="192.0.2.61",
            mac_address="",
            device_id="mesh-node",
            network_check_mode="ping",
        )

        result = poll_network_device(ping_config, 5)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "ping_unreachable")

    @patch("poll_devices.socket.getaddrinfo", side_effect=OSError("not found"))
    def test_reports_dns_failure(self, _getaddrinfo) -> None:
        result = poll_network_device(config(), 5)
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "dns_failed")


if __name__ == "__main__":
    unittest.main()
