"""
Smart Rate Limiter for OpenAI API
- Prevents hitting rate limits (RPM, TPM, RPD)
- Logs all usage for cost tracking
- Automatically waits when approaching limits
- Future-proof: reads limits from config
"""
import time
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from app.models.usage_log import APIUsageLog
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Production-grade rate limiter with usage tracking
    
    Features:
    - Dynamic limits from config (easy to upgrade tiers)
    - Real-time usage monitoring
    - Automatic throttling
    - Cost tracking
    - Comprehensive logging
    """
    
    def __init__(self):
        # Load limits dynamically from settings
        self.rpm_limit = settings.OPENAI_RPM_LIMIT
        self.tpm_limit = settings.OPENAI_TPM_LIMIT
        self.rpd_limit = settings.OPENAI_RPD_LIMIT
        
        logger.info(f"🔒 Rate Limiter initialized:")
        logger.info(f"   - RPM Limit: {self.rpm_limit}")
        logger.info(f"   - TPM Limit: {self.tpm_limit}")
        logger.info(f"   - RPD Limit: {self.rpd_limit}")

    def check_and_wait(
        self, 
        db: Session, 
        estimated_tokens: int = 2000,
        document_id: Optional[str] = None
    ) -> None:
        """
        Check rate limits and wait if necessary
        
        Args:
            db: Database session
            estimated_tokens: Expected token usage for this request
            document_id: Document being processed (for logging)
            
        Raises:
            Exception: If daily limit is reached (hard stop)
        """
        logger.info(f"🔍 Checking rate limits for document {document_id or 'unknown'}")
        
        while True:
            now = datetime.now(timezone.utc)
            one_minute_ago = now - timedelta(seconds=60)
            one_day_ago = now - timedelta(hours=24)

            # 1. DAILY LIMIT CHECK (Hard Stop)
            daily_requests = db.query(func.count(APIUsageLog.id)).filter(
                APIUsageLog.timestamp >= one_day_ago,
                APIUsageLog.status == "success"
            ).scalar() or 0

            if daily_requests >= self.rpd_limit:
                logger.critical(f"⛔ DAILY LIMIT REACHED: {daily_requests}/{self.rpd_limit}")
                logger.critical(f"⛔ System will resume tomorrow at midnight UTC")
                
                # Log the rate limit hit
                self._log_rate_limit(db, "daily", daily_requests, self.rpd_limit, document_id)
                
                raise Exception(
                    f"Daily OpenAI API limit reached ({daily_requests}/{self.rpd_limit}). "
                    "Please try again tomorrow or upgrade your OpenAI tier."
                )

            # 2. MINUTE REQUEST LIMIT (RPM)
            minute_requests = db.query(func.count(APIUsageLog.id)).filter(
                APIUsageLog.timestamp >= one_minute_ago,
                APIUsageLog.status == "success"
            ).scalar() or 0

            # 3. MINUTE TOKEN LIMIT (TPM)
            minute_tokens = db.query(func.sum(APIUsageLog.total_tokens)).filter(
                APIUsageLog.timestamp >= one_minute_ago,
                APIUsageLog.status == "success"
            ).scalar() or 0

            # 4. DECISION LOGIC
            
            # Check RPM
            if minute_requests >= self.rpm_limit:
                wait_time = 20  # Wait 20 seconds
                logger.warning(f"⏳ RPM Limit approaching: {minute_requests}/{self.rpm_limit}")
                logger.warning(f"⏳ Pausing for {wait_time}s to avoid rate limit...")
                
                self._log_rate_limit(db, "rpm", minute_requests, self.rpm_limit, document_id)
                time.sleep(wait_time)
                continue  # Re-check after waiting

            # Check TPM
            if (minute_tokens + estimated_tokens) >= self.tpm_limit:
                wait_time = 15  # Wait 15 seconds
                logger.warning(f"⏳ TPM Limit approaching: {minute_tokens + estimated_tokens}/{self.tpm_limit}")
                logger.warning(f"⏳ Pausing for {wait_time}s to avoid rate limit...")
                
                self._log_rate_limit(db, "tpm", minute_tokens, self.tpm_limit, document_id)
                time.sleep(wait_time)
                continue

            # Safe to proceed!
            logger.info(f"✅ Rate limits OK:")
            logger.info(f"   - RPM: {minute_requests}/{self.rpm_limit}")
            logger.info(f"   - TPM: {minute_tokens}/{self.tpm_limit}")
            logger.info(f"   - RPD: {daily_requests}/{self.rpd_limit}")
            return

    def log_usage(
        self,
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
        Log API usage for tracking and billing
        
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
        # Calculate cost
        cost_usd = self._calculate_cost(model, input_tokens, output_tokens)
        
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
        
        logger.info(f"💰 Usage logged:")
        logger.info(f"   - Document: {document_id}")
        logger.info(f"   - Model: {model}")
        logger.info(f"   - Tokens: {input_tokens} in + {output_tokens} out = {input_tokens + output_tokens} total")
        logger.info(f"   - Cost: ${cost_usd:.6f}")
        logger.info(f"   - Status: {status}")

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost in USD
        
        Pricing is configurable in settings for easy updates
        """
        if "gpt-4o" in model.lower():
            input_cost = (input_tokens * settings.OPENAI_INPUT_COST_PER_1M) / 1_000_000
            output_cost = (output_tokens * settings.OPENAI_OUTPUT_COST_PER_1M) / 1_000_000
            return input_cost + output_cost
        elif "gpt-4o-mini" in model.lower():
            # Mini pricing: $0.15 input, $0.60 output per 1M
            input_cost = (input_tokens * 0.15) / 1_000_000
            output_cost = (output_tokens * 0.60) / 1_000_000
            return input_cost + output_cost
        else:
            logger.warning(f"Unknown model pricing: {model}")
            return 0.0

    def _log_rate_limit(
        self,
        db: Session,
        limit_type: str,
        current_value: int,
        limit_value: int,
        document_id: Optional[str]
    ) -> None:
        """Log rate limit events for monitoring"""
        log = APIUsageLog(
            endpoint="rate_limiter",
            document_id=document_id or "system",
            document_type="rate_limit",
            model="n/a",
            tokens_input=0,
            tokens_output=0,
            total_tokens=0,
            cost_usd=0.0,
            status="rate_limited",
            error_message=f"{limit_type.upper()} limit: {current_value}/{limit_value}"
        )
        db.add(log)
        db.commit()

    def get_usage_stats(self, db: Session) -> dict:
        """
        Get current usage statistics
        
        Returns:
            {
                "minute": {"requests": X, "tokens": Y},
                "day": {"requests": Z, "cost": $W}
            }
        """
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(seconds=60)
        one_day_ago = now - timedelta(hours=24)

        # Minute stats
        minute_requests = db.query(func.count(APIUsageLog.id)).filter(
            APIUsageLog.timestamp >= one_minute_ago,
            APIUsageLog.status == "success"
        ).scalar() or 0

        minute_tokens = db.query(func.sum(APIUsageLog.total_tokens)).filter(
            APIUsageLog.timestamp >= one_minute_ago,
            APIUsageLog.status == "success"
        ).scalar() or 0

        # Day stats
        daily_requests = db.query(func.count(APIUsageLog.id)).filter(
            APIUsageLog.timestamp >= one_day_ago,
            APIUsageLog.status == "success"
        ).scalar() or 0

        daily_cost = db.query(func.sum(APIUsageLog.cost_usd)).filter(
            APIUsageLog.timestamp >= one_day_ago,
            APIUsageLog.status == "success"
        ).scalar() or 0.0

        return {
            "minute": {
                "requests": minute_requests,
                "tokens": minute_tokens,
                "rpm_limit": self.rpm_limit,
                "tpm_limit": self.tpm_limit
            },
            "day": {
                "requests": daily_requests,
                "cost_usd": float(daily_cost),
                "rpd_limit": self.rpd_limit
            }
        }
