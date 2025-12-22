from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "OPD Claims Adjudication System"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql://opd_user:opd_password@localhost:5432/opd_claims"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    
    # Rate Limits (Tier 1 / Free Tier - Update in .env for higher tiers)
    OPENAI_RPM_LIMIT: int = 3
    OPENAI_TPM_LIMIT: int = 8000
    OPENAI_RPD_LIMIT: int = 150
    
    # OpenAI Pricing (USD per 1M tokens)
    OPENAI_INPUT_COST_PER_1M: float = 5.0
    OPENAI_OUTPUT_COST_PER_1M: float = 15.0
    
    LLM_TEMPERATURE: float = 0.0  # Zero for consistency
    MAX_TOKENS: int = 2000
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    # Confidence Thresholds
    MANUAL_REVIEW_THRESHOLD: float = 0.70
    HIGH_VALUE_CLAIM_THRESHOLD: float = 25000.0
    
    # Vector Database (Qdrant)
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "policy_documents"
    QDRANT_USE_MEMORY: bool = True
    
    # MinIO Object Storage
    MINIO_HOST: str = "localhost"
    MINIO_PORT: int = 9000
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "opd-claims"
    MINIO_SECURE: bool = False
    
    # Redis (Celery Message Broker)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        case_sensitive = True
        env_file = "../.env"  # Load from root .env file
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Ignore extra env variables not in Settings

settings = Settings()
