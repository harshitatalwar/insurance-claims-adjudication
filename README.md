# OPD Claims Adjudication Tool

AI-powered system for automating Outpatient Department (OPD) Insureho claim decisions.

## 🎯 Overview

This application automates the adjudication (approval/rejection) of OPD Insureho claims by:
- Processing medical documents (bills, prescriptions, reports) using GPT-4 Vision
- Extracting structured data with AI
- Validating against policy terms
- Making intelligent decisions with confidence scores
- Providing manual review workflow for edge cases

## 🏗️ Architecture

```
opd-claims-adjudication/
├── backend/          # FastAPI backend with Python
├── frontend/         # Next.js frontend with TypeScript
└── docs/            # Documentation and diagrams
```

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Copy environment file
cp .env.docker.example .env
# Add your OPENAI_API_KEY to .env

# Start all services
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard

See [Docker Setup Guide](docs/DOCKER_SETUP.md) for details.

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Install Poetry if not already installed
pip install poetry

# Install dependencies
poetry install

# Copy environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start server
poetry run uvicorn app.main:app --reload
```

Backend will run on: http://localhost:8000
API Docs: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on: http://localhost:3000

## 📋 Features

### Core Features
- ✅ Document upload and processing (images/PDFs)
- ✅ AI-powered data extraction (GPT-4 Vision)
- ✅ Automated claim adjudication
- ✅ Policy validation and limit checking
- ✅ Confidence scoring for decisions

### Advanced Features
- ✅ Manual review workflow
- ✅ Admin dashboard for policy configuration
- ✅ Evaluation metrics and analytics
- ✅ RAG for policy document retrieval
- ✅ Fraud detection indicators
- ✅ CI/CD pipeline

## 🧪 Testing

### Run Test Cases

```bash
cd backend
poetry run pytest tests/ -v
```

All 10 provided test cases are validated automatically.

## 📚 Documentation

- [Architecture Diagram](docs/architecture.md)
- [API Documentation](http://localhost:8000/docs)
- [Decision Flowchart](docs/decision_flowchart.md)
- [Implementation Plan](docs/implementation_plan.md)

## 🛠️ Technology Stack

**Backend:**
- FastAPI (Python)
- SQLAlchemy + PostgreSQL/SQLite
- OpenAI GPT-4 Vision API
- Qdrant (Vector Database for RAG)
- LangChain

**Frontend:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Shadcn/ui Components

**Deployment:**
- Frontend: Vercel
- Backend: Railway/Render
- Database: Supabase/Railway PostgreSQL

## 📊 Evaluation Metrics

The system tracks:
- Decision accuracy
- Confidence score distribution
- Processing time
- Approval/rejection rates
- Confusion matrix

## 🔐 Environment Variables

### Backend (.env)
```
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./opd_claims.db
MANUAL_REVIEW_THRESHOLD=0.70
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 👥 Contributors

Built for Insureho AI Automation Engineer Intern Assignment

## 📝 License

MIT
