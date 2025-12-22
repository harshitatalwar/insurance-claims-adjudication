# Deployment Guide

This guide covers deploying the OPD Claims Adjudication System in both development and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Database Migrations](#database-migrations)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Checklist](#production-checklist)

---

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Docker & Docker Compose (for containerized deployment)
- Poetry (for dependency management)

---

## Database Migrations

### Important: Migration-First Approach

This application uses **Alembic** for database schema management. The application **will not** automatically create tables on startup.

### Initial Setup

1. **Initialize Alembic** (if not already done):
   ```bash
   cd backend
   alembic init alembic
   ```

2. **Configure Alembic** (`alembic.ini`):
   - Update `sqlalchemy.url` to match your `DATABASE_URL`
   - Or use environment variables (recommended)

3. **Create Initial Migration**:
   ```bash
   # Auto-generate migration from models
   alembic revision --autogenerate -m "Initial schema"
   
   # Review the generated migration in alembic/versions/
   ```

4. **Apply Migrations**:
   ```bash
   alembic upgrade head
   ```

### Common Migration Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

---

## Environment Configuration

### Docker vs. Local Development

The application defaults are optimized for **Docker Compose** deployments. For local development, you need to override certain environment variables.

### Docker Compose (Default)

Create a `.env` file in the `backend/` directory:

```env
# Application
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Database (Docker service name)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/opd_claims

# OpenAI
OPENAI_API_KEY=sk-your-api-key

# Qdrant (Docker service name)
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# MinIO (Docker service name)
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
```

### Local Development

For local development (without Docker Compose):

```env
# Application
DEBUG=True
SECRET_KEY=your-secret-key

# Database (localhost)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/opd_claims

# OpenAI
OPENAI_API_KEY=sk-your-api-key

# Qdrant (localhost)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MinIO (localhost)
MINIO_HOST=localhost
MINIO_PORT=9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
```

---

## Local Development

### 1. Install Dependencies

```bash
cd backend
poetry install
```

### 2. Start External Services

You can run Qdrant and MinIO locally via Docker:

```bash
# Qdrant
docker run -p 6333:6333 qdrant/qdrant

# MinIO
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  minio/minio server /data --console-address ":9001"

# PostgreSQL
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=opd_claims \
  postgres:15
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start the Application

```bash
# Using Poetry
poetry run uvicorn app.main:app --reload

# Or activate the virtual environment
poetry shell
uvicorn app.main:app --reload
```

---

## Docker Deployment

### Build Images

```bash
# From project root
docker compose build
```

### Run Services

```bash
docker compose up -d
```

### Run Migrations in Container

```bash
# Execute migrations inside the backend container
docker compose exec backend alembic upgrade head
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
```

### Stop Services

```bash
docker compose down

# Remove volumes (WARNING: deletes data)
docker compose down -v
```

---

## Production Checklist

### Security

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=False`
- [ ] Use strong passwords for PostgreSQL, MinIO
- [ ] Enable HTTPS/TLS (`MINIO_SECURE=True`)
- [ ] Restrict CORS origins (`ALLOWED_ORIGINS`)
- [ ] Use environment-specific `.env` files (never commit to git)

### Database

- [ ] Use managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
- [ ] Enable automated backups
- [ ] Set up connection pooling
- [ ] Run migrations before deploying new code: `alembic upgrade head`

### Dependencies

- [ ] Verify `psycopg2` (not `psycopg2-binary`) is installed
- [ ] Ensure `libpq-dev` is available in build environment
- [ ] Lock dependency versions in `poetry.lock`

### Monitoring

- [ ] Set up application logging
- [ ] Configure error tracking (Sentry, etc.)
- [ ] Monitor database performance
- [ ] Set up health check endpoints

### Infrastructure

- [ ] Use container orchestration (Kubernetes, ECS, etc.)
- [ ] Configure auto-scaling
- [ ] Set resource limits (CPU, memory)
- [ ] Use persistent volumes for uploads
- [ ] Set up load balancer

### Testing

- [ ] Run full test suite before deployment
- [ ] Test migrations on staging environment
- [ ] Verify all environment variables are set
- [ ] Test service connectivity (Qdrant, MinIO, PostgreSQL)

---

## Troubleshooting

### "No module named 'psycopg2'"

**Solution**: Ensure `libpq-dev` is installed and rebuild:
```bash
# Debian/Ubuntu
apt-get install libpq-dev

# Rebuild Docker image
docker compose build --no-cache backend
```

### "Connection refused" to Qdrant/MinIO

**Solution**: Check environment variables:
- **Docker**: Use service names (`qdrant`, `minio`)
- **Local**: Use `localhost`

### "Alembic can't locate revision"

**Solution**: Ensure migrations are in sync:
```bash
# Check current version
alembic current

# Stamp database with current version
alembic stamp head
```

### Tables not created

**Solution**: Run migrations manually:
```bash
alembic upgrade head
```

The application no longer auto-creates tables via `create_all()`.

---

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
