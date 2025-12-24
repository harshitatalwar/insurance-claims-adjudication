# OPD Claims Adjudication Tool

AI-powered system for automating Outpatient Department (OPD) insurance claim decisions with intelligent document processing, policy validation, and real-time adjudication.

---

## 🎯 Overview

This production-ready application automates the complete lifecycle of OPD insurance claims:
- **Document Upload**: Secure presigned URL-based upload to MinIO object storage
- **AI Processing**: GPT-4o Vision extracts structured data from medical documents (bills, prescriptions, reports)
- **Policy Validation**: Multi-validator system checks eligibility, coverage, limits, and fraud indicators
- **Automated Adjudication**: LLM-powered decision engine with confidence scoring and guardrails
- **Real-time Updates**: WebSocket-based progress tracking via Redis Pub/Sub
- **Manual Review**: Human-in-the-loop workflow for edge cases and low-confidence decisions

---

## Architecture

### **Tech Stack**

#### **Backend**
- **Framework**: FastAPI 
- **Database**: PostgreSQL (relational data)
- **Vector DB**: Qdrant (document embeddings for RAG)
- **Object Storage**: MinIO (medical documents)
- **Task Queue**: Celery + Redis (async processing)
- **AI/ML**: OpenAI GPT-4o Vision, GPT-4o (adjudication)
- **ORM**: SQLAlchemy with Alembic migrations

#### **Frontend**
- **Framework**: Next.js (App Router)
- **Styling**: TailwindCSS (CSS-first configuration)
- **State Management**: React Context API
- **Real-time**: Server-Sent Events (SSE)

#### **Infrastructure**
- **Containerization**: Docker + Docker Compose
- **Rate Limiting**: Redis-based token bucket
- **Monitoring**: Usage tracking, cost monitoring, logging

---

## Complete Workflow

### **1. User Registration & Authentication**
```
Frontend (register page) → POST /api/auth/register → Backend creates user → JWT token issued
```

### **2. Document Upload Flow**
```
1. Frontend requests presigned URL
   POST /api/upload/{format} (jpg/pdf/text)
   
2. Backend generates presigned URL
   - Creates document record in PostgreSQL
   - Generates MinIO presigned URL (15 min expiry)
   - Returns upload URL to frontend
   
3. Frontend uploads directly to MinIO
   PUT {presigned_url} with file binary
   
4. Frontend confirms upload
   POST /api/upload/complete
   
5. Backend triggers async processing
   - Celery task: process_document_task
```

### **3. Document Processing (Async)**
```
Celery Worker:
├─ Download from MinIO
├─ Base64 encode image
├─ GPT-4o Vision extraction
│  ├─ Prescription: medicines, dosages, doctor info
│  ├─ Bill: items, amounts, hospital details
│  └─ Report: diagnosis, tests, findings
├─ Store extracted JSON in PostgreSQL
├─ Generate embeddings (optional RAG)
├─ Store in Qdrant vector DB
└─ Publish real-time update via Redis Pub/Sub
```

### **4. Automated Adjudication (Async)**
```
Celery Worker (adjudicate_claim_task):
├─ Load claim + documents + policy holder
├─ Run validation pipeline:
│  ├─ Eligibility Validator (policy active, waiting period)
│  ├─ Coverage Validator (treatment covered, exclusions)
│  ├─ Limit Validator (annual limit, per-claim cap)
│  ├─ Document Validator (completeness, authenticity)
│  └─ Fraud Detector (anomalies, red flags)
│
├─ Check kill switches (hard rejections)
│  └─ Expired policy, exceeded limit → REJECT
│
├─ LLM Enrichment (GPT-4o)
│  ├─ Input: validation results + policy terms + claim evidence
│  ├─ Output: structured decision with reasoning
│  └─ Schema: decision, approved_amount, rejection_reasons, next_steps
│
├─ Apply guardrails
│  └─ Override LLM if critical failures detected
│
├─ Calculate confidence score
│  └─ All pass: 0.95+ | 1 fail: 0.75-0.85 | 2+ fail: <0.70
│
├─ Save decision to PostgreSQL
└─ Publish decision via Redis Pub/Sub
```

### **5. Real-time Updates**
```
Frontend subscribes to claim channel:
Redis Pub/Sub: claim_updates:{claim_id}

Events:
- document_update: OCR completed
- claim_decision: Adjudication result
- status_change: Manual review assigned
```

