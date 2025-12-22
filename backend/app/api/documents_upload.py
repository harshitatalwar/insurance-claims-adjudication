"""
Enhanced Document Upload API with Auto-Classification
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import logging

from app.utils.database import get_db
from app.services.minio_service import get_storage_service
from app.services.document_classifier import DocumentClassifier
from app.models.models import Document, Claim

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)


class DocumentUploadRequest(BaseModel):
    claim_id: str
    filename: str
    document_type: Optional[str] = "auto"  # auto, prescription, bill, report


class DocumentUploadResponse(BaseModel):
    file_id: str
    upload_url: str
    object_name: str
    document_type: str
    expires_in: int


class DocumentStatusResponse(BaseModel):
    file_id: str
    filename: str
    document_type: str
    status: str
    uploaded_at: Optional[datetime]
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    confidence_score: Optional[float]
    error_message: Optional[str]
    extracted_data: Optional[dict]


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: DocumentUploadRequest,
    db: Session = Depends(get_db)
):
    """
    Generate presigned URL for document upload with auto-classification
    
    - Accepts any file type (images, PDFs, docs)
    - Auto-classifies document type if not provided
    - Organizes files in MinIO: claims/{claim_id}/{doc_type}/{file_id}.ext
    """
    # Verify claim exists
    claim = db.query(Claim).filter(Claim.claim_id == request.claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {request.claim_id} not found")
    
    # Auto-classify document type if needed
    if request.document_type == "auto":
        doc_type = DocumentClassifier.classify_by_filename(request.filename)
        if not doc_type:
            doc_type = "other"
    else:
        doc_type = request.document_type
    
    # Generate unique file ID
    file_id = f"DOC{uuid.uuid4().hex[:10].upper()}"
    
    # Get file extension
    import os
    file_ext = os.path.splitext(request.filename)[1]
    
    # Create object path: claims/{claim_id}/{doc_type}/{file_id}.ext
    object_name = f"claims/{request.claim_id}/{doc_type}/{file_id}{file_ext}"
    
    # Determine content type
    content_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    content_type = content_type_map.get(file_ext.lower(), 'application/octet-stream')
    
    # Generate presigned URL
    try:
        minio_service = get_storage_service()
        upload_url = minio_service.generate_presigned_upload_url(
            object_name=object_name
        )
    except Exception as e:
        logger.error(f"MinIO error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
    
    # Create document record
    document = Document(
        document_id=file_id,
        claim_id=request.claim_id,
        file_path=object_name,
        file_url=upload_url.split('?')[0],  # Store URL without query params
        document_type=doc_type,
        status="uploaded",
        created_at=datetime.utcnow()
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return DocumentUploadResponse(
        file_id=file_id,
        upload_url=upload_url,
        object_name=object_name,
        document_type=doc_type,
        expires_in=3600
    )


@router.get("/status", response_model=list[DocumentStatusResponse])
async def get_documents_status(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Get status of all documents for a claim
    Used by frontend for real-time polling
    """
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()
    
    return [
        DocumentStatusResponse(
            file_id=doc.document_id,
            filename=doc.file_path.split('/')[-1] if doc.file_path else "unknown",
            document_type=doc.document_type or "other",
            status=doc.status or "uploaded",
            uploaded_at=doc.created_at,
            processing_started_at=getattr(doc, 'processing_started_at', None),
            processing_completed_at=getattr(doc, 'processing_completed_at', None),
            confidence_score=getattr(doc, 'confidence_score', None),
            error_message=getattr(doc, 'error_message', None),
            extracted_data=doc.extracted_data
        )
        for doc in documents
    ]


@router.get("/{file_id}", response_model=DocumentStatusResponse)
async def get_document_status(
    file_id: str,
    db: Session = Depends(get_db)
):
    """Get status of a specific document"""
    document = db.query(Document).filter(Document.document_id == file_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentStatusResponse(
        file_id=document.document_id,
        filename=document.file_path.split('/')[-1] if document.file_path else "unknown",
        document_type=document.document_type or "other",
        status=document.status or "uploaded",
        uploaded_at=document.created_at,
        processing_started_at=getattr(document, 'processing_started_at', None),
        processing_completed_at=getattr(document, 'processing_completed_at', None),
        confidence_score=getattr(document, 'confidence_score', None),
        error_message=getattr(document, 'error_message', None),
        extracted_data=document.extracted_data
    )
