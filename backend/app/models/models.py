from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Enum as SQLEnum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.utils.database import Base

# Enums
class DecisionType(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class PolicyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class TreatmentType(str, enum.Enum):
    CONSULTATION = "consultation"
    DIAGNOSTIC = "diagnostic"
    PHARMACY = "pharmacy"
    DENTAL = "dental"
    VISION = "vision"
    ALTERNATIVE_MEDICINE = "alternative_medicine"

# Policy Terms Model
class PolicyTerms(Base):
    __tablename__ = "policy_terms"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(String, unique=True, index=True)
    policy_name = Column(String)
    effective_date = Column(DateTime)
    
    # Limits
    annual_limit = Column(Float, default=50000.0)
    per_claim_limit = Column(Float, default=5000.0)
    family_floater_limit = Column(Float, default=150000.0)
    
    # Sub-limits by category
    consultation_limit = Column(Float, default=2000.0)
    diagnostic_limit = Column(Float, default=10000.0)
    pharmacy_limit = Column(Float, default=15000.0)
    dental_limit = Column(Float, default=10000.0)
    vision_limit = Column(Float, default=5000.0)
    alternative_medicine_limit = Column(Float, default=8000.0)
    
    # Co-payment percentages
    consultation_copay = Column(Float, default=10.0)
    network_discount = Column(Float, default=20.0)
    branded_drugs_copay = Column(Float, default=30.0)
    
    # Waiting periods (in days)
    initial_waiting_period = Column(Integer, default=30)
    pre_existing_waiting_period = Column(Integer, default=365)
    maternity_waiting_period = Column(Integer, default=270)
    
    # JSON fields
    exclusions = Column(JSON, default=list)
    covered_services = Column(JSON, default=dict)
    network_providers = Column(JSON, default=list)
    specific_ailment_waiting = Column(JSON, default=dict)  # {"diabetes": 90, "hypertension": 90}
    
    # Requirements
    minimum_claim_amount = Column(Float, default=500.0)
    submission_timeline_days = Column(Integer, default=30)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Dependent Model
class Dependent(Base):
    __tablename__ = "dependents"
    
    id = Column(Integer, primary_key=True, index=True)
    dependent_id = Column(String, unique=True, index=True)
    policy_holder_id = Column(String, ForeignKey("policy_holders.policy_holder_id"))
    dependent_name = Column(String)
    relationship_type = Column(String)  # spouse, child, parent
    date_of_birth = Column(DateTime)
    gender = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    policy_holder = relationship("PolicyHolder", back_populates="dependents")

# PolicyHolder Model (Enhanced)
class PolicyHolder(Base):
    __tablename__ = "policy_holders"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_holder_id = Column(String, unique=True, index=True)
    policy_holder_name = Column(String)
    
    # Contact Information
    dob = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True, index=True)  # Made unique for auth
    phone = Column(String, nullable=True)
    
    # Authentication fields (NEW)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    join_date = Column(DateTime)
    
    # Policy details
    policy_terms_id = Column(String, ForeignKey("policy_terms.policy_id"), nullable=True)
    policy_status = Column(SQLEnum(PolicyStatus), default=PolicyStatus.ACTIVE)
    policy_start_date = Column(DateTime, default=datetime.utcnow)
    waiting_period_completed = Column(Boolean, default=False)
    
    # Limits tracking
    annual_limit = Column(Float, default=50000.0)
    annual_limit_used = Column(Float, default=0.0)
    family_floater_limit = Column(Float, default=150000.0)
    
    # Medical history
    pre_existing_conditions = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    claims = relationship("Claim", back_populates="policy_holder")
    dependents = relationship("Dependent", back_populates="policy_holder")
    policy_terms = relationship("PolicyTerms", foreign_keys=[policy_terms_id])

