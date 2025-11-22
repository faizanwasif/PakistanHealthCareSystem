from crewai import Agent, Task, Crew, Process
from crewai_tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from config.config import config
from backend.database import get_db
from typing import Dict, Any, List
import logging
import json
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    google_api_key=config.GEMINI_API_KEY,
    temperature=0.3
)

class MedicalKnowledgeTool(BaseTool):
    name: str = "medical_knowledge_search"
    description: str = "Search medical knowledge base for relevant information"
    
    def _run(self, query: str, symptoms: List[str]) -> str:
        try:
            from backend.rag_pipeline import medical_rag
            import asyncio
            
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(medical_rag.search_medical_knowledge(query, symptoms))
            loop.close()
            
            if result["relevant_knowledge"]:
                knowledge_summary = []
                for doc in result["relevant_knowledge"][:2]:  # Top 2 results
                    knowledge_summary.append(f"Condition: {doc['condition']} | Urgency: {doc['urgency']} | Treatment: {doc['treatment']}")
                
                return f"Medical Knowledge Found: {'; '.join(knowledge_summary)}"
            else:
                return "No specific medical knowledge found for this query"
                
        except Exception as e:
            return f"Knowledge search error: {e}"

class DatabaseTool(BaseTool):
    name: str = "database_query"
    description: str = "Query Firebase database for user data, facilities, or medical records"
    
    def _run(self, query_type: str, params: Dict[str, Any]) -> str:
        try:
            db = get_db()
            if query_type == "user_data":
                user = db.collection("users").document(params["user_id"]).get()
                return str(user.to_dict() if user.exists else {})
            elif query_type == "facilities":
                facilities = db.collection("facilities").limit(5).stream()
                return str([f.to_dict() for f in facilities])
            return "Query completed"
        except Exception as e:
            return f"Database error: {e}"

