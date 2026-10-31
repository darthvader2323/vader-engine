"""Delivery safety across abrupt runner loss and durable-ledger failures."""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import checkpoint
import engine
from run import child_environments


class DurableCheckpointTests(unittest.TestCase):
    def test_credentials_are_separated_between_children(self):
        worker, ledger = child_environments({
            "PATH": "/bin", "GITHUB_TOKEN": "repository-only", "GH_TOKEN": "other-repository",
            "GITHUB_REPOSITORY": "example/repo", "TG_YODA": "telegram-only",
            "BOT_TOKENS_JSON": "telegram-only", "MANAGED_BOTS_JSON": "public-ids",
            "STATE_BRANCH": "community-live",
        }, "/local/socket")
        self.assertNotIn("GITHUB_TOKEN", worker)
        self.assertNotIn("GH_TOKEN", worker)
        self.assertEqual(worker["TG_YODA"], "telegram-only")
        self.assertEqual(ledger["GITHUB_TOKEN"], "repository-only")
        self.assertFalse(any(key.startswith("TG_") or key.endswith("BOTS_JSON") or
                             key == "BOT_TOKENS_JSON" for key in ledger))

    def test_confirm_requires_positive_helper_acknowledgement(self):
        for succeeds in [True, False]:
            with self.subTest(succeeds=succeeds), tempfile.TemporaryDirectory() as directory:
                stopped = threading.Event()
                calls = []
                def save():
                    calls.append(True)
                    if not succeeds:
                        raise RuntimeError("simulated repository failure")
                thread = threading.Thread(target=checkpoint.serve, args=(directory, save, stopped))
                thread.start()
                try:
                    with patch.dict(os.environ, {"VADER_CHECKPOINT_DIR": directory}):
                        if succeeds:
                            checkpoint.confirm_persist()
                            checkpoint.confirm_persist()  # An old acknowledgement cannot confirm a new request.
                            self.assertEqual(len(calls), 2)
                        else:
                            with self.assertRaises(checkpoint.CheckpointUnavailable):
                                checkpoint.confirm_persist()
                finally:
                    stopped.set()
                    thread.join(2)
                self.assertFalse(thread.is_alive())

    def test_absent_helper_fails_closed(self):
        with patch.dict(os.environ, {"VADER_CHECKPOINT_DIR": "/missing/ledger"}):
            with self.assertRaises(checkpoint.CheckpointUnavailable):
                checkpoint.confirm_persist()

    def test_newer_rollback_survives_merging_an_older_claim(self):
        claim = {"updated_at": 100, "used": {"idea": 99}, "scheduled_news_count": 10}
        checkpoint.version_changes(claim, {}, 100)
        rollback = copy.deepcopy(claim)
        rollback["used"].pop("idea")
        rollback["scheduled_news_count"] = 9
        rollback["updated_at"] = 101
        checkpoint.version_changes(rollback, claim, 101)
        for remote, local in [(claim, rollback), (rollback, claim)]:
            merged = checkpoint.merge_state(remote, local)
            self.assertNotIn("idea", merged["used"])
            self.assertEqual(merged["scheduled_news_count"], 9)
        self.assertNotIn("idea", checkpoint.merge_state(merged, {"used": {"idea": 99}})["used"])

    def test_rollback_restores_previous_topic_time_and_media_count(self):
        before = {"last_topic_at": {"source_link": 20}, "sticker_counts": {"yoda": 2}}
        claim = {"last_topic_at": {"source_link": 30}, "sticker_counts": {"yoda": 3}}
        checkpoint.version_changes(claim, before, 30)
        rollback = copy.deepcopy(claim)
        rollback["last_topic_at"]["source_link"] = 20
        rollback["sticker_counts"]["yoda"] = 2
        checkpoint.version_changes(rollback, claim, 31)
        merged = checkpoint.merge_state(claim, rollback)
        self.assertEqual(merged["last_topic_at"]["source_link"], 20)
        self.assertEqual(merged["sticker_counts"]["yoda"], 2)

    def test_legacy_checkpoint_cannot_erase_recovered_history(self):
        recovered = {"used": {"recovered": 1_800_000_000}, "updated_at": 1_800_000_010}
        checkpoint.version_changes(recovered, {}, 1_800_000_010)
        legacy = {"used": {"new": 1_800_000_020}, "updated_at": 1_800_000_020}
        merged = checkpoint.merge_state(recovered, legacy)
        self.assertEqual(set(merged["used"]), {"recovered", "new"})

    def test_later_legacy_claim_is_not_lost_during_handoff(self):
        old = {"used": {}, "ledger_versions": {"used": {"idea": 1_800_000_010}}}
        later = {"used": {"idea": 1_800_000_020}}
        self.assertIn("idea", checkpoint.merge_state(old, later)["used"])

    def test_frozen_or_backwards_clock_does_not_revive_an_older_claim(self):
        claim = {"used": {"idea": 100}}
        checkpoint.version_changes(claim, {}, 100)
        rollback = copy.deepcopy(claim)
        rollback["used"] = {}
        checkpoint.version_changes(rollback, claim, 90)
        self.assertNotIn("idea", checkpoint.merge_state(rollback, claim)["used"])

    def test_audited_recovery_restores_shared_keys_and_count_exactly_once(self):
        state = {"used": {"newer": 30}, "scheduled_news_count": 20}
        recovery = {"recovery_id": "interrupted-run", "observed_at": 40,
                    "used": {"old-delivery": 10}, "scheduled_news_delta": 2}
        self.assertTrue(checkpoint.apply_recovery(state, recovery))
        restored = checkpoint.merge_state({}, state)
        self.assertFalse(checkpoint.apply_recovery(restored, recovery))
        self.assertEqual(restored["scheduled_news_count"], 22)
        self.assertEqual(set(restored["used"]), {"newer", "old-delivery"})


class DeliveryDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for name, value in {"S": Path(self.directory.name), "STATE": engine.initial_state(),
                            "TOK": {"yoda": "test-token"}, "CHAT": "-123"}.items():
            context = patch.object(engine, name, value)
            context.start()
            self.addCleanup(context.stop)
        for name, value in [("log", None), ("maybe_sticker", 0)]:
            context = patch.object(engine, name, return_value=value)
            context.start()
            self.addCleanup(context.stop)
        self.remote = {}

    def save(self):
        local = json.loads((engine.S / "runtime.json").read_text())
        self.remote = checkpoint.merge_state(self.remote, local)

    def test_claim_is_durable_before_telegram_accepts_a_message(self):
        key = engine.digest("discussion:starwars:durable-example")
        def telegram(*_args):
            self.assertIn(key, self.remote["used"])
            raise SystemExit("simulate runner loss after accepted delivery")
        with patch.object(engine, "confirm_persist", side_effect=self.save), \
             patch.object(engine, "tg", side_effect=telegram):
            with self.assertRaises(SystemExit):
                engine.send("yoda", "A new authored example.", content_key="discussion:starwars:durable-example", kind="starwars")
        engine.STATE = checkpoint.merge_state({}, self.remote)
        with patch.object(engine, "tg") as telegram:
            self.assertEqual(engine.send("yoda", "A different style of that idea.",
                content_key="discussion:starwars:durable-example", kind="starwars"), 0)
            telegram.assert_not_called()

    def test_checkpoint_failure_prevents_telegram_delivery(self):
        with patch.object(engine, "confirm_persist", side_effect=checkpoint.CheckpointUnavailable("test")), \
             patch.object(engine, "tg") as telegram:
            with self.assertRaises(checkpoint.CheckpointUnavailable):
                engine.send("yoda", "Do not deliver without a saved claim.")
            telegram.assert_not_called()

    def test_known_rejection_rolls_back_the_durable_reply_claim(self):
        with patch.object(engine, "confirm_persist", side_effect=self.save), \
             patch.object(engine, "tg", return_value={"ok": False, "error_code": 400}):
            self.assertEqual(engine.send("yoda", "A supported answer.", reply=123), 0)
        self.assertNotIn("123", self.remote["replies"])
        engine.STATE = checkpoint.merge_state({}, self.remote)
        with patch.object(engine, "confirm_persist", side_effect=self.save), \
             patch.object(engine, "tg", return_value={"ok": True, "result": {"message_id": 124}}):
            self.assertEqual(engine.send("yoda", "A supported answer.", reply=123), 124)

    def test_unknown_delivery_keeps_the_durable_reply_claim(self):
        with patch.object(engine, "confirm_persist", side_effect=self.save), \
             patch.object(engine, "tg", return_value={"ok": False, "uncertain": True}):
            self.assertEqual(engine.send("yoda", "A supported answer.", reply=123), -1)
        self.assertIn("123", self.remote["replies"])

    def test_media_claim_is_saved_before_delivery_and_retained_on_interruption(self):
        self._media_case(interrupt=True)

    def test_known_media_rejection_remains_retryable_after_restart(self):
        self._media_case(interrupt=False)

    def _media_case(self, interrupt):
        def telegram(_token, method, _params):
            if method == "getStickerSet":
                return {"ok": True, "result": {"stickers": [
                    {"file_id": "file", "file_unique_id": "unique", "is_video": True}]}}
            self.assertIn("uid:unique", self.remote["stickers"])
            if interrupt:
                raise SystemExit("simulate lost runner")
            return {"ok": False, "error_code": 400}
        with patch.object(engine, "confirm_persist", side_effect=self.save), \
             patch.object(engine, "tg", side_effect=telegram), \
             patch.object(engine, "CACHE", {}), patch.object(engine, "LEGACY_STICKERS", set()), \
             patch.object(engine, "PACKS", {"yoda": "reviewed-pack"}), \
             patch.object(engine, "sticker_moods", return_value={"serious"}):
            if interrupt:
                with self.assertRaises(SystemExit):
                    engine.sticker("yoda", "A quiet moment.", kind="starwars")
            else:
                self.assertEqual(engine.sticker("yoda", "A quiet moment.", kind="starwars"), 0)
        self.assertEqual("uid:unique" in self.remote["stickers"], interrupt)


if __name__ == "__main__":
    unittest.main()
