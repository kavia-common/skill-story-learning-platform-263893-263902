#!/usr/bin/env python3
"""
PUBLIC_INTERFACE
End-to-end backend smoke for auth: register (if needed) -> login -> me.

- Tries to register the provided email; treats 200 as success and 409 Conflict as "already exists".
- Logs in to obtain access_token.
- Calls /api/auth/me with Bearer token.
- Emits a compact JSON report to stdout, exits 0 on success, 1 on failure.

Usage:
  python tests/smoke_register_login_me.py --base-url http://localhost:3001 --email you@example.com --password "yourStrongPassword" --display-name "Your Name"
"""
import argparse
import json
import sys
import os

import httpx


def _post_json(url: str, payload: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.post(url, json=payload, headers=headers or {"Content-Type": "application/json"}, timeout=15.0)


# PUBLIC_INTERFACE
def main():
    """Run auth smoke: register if needed, then login and call /me."""
    parser = argparse.ArgumentParser(description="Auth smoke: register->login->me")
    parser.add_argument("--base-url", default=os.getenv("BACKEND_BASE_URL", "http://localhost:3001"), help="Backend base URL, e.g., http://localhost:3001")
    parser.add_argument("--email", required=True, help="Email for register/login")
    parser.add_argument("--password", required=True, help="Password for register/login")
    parser.add_argument("--display-name", default=None, help="Optional display name for registration")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    report: dict = {"base": base}

    # 1) Register (ok if already exists -> 409)
    reg_payload = {"email": args.email, "password": args.password}
    if args.display_name:
        reg_payload["display_name"] = args.display_name
    try:
        reg_resp = _post_json(f"{base}/api/auth/register", reg_payload)
        report["register_status"] = reg_resp.status_code
        try:
            # redact tokens if provided by registration
            reg_body = reg_resp.json()
            report["register_body"] = {k: ("<redacted>" if "token" in k else v) for k, v in reg_body.items()} if isinstance(reg_body, dict) else reg_body
        except Exception:
            report["register_body_raw"] = reg_resp.text
        if reg_resp.status_code not in (200, 409):
            print(json.dumps({"ok": False, "step": "register", "report": report}, indent=2))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"ok": False, "step": "register", "error": str(e), "report": report}, indent=2))
        sys.exit(1)

    # 2) Login
    try:
        login_resp = _post_json(f"{base}/api/auth/login", {"email": args.email, "password": args.password})
        report["login_status"] = login_resp.status_code
        try:
            login_body = login_resp.json()
        except Exception:
            print(json.dumps({"ok": False, "step": "login", "error": "Non-JSON response", "report": report}, indent=2))
            sys.exit(1)
        report["login_body"] = {k: ("<redacted>" if "token" in k else v) for k, v in (login_body.items() if isinstance(login_body, dict) else [])}
        if login_resp.status_code != 200 or not isinstance(login_body, dict) or "access_token" not in login_body:
            print(json.dumps({"ok": False, "step": "login", "report": report}, indent=2))
            sys.exit(1)
        access_token = login_body["access_token"]
    except Exception as e:
        print(json.dumps({"ok": False, "step": "login", "error": str(e), "report": report}, indent=2))
        sys.exit(1)

    # 3) Me
    try:
        me_resp = httpx.get(f"{base}/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=15.0)
        report["me_status"] = me_resp.status_code
        try:
            me_body = me_resp.json()
        except Exception:
            print(json.dumps({"ok": False, "step": "me", "error": "Non-JSON response", "report": report}, indent=2))
            sys.exit(1)
        report["me_body"] = me_body
        ok = (
            me_resp.status_code == 200
            and isinstance(me_body, dict)
            and all(k in me_body for k in ("username", "display_name", "xp"))
        )
        print(json.dumps({"ok": ok, "step": "done", "report": report}, indent=2))
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(json.dumps({"ok": False, "step": "me", "error": str(e), "report": report}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
