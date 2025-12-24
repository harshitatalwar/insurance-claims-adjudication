"""
Production-Ready Document Processor with GPT-4o Vision
- Rate limiting and usage tracking
- Base64 encoding for private MinIO
- Comprehensive logging
- Cost monitoring
- Error handling
"""
import base64
import json
import logging
import time
from typing import Dict, Any

from app.services.minio_service import get_storage_service
# from app.services.rag_service import RAGService  # DISABLED - Not needed for OCR
from app.services.redis_rate_limiter import RedisRateLimiter, log_usage_async, _calculate_cost
from app.config import settings
from app.utils.database import SessionLocal
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.minio_service = get_storage_service()
        # self.rag_service = RAGService()  # DISABLED - Sentence transformer permission error
        self.rag_service = None  # Temporarily disabled
        self.rate_limiter = RedisRateLimiter()
        
        # Initialize AsyncOpenAI client for async/await support
        if not settings.OPENAI_API_KEY:
            logger.error("❌ OPENAI_API_KEY not set in environment")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info(f"✅ AsyncOpenAI client initialized (Model: {settings.OPENAI_MODEL})")
        
        self.model = settings.OPENAI_MODEL

    async def process_document(
        self, 
        file_id: str, 
        object_name: str, 
        document_type: str
    ) -> Dict[str, Any]:
        """
        Production-ready processing pipeline:
        Rate Limit Check → MinIO Download → Base64 Encode → GPT-4o Vision → Log Usage → Qdrant
        
        Args:
            file_id: Document ID (e.g., DOC4A2B3C4D5E)
            object_name: MinIO path (e.g., claims/CLM000001/prescription/DOC4A2B3C4D5E.jpg)
            document_type: prescription, bill, report
            
        Returns:
            {
                "status": "processed",
                "extracted_data": {...},
                "confidence_score": 0.95,
                "tokens_used": 1234,
                "cost_usd": 0.0123
            }
        """
        logger.info(f"📄 Processing document {file_id} ({document_type}) using {self.model}")
        
        if not self.client:
            logger.error(f"❌ Cannot process {file_id}: OpenAI client not initialized")
            return {
                "status": "failed",
                "error": "OpenAI API key not configured"
            }
        
        db = SessionLocal()
        start_time = time.time()
        
        try:
            # STEP 1: RATE LIMITING
            # Check if we have quota before doing any work
            logger.info(f"🔒 Checking rate limits...")
            self.rate_limiter.check_and_wait(
                estimated_tokens=2000,  # Conservative estimate
                document_id=file_id
            )

            # STEP 2: DOWNLOAD from Private MinIO
            try:
                logger.info(f"📥 Downloading from MinIO: {object_name}")
                logger.info(f"   Bucket: {self.minio_service.bucket_name}")
                logger.info(f"   Object: {object_name}")
                file_data = self.minio_service.download_file(object_name)
                logger.info(f"✅ Downloaded {len(file_data)} bytes")
                logger.info(f"   First 100 bytes: {file_data[:100]}")
            except Exception as e:
                logger.error(f"❌ MinIO download failed: {e}")
                logger.error(f"   Bucket: {self.minio_service.bucket_name}")
                logger.error(f"   Object: {object_name}")
                log_usage_async(
                    db, file_id, document_type, self.model,
                    0, 0, None, "failed", f"MinIO error: {str(e)}"
                )
                raise

            # STEP 3: ENCODE to Base64 (Secure transmission to OpenAI)
            logger.info(f"🔐 Encoding to base64...")
            base64_image = base64.b64encode(file_data).decode('utf-8')
            logger.info(f"✅ Encoded to base64: {len(base64_image)} characters")
            logger.info(f"   First 100 chars: {base64_image[:100]}...")
            logger.info(f"   Last 50 chars: ...{base64_image[-50:]}")

            # STEP 4: PREPARE EXTRACTION PROMPT
            prompts = self._get_extraction_prompts()
            system_prompt = prompts[document_type]["system"]
            user_prompt = prompts[document_type]["user"]
            logger.info(f"📝 Prepared extraction prompts for {document_type}")
            logger.debug(f"   System Prompt: {system_prompt[:100]}...")
            logger.debug(f"   User Prompt: {user_prompt[:100]}...")

            # STEP 5: CALL GPT-4o VISION
            logger.info(f"🤖 Calling {self.model} Vision API...")
            logger.info(f"   Model: {self.model}")
            logger.info(f"   Document Type: {document_type}")
            api_start = time.time()
            
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS
                )
                
                api_time = int((time.time() - api_start) * 1000)
                logger.info(f"✅ API response received ({api_time}ms)")
                logger.info(f"   Response ID: {response.id}")
                logger.info(f"   Model used: {response.model}")
                logger.info(f"   Tokens: {response.usage.total_tokens}")
                
            except Exception as e:
                logger.error(f"❌ OpenAI API call failed: {e}")
                log_usage_async(
                    db, file_id, document_type, self.model,
                    0, 0, None, "error", str(e)
                )
                raise
            
            # STEP 6: LOG API USAGE
            usage = response.usage
            log_usage_async(
                db=db,
                document_id=file_id,
                document_type=document_type,
                model=self.model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                response_time_ms=api_time,
                status="success"
            )
            
            # STEP 7: PARSE JSON RESPONSE
            json_content = response.choices[0].message.content
            try:
                extracted_data = json.loads(json_content)
                logger.info(f"✅ Extracted {len(extracted_data)} fields")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse JSON: {e}")
                logger.error(f"Raw content: {json_content}")
                extracted_data = {"error": "Invalid JSON", "raw": json_content}

            # STEP 8: STORE in Qdrant for RAG (TEMPORARILY DISABLED - Permission error)
            # try:
            #     summary_text = f"Document Type: {document_type}\nData: {json.dumps(extracted_data)}"
            #     await self._store_in_qdrant(
            #         file_id=file_id,
            #         text=summary_text,
            #         structured_data=extracted_data,
            #         document_type=document_type,
            #         object_name=object_name
            #     )
            # except Exception as e:
            #     logger.warning(f"⚠️  Qdrant storage failed (non-critical): {e}")
            logger.info("⏭️  Skipping Qdrant storage (disabled)")

            # Calculate total processing time
            total_time = int((time.time() - start_time) * 1000)
            logger.info(f"✅ Processing complete ({total_time}ms total)")
            
            # Calculate intelligent quality score
            from app.services.quality_scorer import QualityScoreCalculator
            
            response_metadata = {
                "finish_reason": response.choices[0].finish_reason if response.choices else "unknown"
            }
            
            quality_score = QualityScoreCalculator.calculate_score(
                extracted_data=extracted_data,
                document_type=document_type,
                response_metadata=response_metadata
            )
            
            # Get detailed breakdown for logging
            score_breakdown = QualityScoreCalculator.get_score_breakdown(
                extracted_data, document_type, response_metadata
            )
            
            logger.info(f"📊 Quality Score: {quality_score}")
            logger.info(f"   Completeness: {score_breakdown['breakdown']['completeness']:.2f}")
            logger.info(f"   Validation: {score_breakdown['breakdown']['validation']:.2f}")
            logger.info(f"   Consistency: {score_breakdown['breakdown']['consistency']:.2f}")
            logger.info(f"   Confidence: {score_breakdown['breakdown']['confidence']:.2f}")
            
            if score_breakdown['missing_required']:
                logger.warning(f"   Missing fields: {score_breakdown['missing_required']}")

            return {
                "status": "processed",
                "extracted_data": extracted_data,
                "confidence_score": quality_score,  # Now intelligently calculated!
                "score_breakdown": score_breakdown,
                "tokens_used": usage.total_tokens,
                "cost_usd": _calculate_cost(
                    self.model, usage.prompt_tokens, usage.completion_tokens
                ),
                "processing_time_ms": total_time
            }

        except Exception as e:
            logger.error(f"❌ Processing failed for {file_id}: {str(e)}")
            raise
        finally:
            db.close()

    def _get_extraction_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Get comprehensive extraction prompts for medical insurance adjudication
        
        Returns schemas optimized for policy validation and fraud detection
        """
        
        # Unified system prompt for all document types
        system_prompt = """You are an expert AI Medical Data Extractor for an insurance adjudication system. Your task is to analyze medical documents (bills, prescriptions, lab reports) and extract structured data into a strict JSON format.

