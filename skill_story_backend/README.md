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
- Seeded demo story ("Leadership Basics") with 3 episodes and branching choices
- Simple auth stub using header `X-Demo-User` and optional local JWT issuing
- Centralized error handling with consistent response envelopes: `{ success, data | error }`
- CORS configured via `FRONTEND_ORIGIN`
- OpenAPI docs at `/docs`, schema export script at `src/api/generate_openapi.py`

## Environment Variables

Copy `.env.example` to `.env` and set values:

- DATABASE_URL (preferred) OR:
  - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
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

3. Start the API (the container uses uvicorn by default):

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

4. Visit:
- Health: `GET http://localhost:3001/health`
- Docs: `http://localhost:3001/docs`

## Demo Flow

- Use header `X-Demo-User: demo_user` (or any name) to interact.
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

## Notes

- This backend includes a rate-limiting stub middleware header `X-RateLimit-Policy: stub` for future use.
- Database schema is created at startup if not present; demo data is seeded idempotently.
