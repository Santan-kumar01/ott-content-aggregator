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

### 4. Database Setup

#### Using Docker (Recommended)

Start a PostgreSQL 16 container with a persistent named volume:

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

*(Optional)* Start a Redis container for caching:

```powershell
docker run -d `
  --name ott-redis `
  -p 6379:6379 `
  redis:7-alpine
```

#### Using Native PostgreSQL

If using a local PostgreSQL service, create the database user and database:

```sql
CREATE USER postgres WITH PASSWORD 'postgres';
CREATE DATABASE ott_db OWNER postgres;
```

---

### 5. Database Migrations

Apply existing Alembic migrations to set up the database schema (`titles` and `users` tables):

```powershell
alembic upgrade head
```

#### Common Alembic Commands

- **Check current revision:**
  ```powershell
  alembic current
  ```
- **Check for schema drift:**
  ```powershell
  alembic check
  ```
- **Roll back the last migration:**
  ```powershell
  alembic downgrade -1
  ```
- **Generate a new migration:**
  ```powershell
  alembic revision --autogenerate -m "description of changes"
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
| `GET` | `/api/v1/titles/{id}` | Public | Retrieve a title by ID |
| `POST` | `/api/v1/titles/` | Protected | Create a new title |
| `PUT` | `/api/v1/titles/{id}` | Protected | Update an existing title |
| `DELETE` | `/api/v1/titles/{id}` | Protected | Delete a title |

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

## Project Structure

```text
ott-content-aggregator/
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
├── .env.example                  # Environment configuration template
├── alembic.ini                   # Alembic configuration
├── requirements.txt              # Production and development dependencies
└── README.md                     # Project documentation
```

---

## Team Collaboration & Workflow

- Feature development occurs on dedicated topic branches (e.g., `feat/authentication`).
- Pull requests are reviewed and verified via automated test suites prior to merging into `main`.
- Direct pushes or commits to `main` are restricted.