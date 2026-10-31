#!/usr/bin/env python3
"""Checkpoint only the bot ledger, without overwriting concurrent code changes."""
import base64
import json
import os
from pathlib import Path
import sys
import time
import uuid
import urllib.error
import urllib.request

MAPS = ("used", "replies", "stickers", "pins", "offsets", "last_spoke", "last_topic_at",
        "telegram_retry_until", "profile_retry_until", "greetings")
VERSIONED_MAPS = ("used", "replies", "stickers", "last_topic_at", "recent_content", "sticker_counts")


def apply_recovery(state, recovery):
    """Apply an audited hash-only recovery once, after loading the latest ledger."""
    identity = recovery.get("recovery_id")
    if not identity or identity in (state.get("ledger_recoveries") or {}):
        return False
    for field in ("used", "last_spoke", "last_topic_at"):
        target = state.setdefault(field, {})
        for key, value in (recovery.get(field) or {}).items():
            target[key] = max(target.get(key, 0), value)
    recent = state.setdefault("recent_content", {})
    for key, value in (recovery.get("recent_content") or {}).items():
        if value.get("at", 0) > recent.get(key, {}).get("at", 0):
            recent[key] = value
    state["scheduled_news_count"] = state.get("scheduled_news_count", 0) + recovery.get("scheduled_news_delta", 0)
    state.setdefault("ledger_recoveries", {})[identity] = recovery["observed_at"]
    return True


class CheckpointUnavailable(RuntimeError):
    """No delivery may follow an unconfirmed durable claim."""


def version_changes(state, previous, now):
    versions = state.setdefault("ledger_versions", {})
    now = max(now, max((stamp for values in versions.values() for stamp in values.values()),
                       default=0) + 0.000001, state.get("news_count_version", 0) + 0.000001)
    for field in VERSIONED_MAPS:
        before, after = previous.get(field) or {}, state.get(field) or {}
        changed = [key for key in set(before) | set(after)
                   if (key in before) != (key in after) or before.get(key) != after.get(key)]
        if changed:
            versions.setdefault(field, {}).update({key: now for key in changed})
    if state.get("scheduled_news_count", 0) != previous.get("scheduled_news_count", 0):
        state["news_count_version"] = now


def _stamp(value):
    if isinstance(value, dict):
        return value.get("at", 0)
    return value if isinstance(value, (int, float)) and value >= 1_000_000_000 else 0


def _merge_versioned(remote, local, field):
    rmap, lmap = remote.get(field) or {}, local.get(field) or {}
    rver = (remote.get("ledger_versions") or {}).get(field) or {}
    lver = (local.get("ledger_versions") or {}).get(field) or {}
    merged, versions = {}, {}
    for key in set(rmap) | set(lmap) | set(rver) | set(lver):
        rv, lv = rver.get(key, 0), lver.get(key, 0)
        if rv or lv:
            # Legacy checkpoints can add a later timestamped claim, but their
            # missing keys cannot undo an explicit newer rollback/tombstone.
            rv, lv = max(rv, _stamp(rmap.get(key))), max(lv, _stamp(lmap.get(key)))
            winner = lmap if lv >= rv else rmap
            if key in winner:
                merged[key] = winner[key]
            versions[key] = max(rv, lv)
        elif key not in rmap:
            merged[key] = lmap[key]
        elif key not in lmap:
            merged[key] = rmap[key]
        elif field == "recent_content":
            merged[key] = max((rmap[key], lmap[key]), key=_stamp)
        else:
            merged[key] = max(rmap[key], lmap[key])
    return merged, versions


def confirm_persist():
    directory = os.environ.get("VADER_CHECKPOINT_DIR")
    if not directory:
        return
    try:
        directory = Path(directory)
        request = uuid.uuid4().hex
        temporary = directory / "request.tmp"
        temporary.write_text(request)
        temporary.replace(directory / "request")
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            answer = (directory / "ack").read_text() if (directory / "ack").is_file() else ""
            if answer == "ok:" + request:
                return
            if answer == "failed:" + request:
                raise CheckpointUnavailable("Durable checkpoint was not confirmed; worker stopped before further delivery.")
            time.sleep(0.05)
        raise CheckpointUnavailable("Durable checkpoint confirmation timed out; worker stopped before further delivery.")
    except OSError as error:
        raise CheckpointUnavailable("Durable checkpoint unavailable; worker stopped before further delivery.") from error

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
    result["ledger_recoveries"] = dict(remote.get("ledger_recoveries") or {})
    result["ledger_recoveries"].update(local.get("ledger_recoveries") or {})
    result["ledger_versions"] = {}
    for field in VERSIONED_MAPS:
        result[field], result["ledger_versions"][field] = _merge_versioned(remote, local, field)
    result["recent_content"] = dict(sorted(result["recent_content"].items(),
        key=lambda item: item[1].get("at", 0), reverse=True)[:100])
    rv, lv = remote.get("news_count_version", 0), local.get("news_count_version", 0)
    if rv or lv:
        result["scheduled_news_count"] = (local if lv >= rv else remote).get("scheduled_news_count", 0)
        result["news_count_version"] = max(rv, lv)
    else:
        result["scheduled_news_count"] = max(remote.get("scheduled_news_count", 0),
                                             local.get("scheduled_news_count", 0))
    result["updated_at"] = max(remote.get("updated_at", 0), local.get("updated_at", 0))
    return result

def save_checkpoint():
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


def serve(directory, save=save_checkpoint, stop=None):
    """Only this narrow helper receives the existing repository credential."""
    directory = Path(directory)
    (directory / "ready").touch(mode=0o600)
    print("Durable ledger helper ready.", flush=True)
    previous = None
    while stop is None or not stop.is_set():
        path = directory / "request"
        request = path.read_text() if path.is_file() else ""
        if request and request != previous:
            try:
                save()
            except (Exception, SystemExit):
                print("Durable ledger save failed; delivery remains paused.", flush=True)
                answer = "failed:"
            else:
                answer = "ok:"
            temporary = directory / "ack.tmp"
            temporary.write_text(answer + request)
            temporary.replace(directory / "ack")
            previous = request
        time.sleep(0.05)


def main():
    if sys.argv[1:] == ["--serve"]:
        serve(os.environ["VADER_CHECKPOINT_DIR"])
    else:
        save_checkpoint()

if __name__ == "__main__":
    main()
