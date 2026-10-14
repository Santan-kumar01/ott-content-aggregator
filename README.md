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
| POST | `/api/v1/titles/` | Create a title |
| GET | `/api/v1/titles/` | List and filter titles |
| GET | `/api/v1/titles/{title_id}` | Retrieve a title |
| PATCH | `/api/v1/titles/{title_id}` | Update a title |
| DELETE | `/api/v1/titles/{title_id}` | Delete a title |

## Team Collaboration

Team members should work on separate feature branches and create Pull Requests for review before merging into `main`.

## License

Educational and internship project.