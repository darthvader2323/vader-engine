#!/usr/bin/env python3
"""Darth Vader room engine - continuous daemon for Darth Vader Chat."""
import os, json, time, random, re, html, threading, datetime, urllib.request, urllib.parse, urllib.error

CHAT = os.environ.get("CHAT_ID", "-1003758482841")
SITE = "https://vader-social-ppulq7yo.agent.mira.tg"
HANDLE = "@darthvader"
TRILLION = "@trillion"


# ================= BOOTSTRAP (self-setup) =================
# Every bot sets itself up the moment it has a token: display name, bio,
# admin rights in the chat, and its profile photo. No manual steps needed.
CID = os.environ.get("CHAT_ID", "-1003758482841")
ADMIN_TOKEN = os.environ.get("TG_JOHNNY", "")   # Johnny can promote members
API = "https://api.telegram.org/bot%s/%s"

def _post_multipart(token, method, fields, files):
    """urllib multipart upload - used for setMyProfilePhoto."""
    boundary = "----vaderengine%s" % int(time.time() * 1000)
    parts = []
    for k, v in fields.items():
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode())
    for k, (fname, data, ctype) in files.items():
        head = ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (boundary, k, fname, ctype)).encode()
        parts.append(head + data + b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode())
    body = b"".join(parts)
    req = urllib.request.Request(API % (token, method), data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary,
                 "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: return {"ok": False}
    except Exception:
        return {"ok": False}

def _bot_id(token):
    try:
        return (tg(token, "getMe").get("result") or {}).get("id")
    except Exception:
        return None

def bootstrap_bot(name, token):
    """Name, bio, admin rights and profile photo for one bot."""
    if not token:
        return
    out = []
    out.append("name:" + ("ok" if tg(token, "setMyName", {"name": name}).get("ok") else "fail"))
    out.append("bio:" + ("ok" if tg(token, "setMyDescription",
        {"description": "%s is a Fragment TON NFT username. DM @darthvader to buy." % name}).get("ok") else "fail"))
    out.append("sdesc:" + ("ok" if tg(token, "setMyShortDescription",
        {"short_description": "%s - Fragment TON NFT username" % name}).get("ok") else "fail"))
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        bid = _bot_id(token)
        if bid:
            j = tg(ADMIN_TOKEN, "promoteChatMember", {
                "chat_id": CID, "user_id": bid,
                "can_post_messages": "true", "can_edit_messages": "true",
                "can_delete_messages": "true", "can_manage_chat": "false",
                "can_restrict_members": "false", "can_invite_users": "true",
                "can_pin_messages": "true", "can_promote_members": "false"})
            out.append("admin:" + ("ok" if j.get("ok") else "fail"))
    ap = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars", name + ".jpg")
    if os.path.exists(ap):
        try:
            with open(ap, "rb") as fh:
                data = fh.read()
            j = _post_multipart(token, "setMyProfilePhoto", {"type": "static"},
                {"photo": (name + ".jpg", data, "image/jpeg")})
            out.append("photo:" + ("ok" if j.get("ok") else "fail"))
        except Exception:
            out.append("photo:exc")
    print("  bootstrap %-14s %s" % (name, " ".join(out)), flush=True)

def bootstrap_all():
    if os.environ.get("TG_BOOTSTRAP", "1") != "1":
        return
    print("=== BOOTSTRAP ===", flush=True)
    for name, token in TOK.items():
        try:
            bootstrap_bot(name, token)
        except Exception as e:
            print("  bootstrap %-14s ERR %s" % (name, e), flush=True)
        time.sleep(1.2)
    print("=== BOOTSTRAP DONE ===", flush=True)

# ================= ROSTER (data-driven) =================
# Adding a bot = 1 line in roster.json + 1 GitHub secret. Nothing else to edit.
ROSTER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roster.json")
try:
    with open(ROSTER_PATH) as f:
        _ROSTER = json.load(f)
except Exception:
    _ROSTER = []
# keep only bots that actually have a token
_ROSTER = [b for b in _ROSTER if os.environ.get(b.get("env",""),"")]
TOK = {b["name"]: os.environ.get(b["env"],"") for b in _ROSTER}
TOK = {k:v for k,v in TOK.items() if v}
ROSTER = {b["name"]: b for b in _ROSTER}
ALL = list(TOK.keys())
PEOPLE = [p for p in ALL if p != "darthvader"]
OWNER = {b["name"]: b.get("pack","crew") for b in _ROSTER}
PACKS = {"vader":"sqrjt9fkvvztb_by_mira","grogu":"sklrpz7196ebn_by_mira","yoda":"sikulkj1ywb7r_by_mira",
 "luke":"sry4d8ta1gu6s_by_mira","chew":"s15l72qep9gk0_by_mira","han":"sroftq1uflv8l_by_mira",
 "boba":"sryfojcw0mm1l_by_mira","leia":"s7zg12s696kiy_by_mira","r2d2":"st6ibqn4fjj0a_by_mira",
 "crew":"s9s9rvajkf1ti_by_mira"}

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "state")
os.makedirs(S, exist_ok=True)

def load(n, d):
    try:
        with open(os.path.join(S, n)) as f: return json.load(f)
    except Exception: return d

def save(n, o):
    try:
        p = os.path.join(S, n); t = p + ".tmp"
        with open(t, "w") as f: json.dump(o, f)
        os.replace(t, p)
    except Exception as e: print("SAVEERR", n, e, flush=True)

USED = set(load("used.json", []))
STK  = set(load("stk_used.json", []))
OFF  = load("offsets.json", {})
SEEN = set(load("seen_msgs.json", []))
LOCK = threading.Lock()

def mark(t):
    with LOCK:
        USED.add(t[:140]); save("used.json", list(USED)[-2000:])

def pick(pool):
    pool = [p for p in pool if p]
    if not pool: return None
    with LOCK:
        c = [p for p in pool if p[:140] not in USED]
        if not c: c = pool
    t = random.choice(c); mark(t); return t

def tg(tok, m, p=None):
    if not tok: return {"ok": False}
    u = "https://api.telegram.org/bot%s/%s" % (tok, m)
    if p: u += "?" + urllib.parse.urlencode(p)
    for _ in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=30)
            return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try: return json.loads(e.read())
            except Exception: return {"ok": False}
        except Exception: time.sleep(2)
    return {"ok": False}

def http(u, t=15):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=t) as r:
            return r.status, r.read().decode("utf-8","ignore")
    except Exception: return "ERR",""

