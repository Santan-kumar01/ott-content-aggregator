# OTT Content Aggregator API

A high-performance, asynchronous RESTful API built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL** to aggregate, manage, and search movies and web series across multiple streaming platforms.

---

## Features

- **Title Catalog Management**: Full CRUD operations for movies and series with metadata (genres, release year, director, cast, platform availability).
- **Catalog Search & Sorting**: Search title names and descriptions, combine search with genre, platform, and release-year filters, and sort results by name, release year, or creation time.
- **JWT Authentication & Security**: Secure user registration, OAuth2 password flow login, cryptographically hashed passwords with `bcrypt`, and stateless JWT tokens.
- **Protected Write Endpoints**: Title modifications (create, update, delete) are protected by Bearer authentication, while catalog browsing remains publicly accessible.
- **Asynchronous Database Access**: Built on SQLAlchemy 2.0 with the `asyncpg` PostgreSQL driver for high concurrency.
- **Database Migrations**: Version-controlled schema migrations with **Alembic**.
- **Caching**: Redis integration for accelerated query performance.
- **Interactive Documentation**: Auto-generated Swagger UI and ReDoc OpenAPI specifications.
- **Comprehensive Test Suite**: Automated unit and integration tests using `pytest` and `httpx`.

---

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Database**: [PostgreSQL 16+](https://www.postgresql.org/)
- **ORM & Database Driver**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [asyncpg](https://github.com/MagicStack/asyncpg)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Security & Auth**: [python-jose](https://github.com/mpdavis/python-jose), [passlib](https://passlib.readthedocs.io/), and [bcrypt](https://github.com/pyca/bcrypt)
- **Cache**: [Redis](https://redis.io/)
- **Testing**: [pytest](https://docs.pytest.org/), [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio), [HTTPX](https://www.python-httpx.org/), and [aiosqlite](https://github.com/omnilib/aiosqlite)

---

## Getting Started

### 1. Prerequisites

- Python 3.10 or higher
- Docker Desktop (recommended for PostgreSQL and Redis) or locally installed PostgreSQL and Redis instances
- Git

---

### 2. Installation

#### Clone the Repository

```bash
git clone https://github.com/Santan-kumar01/ott-content-aggregator.git
cd ott-content-aggregator
```

#### Set Up Virtual Environment

- **On Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```

- **On macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

#### Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

### 3. Environment Configuration

Copy the example environment file to `.env`:

- **Windows PowerShell:**
  ```powershell
  Copy-Item .env.example .env
  ```
- **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

Generate a secure, random 32-byte secret key for JWT signing:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env` and set your credentials:

```dotenv
# Database Connection (PostgreSQL asyncpg driver)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ott_db

# Security & Authentication
JWT_SECRET_KEY=<paste_generated_32_byte_secret_here>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis Cache
REDIS_URL=redis://localhost:6379/0
```

> [!CAUTION]
> Never commit `.env` or expose real passwords and JWT secret keys in version control.

---

### 4. Running with Docker Compose (Recommended)

Docker Compose provides a complete, containerized environment consisting of the FastAPI application (`api`) and PostgreSQL 16 database (`db`) with automated health checks and persistent storage.

#### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- Docker Compose v2 (`docker compose version`).

#### Step-by-Step Setup

1. **Configure Environment:**
   Ensure `.env` exists and has a generated 32-byte JWT secret:
   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   ```bash
   # Linux / macOS
   cp .env.example .env
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Paste the generated token into `JWT_SECRET_KEY` in `.env`.

2. **Build and Start Services:**
   ```powershell
   docker compose up -d --build
   ```
   Compose starts the PostgreSQL container (`db`), monitors its health check until it is healthy, and then starts the API service (`api`).

3. **Verify Service Health:**
   ```powershell
   docker compose ps
   ```
   Both services will report `Up` with `db` showing `healthy`.

4. **Apply Database Migrations:**
   Run Alembic migrations inside an ephemeral API container connected to the database:
   ```powershell
   docker compose run --rm api alembic upgrade head
   ```
   Verify the applied revision:
   ```powershell
   docker compose run --rm api alembic current
   # Expected output: 0002 (head)
   ```

5. **Access the API:**
   - **Interactive Swagger UI:** http://localhost:8000/docs
   - **ReDoc Documentation:** http://localhost:8000/redoc
   - **Health Check Endpoint:** http://localhost:8000/health (returns `{"status":"healthy","database":"connected"}`)

6. **View Live Container Logs:**
   ```powershell
   # Follow logs for the API service:
   docker compose logs -f api

   # Follow logs for all services:
   docker compose logs -f
   ```

7. **Stopping Containers (Preserving Data):**
   ```powershell
   docker compose down
   ```
   This stops and removes the containers and network while **preserving** the named volume `postgres_data`. When you start the services again with `docker compose up -d`, all data remains intact.

8. **Resetting Development Database (Destructive):**
   > [!WARNING]
   > The `-v` flag permanently deletes the named volume `postgres_data` and all database tables, users, and catalog data. Only use this when you intentionally want a clean slate.
   ```powershell
   docker compose down -v
   ```

#### Troubleshooting

- **Missing Environment Credentials (Fail-Fast):** Both `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` are strictly required by Docker Compose. If either is missing or empty, Compose will fail immediately on startup to prevent silent fallback to weak credentials or insecure defaults.
- **Passwords with Special Characters:** If your PostgreSQL password contains URL-reserved characters (e.g. `@`, `:`, `/`, `#`, `%`), PostgreSQL expects the unescaped password in `POSTGRES_PASSWORD`, while SQLAlchemy requires the URL-encoded version in `DATABASE_URL`. URL-encode the password using `python -c "import urllib.parse; print(urllib.parse.quote('your_password'))"` and provide `POSTGRES_PASSWORD_ENCODED=<encoded>` or `COMPOSE_DATABASE_URL` in `.env`.
- **Port 8000 Conflict:** If port 8000 is occupied by another application on your host, set `API_PORT` in `.env`:
  ```dotenv
  API_PORT=8001
  ```
  Then restart with `docker compose up -d`.
- **Database Port Conflicts (Port 5432):** By default, `docker-compose.yml` does **not** map port 5432 to the host to prevent collisions with existing host PostgreSQL services (e.g. `ott-postgres`). The `api` service communicates with PostgreSQL over the internal Docker network via hostname `db`. If you require host access for tools like DBeaver or pgAdmin, set `POSTGRES_PORT=5433` in `.env` and uncomment the port mapping in `docker-compose.yml`.

---

### 5. Local Development Setup Without Compose (Alternative)

If you prefer running Uvicorn and PostgreSQL directly on your host machine without Docker Compose:

#### 1. Start Local PostgreSQL

Start a standalone PostgreSQL 16 container:

```powershell
docker run -d `
  --name ott-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=ott_db `
  -p 5432:5432 `
  -v ott_postgres_data:/var/lib/postgresql/data `
  postgres:16-alpine
```

Or configure a native local PostgreSQL service:

```sql
CREATE USER postgres WITH PASSWORD 'postgres';
CREATE DATABASE ott_db OWNER postgres;
```

---

### 6. Database Migrations & Schema Management

Schema management is handled exclusively through **Alembic**.
Alembic uses the same `DATABASE_URL` configured in `.env` as the application.

#### Path A: Fresh Database Setup

For a newly created database with no existing tables:

```powershell
alembic upgrade head
```

This applies migrations `0001` (titles catalog) and `0002` (user authentication) in sequence, creating all required tables, columns, primary keys, and indexes.

---

#### Path B: Adopting Pre-Existing Databases (Tables Created Outside Alembic)

If your database already contains tables (e.g., created during earlier development or via legacy scripts), follow this safe adoption workflow:

##### Step 1: Create a Full Database Backup

Always take a complete backup before running migrations or altering production databases:

```powershell
# Using Docker
docker exec -t ott-postgres pg_dump -U postgres -d ott_db -F c -b -v -f /tmp/ott_db_backup.dump
docker cp ott-postgres:/tmp/ott_db_backup.dump ./ott_db_backup.dump

# Using Native PostgreSQL
pg_dump -U postgres -d ott_db -F c -b -v -f "ott_db_backup.dump"
```

##### Step 2: Schema Compatibility Verification & Adoption

Our migration scripts (`0001_initial_titles.py` and `0002_add_user_model.py`) feature **strict schema validation**:
- When pre-existing tables are encountered, the migrations inspect all existing columns, types, nullability, and primary key constraints.
- If required columns or constraints are missing or incompatible, the migration **aborts immediately** with a descriptive error message indicating the exact missing elements, preventing silent database corruption.
- If the schema is compatible, the migration safely adopts the existing tables, preserves all existing data, and provisions any missing performance indexes (such as `ix_titles_*` and `ix_users_*`).

To adopt and validate the pre-existing database, simply run:

```powershell
alembic upgrade head
```

##### Step 3: Baseline Stamping (Alternative)

If you have already independently audited and verified that your database matches the current schema state, you can stamp the database at the target revision:

```powershell
# Stamp as fully migrated to head (revision 0002)
alembic stamp head
```

> [!WARNING]
> **Never blindly stamp an unverified database.** Stamping marks a revision as applied in `alembic_version` without executing schema checks or creating missing indexes. Always verify your database schema matches `src/models/` before stamping.

---

#### Downgrade Safety & Data Protection

To guard against catastrophic accidental data loss:
- Both `0001` and `0002` downgrade handlers check whether tables contain data before dropping them.
- If any data rows exist in the table, **downgrade is immediately aborted** with a `RuntimeError`:
  ```text
  Downgrade aborted: Table 'users' contains data. Refusing to drop table during rollback to prevent accidental data loss.
  ```
- **Explicit Override**: If you intentionally wish to destroy the table and all contained data during development or testing, you must explicitly opt in by setting the environment variable:
  - **Windows (PowerShell):**
    ```powershell
    $env:ALLOW_DESTRUCTIVE_DOWNGRADE = "1"
    alembic downgrade -1
    ```
  - **Linux / macOS:**
    ```bash
    ALLOW_DESTRUCTIVE_DOWNGRADE=1 alembic downgrade -1
    ```

> [!IMPORTANT]
> **Migration Limitations & Irreversible Baseline**:
> Relational databases do not automatically track table provenance (whether a table was originally created by an earlier Alembic run or adopted from a legacy schema). Revision `0001` represents the foundational baseline of the application. Downgrading the baseline removes the core database schema. Always take a verified database backup prior to performing any schema downgrade in non-ephemeral environments.

---

#### Common Alembic Commands

- **Check current applied revision:**
  ```powershell
  alembic current
  ```
- **Check for schema drift against SQLAlchemy models:**
  ```powershell
  alembic check
  ```
- **View migration history:**
  ```powershell
  alembic history --verbose
  ```
- **Generate SQL script for dry-run inspection (offline mode):**
  ```powershell
  alembic upgrade head --sql
  ```
- **Generate a new autodetected migration:**
  ```powershell
  alembic revision --autogenerate -m "description_of_changes"
  ```

---

### 7. Running the API Locally (Host)

Start the local development server with auto-reload:

```powershell
python -m uvicorn src.main:app --reload
```

The API will be available at:
- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/health`

---

## Authentication Workflow & Protected Endpoints

### 1. Register a New User

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "ottuser",
    "password": "StrongPassword123!"
  }'
```

**Response (`201 Created`):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "ottuser",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-10-16T10:00:00"
}
```

---

### 2. Log In & Obtain Access Token

Login supports both OAuth2 form data (used by Swagger UI "Authorize" button) and JSON:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=StrongPassword123!"
```

**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 3. Verify Current User Profile

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "ottuser",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-10-16T10:00:00"
}
```

---

### 4. Public vs. Protected Title Endpoints

#### Public Access: Browse Catalog (No Token Required)

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/titles/"
```

#### Protected Access: Create a Title (Bearer Token Required)

Unauthenticated requests to write endpoints return `401 Unauthorized`. To create a title, supply the Bearer token:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/titles/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Inception",
    "type": "Movie",
    "director": "Christopher Nolan",
    "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
    "genres": ["Sci-Fi", "Action"],
    "release_year": 2010,
    "available_platforms": ["Netflix", "Amazon Prime"]
  }'
```

Similarly, updating (`PUT /api/v1/titles/{id}`) and deleting (`DELETE /api/v1/titles/{id}`) require the Bearer token.

---

## API Endpoints Reference

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Application health check |
| `POST` | `/api/v1/auth/register` | Public | Register a new user |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and obtain JWT token |
| `GET` | `/api/v1/auth/me` | Protected | Get profile of authenticated user |
| `GET` | `/api/v1/titles/` | Public | List and filter titles |
| `GET` | `/api/v1/titles/paginated` | Public | List, search, filter, sort, and paginate titles with total count |
| `GET` | `/api/v1/titles/{id}` | Public | Retrieve a title by ID |
| `POST` | `/api/v1/titles/` | Protected | Create a new title |
| `PUT` | `/api/v1/titles/{id}` | Protected | Update an existing title |
| `DELETE` | `/api/v1/titles/{id}` | Protected | Delete a title |

### Catalog Search, Filtering, Sorting, and Pagination

Both `GET /api/v1/titles/` and `GET /api/v1/titles/paginated` accept the same catalog query parameters. Search matches title names or descriptions without regard to letter case. Search, filters, sorting, and pagination can be combined; the paginated route's `total` counts all results matching the search and filters before pagination.

| Parameter | Description |
|---|---|
| `search` | Optional keyword matched anywhere in a title name or description (1–200 characters). |
| `genre` | Optional exact genre filter (case-insensitive). |
| `platform` | Optional exact platform filter (case-insensitive). |
| `release_year` | Optional release year filter (1888–2100). |
| `sort_by` | Optional sort field: `name`, `release_year`, or `created_at`. |
| `sort_order` | Optional sort direction: `asc` or `desc`; defaults to `asc` when `sort_by` is provided. |
| `skip` | Number of matching titles to skip; defaults to `0`. |
| `limit` | Maximum number of titles to return (1–100); defaults to `20`. |

Without `sort_by`, results retain the default ID order. When a sort field is selected, equal values are returned in ascending ID order. Invalid search lengths, sort fields, sort directions, filter ranges, or pagination values return `422 Unprocessable Entity`.

Example: search for titles mentioning “space”, keep only Netflix Sci-Fi titles released in 2020, sort newest names first, and return the second result:

```bash
curl "http://127.0.0.1:8000/api/v1/titles/paginated?search=space&genre=Sci-Fi&platform=Netflix&release_year=2020&sort_by=name&sort_order=desc&skip=1&limit=1"
```

The paginated response includes `items`, the filtered `total`, `skip`, `limit`, and `has_next`. The non-paginated route returns a title array and uses the same `skip` and `limit` parameters.

---

## Running Tests

Run the complete test suite:

```powershell
python -m pytest
```

To run with verbose output and test names:

```powershell
python -m pytest -v
```

The test suite runs against an isolated async SQLite test database (`aiosqlite`), ensuring fast, reliable, and side-effect-free execution without depending on external network services.

---

## Continuous Integration (CI)

Automated testing and verification are handled by GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):
- **Triggers:** Runs automatically on all pushes and pull requests across all branches.
- **Environment:** Ubuntu runner (`ubuntu-latest`) with Python 3.11 and automated pip dependency caching.
- **PostgreSQL Service:** Provisions a containerized PostgreSQL 16 service with automated `pg_isready` readiness health checks.
- **Automated Validation:**
  1. Applies Alembic migrations (`alembic upgrade head`) against real PostgreSQL 16 and validates schema head revision (`alembic current`).
  2. Executes the complete pytest test suite (`python -m pytest`).
- **Validation Status:** Locally validated with simulated CI environment and test suites; remote execution activates on push to GitHub.

---

## Project Structure

```text
ott-content-aggregator/
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions CI pipeline
├── alembic/                      # Alembic database migrations
│   ├── versions/                 # Migration scripts (0001, 0002)
│   └── env.py                    # Async migration runner environment
├── src/
│   ├── api/
│   │   ├── dependencies/         # Dependency injection (database, auth)
│   │   └── endpoints/            # Route controllers (titles, auth)
│   ├── core/                     # Application configuration & security
│   ├── models/                   # SQLAlchemy 2.0 ORM models (Title, User)
│   ├── schemas/                  # Pydantic v2 validation models
│   ├── services/                 # Business logic & repository layers
│   └── main.py                   # FastAPI application factory & lifespan
├── tests/                        # Comprehensive pytest suite
├── .dockerignore                 # Docker build context exclusion rules
├── .env.example                  # Environment configuration template
├── alembic.ini                   # Alembic configuration
├── docker-compose.yml            # Multi-container orchestration (api, db)
├── Dockerfile                    # Multi-stage production container image
├── requirements.txt              # Production and development dependencies
└── README.md                     # Project documentation
```

---

## Team Collaboration & Workflow

- Feature development occurs on dedicated topic branches (e.g., `feat/authentication`).
- Pull requests are reviewed and verified via automated test suites prior to merging into `main`.
- Direct pushes or commits to `main` are restricted.