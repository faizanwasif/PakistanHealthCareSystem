import google.generativeai as genai
from config.config import config
import logging
from typing import Dict, Any
import yaml

logger = logging.getLogger(__name__)

class SimpleHealthcareAgent:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    async def process_query(self, user_id: str, query: str, conversation_id: str) -> Dict[str, Any]:
        """Process healthcare query quickly and directly"""
        try:
            prompt = f"""You are a Pakistani healthcare assistant. Respond directly to the user's question in a helpful, medical way.

User Query: {query}

Provide a helpful response with urgency assessment and recommended action.
Keep response under 200 words. Be practical and helpful for Pakistani healthcare context.
Include both English and Urdu if appropriate.

STRICTLY return your response in this YAML format:
```yaml
response: "your helpful response here"
urgency: "high/medium/low"
action: "recommended action"
agents_involved: ["Medical Triage Specialist"]
```"""

            response = self.model.generate_content(prompt)
            
            try:
                # Extract YAML from response
                response_text = response.text.strip()
                if "```yaml" in response_text:
                    yaml_content = response_text.split("```yaml")[1].split("```")[0].strip()
                else:
                    yaml_content = response_text
                
                # Parse YAML
                result = yaml.safe_load(yaml_content)
                
                # Ensure all required fields exist
                if not isinstance(result, dict):
                    raise ValueError("Invalid YAML structure")
                    
            except Exception as e:
                logger.warning(f"YAML parsing failed: {e}, using fallback")
                # Fallback if YAML parsing fails
                result = {
                    "response": response.text,
                    "urgency": "medium",
                    "action": "Consult healthcare provider if symptoms persist",
                    "agents_involved": ["Medical Triage Specialist"]
                }
            
            return {
                "success": True,
                "result": result["response"],
                "urgency": result.get("urgency", "medium"),
                "action": result.get("action", ""),
                "agents_involved": result.get("agents_involved", ["Medical Triage Specialist"]),
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Healthcare agent error: {e}")
            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id
            }

# Global instance
simple_healthcare_agent = SimpleHealthcareAgent()
