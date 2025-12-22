"""
Seed script to populate policy_terms table with data from policy_terms.json
"""
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(r"C:\Users\Harshita\Documents\ASSIGNMENT\opd-claims-adjudication\.env")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.database import SessionLocal
from app.models import PolicyTerms

def load_policy_terms():
    """Load policy terms from JSON file and seed database"""
    
    # Path to policy_terms.json
    json_path = r"C:\Users\Harshita\Documents\ASSIGNMENT\plum_intern_assignment\policy_terms.json"
    
    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    db = SessionLocal()
    
    try:
        # Delete existing policy if it exists
        db.query(PolicyTerms).filter(
            PolicyTerms.policy_id == data["policy_id"]
        ).delete()
        db.commit()
        
        print(f"Creating new policy {data['policy_id']}...")
        policy = PolicyTerms()
        
        # Basic info
        policy.policy_id = data["policy_id"]
        policy.policy_name = data["policy_name"]
        policy.effective_date = datetime.strptime(data["effective_date"], "%Y-%m-%d")
        
        # Limits
        coverage = data["coverage_details"]
        policy.annual_limit = coverage["annual_limit"]
        policy.per_claim_limit = coverage["per_claim_limit"]
        policy.family_floater_limit = coverage["family_floater_limit"]
        
        # Sub-limits
        policy.consultation_limit = coverage["consultation_fees"]["sub_limit"]
        policy.diagnostic_limit = coverage["diagnostic_tests"]["sub_limit"]
        policy.pharmacy_limit = coverage["pharmacy"]["sub_limit"]
        policy.dental_limit = coverage["dental"]["sub_limit"]
        policy.vision_limit = coverage["vision"]["sub_limit"]
        policy.alternative_medicine_limit = coverage["alternative_medicine"]["sub_limit"]
        
        # Co-payments
        policy.consultation_copay = coverage["consultation_fees"]["copay_percentage"]
        policy.network_discount = coverage["consultation_fees"]["network_discount"]
        policy.branded_drugs_copay = coverage["pharmacy"]["branded_drugs_copay"]
        
        # Waiting periods
        waiting = data["waiting_periods"]
        policy.initial_waiting_period = waiting["initial_waiting"]
        policy.pre_existing_waiting_period = waiting["pre_existing_diseases"]
        policy.maternity_waiting_period = waiting["maternity"]
        policy.specific_ailment_waiting = waiting["specific_ailments"]
        
        # JSON fields
        policy.exclusions = data["exclusions"]
        policy.network_providers = data["network_hospitals"]
        
        # Covered services
        policy.covered_services = {
            "consultation": coverage["consultation_fees"]["covered"],
            "diagnostic": {
                "covered": coverage["diagnostic_tests"]["covered"],
                "tests": coverage["diagnostic_tests"]["covered_tests"]
            },
            "pharmacy": {
                "covered": coverage["pharmacy"]["covered"],
                "generic_mandatory": coverage["pharmacy"]["generic_drugs_mandatory"]
            },
            "dental": {
                "covered": coverage["dental"]["covered"],
                "procedures": coverage["dental"]["procedures_covered"]
            },
            "vision": {
                "covered": coverage["vision"]["covered"],
                "services": ["eye_test", "glasses", "contact_lenses"]
            },
            "alternative_medicine": {
                "covered": coverage["alternative_medicine"]["covered"],
                "treatments": coverage["alternative_medicine"]["covered_treatments"]
            }
        }
        
        # Requirements
        requirements = data["claim_requirements"]
        policy.minimum_claim_amount = requirements["minimum_claim_amount"]
        policy.submission_timeline_days = requirements["submission_timeline_days"]
        
        db.add(policy)
        db.commit()
        print(f"✅ Successfully seeded policy terms: {policy.policy_id}")
        
    except Exception as e:
        print(f"❌ Error seeding policy terms: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    load_policy_terms()
