#!/usr/bin/env python3
"""
PUBLIC_INTERFACE
Simple login smoke test for Skill Story LMS backend.

This script sends a POST to the backend's /api/auth/login endpoint with the provided
email and password, prints the HTTP status, and token fields if successful.

Usage:
  python tests/login_smoke.py --base-url http://localhost:3001 --email you@example.com --password "yourpassword"

Notes:
- Ensure the backend API is running (uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload).
- If you have not created a user yet, first register:
    POST /api/auth/register with { "email", "password", "display_name?" }
  You can also use the React frontend's Register flow.
"""
import argparse
import sys
import json
import httpx


def main():
    parser = argparse.ArgumentParser(description="Login smoke test")
    parser.add_argument("--base-url", default="http://localhost:3001", help="Backend base URL, e.g., http://localhost:3001")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/api/auth/login"
    payload = {"email": args.email, "password": args.password}

    try:
        resp = httpx.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10.0)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"Request failed: {e}"}))
        sys.exit(2)

    try:
        data = resp.json()
    except Exception:
        data = {"_raw": resp.text}

    output = {
        "status": resp.status_code,
        "ok": resp.is_success,
        "data": data,
    }
    print(json.dumps(output, indent=2))

    if resp.status_code == 401:
        print(
            "\nHint: If this is a fresh environment, register first via POST /api/auth/register "
            "or the frontend Register form, then retry the login.",
            file=sys.stderr,
        )

    sys.exit(0 if resp.is_success else 1)


if __name__ == "__main__":
    main()
