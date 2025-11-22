import logging
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from backend.models import TriageResult, UrgencyLevel
import re

logger = logging.getLogger(__name__)

class TriageAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a medical triage agent for Pakistan's healthcare system.
        You analyze citizen health queries in Urdu or English and assess urgency.
        
        Your responsibilities:
        - Classify symptoms and determine urgency (high/medium/low)
        - Ask clarifying questions when needed
        - Recommend immediate BHU visit for emergencies
        - Suggest home care for minor issues
        - Be culturally sensitive and communicate clearly in Urdu/English
        
        Urgency Levels:
        - HIGH: Severe symptoms, difficulty breathing, chest pain, severe bleeding, unconsciousness
        - MEDIUM: Persistent fever, moderate pain, infection signs
        - LOW: Minor ailments, routine checkups, preventive care
        
        Always provide reasoning for your assessment."""
        
        super().__init__(
            agent_id="triage_agent",
            capabilities=["symptom_analysis", "urgency_assessment", "clarifying_questions"],
            system_prompt=system_prompt
        )
        
        # Offline cache for common symptoms
        self.symptom_cache = {
            "bukhar": {"urgency": "medium", "action": "monitor_and_visit"},
            "sans lene me takleef": {"urgency": "high", "action": "immediate_visit"},
            "dard": {"urgency": "low", "action": "home_care"},
            "khoon": {"urgency": "high", "action": "immediate_visit"},
            "chakkar": {"urgency": "medium", "action": "visit_soon"}
        }
    
    async def process(self, input_data: Dict[str, Any]) -> TriageResult:
        """Process citizen health query and perform triage"""
        try:
            citizen_query = input_data.get("query", "")
            conversation_id = input_data.get("conversation_id", "")
            
            logger.info(f"Triage processing query: {citizen_query}")
            
            # Add to conversation history
            self.add_to_history(conversation_id, "user", citizen_query)
            
            # Check if this is a health-related query
            health_keywords = ["pain", "fever", "sick", "hurt", "ache", "doctor", "hospital", "medicine", "treatment", "emergency", "symptoms", "bukhar", "dard", "bimari"]
            is_health_query = any(keyword in citizen_query.lower() for keyword in health_keywords)
            
            if not is_health_query and len(citizen_query.split()) < 10:
                # Handle general greetings and simple queries
                simple_responses = {
                    "hello": "Hello! I'm here to help with your health concerns. How are you feeling today?",
                    "hi": "Hi there! I'm your healthcare assistant. What can I help you with?",
                    "hey": "Hey! I'm your healthcare assistant. What can I help you with today?",
                    "help": "I can help you with health concerns, find nearby hospitals, and provide medical guidance. What do you need assistance with?",
                    "thanks": "You're welcome! Feel free to ask if you have any health concerns.",
                    "bye": "Take care! Remember to stay healthy and don't hesitate to reach out if you need medical assistance.",
                    "helo": "Hello! I'm your healthcare assistant. How can I help you today?",
                    "salam": "Wa alaykum salam! I'm here to help with your health needs. What can I assist you with?"
                }
                
                for key, response in simple_responses.items():
                    if key in citizen_query.lower():
                        logger.info(f"Handling simple greeting: {key}")
                        return TriageResult(
                            citizen_query=citizen_query,
                            symptoms=[],
                            urgency_level=UrgencyLevel.LOW,
                            recommended_action=response,
                            clarifying_questions=None,
                            reasoning="General greeting or simple query - no medical assessment needed"
                        )
                
                # Default response for unrecognized general queries
                logger.info("Handling general non-health query")
                return TriageResult(
                    citizen_query=citizen_query,
                    symptoms=[],
                    urgency_level=UrgencyLevel.LOW,
                    recommended_action="I'm here to help with your health concerns. Please describe any symptoms you're experiencing, or ask about finding nearby hospitals.",
                    clarifying_questions=None,
                    reasoning="General query - providing guidance on how to use the system"
                )
            
            # Extract symptoms for health queries
            symptoms = await self._extract_symptoms(citizen_query)
            
            # Assess urgency
            urgency_level = await self._assess_urgency(citizen_query, symptoms)
            
            # Generate recommendation
            recommended_action = await self._generate_recommendation(urgency_level, symptoms, citizen_query)
            
            # Check if clarifying questions needed
            clarifying_questions = await self._generate_clarifying_questions(
                citizen_query, symptoms, urgency_level
            )
            
            # Create decision trace
            decision = await self.make_decision(
                decision_name=f"triage_{urgency_level.value}",
                inputs=["citizen_query", "symptoms", "medical_guidelines"],
                alternatives=["high_urgency", "medium_urgency", "low_urgency"],
                context={
                    "conversation_id": conversation_id,
                    "query": citizen_query,
                    "symptoms": symptoms
                }
            )
            
            result = TriageResult(
                citizen_query=citizen_query,
                symptoms=symptoms,
                urgency_level=urgency_level,
                recommended_action=recommended_action,
                clarifying_questions=clarifying_questions,
                reasoning=decision.reasoning
            )
            
            logger.info(f"Triage result: {urgency_level.value} - {recommended_action}")
            return result
            
        except Exception as e:
            logger.error(f"Error in triage processing: {e}")
            raise
    
    async def _extract_symptoms(self, query: str) -> List[str]:
        """Extract symptoms from query using AI"""
        try:
            prompt = f"""Extract all health symptoms from this query (in Urdu or English):
            "{query}"
            
            Return only a comma-separated list of symptoms in English.
            Example: fever, cough, headache"""
            
            response = await self.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            symptoms = [s.strip() for s in response.split(",")]
            return symptoms
        except Exception as e:
            logger.error(f"Error extracting symptoms: {e}")
            return ["unknown"]
    
    async def _assess_urgency(self, query: str, symptoms: List[str]) -> UrgencyLevel:
        """Assess urgency level using AI and rules"""
        try:
            # Check cache first for offline mode
            query_lower = query.lower()
            for symptom, data in self.symptom_cache.items():
                if symptom in query_lower:
                    if data["urgency"] == "high":
                        return UrgencyLevel.HIGH
                    elif data["urgency"] == "medium":
                        return UrgencyLevel.MEDIUM
            
            # Use AI for detailed assessment
            prompt = f"""Assess the urgency level for this health query:
            Query: "{query}"
            Symptoms: {', '.join(symptoms)}
            
            Respond with only one word: HIGH, MEDIUM, or LOW
            
            HIGH: Life-threatening, needs immediate care
            MEDIUM: Needs medical attention within 24 hours
            LOW: Can wait or manage at home"""
            
            response = await self.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            response = response.strip().upper()
            if "HIGH" in response:
                return UrgencyLevel.HIGH
            elif "MEDIUM" in response:
                return UrgencyLevel.MEDIUM
            else:
                return UrgencyLevel.LOW
                
        except Exception as e:
            logger.error(f"Error assessing urgency: {e}")
            return UrgencyLevel.MEDIUM  # Default to medium for safety
    
    async def _generate_recommendation(self, urgency: UrgencyLevel, symptoms: List[str], query: str = "") -> str:
        """Generate action recommendation"""
        
        # Check if this is a facility search request
        facility_keywords = ["find hospital", "nearby hospital", "hospital near", "find clinic", "nearby clinic", "find doctor", "nearby doctor"]
        if any(keyword in query.lower() for keyword in facility_keywords):
            return "I'll help you find nearby hospitals and healthcare facilities in your area."
        
        # Medical disclaimer for health-related advice
        disclaimer = "\n\n⚠️ DISCLAIMER: This is AI-generated guidance only. Always consult qualified healthcare professionals for medical decisions."
        
        # Standard medical recommendations
        if urgency == UrgencyLevel.HIGH:
            return "Immediate BHU visit required - emergency care needed" + disclaimer
        elif urgency == UrgencyLevel.MEDIUM:
            return "Schedule BHU visit within 24 hours for medical consultation" + disclaimer
        else:
            return "Home care recommended - monitor symptoms and schedule routine checkup if needed" + disclaimer
    
    async def _generate_clarifying_questions(
        self, query: str, symptoms: List[str], urgency: UrgencyLevel
    ) -> List[str]:
        """Generate clarifying questions if needed"""
        try:
            if urgency == UrgencyLevel.HIGH:
                return []  # No time for questions in emergencies
            
            prompt = f"""For this health query, generate 1-2 clarifying questions in Urdu:
            Query: "{query}"
            Symptoms: {', '.join(symptoms)}
            
            Ask about duration, severity, or other relevant details.
            Format: One question per line."""
            
            response = await self.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            questions = [q.strip() for q in response.split("\n") if q.strip()]
            return questions[:2]  # Max 2 questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return []
