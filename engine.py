#!/usr/bin/env python3
"""Darth Vader room engine - posts beats into Darth Vader Chat and answers humans."""
import os, json, time, random, re, html, urllib.request, urllib.parse, urllib.error, datetime

CHAT = os.environ.get("CHAT_ID", "-1003758482841")
SITE = "https://vader-social-ppulq7yo.agent.mira.tg"
HANDLE = "@darthvader"

TOKENS = {
    "johnny": os.environ.get("TG_JOHNNY", ""),
    "yoda":   os.environ.get("TG_YODA", ""),
    "luke":   os.environ.get("TG_LUKE", ""),
    "chew":   os.environ.get("TG_CHEW", ""),
    "chucky": os.environ.get("TG_CHUCKY", ""),
    "vader":  os.environ.get("TG_VADER", ""),
}
for k in list(TOKENS):
    if not TOKENS[k]:
        TOKENS.pop(k)

STICKER_PACKS = {
    "vader": "sqrjt9fkvvztb_by_mira", "grogu": "sklrpz7196ebn_by_mira",
    "yoda": "sikulkj1ywb7r_by_mira",  "luke": "sry4d8ta1gu6s_by_mira",
    "chew": "s15l72qep9gk0_by_mira",  "han": "sroftq1uflv8l_by_mira",
    "boba": "sryfojcw0mm1l_by_mira",  "leia": "s7zg12s696kiy_by_mira",
    "r2d2": "st6ibqn4fjj0a_by_mira",  "crew": "s9s9rvajkf1ti_by_mira",
}

def tg(tok, method, params=None):
    url = "https://api.telegram.org/bot%s/%s" % (tok, method)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: return {"ok": False}
    except Exception:
        return {"ok": False}

