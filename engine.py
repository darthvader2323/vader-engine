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

def load(name, default):
    try:
        return json.loads((S / name).read_text())
    except (OSError, ValueError):
        return default

def initial_state():
    return {"version": 1, "used": {}, "replies": {}, "stickers": {},
            "pins": {}, "profiles": {}, "offsets": {}, "last_spoke": {},
            "last_topic_at": {}, "next_beat": 0, "cursor": 0, "updated_at": 0}

STATE = initial_state()
_saved = load("runtime.json", {})
if isinstance(_saved, dict):
    STATE.update(_saved)
for _key in ("used", "replies", "stickers", "pins", "profiles", "offsets",
             "last_spoke", "last_topic_at"):
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

def tg(token, method, params=None):
    if not token:
        return {"ok": False, "error_code": 401}
    if BACKOFF.get(token, 0) > time.time():
        return {"ok": False, "error_code": 429}
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
    if result.get("error_code") == 429:
        BACKOFF[token] = time.time() + (result.get("parameters", {}).get("retry_after") or 60)
    return result

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

def send(who, text, reply=None, content_key=None):
    if who not in TOK or not text:
        return 0
    key = digest(content_key or text)
    reply_key = ((content_key + ":" if content_key else "") + str(reply)) if reply is not None else None
    if reply_key and reply_key in STATE["replies"]:
        return 0
    if not reply_key and key in STATE["used"]:
        return 0
    # Claim before sending: a process interruption or unknown API result must not
    # cause a wave of repeated replies on restart.
    if reply_key:
        STATE["replies"][reply_key] = time.time()
    else:
        STATE["used"][key] = time.time()
    persist()
    display = ROSTER.get(who, {}).get("display", who)
    params = {"chat_id": CHAT, "text": "[%s bot]\n%s" % (display, text),
              "link_preview_options": {"is_disabled": True}}
    if reply_key:
        params["reply_parameters"] = {"message_id": int(reply),
                                      "allow_sending_without_reply": False}
    result = tg(TOK[who], "sendMessage", params)
    if result.get("ok"):
        STATE["used"][digest(text)] = time.time()
        STATE["last_spoke"][who] = time.time()
        persist()
        log("SENT %s%s" % (who, " reply" if reply_key else " scheduled"))
        return result["result"]["message_id"]
    if result.get("uncertain"):
        log("DELIVERY UNKNOWN %s; no automatic duplicate send" % who)
        return -1
    if reply_key:
        STATE["replies"].pop(reply_key, None)
    else:
        STATE["used"].pop(key, None)
    persist()
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
    return gnews('"Elon Musk" OR SpaceX OR xAI OR Tesla')

def deals():
    return gnews('company acquisition merger "$" million billion', 7)

def youngboy():
    return gnews('"NBA YoungBoy" OR "YoungBoy Never Broke Again"', 7)

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
        or re.search(r"\b(how much|pricing|cost)\b.{0,35}\b(verification|unban|recovery|service)\b", text))

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

def content_for(kind):
    providers = {"world": world, "elon": elon, "deals": deals, "rap": youngboy,
                 "crypto": crypto, "sports": sports, "fragment": fragment}
    if kind == "starwars":
        return [(text, text) for text in STAR_WARS]
    if kind == "rap":
        news = youngboy()
        return news + [(text, text) for text in RAP]
    return providers[kind]() if kind in providers else []

GENERAL_VOICES = {
 "brucewayne": [
  "right, i run this desk. ask properly and i will answer properly",
  "that is my corner. give me the ask",
  "i handle the service side. what do you need done",
  "morning. i am on it, what is the job",
  "you are in the right place. talk to me",
  "give me the details and i will sort it",
 ],
 "yoda": [
  "hmm. interesting question you ask",
  "the force of the matter is simple. tell me more",
  "much to think about, yes. go on",
  "hmm yes. that path you choose, tell me",
 ],
 "lukeskywalker": [
  "sure thing. what are we working on",
  "yeah of course. lay it out for me",
  "happy to help. what do you need",
  "no problem. what is the goal here",
 ],
 "chewbacca": [
  "raaaawggh! rooo",
  "rroooaaawr. yes, talk",
  "rrrraaaawh. here, listen",
  "rrgghh. what you want",
 ],
 "chucky": [
  "ohhh i like where this is going. keep talking",
  "hehe. say that again for me",
  "sweetie, tell me more",
  "ohhh you are trouble. i like it",
 ],
 "darthvader": [
  "state your request. it will be handled",
  "your answer is near. be precise",
  "i have heard you. proceed",
  "speak plainly and it will be done",
 ],
}

