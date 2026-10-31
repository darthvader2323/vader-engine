"""Publishing must preserve permanent sticker identities and be safe to rerun."""
import copy
import json
import unittest
from unittest.mock import patch

import sticker_setup


class PackPublishingTests(unittest.TestCase):
    def setUp(self):
        self.items = [{"file": name + ".webm", "emoji": "💚", "title": "Yoda Motion"}
                      for name in ("old", "new")]
        self.pack = {"stickers": [{"file_id": "old", "file_unique_id": "old", "is_video": True}]}
        self.methods = []

    def api(self, method, fields=None, files=None, allow_missing=False):
        self.methods.append(method)
        if method == "getStickerSet":
            return copy.deepcopy(self.pack)
        if method == "addStickerToSet":
            self.assertEqual(json.loads(fields["sticker"])["format"], "video")
            uid = files["video"].stem
            if uid not in {s["file_unique_id"] for s in self.pack["stickers"]}:
                self.pack["stickers"].append({"file_id": uid, "file_unique_id": uid, "is_video": True})
            return True
        if method == "createNewStickerSet":
            self.assertTrue(all(s["format"] == "video" for s in json.loads(fields["stickers"])))
            self.pack = {"stickers": [{"file_id": p.stem, "file_unique_id": p.stem, "is_video": True}
                                     for p in files.values()]}
            return True
        self.fail("Unexpected method: " + method)

    def test_append_and_rerun_preserve_old_ids_without_duplicates(self):
        with patch.object(sticker_setup, "call", side_effect=self.api), patch.object(sticker_setup.time, "sleep"):
            pack, added = sticker_setup.publish_pack("yoda_pack", self.items, 123)
            self.assertEqual(added, 1)
            self.assertEqual(pack["stickers"][0]["file_unique_id"], "old")
            pack, added = sticker_setup.publish_pack("yoda_pack", self.items, 123)
        self.assertEqual(added, 0)
        self.assertEqual(len(pack["stickers"]), 2)
        self.assertFalse(any("delete" in m.lower() or "replace" in m.lower() for m in self.methods))

    def test_new_pack_is_created_as_video(self):
        self.pack = None
        with patch.object(sticker_setup, "call", side_effect=self.api), patch.object(sticker_setup.time, "sleep"):
            pack, added = sticker_setup.publish_pack("yoda_pack", self.items, 123)
        self.assertEqual(added, 2)
        self.assertEqual(len(pack["stickers"]), 2)

    def test_mixed_existing_pack_is_rejected_before_mutation(self):
        self.pack["stickers"][0]["is_video"] = False
        with patch.object(sticker_setup, "call", side_effect=self.api):
            with self.assertRaisesRegex(SystemExit, "video-only"):
                sticker_setup.publish_pack("yoda_pack", self.items, 123)
        self.assertEqual(self.methods, ["getStickerSet"])

    def test_uncertain_append_stops_without_repeating(self):
        def api(method, *args, **kwargs):
            if method == "addStickerToSet":
                self.methods.append(method)
                raise SystemExit("delivery uncertain")
            return self.api(method, *args, **kwargs)
        with patch.object(sticker_setup, "call", side_effect=api):
            with self.assertRaisesRegex(SystemExit, "uncertain"):
                sticker_setup.publish_pack("yoda_pack", self.items, 123)
        self.assertEqual(self.methods.count("addStickerToSet"), 1)


if __name__ == "__main__":
    unittest.main()
