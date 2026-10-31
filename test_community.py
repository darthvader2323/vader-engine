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
from conversation import DISCUSSIONS, ROLEPLAY_THREADS, compact_sources
from checkpoint import merge_state
from writing_styles import daily_styles, render_style, PLAIN_DISCUSSIONS, PLAIN_THREADS

class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for name, value in {
            "S": Path(self.directory.name),
            "CHAT": "-123456",
            "STATE": engine.initial_state(),
            "TOK": {"brucewayne": "desk-token", "yoda": "yoda-token", "chucky": "chucky-token"},
            "CACHE": {}, "BACKOFF": {}, "LEGACY_STICKERS": set(), "BOT_USERS": {},
            "ROLEPLAY_THREADS": (),
        }.items():
            replacement = patch.object(engine, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        quiet = patch.object(engine, "log")
        quiet.start()
        self.addCleanup(quiet.stop)
        # Existing behavior checks are independent of the calendar's style group.
        tone = patch.object(engine, "writing_style", return_value="analytical")
        tone.start()
        self.addCleanup(tone.stop)
        # These existing routing/format tests isolate the new optional GIF step;
        # reaction integration and real catalog order are covered separately.
        self.reaction_step = patch.object(engine, "maybe_sticker", return_value=0)
        self.reaction_step.start()
        self.addCleanup(self.reaction_step.stop)
        moods = patch.object(engine, "sticker_moods", return_value={"serious"})
        moods.start()
        self.addCleanup(moods.stop)

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

    def managed_api(self, calls, privacy=True, photo=True, status="member", manager=True, identity=4242):
        def api(token, method, params=None):
            calls.append((token, method, params))
            if method == "getMe" and token == "desk-token":
                return {"ok": True, "result": {"id": 90, "is_bot": True, "can_manage_bots": manager}}
            if method == "getManagedBotToken":
                return {"ok": True, "result": "4242:" + "x" * 25}
            if method == "getMe":
                return {"ok": True, "result": {"id": identity, "is_bot": True,
                    "username": "exampletonybot", "can_read_all_group_messages": privacy}}
            if method == "getUserProfilePhotos":
                return {"ok": True, "result": {"total_count": int(photo)}}
            if method == "getChatMember":
                return {"ok": True, "result": {"status": status, "user": {"id": 4242}}}
            raise AssertionError("Unexpected operation: " + method)
        return api

    def test_managed_profile_connects_without_persisting_or_logging_its_token(self):
        calls = []
        child = "4242:" + "x" * 25
        with patch.dict(os.environ, {"MANAGED_BOTS_JSON": '{"tonysoprano":4242}'}), \
             patch.object(engine, "tg", side_effect=self.managed_api(calls)):
            self.assertEqual(engine.load_managed_bots(), 1)
        self.assertEqual(engine.TOK["tonysoprano"], child)
        self.assertIn(("desk-token", "getManagedBotToken", {"user_id": 4242}), calls)
        self.assertIn((child, "getChatMember", {"chat_id": "-123456", "user_id": 4242}), calls)
        engine.persist()
        self.assertNotIn(child, (engine.S / "runtime.json").read_text())
        self.assertNotIn(child, str(engine.log.call_args_list))

    def test_incomplete_managed_profiles_cannot_enter_group_rotation(self):
        for options in ({"privacy": False}, {"photo": False}, {"status": "left"},
                        {"status": "kicked"}, {"manager": False}, {"identity": 5555}):
            with self.subTest(options=options), \
                 patch.dict(os.environ, {"MANAGED_BOTS_JSON": '{"tonysoprano":4242}'}), \
                 patch.object(engine, "tg", side_effect=self.managed_api([], **options)):
                self.assertEqual(engine.load_managed_bots(), 0)
                self.assertNotIn("tonysoprano", engine.TOK)

    def test_managed_metadata_setup_can_prepare_a_profile_before_group_join(self):
        calls = []
        with patch.dict(os.environ, {"MANAGED_BOTS_JSON": '{"tonysoprano":4242}'}), \
             patch.object(engine, "tg", side_effect=self.managed_api(calls, privacy=False, photo=False, status="left")):
            self.assertEqual(engine.load_managed_bots(for_profile_setup=True), 1)
        self.assertNotIn("getChatMember", [method for _, method, _ in calls])
        self.assertNotIn("sendMessage", [method for _, method, _ in calls])

    def test_managed_configuration_cannot_override_an_existing_identity(self):
        with patch.dict(os.environ, {"MANAGED_BOTS_JSON": '{"yoda":4242}'}), \
             patch.object(engine, "tg") as api:
            self.assertEqual(engine.load_managed_bots(), 0)
        api.assert_not_called()
        self.assertEqual(engine.TOK["yoda"], "yoda-token")

    def test_managed_configuration_rejects_invalid_and_duplicate_ids(self):
        for raw in ('[]', '{"unknown":123}', '{"tonysoprano":true}', '{"tonysoprano":0}',
                    '{"tonysoprano":42.5}', '{"tonysoprano":"private-token"}',
                    '{"tonysoprano":123,"johnwick":123}', 'not-json'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                engine.managed_bot_config(raw)
        self.assertEqual(engine.managed_bot_config('{"tonysoprano":"4242"}'), {"tonysoprano": 4242})

    def test_managed_profile_respects_saved_cooldown_before_token_lookup(self):
        engine.STATE["telegram_retry_until"]["tonysoprano"] = time.time() + 120
        calls = []
        with patch.dict(os.environ, {"MANAGED_BOTS_JSON": '{"tonysoprano":4242}'}), \
             patch.object(engine, "tg", side_effect=self.managed_api(calls)):
            self.assertEqual(engine.load_managed_bots(), 0)
        self.assertNotIn("getManagedBotToken", [method for _, method, _ in calls])

    def test_missing_character_picture_does_not_report_success(self):
        with patch.object(engine, "HERE", engine.S), \
             patch.object(engine.urllib.request, "urlopen") as request:
            self.assertFalse(engine.set_photo("tonysoprano", "unused-token"))
        request.assert_not_called()

    def test_existing_character_avatar_filename_aliases_upload_the_matching_file(self):
        folder = engine.S / "avatars"
        folder.mkdir()
        for name, filename in (("brucewayne", "johnny"), ("chewbacca", "chew"), ("lukeskywalker", "luke")):
            (folder / (filename + ".jpg")).write_bytes(("picture-" + filename).encode())
            with self.subTest(name=name), patch.object(engine, "HERE", engine.S), \
                 patch.object(engine.urllib.request, "urlopen", return_value=io.BytesIO(b'{"ok":true}')) as request:
                self.assertTrue(engine.set_photo(name, "unused-token"))
                self.assertIn(("picture-" + filename).encode(), request.call_args.args[0].data)

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
            self.assertEqual(engine.sticker("yoda", "A quiet moment."), 0)
            self.assertEqual(engine.sticker("yoda", "A quiet moment."), 1)

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

    def test_style_change_cannot_replay_an_already_used_discussion(self):
        outgoing = []
        key = "discussion:starwars:suit_life_support"
        text = next(text for text, item in engine.content_for("starwars", "yoda") if item == key)
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            with patch.object(engine, "writing_style", return_value="plain"):
                self.assertGreater(engine.send("yoda", text, content_key=key, kind="starwars"), 0)
            restored = merge_state({}, json.loads((engine.S / "runtime.json").read_text()))
            with patch.object(engine, "STATE", restored), \
                 patch.object(engine, "writing_style", return_value="analytical"):
                self.assertEqual(engine.send("yoda", text, content_key=key, kind="starwars"), 0)
        self.assertEqual(len(outgoing), 1)
        self.assertIn("Alive, the suit keeps Vader", outgoing[0][1]["text"])

    def test_plain_native_reply_preserves_price_and_occasional_link_entity_offsets(self):
        outgoing = []
        report = "Bitcoin report: approximately $200 million\nExample Wire · Oct 31, 2026\nhttps://example.org/report"
        with patch.object(engine, "writing_style", return_value="plain"), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            engine.send("yoda", report, reply=300, content_key="news:plain", kind="world")
            engine.STATE["scheduled_news_count"] = 9
            engine.send("chucky", report.replace("$200", "$300"), content_key="news:linked", kind="world")
        reply = outgoing[0][1]
        self.assertIn("about $200 million", reply["text"])
        self.assertEqual(reply["reply_parameters"]["message_id"], 300)
        self.assertNotIn("entities", reply)
        linked = outgoing[1][1]
        entity = linked["entities"][0]
        encoded = linked["text"].encode("utf-16-le")
        self.assertEqual(encoded[2*entity["offset"]:2*(entity["offset"]+entity["length"])].decode("utf-16-le"),
                         "More here")
        self.assertIn("about $300 million", linked["text"])
        self.assertNotIn("Example Wire", linked["text"])
        self.assertNotIn("Oct 31", linked["text"])
        self.assertEqual(entity["url"], "https://example.org/report")

    def test_news_has_no_stock_introduction_or_clickable_source(self):
        outgoing = []
        report = "🚀 Acme opens a new research center\nExample Wire · Oct 30, 2026\nhttps://example.org/report"
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            engine.send("yoda", report, content_key="news:one", kind="world")
        payload = outgoing[0][1]
        self.assertEqual(payload["text"], report.splitlines()[0])
        self.assertNotIn("entities", payload)
        self.assertNotIn("Example Wire", payload["text"])
        self.assertNotIn("Oct 30", payload["text"])
        self.assertNotIn("https://", payload["text"])

    def test_addressed_yoda_uses_his_voice_but_service_goes_to_desk(self):
        self.assertEqual(engine.speaker_for("Yoda, who is the best Jedi?", "starwars"), "yoda")
        self.assertEqual(engine.speaker_for("Yoda, how much for account recovery?", "service"), "brucewayne")
        lines = engine.content_for("starwars", "yoda")
        self.assertTrue(any("Before a word, the music speaks" in text for text, _ in lines))

    def test_discussion_ideas_and_character_wording_are_not_duplicated(self):
        keys = [idea for idea, _ in DISCUSSIONS]
        self.assertEqual(len(keys), len(set(keys)))
        wording = [engine.digest(text) for _, voices in DISCUSSIONS for text in voices.values()]
        self.assertEqual(len(wording), len(set(wording)))

    def test_specific_new_lore_questions_do_not_get_an_unrelated_generic_reply(self):
        for question, expected in (
            ("Yoda, why does Vader need life support?", "suit_life_support"),
            ("Who built C-3PO?", "threepio_builder"),
            ("Yoda, what about the Falcon hyperdrive?", "falcon_hyperdrive"),
        ):
            with self.subTest(question=question):
                self.assertEqual(engine.topic(question), "starwars")
                choices = engine.available_content("starwars", "yoda", question=question)
                self.assertEqual([key for _, key in choices], ["discussion:starwars:" + expected])

    def test_fragment_sale_question_can_mention_a_character_username(self):
        self.assertEqual(engine.topic("Who bought @yoda on Fragment?"), "fragment")

    def test_tony_has_authored_reading_styles_without_new_history_keys(self):
        from tony_voice import DISCUSSIONS as tony
        self.assertEqual(set(tony), {idea for idea, _ in DISCUSSIONS})
        for idea, voices in DISCUSSIONS:
            key = "discussion:starwars:" + idea
            analytical = voices["tonysoprano"]
            plain = render_style(analytical, "starwars", key, "tonysoprano", "plain")
            self.assertEqual((analytical, plain), tony[idea])
            self.assertNotEqual(analytical, plain)
            engine.STATE["used"][engine.digest(key)] = time.time()
        self.assertEqual(engine.available_content("starwars", "tonysoprano"), [])
        with patch.dict(engine.TOK, {"tonysoprano": "tony-token"}):
            self.assertEqual(engine.speaker_for("Tony Soprano, fresh crypto?", "crypto"), "tonysoprano")
            self.assertEqual(engine.topic("Tony Soprano, fresh crypto?"), "crypto")
            self.assertEqual(engine.speaker_for("Tony Soprano, who do I message for services?", "service"), "brucewayne")

    def test_starwars_can_resume_after_its_shorter_topic_cooldown(self):
        now = time.time()
        for kind in ("starwars", "crypto", "sports", "world", "elon", "deals", "rap", "fragment"):
            engine.STATE["last_topic_at"][kind] = now
        engine.STATE["last_topic_at"]["starwars"] = now - 901
        with patch.object(engine, "available_content", return_value=[("An unused observation.", "new-idea")]), \
             patch.object(engine, "send", return_value=1) as send, \
             patch.object(engine, "sticker"):
            self.assertEqual(engine.beat(), 1)
        self.assertEqual(send.call_args.kwargs["kind"], "starwars")

    def test_cadence_update_does_not_keep_the_previous_long_wait(self):
        now = time.time()
        engine.STATE["next_beat"] = now + 800
        engine.STATE["last_spoke"]["yoda"] = now - 1000
        with patch.dict(os.environ, {"VADER_ONCE": "1", "GAP_MIN": "180", "GAP_MAX": "360"}), \
             patch.object(engine.time, "time", return_value=now), \
             patch.object(engine.signal, "signal"), \
             patch.object(engine, "verify_bots"), patch.object(engine, "resolve_chat"), \
             patch.object(engine, "load_managed_bots"), patch.object(engine, "bootstrap_all"), \
             patch.object(engine, "prime_reader"), patch.object(engine, "answer_humans"), \
             patch.object(engine, "react_to_pin"), patch.object(engine, "sticker"), \
             patch.object(engine, "beat", return_value=1) as beat:
            engine.main()
        beat.assert_called_once()
        self.assertGreaterEqual(engine.STATE["next_beat"], now + 180)
        self.assertLessEqual(engine.STATE["next_beat"], now + 360)

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

    def test_broadcast_speaker_varies_among_quieter_profiles_across_topics(self):
        outgoing = []
        engine.STATE["cursor"] = 2
        engine.STATE["last_spoke"] = {"yoda": 200, "brucewayne": 300, "chucky": 100}
        with patch.object(engine, "available_content", return_value=[("NBA scheduled fixture", "fixture:1")]), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.random, "random", return_value=1):
            self.assertGreater(engine.beat(), 0)
        self.assertIn(outgoing[0][0], ("chucky-token", "yoda-token"))

    def test_topic_cooldown_moves_on_instead_of_posting_another_similar_prompt(self):
        outgoing = []
        engine.STATE["last_topic_at"]["starwars"] = time.time()
        engine.STATE["last_topic_at"]["crypto"] = time.time()
        def content(kind, *args, **kwargs):
            return [("NBA fixture", "fixture:2")] if kind == "sports" else []
        with patch.object(engine, "available_content", side_effect=content) as provider, \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.random, "random", return_value=1):
            self.assertGreater(engine.beat(), 0)
        self.assertEqual(provider.call_args.args[0], "sports")
        self.assertTrue(all(call.args[0] not in ("starwars", "crypto") for call in provider.call_args_list))

    def test_recent_fingerprints_survive_checkpoint_merges(self):
        remote = {"updated_at": 3, "recent_content": {"a": {"at": 1, "signature": {}}, "b": {"at": 3, "signature": {}}}}
        local = {"updated_at": 2, "recent_content": {"a": {"at": 2, "signature": {}}, "c": {"at": 2, "signature": {}}}}
        merged = merge_state(remote, local)
        self.assertEqual(set(merged["recent_content"]), {"a", "b", "c"})
        self.assertEqual(merged["recent_content"]["a"]["at"], 2)

    def test_link_removal_preserves_fragment_username_and_context(self):
        text = "Reported username sale: @example · 100 TON\nOct 30, 2026\nhttps://fragment.com/username/example\nSale details above."
        body, entities = compact_sources(text, "fragment")
        self.assertIn("@example · 100 TON", body)
        self.assertIn("Sale details above.", body)
        self.assertEqual(entities, [])
        self.assertNotIn("https://", body)

    def test_all_routine_news_topics_remove_multiple_and_inline_urls(self):
        report = ("Acme buys Beta for $200 million https://example.org/deal\n"
                  "Example Wire · Oct 30, 2026\nhttps://example.org/report\n"
                  "More at www.example.org. Contact @darthvader.")
        for kind in ("world", "elon", "deals", "rap", "crypto", "sports", "fragment"):
            with self.subTest(kind=kind):
                body, entities = compact_sources(report, kind)
                self.assertEqual(entities, [])
                self.assertNotRegex(body, r"https?://|www\.")
                self.assertIn("$200 million", body)
                self.assertNotIn("Example Wire", body)
                self.assertNotIn("Oct 30", body)
                self.assertIn("@darthvader", body)

    def test_bare_source_hostnames_do_not_auto_link(self):
        body, entities = compact_sources("Headline\nfeeds.bbci.co.uk · Oct 30, 2026\nhttps://www.bbc.co.uk/news", "world")
        self.assertEqual(body, "Headline")
        self.assertEqual(entities, [])

    def test_occasional_short_source_handles_emoji_and_publisher_labels(self):
        body, entities = compact_sources("🚀 New mission\nfeeds.bbci.co.uk · Oct 30, 2026\nhttps://www.bbc.co.uk/news", "world", include_link=True)
        self.assertNotIn("https://", body)
        entity = entities[0]
        encoded = body.encode("utf-16-le")
        label = encoded[2 * entity["offset"]:2 * (entity["offset"] + entity["length"])].decode("utf-16-le")
        self.assertEqual(label, "More here")
        self.assertNotIn("BBC News", body)
        self.assertEqual(entity["url"], "https://www.bbc.co.uk/news")

    def test_links_are_sparse_and_share_one_groupwide_cooldown(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.time, "time", side_effect=lambda: now):
            for index in range(30):
                if index == 20:
                    now += 3601
                report = f"Market sample {index}\nExample Wire · Oct 30, 2026\nhttps://example.org/{index}"
                engine.send("yoda" if index % 2 else "chucky", report,
                            content_key=f"market:{index}", kind="crypto")
        linked = [i for i, (_, payload) in enumerate(outgoing) if payload.get("entities")]
        self.assertEqual(linked, [9, 29])
        self.assertTrue(all("https://" not in p["text"] for _, p in outgoing))

    def test_casual_format_keeps_fixture_times_price_windows_and_dates_in_the_story(self):
        stories = (
            ("sports", "NBA scheduled: Team A at Team B · Tonight 7 PM ET"),
            ("crypto", "BTC is down 1.50% over 24 hours."),
            ("world", "The deadline is Nov 5, 2026, not today."),
        )
        for kind, story in stories:
            raw = story + "\nExample Wire · Oct 31, 01:10 AM CDT\nhttps://example.org/report"
            self.assertEqual(compact_sources(raw, kind), (story, []))
        sale = "Reported username sale: @example · 100 TON\nOct 30, 01:10 PM CDT\nhttps://fragment.com/username/example"
        self.assertEqual(compact_sources(sale, "fragment"), (sale.splitlines()[0], []))

    def test_known_source_metadata_remains_available_before_chat_rendering(self):
        now = int(time.time())
        quote = {"bitcoin": {"usd": 12, "usd_24h_change": -1, "last_updated_at": now}}
        with patch.object(engine, "jget", return_value=quote):
            raw, key = engine.crypto()[0]
        self.assertIn("CoinGecko", raw)
        self.assertIn("https://www.coingecko.com/", raw)
        body, _ = compact_sources(render_style(raw, "crypto", key, "yoda", "plain"), "crypto")
        self.assertIn("$12.00", body)
        self.assertRegex(body, r"(?:down 1\.00%|1\.00% lower)")
        self.assertNotIn("CoinGecko", body)

    def test_exhausted_sticker_cache_can_see_new_clips_without_resetting_history(self):
        engine.ROSTER["yoda"]["persona"] = "yoda"
        old = {"file_id": "old-file", "file_unique_id": "old-uid", "is_video": True}
        fresh = {"file_id": "new-file", "file_unique_id": "new-uid", "is_video": True}
        engine.STATE["stickers"]["uid:old-uid"] = time.time()
        with patch.object(engine, "PACKS", {"yoda": "matching-pack"}):
            engine.CACHE["stickers:yoda:matching-pack"] = (time.time()+3600, [old])
            self.assertEqual(engine.sticker("yoda", "A quiet moment."), 0)
            def api(token, method, params):
                if method == "getStickerSet":
                    return {"ok": True, "result": {"stickers": [old, fresh]}}
                self.assertEqual(params["sticker"], "new-file")
                return {"ok": True, "result": {"message_id": 900}}
            with patch.object(engine, "tg", side_effect=api):
                self.assertEqual(engine.sticker("yoda", "A quiet moment."), 1)
        self.assertIn("uid:old-uid", engine.STATE["stickers"])
        self.assertIn("uid:new-uid", engine.STATE["stickers"])

    def test_replies_do_not_consume_the_occasional_link_slot(self):
        outgoing = []
        engine.STATE["scheduled_news_count"] = 9
        report = "Market sample\nExample Wire · Oct 30, 2026\nhttps://example.org/report"
        with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            engine.send("yoda", report, reply=300, kind="crypto")
        self.assertNotIn("entities", outgoing[0][1])
        self.assertEqual(engine.STATE["scheduled_news_count"], 9)

    def test_failed_delivery_preserves_the_link_slot(self):
        engine.STATE["scheduled_news_count"] = 9
        report = "Market sample\nExample Wire · Oct 30, 2026\nhttps://example.org/report"
        with patch.object(engine, "tg", return_value={"ok": False, "error_code": 400}):
            engine.send("yoda", report, kind="crypto")
        self.assertEqual(engine.STATE["scheduled_news_count"], 9)
        self.assertNotIn("source_link", engine.STATE["last_topic_at"])

    def test_link_frequency_survives_checkpoint_merges(self):
        merged = merge_state({"updated_at": 4, "scheduled_news_count": 9,
                              "last_topic_at": {"source_link": 100}},
                             {"updated_at": 3, "scheduled_news_count": 12,
                              "last_topic_at": {"source_link": 200}})
        self.assertEqual(merged["scheduled_news_count"], 12)
        self.assertEqual(merged["last_topic_at"]["source_link"], 200)

    def test_roleplay_has_one_delayed_native_reply_from_a_different_character(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.time, "time", side_effect=lambda: now), \
             patch.object(engine.random, "uniform", return_value=60):
            seed = engine.start_roleplay()
            self.assertGreater(seed, 0)
            self.assertEqual(engine.continue_roleplay(), 0)
            now += 61
            self.assertGreater(engine.continue_roleplay(), 0)
            self.assertEqual(engine.continue_roleplay(), 0)
            self.assertIsNone(engine.start_roleplay())
        self.assertEqual(len(outgoing), 2)
        self.assertNotEqual(outgoing[0][0], outgoing[1][0])
        self.assertEqual(outgoing[1][1]["reply_parameters"]["message_id"], seed)
        self.assertIsNone(engine.STATE["roleplay_pending"])
        self.assertGreater(engine.STATE["next_beat"], now)

    def test_roleplay_waits_for_real_visitors(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.time, "time", side_effect=lambda: now):
            engine.start_roleplay()
            now += 121
            engine.STATE["last_topic_at"]["human_activity"] = now
            self.assertEqual(engine.continue_roleplay(), 0)
            self.assertEqual(engine.beat(), 0)
            self.assertEqual(len(outgoing), 1)
            now += 91
            self.assertGreater(engine.continue_roleplay(), 0)

    def test_rejected_character_reply_cannot_block_broadcasts_forever(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine.time, "time", side_effect=lambda: now):
            with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
                engine.start_roleplay()
            now += 121
            with patch.object(engine, "tg", return_value={"ok": False, "error_code": 400}) as api:
                for _ in range(3):
                    self.assertEqual(engine.continue_roleplay(), 0)
                    now += 61
                self.assertIsNone(engine.STATE["roleplay_pending"])
                self.assertEqual(engine.continue_roleplay(), 0)
                self.assertEqual(api.call_count, 3)
            self.assertIsNone(engine.start_roleplay())

    def test_expired_roleplay_is_skipped_even_while_people_keep_talking(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine.time, "time", side_effect=lambda: now), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
            engine.start_roleplay()
            now += 601
            engine.STATE["last_topic_at"]["human_activity"] = now
            self.assertEqual(engine.continue_roleplay(), 0)
        self.assertIsNone(engine.STATE["roleplay_pending"])
        self.assertEqual(len(outgoing), 1)

    def test_reply_attempt_limit_and_expiry_survive_a_checkpoint(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine.time, "time", side_effect=lambda: now):
            with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
                engine.start_roleplay()
            now += 121
            with patch.object(engine, "tg", return_value={"ok": False, "error_code": 400}):
                engine.continue_roleplay()
            restored = merge_state({}, json.loads((engine.S / "runtime.json").read_text()))
            self.assertEqual(restored["roleplay_pending"]["attempts"], 1)
            expiry = restored["roleplay_pending"]["expires"]
            with patch.object(engine, "STATE", restored):
                now = expiry + 1
                with patch.object(engine, "tg") as api:
                    engine.continue_roleplay()
                    api.assert_not_called()
                self.assertIsNone(engine.STATE["roleplay_pending"])

    def test_roleplay_resumes_its_pending_reply_after_checkpoint(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing)), \
             patch.object(engine.time, "time", side_effect=lambda: now):
            seed = engine.start_roleplay()
            restored = merge_state({}, json.loads((engine.S / "runtime.json").read_text()))
            now += 121
            with patch.object(engine, "STATE", restored):
                self.assertGreater(engine.continue_roleplay(), 0)
        self.assertEqual(len(outgoing), 2)
        self.assertEqual(outgoing[1][1]["reply_parameters"]["message_id"], seed)

    def test_uncertain_roleplay_seed_never_creates_a_blind_followup(self):
        outgoing = []
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine, "tg", side_effect=self.api_for([], outgoing, {"ok": False, "uncertain": True})):
            self.assertEqual(engine.start_roleplay(), -1)
            self.assertIsNone(engine.STATE["roleplay_pending"])
            self.assertEqual(engine.continue_roleplay(), 0)
            self.assertIsNone(engine.start_roleplay())
        self.assertEqual(len(outgoing), 1)

    def test_uncertain_roleplay_reply_cannot_repeat_after_a_crash(self):
        outgoing = []
        now = 2_000_000_000
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine.time, "time", side_effect=lambda: now):
            with patch.object(engine, "tg", side_effect=self.api_for([], outgoing)):
                engine.start_roleplay()
            pending = dict(engine.STATE["roleplay_pending"])
            now += 121
            with patch.object(engine, "tg", side_effect=self.api_for([], outgoing, {"ok": False, "uncertain": True})):
                self.assertEqual(engine.continue_roleplay(), -1)
                engine.STATE["roleplay_pending"] = pending
                self.assertEqual(engine.continue_roleplay(), 0)
        self.assertEqual(len(outgoing), 2)
        self.assertIsNone(engine.STATE["roleplay_pending"])

    def test_roleplay_requires_its_actual_characters_and_has_distinct_wording(self):
        bodies = [text for _, turns in ROLEPLAY_THREADS for _, text in turns]
        self.assertEqual(len(bodies), len(set(bodies)))
        self.assertTrue(all(len({who for who, _ in turns}) == 2 for _, turns in ROLEPLAY_THREADS))
        with patch.object(engine, "ROLEPLAY_THREADS", ROLEPLAY_THREADS[:1]), \
             patch.object(engine, "TOK", {"chucky": "character-token"}), \
             patch.object(engine, "tg") as api:
            self.assertIsNone(engine.start_roleplay())
        api.assert_not_called()

    def test_changed_crypto_figures_can_answer_a_request_in_the_same_hour(self):
        outgoing = []
        data = {"bitcoin": {"usd": 11, "usd_24h_change": 1, "last_updated_at": int(time.time())}}
        request = self.message(text="Yoda, any fresh crypto figures?", username="darthvader")
        with patch.object(engine, "jget", return_value=data), \
             patch.object(engine, "tg", side_effect=self.api_for([request], outgoing)):
            first, key = engine.crypto()[0]
            engine.send("yoda", first, content_key=key, kind="crypto")
            data["bitcoin"]["usd"] = 12
            self.assertEqual(engine.answer_humans(), 1)
        self.assertEqual(len(outgoing), 2)
        self.assertIn("$12.00", outgoing[1][1]["text"])
        self.assertEqual(outgoing[1][1]["reply_parameters"]["message_id"], 300)

    def test_character_address_does_not_override_the_requested_topic(self):
        for text, expected in [
                ("Yoda, any fresh crypto figures?", "crypto"),
                ("Chewbacca, any fresh crypto numbers?", "crypto"),
                ("Yoda, what's happening in the NBA?", "sports"),
                ("Yoda, news about Elon Musk?", "elon"),
                ("Chewbacca, who bought a company today? Any business deals?", "deals"),
                ("Yoda, what's in the world news?", "world"),
                ("Yoda, how much for Instagram verification?", "service"),
                ("Yoda, why is patience important for a Jedi?", "starwars"),
                ("Yoda species?", "starwars")]:
            with self.subTest(text=text):
                self.assertEqual(engine.topic(text), expected)

    def test_unchanged_crypto_figures_keep_their_shared_key(self):
        data = {"bitcoin": {"usd": 11, "usd_24h_change": 1, "last_updated_at": int(time.time())}}
        with patch.object(engine, "jget", return_value=data):
            _, before = engine.crypto()[0]
            data["bitcoin"]["last_updated_at"] += 30
            _, after = engine.crypto()[0]
        self.assertEqual(before, after)

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
            self.assertEqual(engine.sticker("yoda", "A quiet moment."), 1)
            self.assertEqual(engine.sticker("chucky", "A quiet moment."), 0)
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
                engine.sticker("yoda", "A quiet moment.")
        self.assertEqual(looked_up, ["yoda"])
        self.assertEqual(len(outgoing), 10)
        self.assertTrue(all(item.startswith("yoda-") for item in outgoing))
        self.assertEqual(len(outgoing), len(set(outgoing)))

    def test_exhausted_matching_pack_does_not_fall_back_to_another_character(self):
        engine.STATE["stickers"]["uid:already-used"] = time.time()
        with patch.object(engine, "PACKS", {"yoda": "yoda-pack", "vader": "vader-pack"}), \
             patch.object(engine, "tg", return_value={"ok": True, "result": {"stickers": [
                 {"file_id": "yoda-file", "file_unique_id": "already-used", "is_video": True}]}}) as api:
            self.assertEqual(engine.sticker("yoda", "A quiet moment."), 0)
        api.assert_called_once_with("yoda-token", "getStickerSet", {"name": "yoda-pack"})

    def test_missing_matching_pack_never_uses_a_legacy_unrelated_pack(self):
        with patch.object(engine, "PACKS", {"han": "han-pack", "vader": "vader-pack"}), \
             patch.object(engine, "tg") as api:
            self.assertEqual(engine.sticker("brucewayne", "A quiet moment."), 0)
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
                self.assertEqual(engine.sticker(who, "A quiet moment."), 0)
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

