#!/usr/bin/env python3
"""Upload profile photos for every roster bot. Runs on the GitHub runner so the
upload path is not mangled by any proxy. Telegram wants multipart field
photo=<file> plus type=static; the JSON form is used as a fallback."""
import os, json, sys, time, requests

HERE = os.path.dirname(os.path.abspath(__file__))
CID = os.environ.get("TG_CHAT_ID", "-1003758482841")
API = "https://api.telegram.org/bot%s/%s"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0"})

def load_roster():
    with open(os.path.join(HERE, "roster.json")) as f:
        return json.load(f)

def roster_tokens(roster):
    out = {}
    for b in roster:
        t = os.environ.get(b.get("env", ""), "")
        if t:
            out[b["name"]] = t
    return out

def set_photo(name, token, path):
    if not os.path.exists(path):
        return "no-file"
    # method 1: multipart file + type field
    try:
        with open(path, "rb") as fh:
            r = S.post(API % (token, "setMyProfilePhoto"),
                       data={"type": "static"},
                       files={"photo": (os.path.basename(path), fh, "image/jpeg")},
                       timeout=120)
        j = r.json()
        if j.get("ok"):
            return "OK"
        err1 = str(j.get("description"))[:90]
    except Exception as e:
        err1 = "multipart-exc:" + str(e)[:60]
    # method 2: upload to get file_id, then JSON body
    try:
        with open(path, "rb") as fh:
            r = S.post(API % (token, "sendPhoto"),
                       params={"chat_id": CID, "caption": "."},
                       files={"photo": (os.path.basename(path), fh, "image/jpeg")},
                       timeout=120)
        j = r.json()
        if not j.get("ok"):
            return "upload-fail:" + str(j.get("description"))[:70]
        fid = j["result"]["photo"][-1]["file_id"]
        mid = j["result"]["message_id"]
        r = S.post(API % (token, "setMyProfilePhoto"),
                   json={"type": "static", "photo": fid}, timeout=120)
        j2 = r.json()
        S.post(API % (token, "deleteMessage"), params={"chat_id": CID, "message_id": mid}, timeout=30)
        if j2.get("ok"):
            return "OK(json)"
        return "json-fail:" + str(j2.get("description"))[:70]
    except Exception as e:
        return "exc:" + str(e)[:60]

def main():
    roster = load_roster()
    toks = roster_tokens(roster)
    print("avatars.py: %d roster entries, %d tokens" % (len(roster), len(toks)), flush=True)
    for name, tok in toks.items():
        path = os.path.join(HERE, "avatars", name + ".jpg")
        res = set_photo(name, tok, path)
        print("  %-16s %s" % (name, res), flush=True)
        time.sleep(1.5)
    print("avatars.py: done", flush=True)

if __name__ == "__main__":
    main()
