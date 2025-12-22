# This file makes the schemas directory a Python package
from app.schemas.schemas import (
    ClaimCreate, ClaimResponse, AdjudicationResult,
    DocumentUpload, DocumentResponse,
    PolicyHolderCreate, PolicyHolderResponse,
    PolicyTermsResponse,
    DependentCreate, DependentResponse,
    PrescriptionData, BillData,
    ManualReviewCreate, ManualReviewUpdate, ManualReviewResponse,
    DecisionType, DocumentType, TreatmentType
)
