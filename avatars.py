#!/usr/bin/env python3
"""Configure disclosed bot profiles using the standard-library API client."""
from engine import bootstrap_all, load_managed_bots, resolve_chat, verify_bots

if __name__ == "__main__":
    verify_bots()
    resolve_chat()
    load_managed_bots(for_profile_setup=True)
    bootstrap_all()
