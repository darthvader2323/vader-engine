#!/usr/bin/env python3
"""Publish validated video packs using an existing bot and the verified group owner."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
TOKEN = os.environ.get("TG_JOHNNY", "")


def call(method, fields=None, files=None, allow_missing=False):
    fields = fields or {}
    if files:
        boundary = "vader" + os.urandom(12).hex()
        chunks = []
        for key, value in fields.items():
            chunks.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" %
                           (boundary, key, value)).encode())
        for key, path in files.items():
            chunks.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                           "Content-Type: video/webm\r\n\r\n" % (boundary, key, path.name)).encode())
            chunks.append(path.read_bytes() + b"\r\n")
        chunks.append(("--%s--\r\n" % boundary).encode())
        body = b"".join(chunks)
        content_type = "multipart/form-data; boundary=" + boundary
    else:
        body = json.dumps(fields).encode()
        content_type = "application/json"
    request = urllib.request.Request("https://api.telegram.org/bot%s/%s" % (TOKEN, method),
                                     data=body, headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            result = json.loads(error.read())
        except (ValueError, OSError):
            raise SystemExit("%s failed: HTTP %s" % (method, error.code)) from None
    except (OSError, ValueError):
        raise SystemExit("%s delivery uncertain; stopped without automatically repeating the request" % method) from None
    if result.get("ok"):
        return result.get("result")
    description = str(result.get("description", "")).replace(TOKEN, "[token]")
    if result.get("error_code") == 429:
        retry = (result.get("parameters") or {}).get("retry_after", "unknown")
        raise SystemExit("Telegram cooldown during %s; retry_after=%s seconds. No more calls made." % (method, retry))
    if allow_missing and result.get("error_code") == 400 and "STICKERSET_INVALID" in description.upper():
        return None
    raise SystemExit("%s failed: %s" % (method, description))


def publish_pack(name, items, owner):
    """Append to existing packs; Telegram deduplicates identical sticker uploads.

    Never replace or delete old entries: their unique IDs are the runtime's
    permanent no-repeat keys. A failed/uncertain API request stops the run.
    """
    pack = call("getStickerSet", {"name": name}, allow_missing=True)
    previous = (pack or {}).get("stickers", [])
    if previous and (not all(s.get("is_video") for s in previous)
                     or len({s["file_unique_id"] for s in previous}) != len(previous)):
        raise SystemExit("Existing pack is not a unique video-only pack: " + name)
    previous_ids = {s["file_unique_id"] for s in previous}
    if not pack:
        files = {"video_%d" % i: HERE / "stickers" / item["file"] for i, item in enumerate(items)}
        stickers = [{"sticker": "attach://video_%d" % i, "format": "video",
                     "emoji_list": [item["emoji"]]} for i, item in enumerate(items)]
        call("createNewStickerSet", {"user_id": owner, "name": name,
                                    "title": items[0]["title"],
                                    "stickers": json.dumps(stickers, ensure_ascii=False),
                                    "sticker_type": "regular"}, files)
    else:
        for item in items:
            # addStickerToSet leaves the set unchanged for the exact same file.
            sticker = {"sticker": "attach://video", "format": "video",
                       "emoji_list": [item["emoji"]]}
            call("addStickerToSet", {"user_id": owner, "name": name,
                                    "sticker": json.dumps(sticker, ensure_ascii=False)},
                 {"video": HERE / "stickers" / item["file"]})
            time.sleep(1)
    pack = call("getStickerSet", {"name": name})
    videos = pack.get("stickers", [])
    ids = {s["file_unique_id"] for s in videos}
    if (len(videos) != len(items) or len(ids) != len(videos)
            or not all(s.get("is_video") for s in videos)
            or not previous_ids.issubset(ids)):
        raise SystemExit("Published pack failed append-only video verification: " + name)
    return pack, len(ids - previous_ids)


def main():
    if not TOKEN:
        raise SystemExit("Missing existing bot credential")
    entries = json.loads((HERE / "stickers/manifest.json").read_text())
    expected = json.loads((HERE / "stickers/validation.json").read_text())
    groups = {}
    for entry in entries:
        path = HERE / "stickers" / entry["file"]
        record = expected[entry["file"]]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise SystemExit("Asset checksum mismatch: " + entry["file"])
        if path.stat().st_size > 256 * 1024 or not 0 < record["seconds"] <= 3:
            raise SystemExit("Invalid video sticker: " + entry["file"])
        groups.setdefault(entry["character"], []).append(entry)
    identity = call("getMe")
    if not identity.get("is_bot") or not re.fullmatch(r"[A-Za-z0-9_]+", identity.get("username", "")):
        raise SystemExit("Existing credential is not a bot")
    chat = call("getChat", {"chat_id": os.environ.get("CHAT_HANDLE", "@darthvaderchat2")})
    if chat.get("title") != "Darth Vader Chat" or chat.get("username", "").casefold() != "darthvaderchat2":
        raise SystemExit("Public group did not match the authorized destination")
    admins = call("getChatAdministrators", {"chat_id": chat["id"]})
    owners = [a["user"]["id"] for a in admins if a.get("status") == "creator"
              and a.get("user", {}).get("username", "").casefold() == "darthvader"]
    if len(owners) != 1:
        raise SystemExit("Could not uniquely verify @darthvader as the group creator")
    print("Verified @darthvader as creator of @darthvaderchat2", flush=True)
    print("Public group numeric ID:", chat["id"], flush=True)
    packs = {}
    for character, items in groups.items():
        name = "vadersocial_%s_motion1_by_%s" % (character, identity["username"].lower())
        if len(name) > 64:
            raise SystemExit("Sticker set name exceeds Telegram length limit")
        pack, added = publish_pack(name, items, owners[0])
        videos = pack["stickers"]
        packs[character] = name
        print("VIDEO PACK %s verified=%d added=%d name=%s" %
              (character, len(videos), added, name), flush=True)
        time.sleep(2)
    (HERE / "stickers/packs.json").write_text(json.dumps(packs, indent=2) + "\n")
    print("STICKER_PACKS_JSON=" + json.dumps(packs, separators=(",", ":")), flush=True)
    print("Video sticker setup complete.", flush=True)


if __name__ == "__main__":
    main()