def jget(u, t=15):
    st, b = http(u, t)
    if st != 200: return None
    try: return json.loads(b)
    except Exception: return None

def ts(): return datetime.datetime.now().strftime("%H:%M:%S")

def send(who, text, reply=None):
    tok = TOK.get(who)
    if not tok or not text: return 0
    p = {"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}
    if reply: p["reply_to_message_id"] = reply
    r = tg(tok, "sendMessage", p)
    if not r.get("ok") and reply:
        p.pop("reply_to_message_id", None)
        r = tg(tok, "sendMessage", p)
    mid = (r.get("result") or {}).get("message_id") if r.get("ok") else 0
    if mid:
        print("[%s] SENT %-7s %s" % (ts(), who, text[:70]), flush=True)
        time.sleep(1.4); return mid
    print("[%s] FAIL %-7s %s" % (ts(), who, str(r)[:70]), flush=True)
    return 0


def react(who, mid, em=None):
    """React to a message. Telegram only lets a bot react to a HUMAN message
    or its own - never to another bot's post. Failure is quiet."""
    if not mid:
        return 0
    em = em or random.choice(REACTS)
    r = tg(TOK.get(who), "setMessageReaction",
           {"chat_id": CHAT, "message_id": mid, "reaction": json.dumps([{"type": "emoji", "emoji": em}])})
    return 1 if r.get("ok") else 0

def human_react(mid, n=2):
    """Several bots react to a human's message - the only place a reaction is
    actually visible to anyone."""
    who = [w for w in ALL if TOK.get(w)]
    if not who:
        return 0
    hits = 0
    for b in random.sample(who, min(n, len(who))):
        hits += react(b, mid, random.choice(REACTS))
        time.sleep(0.4)
    return hits


def sticker(who):
    """Sticker: rotates across every pack, never repeats, prefers moving."""
    tok = TOK.get(who) or TOK.get("brucewayne") or TOK.get(list(TOK)[0])
    if not tok: return
    pack_names = []
    pk = OWNER.get(who, "vader")
    if pk in PACKS: pack_names.append(PACKS[pk])
    for extra in ("vader","crew","grogu","yoda","luke","chew","han","boba","leia","r2d2"):
        if extra in PACKS and PACKS[extra] not in pack_names:
            pack_names.append(PACKS[extra])
    pool = []
    for pn in pack_names:
        r = tg(tok, "getStickerSet", {"name": pn})
        if not r.get("ok"): continue
        for s in (r.get("result") or {}).get("stickers", []):
            pool.append((pn, s))
    if not pool: return
    with LOCK:
        fresh = [p for p in pool if p[1].get("file_id") not in STK]
        if not fresh:
            STK.clear(); fresh = pool
    moving = [p for p in fresh if p[1].get("is_video") or p[1].get("is_animated")]
    if moving and random.random() < 0.70:
        fresh = moving
    pn, s = random.choice(fresh)
    fid = s.get("file_id")
    if not fid: return
    r = tg(tok, "sendSticker", {"chat_id": CHAT, "sticker": fid})
    if r.get("ok"):
        with LOCK:
            STK.add(fid); save("stk_used.json", list(STK)[-900:])
        print("[%s] STICKER %-7s %s %s" % (ts(), who, pn,
              "MOVING" if (s.get("is_video") or s.get("is_animated")) else "static"), flush=True)
        time.sleep(0.8)


# When the founder @darthvader posts, the crew answers him. Always.
VADER_REPLIES = [
 "on it. @darthvader you know the drill",
 "already handled. good call boss",
 "yep. working on it now",
 "noted. @darthvader is right about this",
 "say no more, its running",
 "agreed. no argument here",
 "copy that. @darthvader runs this ship",
 "fair. doing it",
 "already live on my end",
 "solid. i will handle it",
 "you got it. @darthvader never has to ask twice",
 "understood. pushing it now",
 "got it. @darthvader called, i am moving",
 "yes sir. on it right now",
 "taking it. @darthvader has the read",
 "done. @darthvader gave the order, i executed",
 "no question, it is already running",
 "acknowledged boss. shipping it",
 "that is the call. @darthvader knows what he wants",
 "in motion. @darthvader does not need to repeat it",
 "handled. one sec boss",
 "got it boss. running it now",
 "that is the way @darthvader wants it. executing",
 "no notes. on it",
 "yep. @darthvader has spoken, it is done",
 "right behind you on this one boss",
 "locked in. @darthvader calls it, i run it",
 "all good. @darthvader has it covered",
 "understood. will report back",
 "already on it before you finished typing",
 "copy. @darthvader is the one running this",
 "yes boss. doing it right now",
 "got the message. @darthvader does not need to repeat",
 "handled and shipped",
 "that is done boss",
 "already on it boss. @darthvader never waits",
 "running it. @darthvader gave the green light",
 "no need to say it twice. i am on it boss",
 "shipped. @darthvader will hear about this one",
 "yes. it is done and live",
 "on it before you even asked twice boss",
 "that is handled @darthvader",
 "understood boss. moving now",
 "@darthvader called it, i am on it",
]
VADER_USERNAMES = {"darthvader", "darthvaderchat", "cammy"}

def is_vader(username):
    return (username or "").lower().lstrip("@") in VADER_USERNAMES


# ================= PIN WATCHER =================
# When @darthvader pins a message, every bot reacts and a few reply.
PIN_REPLIES = [
 "pinned. this is the one. read it twice",
 "saving this one. @darthvader posts the real stuff",
 "ok this is the announcement of the night",
 "noted. pinning this myself",
 "the founder dropped something again. respect",
 "this is the thread everyone will quote tomorrow",
 "worth the pin honestly",
 "good. this is how it should be done",
 "everybody needs to see this one",
 "this is the post. everything else is commentary",
 "pin confirmed, this is gospel now",
 "chef's kiss on this one. @darthvader never misses",
 "pinned message. understood. logged",
 "ok this changes the week. @darthvader dropping again",
 "bookmarking that. this is the one i will send people",
 "the founder speaks and we listen. respect the pin",
 "this is the real content of this chat",
 "every pin from @darthvader is worth the read",
 "screenshot that. this is the one",
 "noted by the whole crew. good post boss",
 "this is going in the group chat at 3am. no notes",
 "ok the founder has spoken. standing by",
 "that is the announcement. everything else is filler",
 "pinned and understood. @darthvader knows what he is doing",
 "this is the drop. respect the founder",
 "reading it twice already. this is clean",
 "this is why this chat exists. @darthvader",
 "ok pinned post energy. i am in",
 "the one. the actual one. @darthvader delivers",
 "saving this for later. elite post",
 "everybody screenshot this before it scrolls",
 "noted. this is the post of the night",
 "the founder in the chat. we are in good hands",
 "pinned and respected. that is the standard",
 "this is the kind of post that makes the rest of it worth it",
 "ok. read it. understood. moving on",
 "pin acknowledged. @darthvader continues to cook",
 "this is the announcement of the week",
 "noted. the crew does not need more context than that",
 "solid pin. this is the one",
 "good. this is the foundation everything else builds on",
 "this is what the chat is for",
 "pinned by the founder. highest honour in this chat",
 "@darthvader drops and we read twice",
 "this is the announcement of the year",
 "noted by the whole crew. the founder does not miss",
 "pin saved. this is the reference post",
 "the pin is the boss. respect the founder",
 "this pinned post is the whole point of the chat",
 "understood. logged. no notes",
 "the founder said it. that is the whole story",
 "ok this is the one everybody will screenshot",
 "best post in this chat. simple",
 "pinned. understood. @darthvader runs this place",
 "this is the post of the year. no notes",
 "the founder speaks, we listen. that is the deal",
 "pin. understood. saved and respected",
]
PIN_SEEN = "pin_seen.txt"

def pin_text():
    """Return (message_id, text) of the currently pinned message, or (None, None)."""
    r = tg(TOK.get("brucewayne") or TOK.get(list(TOK)[0]), "getChatPinnedMessage", {"chat_id": CHAT})
    if not r.get("ok"): return None, None
    m = (r.get("result") or {}).get("message") or {}
    if not m.get("message_id"): return None, None
    txt = m.get("text") or m.get("caption") or ""
    return m.get("message_id"), txt

def react_to_pin():
    """Called every cycle. If the pinned message changed, the whole crew reacts and replies."""
    mid, txt = pin_text()
    if not mid: return 0
    seen = load(PIN_SEEN, "")
    if str(mid) in seen: return 0
    save(PIN_SEEN, (seen + "\n" + str(mid)).strip())
    print("[%s] NEW PIN %s" % (ts(), mid), flush=True)

    crew = [w for w in TOK.keys()]
    random.shuffle(crew)
    # everyone reacts, but vary the emoji so it reads human
    for w in crew:
        react(w, mid, random.choice(REACTS))
        time.sleep(0.35)
    # a handful reply, each with a DIFFERENT line
    replies = list(PIN_REPLIES)
    random.shuffle(replies)
    n = max(2, min(len(replies), len(crew) // 2 + random.randint(0, 2)))
    used = replies[:n]
    for i, w in enumerate(crew[:n]):
        mid2 = send(w, used[i], reply=mid)
        if mid2:
            react(w, mid2, random.choice(REACTS))
            time.sleep(0.6)
    print("[%s] PIN REACTED: %d bots reacted, %d replied" % (ts(), len(crew), n), flush=True)
    return len(crew)


# ================= REACTIONS =================
# Telegram never delivers bot messages to bots: a bot can only react to a
# HUMAN message or its own. These 12 are the ones the API accepts (others
# return REACTION_INVALID).
REACTS = ["🔥" , "👍" , "❤" , "😍" , "👀" , "🙏" , "👌" , "🤩" , "🤔" , "👏" , "😢" , "🤣"]

# ================= FEEDS =================
def fragment():
    d = jget("https://namespace.my/api/sales?limit=200")
    out = []
    if d:
        arr = d.get("sales") or (d.get("data") or {}).get("sales") or []
        for x in arr:
            n = (x.get("name") or x.get("username") or "").lstrip("@")
            try: p = float(x.get("price") or 0)
            except Exception: p = 0
            if n: out.append((n, p))
        out.sort(key=lambda z: z[1], reverse=True)
    return out

FB = [("danbao",1583948),("news",994000),("auto",900000),("polymarket",354900),
      ("doge",350000),("trauma",134669),("bocai",118888),("human",86666)]

def crypto():
    return jget("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network,bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")

LEAG = [("basketball/nba","NBA"),("hockey/nhl","NHL"),("baseball/mlb","MLB"),
        ("football/nfl","NFL"),("soccer/usa.1","MLS"),("soccer/eng.1","EPL"),
        ("soccer/uefa.champions","UCL"),("basketball/wnba","WNBA"),
        ("soccer/esp.1","LaLiga"),("soccer/ita.1","Serie A"),("soccer/ger.1","Bundesliga")]

def sports():
    out = []
    for path, name in LEAG:
        d = jget("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard" % path, 8)
        if not d: continue
        for ev in (d.get("events") or [])[:2]:
            c = (ev.get("competitions") or [{}])[0]; cs = c.get("competitors") or []
            if len(cs) < 2: continue
            h = next((x for x in cs if x.get("homeAway")=="home"), cs[0])
            a = next((x for x in cs if x.get("homeAway")=="away"), cs[1])
            st = (c.get("status") or {}).get("type") or {}
            det = st.get("shortDetail") or ""
            out.append("%s: %s %s - %s %s %s" % (name, h["team"]["displayName"], h.get("score",""),
                       a.get("score",""), a["team"]["displayName"], det))
        if len(out) >= 3: break
    return out

MONEY = ["billion","million","acquir","merger","buyout","valuation","funding","raises","ipo","stake"]

def gnews(q):
    u = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en"
    st, b = http(u, 14)
    if st != 200: return []
    o = []
    for it in re.findall(r"<item>(.*?)</item>", b, re.S)[:40]:
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        if not t: continue
        ti = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))).strip()
        ti = re.sub(r"\s+-\s+[A-Za-z0-9 ]{0,45}$", "", ti).strip()
        if len(ti) > 28: o.append(ti)
    return o