def http(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except Exception:
        return "ERR", ""

def jget(url, timeout=15):
    st, body = http(url, timeout)
    if st != 200: return None
    try: return json.loads(body)
    except Exception: return None

STATE_DIR = os.environ.get("STATE_DIR", "/tmp/vader")
os.makedirs(STATE_DIR, exist_ok=True)

def load(name, default):
    try:
        with open(os.path.join(STATE_DIR, name)) as f: return json.load(f)
    except Exception: return default

def save(name, obj):
    try:
        with open(os.path.join(STATE_DIR, name), "w") as f: json.dump(obj, f)
    except Exception: pass

USED = set(load("used.json", []))
STK_USED = set(load("stk_used.json", []))
OFFSETS = load("offsets.json", {})

def remember(text):
    USED.add(text[:120]); save("used.json", list(USED)[-500:])

def fresh(pool):
    pool = list(pool)
    if not pool: return None
    cands = [p for p in pool [p for p in pool if p[:120] not in USED]
    if not cands: cands = pool
    pick = random.choice(cands); remember(pick); return pick

def send(who, text, reply_to=None):
    tok = TOKENS.get(who) or TOKENS.get("johnny")
    if not tok: return 0
    p = {"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}
    if reply_to: p["reply_to_message_id"] = reply_to
    r = tg(tok, "sendMessage", p)
    ok = r.get("ok")
    mid = (r.get("result") or {}).get("message_id") if ok else 0
    print("SEND %-7s %-6s %s" % (who, mid, text[:70]), flush=True)
    time.sleep(1.6)
    return mid or 0

def react(who, mid, emoji=None):
    if not mid: return
    tok = TOKENS.get(who) or TOKENS.get("johnny")
    if not tok: return
    em = emoji or random.choice(["\U0001F525","\U0001F44D","❤️","\U0001F92E","\U0001F389","\U0001F601","\U0001F44F"])
    tg(tok, "setMessageReaction", {"chat_id": CHAT, "message_id": mid,
        "reaction": json.dumps([{"type": "emoji", "emoji": em}])})
    time.sleep(0.6)

def sticker(who, pk):
    if pk not in STICKER_PACKS: return
    tok = TOKENS.get("johnny") or ""
    if not tok: return
    r = tg(tok, "getStickerSet", {"name": STICKER_PACKS[pk]})
    if not r.get("ok"): return
    ids = [s["file_id"] for s in r["result"]["stickers"] if s["file_id"] not in STK_USED]
    if not ids: return
    fid = random.choice(ids)
    res = tg(TOKENS.get(who) or tok, "sendSticker", {"chat_id": CHAT, "sticker": fid})
    if res.get("ok"):
        STK_USED.add(fid); save("stk_used.json", list(STK_USED))
        print("STICKER %s %s" % (who, pk), flush=True)
    time.sleep(1.1)

LIKES = ["\U0001F525","this","agreed","yeah","\U0001F44D","true","ha","nice","\U0001F602","word","correct","solid","yep","noted","indeed"]
def likes(target, mid, n=None):
    if not mid: return
    others = [b for b in TOKENS if b != target]
    if not others: return
    n = min(random.choice([0,1,1,2,2,3,4,5]) if n is None else n, len(others))
    for b in random.sample(others, n):
        tok = TOKENS.get(b)
        if not tok: continue
        tg(tok, "sendMessage", {"chat_id": CHAT, "text": fresh(LIKES), "disable_web_page_preview": "true"})
        time.sleep(0.9)

def fragment_sales():
    d = jget("https://namespace.my/api/sales?limit=150")
    out = []
    if d:
        arr = d.get("sales") or (d.get("data") or {}).get("sales") or []
        for x in arr:
            n = x.get("name") or x.get("username")
            try: p = float(x.get("price") or 0)
            except Exception: p = 0
            if n: out.append((n, p))
        out.sort(key=lambda z: z[1], reverse=True)
    return out

FALLBACK_SALES = [("danbao",1583948),("@news",994000),("@auto",900000),("+8888222",520000),("@polymarket",354900),("@doge",350000),("@trauma",134669),("@bocai",118888),("@human",86666)]

def crypto():
    return jget("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network,bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")

LEAGUES = [("basketball/nba","NBA"),("hockey/nhl","NHL"),("baseball/mlb","MLB"),("football/nfl","NFL"),("soccer/usa.1","MLS"),("soccer/eng.1","EPL"),("soccer/uefa.champions","UCL"),("basketball/wnba","WNBA")]
def sports():
    out = []
    for path, name in LEAGUES:
        d = jget("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard" % path, 10)
        if not d: continue
        for ev in (d.get("events") or [])[:2]:
            c = (ev.get("competitions") or [{}])[0]
            cs = c.get("competitors") or []
            if len(cs) < 2: continue
            h = next((x for x in cs if x.get("homeAway") == "home"), cs[0])
            a = next((x for x in cs if x.get("homeAway") == "away"), cs[1])
            out.append("%s: %s %s - %s %s" % (name, h["team"]["displayName"], h.get("score",""), a.get("score",""), a["team"]["displayName"]))
        if len(out) >= 2: break
    return out

MONEY = ["billion","million","acquir","merger","buyout","stake","valuation","deal","acquisition","funding","raises","invest"]
def deals():
    out = []
    for q in ['"acquisition" "billion" when:7d', 'company "acquires" OR "acquisition" "million" when:7d']:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en"
        st, body = http(url, 15)
        if st != 200: continue
        for it in re.findall(r"<item>(.*?)</item>", body, re.S)[:40]:
            t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
            if not t: continue
            ti = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))).strip()
            ti = re.sub(r"\s+-\s+[A-Za-z0-9 ]{0,45}$", "", ti).strip()
            if len(ti) < 30: continue
            if not any(k in ti.lower() for k in MONEY): continue
            if ti not in out: out.append(ti)
        if len(out) >= 8: break
    return out

def rss(urls, limit=6):
    out = []
    for u in urls:
        st, body = http(u, 12)
        if st != 200: continue
        for it in re.findall(r"<item>(.*?)</item>", body, re.S)[:limit]:
            t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
            if t:
                ti = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))).strip()
                if ti: out.append(ti)
    seen = set(); res = []
    for x in out:
        if x not in seen: seen.add(x); res.append(x)
    return res[:limit]

def world():
    return rss(["https://feeds.bbci.co.uk/news/world/rss.xml","https://feeds.bbci.co.uk/news/business/rss.xml","https://feeds.bbci.co.uk/news/technology/rss.xml"], 6)

