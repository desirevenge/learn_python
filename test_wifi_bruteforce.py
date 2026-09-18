"""Unit tests for wifi_bruteforce using a fake pywifi module.

These tests do not require a real Wi-Fi adapter or the pywifi package;
``wifi_bruteforce.pywifi`` is swapped for a lightweight fake that mimics the
subset of the pywifi API used by the script.
"""

import tempfile
import types
import unittest
from pathlib import Path

import wifi_bruteforce as wb


class FakeConst:
    AUTH_ALG_OPEN = 0
    AKM_TYPE_WPA2PSK = 1
    CIPHER_TYPE_CCMP = 2
    IFACE_CONNECTED = 3


class FakeProfile:
    def __init__(self):
        self.ssid = None
        self.auth = None
        self.akm = []
        self.cipher = None
        self.key = None


class FakeIface:
    """Mimics the pywifi interface object."""

    def __init__(self, networks, correct):
        # networks: list of (ssid, signal); correct: dict ssid -> password
        self.networks = networks
        self.correct = correct
        self.profiles = []
        self.connected = False
        self.scan_calls = 0

    def scan(self):
        self.scan_calls += 1

    def scan_results(self):
        return [
            types.SimpleNamespace(ssid=ssid, signal=signal)
            for ssid, signal in self.networks
        ]

    def remove_all_network_profiles(self):
        self.profiles = []

    def add_network_profile(self, profile):
        self.profiles.append(profile)
        return profile

    def connect(self, profile):
        self.connected = self.correct.get(profile.ssid) == profile.key

    def disconnect(self):
        self.connected = False

    def status(self):
        return FakeConst.IFACE_CONNECTED if self.connected else 0


def install_fake_pywifi(iface):
    fake = types.SimpleNamespace(
        PyWiFi=lambda: types.SimpleNamespace(interfaces=lambda: [iface]),
        Profile=FakeProfile,
        const=FakeConst,
    )
    wb.pywifi = fake
    return fake


class NoSleepMixin:
    """Neutralize time.sleep so the WiFi interaction tests run fast."""

    def setUp(self):
        self._original_sleep = wb.time.sleep
        wb.time.sleep = lambda seconds: None

    def tearDown(self):
        wb.time.sleep = self._original_sleep


class GenerateDictTest(unittest.TestCase):
    def test_writes_all_combinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dict.txt"
            total = wb.generate_password_dict("ab", 3, path)
            self.assertEqual(total, 8)  # 2 ** 3
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 8)
            self.assertIn("aaa", lines)
            self.assertIn("bbb", lines)

    def test_returns_zero_for_empty_alphabet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dict.txt"
            total = wb.generate_password_dict("", 3, path)
            self.assertEqual(total, 0)


class ScanNetworksTest(NoSleepMixin, unittest.TestCase):
    def test_deduplicates_and_sorts_by_signal(self):
        iface = FakeIface(
            networks=[
                ("NetA", -50),
                ("NetB", -30),
                ("NetA", -20),  # stronger duplicate
                ("NetC", -90),
            ],
            correct={},
        )
        result = wb.scan_networks(iface, set(), 10)
        self.assertEqual(result, ["NetA", "NetB", "NetC"])

    def test_respects_exclude_and_count(self):
        iface = FakeIface(
            networks=[("NetA", -50), ("NetB", -30), ("NetC", -90)],
            correct={},
        )
        result = wb.scan_networks(iface, {"NetB"}, 1)
        self.assertEqual(result, ["NetA"])

    def test_ignores_empty_ssid(self):
        iface = FakeIface(networks=[("", -50), ("NetA", -40)], correct={})
        result = wb.scan_networks(iface, set(), 10)
        self.assertEqual(result, ["NetA"])


class TestWifiTest(NoSleepMixin, unittest.TestCase):
    def test_correct_password_connects(self):
        iface = FakeIface(networks=[], correct={"Home": "secret"})
        install_fake_pywifi(iface)
        self.assertTrue(wb.test_wifi(iface, "Home", "secret"))

    def test_wrong_password_fails(self):
        iface = FakeIface(networks=[], correct={"Home": "secret"})
        install_fake_pywifi(iface)
        self.assertFalse(wb.test_wifi(iface, "Home", "wrong"))


class BruteforceWifiTest(NoSleepMixin, unittest.TestCase):
    def test_finds_password_and_stops(self):
        iface = FakeIface(networks=[], correct={"Home": "1234"})
        install_fake_pywifi(iface)
        with tempfile.TemporaryDirectory() as tmp:
            dict_path = Path(tmp) / "dict.txt"
            dict_path.write_text("0000\n1234\n9999\n", encoding="utf-8")
            cracked = wb.bruteforce_wifi(iface, ["Home"], dict_path)
        self.assertEqual(cracked, [("Home", "1234")])

    def test_cracks_multiple_networks(self):
        iface = FakeIface(networks=[], correct={"A": "1", "B": "2"})
        install_fake_pywifi(iface)
        with tempfile.TemporaryDirectory() as tmp:
            dict_path = Path(tmp) / "dict.txt"
            dict_path.write_text("1\n2\n", encoding="utf-8")
            cracked = wb.bruteforce_wifi(iface, ["A", "B"], dict_path)
        self.assertEqual(cracked, [("A", "1"), ("B", "2")])

    def test_no_match_returns_empty(self):
        iface = FakeIface(networks=[], correct={"A": "secret"})
        install_fake_pywifi(iface)
        with tempfile.TemporaryDirectory() as tmp:
            dict_path = Path(tmp) / "dict.txt"
            dict_path.write_text("nope\n", encoding="utf-8")
            cracked = wb.bruteforce_wifi(iface, ["A"], dict_path)
        self.assertEqual(cracked, [])


class MainTest(unittest.TestCase):
    def test_generate_dict_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            dict_path = Path(tmp) / "dict.txt"
            code = wb.main(
                ["--generate-dict", "--dict", str(dict_path), "--alphabet", "ab",
                 "--length", "2"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(dict_path.read_text(encoding="utf-8").splitlines()), 4)


if __name__ == "__main__":
    unittest.main()