GENERAL_REPLIES = [
 "here. what is it", "i am here. hit me", "listening. what do you need",
 "go ahead, ask away", "that is the right question to ask", "okay. give me the details",
 "i am on it. talk to me", "say more, i am following", "good question, let me think about that",
 "noted. that is worth digging into", "you have my attention",
 "ask away, i will give you the honest version", "sure, lay it out", "that lands. what else",
 "i am here for it", "talk to me. what is on your mind", "okay, i hear you. keep going",
 "that is the kind of thing i can help with", "right. so what is the actual question",
 "give me the short version and i will take it from there",
 "understood. what is the outcome you want", "noted, boss. continue",
 "i am watching. keep talking", "that is enough for me to work with",
 "fine. i am listening properly now", "go on then",
 "that is a real one. let me handle it", "you want the short answer or the long one",
 "okay, that is on my list", "speak, i will answer properly", "noted. no fluff from me",
 "i hear you. what is the deadline", "that is workable. talk to me", "i am here, no rush",
 "ask me properly and i will answer properly", "that is a clean question. answering now",
 "okay. understood the ask", "that is straight enough for me", "i am with you. continue",
 "right. say the rest", "good, that is clear enough", "noted and logged",
 "i am here, no nonsense", "go ahead", "that is workable, i can do something with it",
 "yeah, i am listening", "okay, that landed. what next", "i will take that one",
 "right. give me the details and i will handle it",
]

CONFIRM_REPLIES = [
 "i cannot confirm a fresh update on that right now, and i will not guess",
 "nothing solid on that this second. i do not want to fake it",
 "that is moving fast, i will not post something I cannot stand behind",
 "no clean read on it yet. hold that thought",
 "i would rather say nothing than say something wrong about that",
 "still checking that one. i will get back to it",
 "i do not have that confirmed, sorry",
 "that is a gap on my end right now, not a real answer",
 "nothing verified yet on that",
 "i will not fake it. nothing confirmed on that one",
]


def pick_general(who):
    """General chatter that differs per persona and never repeats."""
    pool = GENERAL_VOICES.get(who) or GENERAL_REPLIES
    fresh = [t for t in pool if digest(t) not in STATE["used"]]
    if not fresh:
        fresh = [t for t in GENERAL_REPLIES if digest(t) not in STATE["used"]]
    if not fresh:
        fresh = list(GENERAL_REPLIES)
    return random.choice(fresh)

DESKS = {
    "service": ["brucewayne"], "crypto": ["yoda", "dexter"],
    "fragment": ["chewbacca"], "sports": ["lukeskywalker", "johnwick"],
    "elon": ["lukeskywalker"], "deals": ["chucky", "tonysoprano", "brucewayne"],
    "world": ["darthvader", "peterparker"],
    "rap": ["chucky", "brucewayne"], "starwars": ["darthvader", "yoda", "chewbacca", "lukeskywalker"],
}

def answer_humans(limit=10):
    reader = "brucewayne" if "brucewayne" in TOK else next(iter(TOK), None)
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
        log("POLL FAILED code=%s; check for another worker or an existing webhook" %
            result.get("error_code", "network"))
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
        asks = is_service(text) or "?" in text or text.startswith("/") or bool(
            re.search(r"\b(who|what|why|when|where|how|tell|send|show|explain)\b", text, re.I))
        if not asks and re.match(r"^(gm|gn|hello|hi|hey|yo|sup|morning|good morning|"
                                 r"good evening|how you doing|hows it going|whats up|"
                                 r"what's up|anyone|anybody|good night|lol|lmao|nice|"
                                 r"cool|wow|damn|lets go|let's go|how about it)\b", text, re.I):
            asks = True
        if relevant and fresh and text and asks and str(mid) not in STATE["replies"]:
            kind = topic(text)
            speaker = choose_speaker(DESKS.get(kind))
            if kind == "service":
                reply = "For services, message %s privately with your request. %s" % (HANDLE, SITE)
            elif kind == "general":
                reply = pick_general(speaker)
            else:
                choices = content_for(kind)
                reply = next((entry[0] for entry in choices
                              if digest(entry[1]) not in STATE["used"]
                              and digest(entry[0]) not in STATE["used"]), None)
                if not reply:
                    reply = random.choice(CONFIRM_REPLIES)
            sent = send(speaker, reply, reply=mid)
            if sent == 0:
                # Keep this update and the rest of the batch pending on a known failure.
                break
            answered += 1
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
    pin_lines = [
        "pinned. read it twice", "noted. this is the one",
        "acknowledged. the founder spoke", "saved. that is the announcement",
        "got it. reading it again", "understood. this is the standard",
        "logged. no notes", "that is the post. everything else is commentary",
    ]
    sent = send(reader, random.choice(pin_lines), reply=mid, content_key="pin")
    if sent:
        STATE["pins"][str(mid)] = time.time()
        persist()
        return 1
    return 0

