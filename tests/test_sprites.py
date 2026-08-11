import tempfile
import unittest
import zipfile
from pathlib import Path

from pns_wulf.sprites import extract_images_from_archive, extract_zip, safe_archive_path


class SpriteExtractionTests(unittest.TestCase):
    def test_safe_archive_path_rejects_escape_and_drive_paths(self):
        self.assertEqual(safe_archive_path("assets/pas/menu/back.png"), "assets/pas/menu/back.png")
        self.assertIsNone(safe_archive_path("../escape.png"))
        self.assertIsNone(safe_archive_path("/absolute.png"))
        self.assertIsNone(safe_archive_path("C:/escape.png"))

    def test_extractors_keep_outputs_inside_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive_path = base / "sample.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("assets/pas/menu/back.png", b"good")
                archive.writestr("assets/pas/../../escape.png", b"bad")
                archive.writestr("../outside.png", b"bad")
                archive.writestr("C:/pas/drive.png", b"bad")

            raw = base / "raw"
            count = extract_zip(archive_path, raw)
            self.assertEqual(count, 1)
            self.assertTrue((raw / "assets" / "pas" / "menu" / "back.png").exists())
            self.assertFalse((base / "escape.png").exists())
            self.assertFalse((base / "outside.png").exists())

            sprites = base / "sprites"
            index = []
            extract_images_from_archive(archive_path, sprites, index)
            self.assertTrue((sprites / "pas" / "menu" / "back.png").exists())
            self.assertEqual(len(index), 1)
            self.assertFalse((base / "escape.png").exists())
            self.assertFalse((base / "outside.png").exists())


if __name__ == "__main__":
    unittest.main()
