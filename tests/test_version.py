import json
import unittest
from pathlib import Path

from pns_wulf.constants import VERSION
from pns_wulf.paths import PROJECT_ROOT


class VersionTests(unittest.TestCase):
    def test_display_version(self):
        self.assertEqual(VERSION, "v1.33.7a")

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


if __name__ == "__main__":
    unittest.main()
