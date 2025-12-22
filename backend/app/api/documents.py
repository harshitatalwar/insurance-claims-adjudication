from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import os
from datetime import datetime

from app.schemas import DocumentResponse
from app.models import Document, Claim
from app.utils.database import get_db
from app.services.document_processor import DocumentProcessor
from app.config import settings

router = APIRouter()

@router.post("/{claim_id}/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    claim_id: str,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document for a claim"""
    # Verify claim exists
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Save file
    file_extension = os.path.splitext(file.filename)[1]
    document_id = f"DOC_{uuid.uuid4().hex[:8].upper()}"
    file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}{file_extension}")
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Process document
    processor = DocumentProcessor()
    extracted_data = await processor.process_document(file_path, document_type)
    
    # Create document record
    db_document = Document(
        document_id=document_id,
        claim_id=claim_id,
        document_type=document_type,
        file_path=file_path,
        extracted_data=extracted_data,
        created_at=datetime.utcnow()
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return db_document

@router.get("/{claim_id}", response_model=List[DocumentResponse])
async def list_documents(claim_id: str, db: Session = Depends(get_db)):
    """List all documents for a claim"""
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()
    return documents

@router.get("/document/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get a specific document"""
    document = db.query(Document).filter(Document.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
