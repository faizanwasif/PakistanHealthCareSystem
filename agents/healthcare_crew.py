from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from config.config import config
from backend.database import get_db
from typing import Dict, Any, List
import logging
import json
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize LLM - Use current Gemini model
llm_config = f"gemini/gemini-2.5-flash"

@tool
def database_query(query_type: str, params: str) -> str:
    """Query Firebase database for user data, facilities, or medical records"""
    try:
        db = get_db()
        params_dict = json.loads(params) if isinstance(params, str) else params
        
        if query_type == "user_data":
            user = db.collection("users").document(params_dict["user_id"]).get()
            return str(user.to_dict() if user.exists else {})
        elif query_type == "facilities":
            facilities = db.collection("facilities").limit(5).stream()
            return str([f.to_dict() for f in facilities])
        return "Query completed"
    except Exception as e:
        return f"Database error: {e}"

@tool
def agent_negotiation(agent_decision: str, challenge_reason: str, confidence: str) -> str:
    """Challenge or validate decisions from other agents with reasoning"""
    try:
        db = get_db()
        negotiation_id = str(uuid.uuid4())
        confidence_float = float(confidence)
        
        negotiation_record = {
            "negotiation_id": negotiation_id,
            "original_decision": agent_decision,
            "challenge_reason": challenge_reason,
            "challenger_confidence": confidence_float,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        db.collection("agent_negotiations").document(negotiation_id).set(negotiation_record)
        
        if confidence_float > 0.8:
            return f"Strong challenge raised: {challenge_reason}. Requires consensus."
        elif confidence_float > 0.6:
            return f"Moderate concern: {challenge_reason}. Seeking validation."
        else:
            return f"Weak objection noted: {challenge_reason}. Proceeding with caution."
            
    except Exception as e:
        return f"Negotiation error: {e}"

@tool
def send_notification(user_id: str, message: str, notification_type: str = "sms") -> str:
    """Send notifications to users via SMS or app"""
    try:
        db = get_db()
        db.collection("notifications").add({
            "user_id": user_id,
            "message": message,
            "type": notification_type,
            "status": "sent",
            "created_at": datetime.utcnow().isoformat()
        })
        return f"Notification sent to {user_id}"
    except Exception as e:
        return f"Notification error: {e}"

# Define Enhanced Agents with Tools
triage_agent = Agent(
    role='Medical Triage Specialist',
    goal='Assess patient symptoms, determine urgency, and challenge other agents when medical safety is at risk',
    backstory='Expert in Pakistani healthcare protocols with authority to override non-medical recommendations when patient safety is concerned.',
    verbose=True,
    allow_delegation=True,
    llm=llm_config,
    tools=[database_query, agent_negotiation]
)

eligibility_agent = Agent(
    role='Sehat Card Eligibility Officer',
    goal='Verify patient eligibility and negotiate resource allocation with other agents',
    backstory='Government health program specialist who must balance policy compliance with patient needs.',
    verbose=True,
    allow_delegation=False,
    llm=llm_config,
    tools=[database_query, agent_negotiation]
)

facility_agent = Agent(
    role='Healthcare Facility Coordinator',
    goal='Find optimal facilities while considering capacity constraints and negotiating with other agents',
    backstory='Local healthcare network coordinator who understands real-world facility limitations.',
    verbose=True,
    allow_delegation=False,
    llm=llm_config,
    tools=[database_query, agent_negotiation]
)

notification_agent = Agent(
    role='Patient Communication Coordinator',
    goal='Ensure effective communication while validating the feasibility of other agents recommendations',
    backstory='Healthcare communication specialist who understands patient literacy levels.',
    verbose=True,
    allow_delegation=False,
    llm=llm_config,
    tools=[send_notification, database_query]
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
            
            # Set tasks on crew and execute
            self.crew.tasks = tasks
            result = self.crew.kickoff()
            
            return {
                "success": True,
                "result": str(result),
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
        
        # Always start with enhanced triage
        triage_task = Task(
            description=f"""Analyze patient query: '{query}' for user {user_id}. 
            Requirements:
            1. Assess symptoms and determine urgency level (high/medium/low)
            2. Provide medical guidance appropriate for Pakistani healthcare context
            3. Challenge other agents if patient safety is at risk
            4. Consider rural vs urban healthcare access""",
            agent=triage_agent,
            expected_output="Urgency level, symptom analysis, and recommended action with reasoning"
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
                2. Challenge triage agent if cost concerns override medical urgency
                3. Negotiate resource allocation if multiple programs available""",
                agent=eligibility_agent,
                expected_output="Eligibility status, program options, and any challenges to other agents"
            )
            tasks.append(eligibility_task)
        
        # Add facility search with capacity negotiation
        if any(keyword in query_lower for keyword in ["hospital", "clinic", "doctor", "facility", "nearby", "emergency"]):
            facility_task = Task(
                description=f"""Find appropriate healthcare facilities for user {user_id}.
                Requirements:
                1. Search facilities based on location and medical needs
                2. Challenge unrealistic recommendations considering real-world constraints
                3. Negotiate alternative options if primary choices unavailable""",
                agent=facility_agent,
                expected_output="Facility recommendations with capacity context"
            )
            tasks.append(facility_task)
        
        # Enhanced notification with feasibility validation
        notification_task = Task(
            description=f"""Coordinate patient communication for user {user_id}.
            Requirements:
            1. Review all agent recommendations for feasibility
            2. Challenge overly complex instructions considering patient literacy
            3. Create follow-up schedule based on consensus""",
            agent=notification_agent,
            expected_output="Communication plan and follow-up schedule"
        )
        tasks.append(notification_task)
        
        return tasks

# Global crew instance
healthcare_crew = HealthcareCrew()
