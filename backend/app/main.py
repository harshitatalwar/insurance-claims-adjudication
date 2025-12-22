from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.api import (
    claims,
    policy_holders,
    policy_terms,
    dependents,
    documents,
    document_processing,
    documents_upload,  # New enhanced upload API
    policy,
    admin,
    metrics,
    upload,
    auth,
    usage_monitoring  # Usage tracking and monitoring
)
from app.utils.database import engine, Base

# Load environment variables from root .env file
# In Docker: environment variables are passed directly by docker-compose
# In local dev: load from parent directory (root) .env file
load_dotenv()  # Try current directory first
if not os.getenv("DATABASE_URL"):
    # If not found, try parent directory (root .env)
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# NOTE: Database tables are managed via Alembic migrations
# Run `alembic upgrade head` to create/update database schema
# Do NOT use Base.metadata.create_all() in production as it conflicts with migration tracking

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting OPD Claims Adjudication System...")
    print("📊 Ensure database migrations are up to date: alembic upgrade head")
    
    # Create upload directory if it doesn't exist
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="OPD Claims Adjudication API",
    description="AI-powered system for automating OPD Insureho claim decisions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(claims.router, prefix="/api/claims", tags=["Claims"])
app.include_router(policy_holders.router, prefix="/api/policy-holders", tags=["Policy Holders"])
app.include_router(policy_terms.router, prefix="/api/policy-terms", tags=["Policy Terms"])
app.include_router(dependents.router, prefix="/api/dependents", tags=["Dependents"])

# Document Routers - Specific routes MUST come before generic ones to prevent shadowing
app.include_router(document_processing.router, prefix="/api/documents", tags=["Document Processing"])
app.include_router(documents_upload.router, tags=["Document Upload"])  # Contains /status endpoint
# app.include_router(documents.router, prefix="/api/documents", tags=["Documents"]) # Commented out old router to prevent conflicts

app.include_router(policy.router, prefix="/api/policy", tags=["Policy"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(usage_monitoring.router, prefix="/api", tags=["Usage Monitoring"])

# Import adjudication router
from app.api import adjudication
app.include_router(adjudication.router, tags=["Adjudication"])

@app.get("/")
async def root():
    return {
        "message": "OPD Claims Adjudication API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
