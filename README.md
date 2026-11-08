# Sales Automation Lab

A Python project that cleans and validates sales CSV files and stores money as integer cents.
The data is available through a CLI with SQL reports over SQLite, and through a REST API on
PostgreSQL with JWT auth, CRUD, CSV upload and revenue reports. It has type checking, tests,
Docker and CI on GitHub Actions.

## Tech stack

| Area       | Tools                                                          |
| ---------- | -------------------------------------------------------------- |
| Language   | Python 3.11+ (type hints, mypy `--strict`)                     |
| Data / ETL | pandas, `decimal`, SQL (CTEs, window functions)                |
| API        | FastAPI, Pydantic v2, pydantic-settings                        |
| Database   | PostgreSQL 17, SQLAlchemy 2.0, Alembic; SQLite for the CLI     |
| Security   | Argon2 password hashing (pwdlib), JWT (PyJWT), OAuth2 bearer   |
| Tooling    | uv, Ruff, mypy, pytest, Docker, Docker Compose, GitHub Actions |

## Architecture

```text
                    ┌──────────────────────────── sales_api (REST, PostgreSQL) ───┐
 HTTP client ──►    │ routers ──► services ──► repositories ──► SQLAlchemy ──► DB │
                    │   │  (DTOs)      │  (transactions)                          │
                    │   └─ deps (session, auth)                                   │
                    └────────────────────┬────────────────────────────────────────┘
                                         │ reuses
                    ┌────────────────────▼──────── sales_lab (CLI, SQLite) ───────┐
 CSV file ──►       │ SalesETL (extract, transform) ──► SalesService ──► SQLite   │
 CLI / cron ──►     │                                       ▲                     │
                    │              cli.py · scripts/run_daily.py · read-only API  │
                    └─────────────────────────────────────────────────────────────┘
```

- `sales_lab` contains the ETL, the SQLite repository, the CLI
  (`sales-lab run | summary | report`), a scheduler entry point (`scripts/run_daily.py`,
  exits 0 or 1) and a small read-only API.
- `sales_api` is the REST backend. It uses the same `SalesETL` for CSV uploads, so both apps
  validate rows the same way.

## API endpoints (`sales_api`)

Interactive docs are at `/docs` once the app is running.

| Method | Path                  | Auth | Success | Errors        | Notes                                       |
| ------ | --------------------- | ---- | ------- | ------------- | ------------------------------------------- |
| GET    | `/health`             |      | 200     |               | Also checks the database connection         |
| POST   | `/auth/register`      |      | 201     | 409, 422      | Email is normalized; password >= 8 chars    |
| POST   | `/auth/token`         |      | 200     | 401           | OAuth2 form: `username` = email             |
| GET    | `/auth/me`            | yes  | 200     | 401           |                                             |
| GET    | `/orders`             |      | 200     | 422           | `?category=&limit=1..100&offset=`           |
| GET    | `/orders/{id}`        |      | 200     | 404           |                                             |
| POST   | `/orders`             | yes  | 201     | 401, 409, 422 | 409 on duplicate `external_id`              |
| PATCH  | `/orders/{id}`        | yes  | 200     | 401, 404, 422 | Changes only the fields sent                |
| DELETE | `/orders/{id}`        | yes  | 204     | 401, 404      |                                             |
| POST   | `/imports`            | yes  | 200     | 400, 401      | Multipart CSV; returns read/loaded/rejected |
| GET    | `/reports/categories` |      | 200     |               | Orders, units and revenue per category      |

Endpoints with "yes" in the Auth column need an `Authorization: Bearer <token>` header.
Errors return a JSON body with a `detail` field.

## Running locally (uv)

```bash
uv sync --all-extras
cp .env.example .env            # then set SALES_API_JWT_SECRET to a long random string:
                                # python -c "import secrets; print(secrets.token_urlsafe(48))"

# REST API on PostgreSQL
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn sales_api.api.main:create_app --factory --reload   # http://127.0.0.1:8000/docs

# CLI on SQLite (no database server needed)
uv run sales-lab run            # import data/sales.csv; rejected rows -> outputs/rejected.csv
uv run sales-lab summary        # total orders, units, revenue
uv run sales-lab report         # outputs/category_report.csv
```

## Running with Docker

```bash
cp .env.example .env            # set SALES_API_JWT_SECRET (Compose refuses to start without it)
docker compose up --build       # runs migrations, then serves http://localhost:8000/docs
```

The image is a two-stage build on `python:3.12-slim` and runs as a non-root user.

## Tests and quality checks

```bash
uv run pytest -q                # ETL, service, CLI and both APIs
uv run ruff check . && uv run ruff format --check .
uv run mypy                     # strict mode, checks src/
```

The backend tests call the FastAPI app through `TestClient`. By default each test gets its
own temporary SQLite database. To run them against PostgreSQL, migrate a separate test
database and set `SALES_API_TEST_DATABASE_URL`. The tests empty every table, so don't point
it at a database you want to keep.

```bash
SALES_API_DATABASE_URL=postgresql+psycopg://sales:sales@localhost:5432/sales_test uv run alembic upgrade head
SALES_API_TEST_DATABASE_URL=postgresql+psycopg://sales:sales@localhost:5432/sales_test uv run pytest -q tests/backend
```

CI runs on pushes to `main` and on pull requests, in two jobs:

- `test`: lint, format check, mypy and the full test suite.
- `backend-postgres`: starts a PostgreSQL 17 service container, runs `alembic upgrade head`,
  then runs the backend tests against it.

## Design decisions

- **Layered architecture.** Routers handle HTTP, services hold the business rules and commit
  transactions, and repositories run the queries. Domain errors are mapped to HTTP status
  codes in one place.
- **Idempotent import.** Orders are keyed by `order_id`, so importing the same file again
  updates rows instead of duplicating them. An API upload runs in one transaction.
- **Explicit validation.** The CSV is read as text and parsed by hand, and each invalid row is
  kept with a `reject_reason`. The CLI writes rejected rows to `outputs/rejected.csv`; the API
  returns how many there were.
- **Money in cents.** Amounts are parsed with `Decimal` and stored as integer cents, never as
  floats.
- **DTOs separate from ORM models.** Pydantic schemas define the API contract separately from
  the SQLAlchemy models, so fields like `password_hash` never appear in a response.
- **Security basics.** Passwords are hashed with Argon2, JWTs expire, and login gives the same
  error for an unknown email and a wrong password. The app refuses to start without a JWT
  secret.

## Limitations

- **No authorization model.** Any registered user can create, change or delete any order:
  there are no roles or ownership checks. Registration is open, there are no refresh tokens,
  and login is not rate-limited.
- **Import scale.** Uploads are read fully into memory, have no size limit and are processed
  synchronously, with one lookup query per row. It is built for small files; large imports
  would need streaming, a bulk upsert and a background job.
- **Two storage paths.** The CLI (SQLite) and the API (PostgreSQL) keep separate data. The
  CLI is the original batch tool and the API was added on top of it, so a few rules (such as
  category normalization) exist in both.
- **Single currency.** Amounts are assumed to be in EUR, and the currency is not stored.
