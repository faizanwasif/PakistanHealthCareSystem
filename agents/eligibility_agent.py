import logging
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from backend.models import EligibilityResult
from backend.database import get_db

logger = logging.getLogger(__name__)

class EligibilityAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are an eligibility verification agent for Pakistan's healthcare programs.
        You check citizen eligibility for Sehat Card and government health subsidies.
        
        Your responsibilities:
        - Verify Sehat Card status
        - Check eligibility for government health programs
        - Match citizens against program criteria (income, location, family size)
        - Recommend enrollment when eligible
        - Provide list of covered facilities
        
        Be helpful and guide citizens through enrollment processes."""
        
        super().__init__(
            agent_id="eligibility_agent",
            capabilities=["sehat_card_verification", "program_eligibility", "enrollment_guidance"],
            system_prompt=system_prompt
        )
        
        # Cached eligibility rules for offline mode
        self.eligibility_rules = {
            "sehat_card": {
                "income_threshold": 50000,  # PKR per month
                "family_size_min": 1
            },
            "maternal_health": {
                "requires": ["pregnant", "children_under_5"]
            },
            "vaccination": {
                "age_range": [0, 5]
            }
        }
    
    async def process(self, input_data: Dict[str, Any]) -> EligibilityResult:
        """Check citizen eligibility for health programs"""
        try:
            # Use consistent user_id (accept both citizen_id and user_id for compatibility)
            user_id = input_data.get("citizen_id") or input_data.get("user_id")
            conversation_id = input_data.get("conversation_id", "")
            
            logger.info(f"Checking eligibility for user: {user_id}")
            
            # Fetch citizen data
            citizen_data = await self._get_citizen_data(user_id)
            
            if not citizen_data:
                raise ValueError(f"Citizen not found: {user_id}")
            
            # Check Sehat Card status
            sehat_card_active = citizen_data.get("sehat_card_status", False)
            
            # Check program eligibility
            eligible_programs = await self._check_program_eligibility(citizen_data)
            
            # Get covered facilities
            covered_facilities = await self._get_covered_facilities(citizen_data)
            
            # Generate reasoning
            decision = await self.make_decision(
                decision_name="eligibility_verified",
                inputs=["citizen_data", "program_rules", "facility_database"],
                alternatives=["eligible", "not_eligible", "partial_eligibility"],
                context={
                    "conversation_id": conversation_id,
                    "citizen_id": user_id,
                    "sehat_card_active": sehat_card_active
                }
            )
            
            result = EligibilityResult(
                citizen_id=user_id,
                sehat_card_active=sehat_card_active,
                eligible_programs=eligible_programs,
                covered_facilities=covered_facilities,
                reasoning=decision.reasoning
            )
            
            logger.info(f"Eligibility result: Sehat Card={sehat_card_active}, Programs={len(eligible_programs)}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            raise
    
    async def _get_citizen_data(self, citizen_id: str) -> Dict[str, Any]:
        """Fetch citizen data from database"""
        try:
            db = get_db()
            # Try users collection first (new system)
            user = await db.users.find_one({"user_id": citizen_id})
            if user:
                return user
            # Fallback to citizens collection (old system)
            citizen = await db.citizens.find_one({"citizen_id": citizen_id})
            return citizen if citizen else {}
        except Exception as e:
            logger.error(f"Error fetching citizen data: {e}")
            return {}
    
    async def _check_program_eligibility(self, citizen_data: Dict[str, Any]) -> List[str]:
        """Check eligibility for various health programs"""
        eligible = []
        
        try:
            # Sehat Card eligibility
            income = citizen_data.get("income", 0)
            family_size = citizen_data.get("family_members", 0)
            
            if income < self.eligibility_rules["sehat_card"]["income_threshold"]:
                if not citizen_data.get("sehat_card_status", False):
                    eligible.append("sehat_card_enrollment")
            
            # Maternal health programs
            if citizen_data.get("has_pregnant_member") or citizen_data.get("children_under_5", 0) > 0:
                eligible.append("maternal_child_health")
            
            # Vaccination programs
            if citizen_data.get("children_under_5", 0) > 0:
                eligible.append("vaccination_program")
            
            # Use AI for complex eligibility
            if len(eligible) == 0:
                prompt = f"""Based on this citizen profile, what health programs might they be eligible for in Pakistan?
                Income: {income} PKR/month
                Family size: {family_size}
                Location: {citizen_data.get('location', {})}
                
                List only program names, comma-separated."""
                
                response = await self.chat_completion([
                    {"role": "user", "content": prompt}
                ])
                
                ai_programs = [p.strip() for p in response.split(",")]
                eligible.extend(ai_programs)
            
            return eligible
            
        except Exception as e:
            logger.error(f"Error checking program eligibility: {e}")
            return []
    
    async def _get_covered_facilities(self, citizen_data: Dict[str, Any]) -> List[str]:
        """Get list of facilities covered by citizen's insurance"""
        try:
            if not citizen_data.get("sehat_card_status", False):
                return []
            
            db = get_db()
            facilities = await db.facilities.find(
                {"sehat_card_accepted": True}
            ).limit(20).to_list(length=20)
            
            return [f["facility_id"] for f in facilities]
            
        except Exception as e:
            logger.error(f"Error fetching covered facilities: {e}")
            return []