# Claim Model (Enhanced)
class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, unique=True, index=True)
    policy_holder_id = Column(String, ForeignKey("policy_holders.policy_holder_id"), index=True)
    policy_holder_name = Column(String)
    
    # Treatment details
    treatment_date = Column(DateTime)
    treatment_type = Column(String, nullable=True)  # consultation, diagnostic, pharmacy, dental, vision
    treatment_category = Column(String, nullable=True)  # For sub-limit tracking
    diagnosis = Column(String, nullable=True)
    
    # Provider details
    provider_name = Column(String, nullable=True)
    provider_type = Column(String, nullable=True)  # hospital, clinic, pharmacy
    provider_network = Column(Boolean, default=False)
    doctor_name = Column(String, nullable=True)
    doctor_registration_number = Column(String, nullable=True)
    
    # Financial details
    submission_date = Column(DateTime, default=datetime.utcnow)
    claimed_amount = Column(Float)  # Original claimed amount
    eligible_amount = Column(Float, nullable=True)  # After coverage check
    co_payment_amount = Column(Float, default=0.0)
    network_discount_amount = Column(Float, default=0.0)
    approved_amount = Column(Float, default=0.0)  # Final approved amount
    deductions = Column(JSON, default=dict)  # Detailed breakdown
    
    # Status tracking
    status = Column(String, default="pending")  # pending, processing, approved, rejected, manual_review
    decision = Column(SQLEnum(DecisionType), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Decision details
    confidence_score = Column(Float, nullable=True)
    rejection_reasons = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    
    # Validation
    submission_delay_days = Column(Integer, default=0)
    fraud_indicators = Column(JSON, default=list)
    validation_errors = Column(JSON, default=list)
    manual_review_reason = Column(String, nullable=True)
    
    # Extracted data from documents
    extracted_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="claim")
    policy_holder = relationship("PolicyHolder", back_populates="claims")

# Document Model (Enhanced)
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, unique=True, index=True)
    claim_id = Column(String, ForeignKey("claims.claim_id"))
    document_type = Column(String)  # prescription, bill, test_report
    file_path = Column(String)
    file_url = Column(String, nullable=True)
    
    # Processing status
    status = Column(String, default="pending")  # pending, processing, processed, failed
    ocr_text = Column(Text, nullable=True)
    extracted_data = Column(JSON, default=dict)
    quality_score = Column(Float, nullable=True)
    
    # Validation
    is_legible = Column(Boolean, default=True)
    validation_errors = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    claim = relationship("Claim", back_populates="documents")

# Manual Review Model
class ManualReview(Base):
    __tablename__ = "manual_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("claims.claim_id"))
    reviewer_id = Column(String, nullable=True)
    review_status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    review_notes = Column(Text, nullable=True)
    original_decision = Column(String)
    final_decision = Column(String, nullable=True)
    reason_for_review = Column(String, nullable=True)  # fraud_suspected, high_value, low_confidence
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


# Claim Decision Model - Detailed Adjudication Results
class ClaimDecision(Base):
    __tablename__ = "claim_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("claims.claim_id"), unique=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=True)
    
    # Decision outcome
    decision = Column(SQLEnum(DecisionType), nullable=False)
    approved_amount = Column(Float, default=0.0)
    original_amount = Column(Float)
    rejection_reasons = Column(JSON, default=list)  # List of rejection reason codes
    confidence_score = Column(Float)  # 0.0 to 1.0
    notes = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    
    # Detailed validation results
    eligibility_passed = Column(Boolean, default=False)
    documents_valid = Column(Boolean, default=False)
    coverage_verified = Column(Boolean, default=False)
    limits_ok = Column(Boolean, default=False)
    medically_necessary = Column(Boolean, default=False)
    fraud_indicators = Column(JSON, default=list)  # List of fraud flags
    
    # Calculation details
    copay_amount = Column(Float, default=0.0)
    copay_percentage = Column(Float, default=0.0)
    sub_limit_applied = Column(String, nullable=True)  # Which sub-limit was checked
    annual_limit_remaining = Column(Float, nullable=True)
    
    # Audit trail
    adjudicated_at = Column(DateTime, default=datetime.utcnow)
    adjudicated_by = Column(String, default="SYSTEM")  # "SYSTEM" or user_id
    reviewed_by = Column(String, nullable=True)  # For manual review override
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

