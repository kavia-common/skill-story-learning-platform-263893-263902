"""One-time insertion script for 'The Focus Master' story.

Run:
  PYTHONPATH=. uvicorn is not required. Just execute:
  python -m src.api.modules.seed_focus_master_once

Environment:
  - Uses normal application DB settings resolved by src.api.modules.config.Settings
  - Requires the database to be reachable.

Notes:
  - Operation is idempotent: safe to rerun; it updates content/links if they changed.
"""
import asyncio
import json

from .db import init_db, get_session
from .seed_focus_master import seed_focus_master


# PUBLIC_INTERFACE
async def main() -> int:
    """Seed the 'The Focus Master' story once and print a small JSON report."""
    await init_db()  # ensure engine/session factory and create_all safety
    async with get_session() as session:  # type: AsyncSession
        result = await seed_focus_master(session)
    print(json.dumps({"ok": True, "seeded": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
