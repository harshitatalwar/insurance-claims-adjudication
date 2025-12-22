"""
Document Processing API - Celery-based async processing
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.models import Document
from app.utils.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{file_id}/process")
async def process_document(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Trigger OCR processing via Celery worker
    - Returns immediately (non-blocking)
    - Processing happens in background Celery worker
    - Frontend polls /api/documents/status for updates
    """
    # Get document record
    document = db.query(Document).filter(Document.document_id == file_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status to queued
    document.status = "processing"
    db.commit()
    
    # Dispatch to Celery worker (non-blocking)
    try:
        from app.worker import process_document_task
        
        task = process_document_task.delay(
            file_id=file_id,
            file_path=document.file_path,
            document_type=document.document_type or "other"
        )
        
        logger.info(f"✅ Queued document {file_id} for processing (Task ID: {task.id})")
        
        return {
            "file_id": file_id,
            "status": "processing",
            "message": "Document queued for Celery worker",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Failed to queue task: {e}")
        document.status = "failed"
        document.error_message = f"Failed to queue: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")
