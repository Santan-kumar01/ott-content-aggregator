# OTT Content Aggregator API

A RESTful API built using FastAPI and PostgreSQL to manage and search movies and web series.

## Features

- Create, read, update, and delete titles (CRUD)
- Filter titles by genre, release year, and platform
- Input validation using Pydantic
- PostgreSQL integration with SQLAlchemy
- Interactive API documentation using Swagger UI

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Pytest

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Santan-kumar01/ott-content-aggregator.git
cd ott-content-aggregator
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and configure your local PostgreSQL credentials and a strong JWT secret.

Never upload your `.env` file or secrets to GitHub.

### 5. Run the application

```powershell
uvicorn src.main:app --reload
```

## API Documentation

Once the application is running:

- Swagger UI: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user account |
| POST | `/api/v1/auth/login` | Authenticate user and issue JWT bearer access token |
| GET | `/api/v1/auth/me` | Retrieve profile of authenticated user |
| POST | `/api/v1/titles` | Create a title (Requires Bearer Token) |
| GET | `/api/v1/titles` | List, search, and filter titles (Public) |
| GET | `/api/v1/titles/paginated` | List, search, filter, sort, and paginate titles with metadata (Public) |
| GET | `/api/v1/titles/{title_id}` | Retrieve a title by ID (Public) |
| PATCH | `/api/v1/titles/{title_id}` | Update a title (Requires Bearer Token) |
| DELETE | `/api/v1/titles/{title_id}` | Delete a title (Requires Bearer Token) |

### Catalog Search, Filtering, Sorting, and Pagination

Both `GET /api/v1/titles` and `GET /api/v1/titles/paginated` accept query parameters to filter, search, sort, and paginate catalog titles:

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


## Team Collaboration

Team members should work on separate feature branches and create Pull Requests for review before merging into `main`.

## License

Educational and internship project.