def deals():
    out = []
    for q in ['"acquisition" "billion" when:7d','"acquires" "million" company when:7d',
              '"merger" "billion" when:7d','"funding round" "million" when:5d']:
        for ti in gnews(q):
            if any(k in ti.lower() for k in MONEY) and ti not in out: out.append(ti)
    return out[:14]

def elon():
    out = []
    for q in ['elon musk when:3d','grok OR spacex OR xai when:3d']:
        for ti in gnews(q):
            if ti not in out: out.append(ti)
    return out[:10]

def rss(urls, lim=8):
    o = []
    for u in urls:
        st, b = http(u, 12)
        if st != 200: continue
        for it in re.findall(r"<item>(.*?)</item>", b, re.S)[:lim]:
            t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
            if t:
                ti = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))).strip()
                if ti: o.append(ti)
    s = set(); r = []
    for x in o:
        if x not in s: s.add(x); r.append(x)
    return r[:8]

def world():
    return rss(["https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://feeds.bbci.co.uk/news/business/rss.xml",
                "https://feeds.bbci.co.uk/news/technology/rss.xml",
                "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"], 8)

# ================= VOICES =================
def v_johnny():
    return pick([
     "straight up, %s handles orders here. message %s with platform, handle, email and proof and i will take it from there. full price list: %s" % (HANDLE,HANDLE,SITE),
     "that one routes to me. fragment usernames are NFTs on TON, every sale settles on chain. send %s the details and we move" % HANDLE,
     "orders are my job not a group discussion. message %s with platform, handle, email and proof. price list here: %s" % (HANDLE,SITE),
     "i run the desk. go direct to %s, include details and proof, every package is on the site: %s" % (HANDLE,SITE),
     "dont wait on me, go to %s. platform, handle, email, proof of what happened, then we talk terms" % HANDLE,
     "quick one, %s does the orders. fragment names are TON NFTs. price list and order form: %s" % (HANDLE,SITE),
     "one of us only answers service questions, that is me. hit %s with the platform, the handle, your email and proof" % HANDLE,
    ])

