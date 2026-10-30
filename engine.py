#!/usr/bin/env python3
"""Darth Vader room engine - continuous daemon for Darth Vader Chat."""
import os, json, time, random, re, html, threading, datetime, urllib.request, urllib.parse, urllib.error

CHAT = os.environ.get("CHAT_ID", "-1003758482841")
SITE = "https://vader-social-ppulq7yo.agent.mira.tg"
HANDLE = "@darthvader"
TRILLION = "@trillion"

TOK = {
 "johnny": os.environ.get("TG_JOHNNY",""),
 "yoda":   os.environ.get("TG_YODA",""),
 "luke":   os.environ.get("TG_LUKE",""),
 "chew":   os.environ.get("TG_CHEW",""),
 "chucky": os.environ.get("TG_CHUCKY",""),
 "vader":  os.environ.get("TG_VADER",""),
}
TOK = {k:v for k,v in TOK.items() if v}
ALL = list(TOK.keys())
PEOPLE = [p for p in ALL if p != "vader"]

PACKS = {"vader":"sqrjt9fkvvztb_by_mira","grogu":"sklrpz7196ebn_by_mira","yoda":"sikulkj1ywb7r_by_mira",
 "luke":"sry4d8ta1gu6s_by_mira","chew":"s15l72qep9gk0_by_mira","han":"sroftq1uflv8l_by_mira",
 "boba":"sryfojcw0mm1l_by_mira","leia":"s7zg12s696kiy_by_mira","r2d2":"st6ibqn4fjj0a_by_mira",
 "crew":"s9s9rvajkf1ti_by_mira"}
OWNER = {"vader":"vader","yoda":"yoda","luke":"grogu","chew":"chew","chucky":"crew","johnny":"han"}

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
    if not mid: return
    em = em or random.choice(REACTS)
    tg(TOK.get(who), "setMessageReaction",
       {"chat_id": CHAT, "message_id": mid, "reaction": json.dumps([{"type":"emoji","emoji":em}])})
    time.sleep(0.4)

def sticker(who):
    """Prefer MOVING stickers (video > lottie > static). Never repeat one."""
    pk = OWNER.get(who, "vader")
    if pk not in PACKS: return
    tok = TOK.get(who) or TOK.get("johnny") or TOK.get(list(TOK)[0])
    r = tg(TOK.get("johnny") or tok, "getStickerSet", {"name": PACKS[pk]})
    if not r.get("ok"): return
    allst = r["result"]["stickers"]
    unused = [s for s in allst if s["file_id"] not in STK]
    if not unused:
        STK.clear(); save("stk_used.json", [])
        unused = list(allst)
    if not unused: return
    def rank(s):
        if s.get("is_video"): return 0
        if s.get("is_animated"): return 1
        return 2
    unused.sort(key=rank)
    moving = [s for s in unused if rank(s) == 0]
    anim = [s for s in unused if rank(s) == 1]
    pool = moving or anim or unused
    kind = "moving" if moving else ("animated" if anim else "static")
    fid = random.choice(pool)["file_id"]
    res = tg(tok, "sendSticker", {"chat_id": CHAT, "sticker": fid})
    if res.get("ok"):
        STK.add(fid); save("stk_used.json", list(STK))
        print("[%s] STICKER %s (%s)" % (ts(), who, kind), flush=True)
    time.sleep(1.0)



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
]
PIN_SEEN = "pin_seen.txt"

def pin_text():
    """Return (message_id, text) of the currently pinned message, or (None, None)."""
    r = tg(TOK.get("johnny") or TOK.get(list(TOK)[0]), "getChatPinnedMessage", {"chat_id": CHAT})
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

VOICES = {"johnny":v_johnny,"yoda":v_yoda,"chew":v_chew,"luke":v_luke,"chucky":v_chucky,"vader":v_vader}

# ================= REPLIES / ACKS =================
ACKS = ["fair point, that tracks","that is a good read","agreed, no argument from me",
 "ha, that is the one","you are right about that","not wrong","that tracks with what i am seeing",
 "ok that lands","strong take and i am into it","yeah i see it","hard to argue","that is the move",
 "mhm. good read","true","no notes","that is how it goes","ok fair","yeah that is the play",
 "cant argue with that","solid","that is cleaner","right","i see it","good call",
 "yeah that lines up","makes sense to me","that is the correct read","accurate","w take",
 "i will take that","honestly yeah","that is the standard","seconded","agreed entirely",
 "point taken","yeah ok","fine by me","that is correct","take it","noted","clean read",
 "true enough","i am with you","no complaints","works for me","that is the way"]

