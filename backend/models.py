from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class UrgencyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MessageStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"

class MCPMessage(BaseModel):
    message_id: str
    from_agent: str
    to_agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]
    requires_response: bool = False
    status: MessageStatus = MessageStatus.PENDING

class TriageResult(BaseModel):
    citizen_query: str
    symptoms: List[str]
    urgency_level: UrgencyLevel
    recommended_action: str
    clarifying_questions: Optional[List[str]] = None
    reasoning: str

class EligibilityResult(BaseModel):
    citizen_id: str
    sehat_card_active: bool
    eligible_programs: List[str]
    covered_facilities: List[str]
    reasoning: str

class FacilityRecommendation(BaseModel):
    facility_id: str
    facility_name: str
    distance_km: float
    available_services: List[str]
    medicine_availability: Dict[str, bool]
    estimated_wait_time: Optional[int] = None
    reasoning: str

class AgentDecision(BaseModel):
    decision_id: str
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    decision: str
    reasoning: str
    inputs: List[str]
    alternatives_considered: List[str]
    confidence: float
    context: Dict[str, Any]

class Citizen(BaseModel):
    citizen_id: str
    name: str
    phone: str
    location: Dict[str, float]  # {"lat": 24.8607, "lng": 67.0011}
    sehat_card_status: bool
    family_members: int
    medical_history: List[Dict[str, Any]] = []

class Facility(BaseModel):
    facility_id: str
    name: str
    type: str
    location: Dict[str, float]
    services: List[str]
    doctors: List[Dict[str, str]]
    timings: str
    sehat_card_accepted: bool

class Conversation(BaseModel):
    conversation_id: str
    citizen_id: str
    messages: List[Dict[str, Any]]
    agent_interactions: List[Dict[str, Any]]
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
