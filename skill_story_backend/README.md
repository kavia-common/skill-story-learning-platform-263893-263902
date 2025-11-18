# Skill Story LMS Backend (FastAPI)

This service provides the backend API for the Skill Story LMS: interactive stories, XP tracking, and journaling.

## Features

- FastAPI with modular routers:
  - Auth (demo): POST /api/auth/token
  - Stories: GET /api/stories, GET /api/stories/{id}, GET /api/stories/{id}/episodes/{n}, POST /api/stories/{id}/choices
  - Profile: GET /api/profile, PATCH /api/profile
  - Progress: GET /api/progress
  - Journal: GET /api/journal, POST /api/journal
  - Health: GET /health
- Async Postgres via SQLModel/SQLAlchemy (asyncpg)
- Alembic migrations with baseline + initial schema + seed migration
- Seeded demo story ("Leadership Basics") with 3 episodes and branching choices
- Additional bundled story: "The Focus Master" (productivity/focus) seeded idempotently at startup
- Simple auth (JWT) with register/login/refresh endpoints
- Centralized error handling with consistent response envelopes: `{ success, data | error }`
- CORS configured via `FRONTEND_ORIGIN`
- OpenAPI docs at `/docs`, schema export script at `src/api/generate_openapi.py`

## Environment Variables

Copy `.env.example` to `.env` and set values:

- DATABASE_URL (preferred) OR:
  - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
- Optional for Alembic CLI (sync driver URL): `ALEMBIC_DB_URL`
- APP_SECRET (required)
- FRONTEND_ORIGIN (recommended)
- ACCESS_TOKEN_EXPIRE_MINUTES (default 60)
- REFRESH_TOKEN_EXPIRE_DAYS (default 14)

No secrets are committed to the codebase.

## Local Development

1. Create and populate `.env` based on `.env.example`. Ensure either `DATABASE_URL` or all of `DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD` are set, and set `APP_SECRET`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply migrations (first time) to create tables and seed initial content:

```bash
# If DATABASE_URL is async (postgresql+asyncpg://...), provide ALEMBIC_DB_URL=postgresql://...
# Or let utils helper derive a sync URL from your env:
export $(grep -v '^#' .env | xargs)  # load envs in your shell (optional)
PYTHONPATH=. python utils/run_and_verify_migrations.py
# Alternatively:
alembic upgrade head
```

4. Start the API (the container uses uvicorn by default):

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

5. Visit:
- Health: `GET http://localhost:3001/health`
- Docs: `http://localhost:3001/docs`
- WebSocket note: `GET http://localhost:3001/docs/websocket-help`

### Verify Login Locally

- Register a test user (if you don't have one yet):
  `POST http://localhost:3001/api/auth/register` with body:
  {"email":"you@example.com","password":"yourStrongPassword","display_name":"Your Name"}

- Then test login:
  `POST http://localhost:3001/api/auth/login` with body:
  {"email":"you@example.com","password":"yourStrongPassword"}

- Or use the helper script:
  python tests/login_smoke.py --base-url http://localhost:3001 --email you@example.com --password "yourStrongPassword"

- Full smoke (register if needed -> login -> me):
  python tests/smoke_register_login_me.py --base-url http://localhost:3001 --email you@example.com --password "yourStrongPassword" --display-name "Your Name"

### Verify Stories and "The Focus Master"

- List stories:
  GET http://localhost:3001/api/stories

- Fetch first episode of "The Focus Master":
  1) Find its id from the list response (title == "The Focus Master")
  2) GET /api/stories/{id}/episodes/0

- Or use the helper script:
  python tests/smoke_stories_focus_master.py --base-url http://localhost:3001

Notes:
- Both /api/auth/login and its alias /api/auth/token are available for compatibility with older clients.
- Successful responses return:
  { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
- Ensure .env is configured (see .env.example) and the database is reachable. Register a user before login if none exists.

## Demo Flow

- Register/login to obtain JWT or use seeded `demo_user` via token issuance after registration.
- Start by listing stories and fetching an episode:
  - `GET /api/stories`
  - `GET /api/stories/{id}/episodes/0`
- Submit a choice:
  - `POST /api/stories/{id}/choices` with body `{"choice_id": <id>}`
- Check progress/XP:
  - `GET /api/progress`
- Add a journal entry:
  - `POST /api/journal` with body `{"content": "Reflection text..."}`

## OpenAPI

Generate the OpenAPI JSON into `interfaces/openapi.json`:

```bash
python -m src.api.generate_openapi
```

## Content Seeding: "The Focus Master"

- The story "The Focus Master" is added as bundled content and seeded idempotently during startup.
- If you need to insert it once in an authoring or staging DB without full startup, you can run:

```bash
PYTHONPATH=. python -m src.api.modules.seed_focus_master_once
```

This prints a small JSON report and is safe to rerun (idempotent).

## Migrations (Alembic)

- Baseline: 0001_baseline
- Initial schema: 0002_initial_schema
- Seed data: 0003_seed_initial_data

Common commands:

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "change message"
alembic history
```

Notes:
- CLI prefers a sync URL. Set ALEMBIC_DB_URL=postgresql://user:pass@host:port/db if your DATABASE_URL uses async driver.
- Autogenerate uses SQLModel metadata from src.api.modules.db.

## Notes

- This backend includes a rate-limiting stub middleware header `X-RateLimit-Policy: stub` for future use.
- Database schema and seeding are managed via Alembic migrations. Startup still attempts create_all defensively, but migrations are the source of truth.
