#!/usr/bin/env python3
"""
PUBLIC_INTERFACE
Smoke test for stories listing and episode retrieval focusing on 'The Focus Master'.

Usage:
  python tests/smoke_stories_focus_master.py --base-url http://localhost:3001
"""
import argparse
import json
import sys
import httpx


def main():
    parser = argparse.ArgumentParser(description="Stories smoke: verify 'The Focus Master' presence and episodes")
    parser.add_argument("--base-url", default="http://localhost:3001", help="Backend base URL")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    report = {"base": base}

    try:
        r = httpx.get(f"{base}/api/stories", timeout=15.0)
        report["list_status"] = r.status_code
        stories = r.json()["data"] if r.is_success and isinstance(r.json(), dict) and "data" in r.json() else None
        if not r.is_success or not isinstance(stories, list):
            print(json.dumps({"ok": False, "step": "list_stories", "report": report}, indent=2))
            sys.exit(1)
        fm = next((s for s in stories if s.get("title") == "The Focus Master"), None)
        if not fm:
            print(json.dumps({"ok": False, "step": "find_focus_master", "report": report, "hint": "Seeding may not have completed yet"}, indent=2))
            sys.exit(1)
        report["focus_master_id"] = fm["id"]

        r2 = httpx.get(f"{base}/api/stories/{fm['id']}/episodes/0", timeout=15.0)
        report["ep0_status"] = r2.status_code
        ok = r2.is_success and isinstance(r2.json(), dict) and "data" in r2.json() and r2.json()["data"].get("index") == 0
        print(json.dumps({"ok": ok, "step": "done", "report": report}, indent=2))
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(json.dumps({"ok": False, "step": "exception", "error": str(e), "report": report}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