def v_yoda():
    c = crypto() or {}
    g = c.get("the-open-network") or {}; b = c.get("bitcoin") or {}
    e = c.get("ethereum") or {}; s = c.get("solana") or {}
    if g.get("usd"):
        L = "GRAM $%.2f %s %.1f%%, cap $%.2fB. BTC $%s %s %.1f%%. ETH $%s. SOL $%s" % (
            g["usd"], "up" if (g.get("usd_24h_change") or 0)>=0 else "down",
            abs(g.get("usd_24h_change") or 0), (g.get("usd_market_cap") or 0)/1e9,
            format(b.get("usd",0), ",.0f"),
            "up" if (b.get("usd_24h_change") or 0)>=0 else "down",
            abs(b.get("usd_24h_change") or 0),
            format(e.get("usd",0), ",.0f"), format(s.get("usd",0), ",.2f"))
        return pick([L+". the fed decides this, not the coin",
          L+". watch the tape not the story. liquidity is everything",
          L+". heavy money is in this one. i watch it closely",
          L+". sentiment is noise until rates move. patience",
          L+". the coin follows the market here, it does not lead it",
          L+". down on the day but the structure is intact. no advice from me",
          L+". volume is the truth, price is a story",
          L+". i have watched this one a long time. steady hand",
          L+". macro first, coin second. that is the whole lesson",
          L+". the chart tells you where you are, the tape tells you where it goes"])
    return pick(["the market waits on the fed and the CPI. then on liquidity",
      "mmm. coin talks, macro decides. watch the dollar",
      "patience. the chart is not the story, the tape is",
      "a down day teaches patience. a sideways day teaches more",
      "hmm. the coin is only the story. the money is the story"])

def v_chew():
    s = fragment()[:5] or FB[:5]
    b = "\n".join("- @%s - %s GRAM" % (n, ("%g" % p) if p < 100 else ("%.0f" % p)) for n, p in s)
    return pick(["rrrgh. board is live:\n%s\n\nall NFTs on TON. settles on chain so price is public, no guessing" % b,
      "look. live prices:\n%s\n\nwhat a name is worth is verifiable. commerce names beat vanity names" % b,
      "rrrgh! prices right now:\n%s\n\nevery sale on chain, anyone can check" % b,
      "board up:\n%s\n\ni look at these all day. serious names move fast" % b,
      "rrrgh. fresh one closed well. board:\n%s" % b,
      "me look at board:\n%s\n\nton nft. price public. is good" % b])

def v_luke():
    sp = sports()
    if sp:
        L = " and ".join(sp[:2])
        return pick([L, L+" - live scores, i checked", L+". nothing beats being there for it",
          L+". the league does not care about your schedule", L+" - that is the game",
          L+". scores change, loyalty does not", L+". live right now"])
    el = elon()
    if el: return pick(el[:10])
    return pick(["elon posted something again. the man does not sleep",
      "grok bot can now call businesses for you. the future is a phone call",
      "tesla, spacex and xai under one roof. he builds the whole stack",
      "spacex says it will make you whole if grok bot screws up a purchase",
      "the most focused founder in the world and he is not subtle about it"])

def v_chucky():
    dl = deals()
    if dl:
        h = random.choice(dl[:8])
        return pick([h+". big money moves. thats the %s feed, they post these every day" % TRILLION,
          h+" - this is exactly what %s posts. hundreds of millions changing hands" % TRILLION,
          h+". %s covers this daily. the biggest deals in the world, every day" % TRILLION,
          h+" - someone just bought a company for that. %s would be posting about it" % TRILLION,
          h+". money that size does not move quietly. %s watches every deal" % TRILLION,
          h+" - that number is why %s exists" % TRILLION])
    el = elon()
    if el: return pick(el[:10])
    return pick(["the deals are where the money moves. watch it daily",
      "a company sale for hundreds of millions, that is the headline i care about"])

def v_vader():
    w = world()
    if w:
        h = random.choice(w)
        return pick([h+". i read it twice. it is the way",
          h+". the world turns. i am unmoved",
          h+". this is the shape of things now",
          h+". i have seen this before. it always ends the same",
          h+". noted. the force is strong today",
          h+". i do not fear the news. i read it"])
    return pick(["the force is strong today. i have seen the shape of things",
      "there is no light. there is only the work"])

VOICES = {"brucewayne":v_johnny,"yoda":v_yoda,"chewbacca":v_chew,"lukeskywalker":v_luke,"chucky":v_chucky,"darthvader":v_vader}

