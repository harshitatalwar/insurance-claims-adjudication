"""
Seed Policy Terms Data
Populates the policy_terms table with Insureho OPD policy data
"""
from datetime import datetime
from app.utils.database import SessionLocal
from app.models.models import PolicyTerms

def seed_policy_terms():
    db = SessionLocal()
    
    try:
        # Check if policy already exists
        existing = db.query(PolicyTerms).filter(
            PolicyTerms.policy_id == "PLUM_OPD_2024"
        ).first()
        
        if existing:
            print("✅ Policy terms already exist")
            return
        
        # Create policy terms
        policy = PolicyTerms(
            policy_id="PLUM_OPD_2024",
            policy_name="PLUM OPD Advantage",
            effective_date=datetime(2024, 1, 1),
            
            # Limits
            annual_limit=50000.0,
            per_claim_limit=5000.0,
            family_floater_limit=150000.0,
            
            # Sub-limits
            consultation_limit=2000.0,
            diagnostic_limit=10000.0,
            pharmacy_limit=15000.0,
            dental_limit=10000.0,
            vision_limit=5000.0,
            alternative_medicine_limit=8000.0,
            
            # Co-payments
            consultation_copay=10.0,
            network_discount=20.0,
            branded_drugs_copay=30.0,
            
            # Waiting periods
            initial_waiting_period=30,
            pre_existing_waiting_period=365,
            maternity_waiting_period=270,
            
            # JSON fields
            exclusions=[
                "Cosmetic procedures",
                "Weight loss treatments",
                "Infertility treatments",
                "Experimental treatments",
                "Self-inflicted injuries",
                "Adventure sports injuries",
                "War and nuclear risks",
                "HIV/AIDS treatment",
                "Alcoholism/drug abuse treatment",
                "Non-allopathic treatments (except listed)",
                "Vitamins and supplements (unless prescribed for deficiency)"
            ],
            
            covered_services={
                "consultation": True,
                "diagnostic_tests": True,
                "pharmacy": True,
                "dental": True,
                "vision": True,
                "alternative_medicine": True
            },
            
            network_providers=[
                "Apollo Hospitals",
                "Fortis Healthcare",
                "Max Healthcare",
                "Manipal Hospitals",
                "Narayana Health"
            ],
            
            specific_ailment_waiting={
                "diabetes": 90,
                "hypertension": 90,
                "joint_replacement": 730
            },
            
            # Requirements
            minimum_claim_amount=500.0,
            submission_timeline_days=30
        )
        
        db.add(policy)
        db.commit()
        
        print("✅ Policy terms seeded successfully!")
        print(f"   Policy ID: {policy.policy_id}")
        print(f"   Annual Limit: ₹{policy.annual_limit:,.0f}")
        print(f"   Per Claim Limit: ₹{policy.per_claim_limit:,.0f}")
        
    except Exception as e:
        print(f"❌ Error seeding policy terms: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_policy_terms()
