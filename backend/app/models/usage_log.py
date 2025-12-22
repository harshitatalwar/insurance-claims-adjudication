"""
API Usage Logging Model
Tracks every OpenAI API call for auditing and cost monitoring
"""
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.utils.database import Base


class APIUsageLog(Base):
    """
    Logs every OpenAI API call for:
    - Cost tracking
    - Rate limit monitoring
    - Audit trail
    - Usage analytics
    """
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Request metadata
    endpoint = Column(String, index=True)  # e.g., "document_processing"
    document_id = Column(String, index=True)  # e.g., "DOC4A2B3C4D5E"
    document_type = Column(String)  # prescription, bill, report
    
    # OpenAI metadata
    model = Column(String)  # e.g., "gpt-4o"
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    total_tokens = Column(Integer)
    
    # Cost tracking
    cost_usd = Column(Float)  # Estimated cost in USD
    
    # Status tracking
    status = Column(String)  # "success", "rate_limited", "failed", "error"
    error_message = Column(String, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)  # API response time
