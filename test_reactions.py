"""Movie reactions must fit the actual speaker, tone and delivered comment."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import engine
import reactions


class ReactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in {
            "S": Path(self.tmp.name), "STATE": engine.initial_state(),
            "CHAT": "-123", "TOK": {"yoda": "test-token"},
            "CACHE": {}, "BACKOFF": {}, "LEGACY_STICKERS": set(),
            "PACKS": {"yoda": "vadersocial_yoda_motion1_by_batmanbrucewaynebot"},
        }.items():
            mock = patch.object(engine, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        quiet = patch.object(engine, "log")
        quiet.start()
        self.addCleanup(quiet.stop)

    def api(self, outgoing):
        count = len(reactions.CATALOG[engine.PACKS["yoda"]]["clips"])
        def call(token, method, params=None):
            if method == "getStickerSet":
                return {"ok": True, "result": {"stickers": [
                    {"file_id": "file-" + str(i), "file_unique_id": "uid-" + str(i), "is_video": True}
                    for i in range(count)]}}
            if method == "sendSticker":
                outgoing.append(params)
                return {"ok": True, "result": {"message_id": 901}}
            self.fail("Unexpected API method: " + method)
        return call

    def test_curated_slots_match_the_published_manifest_order(self):
        manifest = json.loads((reactions.HERE / "stickers/manifest.json").read_text())
        groups = {}
        for entry in manifest:
            groups.setdefault(entry["character"], []).append(entry["file"])
        for pack, record in reactions.CATALOG.items():
            self.assertEqual([c["file"] for c in record["clips"]], groups[record["character"]])
            for clip in record["clips"]:
                self.assertLessEqual(set(clip["moods"]), reactions.MOODS)

    def test_clear_moods_and_negation_do_not_become_random_cheer(self):
        cases = [("Sad, that ending makes me.", "sad"),
                 ("Funny, that hairbrush joke was.", "playful"),
                 ("Happy for Luke, I am.", "happy"),
                 ("Not happy about this.", "serious"),
                 ("Not sad, just thinking.", "serious"),
                 ("The Death Star plans change the battle.", "serious"),
                 ("Quiet, that room becomes.", "serious")]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(reactions.comment_mood(text, "starwars"), expected)

    def test_real_world_loss_and_service_messages_have_no_reaction(self):
        self.assertIsNone(reactions.comment_mood("People killed in an attack", "world"))
        self.assertIsNone(reactions.comment_mood("Not happy after people killed in an attack", "world"))
        self.assertIsNone(reactions.comment_mood("Rapper's funeral announced", "rap"))
        for kind in ("service", "pin", "general"):
            self.assertIsNone(reactions.comment_mood("Happy to help", kind))

    def test_authored_banter_retains_its_mood_in_either_writing_style(self):
        for text in ("Chewie, your hairbrush has requested a transfer.",
                     "Big grooming advice from someone with three hairs."):
            self.assertEqual(reactions.comment_mood(text, "starwars", "roleplay:hairbrush_transfer:1"), "playful")

    def test_new_authored_jokes_keep_playful_tone_in_both_styles(self):
        from conversation import ROLEPLAY_THREADS
        from writing_styles import render_style
        selected = {key: turns for key, turns in ROLEPLAY_THREADS
                    if key in {"wookiee_alarm", "yoda_waiting_room"}}
        self.assertEqual(len(selected), 2)
        for key, turns in selected.items():
            for index, (speaker, text) in enumerate(turns):
                content_key = f"roleplay:{key}:{index}"
                for style in ("analytical", "plain"):
                    rendered = render_style(text, "starwars", content_key, speaker, style)
                    self.assertEqual(reactions.comment_mood(rendered, "starwars", content_key), "playful")

    def test_unknown_pack_slot_or_wrong_character_is_not_guessed(self):
        pack = engine.PACKS["yoda"]
        self.assertFalse(reactions.sticker_moods("chew", pack, 0))
        self.assertFalse(reactions.sticker_moods("yoda", "other-pack", 0))
        self.assertFalse(reactions.sticker_moods("yoda", pack, 500))

    def test_sad_yoda_selects_only_sad_yoda_and_replies_to_his_comment(self):
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api(outgoing)):
            self.assertEqual(engine.sticker("yoda", "Sad, that ending feels.", "starwars", reply_to=800), 1)
        self.assertEqual([p["sticker"] for p in outgoing], ["file-8"])
        self.assertEqual(outgoing[0]["reply_parameters"], {"message_id": 800, "allow_sending_without_reply": False})
        self.assertIn("uid:uid-8", engine.STATE["stickers"])

    def test_used_sad_clip_cannot_fall_back_to_fresh_laughing_clip(self):
        engine.STATE["stickers"]["uid:uid-8"] = 1
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api(outgoing)):
            self.assertEqual(engine.sticker("yoda", "Sad, that ending feels.", "starwars"), 0)
        self.assertFalse(outgoing)
        self.assertIn("uid:uid-8", engine.STATE["stickers"])
        self.assertFalse(engine.CACHE)

    def test_standalone_sticker_without_a_comment_is_skipped(self):
        with patch.object(engine, "tg") as api:
            self.assertEqual(engine.sticker("yoda"), 0)
        api.assert_not_called()

    def test_successful_text_passes_its_final_body_and_message_id(self):
        raw = "Sample headline\nExample Wire · Oct 31, 2026\nhttps://example.org/story"
        with patch.object(engine, "tg", return_value={"ok": True, "result": {"message_id": 800}}), \
             patch.object(engine, "maybe_sticker") as reaction:
            self.assertEqual(engine.send("yoda", raw, content_key="news:sample", kind="world"), 800)
        reaction.assert_called_once_with("yoda", "Sample headline", "world", "news:sample", 800)

    def test_failed_or_uncertain_text_never_posts_a_detached_reaction(self):
        for outcome in ({"ok": False, "error_code": 400}, {"ok": False, "uncertain": True}):
            with self.subTest(outcome=outcome):
                engine.STATE = engine.initial_state()
                with patch.object(engine, "tg", return_value=outcome), \
                     patch.object(engine, "maybe_sticker") as reaction:
                    engine.send("yoda", "Sad, that ending feels.", kind="starwars")
                reaction.assert_not_called()

    def test_topical_native_reply_uses_the_new_comment_id_for_its_gif(self):
        with patch.object(engine, "tg", return_value={"ok": True, "result": {"message_id": 800}}), \
             patch.object(engine, "maybe_sticker") as reaction:
            engine.send("yoda", "Sad, that ending feels.", reply=700, kind="starwars")
        self.assertEqual(reaction.call_args.args[-1], 800)


if __name__ == "__main__":
    unittest.main()
