"""
RAG Service using Qdrant Vector Database
Handles policy document indexing and retrieval
"""
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import json
import os
from app.config import settings

class RAGService:
    def __init__(self):
        # Initialize Qdrant client
        if settings.QDRANT_USE_MEMORY:
            # In-memory mode for development
            self.client = QdrantClient(":memory:")
        else:
            # Persistent mode for production
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        
        # Initialize collection
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Create Qdrant collections if they don't exist"""
        # Policy documents collection
        try:
            self.client.get_collection(self.collection_name)
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,  # all-MiniLM-L6-v2 embedding size
                    distance=Distance.COSINE
                )
            )
        
        # Medical documents collection (for uploaded docs)
        try:
            self.client.get_collection("medical_documents")
        except:
            self.client.create_collection(
                collection_name="medical_documents",
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )
    
    def index_policy_documents(self, policy_file_path: str = None):
        """
        Index policy documents into Qdrant
        
        Args:
            policy_file_path: Path to policy_terms.json
        """
        if policy_file_path is None:
            policy_file_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "policy_terms.json"
            )
        
        with open(policy_file_path, 'r') as f:
            policy_data = json.load(f)
        
        # Extract policy sections for indexing
        documents = self._extract_policy_sections(policy_data)
        
        # Create embeddings and index
        points = []
        for idx, doc in enumerate(documents):
            embedding = self.embedding_model.encode(doc['text']).tolist()
            point = PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "text": doc['text'],
                    "category": doc['category'],
                    "metadata": doc.get('metadata', {})
                }
            )
            points.append(point)
        
        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def _extract_policy_sections(self, policy_data: Dict) -> List[Dict]:
        """Extract meaningful sections from policy JSON for indexing"""
        documents = []
        
        # Index coverage details
        if 'coverage_details' in policy_data:
            for category, details in policy_data['coverage_details'].items():
                text = f"Coverage for {category}: {json.dumps(details, indent=2)}"
                documents.append({
                    'text': text,
                    'category': 'coverage',
                    'metadata': {'subcategory': category}
                })
        
        # Index exclusions
        if 'exclusions' in policy_data:
            text = f"Policy exclusions: {', '.join(policy_data['exclusions'])}"
            documents.append({
                'text': text,
                'category': 'exclusions',
                'metadata': {}
            })
        
        # Index waiting periods
        if 'waiting_periods' in policy_data:
            text = f"Waiting periods: {json.dumps(policy_data['waiting_periods'], indent=2)}"
            documents.append({
                'text': text,
                'category': 'waiting_periods',
                'metadata': {}
            })
        
        # Index claim requirements
        if 'claim_requirements' in policy_data:
            text = f"Claim requirements: {json.dumps(policy_data['claim_requirements'], indent=2)}"
            documents.append({
                'text': text,
                'category': 'claim_requirements',
                'metadata': {}
            })
        
        return documents
    
    def retrieve_relevant_policy(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve relevant policy sections for a query
        
        Args:
            query: Search query (e.g., diagnosis, treatment)
            top_k: Number of results to return
        
        Returns:
            List of relevant policy sections with scores
        """
        # Create query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        # Format results
        results = []
        for result in search_results:
            results.append({
                'text': result.payload['text'],
                'category': result.payload['category'],
                'score': result.score,
                'metadata': result.payload.get('metadata', {})
            })
        
        return results
    
    def get_coverage_info(self, treatment_category: str) -> Dict:
        """Get specific coverage information for a treatment category"""
        query = f"Coverage details for {treatment_category}"
        results = self.retrieve_relevant_policy(query, top_k=1)
        return results[0] if results else None
    
    def check_exclusions(self, diagnosis: str, treatment: str) -> List[str]:
        """Check if diagnosis/treatment matches any exclusions"""
        query = f"Exclusions for {diagnosis} {treatment}"
        results = self.retrieve_relevant_policy(query, top_k=1)
        
        # TODO: Implement smart matching logic
        return []
