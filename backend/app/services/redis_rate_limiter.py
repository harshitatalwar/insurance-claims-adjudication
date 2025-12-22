"""
Redis-Based Rate Limiter for OpenAI API

High-performance rate limiting using Redis for O(1) operations.
Database is used only for asynchronous audit logging.

Benefits over SQL-based approach:
- O(1) performance (vs O(N) COUNT(*) queries)
- No database load for rate limiting
- Sliding window algorithm for accurate limits
- Handles high concurrency
- Automatic expiration of old data

Architecture:
- Redis: Real-time rate limiting (blocking logic)
- PostgreSQL: Async audit logging (non-blocking)
"""
import time
import logging
import redis
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from typing import Optional
from contextlib import contextmanager

from app.config import settings

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Production-grade rate limiter using Redis
    
    Features:
    - Sliding window algorithm
    - O(1) performance
    - Thread-safe
    - Automatic cleanup
    - No database load
    """
    
    def __init__(self):
        # Parse Redis URL
        redis_url = settings.REDIS_URL
        
        # Connect to Redis
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis connected: {redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️  Falling back to in-memory rate limiting (not production-safe)")
            self.redis_client = None
        
        # Load limits from config
        self.rpm_limit = settings.OPENAI_RPM_LIMIT
        self.tpm_limit = settings.OPENAI_TPM_LIMIT
        self.rpd_limit = settings.OPENAI_RPD_LIMIT
        
        logger.info(f"🔒 Redis Rate Limiter initialized:")
        logger.info(f"   - RPM Limit: {self.rpm_limit}")
        logger.info(f"   - TPM Limit: {self.tpm_limit}")
        logger.info(f"   - RPD Limit: {self.rpd_limit}")
    
    def check_and_wait(
        self,
        estimated_tokens: int = 2000,
        document_id: Optional[str] = None
    ) -> None:
        """
        Check rate limits using Redis and wait if necessary
        
        This is O(1) and does NOT query the database.
        
        Args:
            estimated_tokens: Expected token usage
            document_id: Document being processed (for logging)
            
        Raises:
            Exception: If daily limit is reached
        """
        if not self.redis_client:
            logger.warning("⚠️  Redis unavailable, skipping rate limit check")
            return
        
        logger.info(f"🔍 Checking rate limits (Redis) for document {document_id or 'unknown'}")
        
        while True:
            now = int(time.time())
            
            # Redis keys
            rpm_key = "ratelimit:openai:rpm"
            tpm_key = "ratelimit:openai:tpm"
            rpd_key = "ratelimit:openai:rpd"
            
            # 1. DAILY LIMIT CHECK (Hard Stop)
            daily_requests = self._get_count(rpd_key, now, 86400)  # 24 hours
            
            if daily_requests >= self.rpd_limit:
                logger.critical(f"⛔ DAILY LIMIT REACHED: {daily_requests}/{self.rpd_limit}")
                logger.critical(f"⛔ System will resume tomorrow at midnight UTC")
                
                raise Exception(
                    f"Daily OpenAI API limit reached ({daily_requests}/{self.rpd_limit}). "
                    "Please try again tomorrow or upgrade your OpenAI tier."
                )
            
            # 2. MINUTE REQUEST LIMIT (RPM)
            minute_requests = self._get_count(rpm_key, now, 60)
            
            # 3. MINUTE TOKEN LIMIT (TPM)
            minute_tokens = self._get_sum(tpm_key, now, 60)
            
            # 4. DECISION LOGIC
            
            # Check RPM
            if minute_requests >= self.rpm_limit:
                wait_time = 20
                logger.warning(f"⏳ RPM Limit approaching: {minute_requests}/{self.rpm_limit}")
                logger.warning(f"⏳ Pausing for {wait_time}s to avoid rate limit...")
                time.sleep(wait_time)
                continue
            
            # Check TPM
            if (minute_tokens + estimated_tokens) >= self.tpm_limit:
                wait_time = 15
                logger.warning(f"⏳ TPM Limit approaching: {minute_tokens + estimated_tokens}/{self.tpm_limit}")
                logger.warning(f"⏳ Pausing for {wait_time}s to avoid rate limit...")
                time.sleep(wait_time)
                continue
            
            # Safe to proceed!
            logger.info(f"✅ Rate limits OK (Redis):")
            logger.info(f"   - RPM: {minute_requests}/{self.rpm_limit}")
            logger.info(f"   - TPM: {minute_tokens}/{self.tpm_limit}")
            logger.info(f"   - RPD: {daily_requests}/{self.rpd_limit}")
            return
    
    def record_request(
        self,
        tokens_used: int,
        document_id: Optional[str] = None
    ) -> None:
        """
        Record a successful API request in Redis
        
        This is O(1) and does NOT query the database.
        
        Args:
            tokens_used: Actual tokens used
            document_id: Document processed
        """
        if not self.redis_client:
            return
        
        now = int(time.time())
        
        # Redis keys
        rpm_key = "ratelimit:openai:rpm"
        tpm_key = "ratelimit:openai:tpm"
        rpd_key = "ratelimit:openai:rpd"
        
        # Record request count (for RPM and RPD)
        self._increment_count(rpm_key, now, 60)   # Expires in 60 seconds
        self._increment_count(rpd_key, now, 86400)  # Expires in 24 hours
        
        # Record token usage (for TPM)
        self._add_value(tpm_key, now, tokens_used, 60)  # Expires in 60 seconds
        
        logger.debug(f"📊 Recorded request in Redis: {tokens_used} tokens")
    
    def get_usage_stats(self) -> dict:
        """
        Get current usage statistics from Redis
        
        This is O(1) and does NOT query the database.
        
        Returns:
            {
                "minute": {"requests": X, "tokens": Y},
                "day": {"requests": Z}
            }
        """
        if not self.redis_client:
            return {
                "minute": {"requests": 0, "tokens": 0},
                "day": {"requests": 0}
            }
        
        now = int(time.time())
        
        minute_requests = self._get_count("ratelimit:openai:rpm", now, 60)
        minute_tokens = self._get_sum("ratelimit:openai:tpm", now, 60)
        daily_requests = self._get_count("ratelimit:openai:rpd", now, 86400)
        
        return {
            "minute": {
                "requests": minute_requests,
                "tokens": minute_tokens,
                "rpm_limit": self.rpm_limit,
                "tpm_limit": self.tpm_limit
            },
            "day": {
                "requests": daily_requests,
                "rpd_limit": self.rpd_limit
            }
        }
    
    # ===== REDIS HELPERS (Sliding Window Algorithm) =====
    
    def _get_count(self, key: str, now: int, window_seconds: int) -> int:
        """
        Get count of requests in sliding window
        
        Uses Redis Sorted Set with timestamps as scores.
        Automatically removes expired entries.
        """
        try:
            # Remove expired entries
            min_timestamp = now - window_seconds
            self.redis_client.zremrangebyscore(key, '-inf', min_timestamp)
            
            # Count remaining entries
            count = self.redis_client.zcard(key)
            return count
        except Exception as e:
            logger.error(f"Redis error in _get_count: {e}")
            return 0
    
    def _get_sum(self, key: str, now: int, window_seconds: int) -> int:
        """
        Get sum of values in sliding window
        
        For token counting: each entry has timestamp as score and tokens as value.
        """
        try:
            # Remove expired entries
            min_timestamp = now - window_seconds
            self.redis_client.zremrangebyscore(key, '-inf', min_timestamp)
            
            # Get all values and sum them
            entries = self.redis_client.zrange(key, 0, -1)
            total = sum(int(entry) for entry in entries)
            return total
        except Exception as e:
            logger.error(f"Redis error in _get_sum: {e}")
            return 0
    
    def _increment_count(self, key: str, now: int, ttl_seconds: int) -> None:
        """
        Increment request count in sliding window
        
        Adds current timestamp to sorted set.
        """
        try:
            # Add entry with current timestamp as both score and member
            self.redis_client.zadd(key, {str(now): now})
            
            # Set expiration on the key
            self.redis_client.expire(key, ttl_seconds + 10)  # +10 for safety margin
        except Exception as e:
            logger.error(f"Redis error in _increment_count: {e}")
    
    def _add_value(self, key: str, now: int, value: int, ttl_seconds: int) -> None:
        """
        Add value to sliding window
        
        For token tracking: adds tokens as member, timestamp as score.
        """
        try:
            # Add entry with timestamp as score and value as member
            member_key = f"{now}:{value}"
            self.redis_client.zadd(key, {member_key: now})
            
            # Set expiration
            self.redis_client.expire(key, ttl_seconds + 10)
        except Exception as e:
            logger.error(f"Redis error in _add_value: {e}")
    
    def reset_limits(self) -> None:
        """
        Reset all rate limits (for testing only)
        
        WARNING: Use only in development/testing
        """
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(
                "ratelimit:openai:rpm",
                "ratelimit:openai:tpm",
                "ratelimit:openai:rpd"
            )
            logger.warning("⚠️  Rate limits reset (testing only)")
        except Exception as e:
            logger.error(f"Redis error in reset_limits: {e}")


# ===== ASYNC AUDIT LOGGING (Database) =====

def log_usage_async(
    db: Session,
    document_id: str,
    document_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    response_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None
) -> None:
    """
    Log API usage to database for audit trail
    
    This is ASYNC and does NOT block rate limiting.
    Database is used only for historical tracking, not real-time decisions.
    
    Args:
        db: Database session
        document_id: Document being processed
        document_type: prescription, bill, report
        model: OpenAI model used
        input_tokens: Prompt tokens
        output_tokens: Completion tokens
        response_time_ms: API response time
        status: success, failed, error
        error_message: Error details if failed
    """
    from app.models.usage_log import APIUsageLog
    
    # Calculate cost
    cost_usd = _calculate_cost(model, input_tokens, output_tokens)
    
    # Create log entry
    log = APIUsageLog(
        endpoint="document_processor",
        document_id=document_id,
        document_type=document_type,
        model=model,
        tokens_input=input_tokens,
        tokens_output=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=cost_usd,
        status=status,
        error_message=error_message,
        response_time_ms=response_time_ms
    )
    
    db.add(log)
    db.commit()
    
    logger.info(f"💰 Usage logged to DB:")
    logger.info(f"   - Document: {document_id}")
    logger.info(f"   - Model: {model}")
    logger.info(f"   - Tokens: {input_tokens} in + {output_tokens} out = {input_tokens + output_tokens} total")
    logger.info(f"   - Cost: ${cost_usd:.6f}")


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD"""
    if "gpt-4o" in model.lower() and "mini" not in model.lower():
        input_cost = (input_tokens * settings.OPENAI_INPUT_COST_PER_1M) / 1_000_000
        output_cost = (output_tokens * settings.OPENAI_OUTPUT_COST_PER_1M) / 1_000_000
        return input_cost + output_cost
    elif "gpt-4o-mini" in model.lower():
        input_cost = (input_tokens * 0.15) / 1_000_000
        output_cost = (output_tokens * 0.60) / 1_000_000
        return input_cost + output_cost
    else:
        logger.warning(f"Unknown model pricing: {model}")
        return 0.0
