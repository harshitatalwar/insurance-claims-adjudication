# OPD Claims Adjudication Backend

## Setup

### Prerequisites
- Python 3.10+
- Poetry (install: `pip install poetry`)

### Installation

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Copy environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run database migrations (if using PostgreSQL)
alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/          # API route handlers
│   ├── models/       # Database models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── utils/        # Utilities
├── tests/            # Test files
└── pyproject.toml    # Poetry dependencies
```

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run ruff check .
```
