"""Future human greetings get one reply; replays and crowds are excluded."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import engine
from greetings import is_greeting
from checkpoint import merge_state


class GreetingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in {
            "S": Path(self.tmp.name), "STATE": engine.initial_state(), "CHAT": "-123",
            "TOK": {"brucewayne": "desk-token", "yoda": "yoda-token"},
            "CACHE": {}, "BACKOFF": {}, "BOT_USERS": {}, "LEGACY_STICKERS": set(),
        }.items():
            mock = patch.object(engine, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        for name, kwargs in (("log", {}), ("writing_style", {"return_value": "analytical"})):
            mock = patch.object(engine, name, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)
        self.clock = patch.object(engine.time, "time", return_value=1000)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        engine.STATE["greetings"]["enabled_at"] = 900
        engine.STATE["last_spoke"]["brucewayne"] = 990
        self.calls = []
        self.outcome = {"ok": True, "result": {"message_id": 800}}
        self.reaction = {"ok": True, "result": True}

    def message(self, mid=300, uid=1, text="what’s up!", date=1000):
        return {"update_id": mid, "message": {"message_id": mid, "date": date,
            "chat": {"id": -123}, "from": {"id": uid, "is_bot": False}, "text": text}}

    def api(self, updates):
        def call(token, method, params=None):
            self.calls.append((token, method, dict(params or {})))
            if method == "getUpdates":
                return {"ok": True, "result": [u for u in updates if u["update_id"] >= params.get("offset", 0)]}
            if method == "sendMessage":
                return self.outcome
            if method == "setMessageReaction":
                return self.reaction
            self.fail("Unexpected API call: " + method)
        return call

    def sent(self):
        return [call for call in self.calls if call[1] == "sendMessage"]

    def reacted(self):
        return [call for call in self.calls if call[1] == "setMessageReaction"]

    def test_greeting_parser_keeps_substantive_messages_out(self):
        for text in ("what’s up!", "hey everyone", "yo", "hello 👋", "/hello", "Yoda, hi!"):
            self.assertTrue(is_greeting(text, ["Yoda"]), text)
        for text in ("hi, how much for services?", "what's up with Bitcoin?", "I lost my account", "thanks", "👍"):
            self.assertFalse(is_greeting(text, ["Yoda"]), text)

    def test_one_native_character_reply_and_one_same_character_reaction(self):
        with patch.object(engine, "tg", side_effect=self.api([self.message()])):
            self.assertEqual(engine.answer_humans(), 1)
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(len(self.reacted()), 1)
        self.assertEqual(self.sent()[0][0], self.reacted()[0][0])
        self.assertEqual(self.sent()[0][2]["reply_parameters"], {"message_id": 300, "allow_sending_without_reply": False})
        self.assertNotIn("@", self.sent()[0][2]["text"])
        self.assertEqual(self.reacted()[0][2]["reaction"], [{"type": "emoji", "emoji": "👍"}])
        self.assertNotIn("help", engine.STATE["last_topic_at"])

    def test_direct_character_greeting_keeps_the_addressed_voice(self):
        with patch.object(engine, "tg", side_effect=self.api([self.message(text="Yoda, hello!")])):
            engine.answer_humans()
        self.assertEqual(self.sent()[0][0], "yoda-token")
        self.assertIn("you are", self.sent()[0][2]["text"])

    def test_replayed_update_and_new_update_for_same_message_do_not_repeat(self):
        update = self.message()
        with patch.object(engine, "tg", side_effect=self.api([update])):
            engine.answer_humans()
            engine.answer_humans()
        update["update_id"] = 400
        with patch.object(engine, "tg", side_effect=self.api([update])):
            engine.answer_humans()
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(len(self.reacted()), 1)

    def test_first_activation_does_not_backfill_older_greetings(self):
        engine.STATE["greetings"] = {}
        with patch.object(engine, "tg", side_effect=self.api([self.message(date=999)])):
            engine.answer_humans()
        self.assertEqual(engine.STATE["greetings"]["enabled_at"], 1000)
        self.assertFalse(self.sent())
        self.assertFalse(self.reacted())

    def test_bot_other_group_and_human_to_human_reply_are_ignored(self):
        bot = self.message(300)
        bot["message"]["from"]["is_bot"] = True
        other = self.message(301)
        other["message"]["chat"]["id"] = -999
        reply = self.message(302)
        reply["message"]["reply_to_message"] = {"from": {"id": 50, "is_bot": False}}
        with patch.object(engine, "tg", side_effect=self.api([bot, other, reply])):
            engine.answer_humans()
        self.assertFalse(self.sent())
        self.assertFalse(self.reacted())

    def test_service_request_stays_one_bruce_answer_without_greeting_reaction(self):
        with patch.object(engine, "tg", side_effect=self.api([self.message(text="Hi, who do I message for services?")])):
            engine.answer_humans()
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(self.sent()[0][0], "desk-token")
        self.assertIn("@darthvader", self.sent()[0][2]["text"])
        self.assertFalse(self.reacted())

    def test_per_person_and_room_cooldowns_avoid_welcome_floods(self):
        with patch.object(engine, "tg", side_effect=self.api([self.message()])):
            engine.answer_humans()
        with patch.object(engine.time, "time", return_value=1010), \
             patch.object(engine, "tg", side_effect=self.api([self.message(301, uid=2, date=1010)])):
            engine.answer_humans()
        with patch.object(engine.time, "time", return_value=1030), \
             patch.object(engine, "tg", side_effect=self.api([self.message(302, uid=1, date=1030)])):
            engine.answer_humans()
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(engine.STATE["offsets"]["brucewayne"], 303)

    def test_new_visitor_after_room_cooldown_gets_one_reply(self):
        with patch.object(engine, "tg", side_effect=self.api([self.message()])):
            engine.answer_humans()
        with patch.object(engine.time, "time", return_value=1030), \
             patch.object(engine, "tg", side_effect=self.api([self.message(301, uid=2, date=1030)])):
            engine.answer_humans()
        self.assertEqual(len(self.sent()), 2)
        self.assertEqual(len(self.reacted()), 2)
        self.assertNotEqual(self.sent()[0][2]["text"], self.sent()[1][2]["text"])

    def test_failed_text_stays_pending_without_reaction_or_cooldown(self):
        self.outcome = {"ok": False, "error_code": 403}
        with patch.object(engine, "tg", side_effect=self.api([self.message()])):
            self.assertEqual(engine.answer_humans(), 0)
        self.assertFalse(self.reacted())
        self.assertNotIn("brucewayne", engine.STATE["offsets"])
        self.assertNotIn("last", engine.STATE["greetings"])

    def test_uncertain_text_is_not_repeated_or_reacted_to(self):
        self.outcome = {"ok": False, "uncertain": True}
        with patch.object(engine, "tg", side_effect=self.api([self.message()])):
            engine.answer_humans()
            engine.answer_humans()
        self.assertEqual(len(self.sent()), 1)
        self.assertFalse(self.reacted())
        self.assertIn("300", engine.STATE["replies"])
        self.assertEqual(engine.STATE["greetings"]["count"], 1)

    def test_rejected_reaction_does_not_repeat_successful_reply(self):
        self.reaction = {"ok": False, "error_code": 400}
        with patch.object(engine, "tg", side_effect=self.api([self.message()])):
            engine.answer_humans()
            engine.answer_humans()
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(len(self.reacted()), 1)

    def test_restart_merge_preserves_activation_and_hashed_visitor_cooldown(self):
        with patch.object(engine, "tg", side_effect=self.api([self.message(uid=1234567)])):
            engine.answer_humans()
        merged = merge_state({"updated_at": 1100}, engine.STATE)
        self.assertEqual(merged["greetings"], engine.STATE["greetings"])
        self.assertNotIn("1234567", str(merged["greetings"]))
        self.assertIn("person:" + engine.digest("1234567"), merged["greetings"])


if __name__ == "__main__":
    unittest.main()