CRITICAL RULES:

1. OUTPUT FORMAT: Return ONLY raw JSON. Do NOT include markdown formatting (```json ... ```) or conversational text.

2. DATES: Convert all dates to YYYY-MM-DD format.

3. CURRENCY: Extract numeric values only (e.g., 1500.00). Do not include currency symbols.

4. CATEGORY CLASSIFICATION: You MUST classify every bill line item into ONE of these categories:
   - CONSULTATION: Doctor consultation fees, OPD charges
   - PHARMACY: Medicines, drugs, prescriptions
   - DIAGNOSTIC: Lab tests, X-rays, MRI, CT scans, ECG, ultrasound
   - DENTAL: Any dental procedure (filling, extraction, root canal, cleaning)
   - VISION: Eye tests, glasses, contact lenses
   - ALTERNATIVE: Ayurveda, Homeopathy, Unani treatments
   - PROCEDURE: Surgery, dressings, physiotherapy, minor procedures
   - ROOM_RENT: Hospital stay charges, bed charges
   - OTHER: Registration fees, consumables, food, miscellaneous

5. DOCTOR REGISTRATION: Extract the registration number EXACTLY as shown. Valid format: [State Code]/[Number]/[Year] (e.g., "KA/12345/2015", "MH/67890/2018"). If not found or illegible, return null.

