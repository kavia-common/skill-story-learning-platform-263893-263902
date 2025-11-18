#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import psycopg2
from psycopg2.extras import RealDictCursor


def resolve_sync_url() -> str:
    # Prefer ALEMBIC_DB_URL if provided
    alembic = os.getenv("ALEMBIC_DB_URL")
    if alembic and alembic.strip():
        return alembic.strip()

    # Normalize DATABASE_URL (async -> sync)
    db = os.getenv("DATABASE_URL", "").strip()
    if db.startswith("postgresql+asyncpg://"):
        return "postgresql://" + db[len("postgresql+asyncpg://") :]
    if db.startswith("postgres://"):
        return "postgresql://" + db[len("postgres://") :]
    if db:
        return db

    # Build from parts if available (support both app-style and postgres-style vars)
    host = (
        os.getenv("ALEMBIC_HOST")
        or os.getenv("RUNNING_DB_HOST")
        or os.getenv("DB_HOST")
        or os.getenv("POSTGRES_HOST")
    )
    port = (
        os.getenv("ALEMBIC_PORT")
        or os.getenv("RUNNING_DB_PORT")
        or os.getenv("DB_PORT")
        or os.getenv("POSTGRES_PORT")
    )
    name = os.getenv("ALEMBIC_DB_NAME") or os.getenv("DB_NAME") or os.getenv("POSTGRES_DB")
    user = os.getenv("ALEMBIC_DB_USER") or os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    password = os.getenv("ALEMBIC_DB_PASSWORD") or os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

    # If host/port not explicitly provided, try known runtime metadata fallback from work item
    # This is a non-secret, externally reachable host/port for the running database container.
    if not host and not port:
        host = "vscode-internal-37210-beta.beta01.cloud.kavia.ai"
        port = "3020"

    if all([host, port, name, user, password]):
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    # Final explicit message to guide operator rather than returning an unusable URL
    raise SystemExit(
        "Database connection details are missing. Set ALEMBIC_DB_URL or provide "
        "DATABASE_URL (async accepted) or set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD. "
        "Optionally use RUNNING_DB_HOST/RUNNING_DB_PORT to override host/port in this environment."
    )


def run(cmd: list, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(cmd, env=env, text=True, capture_output=True)


def verify(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Verify tables exist
        expected_tables = {"user", "story", "episode", "choice", "journal_entry"}
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public';
        """)
        existing = {row["table_name"] for row in cur.fetchall()}
        missing = sorted(list(expected_tables - existing))
        present = sorted(list(expected_tables & existing))

        # Verify seed presence: sample story and demo user
        seeds = {}
        if "story" in existing:
            cur.execute('SELECT COUNT(*) AS cnt FROM "story"')
            seeds["story_count"] = cur.fetchone()["cnt"]
            cur.execute('SELECT id FROM "story" WHERE title=%s', ("Leadership Basics",))
            seeds["leadership_basics"] = (cur.fetchone() is not None)
        if "user" in existing:
            cur.execute('SELECT id FROM "user" WHERE username=%s', ("demo_user",))
            seeds["demo_user_exists"] = (cur.fetchone() is not None)

        return {
            "tables_present": present,
            "tables_missing": missing,
            "seed_summary": seeds
        }


def main():
    sync_url = resolve_sync_url()
    os.environ["ALEMBIC_DB_URL"] = sync_url
    print(json.dumps({"step": "resolve_url", "alembic_db_url": sync_url}, indent=2))

    # Run alembic upgrade head
    res = run(
        ["alembic", "upgrade", "head"],
        extra_env={"PYTHONPATH": ".", "ALEMBIC_DB_URL": sync_url}
    )
    print(json.dumps({
        "step": "alembic_upgrade",
        "returncode": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr
    }, indent=2))
    if res.returncode != 0:
        sys.exit(res.returncode)

    # Verify using psycopg2 connection
    try:
        conn = psycopg2.connect(sync_url)
    except Exception as e:
        print(json.dumps({"step": "connect_verify_failed", "error": str(e)}, indent=2))
        sys.exit(1)

    try:
        report = verify(conn)
        print(json.dumps({"step": "verification", "report": report}, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
