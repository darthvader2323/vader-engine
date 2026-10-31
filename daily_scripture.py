"""Validate the publisher's current KJV verse before preparing a daily post."""
import datetime as dt
import html
import re
from urllib.parse import parse_qs, urlsplit

FEED_URL = "https://www.biblegateway.com/votd/get/?format=json&version=KJV"
BOOKS = (
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalm", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Song of Songs", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
)
REFERENCE = re.compile(r"(?:" + "|".join(re.escape(book) for book in BOOKS)
                       + r") [1-9]\d{0,2}:[1-9]\d{0,2}(?:[-,] ?[1-9]\d{0,2}(?::[1-9]\d{0,2})?)*", re.I)


def verse_item(data, day):
    """Return exact plain scripture plus reference; malformed/stale feeds fail closed."""
    row = data.get("votd") if isinstance(data, dict) else None
    if not isinstance(row, dict) or row.get("version_id") != "KJV":
        return None
    try:
        published = dt.date(int(row["year"]), int(row["month"]), int(row["day"]))
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if published != day:
        return None
    text, reference, link = (row.get(field) for field in ("rawtext", "reference", "permalink"))
    if not all(isinstance(value, str) for value in (text, reference, link)):
        return None
    text = html.unescape(text)
    reference = html.unescape(reference).strip().replace("–", "-")
    if (not 4 <= len(text.strip()) <= 2000 or re.search(r"[<>\x00-\x08\x0b\x0c\x0e-\x1f]", text)
            or re.search(r"https?://|www\.|@[A-Za-z0-9_]", text) or not REFERENCE.fullmatch(reference)):
        return None
    try:
        source = urlsplit(html.unescape(link))
        query = parse_qs(source.query)
    except ValueError:
        return None
    normalize = lambda value: re.sub(r"\s+", "", value).casefold().replace("–", "-")
    if (source.scheme != "https" or source.hostname != "www.biblegateway.com" or source.path != "/passage/"
            or query.get("version") != ["KJV"] or len(query.get("search", [])) != 1
            or normalize(query["search"][0]) != normalize(reference)):
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return f'“{text}” — {reference} (KJV)', "scripture:kjv:" + normalize(reference)
