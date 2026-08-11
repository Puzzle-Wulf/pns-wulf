import unittest

from pns_wulf.cli import build_parser
from pns_wulf.template_capture import parse_region, safe_event_name


class TemplateCaptureTests(unittest.TestCase):
    def test_parse_region_accepts_common_separators(self):
        self.assertEqual(parse_region("10,20,30,40"), (10, 20, 30, 40))
        self.assertEqual(parse_region("10 20 30 40"), (10, 20, 30, 40))
        self.assertEqual(parse_region("10x20x30x40"), (10, 20, 30, 40))

    def test_parse_region_rejects_invalid_size(self):
        with self.assertRaises(ValueError):
            parse_region("10,20,0,40")
        with self.assertRaises(ValueError):
            parse_region("10,20,30")

    def test_safe_event_name_removes_path_components(self):
        self.assertEqual(safe_event_name("../donate/button"), "donate_button")
        self.assertEqual(safe_event_name("alliance research"), "alliance_research")
        with self.assertRaises(ValueError):
            safe_event_name("..")

    def test_click_event_crop_parser(self):
        args = build_parser().parse_args(
            ["click-event", "crop", "donate", "--file", "screen.png", "--region", "1,2,30,40"]
        )
        self.assertEqual(args.ecmd, "crop")
        self.assertEqual(args.name, "donate")
        self.assertEqual(parse_region(args.region), (1, 2, 30, 40))

    def test_click_event_capture_parser(self):
        args = build_parser().parse_args(["click-event", "capture", "help_all"])
        self.assertEqual(args.ecmd, "capture")
        self.assertEqual(args.name, "help_all")
        self.assertIsNone(parse_region(args.region))


if __name__ == "__main__":
    unittest.main()