class AgentNegotiationTool(BaseTool):
    name: str = "agent_negotiation"
    description: str = "Challenge or validate decisions from other agents with reasoning"
    
    def _run(self, agent_decision: str, challenge_reason: str, confidence: float) -> str:
        try:
            db = get_db()
            negotiation_id = str(uuid.uuid4())
            
            negotiation_record = {
                "negotiation_id": negotiation_id,
                "original_decision": agent_decision,
                "challenge_reason": challenge_reason,
                "challenger_confidence": confidence,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            db.collection("agent_negotiations").document(negotiation_id).set(negotiation_record)
            
            if confidence > 0.8:
                return f"Strong challenge raised: {challenge_reason}. Requires consensus."
            elif confidence > 0.6:
                return f"Moderate concern: {challenge_reason}. Seeking validation."
            else:
                return f"Weak objection noted: {challenge_reason}. Proceeding with caution."
                
        except Exception as e:
            return f"Negotiation error: {e}"

class ConfidenceScoring(BaseTool):
    name: str = "confidence_scoring"
    description: str = "Score confidence in decisions and track reasoning quality"
    
    def _run(self, decision: str, evidence: List[str], uncertainty_factors: List[str]) -> str:
        try:
            evidence_score = min(len(evidence) * 0.2, 1.0)
            uncertainty_penalty = len(uncertainty_factors) * 0.1
            base_confidence = max(0.1, evidence_score - uncertainty_penalty)
            
            confidence_record = {
                "decision": decision,
                "evidence": evidence,
                "uncertainty_factors": uncertainty_factors,
                "confidence_score": base_confidence,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            db = get_db()
            db.collection("agent_confidence").add(confidence_record)
            
            return f"Confidence: {base_confidence:.2f} | Evidence: {len(evidence)} | Uncertainties: {len(uncertainty_factors)}"
            
        except Exception as e:
            return f"Confidence scoring error: {e}"

class ContextSharingTool(BaseTool):
    name: str = "context_sharing"
    description: str = "Share context and insights between agents for collaborative reasoning"
    
    def _run(self, context_type: str, data: Dict[str, Any], target_agents: List[str]) -> str:
        try:
            db = get_db()
            context_id = str(uuid.uuid4())
            
            shared_context = {
                "context_id": context_id,
                "type": context_type,
                "data": data,
                "target_agents": target_agents,
                "shared_at": datetime.utcnow().isoformat(),
                "accessed_by": []
            }
            
            db.collection("shared_context").document(context_id).set(shared_context)
            return f"Context shared with {len(target_agents)} agents: {context_type}"
            
        except Exception as e:
            return f"Context sharing error: {e}"
    name: str = "send_notification"
    description: str = "Send notifications to users via SMS or app"
    
    def _run(self, user_id: str, message: str, type: str = "sms") -> str:
        try:
            db = get_db()
            db.collection("notifications").add({
                "user_id": user_id,
                "message": message,
                "type": type,
                "status": "sent",
                "created_at": "now"
            })
            return f"Notification sent to {user_id}"
        except Exception as e:
            return f"Notification error: {e}"

# Define Enhanced Agents with Negotiation Capabilities
triage_agent = Agent(
    role='Medical Triage Specialist',
    goal='Assess patient symptoms, determine urgency, and challenge other agents when medical safety is at risk',
    backstory='Expert in Pakistani healthcare protocols with authority to override non-medical recommendations when patient safety is concerned. Known for rigorous evidence-based decisions.',
    verbose=True,
    allow_delegation=True,
    llm=llm,
    tools=[DatabaseTool(), AgentNegotiationTool(), ConfidenceScoring(), ContextSharingTool(), MedicalKnowledgeTool()]
)

eligibility_agent = Agent(
    role='Sehat Card Eligibility Officer',
    goal='Verify patient eligibility and negotiate resource allocation with other agents',
    backstory='Government health program specialist who must balance policy compliance with patient needs. Experienced in finding creative solutions within bureaucratic constraints.',
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[DatabaseTool(), AgentNegotiationTool(), ConfidenceScoring()]
)

facility_agent = Agent(
    role='Healthcare Facility Coordinator',
    goal='Find optimal facilities while considering capacity constraints and negotiating with other agents on recommendations',
    backstory='Local healthcare network coordinator who understands real-world facility limitations and can challenge unrealistic recommendations from other agents.',
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[DatabaseTool(), AgentNegotiationTool(), ContextSharingTool()]
)

notification_agent = Agent(
    role='Patient Communication Coordinator',
    goal='Ensure effective communication while validating the feasibility of other agents recommendations',
    backstory='Healthcare communication specialist who understands patient literacy levels and can challenge overly complex recommendations from medical agents.',
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[NotificationTool(), DatabaseTool(), ConfidenceScoring()]
)

class HealthcareCrew:
    def __init__(self):
        self.crew = None
        self.setup_crew()
    
    def setup_crew(self):
        """Initialize the healthcare crew with agents and tasks"""
        self.crew = Crew(
            agents=[triage_agent, eligibility_agent, facility_agent, notification_agent],
            process=Process.sequential,
            verbose=True,
            memory=True
        )
    
    async def process_patient_query(self, user_id: str, query: str, conversation_id: str) -> Dict[str, Any]:
        """Process patient query through the healthcare crew"""
        try:
            # Create dynamic tasks based on query
            tasks = self._create_tasks(user_id, query, conversation_id)
            
            # Execute crew with tasks
            result = self.crew.kickoff(tasks=tasks)
            
            return {
                "success": True,
                "result": result,
                "conversation_id": conversation_id,
                "agents_involved": [agent.role for agent in self.crew.agents]
            }
        except Exception as e:
            logger.error(f"Crew execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id
            }
    
    def _create_tasks(self, user_id: str, query: str, conversation_id: str) -> list:
        """Create dynamic tasks with agent negotiation and autonomy"""
        tasks = []
        
        # Always start with enhanced triage that includes confidence scoring
        triage_task = Task(
            description=f"""Analyze patient query: '{query}' for user {user_id}. 
            Requirements:
            1. Assess symptoms and determine urgency level (high/medium/low)
            2. Score your confidence in the assessment using evidence
            3. Identify any uncertainty factors
            4. Share critical context with other agents if needed
            5. Be prepared to challenge other agents if patient safety is at risk""",
            agent=triage_agent,
            expected_output="Urgency level, confidence score, symptom analysis, and recommended action with reasoning"
        )
        tasks.append(triage_task)
        
        # Dynamic task creation based on query analysis
        query_lower = query.lower()
        
        # Add eligibility check with negotiation capability
        if any(keyword in query_lower for keyword in ["sehat card", "eligibility", "program", "benefits", "cost", "afford"]):
            eligibility_task = Task(
                description=f"""Check Sehat Card eligibility for user {user_id}.
                Requirements:
                1. Verify eligibility and available programs
                2. Score confidence in eligibility assessment
                3. Challenge triage agent if cost concerns override medical urgency
                4. Negotiate resource allocation if multiple programs available""",
                agent=eligibility_agent,
                expected_output="Eligibility status, program options, confidence score, and any challenges to other agents"
            )
            tasks.append(eligibility_task)
        
        # Add facility search with capacity negotiation
        if any(keyword in query_lower for keyword in ["hospital", "clinic", "doctor", "facility", "nearby", "emergency"]):
            facility_task = Task(
                description=f"""Find appropriate healthcare facilities for user {user_id}.
                Requirements:
                1. Search facilities based on location and medical needs
                2. Share facility capacity context with other agents
                3. Challenge unrealistic recommendations considering real-world constraints
                4. Negotiate alternative options if primary choices unavailable""",
                agent=facility_agent,
                expected_output="Facility recommendations with capacity context and any challenges to other recommendations"
            )
            tasks.append(facility_task)
        
        # Enhanced notification with feasibility validation
        notification_task = Task(
            description=f"""Coordinate patient communication for user {user_id}.
            Requirements:
            1. Review all agent recommendations for feasibility
            2. Challenge overly complex instructions considering patient literacy
            3. Score confidence in communication effectiveness
            4. Create follow-up schedule based on negotiated consensus""",
            agent=notification_agent,
            expected_output="Communication plan, feasibility assessment, and follow-up schedule"
        )
        tasks.append(notification_task)
        
        # Add autonomous proactive task if high urgency detected
        if "emergency" in query_lower or "urgent" in query_lower or "pain" in query_lower:
            emergency_task = Task(
                description=f"""Emergency response coordination for user {user_id}.
                Autonomous decision: System detected potential emergency.
                Requirements:
                1. Override normal workflows if necessary
                2. Coordinate immediate response between all agents
                3. Challenge any delays or bureaucratic obstacles
                4. Ensure rapid escalation protocols are followed""",
                agent=triage_agent,
                expected_output="Emergency response plan with agent coordination"
            )
            tasks.insert(1, emergency_task)  # Insert after triage but before others
        
        return tasks

# Global crew instance
healthcare_crew = HealthcareCrew()
