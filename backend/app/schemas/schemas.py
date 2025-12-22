from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class DecisionType(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class DocumentType(str, Enum):
    PRESCRIPTION = "prescription"
    BILL = "bill"
    TEST_REPORT = "test_report"

class TreatmentType(str, Enum):
    CONSULTATION = "consultation"
    DIAGNOSTIC = "diagnostic"
    PHARMACY = "pharmacy"
    DENTAL = "dental"
    VISION = "vision"
    ALTERNATIVE_MEDICINE = "alternative_medicine"

# PolicyTerms Schemas
class PolicyTermsResponse(BaseModel):
    id: int
    policy_id: str
    policy_name: str
    annual_limit: float
    per_claim_limit: float
    consultation_limit: float
    diagnostic_limit: float
    pharmacy_limit: float
    dental_limit: float
    vision_limit: float
    minimum_claim_amount: float
    submission_timeline_days: int
    exclusions: List[str]
    network_providers: List[str]
    
    class Config:
        from_attributes = True

# Dependent Schemas
class DependentCreate(BaseModel):
    dependent_name: str
    relationship_type: str
    date_of_birth: datetime
    gender: str

class DependentResponse(BaseModel):
    id: int
    dependent_id: str
    policy_holder_id: str
    dependent_name: str
    relationship_type: str
    date_of_birth: datetime
    gender: str
    
    class Config:
        from_attributes = True

# PolicyHolder Schemas (Enhanced)
class PolicyHolderCreate(BaseModel):
    policy_holder_id: Optional[str] = None  # Auto-generated if not provided
    policy_holder_name: str
    date_of_birth: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    join_date: Optional[str] = None
    policy_terms_id: Optional[str] = None  # Allow NULL
    policy_start_date: Optional[str] = None
    annual_limit: Optional[float] = None
    annual_limit_used: Optional[float] = None
    waiting_period_completed: Optional[bool] = None
    pre_existing_conditions: Optional[List[str]] = []

class PolicyHolderResponse(BaseModel):
    id: int
    policy_holder_id: Optional[str] = None
    policy_holder_name: str
    dob: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    join_date: Optional[datetime] = None
    policy_status: str
    policy_start_date: datetime
    waiting_period_completed: bool
    annual_limit: float
    annual_limit_used: float
    pre_existing_conditions: List[str]
    
    class Config:
        from_attributes = True

# Claim Schemas (Enhanced)
class ClaimCreate(BaseModel):
    policy_holder_id: str
    treatment_date: Optional[datetime] = None
    treatment_type: Optional[str] = None
    claimed_amount: float
    provider_name: Optional[str] = None
    provider_network: Optional[bool] = False
    doctor_name: Optional[str] = None
    doctor_registration_number: Optional[str] = None
    diagnosis: Optional[str] = None

class ClaimResponse(BaseModel):
    id: int
    claim_id: str
    policy_holder_id: str
    policy_holder_name: str
    treatment_date: datetime
    treatment_type: Optional[str]
    treatment_category: Optional[str]
    submission_date: datetime
    
    # Financial
    claimed_amount: float
    eligible_amount: Optional[float]
    co_payment_amount: float
    approved_amount: float
    deductions: Dict[str, Any]
    
    # Provider
    provider_name: Optional[str]
    provider_network: bool
    doctor_name: Optional[str]
    doctor_registration_number: Optional[str]
    
    # Status
    status: str
    decision: Optional[DecisionType]
    processed_at: Optional[datetime]
    
    # Decision details
    confidence_score: Optional[float]
    rejection_reasons: List[str]
    notes: Optional[str]
    next_steps: Optional[str]
    
    # Validation
    fraud_indicators: List[str]
    validation_errors: List[str]
    
    created_at: datetime
    
    class Config:
        from_attributes = True

class AdjudicationResult(BaseModel):
    claim_id: str
    decision: DecisionType
    approved_amount: float
    rejection_reasons: List[str]
    confidence_score: float
    notes: str
    next_steps: str
    deductions: Optional[Dict[str, float]] = None
    co_payment_amount: Optional[float] = 0.0
    eligible_amount: Optional[float] = 0.0

# Document Schemas (Enhanced)
class DocumentUpload(BaseModel):
    document_type: DocumentType

class DocumentResponse(BaseModel):
    id: int
    document_id: str
    claim_id: str
    document_type: str
    file_path: str
    file_url: Optional[str]
    status: str
    ocr_text: Optional[str]
    extracted_data: Dict[str, Any]
    quality_score: Optional[float]
    is_legible: bool
    validation_errors: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Extracted Data Schemas
class PrescriptionData(BaseModel):
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines: List[Dict[str, str]] = []
    tests_advised: List[str] = []
    date: Optional[str] = None

class BillData(BaseModel):
    bill_number: Optional[str] = None
    hospital_name: Optional[str] = None
    patient_name: Optional[str] = None
    date: Optional[str] = None
    consultation_fee: Optional[float] = None
    diagnostic_tests: Optional[float] = None
    medicines: Optional[float] = None
    total_amount: Optional[float] = None
    items: List[Dict[str, Any]] = []

# Manual Review Schemas
class ManualReviewCreate(BaseModel):
    claim_id: str
    reason_for_review: str
    review_notes: Optional[str] = None

class ManualReviewUpdate(BaseModel):
    reviewer_id: str
    review_status: str
    review_notes: Optional[str] = None
    final_decision: Optional[str] = None

class ManualReviewResponse(BaseModel):
    id: int
    claim_id: str
    reviewer_id: Optional[str]
    review_status: str
    reason_for_review: Optional[str]
    review_notes: Optional[str]
    original_decision: str
    final_decision: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Claim Decision Schemas
class ClaimDecisionResponse(BaseModel):
    """Response schema for claim adjudication decision"""
    claim_id: str
    decision: DecisionType
    approved_amount: float
    original_amount: float
    rejection_reasons: List[str] = []
    confidence_score: float
    notes: Optional[str] = None
    next_steps: Optional[str] = None
    
    # Validation details
    eligibility_passed: bool
    documents_valid: bool
    coverage_verified: bool
    limits_ok: bool
    medically_necessary: bool
    fraud_indicators: List[str] = []
    
    # Calculation details
    copay_amount: float = 0.0
    copay_percentage: float = 0.0
    
    # Audit
    adjudicated_at: datetime
    adjudicated_by: str = "SYSTEM"
    
    class Config:
        from_attributes = True


class AdjudicationRequest(BaseModel):
    """Request to trigger adjudication"""
    claim_id: str
    force_reprocess: bool = False


class ManualReviewOverride(BaseModel):
    """Manual review override by human reviewer"""
    reviewer_id: str
    new_decision: DecisionType
    approved_amount: Optional[float] = None
    review_notes: str
    reason: str

