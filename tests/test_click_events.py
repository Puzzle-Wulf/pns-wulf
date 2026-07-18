import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pns_wulf.click_events import ClickEventRegistry, ClickResolution, PauseController


class FakeDevice:
    serial = "emulator-5554"

    def screenshot(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-png")
        return path


class FakeTTY:
    def isatty(self):
        return True


class ClickEventTests(unittest.TestCase):
    def test_coordinate_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = ClickEventRegistry(Path(temp) / "events.json")
            registry.set_coordinate("donate", 512, 840)
            resolution = registry.resolve({"type": "tap_area", "target": "donate"}, Path(temp) / "screen.png")
            self.assertTrue(resolution.resolved)
            self.assertEqual((resolution.x, resolution.y), (512, 840))
            self.assertEqual(resolution.source, "registry-coordinate")

    def test_missing_template_pauses_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = ClickEventRegistry(Path(temp) / "events.json")
            resolution = registry.resolve({"type": "tap_area", "target": "missing_button"}, Path(temp) / "screen.png")
            self.assertFalse(resolution.resolved)
            self.assertIn("PNG-Vorlage fehlt", resolution.reason)

    def test_pause_accepts_coordinates_and_resumes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            registry = ClickEventRegistry(base / "events.json")
            config = {
                "screenshots_dir": str(base / "shots"),
                "pause_state_file": str(base / "pause-state.json"),
                "click_match_threshold": 0.86,
            }
            controller = PauseController(config, FakeDevice(), registry)
            initial_screen = base / "initial.png"
            initial_screen.write_bytes(b"fake-png")
            initial = ClickResolution(False, "donate", reason="PNG-Vorlage fehlt", template=str(base / "donate.png"))
            with mock.patch("sys.stdin", FakeTTY()), mock.patch("builtins.input", return_value="coords 512 840"):
                result = controller.pause({"id": "task", "name": "Task"}, {"type": "tap_area", "target": "donate"}, initial_screen, initial)
            self.assertTrue(result.resolved)
            self.assertEqual((result.x, result.y), (512, 840))
            self.assertFalse((base / "pause-state.json").exists())


if __name__ == "__main__":
    unittest.main()