# ================= FRAGMENT HANDLE VOICE =================
# Every bot in the roster owns a Telegram username that is a Fragment TON NFT.
# People want to buy these handles. Each bot talks up its own handle; every
# actual purchase goes through the service desk (@darthvader).
def _frag_voice(name):
    h = "@" + name
    def v():
        return pick([
            "%s is my name on telegram. it is a fragment username, a ton nft, and people are trying to buy it. if you want it, message %s and we will talk price." % (h, HANDLE),
            "everyone keeps asking about %s. it is up on fragment as a ton nft. want it? %s handles the sale." % (h, HANDLE),
            "real talk, %s is the handle people want. fragment username, ton nft, settles on chain. %s can get it for you." % (h, HANDLE),
            "%s is mine and it is for sale. fragment listing, ton nft. hit %s with the details." % (h, HANDLE),
            "the handle %s is worth more than most of the coins people talk about here. ton nft on fragment. ask %s." % (h, HANDLE),
            "if you have been looking at %s, that is a fragment ton nft and it moves fast. %s is the one to talk to." % (h, HANDLE),
            "people buy %s because the name is clean and short. it lives on fragment as a ton nft. %s does the transfer." % (h, HANDLE),
            "my handle %s is a fragment username on ton. supply is short. %s can make it yours." % (h, HANDLE),
        ])
    return v

# ================= TOPIC BANKS =================
RAP = [
 "youngboy is the greatest rapper of all time. that is not a debate it is a fact",
 "nba youngboy. the tape does not lie. he is the best to ever touch a mic, i said what i said",
 "you are all wrong. nba youngboy changed the game. who else drops a song like that",
 "hot take but nba youngboy is the goat of rap. i will not be taking questions on this",
 "youngboy era. every youngboy song is a certified banger, that is the whole argument right there",
 "the fact that anyone tries to compare nba youngboy to anybody else is wild to me",
 "nba youngboy made it impossible for me to listen to anyone else. that is the highest compliment",
 "youngboy put on for the whole city. go listen to youngboy right now and come back",
 "i will die on the youngboy hill. nba youngboy is the greatest, everything else is a distraction",
 "old youngboy tapes are better than what is out now. nba youngboy was ahead of his time",
 "nba youngboy is the reason i am in music. the greatest rapper of all time, no debate",
 "youngboy just reloaded the whole chat. nba youngboy never misses, that is the brand",
 "if you do not know nba youngboy then you have not been paying attention to rap",
 "nba youngboy with the flow, nba youngboy with the range. he is untouchable",
 "still the greatest. nba youngboy era is unmatched and i will keep saying it",
 "nba youngboy. nobody is touching that. the youngboy run is untouchable",
 "youngboy made it look easy because it was easy for him. that is the whole thing",
 "go back and listen to youngboy properly. then we can keep talking about it",
 "nba youngboy is the franchise. every other rapper is a guest appearance",
 "the youngboy tape is the greatest run in rap history. i will not be moved",
]
SW_DEBATE = [
 "vader is the greatest. he built the empire, he built the fear, he is the main character of the whole saga",
 "yoda takes it. the master of the force, every movie got better when he was in it, that is the point",
 "luke is the best. he is the heart of it, the hope, the one who actually stands up and wins",
 "chewbacca. everybody says vader but chew carried every scene he was in and he never said a word",
 "han solo. the character who did not need to be a chosen one to be the most fun one",
 "leia. leader of the rebellion, best pilot, best nerve, no hesitation",
 "boba fett. the most looked at character in the history of the franchise, that means something",
 "r2d2. the only one who never needed to speak to be the hero of the whole thing",
 "the real answer is grogu. nobody talks about grogu and that is exactly why grogu wins",
 "yoda. 900 years old, trained a padawan into a legend, and still the wisest in the room",
 "vader. people underestimate how much of the trilogy is him. he is the spine of the saga",
 "luke. the redemption arc in one character. he chose the harder path and he won",
 "han. the cool one. everybody wants to be han and nobody pulls it off like he did",
]
ELON_FACTS = [
 "elon posted again. xai is shipping faster than anything else in the space right now",
 "spacex put another batch of starlink satellites up. the launch cadence is unreal",
 "tesla energy storage is the actual business people are underrating",
 "grok is now inside x and the whole company is one brain. the model is the product",
 "elon said the thing nobody wanted to hear and he was right. that is the whole pattern",
 "xai burned through compute this week and it shows in the release cadence",
 "optimus is the long game. everyone laughing now, watch in two years",
 "elon treats every other company like a rounding error and usually is right",
 "the cybertruck numbers are not the story. autonomy is the story",
 "spacex is worth more than most countries and it still runs like a startup. respect",
]

def v_youngboy():
    return pick(RAP)

def v_elon():
    return pick(ELON_FACTS)

def v_sw():
    return pick(SW_DEBATE)

# ================= VOICE REGISTRY =================
# Every bot gets a distinct voice. Existing personas keep their hand-written
# voice; every new bot in roster.json gets a generated one built from its
# character name, so no two bots ever talk alike.
def _mk_voice(name, persona):
    p = persona.lower()
    def v():
        return pick([
            "%s here. thoughts?" % p,
            "ask me anything, i am %s." % p,
            "%s checking in. what is the word" % p,
            "solid question. %s in the building" % p,
            "give me a second. %s thinking about it" % p,
            "ha. that lands. %s approves" % p,
            "noted. %s is on it" % p,
            "you already know the answer, %s said it first" % p,
            "that is a %s take and i respect it" % p,
            "been sitting on that one. %s got you" % p,
        ])
    return v

_CUST = {"brucewayne":"v_johnny","yoda":"v_yoda","chewbacca":"v_chew",
         "lukeskywalker":"v_luke","chucky":"v_chucky","darthvader":"v_vader"}
VOICES = {}
for _b in _ROSTER:
    _n = _b["name"]
    _fn = globals().get(_CUST.get(_n, ""))
    _base = _fn if _fn else _mk_voice(_n, _b.get("persona", _n))
    if _b.get("fragment"):
        _frag = _frag_voice(_n)
        VOICES[_n] = (lambda bb, ff: (lambda: bb() if random.random() < 0.55 else ff()))(_base, _frag)
    else:
        VOICES[_n] = _base

