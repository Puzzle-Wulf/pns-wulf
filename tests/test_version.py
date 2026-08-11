import json
import unittest

from pns_wulf.constants import VERSION
from pns_wulf.paths import PROJECT_ROOT


class VersionTests(unittest.TestCase):
    def test_display_version(self):
        self.assertEqual(VERSION, "v1.33.7a")
        self.assertEqual((PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip(), VERSION)

    def test_json_versions(self):
        for relative in (
            "MANIFEST.json",
            "config/pns_bot_config.example.json",
            "config/task_queues.example.json",
            "config/click_events.example.json",
            "data/pns_tasks_areas_screens_full.json",
        ):
            data = json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(data["version"], VERSION, relative)

    def test_manifest_matches_repository(self):
        manifest = json.loads((PROJECT_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
        tree = json.loads(
            (PROJECT_ROOT / "data" / "pns_tasks_areas_screens_full.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["task_count"], len(tree.get("tasks", [])))
        self.assertEqual(manifest["area_count"], len(tree.get("areas", {})))
        self.assertEqual(manifest["screen_count"], len(tree.get("screens", {})))

        entry_points = set(manifest.get("entry_points", []))
        expected = {"pns-bot", "pns-bot.sh", "pns-bot.cmd", "pns_bot.py"}
        self.assertTrue(expected.issubset(entry_points))
        for relative in entry_points:
            self.assertTrue((PROJECT_ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
