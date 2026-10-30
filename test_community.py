"""User-visible routing, delivery, data-quality and sticker behavior."""
import datetime as dt
import email.utils
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import engine
from checkpoint import merge_state

class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for name, value in {
            "S": Path(self.directory.name),
            "CHAT": "-123456",
            "STATE": engine.initial_state(),
            "TOK": {"brucewayne": "desk-token", "yoda": "yoda-token", "chucky": "chucky-token"},
            "CACHE": {}, "BACKOFF": {}, "LEGACY_STICKERS": set(),
        }.items():
            replacement = patch.object(engine, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        quiet = patch.object(engine, "log")
        quiet.start()
        self.addCleanup(quiet.stop)

    def message(self, update_id=100, mid=300, text="How much for Instagram verification?", username="visitor"):
        return {"update_id": update_id, "message": {
            "message_id": mid, "date": int(time.time()),
            "chat": {"id": -123456}, "from": {"id": 5, "username": username, "is_bot": False},
            "text": text}}

    def api_for(self, updates, outgoing, outcome=None):
        def api(token, method, params=None):
            if method == "getUpdates":
                offset = (params or {}).get("offset", 0)
                return {"ok": True, "result": [item for item in updates if item["update_id"] >= offset]}
            if method == "sendMessage":
                outgoing.append((token, dict(params)))
                return outcome or {"ok": True, "result": {"message_id": 500 + len(outgoing)}}
            return {"ok": True, "result": {}}
        return api

    def test_replayed_service_question_gets_one_designated_answer(self):
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api_for([self.message()], outgoing)):
            self.assertEqual(engine.answer_humans(), 1)
            self.assertEqual(engine.answer_humans(), 0)
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0][0], "desk-token")
        self.assertIn("@darthvader", outgoing[0][1]["text"])
        self.assertTrue(outgoing[0][1]["text"].startswith("[Bruce Wayne bot]"))
        self.assertIn("privately", outgoing[0][1]["text"])
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 101)

    def test_owner_music_question_gets_a_relevant_answer_not_praise(self):
        outgoing = []
        update = self.message(text="Yo everybody who is your favorite rapper?", username="darthvader")
        with patch.object(engine, "youngboy", return_value=[]), \
             patch.object(engine, "tg", side_effect=self.api_for([update], outgoing)):
            self.assertEqual(engine.answer_humans(), 1)
        self.assertEqual(len(outgoing), 1)
        text = outgoing[0][1]["text"].lower()
        self.assertTrue("youngboy" in text or "rapper" in text)
        self.assertNotIn("founder", text)
        self.assertNotIn("built this", text)

    def test_service_intent_takes_priority_over_fragment_topic(self):
        self.assertEqual(engine.topic("I want to buy a username on Fragment"), "service")
        self.assertEqual(engine.topic("How much for TikTok verification?"), "service")
        self.assertEqual(engine.topic("What is the BTC price?"), "crypto")
        self.assertFalse(engine.is_service("How much did the company pay in the acquisition?"))

    def test_batch_limit_does_not_acknowledge_unhandled_updates(self):
        outgoing = []
        updates = [self.message(100 + i, 300 + i) for i in range(3)]
        with patch.object(engine, "tg", side_effect=self.api_for(updates, outgoing)):
            self.assertEqual(engine.answer_humans(limit=2), 2)
            self.assertEqual(engine.STATE["offsets"]["brucewayne"], 102)
            self.assertNotIn("302", engine.STATE["replies"])
            self.assertEqual(engine.answer_humans(limit=2), 1)
        self.assertEqual(len(outgoing), 3)
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 103)

    def test_failed_send_leaves_the_update_pending(self):
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api_for(
                [self.message()], outgoing, {"ok": False, "error_code": 403})):
            self.assertEqual(engine.answer_humans(), 0)
        self.assertNotIn("brucewayne", engine.STATE["offsets"])
        self.assertNotIn("300", engine.STATE["replies"])

    def test_unknown_delivery_is_not_blindly_retried(self):
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api_for(
                [self.message()], outgoing, {"ok": False, "uncertain": True})):
            engine.answer_humans()
            engine.answer_humans()
        self.assertEqual(len(outgoing), 1)
        self.assertIn("300", engine.STATE["replies"])

    def test_messages_in_other_groups_are_not_answered(self):
        outgoing = []
        update = self.message()
        update["message"]["chat"]["id"] = -999
        with patch.object(engine, "tg", side_effect=self.api_for([update], outgoing)):
            engine.answer_humans()
        self.assertEqual(outgoing, [])
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 101)

    def test_scripted_pool_does_not_reset_when_exhausted(self):
        for text in engine.STAR_WARS:
            engine.STATE["used"][engine.digest(text)] = time.time()
        self.assertIsNone(engine.pick(engine.STAR_WARS))

    def test_rss_requires_a_link_and_a_recent_date(self):
        now = dt.datetime.now(dt.timezone.utc)
        recent = email.utils.format_datetime(now)
        old = email.utils.format_datetime(now - dt.timedelta(days=30))
        xml = ("<rss><channel>"
               "<item><title>Fresh headline</title><link>https://example.org/fresh</link>"
               "<pubDate>%s</pubDate></item>"
               "<item><title>Old headline</title><link>https://example.org/old</link>"
               "<pubDate>%s</pubDate></item>"
               "<item><title>Undated headline</title><link>https://example.org/no-date</link></item>"
               "</channel></rss>") % (recent, old)
        with patch.object(engine, "get_url", return_value=xml.encode()):
            records = engine.rss("https://example.org/feed")
        self.assertEqual(len(records), 1)
        self.assertIn("https://example.org/fresh", records[0][0])
        self.assertIn("Fresh headline", records[0][0])

    def test_pregame_is_not_reported_as_a_live_zero_zero_score(self):
        fixture = {"events": [{"id": "game1", "links": [{"href": "https://www.espn.com/game1"}],
            "competitions": [{"status": {"type": {"state": "pre", "shortDetail": "7:00 PM EDT"}},
                "competitors": [
                    {"homeAway": "home", "score": "0", "team": {"displayName": "Home"}},
                    {"homeAway": "away", "score": "0", "team": {"displayName": "Away"}}]}]}]}
        with patch.object(engine, "jget", return_value=fixture):
            records = engine.sports()
        self.assertIn("scheduled", records[0][0])
        self.assertNotIn("0–0", records[0][0])
        self.assertNotIn("Live", records[0][0])
        self.assertEqual(engine.STATE["league_cursor"], 1)

    def test_ton_is_not_mislabeled_gram_and_stale_prices_are_skipped(self):
        quotes = {
            "the-open-network": {"usd": 2.0, "usd_24h_change": 1.2, "last_updated_at": time.time()},
            "bitcoin": {"usd": 100, "usd_24h_change": -1, "last_updated_at": time.time() - 3600}}
        with patch.object(engine, "jget", return_value=quotes):
            records = engine.crypto()
        self.assertIn("TON $2.00", records[0][0])
        self.assertNotIn("GRAM", records[0][0])
        self.assertNotIn("BTC", records[0][0])

    def test_failed_sales_feed_has_no_fabricated_fallback(self):
        with patch.object(engine, "jget", return_value=None):
            self.assertEqual(engine.fragment(), [])

    def test_malformed_sale_date_does_not_crash_the_worker(self):
        record = {"username": "example", "price": 50, "currency": "TON", "status": "sold",
                  "sold_at": {}, "url": "https://fragment.com/username/example"}
        with patch.object(engine, "jget", return_value={"sales": [record]}):
            self.assertEqual(engine.fragment(), [])

    def test_revoked_tokens_are_not_left_in_the_speaker_rotation(self):
        with patch.object(engine, "tg", return_value={"ok": False, "error_code": 401}):
            engine.bootstrap_all()
        self.assertEqual(engine.TOK, {})

    def test_sales_require_explicit_currency_status_date_and_source(self):
        valid = {"username": "example", "price": 50, "currency": "TON", "status": "sold",
                 "sold_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                 "url": "https://fragment.com/username/example"}
        wrong_currency = dict(valid, currency="GRAM")
        undated = dict(valid)
        del undated["sold_at"]
        with patch.object(engine, "jget", return_value={"sales": [valid, wrong_currency, undated]}):
            records = engine.fragment()
        self.assertEqual(len(records), 1)
        self.assertIn("Reported username sale", records[0][0])

    def test_only_moving_stickers_and_cross_bot_unique_ids(self):
        outgoing = []
        def api(token, method, params=None):
            if method == "getStickerSet":
                return {"ok": True, "result": {"stickers": [
                    {"file_id": token + "-static", "file_unique_id": "static", "is_animated": False},
                    {"file_id": token + "-moving", "file_unique_id": "shared-moving", "is_animated": True}]}}
            if method == "sendSticker":
                outgoing.append(params["sticker"])
                return {"ok": True}
            return {"ok": False}
        with patch.object(engine, "PACKS", {"vader": "one-pack"}), patch.object(engine, "tg", side_effect=api):
            self.assertEqual(engine.sticker("yoda"), 1)
            self.assertEqual(engine.sticker("chucky"), 0)
        self.assertEqual(outgoing, ["yoda-token-moving"])
        self.assertIn("uid:shared-moving", engine.STATE["stickers"])

    def test_vader_has_the_largest_share_when_moving_assets_are_available(self):
        outgoing = []
        def api(token, method, params=None):
            if method == "getStickerSet":
                pack = params["name"]
                return {"ok": True, "result": {"stickers": [
                    {"file_id": "%s-%s" % (pack, i), "file_unique_id": "%s-%s" % (pack, i),
                     "is_video": True} for i in range(20)]}}
            outgoing.append(params["sticker"])
            return {"ok": True}
        with patch.object(engine, "PACKS", {"vader": "vader", "yoda": "yoda"}), \
             patch.object(engine, "tg", side_effect=api):
            for _ in range(10):
                engine.sticker("yoda")
        self.assertGreater(sum(item.startswith("vader") for item in outgoing),
                           sum(item.startswith("yoda") for item in outgoing))
        self.assertEqual(len(outgoing), len(set(outgoing)))

    def test_pin_ack_is_once_even_if_the_original_message_was_answered(self):
        calls = []
        engine.STATE["replies"]["123"] = time.time()
        def api(token, method, params=None):
            calls.append(method)
            if method == "getChat":
                return {"ok": True, "result": {"pinned_message": {"message_id": 123}}}
            if method == "sendMessage":
                return {"ok": True, "result": {"message_id": 999}}
            return {"ok": False}
        with patch.object(engine, "tg", side_effect=api):
            self.assertEqual(engine.react_to_pin(), 1)
            self.assertEqual(engine.react_to_pin(), 0)
        self.assertEqual(calls.count("sendMessage"), 1)
        self.assertNotIn("getChatPinnedMessage", calls)
        self.assertNotIn("setMessageReaction", calls)

    def test_checkpoint_preserves_both_ledgers_and_highest_offsets(self):
        remote = {"updated_at": 20, "used": {"remote": 5}, "offsets": {"brucewayne": 200},
                  "stickers": {"uid:remote": 6}, "sticker_counts": {"vader": 4}}
        local = {"updated_at": 10, "used": {"local": 8}, "offsets": {"brucewayne": 150},
                 "stickers": {"uid:local": 9}, "sticker_counts": {"vader": 3}}
        merged = merge_state(remote, local)
        self.assertEqual(set(merged["used"]), {"remote", "local"})
        self.assertEqual(set(merged["stickers"]), {"uid:remote", "uid:local"})
        self.assertEqual(merged["offsets"]["brucewayne"], 200)
        self.assertEqual(merged["sticker_counts"]["vader"], 4)
        self.assertEqual(merged["updated_at"], 20)

if __name__ == "__main__":
    unittest.main()
