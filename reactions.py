"""Conservative comment moods and reviewed, character-specific GIF metadata."""
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
MOODS = {"serious", "sad", "happy", "playful", "angry", "surprised",
         "frustrated", "disappointed", "curious", "supportive"}
try:
    CATALOG = json.loads((HERE / "stickers" / "moods.json").read_text())
except (OSError, ValueError):
    CATALOG = {}


def comment_mood(text, kind=None, content_key=None):
    """Use explicit cues; uncertain tone stays serious, never randomly cheerful.

    This is a small rule-based selector, not a claim to understand every emotion.
    Avoid reaction GIFs entirely for distressing real-world news.
    """
    if not text or not text.strip() or kind in ("service", "pin", "general"):
        return None
    line = text.splitlines()[0].casefold()
    if kind == "starwars" and content_key == "discussion:starwars:order66_loss":
        return "sad"
    loss = re.search(r"\b(sad|sadder|sadness|grief|grieving|heartbreak|heartbroken|cry|crying|tears|"
                     r"died|dying|funeral|killed|casualties|mourning|miss him|miss her|"
                     r"lost everything|lost someone|death(?! star))\b", line)
    if kind in ("world", "elon", "deals", "rap") and loss:
        return None
    if re.search(r"\b(not|isn't|isn’t|wasn't|wasn’t|never)\s+(sad|happy|funny|amused|excited)\b", line):
        return "serious"
    if loss or re.search(r"[😢😭💔]", line):
        return "sad"
    if content_key and any(content_key.startswith("roleplay:" + key + ":") for key in
                           ("dramatic_whisper", "hairbrush_transfer", "patience_contest", "ranking_spreadsheet",
                            "wookiee_alarm", "yoda_waiting_room")):
        return "playful"
    for mood, pattern in (
        ("frustrated", r"\b(frustrated|frustrating|annoyed|annoying|fed up)\b"),
        ("disappointed", r"\b(disappointed|disappointing|let down)\b"),
        ("angry", r"\b(angry|furious|outraged|rage)\b"),
        ("surprised", r"\b(surprised|shocked|stunned|didn't expect|didn’t expect)\b"),
        ("playful", r"\b(joke|joking|funny|laugh|laughing|haha|lol|teasing|hairbrush)\b|[😂🤣]"),
        ("happy", r"\b(happy|joy|joyful|celebrate|celebrating|congratulations|delighted)\b|[🥳🎉]"),
        ("supportive", r"\b(good luck|you've got this|you’ve got this|believe in you)\b"),
        ("curious", r"\b(curious|wondering|wonder why)\b"),
    ):
        if re.search(pattern, line):
            return mood
    return "serious"


def sticker_moods(character, pack, index):
    """Only known ordered packs have reviewed moods; unknown slots fail closed."""
    record = CATALOG.get(pack, {})
    entries = record.get("clips", [])
    if record.get("character") != character or not 0 <= index < len(entries):
        return set()
    return set(entries[index].get("moods", [])) & MOODS
