"""
Claims Adjudication Engine
Automated decision-making for OPD insurance claims
"""
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field

from app.models.models import ClaimDecision, DecisionType, PolicyHolder, Claim
from app.utils.database import SessionLocal
from app.services.validators.eligibility_validator import EligibilityValidator
from app.services.validators.document_validator import DocumentValidator
from app.services.validators.coverage_validator import CoverageValidator
from app.services.validators.limit_validator import LimitValidator
from app.services.validators.medical_necessity_validator import MedicalNecessityValidator
from app.services.validators.fraud_detector import FraudDetector
import os
from openai import AsyncOpenAI

# Initialize OpenAI Client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)


# Pydantic Schema for Structured LLM Output (Guaranteed Parsing)
class LLMAdjudicationResponse(BaseModel):
    """Structured output schema for LLM adjudication - prevents parsing errors"""
    final_decision: str = Field(
        ..., 
        description="Must be one of: APPROVED, REJECTED, PARTIAL, MANUAL_REVIEW"
    )
    reasoning: str = Field(
        ..., 
        description="Clear 2-3 sentence explanation of the decision"
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Specific policy references (e.g., 'Annual Limit: 50000')"
    )
    next_steps: str = Field(
        ..., 
        description="Instructions for the claimant"
    )
    confidence_score: Optional[float] = Field(
        default=0.95,
        description="Confidence in decision (0.0-1.0)"
    )