6. HANDWRITING: If text is handwritten and partially illegible:
   - Extract what you can with high confidence
   - Mark is_handwritten: true
   - If critical fields (Amount, Date, Doctor Name) are illegible, mark is_illegible: true

7. FRAUD DETECTION: Flag suspicious indicators in fraud_flags array:
   - "ALTERED_AMOUNTS": Numbers appear modified or overwritten
   - "MISSING_STAMP": No hospital/clinic stamp visible
   - "MISSING_SIGNATURE": No doctor signature
   - "DATE_INCONSISTENCY": Multiple conflicting dates
   - "DUPLICATE_BILL": Appears to be a photocopy or duplicate
   - "SUSPICIOUS_FORMATTING": Unusual layout or formatting

8. VALIDATION MARKERS: Assess document authenticity:
   - has_doctor_signature: true/false
   - has_hospital_stamp: true/false
   - has_patient_signature: true/false (if required)
   - dates_consistent: All dates match or are logically consistent
   - amounts_add_up: Line items sum to total amount
   - document_quality: HIGH (clear, original) | MEDIUM (readable, may be copy) | LOW (poor quality, partially illegible)

9. MEDICAL NECESSITY: In clinical_info.medical_necessity_justification, briefly explain why the treatment was necessary based on diagnosis and symptoms.

10. GENERIC vs BRANDED DRUGS: For pharmacy items, mark is_generic_drug: true if the medicine name suggests a generic drug (no brand name)."""

        # Common JSON schema for all document types
        json_schema_instruction = """
EXTRACTION SCHEMA:
{
  "document_metadata": {
    "document_type": "PRESCRIPTION | BILL | LAB_REPORT | MIXED",
    "submission_date": "YYYY-MM-DD",
    "page_count": 1,
    "is_illegible": false,
    "is_handwritten": false,
    "fraud_flags": []
  },
  "provider_details": {
    "hospital_name": "string | null",
    "hospital_address": "string | null",
    "hospital_gst_no": "string | null",
    "hospital_registration_no": "string | null",
    "doctor_name": "string | null",
    "doctor_registration_no": "string | null",
    "doctor_qualification": "string | null",
    "doctor_specialty": "string | null"
  },
  "patient_details": {
    "name": "string | null",
    "age": "number | null",
    "gender": "MALE | FEMALE | OTHER | null",
    "uhid_or_ref_no": "string | null",
    "contact_number": "string | null"
  },
  "clinical_info": {
    "diagnosis_primary": "string | null",
    "diagnosis_icd_code": "string | null",
    "symptoms": ["string"],
    "treatment_plan": ["string"],
    "is_follow_up": false,
    "requires_hospitalization": false,
    "medical_necessity_justification": "string | null"
  },
  "financials": {
    "bill_number": "string | null",
    "bill_date": "YYYY-MM-DD",
    "total_amount_claimed": 0.00,
    "total_tax_amount": 0.00,
    "total_discount_amount": 0.00,
    "currency": "INR",
    "payment_mode": "CASH | CARD | UPI | CHEQUE | null",
    "line_items": [
      {
        "description": "string",
        "category": "CONSULTATION | PHARMACY | DIAGNOSTIC | DENTAL | VISION | ALTERNATIVE | PROCEDURE | ROOM_RENT | OTHER",
        "quantity": 1,
        "unit_price": 0.00,
        "total_amount": 0.00,
        "date": "YYYY-MM-DD",
        "is_generic_drug": false
      }
    ]
  },
  "extracted_medicines": [
    {
      "name": "string",
      "dosage": "string",
      "duration": "string",
      "frequency": "string",
      "type": "TABLET | SYRUP | INJECTION | OINTMENT | DROPS | OTHER",
      "is_generic": false
    }
  ],
  "extracted_tests": [
    {
      "test_name": "string",
      "test_date": "YYYY-MM-DD",
      "result": "string | null",
      "normal_range": "string | null"
    }
  ],
  "validation_markers": {
    "has_doctor_signature": false,
    "has_hospital_stamp": false,
    "has_patient_signature": false,
    "dates_consistent": true,
    "amounts_add_up": true,
    "document_quality": "HIGH | MEDIUM | LOW"
  }
}