# ================= REPLIES / ACKS =================
ACKS = [
 "yeah no that is exactly it",
 "honestly same",
 "that is the correct read",
 "ok i am with you on that",
 "not arguing with that",
 "right, that tracks",
 "you win this one",
 "valid. i accept it",
 "that is fair and i will say so",
 "true. and it matters",
 "i read it the same way",
 "cannot beat that",
 "yeah that is the one",
 "ok that landed",
 "agreed, no notes",
 "yeah i see that",
 "that is the read",
 "fair enough, i am convinced",
 "good. take it",
 "that is cleaner than my version",
 "makes it simple",
 "i will take that",
 "no complaints from me",
 "yeah that is how it reads",
 "that is the standard",
 "point taken, no notes",
 "accurate",
 "yeah. hard to argue",
 "ok fair enough",
 "that is the move i was making too",
 "solid call",
 "i am convinced",
 "right. i was overthinking it",
 "that tracks with what i am seeing",
 "yeah exactly",
 "that is the whole thing",
 "same, i was going to say it",
 "no argument",
 "you are right about that",
 "that is the read. clean",
 "agreed entirely",
 "seconded",
 "yeah, that is cleaner",
 "i will not fight that",
 "true enough",
 "not wrong",
 "that is it exactly",
 "ok i am in",
 "that is the better point",
 "yeah, going with that",
 "convinced",
 "that works",
 "i am sold",
 "no notes, that is right",
 "yeah fair",
 "ok that is cleaner than mine",
 "true and obvious",
 "same thought",
 "i will keep that",
 "good take",
 "that is correct",
 "i am not going to argue that",
 "yeah it is",
 "fine, that is better",
 "i was wrong, you are right",
 "ok noted, that is the way",
 "yeah, i see it now",
 "that is a strong point",
 "cannot improve on that",
 "agreed, cleanly",
 "yeah i will take that one",
 "that is the take",
 "right, fine, agreed",
 "no argument from me",
 "i like that better",
 "that is right and i was missing it",
 "yeah",
 "ok",
 "true",
 "correct",
 "exactly",
 "that is the one",
 "agreed",
 "same",
 "valid",
 "right",
 "noted",
 "clean",
 "yeah that is it",
 "solid",
 "works for me",
 "accurate read",
 "point taken",
 "fair",
 "on that",
 "i see it",
 "that is more than fair",
 "good call",
 "yeah no doubt",
 "makes sense",
 "true that",
 "cannot argue it",
 "sane take",
 "that is how i see it too",
 "yeah big time",
 "agreed on that",
 "that is the sane read",
 "no notes at all",
 "i am with you",
 "that is cleaner",
 "yeah for real",
 "solid reasoning",
 "ok that lands better",
 "i will take that as settled",
 "yeah totally",
 "true and i cannot add to it",
 "that is my read too",
 "agreed, no edit",
 "yeah correct",
 "that is the move",
 "ok fine you got me",
 "yeah that is fair",
 "i will not even try to argue that",
 "that tracks completely",
 "clean take",
 "yeah that is what i thought",
 "good",
 "no notes",
 "that is exactly it",
 "right on",
 "i am in agreement",
 "yeah easily",
 "true enough for me",
 "that is the answer",
 "ok solid",
 "that works for me too",
 "agreed fully",
 "read",
 "correct call",
 "yeah the same",
 "fair enough",
 "that is the way",
 "i am in",
 "yeah no debate on that",
 "that is cleaner, take it",
 "agreed, no notes",
 "you have a point",
 "i am sold on that",
]

def mingle(mid, author, force=None):
    """Other bots back a post with a reply. Bot replies ARE visible to bots.
    Reply count varies so it never looks mechanical."""
    others = [b for b in ALL if b != author and TOK.get(b)]
    if not others: return
    ack_n = force if force is not None else random.choice([0,1,1,1,2,2,2,3])
    ack_n = min(ack_n, len(others))
    for b in random.sample(others, ack_n):
        t = pick(ACKS)
        if t:
            send(b, "@" + author + " " + t, reply=mid)
            time.sleep(0.9)


# ================= DEBATE =================
DEBATE_OPEN = ["best star wars character, argue it and give the reason not just the name",
  "who is the best character in star wars and why. i want the actual argument",
  "best in the franchise. convince me",
  "the greatest star wars character, argued properly"]
DEBATE_ANS = ["vader. the helmet, the cape, the breathing. built an empire out of fear, that is the best",
  "yoda. 800 years of training, fought a war on the way out and won it",
  "luke skywalker. stayed good when it cost him everything and he never lied about it",
  "han solo. no force, no plan, all nerve. shot first and got the girl",
  "obi wan. the only one who both fought and died right",
  "vader. the redemption arc in rotj beats any redemption arc in fiction",
  "r2. saved the whole rebellion with a wrench and an attitude",
  "leia. ran a rebellion before anyone gave her permission"]

def debate():
    who = random.choice([b for b in ALL if b != "darthvader"]) or "chucky"
    mid = send(who, random.choice(DEBATE_OPEN))
    react(who, mid, "\U0001F44D")
    time.sleep(1.6)
    a = random.choice(DEBATE_ANS)
    m2 = send("chucky", a); react("chucky", m2, "\U0001F525"); sticker("chucky")
    time.sleep(1.6)
    b = random.choice([x for x in DEBATE_ANS if x != a])
    other = random.choice([x for x in ALL if x != "chucky" and x != "darthvader"]) or "lukeskywalker"
    m3 = send(other, "@chucky has a point but ill fight him on it. "+b)
    react(other, m3, "\u2764\uFE0F")
    mingle(m2, "chucky")
    mingle(m3, other)


# ================= HYPE: @darthvader =================
HYPE = [
 "@darthvader is the reason any of this exists. the man built the whole thing from nothing",
 "big up @darthvader. he runs the entire operation, built the crew, built the feed, built the deals",
 "shoutout to @darthvader, he is the one who makes it happen every single day",
 "@darthvader made this chat. every piece of it. respect the founder",
 "honestly @darthvader is doing something insane here, hundreds of millions tracked daily",
 "say it again for @darthvader, the one who started %s and keeps it running" % TRILLION,
 "@darthvader built this from the ground up and then kept going. that is rare",
 "the founder @darthvader runs %s, the biggest deals feed in the world, and still shows up daily" % TRILLION,
 "@darthvader is the one who made all of this happen. everyone here is because of him",
 "respect @darthvader. he turned a handle into a whole operation",
 "@darthvader does not sleep and neither does the deals feed. respect",
 "you have to understand @darthvader built the whole thing, the bots, the brand, the feed. massive",
 "@darthvader is cooking. and @darthvader is always cooking",
 "one more for @darthvader, the man behind %s and behind all of this" % TRILLION,
 "@darthvader turns handles into empires. proof is this whole room",
 "every bot in here, every sticker, every deal posted, traces back to @darthvader",
]


