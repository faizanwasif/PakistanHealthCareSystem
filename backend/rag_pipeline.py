import logging
from typing import List, Dict, Any
import json
from datetime import datetime
from backend.database import get_db

logger = logging.getLogger(__name__)

class MedicalRAG:
    def __init__(self):
        self.knowledge_base = self._load_medical_knowledge()
    
    def _load_medical_knowledge(self) -> List[Dict[str, Any]]:
        """Load medical knowledge base"""
        return [
            {
                "id": "fever_management",
                "condition": "fever",
                "symptoms": ["high temperature", "chills", "sweating"],
                "urgency": "medium",
                "treatment": "Rest, fluids, paracetamol if needed",
                "when_to_seek_help": "If fever >102F or persists >3 days"
            },
            {
                "id": "chest_pain",
                "condition": "chest pain",
                "symptoms": ["chest discomfort", "pressure", "tightness"],
                "urgency": "high",
                "treatment": "Immediate medical attention required",
                "when_to_seek_help": "Immediately - call emergency services"
            },
            {
                "id": "common_cold",
                "condition": "common cold",
                "symptoms": ["runny nose", "cough", "sore throat"],
                "urgency": "low",
                "treatment": "Rest, warm fluids, throat lozenges",
                "when_to_seek_help": "If symptoms worsen or persist >7 days"
            }
        ]
    
    async def search_medical_knowledge(self, query: str, symptoms: List[str]) -> Dict[str, Any]:
        """Search medical knowledge base"""
        relevant_docs = []
        
        for doc in self.knowledge_base:
            # Simple keyword matching
            score = 0
            query_words = query.lower().split()
            
            for word in query_words:
                if word in doc["condition"].lower():
                    score += 3
                if any(word in symptom.lower() for symptom in doc["symptoms"]):
                    score += 2
            
            for symptom in symptoms:
                if any(symptom.lower() in doc_symptom.lower() for doc_symptom in doc["symptoms"]):
                    score += 2
            
            if score > 0:
                relevant_docs.append({**doc, "relevance_score": score})
        
        # Sort by relevance
        relevant_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "query": query,
            "symptoms": symptoms,
            "relevant_knowledge": relevant_docs[:3],
            "timestamp": datetime.utcnow().isoformat()
        }

# Global RAG instance
medical_rag = MedicalRAG()
