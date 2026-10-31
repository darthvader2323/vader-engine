#!/usr/bin/env python3
"""Supervise one poster and its isolated repository-ledger helper."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent


def child_environments(environment, directory):
    worker = dict(environment)
    worker.pop("GITHUB_TOKEN", None)
    worker.pop("GH_TOKEN", None)
    worker["VADER_CHECKPOINT_DIR"] = directory
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT",
               "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
               "GITHUB_TOKEN", "GITHUB_REPOSITORY", "STATE_BRANCH", "VADER_STATE_DIR"}
    ledger = {key: value for key, value in environment.items() if key in allowed}
    ledger["VADER_CHECKPOINT_DIR"] = directory
    return worker, ledger


def supervised():
    if not os.environ.get("GITHUB_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        raise SystemExit("Durable ledger configuration is incomplete; no posting worker started.")
    with tempfile.TemporaryDirectory(prefix="vader-ledger-") as directory:
        worker_env, ledger_env = child_environments(os.environ, directory)
        helper = subprocess.Popen([sys.executable, str(HERE / "checkpoint.py"), "--serve"],
                                  env=ledger_env, cwd=HERE)
        worker = None
        interrupted = False

        def stop(signum, _frame):
            nonlocal interrupted
            interrupted = True
            if worker is not None and worker.poll() is None:
                worker.send_signal(signum)

        previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            deadline = time.monotonic() + 10
            while not (Path(directory) / "ready").exists():
                if helper.poll() is not None or time.monotonic() >= deadline or interrupted:
                    raise SystemExit("Durable ledger helper did not start; no posting worker started.")
                time.sleep(0.05)
            if interrupted:
                return 0
            worker = subprocess.Popen([sys.executable, str(HERE / "engine.py")],
                                      env=worker_env, cwd=HERE)
            while worker.poll() is None:
                if helper.poll() is not None:
                    worker.terminate()
                    print("Ledger helper stopped; posting worker is stopping.", flush=True)
                    return 1
                time.sleep(0.1)
            return worker.returncode
        finally:
            if worker is not None and worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait()
            helper.terminate()
            try:
                helper.wait(timeout=3)
            except subprocess.TimeoutExpired:
                helper.kill()
                helper.wait()
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def main():
    if os.environ.get("VADER_DURABLE_CHECKPOINT") == "1":
        return supervised()
    from engine import main as worker_main
    worker_main()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