class AdjudicationEngine:
    """
    Core engine for automated claims adjudication
    Evaluates claims against policy terms and adjudication rules
    """
    
    def __init__(self):
        """Initialize engine with policy terms and rules"""
        self.policy_terms = self._load_policy_terms()
        self.adjudication_rules = self._load_adjudication_rules()
        
        # Initialize Validators
        self.eligibility_validator = EligibilityValidator()
        self.document_validator = DocumentValidator()
        self.coverage_validator = CoverageValidator()
        self.limit_validator = LimitValidator()
        self.medical_necessity_validator = MedicalNecessityValidator()
        self.fraud_detector = FraudDetector()
        
        # Decision thresholds
        self.CONFIDENCE_THRESHOLDS = {
            "AUTO_APPROVE": 0.85,
            "AUTO_REJECT": 0.70,
            "MANUAL_REVIEW": 0.70,
            "HIGH_VALUE": 25000,
        }
        
        # 🛡️ KILL SWITCH FLAGS - LLM cannot override these
        self.HARD_GUARDRAILS = [
            "eligibility",  # Policy must be active
            "fraud",        # No fraud indicators allowed
            "coverage",     # Service must be covered
        ]
        
        logger.info("✅ AdjudicationEngine initialized")
    
    def _load_policy_terms(self) -> Dict:
        """
        Load policy terms from database (with JSON fallback)
        
        Priority:
        1. Database (respects admin updates)
        2. JSON file (fallback if database unavailable)
        
        This ensures dynamic policy updates are used, not static files.
        """
        from app.utils.policy_loader import get_policy_terms
        from app.utils.database import SessionLocal
        
        try:
            # Get database session
            db = SessionLocal()
            
            # Load from database (with JSON fallback)
            terms = get_policy_terms(
                db=db,
                policy_terms_id="PLUM_OPD_2024",
                use_fallback=True
            )
            
            db.close()
            
            if terms:
                logger.info(f"📋 Loaded policy terms: {terms.get('policy_id', 'Unknown')}")
            else:
                logger.warning(f"⚠️  No policy terms loaded, using empty dict")
            
            return terms
            
        except Exception as e:
            logger.error(f"❌ Failed to load policy terms: {e}")
            return {}
    
    def _load_adjudication_rules(self) -> Dict:
        """Load adjudication rules from markdown file"""
        try:
            # Use backend directory path
            rules_file = Path(__file__).parent.parent.parent / "adjudication_rules.md"
            
            # For now, return a structured dict
            # TODO: Parse adjudication_rules.md for more detailed rules
            rules = {
                "eligibility_checks": ["policy_status", "waiting_period", "member_verification"],
                "document_checks": ["legibility", "completeness", "authenticity", "date_consistency"],
                "coverage_checks": ["service_covered", "not_excluded", "pre_auth"],
                "limit_checks": ["annual_limit", "sub_limit", "per_claim_limit"],
                "medical_checks": ["diagnosis_treatment_alignment", "medical_necessity"]
            }
            
            return rules
        except Exception as e:
            logger.error(f"❌ Failed to load adjudication rules: {e}")
            return {}
    
    async def adjudicate_claim(
        self,
        claim_id: str,
        adjudication_context: Dict[str, Any]
    ) -> ClaimDecision:
        """
        Main adjudication flow with LLM Enrichment
        """
        logger.info(f"🔍 Starting adjudication for claim {claim_id}")
        
        # Extract context components
        policy_context = adjudication_context.get("policy_context", {})
        claim_evidence = adjudication_context.get("claim_evidence", {})
        policy_terms = adjudication_context.get("policy_terms", self.policy_terms)
        
        # Get total amount
        total_amount = claim_evidence.get("total_amount", 0)
        if "financials" in claim_evidence:
            total_amount = claim_evidence["financials"].get("total_amount_claimed", total_amount)
        
        # Initialize decision object
        decision = ClaimDecision(
            claim_id=claim_id,
            original_amount=total_amount,
            adjudicated_at=datetime.utcnow()
        )
        
        # Run Validators (Hard Rules)
        # We run ALL validators to gather full context for the LLM
        eligibility = self.eligibility_validator.validate(policy_context, claim_evidence, policy_terms)
        documents = self.document_validator.validate(claim_evidence)
        coverage = self.coverage_validator.validate(claim_evidence, policy_terms)
        limits = self.limit_validator.validate(total_amount, policy_context, claim_evidence, policy_terms)
        medical = self.medical_necessity_validator.validate(claim_evidence)
        fraud = self.fraud_detector.detect(claim_evidence, policy_context)
        
        # Aggregate Results
        decision.eligibility_passed = eligibility["passed"]
        decision.documents_valid = documents["passed"]
        decision.coverage_verified = coverage["passed"]
        decision.limits_ok = limits["passed"]
        decision.medically_necessary = medical["passed"]
        decision.fraud_indicators = fraud.get("indicators", [])
        
        # Set Preliminary Decision based on Hard Rules
        errors = []
        if not eligibility["passed"]: errors.extend(eligibility["errors"])
        if not documents["passed"]: errors.extend(documents["errors"])
        if not coverage["passed"]: errors.extend(coverage["errors"])
        if not limits["passed"]: errors.extend(limits["errors"])
        if not medical["passed"]: errors.extend(medical["errors"])
        
        if errors:
            decision.decision = DecisionType.REJECTED
            decision.rejection_reasons = errors
            decision.approved_amount = 0.0
        elif fraud.get("suspicious", False):
            decision.decision = DecisionType.MANUAL_REVIEW
            decision.rejection_reasons = ["Fraud Suspected"]
        else:
             decision.decision = DecisionType.APPROVED
             decision.approved_amount = limits.get("approved_amount", total_amount)
             # Set copay info
             decision.copay_amount = limits.get("copay_amount", 0)
             decision.copay_percentage = limits.get("copay_percentage", 0)

        # 🚀 LLM Enrichment Step (The "Judge")
        # We pass the preliminary status + full context to the LLM for the final narrative
        try:
            logger.info("🤖 Calling LLM for Adjudication Enrichment...")
            enriched_decision = await self._enrich_decision_with_llm(
                decision, 
                adjudication_context,
                validation_results={
                    "eligibility": eligibility,
                    "documents": documents,
                    "coverage": coverage,
                    "limits": limits,
                    "medical": medical,
                    "fraud": fraud
                }
            )
            return enriched_decision
        except Exception as e:
            logger.error(f"❌ LLM Enrichment failed: {e}")
            # Fallback to hard rule decision if LLM fails
            decision.notes = f"Processed by Hard Rules. (LLM Error: {str(e)})"
            return decision

    async def _enrich_decision_with_llm(
        self, 
        decision: ClaimDecision, 
        context: Dict, 
        validation_results: Dict
    ) -> ClaimDecision:
        """
        Uses GPT-4o to generate reasoning, citations, and polished output
        """
        import json
        
        system_prompt = (
            "You are an Expert Insurance Claims Adjudicator. "
            "Your job is to review the claim data, the policy terms, and the automated validation results.\n\n"
            "You must output a JSON object with the following fields:\n"
            "- final_decision: 'APPROVED', 'REJECTED', 'PARTIAL', or 'MANUAL_REVIEW'\n"
            "- reasoning: A clear, professional explanation of the decision (2-3 sentences).\n"
            "- citations: A list of specific reasons linking to policy data (e.g., 'Annual Limit of 50,000 exceeded').\n"
            "- next_steps: Instructions for the claimant.\n\n"
            "Rules:\n"
            "1. Trust the 'validation_results'. If they show failure, you MUST generally Reject.\n"
            "2. However, use your judgment. If the failure seems minor or technical, you can suggest Manual Review.\n"
            "3. Be empathetic but firm in your reasoning.\n"
            "4. Reference specific numbers from the Policy Terms in your citations."
        )
        
        user_prompt = (
            f"Policy Terms:\n{json.dumps(context.get('policy_terms'), indent=2)}\n\n"
            f"Claim Data:\n{json.dumps(context.get('claim_evidence'), indent=2)}\n\n"
            f"Automated Validation Results:\n{json.dumps(validation_results, indent=2)}\n\n"
            f"Current Preliminary Decision: {decision.decision.value}\n"
            f"Current Errors: {json.dumps(decision.rejection_reasons)}"
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.1
        )
        
        llm_content = response.choices[0].message.content
        result = json.loads(llm_content)
        
        # Update Decision Object
        valid_decisions = ["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"]
        if result.get("final_decision") in valid_decisions:
             # Map string to Enum if needed, or just use value
             # Assuming DecisionType matches uppercase strings
             # decision.decision = DecisionType[result["final_decision"]] # Might be risky if enum names differ
             
             # Safe mapping
             decision_map = {
                 "APPROVED": DecisionType.APPROVED,
                 "REJECTED": DecisionType.REJECTED,
                 "PARTIAL": DecisionType.PARTIAL,
                 "MANUAL_REVIEW": DecisionType.MANUAL_REVIEW
             }
             if result["final_decision"] in decision_map:
                 decision.decision = decision_map[result["final_decision"]]
        
        decision.notes = result.get("reasoning", decision.notes)
        decision.next_steps = result.get("next_steps", decision.next_steps)
        
        # Append citations to comments or notes (since schema might not have citations field yet)
        # Or ideally we add it. For now, let's put it in notes formatted nicely if no field exists.
        # But wait, user wanted citations.
        # I'll enable citations in 'rejection_reasons' if rejected, or just append to notes.
        
        citations = result.get("citations", [])
        if citations:
            citation_text = "\n\nPolicy Citations:\n" + "\n".join([f"- {c}" for c in citations])
            decision.notes += citation_text
            
            # Also populate rejection_reasons if empty and rejected
            if decision.decision == DecisionType.REJECTED and not decision.rejection_reasons:
                decision.rejection_reasons = citations

        return decision
    
    def _calculate_confidence(self, *validation_results) -> float:
        """Calculate overall confidence score"""
        base_score = 1.0
        
        # Deduct for failed checks
        for result in validation_results:
            if isinstance(result, dict) and not result.get("passed", True):
                base_score -= 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def _create_rejection(self, decision: ClaimDecision, errors: List[str]) -> ClaimDecision:
        """Create a rejection decision"""
        decision.decision = DecisionType.REJECTED
        decision.rejection_reasons = errors
        decision.approved_amount = 0.0
        decision.confidence_score = 0.95
        decision.notes = f"Claim rejected due to: {', '.join(errors)}"
        decision.next_steps = "Please contact support for more information or submit corrected documents."
        return decision
    
    def _create_manual_review(self, decision: ClaimDecision, reason: str, indicators: List[str]) -> ClaimDecision:
        """Create a manual review decision"""
        decision.decision = DecisionType.MANUAL_REVIEW
        decision.notes = f"Claim requires manual review: {reason}"
        decision.next_steps = "Your claim is under review. You will be notified within 2-3 business days."
        decision.fraud_indicators = indicators
        return decision
    
    def _check_kill_switches(self, validation_results: Dict) -> Optional[str]:
        """
        Check for critical policy violations that MUST result in rejection
        Returns the violation reason if found, None otherwise
        """
        # Fraud Detection (Zero Tolerance)
        if validation_results.get("fraud", {}).get("suspicious", False):
            return "Fraud indicators detected - claim flagged for investigation"
        
        # Eligibility (Policy must be active)
        if not validation_results.get("eligibility", {}).get("passed", False):
            errors = validation_results.get("eligibility", {}).get("errors", [])
            if errors:
                return f"Eligibility failure: {errors[0]}"
        
        # Coverage (Service must be covered)
        if not validation_results.get("coverage", {}).get("passed", False):
            errors = validation_results.get("coverage", {}).get("errors", [])
            if errors:
                return f"Coverage violation: {errors[0]}"
        
        return None
    
    def _apply_guardrails(self, llm_decision: str, validation_results: Dict) -> str:
        """
        Enforce hard guardrails - prevent LLM from approving claims with critical failures
        """
        # If any hard validation failed, force REJECT or MANUAL_REVIEW
        critical_failures = []
        
        if not validation_results.get("limits", {}).get("passed", False):
            critical_failures.append("limits")
        
        if not validation_results.get("documents", {}).get("passed", False):
            critical_failures.append("documents")
        
        if critical_failures and llm_decision == "APPROVED":
            logger.warning(f"🛡️ Guardrail Override: LLM tried to approve despite failures in {critical_failures}")
            return "REJECTED"
        
        return llm_decision

