import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pns_wulf.adb import scroll_swipe_coordinates
from pns_wulf.task_store import _save_record, make_scroll_step, numeric_text_value
from pns_wulf.touch_capture import (
    MultiTouchState,
    TouchDeviceInfo,
    parse_touch_devices,
    region_from_touch_points,
)


class TaskInputTests(unittest.TestCase):
    def test_scroll_down_is_upward_finger_swipe(self):
        x1, y1, x2, y2 = scroll_swipe_coordinates(1080, 1920, "down", 0.60)
        self.assertEqual(x1, x2)
        self.assertGreater(y1, y2)

    def test_scroll_up_is_downward_finger_swipe(self):
        x1, y1, x2, y2 = scroll_swipe_coordinates(1080, 1920, "up", 0.60)
        self.assertEqual(x1, x2)
        self.assertLess(y1, y2)

    def test_scroll_step_is_resolution_independent(self):
        self.assertEqual(
            make_scroll_step("down"),
            {"type": "scroll", "direction": "down", "distance": 0.6, "duration_ms": 450},
        )
        with self.assertRaises(ValueError):
            make_scroll_step("diagonal")

    def test_numeric_text_only(self):
        self.assertEqual(numeric_text_value("001234"), "001234")
        with self.assertRaises(ValueError):
            numeric_text_value("12a4")
        with self.assertRaises(ValueError):
            numeric_text_value("")

    def test_recording_filename_cannot_escape_recordings_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            with mock.patch("pns_wulf.task_store.RECORDINGS_DIR", base):
                path = _save_record({"id": "../../outside/task", "query_loop": []})
            self.assertEqual(path.parent, base)
            self.assertEqual(path.name, "outside_task.task.json")
            self.assertTrue(path.exists())

    def test_parse_multitouch_device(self):
        listing = """
add device 1: /dev/input/event2
  name: "fts_touchscreen"
  events:
    ABS (0003):
      ABS_MT_POSITION_X     : value 0, min 0, max 1080, fuzz 0, flat 0, resolution 0
      ABS_MT_POSITION_Y     : value 0, min 0, max 1920, fuzz 0, flat 0, resolution 0
      ABS_MT_TRACKING_ID    : value 0, min 0, max 65535, fuzz 0, flat 0, resolution 0
  input props:
    INPUT_PROP_DIRECT
"""
        devices = parse_touch_devices(listing)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].path, "/dev/input/event2")
        self.assertTrue(devices[0].direct)
        self.assertEqual(devices[0].max_x, 1080)
        self.assertEqual(devices[0].max_y, 1920)

    def test_multitouch_protocol_b_tracks_two_slots(self):
        state = MultiTouchState()
        lines = [
            "EV_ABS ABS_MT_TRACKING_ID 0000001f",
            "EV_ABS ABS_MT_POSITION_X 00000064",
            "EV_ABS ABS_MT_POSITION_Y 000000c8",
            "EV_ABS ABS_MT_SLOT 00000001",
            "EV_ABS ABS_MT_TRACKING_ID 00000020",
            "EV_ABS ABS_MT_POSITION_X 00000384",
            "EV_ABS ABS_MT_POSITION_Y 00000640",
        ]
        for line in lines:
            state.feed(line)
        self.assertEqual(
            state.active_points(),
            [(0, 100, 200), (1, 900, 1600)],
        )

    def test_two_touch_points_become_crop_region(self):
        info = TouchDeviceInfo(
            "/dev/input/event2",
            min_x=0,
            max_x=1000,
            min_y=0,
            max_y=2000,
            direct=True,
        )
        region, mapped = region_from_touch_points(
            [(0, 100, 200), (1, 900, 1600)],
            info,
            (1001, 2001),
        )
        self.assertEqual(mapped, [(100, 200), (900, 1600)])
        self.assertEqual(region, (100, 200, 801, 1401))


if __name__ == "__main__":
    unittest.main()
