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

1. Create and populate `.env` based on `.env.example`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run migrations (first time):

```bash
# If DATABASE_URL is async (postgresql+asyncpg://...), provide ALEMBIC_DB_URL=postgresql://...
export $(grep -v '^#' .env | xargs)  # load envs in your shell (optional)
alembic upgrade head
```

4. Start the API (the container uses uvicorn by default):

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

5. Visit:
- Health: `GET http://localhost:3001/health`
- Docs: `http://localhost:3001/docs`

### Verify Login Locally

- Register a test user (if you don't have one yet):
  `POST http://localhost:3001/api/auth/register` with body:
  {"email":"you@example.com","password":"yourStrongPassword","display_name":"Your Name"}

- Then test login:
  `POST http://localhost:3001/api/auth/login` with body:
  {"email":"you@example.com","password":"yourStrongPassword"}

- Or use the helper script:
  python tests/login_smoke.py --base-url http://localhost:3001 --email you@example.com --password "yourStrongPassword"

Both /api/auth/login and its alias /api/auth/token return:
  { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

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
