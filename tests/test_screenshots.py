import unittest
from pathlib import Path

from pns_wulf.screenshots import resolve_destination


class ScreenshotDestinationTests(unittest.TestCase):
    def test_userhome(self):
        home = Path("/home/tester")
        self.assertEqual(resolve_destination("Userhome", home), Path("/home/tester/Pictures/Screenshots"))

    def test_desktop_fallback(self):
        home = Path("/tmp/pns-wulf-test-home")
        self.assertEqual(resolve_destination("Desktop", home), home / "Desktop")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            resolve_destination("Somewhere")


if __name__ == "__main__":
    unittest.main()
