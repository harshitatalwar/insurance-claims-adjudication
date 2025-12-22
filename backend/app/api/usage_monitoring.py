"""
API Usage Monitoring Endpoints
Provides real-time usage statistics and cost tracking
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from app.models.usage_log import APIUsageLog
from app.utils.database import get_db
from app.services.redis_rate_limiter import RedisRateLimiter

router = APIRouter()


@router.get("/usage/stats")
async def get_usage_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get current API usage statistics
    
    Returns:
        {
            "current_minute": {...},
            "current_day": {...},
            "limits": {...}
        }
    """
    rate_limiter = RateLimiter()
    stats = rate_limiter.get_usage_stats(db)
    
    return {
        "current_minute": {
            "requests": stats["minute"]["requests"],
            "tokens": stats["minute"]["tokens"],
            "rpm_limit": stats["minute"]["rpm_limit"],
            "tpm_limit": stats["minute"]["tpm_limit"],
            "rpm_percentage": round((stats["minute"]["requests"] / stats["minute"]["rpm_limit"]) * 100, 1),
            "tpm_percentage": round((stats["minute"]["tokens"] / stats["minute"]["tpm_limit"]) * 100, 1)
        },
        "current_day": {
            "requests": stats["day"]["requests"],
            "cost_usd": round(stats["day"]["cost_usd"], 4),
            "rpd_limit": stats["day"]["rpd_limit"],
            "rpd_percentage": round((stats["day"]["requests"] / stats["day"]["rpd_limit"]) * 100, 1)
        },
        "limits": {
            "rpm": stats["minute"]["rpm_limit"],
            "tpm": stats["minute"]["tpm_limit"],
            "rpd": stats["day"]["rpd_limit"]
        }
    }


@router.get("/usage/history")
async def get_usage_history(
    hours: int = 24,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get usage history for the last N hours
    
    Args:
        hours: Number of hours to look back (default: 24)
        
    Returns:
        {
            "total_requests": X,
            "total_tokens": Y,
            "total_cost_usd": Z,
            "by_document_type": {...},
            "by_hour": [...]
        }
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Total stats
    total_requests = db.query(func.count(APIUsageLog.id)).filter(
        APIUsageLog.timestamp >= cutoff_time,
        APIUsageLog.status == "success"
    ).scalar() or 0
    
    total_tokens = db.query(func.sum(APIUsageLog.total_tokens)).filter(
        APIUsageLog.timestamp >= cutoff_time,
        APIUsageLog.status == "success"
    ).scalar() or 0
    
    total_cost = db.query(func.sum(APIUsageLog.cost_usd)).filter(
        APIUsageLog.timestamp >= cutoff_time,
        APIUsageLog.status == "success"
    ).scalar() or 0.0
    
    # By document type
    by_type = db.query(
        APIUsageLog.document_type,
        func.count(APIUsageLog.id).label('count'),
        func.sum(APIUsageLog.cost_usd).label('cost')
    ).filter(
        APIUsageLog.timestamp >= cutoff_time,
        APIUsageLog.status == "success"
    ).group_by(APIUsageLog.document_type).all()
    
    return {
        "period_hours": hours,
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_cost_usd": round(float(total_cost), 4),
        "average_tokens_per_request": round(total_tokens / total_requests, 1) if total_requests > 0 else 0,
        "by_document_type": {
            row.document_type: {
                "count": row.count,
                "cost_usd": round(float(row.cost), 4)
            }
            for row in by_type
        }
    }


@router.get("/usage/recent")
async def get_recent_usage(
    limit: int = 10,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get most recent API calls
    
    Args:
        limit: Number of recent calls to return (default: 10)
        
    Returns:
        List of recent API calls with details
    """
    recent_logs = db.query(APIUsageLog).order_by(
        APIUsageLog.timestamp.desc()
    ).limit(limit).all()
    
    return {
        "recent_calls": [
            {
                "timestamp": log.timestamp.isoformat(),
                "document_id": log.document_id,
                "document_type": log.document_type,
                "model": log.model,
                "tokens": log.total_tokens,
                "cost_usd": round(log.cost_usd, 6),
                "status": log.status,
                "response_time_ms": log.response_time_ms
            }
            for log in recent_logs
        ]
    }
