# OTT Content Aggregator API

A high-performance, asynchronous RESTful API built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL** to aggregate, manage, and search movies and web series across multiple streaming platforms.

---

## Features

- **Title Catalog Management**: Full CRUD operations for movies and series with metadata (genres, release year, director, cast, platform availability).
- **Advanced Filtering**: Filter titles by genre, release year, language, rating, and streaming platform.
- **JWT Authentication & Security**: Secure user registration, OAuth2 password flow login, cryptographically hashed passwords with `bcrypt`, and stateless JWT tokens.
- **Protected Write Endpoints**: Title modifications (create, update, delete) are protected by Bearer authentication, while catalog browsing remains publicly accessible.
- **Asynchronous Database Access**: Built on SQLAlchemy 2.0 with the `asyncpg` PostgreSQL driver for high concurrency.
- **Database Migrations**: Version-controlled schema migrations with **Alembic**.
- **Caching**: Redis integration for accelerated query performance.
- **External HTTP & Background Processing**: Non-blocking external provider metadata synchronization via shared `httpx.AsyncClient` and `FastAPI.BackgroundTasks` with bounded retries and observable job tracking.
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
- **HTTP Client & Background Tasks**: [HTTPX](https://www.python-httpx.org/) & FastAPI BackgroundTasks
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
CACHE_TTL_SECONDS=300
CACHE_ENABLED=true

# External HTTP & Background Sync Operations
EXTERNAL_API_TIMEOUT_SECONDS=10.0
EXTERNAL_API_MAX_RETRIES=2
EXTERNAL_PROVIDER_BASE_URL=https://api.example-ott-provider.com
```

> [!CAUTION]
> Never commit `.env` or expose real passwords and JWT secret keys in version control.


---

### 4. Database & Cache Infrastructure Setup

#### Option A: Using Docker Compose (Recommended)

Start both PostgreSQL 16 and Redis 7 containers together with automated health checks:

```powershell
docker compose up -d
```

Verify service status and health checks:

```powershell
docker compose ps
```

#### Option B: Using Individual Docker Containers

1. **Start PostgreSQL 16** with a persistent named volume:

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

2. **Start Redis 7** for catalog caching:

   ```powershell
   docker run -d `
     --name ott-redis `
     -p 6379:6379 `
     redis:7-alpine
   ```

3. **Verify Connectivity**:

   ```powershell
   # Check PostgreSQL readiness
   docker exec -it ott-postgres pg_isready -U postgres -d ott_db

   # Check Redis responsiveness
   docker exec -it ott-redis redis-cli ping
   ```

#### Option C: Native Local Installation

If running services natively on your host machine:

```sql
-- PostgreSQL
CREATE USER postgres WITH PASSWORD 'postgres';
CREATE DATABASE ott_db OWNER postgres;
```

```powershell
# Redis native service check
redis-cli ping
```

---

### 5. Database Migrations & Schema Management

Schema management is handled exclusively through **Alembic**.

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

### 6. Running the API

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

Similarly, updating (`PATCH /api/v1/titles/{id}`) and deleting (`DELETE /api/v1/titles/{id}`) require the Bearer token.

---

## API Endpoints Reference

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Application health check |
| `POST` | `/api/v1/auth/register` | Public | Register a new user |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and obtain JWT token |
| `GET` | `/api/v1/auth/me` | Protected | Get profile of authenticated user |
| `GET` | `/api/v1/titles/` | Public | List and filter titles |
| `GET` | `/api/v1/titles/paginated` | Public | List, search, filter, sort, and paginate titles with metadata |
| `GET` | `/api/v1/titles/{id}` | Public | Retrieve a title by ID |
| `POST` | `/api/v1/titles/` | Protected | Create a new title |
| `PATCH` | `/api/v1/titles/{id}` | Protected | Update an existing title (Partial update) |
| `DELETE` | `/api/v1/titles/{id}` | Protected | Delete a title |

### Catalog Search, Filtering, Sorting, and Pagination

Both `GET /api/v1/titles/` and `GET /api/v1/titles/paginated` accept query parameters to filter, search, sort, and paginate catalog titles:

| Parameter | Type | Validation / Allowed Values | Description |
|---|---|---|---|
| `search` | Query (string) | Length: 1–200 characters | Case-insensitive partial match in title `name` or `description`. SQL wildcards (`%`, `_`, `\`) are safely escaped. |
| `genre` | Query (string) | Case-insensitive | Filters titles by exact genre name. |
| `platform` | Query (string) | Case-insensitive | Filters titles by exact streaming platform name. |
| `release_year` | Query (int) | Between 1888 and 2100 | Filters titles by release year. |
| `sort_by` | Query (string) | `name`, `release_year`, `created_at` | Field to sort by. Defaults to insertion order (`id`) if omitted. Uses `id` ascending as deterministic tiebreaker. |
| `sort_order` | Query (string) | `asc`, `desc` (default: `asc`) | Sort direction. |
| `skip` | Query (int) | `>= 0` (default: `0`) | Number of matching titles to skip. |
| `limit` | Query (int) | `1` to `100` (default: `20`) | Maximum number of titles to return. |

#### Paginated Response Format (`GET /api/v1/titles/paginated`)

```json
{
  "items": [
    {
      "id": 1,
      "name": "Inception",
      "description": "Mind-bending sci-fi heist thriller",
      "content_type": "movie",
      "release_year": 2010,
      "genre": "Sci-Fi",
      "platform": "Netflix",
      "created_at": "2026-10-25T16:00:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20,
  "has_next": false
}
```

The `total` field reflects the total number of records matching all active search and filter criteria before pagination.


---

## Redis Caching Architecture

The application uses production-conscious asynchronous Redis caching to accelerate catalog queries while guaranteeing consistency with PostgreSQL:

### 1. Key Design & Deterministic Normalization
- All catalog queries (`GET /api/v1/titles` and `GET /api/v1/titles/paginated`) compute deterministic SHA-256 hashes of normalized query parameters (stripped, lowercased string filters, integers, sort direction, and pagination boundaries).
- Key format: `catalog:v{generation}:{endpoint_type}:{sha256_param_hash}`.
- Single title key format: `catalog:v{generation}:title:{title_id}`.

### 2. Atomic Invalidation via Versioned Generation
- A monotonic Redis counter (`catalog:generation`) represents the active cache version.
- On any title write (`POST /api/v1/titles`, `PATCH /api/v1/titles/{id}`, `DELETE /api/v1/titles/{id}`), invalidation executes **only after the database transaction commits successfully**.
- Invalidation increments `catalog:generation` via atomic `INCR`.
- All query permutations across search, filters, sorting, and pagination immediately point to the new generation in $O(1)$ time. Obsolete keys expire naturally via their TTL (default 300s).

### 3. Graceful Outage Resilience & Cache Bypass
- If Redis is unavailable or times out:
  - Cache reads bypass cleanly and query PostgreSQL directly without throwing HTTP 500 errors.
  - Database writes commit successfully and flag a pending invalidation state.
  - When Redis reconnects, the generation counter is automatically bumped to ensure no pre-outage cache entries are served stale.
- The `/health` endpoint reports `"redis": "connected"` or `"redis": "disconnected"` without failing the application status while PostgreSQL remains connected.

---

## Background Processing & External HTTP Operations

The application supports asynchronous external metadata synchronization and background processing to enrich catalog titles with streaming provider data:

### 1. Workflow & Endpoints
- **Queue Synchronization (`POST /api/v1/titles/{title_id}/sync`)**:
  - Requires Bearer authentication.
  - Accepts optional `external_id` (defaults to stringified `title_id`) and `provider` name.
  - Immediately validates title existence in the database.
  - Returns `HTTP 202 Accepted` with a unique `task_id` (`UUIDv4`) and schedules execution outside the request-response cycle via `FastAPI.BackgroundTasks`.
- **Observable Task Status (`GET /api/v1/titles/sync/tasks/{task_id}`)**:
  - Provides execution status (`pending`, `in_progress`, `completed`, `failed`), timestamps, synced fields, and diagnostic error messages.

### 2. Asynchronous External HTTP Client
- Managed via `src/core/http_client.py` using `httpx.AsyncClient`.
- Lifespan-managed initialization on FastAPI startup and graceful disposal on shutdown.
- Configured with strict timeouts (`connect=5.0s`, `read=10.0s`, configurable via `EXTERNAL_API_TIMEOUT_SECONDS`) and connection pooling (10 keepalive, 20 max connections).
- Non-blocking I/O throughout: route handlers and tasks never block the Python event loop.
- Sensitive credentials (tokens, API keys, passwords) in URLs are automatically sanitized and masked in application logs via `sanitize_url`.

### 3. Resilience, Retries & Error Handling
- Bounded retries: Transient network errors (timeouts, connection refused, HTTP 5xx responses) are retried up to 2 times (`EXTERNAL_API_MAX_RETRIES`) using exponential backoff ($0.5\text{s} \times 2^{\text{attempt}}$).
- Non-retryable errors: Client errors (`HTTP 404 Not Found`, invalid schemas, or malformed JSON payloads) fail fast and record clear diagnostics without polluting logs or retrying fruitlessly.
- Data integrity: External failures never corrupt existing PostgreSQL data. If external data cannot be fetched or parsed, the transaction is cleanly aborted, and the background task records a `failed` status.

### 4. Database Session Isolation & Cache Invalidation
- **Session Isolation**: Background tasks never reuse the caller's request database session (which closes when the HTTP response completes). The task creates its own isolated session using `async with SessionLocal() as db:`.
- **Post-Commit Invalidation**: When title metadata updates successfully commit in PostgreSQL, `cache_service.invalidate_catalog(title_id=title_id)` is invoked, ensuring stale cache entries in Redis are purged immediately.

### 5. Architectural Trade-offs & Limitations
- **FastAPI BackgroundTasks vs. Celery**:
  - `FastAPI.BackgroundTasks` was chosen because it provides the simplest, zero-overhead architecture that satisfies all project requirements without adding heavy worker daemons, Celery brokers, or separate container services.
  - **Limitation**: `FastAPI.BackgroundTasks` executes in-memory within the Uvicorn application process. Tasks **do not persist across server restarts or process termination**. If durable delivery, cross-restart persistence, or independently scalable worker nodes are required in future phases, a Celery worker pool with Redis as the message broker can be introduced with the same task logic.

---

## Running Tests

### 1. Test Architecture & Environment Safety

The test suite is structured into isolated unit tests and live integration test modules:
- **Fast In-Memory Tests (SQLite + Mocked Redis)**: Run automatically with zero external dependencies using `sqlite+aiosqlite:///:memory:`. All unit, validation, auth contract, and mock tests run deterministically in seconds.
- **Genuine PostgreSQL Integration Tests**: Run against an actual PostgreSQL 16 container (`ott-postgres`) to verify real database transactions, unique constraints, and schema parity without substituting SQLite.
- **Genuine Redis Integration Tests**: Run against a real Redis 7 container (`ott-redis`) to verify live connection pooling, cache hits/misses, TTL expiration, and multi-version invalidation.
- **Cross-Component Integration Tests**: Exercise authenticated catalog writes followed by cached reads, PATCH/DELETE invalidation lifecycles, database rollback consistency, Redis outage resilience & recovery, and background task failure observability.

---

### 2. Environment Variables for Integration Testing

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_TEST_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/ott_test_db` | Connection string to dedicated disposable PostgreSQL integration test database |
| `REDIS_URL` | `redis://localhost:6379/0` | Connection string to live Redis cache server |
| `CACHE_ENABLED` | `true` | Master toggle to enable or bypass Redis caching logic |
| `CACHE_TTL_SECONDS` | `300` | Default cache expiration lifetime in seconds |
| `EXTERNAL_API_TIMEOUT_SECONDS` | `10.0` | Read timeout for external provider requests |
| `EXTERNAL_API_MAX_RETRIES` | `2` | Number of exponential backoff retry attempts for transient HTTP failures |

---

### 3. Setting Up Live Integration Services (Docker)

To run live PostgreSQL and Redis integration tests, start the container services via Docker:

```powershell
# Start existing containers or start via docker compose
docker compose up -d db redis
# Or start existing containers:
docker start ott-postgres ott-redis
```

Verify services are running and listening on localhost:
```powershell
docker ps
```

---

### 4. Running Test Commands

#### Run the Full Automated Test Suite
```powershell
python -m pytest -v
```

#### Run with Code Coverage Analysis
```powershell
# Terminal report with missing lines
python -m pytest --cov=src --cov-report=term-missing

# Generate interactive HTML coverage report in htmlcov/
python -m pytest --cov=src --cov-report=html
```

#### Specific Test Modules

1. **Cross-Component Integration Tests** (Auth edge cases, CRUD + cache hit/miss flow, DB rollback, Redis outage & recovery):
   ```powershell
   python -m pytest tests/test_cross_component_integration.py -v
   ```

2. **PostgreSQL & Migration Integration Tests** (Real PostgreSQL engine, Alembic head verification, schema parity & persistence):
   ```powershell
   python -m pytest tests/test_postgresql_integration.py -v
   ```

3. **Live Redis Integration Tests** (Real Redis connection, TTL expiration, cache hits, invalidation against Docker Redis):
   ```powershell
   python -m pytest tests/test_redis_integration.py -v
   ```

4. **Redis Caching Unit & Resilience Tests** (Key hashing, URL sanitization, outage tolerance, mock failures):
   ```powershell
   python -m pytest tests/test_redis_caching_unit.py -v
   ```

5. **Background Processing & External HTTP Tests** (Task 5 async HTTP client, timeout, retries, session isolation & task status):
   ```powershell
   python -m pytest tests/test_background_and_external_http.py -v
   ```

6. **Authentication & Security Tests** (Password hashing, JWT generation, validation, role protection):
   ```powershell
   python -m pytest tests/test_auth_api.py tests/test_auth_service.py tests/test_security.py -v
   ```

7. **Catalog Search, Filter, Sort & Pagination Tests**:
   ```powershell
   python -m pytest tests/test_catalog_search_and_pagination.py -v
   ```

8. **Alembic Schema & Migration Lifecycle Tests** (Upgrade, downgrade, re-upgrade on clean disposable DB):
   ```powershell
   python -m pytest tests/test_migrations.py tests/test_migration_and_startup.py -v
   ```

---

### 5. Known Test Limitations

- **FastAPI BackgroundTasks In-Process Execution**: Tasks execute asynchronously in the background within the active process event loop. If the application server process terminates abruptly, in-flight background jobs are not preserved in a durable queue.
- **Docker Dependency for Live Integration**: If Docker is not running on the host machine, `test_postgresql_integration.py` will report connection failure, and `test_redis_integration.py` will skip gracefully with an informative message (`Live Redis service on localhost:6379 is not reachable`) rather than falsely claiming successful integration.

---

## Project Structure

```text
ott-content-aggregator/
├── alembic/                      # Alembic database migrations
│   ├── versions/                 # Version-controlled migration scripts (0001, 0002, 497ce7b6dfad)
│   └── env.py                    # Async migration runner environment
├── src/
│   ├── api/
│   │   ├── dependencies/         # Dependency injection (database, auth)
│   │   └── endpoints/            # Route controllers (titles, auth)
│   ├── core/
│   │   ├── cache.py              # Redis client lifecycle, pooling, URL masking & health
│   │   ├── database.py           # SQLAlchemy 2.0 engine, settings & session factory
│   │   ├── http_client.py        # Shared async HTTPX client, connection pooling & URL masking
│   │   └── security.py           # Password hashing & JWT token management
│   ├── models/                   # SQLAlchemy 2.0 ORM models (Title, User)
│   ├── schemas/                  # Pydantic v2 validation models
│   │   ├── sync.py               # Background task and external metadata schemas
│   │   ├── title.py
│   │   └── user.py
│   ├── services/
│   │   ├── auth_service.py       # Authentication & user registration service
│   │   ├── background_tasks.py   # Background task runner, session isolation & status registry
│   │   ├── cache_service.py      # Catalog caching, deterministic keys & invalidation
│   │   ├── catalog_service.py    # Database catalog CRUD, search, filter & pagination
│   │   └── external_provider_service.py # Non-blocking external HTTP service with retries
│   └── main.py                   # FastAPI application factory, lifespan & health
├── tests/
│   ├── test_api_defects_and_contract.py
│   ├── test_auth_api.py
│   ├── test_auth_service.py
│   ├── test_background_and_external_http.py # Task 5 async HTTP & background tests
│   ├── test_catalog_search_and_pagination.py
│   ├── test_cross_component_integration.py  # Task 6 cross-component integration tests
│   ├── test_migration_and_startup.py
│   ├── test_migrations.py
│   ├── test_postgresql_integration.py       # Genuine PostgreSQL integration tests
│   ├── test_redis_caching_unit.py           # Redis unit & resilience tests
│   ├── test_redis_integration.py            # Live Redis integration tests
│   ├── test_security.py
│   ├── test_title_protection.py
│   └── test_user_model_schemas.py
├── docker-compose.yml            # Docker Compose service definition (PostgreSQL & Redis)
├── alembic.ini                   # Alembic configuration
├── requirements.txt              # Production and development dependencies
├── .env.example                  # Environment configuration template
└── README.md                     # Comprehensive project documentation
```

---

## Team Collaboration & Workflow

- Feature development occurs on dedicated topic branches (e.g., `feat/authentication`).
- Pull requests are reviewed and verified via automated test suites prior to merging into `main`.
- Direct pushes or commits to `main` are restricted.