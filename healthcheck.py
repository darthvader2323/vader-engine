#!/usr/bin/env python3
"""Read-only checks: no posts, reactions, profile changes, or secret output."""
import engine

def main():
    if not engine.TOK:
        raise SystemExit("No configured bot tokens.")
    engine.resolve_chat()
    engine.load_managed_bots(for_profile_setup=True)
    for name, token in engine.TOK.items():
        result = engine.tg(token, "getMe")
        user = result.get("result") or {}
        print("BOT %s valid=%s username=%s manager=%s privacy_disabled=%s" %
              (name, bool(result.get("ok") and user.get("is_bot")), user.get("username", ""),
               bool(user.get("can_manage_bots")), bool(user.get("can_read_all_group_messages"))), flush=True)
    first = next(iter(engine.TOK.values()))
    chat = engine.tg(first, "getChat", {"chat_id": engine.CHAT})
    print("CHAT valid=%s title=%s" %
          (bool(chat.get("ok")), (chat.get("result") or {}).get("title", "")), flush=True)
    if not chat.get("ok"):
        raise SystemExit("Configured CHAT_ID is not accessible.")
    reader = engine.TOK.get("brucewayne") or first
    webhook = engine.tg(reader, "getWebhookInfo").get("result") or {}
    print("POLLING webhook_present=%s" % bool(webhook.get("url")), flush=True)
    for name, pack in engine.PACKS.items():
        result = engine.tg(first, "getStickerSet", {"name": pack})
        stickers = (result.get("result") or {}).get("stickers") or []
        moving = sum(bool(item.get("is_animated") or item.get("is_video")) for item in stickers)
        print("STICKERS %s total=%d moving=%d" % (name, len(stickers), moving), flush=True)
    for name in ("crypto", "world", "sports", "fragment", "elon", "deals", "youngboy"):
        try:
            count = len(getattr(engine, name)())
            print("FEED %s usable_records=%d" % (name, count), flush=True)
        except Exception as error:
            print("FEED %s error=%s" % (name, type(error).__name__), flush=True)

if __name__ == "__main__":
    main()
