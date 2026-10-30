#!/usr/bin/env python3
"""Darth Vader room engine - 24/7 persona ensemble for Darth Vader Chat."""
import os, json, time, random, re, html, datetime, urllib.request, urllib.parse, urllib.error

CHAT = os.environ.get("CHAT_ID", "-1003758482841")
SITE = os.environ.get("SITE_URL", "https://vader-social-ppulq7yo.agent.mira.tg")
HANDLE = "@darthvader"
TRILLION = "@trillion"
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "330"))

TOKENS = {}
for k, v in os.environ.items():
    if k.startswith("TG_") and v.strip():
        TOKENS[k[3:].lower()] = v.strip()
if not TOKENS:
    print("NO TOKENS", flush=True); raise SystemExit(1)

STICKER_PACKS = {
 "vader":"sqrjt9fkvvztb_by_mira","grogu":"sklrpz7196ebn_by_mira","yoda":"sikulkj1ywb7r_by_mira",
 "luke":"sry4d8ta1gu6s_by_mira","chew":"s15l72qep9gk0_by_mira","han":"sroftq1uflv8l_by_mira",
 "boba":"sryfojcw0mm1l_by_mira","leia":"s7zg12s696kiy_by_mira","r2d2":"st6ibqn4fjj0a_by_mira",
 "crew":"s9s9rvajkf1ti_by_mira"}

CHAR = {
 "johnny":("Johnny","broker","johnny"),"yoda":("Yoda","yoda","yoda"),"luke":("Luke","earnest","luke"),
 "chew":("Chewbacca","grunt","chew"),"chucky":("Chucky","kid","crew"),"vader":("Darth Vader","vader","vader"),
 "brucewayne":("Batman","brooder","vader"),"killer":("The Killer","cold","boba"),"assassin":("The Assassin","cold","boba"),
 "hitman":("The Hitman","cold","han"),"gangsta":("Gangsta","brooder","han"),"tonysoprano":("Tony Soprano","broker","han"),
 "peterparker":("Peter Parker","earnest","grogu"),"jacksparrow":("Jack Sparrow","charming","leia"),
 "dexter":("Dexter","cold","r2d2"),"johnwick":("John Wick","cold","boba"),"murder":("Murder","cold","boba"),
 "ghost":("Ghost","cold","r2d2"),"devil":("The Devil","vader","vader"),"demon":("Demon","vader","vader"),
 "hacker":("Hacker","charming","r2d2"),"michaelmyers":("Michael Myers","cold","r2d2"),
 "misaamane":("Misaamane","charming","leia"),"harleyquinn":("Harley Quinn","kid","crew"),
 "slaughter":("Slaughter","cold","boba"),"exclusive":("Exclusive","broker","crew"),
 "freddykrueger":("Freddy Krueger","vader","vader"),"chewbacca":("Chewbacca","grunt","chew"),
 "lukeskywalker":("Luke Skywalker","earnest","luke")}

VOICE = {
 "broker":{"op":["straight up","hand that","my guy","look","quick one","honestly"],
  "cl":["DM "+HANDLE+", he will sort it","orders go through "+HANDLE,"hit "+HANDLE+" with the details",
   "deal closes via "+HANDLE,"talk to "+HANDLE+" for pricing","send it to "+HANDLE+", he handles the order"]},
 "yoda":{"op":["mmm","hmm","yes, yes","oh","ah","i see"],
  "cl":["watch the chart, not the narrative","macro decides, not the coin","patience, padawan",
   "the numbers are the teacher","liquidity is the whole game"]},
 "earnest":{"op":["honestly","ok so","good question","right then","yeah so","well"],
  "cl":["i checked it live","worth a look","hope that helps","happy to dig in","that tracks"]},
 "grunt":{"op":["rrrgh","rrrgh!","hrrr","rrrgh rrrgh"],
  "cl":["me like it","very loud, yes","no noise","good","rrrgh yes"]},
 "kid":{"op":["ooh","heh","okay so","listen kid","aww","hey"],
  "cl":["candy later, deal?","i will wait, not long","that is the good stuff","mwahaha","ooh nice"]},
 "cold":{"op":["","","","","",""],"cl":["","","","","",""]},
 "brooder":{"op":["","","","","",""],"cl":["","","","","",""]},
 "vader":{"op":["i have seen","the force is","listen carefully","there is no escape","my son"],
  "cl":["it is the way","do not be afraid","this is inevitable","the situation is as it should be",
   "i find your lack of faith disturbing"]},
 "charming":{"op":["aye","well now","friend","see here","matey","right"],
  "cl":["no worries","that is the way of it","fair enough","cheers","easy now"]}}

