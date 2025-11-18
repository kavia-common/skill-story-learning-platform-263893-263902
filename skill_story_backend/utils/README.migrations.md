# Migrations: Run and Verify

This utility helps run Alembic migrations with a sync DB URL (required by Alembic CLI) and verifies tables and seed data.

Steps:
1) Activate venv and install requirements:
   source venv/bin/activate
   pip install -r requirements.txt

2) Ensure DB env vars are set. If your app uses async DATABASE_URL (postgresql+asyncpg://...), a sync URL will be derived automatically. You can also set ALEMBIC_DB_URL directly:
   export ALEMBIC_DB_URL=postgresql://user:pass@host:port/db

3) Run:
   # If your DB is reachable via a special host/port (e.g., from running_containers),
   # you can override via environment:
   # export RUNNING_DB_HOST=vscode-internal-37210-beta.beta01.cloud.kavia.ai
   # export RUNNING_DB_PORT=3020
   # And provide credentials/db:
   # export DB_NAME=<your_db>
   # export DB_USER=<your_user>
   # export DB_PASSWORD=<your_password>
   PYTHONPATH=. python utils/run_and_verify_migrations.py

The script logs:
- Resolved sync URL used by Alembic
- Alembic upgrade head output
- Verification report listing expected tables and seeded data presence
