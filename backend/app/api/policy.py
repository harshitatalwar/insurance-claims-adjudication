from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter()

@router.get("/terms")
async def get_policy_terms():
    """Get policy terms and conditions"""
    # Load policy terms from JSON file
    policy_file = os.path.join(os.path.dirname(__file__), "..", "..", "policy_terms.json")
    
    if not os.path.exists(policy_file):
        raise HTTPException(status_code=404, detail="Policy terms not found")
    
    with open(policy_file, "r") as f:
        policy_terms = json.load(f)
    
    return policy_terms

@router.get("/coverage/{category}")
async def get_coverage_details(category: str):
    """Get coverage details for a specific category"""
    policy_terms = await get_policy_terms()
    
    if category not in policy_terms.get("coverage_details", {}):
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    
    return policy_terms["coverage_details"][category]

@router.get("/exclusions")
async def get_exclusions():
    """Get list of policy exclusions"""
    policy_terms = await get_policy_terms()
    return {"exclusions": policy_terms.get("exclusions", [])}
