"""
Unit Tests for Claims Adjudication Engine (Refactored)
Tests separate validators and main engine integration
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from app.services.adjudication_engine import AdjudicationEngine
from app.models.models import DecisionType
from app.services.validators.eligibility_validator import EligibilityValidator
from app.services.validators.document_validator import DocumentValidator
from app.services.validators.coverage_validator import CoverageValidator
from app.services.validators.limit_validator import LimitValidator
from app.services.validators.medical_necessity_validator import MedicalNecessityValidator
from app.services.validators.fraud_detector import FraudDetector


# --- Fixtures ---

@pytest.fixture
def engine():
    """Create AdjudicationEngine instance"""
    return AdjudicationEngine()

@pytest.fixture
def policy_terms():
    """Mock policy terms"""
    return {
        "policy_id": "OPD_GOLD_2024",
        "waiting_periods": {"initial_waiting": 30},
        "exclusions": ["Cosmetic procedure", "Weight loss treatment"],
        "coverage_details": {
            "annual_limit": 50000,
            "per_claim_limit": 5000,
            "consultation_fees": {"copay_percentage": 10},
        }
    }

@pytest.fixture
def active_policy_holder():
    """Mock active policy holder"""
    return {
        "policy_holder_id": "PH001",
        "policy_status": "ACTIVE",
        "policy_start_date": (datetime.now() - timedelta(days=60)).isoformat(),
        "annual_limit_used": 10000,
        "waiting_period_completed": True
    }

@pytest.fixture
def valid_prescription_data():
    """Mock valid prescription OCR data"""
    return {
        "document_type": "prescription",
        "patient_name": "John Doe",
        "doctor_name": "Dr. Smith",
        "doctor_registration_number": "MH/12345/2020",
        "date": datetime.now().isoformat(),
        "diagnosis": "Fever",
        "medicines": [
            {"name": "Paracetamol", "dosage": "500mg"}
        ],
        "total_amount": 1500,
        "treatment_type": "consultation"
    }

# --- Validator Unit Tests ---

class TestEligibilityValidator:
    """Test eligibility validation"""
    
    def test_active_policy_passes(self, active_policy_holder, valid_prescription_data, policy_terms):
        validator = EligibilityValidator()
        result = validator.validate(active_policy_holder, valid_prescription_data, policy_terms)
        assert result["passed"] is True
        assert len(result["errors"]) == 0
    
    def test_inactive_policy_fails(self, active_policy_holder, valid_prescription_data, policy_terms):
        validator = EligibilityValidator()
        active_policy_holder["policy_status"] = "INACTIVE"
        result = validator.validate(active_policy_holder, valid_prescription_data, policy_terms)
        assert result["passed"] is False
        assert "POLICY_INACTIVE" in result["errors"]
    
    def test_waiting_period_fails(self, active_policy_holder, valid_prescription_data, policy_terms):
        validator = EligibilityValidator()
        # Policy started only 10 days ago (< 30 day waiting period)
        active_policy_holder["policy_start_date"] = (datetime.now() - timedelta(days=10)).isoformat()
        result = validator.validate(active_policy_holder, valid_prescription_data, policy_terms)
        assert result["passed"] is False
        assert "WAITING_PERIOD_NOT_MET" in result["errors"]


class TestDocumentValidator:
    """Test document validation"""
    
    def test_complete_documents_pass(self, valid_prescription_data):
        validator = DocumentValidator()
        result = validator.validate(valid_prescription_data)
        assert result["passed"] is True
        assert len(result["errors"]) == 0
    
    def test_missing_patient_name_fails(self, valid_prescription_data):
        validator = DocumentValidator()
        del valid_prescription_data["patient_name"]
        result = validator.validate(valid_prescription_data)
        assert result["passed"] is False
        assert "MISSING_FIELD_PATIENT_NAME" in result["errors"]


class TestCoverageValidator:
    """Test coverage validation"""
    
    def test_covered_service_passes(self, valid_prescription_data, policy_terms):
        validator = CoverageValidator()
        result = validator.validate(valid_prescription_data, policy_terms)
        assert result["passed"] is True
    
    def test_excluded_service_fails(self, valid_prescription_data, policy_terms):
        validator = CoverageValidator()
        valid_prescription_data["diagnosis"] = "Cosmetic procedure"
        result = validator.validate(valid_prescription_data, policy_terms)
        assert result["passed"] is False
        assert "SERVICE_EXCLUDED" in result["errors"]


class TestLimitValidator:
    """Test limit validation"""
    
    def test_within_limits_passes(self, active_policy_holder, valid_prescription_data, policy_terms):
        validator = LimitValidator()
        result = validator.validate(1500, active_policy_holder, valid_prescription_data, policy_terms)
        assert result["passed"] is True
        assert result["approved_amount"] == 1350  # 1500 - 10%
        assert result["copay_amount"] == 150
    
    def test_exceeds_per_claim_limit_fails(self, active_policy_holder, valid_prescription_data, policy_terms):
        validator = LimitValidator()
        result = validator.validate(6000, active_policy_holder, valid_prescription_data, policy_terms)
        assert result["passed"] is False
        assert "PER_CLAIM_LIMIT_EXCEEDED" in result["errors"]
        # Assuming rejected if over limit, or capped? Validator logic says strict fail.
        # Check implementation: if errors, approved_amount = 0
        assert result["approved_amount"] == 0

class TestFraudDetector:
    """Test fraud detection"""
    
    def test_high_amount_flagged(self, active_policy_holder, valid_prescription_data):
        validator = FraudDetector()
        valid_prescription_data["total_amount"] = 25000
        result = validator.detect(valid_prescription_data, active_policy_holder)
        assert result["suspicious"] is True
        assert "HIGH_VALUE_CLAIM" in result["indicators"]


# --- Engine Integration Tests ---

class TestAdjudicationEngine:
    """Test complete adjudication flow"""
    
    @pytest.mark.asyncio
    async def test_approved_claim(self, engine, active_policy_holder, valid_prescription_data):
        """Test full flow for approved claim"""
        # We need to mock _load_policy_terms or ensure it reads correctly.
        # The engine uses _load_policy_terms internally. For tests, we might want to inject dependencies, 
        # but the engine constructor is hardcoded. 
        # However, the engine loads from a file. If the file is missing/invalid in test env, we have issues.
        # Let's see if we can mock the property or method.
        # simpler: just rely on the default loaded terms (empty dict or whatever) OR patch it?
        # The engine logic handles empty terms gracefully but might fail checks.
        # Let's assume the test environment has access to the file or we patch it.
        
        # Patching via instance for this test (since it's not a fixture sharing state aggressively)
        engine.policy_terms = {
            "policy_id": "OPD_GOLD_2024",
            "waiting_periods": {"initial_waiting": 30},
            "exclusions": ["Cosmetic procedure"],
            "coverage_details": {
                "annual_limit": 50000,
                "per_claim_limit": 5000,
                "consultation_fees": {"copay_percentage": 10},
            }
        }
        
        decision = await engine.adjudicate_claim(
            "CLM_TEST_001",
            valid_prescription_data,
            active_policy_holder
        )
        
        assert decision.decision == DecisionType.APPROVED
        assert decision.eligibility_passed is True
        assert decision.documents_valid is True
        assert decision.coverage_verified is True
        assert decision.limits_ok is True
        assert decision.approved_amount > 0
        assert decision.confidence_score >= 0.85
    
    @pytest.mark.asyncio
    async def test_manual_review_fraud(self, engine, active_policy_holder, valid_prescription_data):
        """Test manual review trigger for high amount"""
        engine.policy_terms = {
             "policy_id": "OPD_GOLD_2024",
             "waiting_periods": {"initial_waiting": 30},
             "exclusions": [],
             "coverage_details": {"annual_limit": 100000, "per_claim_limit": 50000}
        }
        
        valid_prescription_data["total_amount"] = 30000
        decision = await engine.adjudicate_claim(
            "CLM_TEST_004",
            valid_prescription_data,
            active_policy_holder
        )
        
        # Fraud detector flags > 20000. 
        # Engine logic: if fraud_result["suspicious"] -> MANUAL_REVIEW
        assert decision.decision == DecisionType.MANUAL_REVIEW
        assert "FRAUD_SUSPECTED" in decision.notes

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
