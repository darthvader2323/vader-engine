#!/usr/bin/env python3
"""Continuous living-room runner for Darth Vader Chat."""
import os, sys, time, random, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MINUTES = float(os.environ.get("RUN_MINUTES", "48"))
GAP_MIN = float(os.environ.get("GAP_MIN", "18"))
GAP_MAX = float(os.environ.get("GAP_MAX", "60"))
print("RUNNER START %s" % datetime.datetime.utcnow().isoformat(), flush=True)
import engine
bots = list(engine.TOK.keys())
print("bots: %s" % bots, flush=True)
if not bots:
    print("NO TOKENS - check repository secrets", flush=True); raise SystemExit(2)
try: print("answered %d humans" % engine.answer_humans(), flush=True)
except Exception as e: print("ANSWER ERR %s" % e, flush=True)
deadline = time.time() + MINUTES * 60
cycle = 0
while time.time() < deadline:
    cycle += 1
    try: print("cycle %d beats=%d" % (cycle, engine.beat()), flush=True)
    except Exception as e: print("BEAT ERR %s" % e, flush=True)
    try: engine.answer_humans()
    except Exception as e: print("ANSWER ERR %s" % e, flush=True)
    time.sleep(random.uniform(GAP_MIN, GAP_MAX))
print("RUNNER DONE %d cycles" % cycle, flush=True)
