#!/usr/bin/env python3
"""Checkpoint only the bot ledger, without overwriting concurrent code changes."""
import base64
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

MAPS = ("used", "replies", "stickers", "pins", "offsets", "last_spoke", "last_topic_at",
        "telegram_retry_until", "profile_retry_until")

def merge_state(remote, local):
    newer = local if local.get("updated_at", 0) >= remote.get("updated_at", 0) else remote
    result = dict(newer)
    for field in MAPS:
        merged = dict(remote.get(field) or {})
        for key, value in (local.get(field) or {}).items():
            merged[key] = max(value, merged.get(key, value))
        result[field] = merged
    older = remote if newer is local else local
    result["profiles"] = dict(older.get("profiles") or {})
    result["profiles"].update(newer.get("profiles") or {})
    result["sticker_counts"] = {
        key: max((remote.get("sticker_counts") or {}).get(key, 0),
                 (local.get("sticker_counts") or {}).get(key, 0))
        for key in set(remote.get("sticker_counts") or {}) | set(local.get("sticker_counts") or {})
    }
    recent = {}
    for history in (remote.get("recent_content"), local.get("recent_content")):
        for key, record in (history or {}).items():
            if isinstance(record, dict) and record.get("at", 0) >= recent.get(key, {}).get("at", 0):
                recent[key] = record
    result["recent_content"] = dict(sorted(recent.items(), key=lambda item: item[1].get("at", 0), reverse=True)[:100])
    result["scheduled_news_count"] = max(remote.get("scheduled_news_count", 0),
                                         local.get("scheduled_news_count", 0))
    result["updated_at"] = max(remote.get("updated_at", 0), local.get("updated_at", 0))
    return result

def main():
    path = Path(os.environ.get("VADER_STATE_DIR", "state")) / "runtime.json"
    if not path.is_file():
        print("No new runtime ledger to checkpoint.", flush=True)
        return
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("STATE_BRANCH", "main")
    url = "https://api.github.com/repos/%s/contents/state/runtime.json" % repository
    headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}
    local = json.loads(path.read_text())
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url + "?ref=" + branch, headers=headers),
                                        timeout=20) as response:
                current = json.load(response)
            remote = json.loads(base64.b64decode(current["content"]))
            sha = current["sha"]
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise SystemExit("Checkpoint read failed: HTTP %s" % error.code)
            remote, sha = {}, None
        merged = merge_state(remote, local)
        encoded = base64.b64encode((json.dumps(merged, sort_keys=True, indent=2) + "\n").encode()).decode()
        if sha and current.get("content", "").replace("\n", "") == encoded:
            print("Runtime ledger already current.", flush=True)
            return
        payload = {"message": "Checkpoint bot ledger [skip ci]", "content": encoded, "branch": branch}
        if sha:
            payload["sha"] = sha
        request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(request, timeout=20):
                pass
            print("Runtime ledger checkpoint saved.", flush=True)
            return
        except urllib.error.HTTPError as error:
            if error.code not in (409, 422):
                raise SystemExit("Checkpoint write failed: HTTP %s" % error.code)
            time.sleep(attempt + 1)
    raise SystemExit("Checkpoint conflicted repeatedly; no remote code or state was overwritten.")

if __name__ == "__main__":
    main()