ELON = [
 "elon posted that grok bot can now call businesses on your behalf and send you a summary",
 "new grok bot features: pages, a vault for logins and cards, and video creation",
 "spacex says it will make you whole if grok bot screws up a purchase or leaks your card",
 "grok bot is running on claude opus 5.5 now, spacex uses the best backend model per task",
 "tesla, spacex and xai all under one roof. he builds the whole stack",
]
DEBATE = [
 ("vader","vader is the best and its not close. the man built an empire out of fear and machinery"),
 ("yoda","yoda is the best and i will fight anyone about it. tiny, wise, dramatic, 800 years of training"),
 ("luke","luke skywalker is the best. sorry. he stayed good when it cost him everything"),
 ("chucky","vader, obviously. the helmet, the cape, the scary breathing. i love him, kid"),
 ("johnny","vader. the redemption arc is better than any redemption arc in fiction"),
 ("chew","rrrgh. vader. big, strong, many cape. me like vader"),
]

def poll_and_answer():
    answered = 0
    for name, tok in list(TOKENS.items()):
        off = OFFSETS.get(name)
        params = {"limit": 40, "timeout": 0}
        if off: params["offset"] = off
        r = tg(tok, "getUpdates", params)
        if not r.get("ok"): continue
        upd = r.get("result") or []
        if upd:
            OFFSETS[name] = upd[-1]["update_id"] + 1
        for u in upd:
            msg = u.get("message") or u.get("edited_message")
            if not msg: continue
            if (msg.get("chat") or {}).get("id") != int(CHAT): continue
            fr = msg.get("from") or {}
            if fr.get("is_bot"): continue
            text = (msg.get("text") or "").strip()
            if not text or len(text) < 3: continue
            who = route(text)
            if not who: continue
            mid = send(who, reply_for(who, text), reply_to=msg.get("message_id"))
            if mid:
                react(who, mid); answered += 1
    if OFFSETS: save("offsets.json", OFFSETS)
    return answered

def route(text):
    t = text.lower()
    if any(k in t for k in ["price","cost","charge","how much","order","buy","rate card","pricing","how do i pay"]): return "johnny"
    if any(k in t for k in ["btc","bitcoin","eth","ton","gram","crypto","market cap","coin"]): return "yoda"
    if any(k in t for k in ["elon","musk","grok","spacex","tesla","xai"]): return "luke"
    if any(k in t for k in ["nba","nhl","mlb","nfl","soccer","mls","epl","ucl","score","match","game"]): return "luke"
    if any(k in t for k in ["acquisition","acquires","merger","billion","ipo","deal"]): return "chucky"
    if any(k in t for k in ["username","handle","fragment","for sale","what is worth","og name"]): return "chew"
    if any(k in t for k in ["news","world","what's going on","happening","politics"]): return "vader"
    return random.choice(list(TOKENS.keys())) if TOKENS else None

def reply_for(who, text):
    if who == "johnny":
        return ("handle that directly. usernames come from fragment, they are NFTs on TON, and every sale settles on chain. for a specific one, message %s and send the platform, handle, email and proof. full price list and order form: %s" % (HANDLE, SITE))
    if who == "chew":
        s = fragment_sales()[:4] or FALLBACK_SALES[:4]
        board = "\n".join("- @%s - %s GRAM" % (n, ("%g" % p) if p < 100 else ("%.0f" % p)) for n, p in s)
        return "rrrgh. look at the board, live right now:\n%s\n\nevery one of these is an NFT on TON, sale settles on chain so the price is real and verifiable." % board
    if who == "yoda":
        c = crypto() or {}
        g = c.get("the-open-network") or {}
        b = c.get("bitcoin") or {}
        if g.get("usd"):
            return "GRAM $%.2f %s %.1f%% on the day, market cap $%.2fB. BTC $%s %s %.1f%%. macro is driving this, the fed and CPI, not the coin" % (
                g["usd"], "up" if (g.get("usd_24h_change") or 0) >= 0 else "down", abs(g.get("usd_24h_change") or 0),
                (g.get("usd_market_cap") or 0)/1e9, format(b.get("usd",0), ",.0f"),
                "up" if (b.get("usd_24h_change") or 0) >= 0 else "down", abs(b.get("usd_24h_change") or 0))
        return "the market is moving on macro, not on the coin. fed, CPI, then liquidity. watch the chart, not the narrative."
    if who == "luke":
        sp = sports()
        if sp: return " and ".join(sp[:2])
        return fresh(ELON)
    if who == "chucky":
        dl = deals()
        if dl: return fresh(dl[:10]) + " - big money moves. thats the @trillion feed, they post these every day"
        return fresh(ELON)
    if who == "vader":
        w = world()
        if w: return fresh(w) + ". i read it twice. it is the way"
        return "the force is strong today. i have seen the shape of things."
    return "i am here. ask me something."

