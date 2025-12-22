"""
Celery Worker for Async Document Processing
Handles OCR and LLM extraction in background
"""
from celery import Celery
from celery.signals import worker_ready
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Redis client for Pub/Sub
import redis
import json
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def publish_update(claim_id: str, message: dict):
    """Publish real-time update to the specific claim channel"""
    if not claim_id:
        return
        
    channel = f"claim_updates:{claim_id}"
    try:
        redis_client.publish(channel, json.dumps(message))
        logger.info(f"📡 Published update to {channel}: {message.get('type')}")
    except Exception as e:
        logger.error(f"Failed to publish update: {e}")

# Initialize Celery app
celery_app = Celery(
    "opd_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Rate Limiting: Prevent OpenAI API spam
    task_annotations={
        'app.worker.process_document_task': {
            'rate_limit': '20/m'  # Max 20 tasks per minute
        }
    },
    
    # Task routing
    task_routes={
        # 'app.worker.process_document_task': {'queue': 'document_processing'}
    },
    
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
)


@celery_app.task(name="process_document_task", bind=True, max_retries=3)
def process_document_task(self, file_id: str, file_path: str, document_type: str):
    """
    Celery task for document processing
    - Downloads from MinIO
    - Runs Tesseract + OpenAI Vision OCR
    - Extracts structured JSON
    - Updates database
    
    Args:
        file_id: Document ID
        file_path: MinIO object path
        document_type: prescription, bill, report, etc.
    """
    try:
        logger.info(f"🚀 Starting OCR processing for {file_id}")
        
        # Import here to avoid circular dependencies
        from app.services.document_processor import DocumentProcessor
        from app.models.models import Document
        from app.utils.database import SessionLocal
        from datetime import datetime
        import json # Added for json.dumps
        
        # Create new database session
        db = SessionLocal()
        
        try:
            # Get document record
            document = db.query(Document).filter(Document.document_id == file_id).first()
            if not document:
                logger.error(f"❌ Document {file_id} not found in database")
                return {"status": "failed", "error": "Document not found"}
            
            # Process with GPT-4o Vision
            logger.info(f"🔍 Processing with GPT-4o Vision: {file_id}")
            processor = DocumentProcessor()
            
            # Create event loop for async operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                processor.process_document(file_id, file_path, document_type)
            )
            loop.close()
            
            # Update document with results
            document.ocr_text = json.dumps(result.get("extracted_data", {}))
            document.extracted_data = result.get("extracted_data", {})
            document.quality_score = result.get("confidence_score", 0.95)
            document.status = "processed"
            document.processed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"✅ Successfully processed {file_id}")
            logger.info(f"   - Document Type: {document_type}")
            logger.info(f"   - Quality Score: {document.quality_score}")
            
            # Trigger adjudication if claim_id exists
            if document.claim_id:
                # Publish document update
                status_update = {
                    "type": "document_update",
                    "file_id": document.document_id,
                    "status": document.status,
                    "extracted_data": document.extracted_data
                }
                publish_update(document.claim_id, status_update)
                
                logger.info(f"🔍 Triggering adjudication for claim {document.claim_id}")
                adjudicate_claim_task.delay(document.claim_id)
            
            return {
                "status": "processed",
                "file_id": file_id,
                "document_type": document_type,
                "quality_score": document.quality_score
            }
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error processing {file_id}: {e}")
        
        # Update document status to failed
        try:
            db = SessionLocal()
            document = db.query(Document).filter(Document.document_id == file_id).first()
            if document:
                document.status = "failed"
                document.validation_errors = [{"error": str(e), "timestamp": datetime.utcnow().isoformat()}]
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")
        
        # Don't retry for quota errors - retrying won't help
        if "insufficient_quota" in str(e):
            logger.error(f"❌ Insufficient quota - please add credits to OpenAI account")
            return {"status": "failed", "error": "insufficient_quota"}
        
        # Retry with exponential backoff for other errors
        try:
            # Retry in 60, 120, 240 seconds
            countdown = 60 * (2 ** self.request.retries)
            logger.info(f"⏳ Retrying in {countdown} seconds (attempt {self.request.retries + 1}/3)")
            raise self.retry(exc=e, countdown=countdown, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for {file_id}")
            return {"status": "failed", "error": str(e)}


@celery_app.task(name="adjudicate_claim_task", bind=True, max_retries=3)
def adjudicate_claim_task(self, claim_id: str):
    """
    Celery task for automated claim adjudication
    Triggered after OCR processing completes
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        Decision summary
    """
    from app.models.models import Claim, PolicyHolder, Document, ClaimDecision
    from app.services.adjudication_engine import AdjudicationEngine
    from app.utils.database import SessionLocal
    from datetime import datetime
    
    logger.info(f"🔍 Starting adjudication task for claim {claim_id}")
    
    try:
        db = SessionLocal()
        
        try:
            # Get claim
            claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
            if not claim:
                logger.error(f"❌ Claim {claim_id} not found")
                return {"status": "error", "message": "Claim not found"}
            
            # Get policy holder
            policy_holder = db.query(PolicyHolder).filter(
                PolicyHolder.policy_holder_id == claim.policy_holder_id
            ).first()
            if not policy_holder:
                logger.error(f"❌ Policy holder not found for claim {claim_id}")
                return {"status": "error", "message": "Policy holder not found"}
            
            # Get extracted data from documents
            documents = db.query(Document).filter(Document.claim_id == claim_id).all()
            if not documents:
                logger.warning(f"⚠️  No documents found for claim {claim_id}")
                return {"status": "error", "message": "No documents found"}
            
            # Combine extracted data
            extracted_data = {}
            for doc in documents:
                if doc.extracted_data:
                    extracted_data.update(doc.extracted_data)
            
            if not extracted_data:
                logger.warning(f"⚠️  No extracted data for claim {claim_id}")
                return {"status": "error", "message": "No extracted data"}
            
            # Build comprehensive policy context (runtime only - NOT stored in DB)
            policy_context = {
                "policy_holder_id": policy_holder.policy_holder_id,
                "policy_holder_name": policy_holder.policy_holder_name,
                "dob": policy_holder.dob,
                "policy_status": policy_holder.policy_status.value if hasattr(policy_holder.policy_status, 'value') else str(policy_holder.policy_status),
                "policy_start_date": policy_holder.policy_start_date.isoformat() if policy_holder.policy_start_date else None,
                "join_date": policy_holder.join_date.isoformat() if policy_holder.join_date else None,
                "annual_limit": policy_holder.annual_limit,
                "annual_limit_used": policy_holder.annual_limit_used,
                "annual_limit_remaining": policy_holder.annual_limit - policy_holder.annual_limit_used,
                "waiting_period_completed": policy_holder.waiting_period_completed,
                "pre_existing_conditions": policy_holder.pre_existing_conditions or []
            }
            
            logger.info(f"📋 Loaded policy terms: {engine.policy_terms.get('policy_id', 'Unknown')}")
            
            # Build adjudication context (runtime merge - separation of concerns)
            adjudication_context = {
                "policy_context": policy_context,      # From DB (runtime only)
                "claim_evidence": extracted_data,      # From OCR (stored in DB)
                "policy_terms": engine.policy_terms    # From policy_terms.json
            }
            
            # Run adjudication with full context
            engine = AdjudicationEngine()
            decision = asyncio.run(engine.adjudicate_claim(claim_id, adjudication_context))
            
            # Check if decision already exists
            existing_decision = db.query(ClaimDecision).filter(
                ClaimDecision.claim_id == claim_id
            ).first()
            
            if existing_decision:
                # Update existing
                for key, value in decision.__dict__.items():
                    if not key.startswith('_'):
                        setattr(existing_decision, key, value)
                db.commit()
                logger.info(f"✅ Updated decision for claim {claim_id}: {existing_decision.decision}")
            else:
                # Save new decision
                db.add(decision)
                db.commit()
                db.refresh(decision)
                logger.info(f"✅ Created decision for claim {claim_id}: {decision.decision}")
            
            # Update claim status
            claim.status = decision.decision.value.lower()
            claim.decision = decision.decision
            claim.approved_amount = decision.approved_amount
            claim.confidence_score = decision.confidence_score
            claim.rejection_reasons = decision.rejection_reasons
            claim.notes = decision.notes
            claim.next_steps = decision.next_steps
            claim.processed_at = datetime.utcnow()
            db.commit()
            
            # Publish adjudication update
            decision_update = {
                "type": "claim_decision",
                "claim_id": claim.claim_id,
                "decision": decision.decision.value if hasattr(decision.decision, 'value') else decision.decision,
                "status": claim.status,
                "confidence_score": claim.confidence_score,
                "approved_amount": claim.approved_amount
            }
            publish_update(claim_id, decision_update)
            
            logger.info(f"✅ Adjudication complete for claim {claim_id}")
            return {
                "status": "success",
                "claim_id": claim_id,
                "decision": decision.decision.value,
                "approved_amount": decision.approved_amount,
                "confidence_score": decision.confidence_score
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Adjudication task failed for claim {claim_id}: {e}")
        
        # Retry with exponential backoff
        try:
            countdown = 60 * (2 ** self.request.retries)
            logger.info(f"⏳ Retrying adjudication in {countdown} seconds")
            raise self.retry(exc=e, countdown=countdown, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for claim {claim_id}")
            return {"status": "failed", "error": str(e)}

            
    except Exception as e:
        logger.error(f"❌ Error processing {file_id}: {str(e)}")
        
        # Update document status to failed
        try:
            db = SessionLocal()
            document = db.query(Document).filter(Document.document_id == file_id).first()
            if document:
                document.status = "failed"
                # Store error in validation_errors JSON field
                document.validation_errors = [{"error": str(e), "timestamp": datetime.utcnow().isoformat()}]
                document.processed_at = datetime.utcnow()
                db.commit()
            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")
        
        # Don't retry for quota errors - retrying won't help
        if "insufficient_quota" in str(e):
            logger.error(f"❌ Insufficient quota - please add credits to OpenAI account")
            return {"status": "failed", "error": "insufficient_quota"}
        
        # Retry with exponential backoff for other errors
        try:
            # Retry in 60, 120, 240 seconds
            countdown = 60 * (2 ** self.request.retries)
            logger.info(f"⏳ Retrying in {countdown} seconds (attempt {self.request.retries + 1}/3)")
            raise self.retry(exc=e, countdown=countdown, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for {file_id}")
            return {"status": "failed", "error": str(e)}


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Called when Celery worker is ready"""
    logger.info("🎉 Celery worker is ready and waiting for tasks!")
    logger.info(f"📡 Connected to Redis: {REDIS_URL}")
    logger.info(f"⚙️  Rate limit: 20 tasks/minute")