---

## 📂 Project Structure

```
opd-claims-adjudication/
├── backend/
│   ├── app/
│   │   ├── api/              # REST endpoints (auth, upload, claims)
│   │   ├── services/         # Business logic
│   │   │   ├── document_processor.py  # GPT-4o Vision OCR
│   │   │   ├── adjudication_engine.py # Decision engine
│   │   │   ├── minio_service.py       # Object storage
│   │   │   └── validators/   # Policy validation modules
│   │   ├── models/           # SQLAlchemy models
│   │   ├── worker.py         # Celery tasks
│   │   └── main.py           # FastAPI app
│   ├── alembic/              # Database migrations
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── globals.css       # Tailwind Theme Configuration
│   │   ├── (public)/         # Public routes (Login, Register)
│   │   └── (protected)/      # Secure routes (Upload Flow)
│   │       ├── upload/
│   │       │   ├── step1/    # Dashboard & Upload
│   │       │   ├── step2/    # Real-time Processing View
│   │       │   └── step3/    # Adjudication Results
│   ├── components/
│   │   └── ui/               # Reusable Glassmorphism components
│   ├── contexts/             # AuthContext
│   └── Dockerfile
│
├── docker-compose.yml        # Full stack orchestration
└── .env                      # Configuration
```

---

## Quick Start

### **Prerequisites**
- Docker & Docker Compose
- OpenAI API key

### **1. Clone & Configure**
```bash
git clone <repository-url>
cd opd-claims-adjudication
cp .env.local.example .env
```

Edit `.env`:
```bash
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com
```

### **2. Start All Services**
```bash
docker compose up -d --build
```
Location: Root folder (opd-claims-adjudication) Terminal: Terminal 1
Run this to build and start the Backend, Frontend, Database, Redis, and MinIO:
Wait about 1-2 minutes for everything to start.

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9000, console 9001)
- Qdrant (port 6333)
- Backend API (port 8000)
- Celery Worker
- Frontend (port 3000)

### **3. Run Database Migrations**
```bash
docker compose exec backend alembic upgrade head
```
Location: Root folder (opd-claims-adjudication) Terminal: Terminal 1 (Same one)
This creates the tables in your PostgreSQL database

### **4. Seed Policy Terms**
```bash
docker compose exec backend python seed_policy_terms.py
```
Location: Root folder (opd-claims-adjudication) 
Terminal: Terminal 1 (Same one)
This adds the sample policy terms so the AI knows what to check against

### **5. Verify & Access**
Everything is now running.

Frontend (App): Open http://localhost:3000
Login/Register to start uploading.
Backend (Docs): http://localhost:8000/docs
MinIO (Files): http://localhost:9001

### **6. Optional: Monitor Logs**
If you want to see what the AI is doing in real-time (like OCR or Adjudicating), run this in a new terminal
```bash
docker compose logs -f celery_worker
```
Terminal: Terminal 2

---

## Key Features

### **1. Intelligent Document Processing**
- **GPT-4o Vision**: Extracts structured data from images/PDFs
- **Multi-format Support**: JPG, PNG, PDF, HEIC
- **Rate Limiting**: 20 requests/min to prevent API abuse
- **Cost Tracking**: Logs token usage and costs per document

### **2. Multi-Validator Adjudication**
- **Eligibility**: Policy status, waiting periods, coverage dates
- **Coverage**: Treatment type, exclusions, pre-existing conditions
- **Limits**: Annual caps, per-claim limits, remaining balance
- **Fraud Detection**: Anomaly detection, duplicate claims
- **Document Quality**: Completeness, authenticity checks

### **3. LLM-Powered Decision Engine**
- **Structured Output**: Pydantic schemas prevent parsing errors
- **Guardrails**: Hard rules override LLM for critical violations
- **Confidence Scoring**: 0.0-1.0 based on validation results
- **Explainability**: Detailed reasoning with policy citations

### **4. Real-time Progress Tracking**
- **Redis Pub/Sub**: Live updates during processing
- **Status Events**: Upload → Processing → Adjudication → Decision
- **WebSocket Support**: Frontend receives instant notifications

### **5. Production-Ready Infrastructure**
- **Async Processing**: Celery workers handle long-running tasks
- **Retry Logic**: Exponential backoff for transient failures
- **Health Checks**: Docker healthchecks for all services
- **CORS Configuration**: Secure cross-origin requests

---