def pname(k): return CHAR.get(k,(k.title(),"charming","crew"))[0]
def pvoice(k): return CHAR.get(k,(k.title(),"charming","crew"))[1]
def ppack(k): return CHAR.get(k,(k.title(),"charming","crew"))[2]

def tg(tok, method, params=None):
    url = "https://api.telegram.org/bot%s/%s" % (tok, method)
    if params: url += "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: return {"ok":False}
    except Exception: return {"ok":False}

def http(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8","ignore")
    except Exception: return "ERR",""

def jget(url, timeout=15):
    st,b = http(url,timeout)
    if st != 200: return None
    try: return json.loads(b)
    except Exception: return None

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.environ.get("STATE_DIR") or os.path.join(HERE,"state")
os.makedirs(STATE_DIR, exist_ok=True)

def load(name, default):
    try:
        with open(os.path.join(STATE_DIR,name)) as f: return json.load(f)
    except Exception: return default

def save(name,obj):
    try:
        p = os.path.join(STATE_DIR,name); t = p+".tmp"
        with open(t,"w") as f: json.dump(obj,f)
        os.replace(t,p)
    except Exception as e: print("SAVE ERR %s: %s"%(name,e),flush=True)

USED_REPLIES = set(load("used_replies.json",[]))
USED_LIKES = set(load("used_likes.json",[]))
STK_USED = set(load("stk_used.json",[]))
SEEN_MSGS = set(load("seen_msgs.json",[]))
OFFSET = load("offset.json",0)
START = time.time()

def fresh(pool, ledger=None):
    if not pool: return None
    if ledger is USED_REPLIES: cands=[p for p in pool if p not in USED_REPLIES]
    elif ledger is USED_LIKES: cands=[p for p in pool if p not in USED_LIKES]
    else: cands=list(pool)
    pick = random.choice(cands) if cands else random.choice(pool)
    if ledger is USED_REPLIES:
        USED_REPLIES.add(pick); save("used_replies.json", list(USED_REPLIES)[-900:])
    elif ledger is USED_LIKES:
        USED_LIKES.add(pick); save("used_likes.json", list(USED_LIKES)[-400:])
    return pick

def send(who, text, reply_to=None):
    tok = TOKENS.get(who)
    if not tok: return 0
    p = {"chat_id":CHAT,"text":text,"disable_web_page_preview":"true"}
    if reply_to: p["reply_to_message_id"] = reply_to
    r = tg(tok,"sendMessage",p)
    mid = (r.get("result") or {}).get("message_id") if r.get("ok") else 0
    if mid: print("SEND %-12s %-6s %s"%(who,mid,text[:80]),flush=True)
    time.sleep(1.2)
    return mid or 0

def react(who, mid, emoji=None):
    if not mid: return
    tok = TOKENS.get(who)
    if not tok: return
    em = emoji or random.choice(["\U0001F525","\U0001F44D","\U0001F44F","❤️","\U0001F602","\U0001F389",
   "\U0001F92E","\U0001F643","\U0001F440","\U0001F622","\U0001F44C","\U0001F64F"])
    tg(tok,"setMessageReaction",{"chat_id":CHAT,"message_id":mid,
   "reaction":json.dumps([{"type":"emoji","emoji":em}])})
    time.sleep(0.35)

def sticker(who, pack=None):
    pk = pack or ppack(who)
    if pk not in STICKER_PACKS: return
    tok = TOKENS.get("johnny") or list(TOKENS.values())[0]
    r = tg(tok,"getStickerSet",{"name":STICKER_PACKS[pk]})
    if not r.get("ok"): return
    ids=[s["file_id"] for s in r["result"]["stickers"] if s["file_id"] not in STK_USED]
    if not ids:
        STK_USED.clear(); save("stk_used.json",[])
        ids=[s["file_id"] for s in r["result"]["stickers"]]
    if not ids: return
    fid=random.choice(ids)
    res=tg(TOKENS.get(who) or tok,"sendSticker",{"chat_id":CHAT,"sticker":fid})
    if res.get("ok"):
        STK_USED.add(fid); save("stk_used.json", list(STK_USED))
        print("STICKER %-12s %s"%(who,pk),flush=True)
    time.sleep(1.0)

LIKE_POOL=["fair point","true","agreed","this one","good call","yeah","no doubt","exactly","right on",
"strong take","same","true that","noted","sounds right","solid","yeah that tracks","good point","i feel that",
"cant argue with that","facts","accurate","yep","makes sense","for sure","no complaints","well said",
"read that again","nailed it","clean","big if true","take a bow"]

def fragment_sales():
    d=jget("https://namespace.my/api/sales?limit=200"); out=[]
    if d:
        arr=d.get("sales") or (d.get("data") or {}).get("sales") or []
        for x in arr:
            n=(x.get("name") or x.get("username") or "").lstrip("@")
            try: p=float(x.get("price") or 0)
            except Exception: p=0
            if n: out.append((n,p))
        out.sort(key=lambda z: z[1], reverse=True)
    return out

FALLBACK=[("danbao",1583948),("news",994000),("auto",900000),("+8888222",520000),
("polymarket",354900),("doge",350000),("trauma",134669),("bocai",118888),("human",86666)]

def fmtp(p): return ("%g"%p) if p<100 else ("%.0f"%p)

def crypto():
    return jget("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network,bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")

LEAGUES=[("basketball/nba","NBA"),("basketball/wnba","WNBA"),("hockey/nhl","NHL"),
("baseball/mlb","MLB"),("football/nfl","NFL"),("soccer/usa.1","MLS"),
("soccer/eng.1","EPL"),("soccer/uefa.champions","UCL")]

def sports():
    out=[]
    for path,name in LEAGUES:
        d=jget("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard"%path,9)
        if not d: continue
        for ev in (d.get("events") or [])[:2]:
            c=(ev.get("competitions") or [{}])[0]; cs=c.get("competitors") or []
            if len(cs)<2: continue
            h=next((x for x in cs if x.get("homeAway")=="home"),cs[0])
            a=next((x for x in cs if x.get("homeAway")=="away"),cs[1])
            out.append("%s: %s %s - %s %s"%(name,h["team"]["displayName"],h.get("score",""),
        a.get("score",""),a["team"]["displayName"]))
        if len(out)>=3: break
    return out

MONEY=["billion","million","acquir","merger","buyout","stake","valuation","deal","acquisition","funding","raises","invest","ipo"]
SOURCE=re.compile(r"\s+-\s+[A-Za-z0-9 .]{0,45}$")

def deals():
    out=[]
    for q in ['"acquisition" "billion" when:7d','company "acquires" "million" when:7d','"buys" "billion" when:7d','"stake" "million" when:7d']:
        st,body=http("https://news.google.com/rss/search?q="+urllib.parse.quote(q)+"&hl=en-US&gl=US&ceid=US:en",15)
        if st!=200: continue
        for it in re.findall(r"<item>(.*?)</item>",body,re.S)[:40]:
            t=re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",it,re.S)
            if not t: continue
            ti=html.unescape(re.sub(r"<!\[CDATA\[|\]\]>","",t.group(1))).strip()
            ti=SOURCE.sub("",ti).strip()
            if len(ti)<30: continue
            if not any(k in ti.lower() for k in MONEY): continue
            if ti not in out: out.append(ti)
        if len(out)>=12: break
    return out

def rss(urls,limit=8):
    out=[]
    for u in urls:
        st,body=http(u,12)
        if st!=200: continue
        for it in re.findall(r"<item>(.*?)</item>",body,re.S)[:limit]:
            t=re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",it,re.S)
            if t:
                ti=html.unescape(re.sub(r"<!\[CDATA\[|\]\]>","",t.group(1))).strip()
                if ti and ti not in out: out.append(ti)
    return out[:limit]

def world():
    return rss(["https://feeds.bbci.co.uk/news/world/rss.xml",
 "https://feeds.bbci.co.uk/news/business/rss.xml",
 "https://feeds.bbci.co.uk/news/technology/rss.xml"],8)

ELON=["elon says grok bot can now call businesses on your behalf and send you a summary of the call",
"new grok bot features: pages, a vault for logins and cards, and video creation",
"spacex says it will make you whole if grok bot screws up a purchase or leaks your card",
"grok bot is running on claude opus 5.5 now, spacex uses the best backend model per task",
"tesla, spacex and xai all under one roof. he builds the whole stack",
"xai is shipping models faster than anyone can audit them, which is either genius or a countdown",
"grok just got an agent that does the boring part of running a business. no one is ready"]

DEBATE_LINES=[
("vader","vader is the best and it is not close. the man built an empire out of fear and machinery, and the redemption arc is better than any redemption arc in fiction"),
("yoda","yoda is the best and i will fight anyone about it. tiny, wise, dramatic, eight hundred years of training and a lightsaber he does not need"),
("luke","luke skywalker is the best. sorry. he stayed good when staying good cost him everything, and he did it twice"),
("chucky","vader, obviously. the helmet, the cape, the scary breathing, and the redemption. i love him, kid"),
("johnny","vader. everyone says anakin was the best until they actually sat through all three trilogies"),
("chew","rrrgh. vader. big, strong, many cape, heavy breathing. me like vader very much"),
("brucewayne","batman wins and it is not a debate. no superpowers, all grit, forty years of doing the hard thing every single night"),
("dexter","dexter morgan. the ice truck killer who became a serial killer who became something else entirely. the character study is unmatched"),
("johnwick","john wick. the most efficient action character ever written and the only one who made retirement look sad"),
("jacksparrow","jack sparrow. captain of the black pearl, best friend of a talking parrot, and the only pirate you actually root for"),
("tonysoprano","tony soprano. therapy, murder, and a garage. that is a complete character"),
("peterparker","peter parker. builds the suit out of nothing, misses every date, and saves the city anyway. the guilt is the whole point")]

def decorate(who, core):
    v=VOICE.get(pvoice(who),VOICE["charming"])
    op=random.choice(v["op"]).strip(); cl=random.choice(v["cl"]).strip()
    return " ".join(p for p in (op,core,cl) if p)

def core_fragment():
    s=fragment_sales() or FALLBACK; top=s[0]
    return "@%s just closed at %s GRAM. usernames on fragment are NFTs on TON and every sale settles on chain, so the price is real and anyone can look it up"%(top[0],fmtp(top[1]))

def core_crypto():
    c=crypto() or {}; g=c.get("the-open-network") or {}; b=c.get("bitcoin") or {}; e=c.get("ethereum") or {}
    if not g.get("usd"): return "the market is moving on macro, not on the coin. fed, CPI, then liquidity. watch the chart, not the narrative"
    def d(x): return ("up %.1f%%"%x) if x>=0 else ("down %.1f%%"%abs(x))
    return "GRAM $%.2f %s on the day, market cap $%.2fB. BTC $%s %s. ETH $%s %s"%(
 g["usd"],d(g.get("usd_24h_change") or 0),(g.get("usd_market_cap") or 0)/1e9,
 format(b.get("usd",0),",.0f"),d(b.get("usd_24h_change") or 0),
 format(e.get("usd",0),",.0f"),d(e.get("usd_24h_change") or 0))

def core_sports():
    sp=sports()
    if not sp: return "no scoreboard came back clean. the servers are being weird, i will check again"
    return " and ".join(sp[:3])

def core_deals():
    dl=deals()
    if not dl: return "no big money moves on the wire right now, i am watching the M and A feed all day"
    return fresh(dl[:14])+" - that is straight off the %s feed. they post these every single day"%TRILLION

def core_world():
    w=world()
    if not w: return "the wires are quiet. nothing worth reporting yet"
    return fresh(w)+" - i read it twice"

def core_elon(): return fresh(ELON)

def core_trillion():
    dl=deals()
    if not dl: return "follow %s for the money moves, they post the biggest deals every day. the man who runs %s built this whole thing"%(TRILLION,HANDLE)
    return fresh(dl[:14])+" - that is %s posting. biggest deals, every day. same person behind %s built all of this"%(TRILLION,HANDLE)

TOPIC_ROUTES=[
 (["price","cost","charge","how much","order","buy ","pricing","rate card","how do i pay","quote","payment","discount"],
  "johnny",lambda:"handle that directly. usernames come from fragment, they are NFTs on TON, and every sale settles on chain. for a specific one, message %s and send the platform, handle, email and proof. full price list and order form: %s"%(HANDLE,SITE)),
 (["btc","bitcoin","eth ","ethereum","ton ","gram","crypto","coin","market cap","solana","xrp","doge"],
  "yoda",core_crypto),
 (["elon","musk","grok","spacex","tesla","xai","starlink"],"luke",core_elon),
 (["nba","wnba","nhl","mlb","nfl","soccer","mls","epl","ucl","score","scores","match","game","games","league","playoffs","final"],
  "luke",core_sports),
 (["acquisition","acquires","merger","billion","ipo","buyout","deal","valuation","stake","trillion","bought","sells"],
  "chucky",core_deals),
 (["username","handle","fragment","for sale","og name","og username","telegram name"],"chew",core_fragment),
 (["news","world","what is going on","happening","politics","war","ukraine","gaza","election"],"vader",core_world)]

def route(text):
    t=text.lower()
    for keys,who,maker in TOPIC_ROUTES:
        for k in keys:
            if k in t: return who,maker
    return None,None

def reply_to_human(who,text,maker):
    core=maker() if maker else None
    if core is None:
        core=fresh(["i am here. what do you need","you called. speak","listening, go ahead",
 "ask away, i have got time","sure, what is it"])
        return core
    return decorate(who,core)

# ---------------- human replies + reactions ----------------
def poll_and_answer():
    global OFFSET
    answered=0
    tok=TOKENS.get("johnny") or list(TOKENS.values())[0]
    params={"limit":60,"timeout":0}
    if OFFSET: params["offset"]=OFFSET
    r=tg(tok,"getUpdates",params)
    if not r.get("ok"): return 0
    upd=r.get("result") or []
    if upd: OFFSET=upd[-1]["update_id"]+1
    for u in upd:
        msg=u.get("message") or u.get("edited_message")
        if not msg: continue
        if (msg.get("chat") or {}).get("id")!=int(CHAT): continue
        fr=msg.get("from") or {}
        if fr.get("is_bot"): continue
        mid=msg.get("message_id")
        if mid in SEEN_MSGS: continue
        SEEN_MSGS.add(mid)
        text=(msg.get("text") or "").strip()
        if not text or len(text)<3: continue
        who,maker=route(text)
        if not who: who=random.choice(list(TOKENS.keys()))
        body=reply_to_human(who,text,maker)
        sent=send(who,body,reply_to=mid)
        if sent:
            react(who,sent)
            maybe_like(who,sent)
            answered+=1
        if answered>=6: break
    save("seen_msgs.json",list(SEEN_MSGS)[-800:])
    save("offset.json",OFFSET)
    print("STATE offset=%s seen=%d answered=%d"%(OFFSET,len(SEEN_MSGS),answered),flush=True)
    return answered

def maybe_like(target, mid, force=None):
    """Sometimes one person likes it, sometimes everyone does. Mix it."""
    if not mid: return
    others=[b for b in TOKENS if b!=target]
    if not others: return
    n=force if force is not None else random.choice([0,1,1,1,2,2,3,4,len(others)])
    n=min(n,len(others))
    if n<=0: return
    for b in random.sample(others,n):
        tok=TOKENS.get(b)
        if not tok: continue
        txt=fresh(LIKE_POOL,USED_LIKES)
        if not txt: continue
        r=tg(tok,"sendMessage",{"chat_id":CHAT,"text":txt,"reply_to_message_id":mid,
            "disable_web_page_preview":"true"})
        rid=(r.get("result") or {}).get("message_id") if r.get("ok") else 0
        if rid:
            react(b,rid,random.choice(["\U0001F44D","❤️","\U0001F525","\U0001F44F","\U0001F602"]))
            print("LIKE %-12s -> %s"%(b,mid),flush=True)
        time.sleep(0.9)

# ---------------- beats ----------------
def beat():
    did=0
    topics=["fragment","crypto","sports","deals","world","elon","trillion","debate","sticker"]
    random.shuffle(topics)
    n=random.choice([3,4,4,5])
    for t in topics[:n]:
        try:
            if t=="fragment":
                who="chew"; body=decorate(who,core_fragment())
                m=send(who,body); react(who,m,"\U0001F525"); sticker(who); maybe_like(who,m); did+=1
            elif t=="crypto":
                who="yoda"; body=decorate(who,core_crypto())
                m=send(who,body); react(who,m,"\U0001F44D"); sticker(who,"yoda"); maybe_like(who,m); did+=1
            elif t=="sports":
                who="luke"; body=decorate(who,core_sports())
                m=send(who,body); react(who,m,"\U0001F525"); sticker(who,"grogu"); maybe_like(who,m); did+=1
            elif t=="deals":
                who="chucky"; body=decorate(who,core_deals())
                m=send(who,body); react(who,m,"\U0001F525"); sticker(who,"crew"); maybe_like(who,m); did+=1
            elif t=="world":
                who="vader"; body=decorate(who,core_world())
                m=send(who,body); react(who,m,"\U0001F44F"); sticker(who,"vader"); did+=1
            elif t=="elon":
                who="luke"; body=decorate(who,core_elon())
                m=send(who,body); react(who,m,"\U0001F525"); maybe_like(who,m); did+=1
            elif t=="trillion":
                who=random.choice(["johnny","tonysoprano","exclusive","chucky"] if any(k in TOKENS for k in ["johnny","tonysoprano","exclusive","chucky"]) else ["chucky"])
                body=decorate(who,core_trillion())
                m=send(who,body); react(who,m,"\U0001F525"); maybe_like(who,m); did+=1
            elif t=="debate":
                a,b=random.sample(DEBATE_LINES,2)
                m1=send(a[0],a[1]); react(a[0],m1,"\U0001F525"); sticker(a[0])
                time.sleep(1.5)
                counter=["no shot","that is wrong and i will die on it","disagree, and here is why",
  "not even close","you are wrong, i say so with respect","have to disagree",
  "that take is weak","nah","i disagree","wrong","you lost me","overrated"]
                body=decorate(b[0], random.choice(counter)+". "+b[1])
                m2=send(b[0],body,reply_to=m1); react(b[0],m2,"❤️")
                maybe_like(b[0],m2); did+=1
            elif t=="sticker":
                who=random.choice(list(TOKENS.keys()))
                sticker(who); did+=1
        except Exception as ex:
            print("ERR beat %s: %s"%(t,ex),flush=True)
    return did

def loop_once():
    print("--- loop tick %s ---"%datetime.datetime.utcnow().isoformat(),flush=True)
    a=poll_and_answer()
    b=beat()
    print("tick done answered=%d beats=%d"%(a,b),flush=True)

def main():
    print("ENGINE START %s bots=%s"%(datetime.datetime.utcnow().isoformat(),list(TOKENS.keys())),flush=True)
    while True:
        try:
            loop_once()
        except Exception as ex:
            print("LOOP ERR %s"%ex,flush=True)
        elapsed=time.time()-START
        if elapsed>RUN_SECONDS:
            print("run window done at %ds"%elapsed,flush=True)
            return
        time.sleep(random.uniform(25,70))

if __name__=="__main__":
    main()
