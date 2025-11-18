#!/usr/bin/env python3
"""
PUBLIC_INTERFACE
Combined end-to-end smoke:
1) Register (handles 409 already-exists)
2) Login -> get access token
3) GET /api/auth/me
4) GET /api/stories and verify "The Focus Master" exists
5) GET first episode of that story

Usage:
  python tests/smoke_e2e_auth_and_stories.py --base-url http://localhost:3001 --email you@example.com --password "YourStrongPassword" --display-name "Your Name"
"""
import argparse
import json
import sys
import httpx


def _post_json(url: str, payload: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.post(url, json=payload, headers=headers or {"Content-Type": "application/json"}, timeout=20.0)


# PUBLIC_INTERFACE
def main():
    """Run the full backend smoke sequence and emit a concise JSON report."""
    parser = argparse.ArgumentParser(description="E2E: register -> login -> me -> stories -> FM ep0")
    parser.add_argument("--base-url", default="http://localhost:3001", help="Backend base URL")
    parser.add_argument("--email", required=True, help="Email to register/login")
    parser.add_argument("--password", required=True, help="Password to register/login")
    parser.add_argument("--display-name", default=None, help="Optional display name on registration")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    report = {"base": base}

    # 1) Register (ok if 409)
    reg_payload = {"email": args.email, "password": args.password}
    if args.display_name:
        reg_payload["display_name"] = args.display_name
    try:
        r = _post_json(f"{base}/api/auth/register", reg_payload)
        report["register_status"] = r.status_code
        try:
            reg_body = r.json()
            if isinstance(reg_body, dict):
                report["register_body"] = {k: ("<redacted>" if "token" in k else v) for k, v in reg_body.items()}
        except Exception:
            report["register_body_raw"] = r.text
        if r.status_code not in (200, 409):
            print(json.dumps({"ok": False, "step": "register", "report": report}, indent=2))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"ok": False, "step": "register", "error": str(e), "report": report}, indent=2))
        sys.exit(1)

    # 2) Login
    try:
        r = _post_json(f"{base}/api/auth/login", {"email": args.email, "password": args.password})
        report["login_status"] = r.status_code
        body = r.json()
        if r.status_code != 200 or not isinstance(body, dict) or "access_token" not in body:
            print(json.dumps({"ok": False, "step": "login", "report": report, "body": body}, indent=2))
            sys.exit(1)
        report["login_body"] = {"access_token": "<redacted>", "refresh_token": "<redacted>", "token_type": body.get("token_type")}
        token = body["access_token"]
    except Exception as e:
        print(json.dumps({"ok": False, "step": "login", "error": str(e), "report": report}, indent=2))
        sys.exit(1)

    # 3) Me
    try:
        r = httpx.get(f"{base}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=20.0)
        report["me_status"] = r.status_code
        me = r.json()
        report["me_body"] = me
        if r.status_code != 200 or not isinstance(me, dict) or not all(k in me for k in ("username", "display_name", "xp")):
            print(json.dumps({"ok": False, "step": "me", "report": report}, indent=2))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"ok": False, "step": "me", "error": str(e), "report": report}, indent=2))
        sys.exit(1)

    # 4) Stories
    try:
        r = httpx.get(f"{base}/api/stories", timeout=20.0)
        report["stories_status"] = r.status_code
        sbody = r.json()
        if r.status_code != 200 or not isinstance(sbody, dict) or "data" not in sbody or not isinstance(sbody["data"], list):
            print(json.dumps({"ok": False, "step": "stories_list", "report": report}, indent=2))
            sys.exit(1)
        stories = sbody["data"]
        fm = next((s for s in stories if s.get("title") == "The Focus Master"), None)
        if not fm:
            print(json.dumps({"ok": False, "step": "focus_master_missing", "report": report, "hint": "Seeding may still be running; retry shortly."}, indent=2))
            sys.exit(1)
        report["focus_master_id"] = fm["id"]

        # 5) Episode 0
        r2 = httpx.get(f"{base}/api/stories/{fm['id']}/episodes/0", timeout=20.0)
        report["fm_ep0_status"] = r2.status_code
        ep0 = r2.json()
        ok = r2.status_code == 200 and isinstance(ep0, dict) and "data" in ep0 and ep0["data"].get("index") == 0
        print(json.dumps({"ok": ok, "step": "done", "report": report}, indent=2))
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(json.dumps({"ok": False, "step": "focus_master_ep0", "error": str(e), "report": report}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
