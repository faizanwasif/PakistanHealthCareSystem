import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import google.generativeai as genai
from config.config import config
from backend.models import MCPMessage, AgentDecision
import json

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, agent_id: str, capabilities: List[str], system_prompt: str):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.system_prompt = system_prompt
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.AGENT_MODEL)
        self.conversation_history: Dict[str, List[Dict]] = {}
        
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Override this method in child classes"""
        raise NotImplementedError
    
    async def make_decision(
        self,
        decision_name: str,
        inputs: List[str],
        alternatives: List[str],
        context: Dict[str, Any]
    ) -> AgentDecision:
        """Create a decision with reasoning"""
        decision_id = str(uuid.uuid4())
        
        # Use OpenAI to generate reasoning
        reasoning = await self._generate_reasoning(decision_name, inputs, alternatives, context)
        
        decision = AgentDecision(
            decision_id=decision_id,
            agent_id=self.agent_id,
            decision=decision_name,
            reasoning=reasoning,
            inputs=inputs,
            alternatives_considered=alternatives,
            confidence=0.85,  # Can be calculated based on model confidence
            context=context
        )
        
        return decision
    
    async def _generate_reasoning(
        self,
        decision: str,
        inputs: List[str],
        alternatives: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate reasoning using OpenAI"""
        try:
            prompt = f"""
            Decision: {decision}
            Inputs considered: {', '.join(inputs)}
            Alternatives: {', '.join(alternatives)}
            Context: {json.dumps(context, default=str)}
            
            Provide a clear, concise reasoning (2-3 sentences) for why this decision was made.
            """
            
            response = await self.model.generate_content_async(
                f"{self.system_prompt}\n\n{prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=config.AGENT_TEMPERATURE,
                    max_output_tokens=150
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
                ]
            )
            
            # Check if response has valid parts before accessing text
            if response.candidates and response.candidates[0].content.parts:
                return response.text.strip()
            else:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
                logger.warning(f"Empty response from Gemini, finish_reason: {finish_reason}")
                return "Unable to process request at this time."
        except Exception as e:
            logger.error(f"Error generating reasoning: {e}")
            return f"Decision made based on {', '.join(inputs)}"
    
    async def send_mcp_message(
        self,
        to_agent: str,
        payload: Dict[str, Any],
        requires_response: bool = False
    ) -> MCPMessage:
        """Send message via MCP"""
        message = MCPMessage(
            message_id=str(uuid.uuid4()),
            from_agent=self.agent_id,
            to_agent=to_agent,
            payload=payload,
            requires_response=requires_response
        )
        return message
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict]] = None
    ) -> str:
        """Get chat completion from OpenAI"""
        try:
            # Convert messages to single prompt for Gemini
            full_prompt = self.system_prompt + "\n\n"
            for msg in messages:
                full_prompt += f"{msg['role']}: {msg['content']}\n"
            
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=config.AGENT_TEMPERATURE,
                    max_output_tokens=config.AGENT_MAX_TOKENS
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
                ]
            )
            
            # Check if response has valid parts before accessing text
            if response.candidates and response.candidates[0].content.parts:
                return response.text
            else:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
                logger.warning(f"Empty response from Gemini, finish_reason: {finish_reason}")
                return "Unable to process request at this time."
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    def add_to_history(self, conversation_id: str, role: str, content: str):
        """Add message to conversation history"""
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        self.conversation_history[conversation_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history.get(conversation_id, [])
