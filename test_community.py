"""User-visible routing, delivery, data-quality and sticker behavior."""
import datetime as dt
import email.utils
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import engine
from conversation import compact_sources
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

    def test_legacy_token_alias_keeps_the_service_bots_identity(self):
        rows = [
            {"name": "darthvader", "env": "TG_VADER", "desks": ["general"]},
            {"name": "brucewayne", "env": "TG_JOHNNY", "desks": ["service"]},
            {"name": "yoda", "env": "TG_YODA", "desks": ["crypto"]},
        ]
        tokens = engine.configured_tokens(rows, {
            "TG_VADER": " same-token ", "TG_JOHNNY": "same-token", "TG_YODA": "yoda-token",
        }, {})
        self.assertEqual(tokens, {"brucewayne": "same-token", "yoda": "yoda-token"})

    def test_rate_limit_is_remembered_after_restart_without_storing_tokens(self):
        response = io.BytesIO(json.dumps({"ok": False, "error_code": 429,
            "description": "Too Many Requests: retry after 120", "parameters": {"retry_after": 120}}).encode())
        with patch.object(engine.urllib.request, "urlopen", return_value=response) as request:
            engine.tg("desk-token", "getMe")
            engine.BACKOFF.clear()
            engine.restore_backoff()
            engine.tg("desk-token", "getUpdates")
        self.assertEqual(request.call_count, 1)
        saved = (engine.S / "runtime.json").read_text()
        self.assertNotIn("desk-token", saved)
        self.assertGreater(engine.STATE["telegram_retry_until"]["brucewayne"], time.time())

    def test_failed_sticker_request_does_not_cache_a_pack_as_empty(self):
        responses = [{"ok": False, "error_code": 429}, {"ok": True, "result": {"stickers": [
            {"file_id": "moving", "file_unique_id": "unique", "is_video": True}]}}, {"ok": True}]
        with patch.object(engine, "PACKS", {"yoda": "one-pack"}), \
             patch.object(engine, "tg", side_effect=responses):
            self.assertEqual(engine.sticker("yoda"), 0)
            self.assertEqual(engine.sticker("yoda"), 1)

    def test_failed_avatar_does_not_repeat_successful_profile_writes(self):
        calls = []
        def api(token, method, params=None):
            calls.append(method)
            return {"ok": True, "result": {"id": 123, "is_bot": True, "username": "examplebot"}}
        now = time.time()
        with patch.object(engine, "TOK", {"brucewayne": "desk-token"}), \
             patch.object(engine, "tg", side_effect=api), \
             patch.object(engine, "set_photo", side_effect=[False, True]) as photo:
            with patch.object(engine.time, "time", return_value=now):
                engine.bootstrap_all()
            with patch.object(engine.time, "time", return_value=now + 3601):
                engine.bootstrap_all()
        self.assertEqual(calls.count("setMyName"), 1)
        self.assertEqual(calls.count("setMyDescription"), 1)
        self.assertEqual(photo.call_count, 2)

    def test_replayed_service_question_gets_one_designated_answer(self):
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api_for([self.message()], outgoing)):
            self.assertEqual(engine.answer_humans(), 1)
            self.assertEqual(engine.answer_humans(), 0)
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0][0], "desk-token")
        self.assertIn("@darthvader", outgoing[0][1]["text"])
        self.assertTrue(outgoing[0][1]["text"].startswith("For services,"))
        self.assertNotIn("[Bruce Wayne bot]", outgoing[0][1]["text"])
        self.assertIn("privately", outgoing[0][1]["text"])
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 101)

    def test_public_group_alias_resolves_to_incoming_update_id(self):
        with patch.dict(os.environ, {"CHAT_HANDLE": "@darthvaderchat2"}), \
             patch.object(engine, "tg", return_value={"ok": True, "result": {
                 "id": -1003758482841, "title": "Darth Vader Chat", "username": "darthvaderchat2"}}):
            engine.resolve_chat()
        self.assertEqual(engine.CHAT, "-1003758482841")

    def test_separate_listener_still_uses_one_service_responder(self):
        outgoing = []
        with patch.dict(os.environ, {"TG_READER_NAME": "yoda"}), \
             patch.object(engine, "tg", side_effect=self.api_for([self.message()], outgoing)):
            self.assertEqual(engine.answer_humans(), 1)
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0][0], "desk-token")
        self.assertEqual(engine.STATE["offsets"]["yoda"], 101)

    def test_new_listener_skips_backlog_without_replying(self):
        outgoing = []
        with patch.dict(os.environ, {"TG_READER_NAME": "yoda"}), \
             patch.object(engine, "tg", side_effect=self.api_for([self.message()], outgoing)):
            engine.prime_reader()
        self.assertEqual(outgoing, [])
        self.assertEqual(engine.STATE["offsets"]["yoda"], 101)

    def test_unavailable_identity_cannot_keep_winning_rotation(self):
        def identity(token, method, params=None):
            if token == "chucky-token":
                return {"ok": False, "uncertain": True}
            return {"ok": True, "result": {"is_bot": True, "username": "examplebot"}}
        with patch.object(engine, "tg", side_effect=identity):
            engine.verify_bots()
        self.assertNotIn("chucky", engine.TOK)
        self.assertIn(engine.choose_speaker(["chucky"]), ("brucewayne", "yoda"))

    def test_news_has_no_stock_introduction_and_keeps_a_clickable_source(self):
        outgoing = []
        report = "🚀 Acme opens a new research center\nExample Wire · Oct 30, 2026\nhttps://example.org/report"
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            engine.send("yoda", report, content_key="news:one", kind="world")
        payload = outgoing[0][1]
        self.assertEqual(payload["text"], report.rsplit("\n", 1)[0])
        entity = payload["entities"][0]
        self.assertEqual(entity["url"], "https://example.org/report")
        encoded = payload["text"].encode("utf-16-le")
        label = encoded[entity["offset"] * 2:(entity["offset"] + entity["length"]) * 2].decode("utf-16-le")
        self.assertEqual(label, "Example Wire · Oct 30, 2026")

    def test_addressed_yoda_uses_his_voice_but_service_goes_to_desk(self):
        self.assertEqual(engine.speaker_for("Yoda, who is the best Jedi?", "starwars"), "yoda")
        self.assertEqual(engine.speaker_for("Yoda, how much for account recovery?", "service"), "brucewayne")
        lines = engine.content_for("starwars", "yoda")
        self.assertTrue(any("Before a word, the music speaks" in text for text, _ in lines))

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
        self.assertEqual(engine.topic("Who should clients contact for services?"), "service")
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

    def test_shared_discussion_idea_cannot_be_repeated_by_another_character(self):
        outgoing = []
        text, key = next(item for item in engine.available_content("starwars", "yoda")
                         if item[1].endswith(":music"))
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            engine.send("yoda", text, content_key=key, kind="starwars")
        next_choices = engine.available_content("starwars", "chucky")
        self.assertNotIn(key, [key for _, key in next_choices])
        self.assertTrue(next_choices)

    def test_legacy_variations_mark_the_shared_idea_as_used(self):
        engine.STATE["used"][engine.digest(engine.STAR_WARS_BY_PERSONA["chewbacca"][0])] = time.time()
        choices = engine.available_content("starwars", "lukeskywalker")
        self.assertNotIn("discussion:starwars:loyalty", [key for _, key in choices])

    def test_near_duplicate_headline_is_blocked_across_speakers_and_topics(self):
        outgoing = []
        first = "Acme wins regulatory approval to buy Beta for $200 million\nWire · today\nhttps://example.org/one"
        second = "Regulatory approval for Acme to buy Beta for $200 million\nOther Wire · today\nhttps://example.org/two"
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            self.assertGreater(engine.send("yoda", first, content_key="one", kind="world"), 0)
            self.assertEqual(engine.send("chucky", second, content_key="two", kind="deals"), 0)
        self.assertEqual(len(outgoing), 1)
        saved = (engine.S / "runtime.json").read_text()
        self.assertNotIn("Acme", saved)
        self.assertIn("recent_content", saved)

    def test_changed_amount_and_negative_update_are_not_lost_as_duplicates(self):
        outgoing = []
        reports = ["Regulators approve Acme purchase of Beta for $200 million",
                   "Regulators approve Acme purchase of Beta for $300 million",
                   "Regulators do not approve Acme purchase of Beta for $200 million"]
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            for index, report in enumerate(reports):
                self.assertGreater(engine.send("yoda", report, content_key=str(index), kind="world"), 0)
        self.assertEqual(len(outgoing), 3)

    def test_failed_post_does_not_consume_the_idea_or_recent_signature(self):
        text = "Acme wins regulatory approval to buy Beta for $200 million"
        with patch.object(engine, "tg", return_value={"ok": False, "error_code": 403}):
            self.assertEqual(engine.send("yoda", text, content_key="one", kind="world"), 0)
        self.assertNotIn(engine.digest("one"), engine.STATE["used"])
        self.assertEqual(engine.STATE["recent_content"], {})
        with patch.object(engine, "tg", return_value={"ok": True, "result": {"message_id": 9}}):
            self.assertEqual(engine.send("yoda", text, content_key="one", kind="world"), 9)

    def test_uncertain_discussion_reply_cannot_be_replayed_by_another_character(self):
        text, key = next(item for item in engine.available_content("starwars", "yoda")
                         if item[1].endswith(":music"))
        other = next(text for text, other_key in engine.content_for("starwars", "chucky") if other_key == key)
        with patch.object(engine, "tg", return_value={"ok": False, "uncertain": True}) as api:
            self.assertEqual(engine.send("yoda", text, reply=1, content_key=key, kind="starwars"), -1)
            self.assertEqual(engine.send("chucky", other, reply=2, content_key=key, kind="starwars"), 0)
        self.assertEqual(api.call_count, 1)

    def test_empty_news_is_acknowledged_without_a_fallback_post(self):
        outgoing = []
        update = self.message(text="Any new NBA YoungBoy news?")
        with patch.object(engine, "youngboy", return_value=[]), \
             patch.object(engine, "tg", side_effect=self.api_for([update], outgoing)):
            self.assertEqual(engine.answer_humans(), 0)
        self.assertEqual(outgoing, [])
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 101)

    def test_general_question_does_not_trigger_the_same_help_pitch(self):
        outgoing = []
        with patch.object(engine, "tg", side_effect=self.api_for(
                [self.message(text="How is everyone?")], outgoing)):
            self.assertEqual(engine.answer_humans(), 0)
        self.assertEqual(outgoing, [])
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 101)

    def test_scheduled_rap_has_no_scripted_opinion_fallback(self):
        with patch.object(engine, "youngboy", return_value=[]):
            self.assertEqual(engine.content_for("rap", "chucky", scheduled=True), [])
            self.assertTrue(engine.content_for("rap", "chucky"))

    def test_scheduled_post_waits_while_people_are_talking(self):
        engine.STATE["last_topic_at"]["human_activity"] = time.time()
        with patch.object(engine, "available_content") as provider:
            self.assertEqual(engine.beat(), 0)
        provider.assert_not_called()

    def test_broadcast_speaker_rotation_is_shared_across_topics(self):
        outgoing = []
        engine.STATE["cursor"] = 2
        engine.STATE["last_spoke"] = {"yoda": 200, "brucewayne": 300, "chucky": 100}
        with patch.object(engine, "available_content", return_value=[("NBA scheduled fixture", "fixture:1")]), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.random, "random", return_value=1):
            self.assertGreater(engine.beat(), 0)
        self.assertEqual(outgoing[0][0], "chucky-token")

    def test_topic_cooldown_moves_on_instead_of_posting_another_similar_prompt(self):
        outgoing = []
        engine.STATE["last_topic_at"]["starwars"] = time.time()
        engine.STATE["last_topic_at"]["crypto"] = time.time()
        with patch.object(engine, "available_content", return_value=[("NBA fixture", "fixture:2")]) as provider, \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.random, "random", return_value=1):
            self.assertGreater(engine.beat(), 0)
        self.assertEqual(provider.call_args.args[0], "sports")

    def test_recent_fingerprints_survive_checkpoint_merges(self):
        remote = {"updated_at": 3, "recent_content": {"a": {"at": 1, "signature": {}}, "b": {"at": 3, "signature": {}}}}
        local = {"updated_at": 2, "recent_content": {"a": {"at": 2, "signature": {}}, "c": {"at": 2, "signature": {}}}}
        merged = merge_state(remote, local)
        self.assertEqual(set(merged["recent_content"]), {"a", "b", "c"})
        self.assertEqual(merged["recent_content"]["a"]["at"], 2)

    def test_compact_source_link_preserves_fragment_username_and_context(self):
        text = "Reported username sale: @example · 100 TON\nOct 30, 2026\nhttps://fragment.com/username/example\nSale details above."
        body, entities = compact_sources(text, "fragment")
        self.assertIn("@example · 100 TON", body)
        self.assertIn("Sale details above.", body)
        self.assertEqual(entities[0]["url"], "https://fragment.com/username/example")

    def test_topic_filters_reject_irrelevant_headlines_and_aggregate_deal_reports(self):
        with patch.object(engine, "gnews", return_value=[
                ("Celebrity welcomes a child", "unrelated"),
                ("NBA YoungBoy releases a new album", "youngboy")]):
            self.assertEqual([key for _, key in engine.youngboy()], ["youngboy"])
        with patch.object(engine, "gnews", return_value=[
                ("Mergers and acquisitions move $70 billion through September", "aggregate"),
                ("Acme buys Beta for $200 million", "deal")]):
            self.assertEqual([key for _, key in engine.deals()], ["deal"])
        with patch.object(engine, "gnews", return_value=[
                ("Unrelated market update", "unrelated"),
                ("SpaceX announces a mission", "space")]):
            self.assertEqual([key for _, key in engine.elon()], ["space"])

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
        with patch.object(engine, "PACKS", {"yoda": "yoda-pack", "chucky": "chucky-pack"}), \
             patch.object(engine, "tg", side_effect=api):
            self.assertEqual(engine.sticker("yoda"), 1)
            self.assertEqual(engine.sticker("chucky"), 0)
        self.assertEqual(outgoing, ["yoda-token-moving"])
        self.assertIn("uid:shared-moving", engine.STATE["stickers"])

    def test_speaker_only_sends_its_own_character_even_with_other_assets_available(self):
        outgoing = []
        looked_up = []
        def api(token, method, params=None):
            if method == "getStickerSet":
                pack = params["name"]
                looked_up.append(pack)
                return {"ok": True, "result": {"stickers": [
                    {"file_id": "%s-%s" % (pack, i), "file_unique_id": "%s-%s" % (pack, i),
                     "is_video": True} for i in range(20)]}}
            outgoing.append(params["sticker"])
            return {"ok": True}
        with patch.object(engine, "PACKS", {"vader": "vader", "yoda": "yoda"}), \
             patch.object(engine, "tg", side_effect=api):
            for _ in range(10):
                engine.sticker("yoda")
        self.assertEqual(looked_up, ["yoda"])
        self.assertEqual(len(outgoing), 10)
        self.assertTrue(all(item.startswith("yoda-") for item in outgoing))
        self.assertEqual(len(outgoing), len(set(outgoing)))

    def test_exhausted_matching_pack_does_not_fall_back_to_another_character(self):
        engine.STATE["stickers"]["uid:already-used"] = time.time()
        with patch.object(engine, "PACKS", {"yoda": "yoda-pack", "vader": "vader-pack"}), \
             patch.object(engine, "tg", return_value={"ok": True, "result": {"stickers": [
                 {"file_id": "yoda-file", "file_unique_id": "already-used", "is_video": True}]}}) as api:
            self.assertEqual(engine.sticker("yoda"), 0)
        api.assert_called_once_with("yoda-token", "getStickerSet", {"name": "yoda-pack"})

    def test_missing_matching_pack_never_uses_a_legacy_unrelated_pack(self):
        with patch.object(engine, "PACKS", {"han": "han-pack", "vader": "vader-pack"}), \
             patch.object(engine, "tg") as api:
            self.assertEqual(engine.sticker("brucewayne"), 0)
        api.assert_not_called()

    def test_display_name_aliases_route_to_the_correct_character_pack(self):
        cases = [("chewbacca", "chew"), ("lukeskywalker", "luke"),
                 ("darthvader", "vader"), ("brucewayne", "batman"),
                 ("chucky", "chucky"), ("nbayoungboy", "youngboy")]
        for who, character in cases:
            with self.subTest(who=who), \
                 patch.object(engine, "TOK", {who: "character-token"}), \
                 patch.object(engine, "PACKS", {character: character + "-pack"}), \
                 patch.object(engine, "tg", return_value={"ok": True, "result": {"stickers": []}}) as api:
                self.assertEqual(engine.sticker(who), 0)
                api.assert_called_once_with("character-token", "getStickerSet", {"name": character + "-pack"})

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
