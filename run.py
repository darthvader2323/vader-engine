#!/usr/bin/env python3
"""Continuous living-room runner. Kept as a separate file so the workflow YAML
never has to carry inline python with nested quotes."""
import os, sys, time, random, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MINUTES = float(os.environ.get("RUN_MINUTES", "48"))
GAP_MIN = float(os.environ.get("GAP_MIN", "20"))
GAP_MAX = float(os.environ.get("GAP_MAX", "65"))

print("RUNNER START %s" % datetime.datetime.utcnow().isoformat(), flush=True)

try:
    import engine
except Exception as e:
    print("IMPORT FAIL: %s" % e, flush=True)
    raise

print("bots: %s" % list(engine.TOKENS.keys()), flush=True)
if not engine.TOKENS:
    print("NO TOKENS - check repository secrets", flush=True)
    raise SystemExit(2)

try:
    n = engine.answer_humans()
    print("answered %d humans" % n, flush=True)
except Exception as e:
    print("ANSWER ERR %s" % e, flush=True)

deadline = time.time() + MINUTES * 60
cycle = 0
while time.time() < deadline:
    cycle += 1
    try:
        b = engine.beat()
        print("cycle %d beats=%d" % (cycle, b), flush=True)
    except Exception as e:
        print("BEAT ERR %s" % e, flush=True)
    try:
        engine.answer_humans()
    except Exception as e:
        print("ANSWER ERR %s" % e, flush=True)
    time.sleep(random.uniform(GAP_MIN, GAP_MAX))

print("RUNNER DONE %d cycles" % cycle, flush=True)
