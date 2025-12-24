# Deployment Guide

This guide covers deploying the **OpenAI OPD Claims Adjudication System** in both development and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Environment Configuration](#environment-configuration)
- [Database Migrations](#database-migrations)
- [Docker Deployment (Recommended)](#docker-deployment-recommended)
- [Local Development](#local-development)
- [Production Checklist](#production-checklist)

---

## Prerequisites

- **Docker & Docker Compose** (Essential for full-stack deployment)
- **Node.js 18+** (For frontend local dev)
- **Python 3.11+** (For backend local dev)
- **OpenAI API Key** (Required for GPT-4o Vision)

---

## Architecture Overview

The system consists of 7 interconnected services:
1.  **Backend (FastAPI)**: API & Business Logic (Port 8000)
2.  **Frontend (Next.js)**: User Interface (Port 3000)
3.  **Worker (Celery)**: Async tasks (OCR, Adjudication)
4.  **PostgreSQL**: Relational Database
5.  **Redis**: Broker, Pub/Sub, & Caching
6.  **MinIO**: Object Storage (S3 Compatible)
7.  **Qdrant**: Vector Database

---

## Environment Configuration

You must configure environment variables for both Backend and Frontend.

### 1. Root `.env` (Docker Compose)
Create a `.env` file in the project root:

```env
# --- Application ---
SECRET_KEY=change-this-to-a-secure-random-key
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# --- OpenAI ---
OPENAI_API_KEY=sk-proj-your-key-here

# --- Database ---
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=opd_claims

# --- MinIO ---
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
```

### 2. Frontend `.env.local`
Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Docker Deployment (Recommended)

The easiest way to run the entire stack is using Docker Compose.

### 1. Build and Run
```bash
docker compose up -d --build
```
This will start all services. 
- Frontend: `http://localhost:3000`
- Backend Docs: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001`

### 2. Run Database Migrations
**Critical Step**: The database is empty on first launch. You must run migrations.

```bash
docker compose exec backend poetry run alembic upgrade head
```

### 3. Seed Policy Data (Optional)
To test adjudication, seed sample policy terms:
```bash
docker compose exec backend poetry run python seed_policy_terms.py
```

### 4. Viewing Logs
```bash
# Backend logs
docker compose logs -f backend

# Celery Worker logs (Important for debugging OCR/Adjudication)
docker compose logs -f celery_worker
```

### 5. Stop Services
```bash
docker compose down
```

---

## Local Development

If you want to run services individually without Docker (not recommended for beginners).

### Backend
1.  **Install**: `cd backend && poetry install`
2.  **Run Dependencies**: You still need Redis/Postgres/MinIO running (use Docker for these).
3.  **Run App**: `poetry run uvicorn app.main:app --reload`
4.  **Run Worker**: `poetry run celery -A app.worker.celery_app worker --loglevel=info`

### Frontend
1.  **Install**: `cd frontend && npm install`
2.  **Run**: `npm run dev`
3.  **Access**: `http://localhost:3000`

---

## Production Checklist

### Security
- [ ] Change `SECRET_KEY`, `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`.
- [ ] Set `minioadmin` credentials to strong values.
- [ ] Restrict `ALLOWED_ORIGINS` to your production domain only.
- [ ] Use **HTTPS** (Reverse Proxy like Nginx/Traefik in front of FastAPI and Next.js).

### Infrastructure
- [ ] Use specialized services for persistence (AWS RDS for Postgres, AWS S3 instead of MinIO).
- [ ] Set `DEBUG=False` in backend.
- [ ] Configure `NEXT_PUBLIC_API_URL` to your production API domain (e.g., `https://api.yourdomain.com`).

### Deployment Strategy
- **Frontend**: Deploy to Vercel or as a Docker container.
- **Backend/Worker**: Deploy to AWS ECS, Kubernetes, or DigitalOcean App Platform.