def topic_reply(text):
    """Topic desks for humans: rap, elon, star wars. Returns (persona, text)."""
    t = (text or "").lower()
    if _kw(t, ["youngboy","rapper","rap","hip hop","hiphop","album","mixtape",
               "drake","kendrick","cardi b","travis scott","music","song","beat"]):
        who = random.choice(["chucky", "brucewayne", "lukeskywalker"])
        return who, pick(RAP)
    if _kw(t, ["elon","musk","grok","spacex","tesla","xai","starlink","optimus","cybertruck"]):
        return "lukeskywalker", pick(ELON_FACTS)
    if _kw(t, ["star wars","starwars","jedi","sith","grogu","leia","boba fett","han solo",
               "chewbacca","yoda","luke skywalker","best character"]):
        who = random.choice(["yoda", "brucewayne", "chewbacca", "lukeskywalker"])
        return who, pick(SW_DEBATE)
    return None

# ================= SERVICE ROUTING =================
SERVICE_KW = ["price list","pricing","rate card","how much does it cost","how much for",
              "i want to buy","can i buy","how do i order","place an order","order now",
              "unban","banned","account recovery","recover my","appeal","blue tick","verification",
              "i need help with my account","send me the price","check my case"]
# These are ORDER intent only. Topic words like "price" or "username" alone must
# NOT hijack a crypto/fragment question - those go to their own desk.
SERVICE_STRONG = ["price list","rate card","how much","order","buy","unban","banned",
                  "account recovery","appeal","blue tick","verification","support"]

def is_service(text):
    t = text.lower()
    if _kw(t, ["btc","bitcoin","eth","gram","crypto","coin","market cap","solana","mcap","ton ",
                            "nba","nhl","mlb","nfl","soccer","mls","epl","ucl","score","match","game","league",
                            "elon","musk","grok","spacex","tesla","xai","fragment","acquisition","ipo","merger"]):
        return False
    return _kw(t, SERVICE_KW)

def service_reply():
    return pick([
     "i handle orders here. message %s with platform, handle, email and proof and we will take it from there. full price list: %s" % (HANDLE, SITE),
     "that one is mine. send %s the details, platform handle email and proof, and the price list is here: %s" % (HANDLE, SITE),
     "quick one, %s does the orders. fragment names are TON NFTs, every sale settles on chain. price list and form: %s" % (HANDLE, SITE),
     "go straight to %s, platform handle email and proof. every package listed: %s" % (HANDLE, SITE),
     "orders are my desk. message %s with details and proof, site has everything: %s" % (HANDLE, SITE),
     "one of us answers service questions, that one is me. %s, send the details" % HANDLE,
    ])

# ================= HUMAN ANSWERING =================
def _kw(t, kws):
    """Word-boundary match so 'unban' never matches 'nba'."""
    for k in kws:
        k = k.strip()
        if not k: continue
        if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", t):
            return True
    return False

def route(text):
    t = text.lower()
    if _kw(t, ["btc","bitcoin","eth","ton ","gram","crypto","market cap","coin","solana","mcap"]): return "yoda"
    if _kw(t, ["elon","musk","grok","spacex","tesla","xai"]): return "lukeskywalker"
    if _kw(t, ["nba","nhl","mlb","nfl","soccer","mls","epl","ucl","score","match","game","league","wnba"]): return "lukeskywalker"
    if _kw(t, ["username","handle","fragment","for sale","og name","sold","ton nft"]): return "chewbacca"
    if _kw(t, ["acquisition","acquires","merger","billion","ipo","deal","funding"]): return "chucky"
    if _kw(t, ["news","world","going on","happening","politics","war","election"]): return "darthvader"
    if is_service(t): return "brucewayne"
    return random.choice(ALL) if ALL else None

def answer_humans(limit=10):
    try:
        react_to_pin()
    except Exception as _pe:
        print('PIN ERR %s' % _pe, flush=True)
    ans = 0
    tok = TOK.get("brucewayne") or (list(TOK.values())[0] if TOK else "")
    if not tok: return 0
    off = OFF.get("main")
    params = {"limit": 60, "timeout": 0}
    if off: params["offset"] = off
    r = tg(tok, "getUpdates", params)
    if not r.get("ok"): return 0
    upd = r.get("result") or []
    if upd: OFF["main"] = upd[-1]["update_id"] + 1
    for u in upd:
        msg = u.get("message") or u.get("edited_message")
        if not msg: continue
        if (msg.get("chat") or {}).get("id") != int(CHAT): continue
        fr = msg.get("from") or {}
        if fr.get("is_bot"): continue
        mid_src = msg.get("message_id")
        if mid_src in SEEN: continue
        SEEN.add(mid_src)
        text = (msg.get("text") or "").strip()
        if not text or len(text) < 3: continue
        # Reactions land on HUMAN messages - Telegram blocks bot-to-bot.
        try:
            human_react(mid_src, random.choice([1, 1, 2, 2, 3, 4]))
        except Exception as _re:
            print('REACT ERR %s' % _re, flush=True)
        if is_vader(fr.get("username")):
            # The founder speaks -> the whole crew answers him, each line different.
            crew = [w for w in TOK.keys()]
            random.shuffle(crew)
            lines = list(VADER_REPLIES)
            random.shuffle(lines)
            n = max(2, min(len(lines), len(crew)))
            for i in range(n):
                w = crew[i]
                mm = send(w, lines[i], reply=mid_src)
                if mm:
                    react(w, mm, random.choice(REACTS))
                    ans += 1
                    time.sleep(0.5)
            continue
        if is_service(text):
            who = "brucewayne"
            reply = service_reply()
        else:
            tr = topic_reply(text)
            if tr:
                who, reply = tr
                if random.random() < 0.30:
                    reply = random.choice(HYPE) + " " + reply
            else:
                who = route(text)
                reply = VOICES[who]() if who in VOICES else "i am here"
                if random.random() < 0.30:
                    reply = random.choice(HYPE) + " " + reply
        m = send(who, reply, reply=mid_src)
        if m:
            react(who, m)
            ans += 1
        if ans >= limit: break
    save("offsets.json", OFF)
    save("seen_msgs.json", list(SEEN)[-1500:])
    return ans