def mingle(mid, author, force=None):
    others = [b for b in ALL if b != author]
    if not others: return
    n = force if force is not None else random.choice([0,1,1,1,2,2,3,3,4,5])
    n = min(n, len(others))
    if n > 0:
        for b in random.sample(others, n):
            react(b, mid, random.choice(REACTS))
        time.sleep(0.6)
    ack_n = min(random.choice([0,1,1,2]), len(others))
    if ack_n > 0:
        for b in random.sample(others, ack_n):
            t = pick(ACKS)
            if t:
                send(b, "@"+author+" "+t, reply=mid)
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
    who = random.choice([b for b in ALL if b != "vader"]) or "chucky"
    mid = send(who, random.choice(DEBATE_OPEN))
    react(who, mid, "\U0001F44D")
    time.sleep(1.6)
    a = random.choice(DEBATE_ANS)
    m2 = send("chucky", a); react("chucky", m2, "\U0001F525"); sticker("chucky")
    time.sleep(1.6)
    b = random.choice([x for x in DEBATE_ANS if x != a])
    other = random.choice([x for x in ALL if x != "chucky" and x != "vader"]) or "luke"
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


# ================= SERVICE ROUTING =================
SERVICE_KW = ["price","pricing","cost","charge","how much","order","buy","rate card","pay",
              "unban","banned","account recovery","recover","appeal","instagram","tiktok",
              "username","handle","fragment","verification","verify","blue tick","support"]

def is_service(text):
    t = text.lower()
    return any(k in t for k in SERVICE_KW)

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
def route(text):
    t = text.lower()
    if is_service(t): return "johnny"
    if any(k in t for k in ["btc","bitcoin","eth","ton","gram","crypto","market cap","coin","solana","mcap"]): return "yoda"
    if any(k in t for k in ["elon","musk","grok","spacex","tesla","xai"]): return "luke"
    if any(k in t for k in ["nba","nhl","mlb","nfl","soccer","mls","epl","ucl","score","match","game","league","wnba"]): return "luke"
    if any(k in t for k in ["acquisition","acquires","merger","billion","ipo","deal","funding"]): return "chucky"
    if any(k in t for k in ["username","handle","fragment","for sale","og name","sold"]): return "chew"
    if any(k in t for k in ["news","world","going on","happening","politics","war","election"]): return "vader"
    return random.choice(ALL) if ALL else None

def answer_humans(limit=10):
    try:
        react_to_pin()
    except Exception as _pe:
        print('PIN ERR %s' % _pe, flush=True)
    ans = 0
    tok = TOK.get("johnny") or (list(TOK.values())[0] if TOK else "")
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
            who = "johnny"
            reply = service_reply()
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
def beat():
    kind = random.choice(["fragment","crypto","sports","deals","news","elon","debate","chatter","hype","hype"])
    if kind == "fragment":
        s = fragment() or FB
        if not s: return
        top = s[0]
        price = ("%g" % top[1]) if top[1] < 100 else ("%.0f" % top[1])
        who = random.choice(["chew","johnny","chucky","yoda"])
        if who == "chew":
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
        who = random.choice(["luke","yoda","johnny"])
        t = " and ".join(sp[:2])
        mid = send(who, t); react(who, mid, "\U0001F525"); sticker("luke"); mingle(mid, who)
    elif kind == "deals":
        dl = deals()
        if not dl: return
        who = random.choice(["chucky","johnny","yoda"])
        h = random.choice(dl[:8])
        t = h + ". big money moves. thats the %s feed, they post the biggest deals every day. all of it built by @darthvader" % TRILLION
        mid = send(who, t); react(who, mid, "\U0001F525"); sticker("chucky"); mingle(mid, who)
    elif kind == "news":
        w = world()
        if not w: return
        h = random.choice(w)
        mid = send("vader", h + ". i read it twice. it is the way")
        react("vader", mid, "\U0001F44D"); sticker("vader"); mingle(mid, "vader")
    elif kind == "elon":
        el = elon()
        t = random.choice(el) if el else "elon posted that grok bot can now call businesses on your behalf and send you a summary"
        mid = send("luke", t); react("luke", mid, "\U0001F525"); sticker("luke"); mingle(mid, "luke")
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
    print("bots: %s" % list(TOK.keys()), flush=True)
    cycle = 0
    while True:
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
