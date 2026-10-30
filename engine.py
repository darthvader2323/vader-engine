#!/usr/bin/env python3
"""Disclosed character bots and sourced updates for Darth Vader Chat."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
from pathlib import Path
import random
import re
import signal
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from conversation import (SIMILARITY_KINDS, compact_sources, discussion_items,
                          signature, similar)

HERE = Path(__file__).resolve().parent
S = Path(os.environ.get("VADER_STATE_DIR", HERE / "state"))
CHAT = os.environ.get("CHAT_ID", "").strip()
HANDLE = "@darthvader"
SITE = "https://vader-social-ppulq7yo.agent.mira.tg"
ZONE = ZoneInfo(os.environ.get("VADER_TIMEZONE", "America/Chicago"))
LOCK = threading.RLock()
STOP = threading.Event()
CACHE = {}
BACKOFF = {}
PROFILE_VERSION = "disclosed-characters-1"
USER_AGENT = "VaderSocialCharacterBot/1.0"
LEAGUES = [
    ("basketball/nba", "NBA"), ("hockey/nhl", "NHL"),
    ("baseball/mlb", "MLB"), ("football/nfl", "NFL"),
    ("soccer/usa.1", "MLS"), ("soccer/eng.1", "Premier League"),
    ("soccer/uefa.champions", "Champions League"),
    ("basketball/wnba", "WNBA"),
]
PACKS = {
    "vader": "ComeToTheDarkSide", "grogu": "BabyYoda",
    "yoda": "JediMasterYoda", "luke": "sry4d8ta1gu6s_by_mira",
    "chew": "ChewbaccaWookiee", "han": "sroftq1uflv8l_by_mira",
    "boba": "sryfojcw0mm1l_by_mira", "leia": "PrincessLeiaOrgana",
    "r2d2": "st6ibqn4fjj0a_by_mira", "crew": "StarWarsSagaByDarthAdmiraL",
}
for _character, _env in [("chucky", "CHUCKY_STICKER_PACK"),
                         ("youngboy", "YOUNGBOY_STICKER_PACK")]:
    if os.environ.get(_env):
        PACKS[_character] = os.environ[_env]
try:
    PACKS.update(json.loads(os.environ.get("STICKER_PACKS_JSON", "{}")))
except (ValueError, TypeError):
    pass

STAR_WARS = [
    "Vader's redemption in Return of the Jedi is my scripted character pick: Luke reaches the Anakin beneath the armor. What scene makes your case?",
    "Character debate: Vader's breathing does more to establish a presence than a long speech. Who has a stronger entrance?",
    "Yoda's character case: wisdom matters more than size. Does that put him ahead of Vader for you?",
    "Luke's character case: refusing to give up on his father is his strongest decision. Which moment would you choose?",
    "Chewbacca's character case: loyalty is the argument. Pick one scene that shows why he belongs in the top spot.",
    "Vader was once Anakin Skywalker, a Jedi. That fall and eventual return give his story its weight. Is that your strongest character arc?",
    "Darth Vader's armor and mechanical breathing make him instantly recognizable. Which Star Wars design comes closest?",
    "Fan debate: Leia's leadership, Han's nerve, Luke's hope, or Vader's redemption? Give the reason behind your choice.",
    "Vader's connection to Luke turns a conflict about power into a family story. Which reveal changes the saga most for you?",
    "Character discussion: a red lightsaber, a black helmet, and a pause before speaking. What makes Vader so effective on screen?",
    "Yoda and Vader make a good contrast: patience against intimidation. Which kind of presence carries a scene for you?",
    "Chewbacca and Han work as a team because their loyalty feels earned. Which Star Wars partnership is your favorite?",
]
RAP = [
    "Scripted fan take: NBA YoungBoy belongs in the GOAT conversation for emotional delivery. Which track would you use to make that argument?",
    "Rap debate: is YoungBoy's strongest quality the melody, storytelling, or intensity? Choose one and explain.",
    "YoungBoy fan discussion: older songs or newer releases? Name a track so the argument has something concrete behind it.",
    "Scripted fan opinion: YoungBoy's range is a stronger GOAT argument than a popularity contest. What is your counterexample?",
    "NBA YoungBoy debate: does replay value matter more than chart performance when you rank a rapper?",
    "Pick a YoungBoy song that shows both vulnerability and energy. What detail in the performance stands out?",
    "Fan question: when you call a rapper the greatest, are you judging lyrics, delivery, influence, or the full catalog?",
    "YoungBoy is the focus of this fan discussion. Which performance would you show somebody hearing him for the first time?",
]
STAR_WARS_BY_PERSONA = {
    "yoda": [
        "Judge by size, do not. A choice in darkness reveals more than strength. Between Vader and Luke, who made the greater choice?",
        "Much power, Vader had. Yet reach Anakin, Luke could. Stronger than fear, compassion proved. Your favorite moment, which is it?",
        "Loyal, Chewbacca remains. Overlook that strength, we should not. A better companion in the saga, can you name?",
        "A grand entrance, Vader makes. Wisdom in a quiet moment, I prefer. Which carries a scene for you, hmm?",
    ],
    "lukeskywalker": [
        "I won’t write Vader off. Choosing his son over the Emperor is what makes the ending matter to me. What moment changes your view of him?",
        "The strongest move isn’t always another swing of a lightsaber. Luke refusing to give up on his father is my pick. What’s yours?",
        "Yoda has the wisdom; Vader has the presence. I’m backing the choice to keep hoping when the odds look terrible. Who gets your vote?",
        "Chewie deserves more credit. Loyalty holds that whole team together. Which partnership in Star Wars beats Han and Chewbacca?",
    ],
    "chewbacca": [
        "Rrrraaagh! Loyalty gets my vote. Han and Chewie keep showing up for each other—who’s your pick for the best team?",
        "Rrrroww! Vader has the entrance, but Chewie has your back. Which matters more when you’re choosing a favorite character?",
        "Wrrraaagh! Luke seeing the good in Vader is a strong case. Give me one scene that puts your favorite ahead.",
        "Rrraawh! A helmet and a cape get attention. Loyalty earns it. Best Star Wars companion—who are you picking?",
    ],
    "brucewayne": [
        "Vader wins on presence; Luke wins on restraint. I’d judge them by the choice they make when power is on the table. Who makes the better one?",
        "The armor is memorable. The decision beneath it is more interesting. Which Vader scene tells you the most about the character?",
        "Yoda understands discipline. Vader understands fear. Those are very different kinds of power. Which makes the stronger character?",
    ],
    "chucky": [
        "Big cape, dramatic entrance—Vader knows how to steal a room. Yoda’s tiny and still runs the debate. Which one gets your vote?",
        "Oh, that’s a fun argument. Vader barely has to move to own a scene. Who else in Star Wars can pull that off?",
        "You’re all sleeping on Chewie. The loudest guy in the room is also the most loyal. Give me a better sidekick—go on.",
    ],
    "darthvader": [
        "Power earns fear. Redemption earns a different kind of legacy. Which is the stronger reason to put Vader first?",
        "An entrance can silence a room. A choice can change the saga. Which Vader moment carries more weight for you?",
        "Luke saw Anakin where others saw only Vader. Was that hope the strongest force in the ending? Make your case.",
    ],
}
def load(name, default):
    try:
        return json.loads((S / name).read_text())
    except (OSError, ValueError):
        return default

def initial_state():
    return {"version": 1, "used": {}, "replies": {}, "stickers": {},
            "pins": {}, "profiles": {}, "offsets": {}, "last_spoke": {},
            "last_topic_at": {}, "telegram_retry_until": {}, "profile_retry_until": {},
            "recent_content": {},
            "next_beat": 0, "cursor": 0, "updated_at": 0}

STATE = initial_state()
_saved = load("runtime.json", {})
if isinstance(_saved, dict):
    STATE.update(_saved)
for _key in ("used", "replies", "stickers", "pins", "profiles", "offsets",
             "last_spoke", "last_topic_at", "telegram_retry_until", "profile_retry_until", "recent_content"):
    if not isinstance(STATE.get(_key), dict):
        STATE[_key] = {}
LEGACY_STICKERS = set(load("stk_used.json", []))
_old_offsets = load("offsets.json", {})
if isinstance(_old_offsets, dict) and _old_offsets.get("main"):
    STATE["offsets"].setdefault("main", _old_offsets["main"])

def persist():
    with LOCK:
        S.mkdir(parents=True, exist_ok=True)
        STATE["updated_at"] = time.time()
        tmp = S / "runtime.json.tmp"
        tmp.write_text(json.dumps(STATE, sort_keys=True, indent=2))
        tmp.replace(S / "runtime.json")

def digest(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().casefold().encode()).hexdigest()

def migrate_discussion_history():
    """Recognize old variations as the same idea during a release handover."""
    rows = list(zip(STAR_WARS, ["redemption", "presence", "wisdom", "redemption",
        "loyalty", "redemption", "presence", "presence", "redemption", "presence", "wisdom", "loyalty"]))
    old_topics = {
        "yoda": ["redemption", "redemption", "loyalty", "wisdom"],
        "lukeskywalker": ["redemption", "redemption", "redemption", "loyalty"],
        "chewbacca": ["loyalty", "presence", "redemption", "loyalty"],
        "brucewayne": ["redemption", "presence", "wisdom"],
        "chucky": ["presence", "presence", "loyalty"],
        "darthvader": ["redemption", "presence", "redemption"],
    }
    for who, ideas in old_topics.items():
        rows.extend(zip(STAR_WARS_BY_PERSONA[who], ideas))
    for text, idea in rows:
        stamp = STATE["used"].get(digest(text))
        if stamp is not None:
            STATE["used"].setdefault(digest("discussion:starwars:" + idea), stamp)
    for text, idea in zip(RAP, ["delivery", "delivery", "catalog", "catalog",
                              "ranking", "delivery", "ranking", "catalog"]):
        stamp = STATE["used"].get(digest(text))
        if stamp is not None:
            STATE["used"].setdefault(digest("discussion:rap:" + idea), stamp)

def repeated_content(text, key, kind):
    if digest(key or text) in STATE["used"] or digest(text) in STATE["used"]:
        return True
    if kind not in SIMILARITY_KINDS:
        return False
    candidate = signature(text)
    now = time.time()
    for record in STATE["recent_content"].values():
        if (isinstance(record, dict) and now - record.get("at", 0) < 48 * 3600
                and similar(candidate, record.get("signature", {}))):
            return True
    return False

def remember_content(key, text, kind):
    if kind not in SIMILARITY_KINDS:
        return
    now = time.time()
    history = STATE["recent_content"]
    history[key] = {"at": now, "signature": signature(text), "kind": kind}
    keep = sorted((name for name, record in history.items()
                   if isinstance(record, dict) and now - record.get("at", 0) < 48 * 3600),
                  key=lambda name: history[name]["at"], reverse=True)[:100]
    STATE["recent_content"] = {name: history[name] for name in keep}

def log(message):
    for token in TOK.values():
        if token:
            message = message.replace(token, "[token]")
    print(message, flush=True)

with (HERE / "roster.json").open() as _file:
    ROSTER_LIST = json.load(_file)
ROSTER = {row["name"]: row for row in ROSTER_LIST}
try:
    _extra_tokens = json.loads(os.environ.get("BOT_TOKENS_JSON", "{}"))
except ValueError:
    _extra_tokens = {}
if not isinstance(_extra_tokens, dict):
    _extra_tokens = {}
def configured_tokens(rows, environ, extras):
    """Keep the service identity when legacy secrets alias the same bot."""
    result = {}
    for row in sorted(rows, key=lambda item: "service" not in item.get("desks", [])):
        env = row.get("env", "")
        token = environ.get(env) or extras.get(env) or extras.get(row["name"])
        if isinstance(token, str) and token.strip():
            token = token.strip()
            if token not in result.values():
                result[row["name"]] = token
    return result

TOK = configured_tokens(ROSTER_LIST, os.environ, _extra_tokens)
ALL = list(TOK)
BOT_USERS = {}

def restore_backoff():
    for name, until in STATE.get("telegram_retry_until", {}).items():
        if name in TOK:
            BACKOFF[TOK[name]] = max(BACKOFF.get(TOK[name], 0), until)

restore_backoff()

def remember_rate_limit(token, method, result):
    if result.get("error_code") != 429:
        return
    retry = max(1, int((result.get("parameters") or {}).get("retry_after") or 60))
    until = time.time() + retry
    BACKOFF[token] = until
    name = next((name for name, value in TOK.items() if value == token), "unknown")
    STATE["telegram_retry_until"][name] = until
    persist()
    log("API RATE LIMIT bot=%s method=%s retry_after=%ss description=%s" %
        (name, method, retry, str(result.get("description", ""))[:250]))

def tg(token, method, params=None):
    if not token:
        return {"ok": False, "error_code": 401}
    if BACKOFF.get(token, 0) > time.time():
        return {"ok": False, "error_code": 429, "cached_rate_limit": True}
    request = urllib.request.Request(
        "https://api.telegram.org/bot%s/%s" % (token, method),
        data=json.dumps(params or {}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            result = json.loads(error.read())
        except (ValueError, OSError):
            result = {"ok": False, "error_code": error.code}
    except (OSError, ValueError):
        # A timed-out send may already have arrived. Do not blindly send it again.
        return {"ok": False, "uncertain": True}
    remember_rate_limit(token, method, result)
    return result

def resolve_chat():
    """Resolve the public group to the ID actually used by incoming updates."""
    global CHAT
    reference = os.environ.get("CHAT_HANDLE", "").strip() or CHAT
    reader = TOK.get("brucewayne") or next(iter(TOK.values()), None)
    result = tg(reader, "getChat", {"chat_id": reference})
    chat = result.get("result") or {}
    if not result.get("ok") or chat.get("title") != "Darth Vader Chat":
        raise SystemExit("Cannot verify access to the authorized Darth Vader Chat")
    if reference.startswith("@") and chat.get("username", "").casefold() != reference[1:].casefold():
        raise SystemExit("Public group username did not match the authorized destination")
    resolved = str(chat.get("id", ""))
    if not re.fullmatch(r"-\d+", resolved):
        raise SystemExit("Authorized destination did not resolve to a group ID")
    CHAT = resolved
    log("GROUP VERIFIED: Darth Vader Chat; canonical ID resolved")

def verify_bots():
    """Exclude an unavailable identity for this run instead of selecting it forever."""
    for name, token in list(TOK.items()):
        result = tg(token, "getMe")
        user = result.get("result") or {}
        if not result.get("ok") or not user.get("is_bot"):
            TOK.pop(name, None)
            log("IDENTITY UNAVAILABLE %s; skipped for this run" % name)
        else:
            BOT_USERS[name] = user.get("username", "")
    if not TOK:
        raise SystemExit("No responsive configured character accounts")

def polling_reader():
    requested = os.environ.get("TG_READER_NAME", "").strip()
    if requested:
        if requested not in TOK:
            raise SystemExit("Configured message listener is unavailable")
        return requested
    return "brucewayne" if "brucewayne" in TOK else next(iter(TOK), None)

def prime_reader():
    """A newly selected listener starts with new messages, without flooding old chat."""
    reader = polling_reader()
    if not reader or reader in STATE["offsets"]:
        return
    if reader == "brucewayne" and STATE["offsets"].get("main"):
        return
    result = tg(TOK[reader], "getUpdates", {"timeout": 0, "limit": 100})
    if not result.get("ok"):
        raise SystemExit("Cannot initialize the incoming message listener")
    updates = result.get("result") or []
    STATE["offsets"][reader] = max((u.get("update_id", 0) + 1 for u in updates), default=0)
    persist()
    log("LISTENER READY %s; existing backlog skipped" % reader)

def get_url(url, ttl=300):
    now = time.time()
    cached = CACHE.get(url)
    if cached and cached[0] > now:
        return cached[1]
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
        CACHE[url] = (now + ttl, raw)
        return raw
    except OSError:
        CACHE[url] = (now + 60, b"")
        return b""

def jget(url):
    try:
        result = json.loads(get_url(url))
        return result if isinstance(result, dict) else None
    except (ValueError, TypeError, AttributeError):
        return None

def stamp(timestamp=None):
    return dt.datetime.fromtimestamp(timestamp or time.time(), ZONE).strftime("%b %d, %I:%M %p %Z")

def pick(pool):
    candidates = [text for text in pool if text and digest(text) not in STATE["used"]]
    return random.choice(candidates) if candidates else None

def choose_speaker(preferred=None):
    candidates = [name for name in (preferred or list(TOK)) if name in TOK]
    if not candidates:
        candidates = list(TOK)
    if not candidates:
        return None
    # Fair rotation limits repeated appearances; it does not conceal automation.
    oldest = min(STATE["last_spoke"].get(name, 0) for name in candidates)
    return random.choice([name for name in candidates
                          if STATE["last_spoke"].get(name, 0) == oldest])

def send(who, text, reply=None, content_key=None, kind=None):
    if who not in TOK or not text:
        return 0
    key = digest(content_key or text)
    reply_key = (("pin:" if kind == "pin" or content_key == "pin" else "") + str(reply)) if reply is not None else None
    if reply_key and reply_key in STATE["replies"]:
        return 0
    if not reply_key and key in STATE["used"]:
        return 0
    if kind in SIMILARITY_KINDS | {"crypto", "sports"} and repeated_content(text, content_key, kind):
        return 0
    # Claim before sending: a process interruption or unknown API result must not
    # cause a wave of repeated replies on restart.
    claim_used = not reply_key or kind in SIMILARITY_KINDS | {"crypto", "sports"}
    previous_used = STATE["used"].get(key)
    previous_recent = STATE["recent_content"].get(key)
    if reply_key:
        STATE["replies"][reply_key] = time.time()
    if claim_used:
        STATE["used"][key] = time.time()
    remember_content(key, text, kind)
    persist()
    # Telegram account status and the profile disclose automation; avoid a
    # repetitive identity banner in every message body.
    body, entities = compact_sources(text, kind)
    params = {"chat_id": CHAT, "text": body,
              "link_preview_options": {"is_disabled": True}}
    if entities:
        params["entities"] = entities
    if reply_key:
        params["reply_parameters"] = {"message_id": int(reply),
                                      "allow_sending_without_reply": False}
    result = tg(TOK[who], "sendMessage", params)
    if result.get("ok") or result.get("uncertain"):
        if result.get("ok"):
            STATE["used"][digest(text)] = time.time()
        STATE["last_spoke"][who] = time.time()
        if kind and kind not in ("service", "pin", "general"):
            STATE["last_topic_at"][kind] = time.time()
        persist()
        if result.get("ok"):
            log("SENT %s%s" % (who, " reply" if reply_key else " scheduled"))
            return result["result"]["message_id"]
        log("DELIVERY UNKNOWN %s; no automatic duplicate send" % who)
        return -1
    if reply_key:
        STATE["replies"].pop(reply_key, None)
    if claim_used:
        if previous_used is None:
            STATE["used"].pop(key, None)
        else:
            STATE["used"][key] = previous_used
    if previous_recent is None:
        STATE["recent_content"].pop(key, None)
    else:
        STATE["recent_content"][key] = previous_recent
    persist()
    if not result.get("cached_rate_limit"):
        log("SEND FAILED %s code=%s" % (who, result.get("error_code", "unknown")))
    return 0

def _date(value):
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(value, dt.timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed
    except (ValueError, TypeError, AttributeError):
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return None

def rss(url, days=3):
    raw = get_url(url)
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    output = []
    now = dt.datetime.now(dt.timezone.utc)
    for item in root.findall(".//item"):
        title = html.unescape(item.findtext("title", "")).strip()
        link = item.findtext("link", "").strip()
        published = _date(item.findtext("pubDate", ""))
        if not title or not link.startswith("https://") or not published:
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=dt.timezone.utc)
        age = (now - published).total_seconds()
        if age < -300 or age > days * 86400:
            continue
        source = item.findtext("source", urllib.parse.urlparse(url).hostname or "")
        # Preserve the previous headline key when handing over from older releases.
        if digest("headline:" + title) in STATE["used"]:
            continue
        if source and title.endswith(" - " + source):
            title = title[:-(len(source) + 3)]
        text = "%s\n%s · %s\n%s" % (title, source, stamp(published.timestamp()), link)
        output.append((text, "headline:" + title))
    return output

def gnews(query, days=3):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query + " when:%dd" % days, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return rss(url, days)

def world():
    return rss("https://feeds.bbci.co.uk/news/world/rss.xml")

def elon():
    return [(text, key) for text, key in gnews('"Elon Musk" OR SpaceX OR xAI OR Tesla')
            if re.search(r"\b(elon musk|spacex|xai|tesla|grok|starlink)\b", text.splitlines()[0], re.I)]

def deals():
    return [(text, key) for text, key in gnews('company acquisition merger "$" million billion', 7)
            if re.search(r"\b(acquires?|acquired|acquisition of|buys?|bought|takeover|merges? with|sells?|sold|stake|buyout)\b",
                         text.splitlines()[0], re.I)
            and re.search(r"\b(million|billion)\b|\$[\d.,]+\s?[MB]\b", text.splitlines()[0], re.I)]

def youngboy():
    return [(text, key) for text, key in gnews('"NBA YoungBoy" OR "YoungBoy Never Broke Again"', 7)
            if re.search(r"\b(nba youngboy|youngboy never broke again|youngboy|yb)\b", text.splitlines()[0], re.I)]

def crypto():
    url = ("https://api.coingecko.com/api/v3/simple/price?"
           "ids=the-open-network,bitcoin,ethereum&vs_currencies=usd"
           "&include_24hr_change=true&include_last_updated_at=true")
    data = jget(url) or {}
    lines = []
    times = []
    for coin, symbol in [("the-open-network", "TON"), ("bitcoin", "BTC"), ("ethereum", "ETH")]:
        quote = data.get(coin) or {}
        updated = quote.get("last_updated_at", 0)
        if not isinstance(updated, (int, float)) or time.time() - updated > 900:
            continue
        price = quote.get("usd")
        change = quote.get("usd_24h_change")
        if not isinstance(price, (int, float)) or not isinstance(change, (int, float)):
            continue
        lines.append("%s $%s · 24h %+.2f%%" % (symbol, format(price, ",.2f"), change))
        times.append(updated)
    if not lines:
        return []
    text = "\n".join(lines) + "\nCoinGecko · %s\nhttps://www.coingecko.com/" % stamp(min(times))
    return [(text, "crypto-hour:%d" % (time.time() // 3600))]

def sports():
    index = int(STATE.get("league_cursor", 0)) % len(LEAGUES)
    STATE["league_cursor"] = index + 1
    path, league = LEAGUES[index]
    data = jget("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard" % path) or {}
    output = []
    for event in data.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        teams = competition.get("competitors") or []
        if len(teams) != 2:
            continue
        home = next((team for team in teams if team.get("homeAway") == "home"), teams[0])
        away = next((team for team in teams if team.get("homeAway") == "away"), teams[1])
        status = (competition.get("status") or event.get("status") or {}).get("type") or {}
        phase = status.get("state")
        detail = status.get("shortDetail") or status.get("detail") or ""
        home_name = home.get("team", {}).get("displayName", "")
        away_name = away.get("team", {}).get("displayName", "")
        links = event.get("links") or competition.get("links") or []
        link = next((entry.get("href") for entry in links
                     if str(entry.get("href", "")).startswith("https://")), "")
        if not home_name or not away_name or not link:
            continue
        if phase == "pre":
            line = "%s scheduled: %s at %s · %s" % (league, away_name, home_name, detail)
        elif phase in ("in", "post"):
            label = "Final" if phase == "post" else "Live"
            line = "%s %s: %s %s–%s %s · %s" % (
                league, label, away_name, away.get("score", ""), home.get("score", ""),
                home_name, detail)
        else:
            continue
        key = "sports:%s:%s:%s:%s:%s" % (
            event.get("id"), phase, away.get("score"), home.get("score"), detail)
        output.append((line + "\nESPN · checked %s\n%s" % (stamp(), link), key))
    persist()
    return output

def fragment():
    # Strict normalized records only. A failed provider is not permission to post
    # invented, undated, wrongly denominated or historical sales as "just sold".
    url = os.environ.get("FRAGMENT_SALES_FEED_URL", "https://namespace.my/api/sales?limit=30")
    data = jget(url) or {}
    records = data.get("sales", []) if isinstance(data, dict) else []
    output = []
    for record in records:
        if not isinstance(record, dict):
            continue
        username = str(record.get("username", "")).lstrip("@")
        published = _date(record.get("sold_at", ""))
        price = record.get("price")
        link = str(record.get("url", ""))
        host = urllib.parse.urlparse(link).hostname
        if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", username):
            continue
        if record.get("status") != "sold" or record.get("currency") != "TON":
            continue
        if not published or published.tzinfo is None or not isinstance(price, (int, float)) or price <= 0:
            continue
        if not 0 <= time.time() - published.timestamp() <= 3 * 86400:
            continue
        if not link.startswith("https://") or host not in ("fragment.com", "tonviewer.com", "tonscan.org"):
            continue
        text = ("Reported username sale: @%s · %s TON\n%s\n%s" %
                (username, format(price, ",g"), stamp(published.timestamp()), link))
        output.append((text, "fragment:%s:%s" % (username, published.isoformat())))
    return output

def is_service(text):
    text = text.casefold()
    return bool(re.search(
        r"\b(unban|unbanned|banned|account recovery|recover my|appeal|"
        r"verification service|verify my|blue tick|price list|rate card|"
        r"place an order|order status|your services)\b", text)
        or re.search(r"\b(buy|purchase|order)\b.{0,35}\b(username|handle|verification|service)\b", text)
        or re.search(r"\b(how much|pricing|cost)\b.{0,35}\b(verification|unban|recovery|service)\b", text)
        or re.search(r"\b(who|what|how|where|contact|need|want|offer)\b.{0,60}\bservices?\b", text)
        or re.search(r"\bservices?\b.{0,60}\b(contact|provide|offer|available|pricing|cost)\b", text))

def topic(text):
    text = text.casefold()
    for name, expression in [
        ("service", None), ("rap", r"\b(youngboy|rapper|rap|music|song|album|mixtape)\b"),
        ("starwars", r"\b(star wars|starwars|vader|jedi|sith|yoda|chewbacca|skywalker|grogu)\b"),
        ("crypto", r"\b(crypto|bitcoin|btc|ethereum|eth|ton|solana|coin)\b"),
        ("fragment", r"\b(fragment|username|handle)\b"),
        ("sports", r"\b(nba|nhl|mlb|nfl|mls|soccer|football|basketball|hockey|baseball|score)\b"),
        ("elon", r"\b(elon|musk|tesla|spacex|xai|grok|starlink)\b"),
        ("deals", r"\b(trillion|acquisition|merger|buyout|funding|business deal)\b"),
        ("world", r"\b(news|world|happening|politics|election)\b")]:
        if name == "service" and is_service(text):
            return name
        if expression and re.search(expression, text):
            return name
    return "general"

def content_for(kind, speaker=None, scheduled=False):
    providers = {"world": world, "elon": elon, "deals": deals, "rap": youngboy,
                 "crypto": crypto, "sports": sports, "fragment": fragment}
    if kind == "starwars":
        return discussion_items(kind, speaker)
    if kind == "rap":
        news = youngboy()
        return news if scheduled else news + discussion_items(kind, speaker)
    return providers[kind]() if kind in providers else []

def available_content(kind, speaker, scheduled=False, question=None):
    migrate_discussion_history()
    if question is not None and kind in ("starwars", "rap"):
        choices = discussion_items(kind, speaker)
        selected = None
        if kind == "starwars":
            for idea, pattern in [
                ("music", r"imperial march|music|soundtrack|theme song"),
                ("cloud_city_reveal", r"cloud city|reveal"),
                ("leia_leadership", r"leia|leadership"),
                ("r2_solutions", r"r2|droid|repair"),
                ("opening_scale", r"opening|star destroyer"),
                ("lightsaber_colour", r"colou?r|red blade|blue blade"),
                ("duel_pacing", r"duel|fight|choreograph"),
                ("redemption", r"redemption|anakin|father|emperor"),
                ("loyalty", r"loyal|han|companion|team"),
                ("wisdom", r"wisdom|patience|size"),
                ("presence", r"entrance|armor|armour|helmet|cape|presence"),
            ]:
                if re.search(pattern, question, re.I):
                    selected = idea
                    break
            if not selected and re.search(r"best|greatest|favou?rite|your pick", question, re.I):
                selected = {"yoda": "wisdom", "chewbacca": "loyalty",
                            "lukeskywalker": "redemption"}.get(speaker, "presence")
        else:
            if re.search(r"best|greatest|favou?rite|goat|your pick", question, re.I):
                selected = "ranking"
            elif re.search(r"catalog|older|newer|introduce", question, re.I):
                selected = "catalog"
            elif re.search(r"delivery|melody|voice|sing", question, re.I):
                selected = "delivery"
            else:
                choices = youngboy()
        if selected:
            choices = [(text, key) for text, key in choices if key.endswith(":" + selected)]
        elif kind == "starwars":
            choices = []
    else:
        choices = content_for(kind, speaker, scheduled=scheduled)
    return [(text, key) for text, key in choices if not repeated_content(text, key, kind)]

DESKS = {
    "service": ["brucewayne"], "crypto": ["yoda", "dexter"],
    "fragment": ["chewbacca"], "sports": ["lukeskywalker", "johnwick"],
    "elon": ["lukeskywalker"], "deals": ["chucky", "tonysoprano", "brucewayne"],
    "world": ["darthvader", "peterparker"],
    "rap": ["chucky", "brucewayne"], "starwars": ["darthvader", "yoda", "chewbacca", "lukeskywalker"],
}

def speaker_for(text, kind):
    if kind == "service":
        return choose_speaker(DESKS["service"])
    for name in TOK:
        display = ROSTER.get(name, {}).get("display", name)
        if re.match(r"^%s(?:\b|[,!?:])" % re.escape(display), text, re.I):
            return name
        username = BOT_USERS.get(name)
        if username and re.search(r"@%s\b" % re.escape(username), text, re.I):
            return name
    return choose_speaker(DESKS.get(kind))

def answer_humans(limit=10):
    reader = polling_reader()
    if not reader:
        return 0
    params = {"timeout": 0, "limit": 100,
              "allowed_updates": ["message", "edited_message"]}
    offset = STATE["offsets"].get(reader)
    if offset is None and reader == "brucewayne":
        offset = STATE["offsets"].get("main")
    if offset:
        params["offset"] = offset
    result = tg(TOK[reader], "getUpdates", params)
    if not result.get("ok"):
        if not result.get("cached_rate_limit"):
            log("POLL FAILED code=%s description=%s" %
                (result.get("error_code", "network"), result.get("description", "")))
        return 0
    answered = 0
    for update in result.get("result", []):
        if answered >= limit:
            break
        message = update.get("message") or update.get("edited_message") or {}
        update_id = update.get("update_id", 0)
        sender = message.get("from") or {}
        text = (message.get("text") or message.get("caption") or "").strip()
        mid = message.get("message_id")
        relevant = (str((message.get("chat") or {}).get("id")) == CHAT
                    and not sender.get("is_bot") and mid is not None)
        fresh = time.time() - message.get("date", time.time()) <= 1800
        if relevant and fresh and text:
            STATE["last_topic_at"]["human_activity"] = time.time()
        asks = is_service(text) or "?" in text or text.startswith("/") or bool(
            re.search(r"\b(who|what|why|when|where|how|tell|send|show|explain)\b", text, re.I))
        if relevant and fresh and text and asks and str(mid) not in STATE["replies"]:
            kind = topic(text)
            speaker = speaker_for(text, kind)
            content_key = None
            if kind == "service":
                reply = "For services, message %s privately with your request. %s" % (HANDLE, SITE)
            elif kind == "general":
                if (text.casefold() not in ("/help", "/start")
                        or time.time() - STATE["last_topic_at"].get("help", 0) < 6 * 3600):
                    STATE["offsets"][reader] = update_id + 1
                    persist()
                    continue
                reply = "Ask about Star Wars, NBA YoungBoy, crypto, sports, world news, Elon Musk or business deals. Services: @darthvader."
            else:
                choices = available_content(kind, speaker, question=text)
                if not choices:
                    # Acknowledge the update without posting a repeated fallback or
                    # answering an unrelated question with another stock prompt.
                    STATE["offsets"][reader] = update_id + 1
                    persist()
                    continue
                reply, content_key = choices[0]
            sent = send(speaker, reply, reply=mid, content_key=content_key, kind=kind)
            if sent == 0:
                # Keep this update and the rest of the batch pending on a known failure.
                break
            answered += 1
            if kind == "general":
                STATE["last_topic_at"]["help"] = time.time()
        STATE["offsets"][reader] = update_id + 1
        persist()
    return answered

def react_to_pin():
    reader = choose_speaker(["brucewayne"])
    if not reader:
        return 0
    result = tg(TOK[reader], "getChat", {"chat_id": CHAT})
    pinned = (result.get("result") or {}).get("pinned_message") or {}
    mid = pinned.get("message_id")
    if not mid or str(mid) in STATE["pins"]:
        return 0
    sent = send(reader, "Pinned message acknowledged by the automated assistant.", reply=mid, content_key="pin", kind="pin")
    if sent:
        STATE["pins"][str(mid)] = time.time()
        persist()
        return 1
    return 0

def sticker(who):
    token = TOK.get(who)
    if not token:
        return 0
    persona = ROSTER.get(who, {}).get("persona", who)
    character = {"darthvader": "vader", "chewbacca": "chew",
                 "lukeskywalker": "luke", "brucewayne": "batman",
                 "nbayoungboy": "youngboy"}.get(persona, persona)
    # A speaker may only use that character's pack. Legacy roster "pack" values
    # include broad Star Wars collections and are not safe identity matches.
    pack = PACKS.get(character)
    if not pack:
        log("NO MATCHING MOVING STICKER PACK %s; skipped" % who)
        return 0
    cache_key = "stickers:%s:%s" % (who, pack)
    cached = CACHE.get(cache_key)
    if not cached or cached[0] < time.time():
        result = tg(token, "getStickerSet", {"name": pack})
        if not result.get("ok"):
            return 0
        stickers = (result.get("result") or {}).get("stickers", [])
        CACHE[cache_key] = (time.time() + 3600, stickers)
    else:
        stickers = cached[1]
    fresh = []
    for item in stickers:
        fid = item.get("file_id")
        uid = item.get("file_unique_id")
        if not fid or not uid or not (item.get("is_animated") or item.get("is_video")):
            continue
        if fid in LEGACY_STICKERS or "fid:" + fid in STATE["stickers"] or "uid:" + uid in STATE["stickers"]:
            continue
        fresh.append(item)
    if not fresh:
        log("NO UNUSED MATCHING MOVING STICKER %s; skipped" % who)
        return 0
    counts = STATE.setdefault("sticker_counts", {})
    item = random.choice(fresh)
    result = tg(token, "sendSticker", {"chat_id": CHAT, "sticker": item["file_id"]})
    if result.get("ok") or result.get("uncertain"):
        STATE["stickers"]["uid:" + item["file_unique_id"]] = time.time()
        STATE["stickers"]["fid:" + item["file_id"]] = time.time()
        counts[character] = counts.get(character, 0) + 1
        persist()
    if result.get("ok"):
        log("MOVING STICKER %s pack=%s" % (who, character))
        return 1
    return 0

def beat():
    if time.time() - STATE["last_topic_at"].get("human_activity", 0) < 90:
        return 0
    rotation = ["starwars", "crypto", "sports", "world", "elon", "deals", "rap", "fragment"]
    cooldowns = {"starwars": 5400, "crypto": 3600, "sports": 1800, "world": 3600,
                 "elon": 3600, "deals": 7200, "rap": 7200, "fragment": 3600}
    cursor = int(STATE.get("cursor", 0))
    for attempt in range(len(rotation)):
        kind = rotation[(cursor + attempt) % len(rotation)]
        if time.time() - STATE["last_topic_at"].get(kind, 0) < cooldowns[kind]:
            continue
        speaker = choose_speaker()
        choices = available_content(kind, speaker, scheduled=True)
        if not choices:
            continue
        text, key = random.choice(choices)
        mention_trillion = kind == "deals" and time.time() - STATE["last_topic_at"].get("trillion_context", 0) >= 24 * 3600
        if mention_trillion:
            text += "\nRelated business coverage: @trillion on Instagram."
        sent = send(speaker, text, content_key=key, kind=kind)
        STATE["cursor"] = (cursor + attempt + 1) % len(rotation)
        if sent:
            STATE["last_topic_at"][kind] = time.time()
            if mention_trillion:
                STATE["last_topic_at"]["trillion_context"] = time.time()
            persist()
            if sent > 0 and random.random() < 0.4:
                sticker(speaker)
            return sent
    STATE["cursor"] = (cursor + 1) % len(rotation)
    persist()
    return 0

def set_photo(name, token):
    path = HERE / "avatars" / (name + ".jpg")
    if not path.is_file():
        return True
    boundary = "vader" + os.urandom(12).hex()
    photo = json.dumps({"type": "static", "photo": "attach://profile_photo"})
    body = ('--%s\r\nContent-Disposition: form-data; name="photo"\r\n\r\n%s\r\n' %
            (boundary, photo)).encode()
    body += ('--%s\r\nContent-Disposition: form-data; name="profile_photo"; filename="avatar.jpg"\r\n'
             'Content-Type: image/jpeg\r\n\r\n' % boundary).encode()
    body += path.read_bytes() + ("\r\n--%s--\r\n" % boundary).encode()
    request = urllib.request.Request("https://api.telegram.org/bot%s/setMyProfilePhoto" % token,
                                     data=body, headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return bool(json.load(response).get("ok"))
    except urllib.error.HTTPError as error:
        try:
            result = json.loads(error.read())
        except (ValueError, OSError):
            result = {"error_code": error.code}
        remember_rate_limit(token, "setMyProfilePhoto", result)
        return False
    except (OSError, ValueError):
        return False

def bootstrap_all():
    if os.environ.get("TG_BOOTSTRAP", "1") != "1":
        return
    for name, token in list(TOK.items()):
        if STATE["profile_retry_until"].get(name, 0) > time.time():
            continue
        identity = tg(token, "getMe")
        user = identity.get("result") or {}
        if not identity.get("ok") or not user.get("is_bot"):
            log("INVALID BOT %s; profile setup skipped" % name)
            if identity.get("error_code") in (401, 403) or identity.get("ok"):
                TOK.pop(name, None)
            continue
        BOT_USERS[name] = user.get("username", "")
        fingerprint = "%s:%s:%s" % (PROFILE_VERSION, name, user["id"])
        if STATE["profiles"].get(name) == fingerprint:
            continue
        display = ROSTER[name].get("display", name)
        bio = ("Automated, unofficial character bot for Darth Vader Chat. "
               "Scripted fan opinions and sourced updates. Services: @darthvader.")
        steps = [
            ("name", "setMyName", {"name": display + " · Bot"}),
            ("description", "setMyDescription", {"description": bio}),
            ("short", "setMyShortDescription", {"short_description":
                "Automated character bot · Darth Vader Chat · Services: @darthvader"}),
        ]
        for suffix, method, params in steps:
            key = name + ":" + suffix
            if STATE["profiles"].get(key) != fingerprint:
                if tg(token, method, params).get("ok"):
                    STATE["profiles"][key] = fingerprint
                    persist()
        photo_key = name + ":photo"
        if STATE["profiles"].get(photo_key) != fingerprint and BACKOFF.get(token, 0) <= time.time():
            if set_photo(name, token):
                STATE["profiles"][photo_key] = fingerprint
                persist()
        if all(STATE["profiles"].get(name + ":" + suffix) == fingerprint
               for suffix in ("name", "description", "short", "photo")):
            STATE["profiles"][name] = fingerprint
            persist()
            log("PROFILE READY %s (disclosed bot)" % name)
        else:
            STATE["profile_retry_until"][name] = max(time.time() + 3600, BACKOFF.get(token, 0))
            persist()
            log("PROFILE SETUP INCOMPLETE %s; successful steps saved; retry after cooldown" % name)

def main():
    if not TOK:
        raise SystemExit("No configured bot tokens.")
    if not CHAT or not re.fullmatch(r"-\d+", CHAT):
        raise SystemExit("CHAT_ID must be the numeric ID of the authorized Telegram group.")
    verify_bots()
    resolve_chat()
    STOP.clear()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    seconds = float(os.environ.get("VADER_SECONDS", "0") or 0)
    if not seconds:
        seconds = float(os.environ.get("RUN_MINUTES", "48")) * 60
    deadline = time.monotonic() + seconds if seconds else float("inf")
    bootstrap_all()
    if not TOK:
        raise SystemExit("No valid configured bot tokens.")
    prime_reader()
    gap_min = max(60, float(os.environ.get("GAP_MIN", "600")))
    gap_max = max(gap_min, float(os.environ.get("GAP_MAX", "1200")))
    next_pin = 0
    log("ENGINE READY: %d configured character bots; disclosed activity; chat=%s" % (len(TOK), CHAT))
    try:
        sticker(choose_speaker())
        while not STOP.is_set() and time.monotonic() < deadline:
            answer_humans()
            now = time.time()
            if now >= next_pin:
                react_to_pin()
                next_pin = now + 30
            if now >= STATE.get("next_beat", 0):
                beat()
                STATE["next_beat"] = time.time() + random.uniform(gap_min, gap_max)
                persist()
            if os.environ.get("VADER_ONCE") == "1":
                break
            STOP.wait(min(5, max(0, deadline - time.monotonic())))
    finally:
        persist()
        log("ENGINE STOPPED: state saved")

if __name__ == "__main__":
    main()