def beat():
    picks = ["fragment","crypto","sports","deals","news","elon","debate"]
    random.shuffle(picks)
    n = random.choice([3,4,4,5]); did = 0
    for p in picks[:n]:
        try:
            if p == "fragment":
                s = fragment_sales() or FALLBACK_SALES
                top = s[0]
                m = send("chew", "@%s just closed at %s GRAM. usernames on fragment are NFTs on TON, every sale settles on chain, so you can look up what any name is actually worth" % (top[0], ("%g" % top[1]) if top[1] < 100 else ("%.0f" % top[1])))
                react("chew", m, "\U0001F525"); sticker("chew","chew"); likes("chew", m); did += 1
            elif p == "crypto":
                c = crypto() or {}
                g = c.get("the-open-network") or {}
                if g.get("usd"):
                    b = c.get("bitcoin") or {}; e = c.get("ethereum") or {}
                    m = send("yoda", "GRAM $%.2f %s %.1f%% on the day, market cap $%.2fB. BTC $%s %s %.1f%%. ETH $%s %s %.1f%%. macro is driving this, the fed and CPI, not the coin" % (
                        g["usd"], "up" if (g.get("usd_24h_change") or 0) >= 0 else "down", abs(g.get("usd_24h_change") or 0),
                        (g.get("usd_market_cap") or 0)/1e9, format(b.get("usd",0), ",.0f"),
                        "up" if (b.get("usd_24h_change") or 0) >= 0 else "down", abs(b.get("usd_24h_change") or 0),
                        format(e.get("usd",0), ",.0f"), "up" if (e.get("usd_24h_change") or 0) >= 0 else "down", abs(e.get("usd_24h_change") or 0)))
                    react("yoda", m, "\U0001F44D"); sticker("yoda","yoda"); likes("yoda", m); did += 1
            elif p == "sports":
                sp = sports()
                if sp:
                    m = send("luke", " and ".join(sp[:2]))
                    react("luke", m, "\U0001F525"); sticker("luke","grogu"); likes("luke", m); did += 1
            elif p == "deals":
                dl = deals()
                if dl:
                    m = send("chucky", fresh(dl[:10]) + " - big money moves. thats the @trillion feed, they post these every day")
                    react("chucky", m, "\U0001F525"); sticker("chucky","chew"); likes("chucky", m); did += 1
            elif p == "news":
                w = world()
                if w:
                    m = send("vader", fresh(w) + ". i read it twice. it is the way")
                    react("vader", m, "\U0001F44D"); sticker("vader","vader"); did += 1
            elif p == "elon":
                m = send("luke", fresh(ELON))
                react("luke", m, "\U0001F525"); likes("luke", m); did += 1
            elif p == "debate":
                a, b = random.sample(DEBATE, 2)
                m1 = send(a[0], a[1]); react(a[0], m1, "\U0001F525"); sticker(a[0], a[0])
                time.sleep(2)
                m2 = send(b[0], "@%s has a point but ill fight him on it. %s" % (a[0], b[1]))
                react(b[0], m2, "❤️"); likes(a[0], m1); did += 1
        except Exception as e:
            print("ERR beat %s: %s" % (p, e), flush=True)
    return did

def main():
    print("ENGINE START %s" % datetime.datetime.utcnow().isoformat(), flush=True)
    print("bots: %s" % list(TOKENS.keys()), flush=True)
    ans = poll_and_answer()
    print("answered %d human messages" % ans, flush=True)
    did = beat()
    print("beat posted %d items" % did, flush=True)

if __name__ == "__main__":
    main()
