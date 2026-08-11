import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pns_wulf.screenshots import _capture_stamp, capture_destination, resolve_destination


class FakeDevice:
    serial = "emulator:5554"

    def screenshot(self, path):
        path.write_bytes(b"png")
        return path


class ScreenshotDestinationTests(unittest.TestCase):
    def test_userhome(self):
        home = Path("/home/tester")
        expected = home.expanduser().resolve() / "Pictures" / "Screenshots"
        self.assertEqual(resolve_destination("Userhome", home), expected)

    def test_desktop_fallback(self):
        home = Path("/tmp/pns-wulf-test-home")
        expected = home.expanduser().resolve() / "Desktop"
        self.assertEqual(resolve_destination("Desktop", home), expected)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            resolve_destination("Somewhere")

    def test_capture_stamp_includes_subsecond_component(self):
        with mock.patch("pns_wulf.screenshots.time.strftime", return_value="20260811-063000"), mock.patch(
            "pns_wulf.screenshots.time.time_ns", return_value=1_234_567_890
        ):
            self.assertEqual(_capture_stamp(), "20260811-063000-234567890")

    def test_capture_destination_uses_safe_unique_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            with mock.patch("pns_wulf.screenshots.resolve_destination", return_value=base), mock.patch(
                "pns_wulf.screenshots._capture_stamp", return_value="20260811-063000-123456789"
            ):
                path = capture_destination(FakeDevice(), "Desktop")
            self.assertEqual(path.name, "pns-wulf_emulator_5554_20260811-063000-123456789.png")
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
