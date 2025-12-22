"""
Integration Tests for Claims Adjudication API
Tests full flow from API to database
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app
from app.models.models import Claim, PolicyHolder, Document, ClaimDecision, DecisionType
from app.utils.database import SessionLocal, Base, engine as db_engine


@pytest.fixture(scope="module")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=db_engine)
    yield
    Base.metadata.drop_all(bind=db_engine)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def db():
    """Create database session"""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_policy_holder(db):
    """Create test policy holder"""
    policy_holder = PolicyHolder(
        policy_holder_id="PH_TEST_001",
        policy_holder_name="Test User",
        policy_status="ACTIVE",
        policy_start_date=datetime.now() - timedelta(days=60),
        annual_limit=50000.0,
        annual_limit_used=10000.0,
        waiting_period_completed=True
    )
    db.add(policy_holder)
    db.commit()
    db.refresh(policy_holder)
    return policy_holder


@pytest.fixture
def test_claim(db, test_policy_holder):
    """Create test claim"""
    claim = Claim(
        claim_id="CLM_TEST_001",
        policy_holder_id=test_policy_holder.policy_holder_id,
        treatment_type="consultation",
        treatment_date=datetime.now(),
        claimed_amount=1500.0,
        status="pending"
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@pytest.fixture
def test_document(db, test_claim):
    """Create test document with extracted data"""
    document = Document(
        document_id="DOC_TEST_001",
        claim_id=test_claim.claim_id,
        document_type="prescription",
        status="processed",
        extracted_data={
            "patient_name": "Test User",
            "doctor_name": "Dr. Test",
            "doctor_registration_number": "MH/12345/2020",
            "date": datetime.now().isoformat(),
            "diagnosis": "Fever",
            "medicines": [{"name": "Paracetamol", "dosage": "500mg"}],
            "total_amount": 1500
        },
        quality_score=0.95
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


class TestAdjudicationAPI:
    """Test adjudication API endpoints"""
    
    def test_adjudicate_claim_success(self, client, test_claim, test_document):
        """Test successful claim adjudication"""
        response = client.post(f"/api/adjudication/claims/{test_claim.claim_id}/adjudicate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["claim_id"] == test_claim.claim_id
        assert data["decision"] in ["APPROVED", "REJECTED", "MANUAL_REVIEW"]
        assert "confidence_score" in data
        assert "approved_amount" in data
        assert "notes" in data
        assert "next_steps" in data
    
    def test_adjudicate_claim_not_found(self, client):
        """Test adjudication for non-existent claim"""
        response = client.post("/api/adjudication/claims/CLM_INVALID/adjudicate")
        assert response.status_code == 404
    
    def test_get_decision(self, client, test_claim, test_document):
        """Test getting decision after adjudication"""
        # First adjudicate
        client.post(f"/api/adjudication/claims/{test_claim.claim_id}/adjudicate")
        
        # Then get decision
        response = client.get(f"/api/adjudication/claims/{test_claim.claim_id}/decision")
        
        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == test_claim.claim_id
    
    def test_get_decision_not_found(self, client):
        """Test getting decision for non-adjudicated claim"""
        response = client.get("/api/adjudication/claims/CLM_INVALID/decision")
        assert response.status_code == 404
    
    def test_pending_reviews(self, client):
        """Test getting pending manual reviews"""
        response = client.get("/api/adjudication/claims/pending-review")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_decision_stats(self, client):
        """Test getting decision statistics"""
        response = client.get("/api/adjudication/stats/decisions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_decisions" in data
        assert "approved" in data
        assert "rejected" in data
        assert "manual_review" in data
        assert "average_confidence" in data
        assert "approval_rate" in data


class TestAdjudicationFlow:
    """Test complete adjudication flow"""
    
    def test_approved_claim_flow(self, client, db, test_claim, test_document):
        """Test complete flow for approved claim"""
        # Adjudicate
        response = client.post(f"/api/adjudication/claims/{test_claim.claim_id}/adjudicate")
        assert response.status_code == 200
        
        # Check decision in database
        decision = db.query(ClaimDecision).filter(
            ClaimDecision.claim_id == test_claim.claim_id
        ).first()
        
        assert decision is not None
        assert decision.decision in [DecisionType.APPROVED, DecisionType.MANUAL_REVIEW]
        assert decision.confidence_score > 0
        
        # Check claim status updated
        db.refresh(test_claim)
        assert test_claim.status in ["approved", "manual_review"]
    
    def test_manual_override(self, client, db, test_claim, test_document):
        """Test manual override of decision"""
        # First adjudicate
        client.post(f"/api/adjudication/claims/{test_claim.claim_id}/adjudicate")
        
        # Override decision
        override_data = {
            "reviewer_id": "REV001",
            "new_decision": "APPROVED",
            "approved_amount": 1500,
            "review_notes": "Verified with provider",
            "reason": "Manual verification"
        }
        
        response = client.post(
            f"/api/adjudication/claims/{test_claim.claim_id}/decision/override",
            json=override_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["decision"] == "APPROVED"
        assert data["reviewed_by"] == "REV001"
        assert data["review_notes"] == "Verified with provider"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
