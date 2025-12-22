"""
Enums for the application
"""
import enum

class DocumentType(str, enum.Enum):
    """Document type enumeration"""
    PRESCRIPTION = "prescription"
    BILL = "bill"
    MEDICAL_REPORT = "medical_report"
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    OTHER = "other"

class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class ClaimStatus(str, enum.Enum):
    """Claim status enumeration"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_INFO = "pending_info"

class DecisionType(str, enum.Enum):
    """Claim decision type"""
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIAL = "partial"
    MANUAL_REVIEW = "manual_review"

class UserRole(str, enum.Enum):
    """User role enumeration"""
    USER = "user"  # Claimant/Provider
    ADMIN = "admin"  # Insurer/Adjudicator
    SUPER_ADMIN = "super_admin"
