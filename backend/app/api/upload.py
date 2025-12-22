"""
Clean, RESTful upload endpoints with semantic URLs
Pattern: /upload/{file_type}/{format}
Examples: /upload/image/jpg, /upload/pdf, /upload/text
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Literal
from pydantic import BaseModel
import logging
import uuid

from app.utils.database import get_db
from app.services.minio_service import get_storage_service
from app.models.models import Document

router = APIRouter(prefix="/api/upload", tags=["upload"])
# DO NOT initialize minio_service here - it will be called lazily in functions
logger = logging.getLogger(__name__)

# Type definitions for clean URLs
ImageFormat = Literal["jpg", "jpeg", "png", "heic"]
DocumentFormat = Literal["pdf", "txt"]

class PresignedURLRequest(BaseModel):
    claim_id: str
    filename: str
    document_type: str  # prescription, bill, report, etc.

class PresignedURLResponse(BaseModel):
    file_id: str
    upload_url: str
    object_name: str
    expires_in: int


# ============= IMAGE UPLOADS =============

@router.post("/image/{format}", response_model=PresignedURLResponse)
async def upload_image(
    format: ImageFormat,
    request: PresignedURLRequest,
    db: Session = Depends(get_db)
):
    """
    Generate presigned URL for image upload
    
    Endpoints:
    - POST /api/upload/image/jpg
    - POST /api/upload/image/jpeg
    - POST /api/upload/image/png
    - POST /api/upload/image/heic
    """
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "heic": "image/heic"
    }
    
    return await _generate_presigned_url(
        claim_id=request.claim_id,
        filename=request.filename,
        document_type=request.document_type,
        content_type=content_type_map[format],
        file_extension=format,
        db=db
    )


# ============= PDF UPLOADS =============

@router.post("/pdf", response_model=PresignedURLResponse)
async def upload_pdf(
    request: PresignedURLRequest,
    db: Session = Depends(get_db)
):
    """
    Generate presigned URL for PDF upload
    
    Endpoint: POST /api/upload/pdf
    """
    return await _generate_presigned_url(
        claim_id=request.claim_id,
        filename=request.filename,
        document_type=request.document_type,
        content_type="application/pdf",
        file_extension="pdf",
        db=db
    )


# ============= TEXT UPLOADS =============

@router.post("/text", response_model=PresignedURLResponse)
async def upload_text(
    request: PresignedURLRequest,
    db: Session = Depends(get_db)
):
    """
    Generate presigned URL for text file upload
    
    Endpoint: POST /api/upload/text
    """
    return await _generate_presigned_url(
        claim_id=request.claim_id,
        filename=request.filename,
        document_type=request.document_type,
        content_type="text/plain",
        file_extension="txt",
        db=db
    )


# ============= GENERIC UPLOAD (FALLBACK) =============

@router.post("/other", response_model=PresignedURLResponse)
async def upload_other(
    request: PresignedURLRequest,
    db: Session = Depends(get_db)
):
    """
    Generate presigned URL for other file types
    
    Endpoint: POST /api/upload/other
    """
    # Detect extension from filename
    file_extension = request.filename.split('.')[-1].lower()
    
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "heic": "image/heic",
        "pdf": "application/pdf",
        "txt": "text/plain"
    }
    
    content_type = content_type_map.get(file_extension, "application/octet-stream")
    
    return await _generate_presigned_url(
        claim_id=request.claim_id,
        filename=request.filename,
        document_type=request.document_type,
        content_type=content_type,
        file_extension=file_extension,
        db=db
    )


# ============= BATCH UPLOAD =============

class BatchUploadRequest(BaseModel):
    claim_id: str
    files: List[PresignedURLRequest]

@router.post("/batch", response_model=List[PresignedURLResponse])
async def upload_batch(
    request: BatchUploadRequest,
    db: Session = Depends(get_db)
):
    """
    Generate presigned URLs for multiple files at once
    
    Endpoint: POST /api/upload/batch
    
    Request body:
    {
        "claim_id": "CLM_12345",
        "files": [
            {"filename": "prescription.jpg", "document_type": "prescription"},
            {"filename": "bill.pdf", "document_type": "bill"}
        ]
    }
    """
    presigned_urls = []
    
    for file_req in request.files:
        # Detect file type from extension
        file_extension = file_req.filename.split('.')[-1].lower()
        
        content_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "heic": "image/heic",
            "pdf": "application/pdf",
            "txt": "text/plain"
        }
        
        content_type = content_type_map.get(file_extension, "application/octet-stream")
        
        url_response = await _generate_presigned_url(
            claim_id=request.claim_id,
            filename=file_req.filename,
            document_type=file_req.document_type,
            content_type=content_type,
            file_extension=file_extension,
            db=db
        )
        
        presigned_urls.append(url_response)
    
    return presigned_urls


# ============= HELPER FUNCTION =============

async def _generate_presigned_url(
    claim_id: str,
    filename: str,
    document_type: str,
    content_type: str,
    file_extension: str,
    db: Session
) -> PresignedURLResponse:
    """
    Internal helper to generate presigned URL and create document record
    """
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Create object name with clean structure
    # Format: claims/{claim_id}/{document_type}/{file_id}.{extension}
    object_name = f"claims/{claim_id}/{document_type}/{file_id}.{file_extension}"
    
    # Generate presigned URL from MinIO
    minio_service = get_storage_service()
    upload_url = minio_service.generate_presigned_upload_url(object_name)
    
    # Note: Document record will be created after successful upload
    # For now, just return the presigned URL
    
    return PresignedURLResponse(
        file_id=file_id,
        upload_url=upload_url,
        object_name=object_name,
        expires_in=3600  # 1 hour
    )


# ============= UPLOAD COMPLETE CALLBACK =============

class UploadCompleteRequest(BaseModel):
    file_id: str
    object_name: str

@router.post("/complete")
async def upload_complete(
    request: UploadCompleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Mark file as uploaded and trigger OCR + Qdrant embedding
    
    Endpoint: POST /api/upload/complete
    
    Called by frontend after successful PUT to MinIO
    """
    # Find document record
    document = db.query(Document).filter(
        Document.document_id == request.file_id
    ).first()
    
    if not document:
        raise HTTPException(404, "Document not found")
    
    # Generate download URL
    minio_service = get_storage_service()
    download_url = minio_service.generate_presigned_download_url(request.object_name)
    document.file_url = download_url
    document.file_path = request.object_name
    
    db.commit()
    
    # Process document in background (async, non-blocking)
    background_tasks.add_task(
        process_document_background,
        file_id=request.file_id,
        object_name=request.object_name
    )
    
    return {
        "status": "processing",
        "file_id": request.file_id,
        "message": "Document uploaded successfully. OCR and embedding in progress."
    }

async def process_document_background(file_id: str, object_name: str):
    """
    Background task to process document
    - Download from MinIO
    - Extract text (OCR)
    - Generate embedding
    - Store in Qdrant
    """
    from app.utils.database import SessionLocal
    from app.services.document_processor import DocumentProcessor
    
    db = SessionLocal()
    try:
        logger.info(f"[BACKGROUND] Processing document: {file_id}")
        
        # Get document
        document = db.query(Document).filter(
            Document.document_id == file_id
        ).first()
        
        if not document:
            logger.error(f"[BACKGROUND] Document not found: {file_id}")
            return
        
        # Update status
        document.status = "processing"
        db.commit()
        
        # Process document
        processor = DocumentProcessor()
        result = await processor.process_document(
            file_id=file_id,
            object_name=object_name,
            document_type=document.document_type
        )
        
        # Update document with results
        document.extracted_data = result.get("structured_data", {})
        document.status = "processed"
        db.commit()
        
        logger.info(f"[BACKGROUND] ✅ Processed: {file_id}")
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Error processing {file_id}: {str(e)}")
        if document:
            document.status = "failed"
            db.commit()
    finally:
        db.close()
