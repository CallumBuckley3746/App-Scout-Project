# downdetector

[Русская версия](README.md)

A backend that shows whether someone else's service is up. The project currently has user accounts with login and the full database schema: service catalog, checks, attempt history, cards, incidents, breaches, and an outbox. The scheduler and the check worker arrive in later slices.

Database details: [docs/db.en.md](docs/db.en.md) (English) and [docs/db.md](docs/db.md) (Russian).

## Structure

```text
.env.example          sample environment, no production secrets
pyproject.toml        project dependencies
uv.lock               pinned versions
Dockerfile            API image
docker-compose.yml    api, PostgreSQL, and Redis
alembic/versions/
  0001_create_users.py       users table
  0002_monitoring_schema.py  monitoring tables and the service_overview view
  0003_add_username.py       optional username
src/downdetector/
  main.py             FastAPI assembly and startup
  config.py           settings from the environment
  db/
    base.py           base model class
    metadata.py       all tables for Alembic and tests
    session.py        async engine
    user.py           accounts
    service.py        service catalog
    check.py          what to check and how often
    check_attempt.py  attempt log
    check_state.py    current success and failure streaks
    service_card.py   status the visitor sees
    incident.py       incidents
    breach.py         data breaches
    outbox.py         events for the site
  auth/
    passwords.py      Argon2id hashing
    accounts.py       registration, password check, first admin
    sessions.py       session key in Redis
  api/
    schemas.py        request bodies and the public account
    deps.py           database session, Redis, current user
    errors.py         422 response without the submitted password
    auth.py           login routes
tests/
  conftest.py         downdetector_test database and Redis index 1
  auth/               hashing and accounts
  api/                routes
  db/                 schema and constraints
docs/
  db.md, db.en.md     database documentation
  spec.md             what each slice delivered
png/                  product diagrams
MAIN.md               problem statement
```

One file, one responsibility. A router neither hashes passwords nor builds SQL.

All data that must not be lost lives in PostgreSQL. Redis holds only login sessions and, later, the job queue. Alembic owns the schema; nobody creates tables by hand.

## Running with Compose

You need Docker and a free port 8000.

```bash
docker compose up -d --build --wait
```

The API listens on `http://127.0.0.1:8000`. Before starting, the container applies all migrations up to `0003_add_username`.

Check:

```bash
curl http://127.0.0.1:8000/health
```

Response: `{"status": "ok"}`. This route touches neither the database nor Redis.

Administrator from `docker-compose.yml`:

- email: `admin@example.com`
- password: `change-me-please`

Stop; PostgreSQL data is kept:

```bash
docker compose stop
```

Do not run `docker compose down -v`: the `-v` flag deletes the database volume.

## Running the API on the host

You need Python 3.13 and `uv`. PostgreSQL and Redis can stay in Compose.

```bash
docker compose up -d --wait postgres redis
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn downdetector.main:app --host 127.0.0.1 --port 8000
```

`.env` is not in git. The process refuses to start with an administrator password shorter than 12 characters.

When done:

```bash
docker compose stop postgres redis
```

## Routes

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/health` | the process is alive |
| `POST` | `/api/auth/register` | new account with role `user`, no cookie |
| `POST` | `/api/auth/login` | password is correct, sets the `session_id` cookie for 8 hours |
| `POST` | `/api/auth/logout` | session deleted |
| `GET` | `/api/auth/me` | current account or 401 |

Registration accepts `email`, a `password` of 12 to 128 characters, and an optional `username`. The username is trimmed, lowercased, and must match `^[a-z0-9_]{3,32}$`. The `role` field is ignored: registration cannot create an administrator. A taken email or a taken username gives the same 409 response. Login is by email.

Register and log in:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"fan@example.com","password":"long-password-123","username":"Spotify_Fan"}'

curl -c cookies.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"fan@example.com","password":"long-password-123"}'

curl -b cookies.txt http://127.0.0.1:8000/api/auth/me
```

`me` response: `{"id": "...", "email": "fan@example.com", "username": "spotify_fan", "role": "user"}`.

## Database

Nine tables and the `service_overview` view in PostgreSQL 17:

| Table | Purpose |
|---|---|
| `users` | accounts and roles |
| `services` | service catalog, filled by an administrator |
| `checks` | check address, interval, timeout, and thresholds |
| `check_attempts` | attempt log, one per slot |
| `check_states` | current success and failure streaks |
| `service_cards` | visitor-facing status: `unknown`, `up`, `degraded`, `down` |
| `incidents` | incidents, our own and vendor-published |
| `breaches` | data breaches; they do not affect availability |
| `outbox_events` | events for the site |

Migrations:

```bash
uv run alembic upgrade head        # apply all
uv run alembic downgrade -1        # roll back the last one
uv run alembic current             # current revision
```

How the tables, relationships, constraints, and data flow work: [docs/db.en.md](docs/db.en.md).