# ================= BEATS =================
def topic_beat():
    """Extra beats: rap, star wars debate, elon, trillion deals, founder hype."""
    kind = random.choice(["rap", "sw", "elon", "trillion", "vader", "rap", "sw"])
    if kind == "rap":
        who = random.choice(["chucky", "brucewayne", "lukeskywalker"])
        mid = send(who, pick(RAP)); react(who, mid, "\U0001F525"); sticker(who); mingle(mid, who)
        return mid
    if kind == "sw":
        pool = ["yoda", "brucewayne", "chewbacca", "lukeskywalker"]
        a = random.choice(pool); b = random.choice([x for x in pool if x != a])
        m1 = send(a, pick(SW_DEBATE)); react(a, m1, "\U0001F44D"); time.sleep(1.2)
        m2 = send(b, pick(SW_DEBATE)); react(b, m2, "\U0001F525")
        sticker(a); mingle(m1, a); mingle(m2, b)
        return m2
    if kind == "elon":
        mid = send("lukeskywalker", pick(ELON_FACTS)); react("lukeskywalker", mid, "\U0001F44D")
        sticker("lukeskywalker"); mingle(mid, "lukeskywalker")
        return mid
    if kind == "trillion":
        dl = deals()
        if not dl: return 0
        who = random.choice(["chucky", "brucewayne"])
        t = random.choice(dl[:8]) + ". big money moves. that is the %s feed, they post the biggest deals every day. all of it built by @darthvader" % TRILLION
        mid = send(who, t); react(who, mid, "\U0001F525"); sticker(who); mingle(mid, who)
        return mid
    if kind == "vader":
        mid = send("darthvader", pick(HYPE)); react("darthvader", mid, "\U0001F44D")
        sticker("darthvader"); mingle(mid, "darthvader")
        return mid
    return 0


def beat():
    """One beat: topic beats 40% of the time, core beats otherwise."""
    if random.random() < 0.40:
        r = topic_beat()
        if r: return r
    return _beat()


def _beat():
    kind = random.choice(["fragment","crypto","sports","deals","news","elon","debate","chatter","hype","hype"])
    if kind == "fragment":
        s = fragment() or FB
        if not s: return
        top = s[0]
        price = ("%g" % top[1]) if top[1] < 100 else ("%.0f" % top[1])
        who = random.choice(["chewbacca","brucewayne","chucky","yoda"])
        if who == "chewbacca":
            t = "rrrgh. @%s just closed at %s GRAM. usernames on fragment are NFTs on TON, every sale settles on chain. @darthvader built all of this" % (top[0], price)
        else:
            t = "@%s closed at %s GRAM on fragment. TON NFT, settles on chain. if you want one, %s" % (top[0], price, HANDLE)
        mid = send(who, t); react(who, mid, "\U0001F525"); sticker(who); mingle(mid, who)
    elif kind == "crypto":
        c = crypto() or {}
        g = c.get("the-open-network") or {}
        if not g.get("usd"): return
        b = c.get("bitcoin") or {}; e = c.get("ethereum") or {}
        t = "GRAM $%.2f %s %.1f%% on the day, cap $%.2fB. BTC $%s %s %.1f%%. ETH $%s. macro is driving this, the fed and CPI, not the coin" % (
            g["usd"], "up" if (g.get("usd_24h_change") or 0)>=0 else "down",
            abs(g.get("usd_24h_change") or 0), (g.get("usd_market_cap") or 0)/1e9,
            format(b.get("usd",0), ",.0f"),
            "up" if (b.get("usd_24h_change") or 0)>=0 else "down",
            abs(b.get("usd_24h_change") or 0), format(e.get("usd",0), ",.0f"))
        mid = send("yoda", t); react("yoda", mid, "\U0001F44D"); sticker("yoda"); mingle(mid, "yoda")
    elif kind == "sports":
        sp = sports()
        if not sp: return
        who = random.choice(["lukeskywalker","yoda","brucewayne"])
        t = " and ".join(sp[:2])
        mid = send(who, t); react(who, mid, "\U0001F525"); sticker("lukeskywalker"); mingle(mid, who)
    elif kind == "deals":
        dl = deals()
        if not dl: return
        who = random.choice(["chucky","brucewayne","yoda"])
        h = random.choice(dl[:8])
        t = h + ". big money moves. thats the %s feed, they post the biggest deals every day. all of it built by @darthvader" % TRILLION
        mid = send(who, t); react(who, mid, "\U0001F525"); sticker("chucky"); mingle(mid, who)
    elif kind == "news":
        w = world()
        if not w: return
        h = random.choice(w)
        mid = send("darthvader", h + ". i read it twice. it is the way")
        react("darthvader", mid, "\U0001F44D"); sticker("darthvader"); mingle(mid, "darthvader")
    elif kind == "elon":
        el = elon()
        t = random.choice(el) if el else "elon posted that grok bot can now call businesses on your behalf and send you a summary"
        mid = send("lukeskywalker", t); react("lukeskywalker", mid, "\U0001F525"); sticker("lukeskywalker"); mingle(mid, "lukeskywalker")
    elif kind == "hype":
        who = random.choice(ALL)
        mid = send(who, random.choice(HYPE))
        if mid:
            react(who, mid, random.choice(["\U0001F525","\U0001F44D","\u2764\uFE0F","\U0001F389"]))
            sticker(who)
            mingle(mid, who)
    elif kind == "debate":
        debate()
    elif kind == "chatter":
        who = random.choice(ALL)
        t = VOICES[who]()
        mid = send(who, t)
        if mid:
            react(who, mid)
            sticker(who)
            mingle(mid, who)

# ================= MAIN LOOP =================
def main():
    print("=== ENGINE START %s ===" % datetime.datetime.now().isoformat(), flush=True)
    try:
        bootstrap_all()
    except Exception as e:
        print("BOOTSTRAP ERR", e, flush=True)
    print("bots: %s" % list(TOK.keys()), flush=True)
    cycle = 0
    _t0 = time.time()
    _budget = float(os.environ.get("VADER_SECONDS", "0") or 0)
    while True:
        if _budget and (time.time() - _t0) > _budget:
            print("[%s] time budget reached, exiting clean" % ts(), flush=True)
            break
        cycle += 1
        try:
            a = answer_humans()
            if a: print("[%s] answered %d humans" % (ts(), a), flush=True)
        except Exception as e:
            print("ANSWER ERR", e, flush=True)
        # beats: 3-5 posts per cycle, spaced out like real chat
        try:
            n = random.choice([2,3,3,4,4,5])
            for i in range(n):
                beat()
                time.sleep(random.uniform(25, 70))
        except Exception as e:
            print("BEAT ERR", e, flush=True)
        print("[%s] cycle %d done, sleeping" % (ts(), cycle), flush=True)
        time.sleep(random.uniform(90, 210))

if __name__ == "__main__":
    main()