class WritingStyleTests(unittest.TestCase):
    def test_daily_split_is_balanced_swaps_and_is_stable_across_restarts(self):
        today = dt.date(2026, 10, 31)
        for count in (1, 2, 5, 24, 29, 100):
            names = [f"profile{n}" for n in range(count)]
            first = daily_styles(names, today)
            self.assertEqual(first, daily_styles(reversed(names), today))
            self.assertLessEqual(abs(list(first.values()).count("plain") - count / 2), 0.5)
            next_day = daily_styles(names, today + dt.timedelta(days=1))
            self.assertTrue(all(first[name] != next_day[name] for name in names))

    def test_worker_uses_local_midnight_and_swaps_during_a_running_process(self):
        names = {"brucewayne": "a", "yoda": "b", "chucky": "c"}
        before = dt.datetime(2026, 10, 31, 4, 59, tzinfo=dt.timezone.utc).timestamp()
        after = before + 120
        with patch.object(engine, "TOK", names), \
             patch.object(engine, "ZONE", engine.ZoneInfo("America/Chicago")):
            with patch.object(engine.time, "time", return_value=before):
                old = {name: engine.writing_style(name) for name in names}
            with patch.object(engine.time, "time", return_value=after):
                new = {name: engine.writing_style(name) for name in names}
        self.assertTrue(all(old[name] != new[name] for name in names))

    def test_every_existing_authored_idea_and_thread_has_plain_wording(self):
        self.assertEqual(set(PLAIN_DISCUSSIONS), {key for key, _ in DISCUSSIONS})
        self.assertEqual(set(PLAIN_THREADS), {key for key, _ in ROLEPLAY_THREADS})
        for key, voices in DISCUSSIONS:
            for name in ("brucewayne", "yoda", "chewbacca", "lukeskywalker", "chucky"):
                text = render_style(voices[name], "starwars", "discussion:starwars:" + key, name, "plain")
                self.assertTrue(text)
                self.assertNotIn("fifth grade", text.casefold())
        for key, turns in ROLEPLAY_THREADS:
            for index, (name, text) in enumerate(turns):
                self.assertTrue(render_style(text, "starwars", f"roleplay:{key}:{index}", name, "plain"))

    def test_plain_crypto_preserves_exact_prices_signs_source_and_date(self):
        raw = ("TON $1.19 · 24h +0.68%\nBTC $77,083.00 · 24h -1.50%\n"
               "ETH $2,236.18 · 24h +0.00%\nCoinGecko · Oct 31, 12:00 AM CDT\nhttps://www.coingecko.com/")
        text = render_style(raw, "crypto", "quote:1", "yoda", "plain")
        self.assertIn("$1.19", text)
        self.assertIn("Up 0.68%", text)
        self.assertIn("$77,083.00", text)
        self.assertIn("down 1.50%", text)
        self.assertIn("$2,236.18", text)
        self.assertIn("unchanged over 24 hours (0.00%)", text)
        self.assertEqual(text.splitlines()[-2:], raw.splitlines()[-2:])
        advanced = render_style(raw, "crypto", "quote:1", "yoda", "analytical")
        for fact in ("$1.19", "$77,083.00", "$2,236.18", "0.68%", "1.50%", "0.00%"):
            self.assertIn(fact, advanced)
        self.assertEqual(advanced.splitlines()[-2:], raw.splitlines()[-2:])

    def test_casual_business_headline_preserves_future_status_and_proper_names(self):
        raw = "First Community Bancshares to Acquire Main Street Financial Services for $243 Million"
        for style in ("plain", "analytical"):
            body = render_style(raw, "deals", "headline:one", "chewbacca", style)
            self.assertEqual(body, "First Community Bancshares plans to buy Main Street Financial Services for $243 million.")
        for headline in ("Acme may not acquire Beta", "Acme denies plans to acquire Beta", "'Acme to Acquire Beta' is an unconfirmed rumor"):
            body = render_style(headline, "deals", "headline:two", "brucewayne", "analytical")
            self.assertEqual(body, headline)

    def test_plain_headline_does_not_turn_plans_or_allegations_into_facts(self):
        raw = ("Acme reportedly plans to acquire Beta for approximately $200 million, but may not proceed\n"
               "Example Wire · Oct 31, 2026\nhttps://example.org/deal\nContact @darthvader.")
        text = render_style(raw, "deals", "news:one", "chucky", "plain")
        self.assertEqual(text.splitlines()[0],
                         "Acme reportedly plans to buy Beta for about $200 million, but may not proceed")
        self.assertEqual(text.splitlines()[1:], raw.splitlines()[1:])
        claim = "Police concluded the alleged deal could not proceed"
        self.assertEqual(render_style(claim, "world", "n:2", "yoda", "plain"), claim)

    def test_quoted_source_wording_and_capitalized_names_are_not_rewritten(self):
        for quote in ('"approximately additional assistance"', '“approximately additional assistance”',
                      "‘approximately additional assistance’", "'approximately additional assistance'"):
            raw = "Company says " + quote + " is needed"
            self.assertEqual(render_style(raw, "world", "n:one", "yoda", "plain"), raw)
        name = "The Additional Assistance Fund plans a vote"
        self.assertEqual(render_style(name, "world", "n:two", "yoda", "plain"), name)

    def test_service_pins_scores_and_unknown_ideas_keep_their_exact_meaning(self):
        for kind, key, text in (
            ("service", "service", "For services, message @darthvader privately with your request."),
            ("pin", "pin", "Pinned message acknowledged by the automated assistant."),
            ("sports", "sports:one", "NBA Final: Team A 100–99 Team B · Final\nESPN · checked Oct 31"),
            ("fragment", "fragment:one", "Reported sale: @example · 100 TON · Oct 31"),
            ("starwars", "roleplay:unknown", "An unfamiliar authored idea."),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(render_style(text, kind, key, "yoda", "plain"), text)


if __name__ == "__main__":
    unittest.main()
