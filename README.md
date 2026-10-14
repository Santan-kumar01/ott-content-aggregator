\# OTT Content Aggregator API



A RESTful API built with FastAPI and PostgreSQL to manage and search movies and web series.



\## Features



\- Create, read, update, and delete titles (CRUD)

\- Search and filter by genre, release year, and platform

\- Input validation using Pydantic

\- PostgreSQL database with SQLAlchemy

\- Interactive API documentation using Swagger UI



\## Tech Stack



\- Python

\- FastAPI

\- PostgreSQL

\- SQLAlchemy

\- Pydantic

\- Pytest



\## Project Structure



```text

ott-content-aggregator/

├── src/

│   ├── api/

│   │   └── endpoints/

│   ├── core/

│   ├── models/

│   ├── schemas/

│   ├── services/

│   └── main.py

├── tests/

├── .env.example

├── .gitignore

├── requirements.txt

└── README.md

```



\## Setup Instructions



\### 1. Clone the repository



```bash

git clone https://github.com/Santan-kumar01/ott-content-aggregator.git

cd ott-content-aggregator

```



\### 2. Create and activate a virtual environment



Windows PowerShell:



```powershell

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



\### 3. Install dependencies



```powershell

python -m pip install -r requirements.txt

```



\### 4. Configure environment variables



Copy `.env.example` to `.env` and update the database credentials and a strong random JWT secret.



Make sure PostgreSQL is running and the configured database exists.



\### 5. Run the API



```powershell

uvicorn src.main:app --reload

```



\## API Documentation



After starting the server, open:



\- Swagger UI: http://127.0.0.1:8000/docs

\- Health Check: http://127.0.0.1:8000/health



\## Example API Endpoints



| Method | Endpoint | Purpose |

|---|---|---|

| POST | `/api/v1/titles/` | Create a title |

| GET | `/api/v1/titles/` | List and filter titles |

| GET | `/api/v1/titles/{title\_id}` | Get a title |

| PATCH | `/api/v1/titles/{title\_id}` | Update a title |

| DELETE | `/api/v1/titles/{title\_id}` | Delete a title |



\## Team Collaboration



Contributors should create feature branches and submit Pull Requests for review before merging changes into `main`.



\## Security



Never commit `.env`, database passwords, or secret keys to GitHub.



\## License



This project is currently developed for educational and internship purposes.

