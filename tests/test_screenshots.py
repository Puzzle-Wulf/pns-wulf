import unittest
from pathlib import Path

from pns_wulf.screenshots import resolve_destination


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


if __name__ == "__main__":
    unittest.main()