def sticker(who):
    token = TOK.get(who)
    if not token:
        return 0
    groups = {}
    for character, pack in PACKS.items():
        cache_key = "stickers:%s:%s" % (who, pack)
        cached = CACHE.get(cache_key)
        if not cached or cached[0] < time.time():
            result = tg(token, "getStickerSet", {"name": pack})
            stickers = (result.get("result") or {}).get("stickers", []) if result.get("ok") else []
            CACHE[cache_key] = (time.time() + 3600, stickers)
        else:
            stickers = cached[1]
        fresh = []
        for item in stickers:
            fid = item.get("file_id")
            uid = item.get("file_unique_id")
            if not fid or not uid:
                continue
            if fid in LEGACY_STICKERS or "fid:" + fid in STATE["stickers"] or "uid:" + uid in STATE["stickers"]:
                continue
            fresh.append(item)
        if fresh:
            moving = [i for i in fresh if i.get("is_animated") or i.get("is_video")]
            groups[character] = moving if moving else fresh
    if not groups:
        log("NO UNUSED STICKERS in any pack")
        return 0
    counts = STATE.setdefault("sticker_counts", {})
    character = min(groups, key=lambda name: (counts.get(name, 0) / (4 if name == "vader" else 1),
                                              random.random()))
    item = random.choice(groups[character])
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
    rotation = ["starwars", "crypto", "sports", "world", "elon", "deals", "rap", "fragment", "starwars"]
    cursor = int(STATE.get("cursor", 0))
    for attempt in range(len(rotation)):
        kind = rotation[(cursor + attempt) % len(rotation)]
        if kind == "crypto" and time.time() - STATE["last_topic_at"].get(kind, 0) < 3600:
            continue
        choices = [(text, key) for text, key in content_for(kind)
                   if digest(key) not in STATE["used"] and digest(text) not in STATE["used"]]
        if not choices:
            continue
        text, key = random.choice(choices)
        if kind == "deals":
            text += ("\n@trillion on Instagram covers major business deals. "
                     "The group owner identifies @darthvader as its creator.")
        speaker = choose_speaker(DESKS.get(kind))
        sent = send(speaker, text, content_key=key)
        STATE["cursor"] = (cursor + attempt + 1) % len(rotation)
        if sent:
            STATE["last_topic_at"][kind] = time.time()
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
    except (OSError, ValueError):
        return False

def bootstrap_all():
    if os.environ.get("TG_BOOTSTRAP", "1") != "1":
        return
    for name, token in list(TOK.items()):
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
        outcomes = [
            tg(token, "setMyName", {"name": display + " · Bot"}).get("ok"),
            tg(token, "setMyDescription", {"description": bio}).get("ok"),
            tg(token, "setMyShortDescription",
               {"short_description": "Automated character bot · Darth Vader Chat · Services: @darthvader"}).get("ok"),
            set_photo(name, token),
        ]
        if all(outcomes):
            STATE["profiles"][name] = fingerprint
            persist()
            log("PROFILE READY %s (disclosed bot)" % name)
        else:
            log("PROFILE SETUP INCOMPLETE %s; will retry next run" % name)

def main():
    if not TOK:
        raise SystemExit("No configured bot tokens.")
    if not CHAT or not re.fullmatch(r"-\d+", CHAT):
        raise SystemExit("CHAT_ID must be the numeric ID of the authorized Telegram group.")
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
    gap_min = max(60, float(os.environ.get("GAP_MIN", "600")))
    gap_max = max(gap_min, float(os.environ.get("GAP_MAX", "1200")))
    next_pin = 0
    log("ENGINE READY: %d configured character bots; disclosed activity; chat=%s" % (len(TOK), CHAT))
    try:
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
            elif STATE.get("next_beat", 0) - time.time() > gap_max * 2:
                STATE["next_beat"] = 0
                persist()
            if os.environ.get("VADER_ONCE") == "1":
                break
            STOP.wait(min(5, max(0, deadline - time.monotonic())))
    finally:
        persist()
        log("ENGINE STOPPED: state saved")

if __name__ == "__main__":
    main()