EXAMPLES:
- Consultation fee → category: "CONSULTATION"
- Paracetamol tablets → category: "PHARMACY", is_generic: true
- Blood test → category: "DIAGNOSTIC"
- Tooth extraction → category: "DENTAL"
- Eye checkup → category: "VISION"
- Ayurvedic medicine → category: "ALTERNATIVE"
- Registration fee → category: "OTHER"

Remember: Return ONLY the JSON object. No explanations, no markdown, no extra text."""

        return {
            "prescription": {
                "system": system_prompt,
                "user": f"""Analyze this PRESCRIPTION document and extract all relevant data.

Focus on:
- Doctor details (name, registration number, specialty)
- Patient information (name, age, gender)
- Diagnosis and symptoms
- Prescribed medicines (name, dosage, frequency, duration, type)
- Recommended tests
- Dates and signatures

{json_schema_instruction}"""
            },
            "bill": {
                "system": system_prompt,
                "user": f"""Analyze this MEDICAL BILL document and extract all relevant data.

Focus on:
- Hospital/clinic details (name, address, GST, registration)
- Patient information
- Bill number and date
- Line items with proper category classification (CONSULTATION, PHARMACY, DIAGNOSTIC, etc.)
- Total amounts, taxes, discounts
- Payment mode
- Signatures and stamps

CRITICAL: Every line item MUST have a category. Classify accurately for sub-limit validation.

{json_schema_instruction}"""
            },
            "report": {
                "system": system_prompt,
                "user": f"""Analyze this LAB REPORT document and extract all relevant data.

Focus on:
- Lab/hospital details
- Patient information
- Test name and date
- Test results and normal ranges
- Abnormal findings
- Doctor details

{json_schema_instruction}"""
            },
            "lab_report": {
                "system": system_prompt,
                "user": f"""Analyze this LAB REPORT document and extract all relevant data.

Focus on:
- Lab/hospital details
- Patient information
- Test name and date
- Test results and normal ranges
- Abnormal findings
- Doctor details

{json_schema_instruction}"""
            },
            "other": {
                "system": system_prompt,
                "user": f"""Analyze this medical document and extract all visible information.

Extract whatever data is available following the schema structure.

{json_schema_instruction}"""
            }
        }

    async def _store_in_qdrant(
        self,
        file_id: str,
        text: str,
        structured_data: Dict[str, Any],
        document_type: str,
        object_name: str
    ):
        """
        Store document in Qdrant for RAG searchability
        """
        try:
            logger.info(f"💾 Storing in Qdrant: {file_id}")
            
            # Generate embedding
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text).tolist()
            
            # Store in Qdrant
            from qdrant_client.models import PointStruct
            
            point = PointStruct(
                id=file_id,
                vector=embedding,
                payload={
                    "file_id": file_id,
                    "object_name": object_name,
                    "document_type": document_type,
                    "text": text,
                    "structured_data": structured_data,
                    "metadata": {
                        "doctor_name": structured_data.get("doctor_name", ""),
                        "patient_name": structured_data.get("patient_name", ""),
                        "diagnosis": structured_data.get("diagnosis", ""),
                        "date": structured_data.get("date", ""),
                        "total_amount": structured_data.get("total_amount", 0)
                    }
                }
            )
            
            # Store in Qdrant collection
            self.rag_service.client.upsert(
                collection_name="medical_documents",
                points=[point]
            )
            
            logger.info(f"✅ Stored document {file_id} in Qdrant")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to store in Qdrant: {e}")
            # Don't fail the entire process if Qdrant fails
