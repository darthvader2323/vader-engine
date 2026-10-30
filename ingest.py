#!/usr/bin/env python3
"""
INGEST NEW BOTS - one command, everything else automatic.

USAGE:
  python ingest.py tokens.txt

tokens.txt format - one per line, either:
    <Name> <bot_token>            e.g.  brucewayne  123456:ABC-DEF...
    <Name> <bot_token> <username> e.g.  brucewayne  123456:ABC-DEF  @brucewaynebot

WHAT IT DOES AUTOMATICALLY:
  1. verify the token with getMe
  2. setMyName        -> display name (e.g. "brucewayne")
  3. setMyDescription + setMyShortDescription -> Fragment TON NFT bio
  4. promote to ADMIN in the chat (using the admin bot token)
  5. upload profile photo from avatars/<name>.jpg if it exists
  6. add the bot to roster.json (env name, display, persona, pack)
  7. write the token into GitHub Actions secrets (TG_<NAME>)
  8. print a report

REQUIRED ENV:
  ADMIN_TOKEN   token of a bot that is already admin in the chat
  CHAT_ID       target chat id
  GITHUB_TOKEN  (optional) a PAT with repo scope, for step 7
"""
import sys, os, json, time, base64, urllib.request, urllib.parse, urllib.error, re

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.telegram.org/bot%s/%s"
CHAT = os.environ.get("CHAT_ID", "-1003758482841")
ADMIN = os.environ.get("ADMIN_TOKEN", "")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = os.environ.get("REPO_OWNER", "darthvader2323")
REPO  = os.environ.get("REPO_NAME", "vader-engine")
PACKS = ["vader","crew","grogu","yoda","luke","chew","han","boba","leia","r2d2"]

def tg(tok, method, params=None):
    if not tok: return {"ok": False, "description": "no token"}
    url = API % (tok, method)
    if params: url += "?" + urllib.parse.urlencode(params)
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try: return json.loads(e.read())
            except Exception: return {"ok": False, "description": "http error"}
        except Exception:
            time.sleep(3)
    return {"ok": False, "description": "timeout"}

def multipart(token, method, fields, files):
    b = "----ing%s" % int(time.time()*1000); parts=[]
    for k,v in fields.items():
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"%(b,k,v)).encode())
    for k,(fn,data) in files.items():
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: application/octet-stream\r\n\r\n"%(b,k,fn)).encode()+data+b"\r\n")
    parts.append(("--%s--\r\n"%b).encode())
    req=urllib.request.Request(API%(token,method),data=b"".join(parts),
        headers={"Content-Type":"multipart/form-data; boundary=%s"%b,"User-Agent":"Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: return {"ok":False}
    except Exception: return {"ok":False}

def set_photo(tok, name):
    p = os.path.join(HERE, "avatars", name + ".jpg")
    if not os.path.exists(p): return "no-photo"
    with open(p,"rb") as f: data=f.read()
    r = multipart(tok, "setMyProfilePhoto", {}, {"photo": (name+".jpg", data)})
    return "ok" if r.get("ok") else "fail"

def gh_secret(name, value):
    if not GH_TOKEN: return "no-pat"
    try:
        req=urllib.request.Request("https://api.github.com/repos/%s/%s/actions/secrets/%s"%(OWNER,REPO,name),
            headers={"Authorization":"Bearer "+GH_TOKEN,"Accept":"application/vnd.github+json"})
        pk=json.loads(urllib.request.urlopen(req,timeout=30).read())
        key=base64.b64decode(pk["key"]); kid=pk["key_id"]
        try:
            import nacl.public, nacl.encoding
            enc=base64.b64encode(nacl.public.SealedBox(nacl.public.PublicKey(key)).encrypt(value.encode())).decode()
        except Exception:
            return "no-nacl"
        body=json.dumps({"encrypted_value":enc,"key_id":kid}).encode()
        req=urllib.request.Request("https://api.github.com/repos/%s/%s/actions/secrets/%s"%(OWNER,REPO,name),
            data=body, method="PUT",
            headers={"Authorization":"Bearer "+GH_TOKEN,"Accept":"application/vnd.github+json","Content-Type":"application/json"})
        urllib.request.urlopen(req,timeout=30)
        return "ok"
    except Exception as e:
        return "err:%s"%str(e)[:40]

def roster_load():
    p=os.path.join(HERE,"roster.json")
    try:
        with open(p) as f: return json.load(f)
    except Exception: return []

def roster_save(r):
    p=os.path.join(HERE,"roster.json")
    with open(p,"w") as f: json.dump(r,f,indent=2)

def main():
    if len(sys.argv)<2:
        print("usage: python ingest.py tokens.txt"); return 1
    lines=[l.strip() for l in open(sys.argv[1]) if l.strip() and not l.strip().startswith("#")]
    roster=roster_load()
    have={b.get("name") for b in roster}
    report=[]
    for ln in lines:
        parts=ln.split()
        if len(parts)<2:
            report.append((parts[0] if parts else "?", "BAD LINE", "need name + token")); continue
        name=parts[0].lower(); tok=parts[1]; uname=parts[2] if len(parts)>2 else ""
        me=tg(tok,"getMe")
        if not me.get("ok"):
            report.append((name,"TOKEN-BAD",str(me.get("description"))[:50])); continue
        real=me["result"].get("username","")
        tg(tok,"setMyName",{"name":name})
        tg(tok,"setMyDescription",{"description":"%s is a Fragment TON NFT username. DM @darthvader to buy."%name})
        tg(tok,"setMyShortDescription",{"short_description":"%s - Fragment TON NFT username"%name})
        time.sleep(0.5)
        adm="-"
        if ADMIN:
            adm="ok" if tg(ADMIN,"promoteChatMember",{"chat_id":CHAT,"user_id":me["result"]["id"],
                "can_post_messages":"true","can_edit_messages":"true","can_delete_messages":"true",
                "can_manage_chat":"false","can_restrict_members":"false","can_invite_users":"true",
                "can_pin_messages":"true","can_promote_members":"false"}).get("ok") else "fail"
            time.sleep(0.5)
        photo=set_photo(tok,name)
        if name not in have:
            roster.append({"name":name,"display":name,"persona":name,
                "pack":PACKS[len(roster)%len(PACKS)],"env":"TG_"+name.upper(),
                "desks":["general"],"handle":"@%s"%name,"fragment":True})
        have.add(name)
        secret=gh_secret("TG_"+name.upper(), tok)
        report.append((name,"OK","@%s admin=%s photo=%s secret=%s"%(real,adm,photo,secret)))
        time.sleep(1.2)
    roster_save(roster)
    print("\n%-14s %-9s %s"%("BOT","STATUS","DETAIL"))
    print("-"*78)
    for r in report: print("%-14s %-9s %s"%r)
    print("\nroster.json now has %d bots"%len(roster))
    return 0

if __name__=="__main__":
    sys.exit(main())
