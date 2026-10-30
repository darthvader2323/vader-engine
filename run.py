#!/usr/bin/env python3
"""Continuous living-room runner for Darth Vader Chat."""
import os, sys, time, random, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MINUTES = float(os.environ.get("RUN_MINUTES", "48"))
GAP_MIN = float(os.environ.get("GAP_MIN", "18"))
GAP_MAX = float(os.environ.get("GAP_MAX", "60"))
print("RUNNER START %s" % datetime.datetime.utcnow().isoformat(), flush=True)
try:
    import engine
except Exception as e:
    print("IMPORT FAIL: %s" % e, flush=True); raise
TOKENS = getattr(engine, "TOKENS", None) or getattr(engine, "TOK", {}) or {}
print("bots: %s" % list(TOKENS.keys()), flush=True)
if not TOKENS:
    print("NO TOKENS - check repository secrets", flush=True); raise SystemExit(2)
def tick():
    try:
        n = engine.answer_humans()
        if n: print("answered %d humans" % n, flush=True)
    except Exception as e:
        print("ANSWER ERR %s" % e, flush=True)
tick()
deadline = time.time() + MINUTES * 60
cycle = 0
while time.time() < deadline:
    cycle += 1
    try:
        b = engine.beat()
        print("cycle %d beats=%d" % (cycle, b), flush=True)
    except Exception as e:
        print("BEAT ERR %s" % e, flush=True)
    tick()
    time.sleep(random.uniform(GAP_MIN, GAP_MAX))
print("RUNNER DONE %d cycles" % cycle, flush=True)
