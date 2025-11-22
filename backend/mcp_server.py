import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import hashlib
import hmac
from cryptography.fernet import Fernet
from backend.database import get_db
from config.config import config

logger = logging.getLogger(__name__)

class PrivateMCPServer:
    def __init__(self):
        self.active_connections = {}
        self.message_queue = {}
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.audit_log = []
        
    async def register_agent(self, agent_id: str, agent_type: str) -> str:
        """Register agent with secure token"""
        token = self._generate_secure_token(agent_id)
        self.active_connections[agent_id] = {
            "type": agent_type,
            "token": token,
            "registered_at": datetime.utcnow().isoformat(),
            "message_count": 0
        }
        
        await self._log_audit("AGENT_REGISTERED", agent_id, {"type": agent_type})
        logger.info(f"Agent {agent_id} registered as {agent_type}")
        return token
    
    async def send_secure_message(self, from_agent: str, to_agent: str, 
                                message_type: str, payload: Dict[str, Any],
                                requires_response: bool = False) -> str:
        """Send encrypted message between agents"""
        
        if from_agent not in self.active_connections:
            raise ValueError(f"Agent {from_agent} not registered")
            
        message_id = str(uuid.uuid4())
        
        # Encrypt sensitive payload
        encrypted_payload = self.cipher.encrypt(json.dumps(payload).encode())
        
        message = {
            "message_id": message_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "encrypted_payload": encrypted_payload.decode(),
            "requires_response": requires_response,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "sent"
        }
        
        # Store in database for persistence
        db = get_db()
        await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: db.collection("mcp_messages").document(message_id).set(message)
        )
        
        # Add to agent's message queue
        if to_agent not in self.message_queue:
            self.message_queue[to_agent] = []
        self.message_queue[to_agent].append(message)
        
        # Update connection stats
        self.active_connections[from_agent]["message_count"] += 1
        
        await self._log_audit("MESSAGE_SENT", from_agent, {
            "to": to_agent, 
            "type": message_type,
            "message_id": message_id
        })
        
        return message_id
    
    async def receive_messages(self, agent_id: str, token: str) -> List[Dict[str, Any]]:
        """Retrieve and decrypt messages for agent"""
        
        if not self._verify_token(agent_id, token):
            raise ValueError("Invalid agent token")
            
        messages = self.message_queue.get(agent_id, [])
        decrypted_messages = []
        
        for message in messages:
            try:
                # Decrypt payload
                encrypted_payload = message["encrypted_payload"].encode()
                decrypted_payload = json.loads(
                    self.cipher.decrypt(encrypted_payload).decode()
                )
                
                decrypted_message = {
                    "message_id": message["message_id"],
                    "from_agent": message["from_agent"],
                    "message_type": message["message_type"],
                    "payload": decrypted_payload,
                    "requires_response": message["requires_response"],
                    "timestamp": message["timestamp"]
                }
                
                decrypted_messages.append(decrypted_message)
                
            except Exception as e:
                logger.error(f"Failed to decrypt message {message['message_id']}: {e}")
        
        # Clear processed messages
        self.message_queue[agent_id] = []
        
        await self._log_audit("MESSAGES_RETRIEVED", agent_id, {
            "count": len(decrypted_messages)
        })
        
        return decrypted_messages
    
    async def share_context(self, agent_id: str, context_type: str, 
                          context_data: Dict[str, Any], 
                          target_agents: List[str]) -> str:
        """Share context between multiple agents"""
        
        context_id = str(uuid.uuid4())
        
        # Encrypt context data
        encrypted_context = self.cipher.encrypt(json.dumps(context_data).encode())
        
        shared_context = {
            "context_id": context_id,
            "sharing_agent": agent_id,
            "context_type": context_type,
            "encrypted_data": encrypted_context.decode(),
            "target_agents": target_agents,
            "shared_at": datetime.utcnow().isoformat(),
            "accessed_by": []
        }
        
        # Store in database
        db = get_db()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: db.collection("shared_contexts").document(context_id).set(shared_context)
        )
        
        # Notify target agents
        for target_agent in target_agents:
            await self.send_secure_message(
                agent_id, target_agent, "CONTEXT_SHARED",
                {"context_id": context_id, "context_type": context_type}
            )
        
        await self._log_audit("CONTEXT_SHARED", agent_id, {
            "context_id": context_id,
            "targets": target_agents
        })
        
        return context_id
    
    def _generate_secure_token(self, agent_id: str) -> str:
        """Generate secure token for agent authentication"""
        secret = config.JWT_SECRET.encode()
        message = f"{agent_id}:{datetime.utcnow().isoformat()}".encode()
        return hmac.new(secret, message, hashlib.sha256).hexdigest()
    
    def _verify_token(self, agent_id: str, token: str) -> bool:
        """Verify agent token"""
        if agent_id not in self.active_connections:
            return False
        return self.active_connections[agent_id]["token"] == token
    
    async def _log_audit(self, action: str, agent_id: str, details: Dict[str, Any]):
        """Log audit trail"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "agent_id": agent_id,
            "details": details
        }
        
        self.audit_log.append(audit_entry)
        
        # Store in database
        db = get_db()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: db.collection("mcp_audit_log").add(audit_entry)
        )
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get MCP system statistics"""
        return {
            "active_agents": len(self.active_connections),
            "total_messages": sum(conn["message_count"] for conn in self.active_connections.values()),
            "queued_messages": sum(len(queue) for queue in self.message_queue.values()),
            "audit_entries": len(self.audit_log),
            "uptime": datetime.utcnow().isoformat()
        }
    
    async def get_trace(self, conversation_id: str) -> Dict[str, Any]:
        """Get agent interaction trace for conversation"""
        try:
            db = get_db()
            
            # Get MCP messages for this conversation
            messages_ref = db.collection("mcp_messages")
            messages = []
            for msg in messages_ref.stream():
                msg_data = msg.to_dict()
                if conversation_id in str(msg_data.get("payload", {})):
                    msg_data['id'] = msg.id
                    messages.append(msg_data)
            
            # Get agent decisions
            decisions_ref = db.collection("agent_decisions")
            decisions = []
            for decision in decisions_ref.stream():
                decision_data = decision.to_dict()
                if conversation_id in str(decision_data.get("context", {})):
                    decision_data['id'] = decision.id
                    decisions.append(decision_data)
            
            # Get agent negotiations
            negotiations_ref = db.collection("agent_negotiations")
            negotiations = []
            for neg in negotiations_ref.stream():
                neg_data = neg.to_dict()
                negotiations.append(neg_data)
            
            return {
                "conversation_id": conversation_id,
                "messages": messages,
                "decisions": decisions,
                "negotiations": negotiations,
                "audit_log": [entry for entry in self.audit_log if conversation_id in str(entry)]
            }
            
        except Exception as e:
            logger.error(f"Error getting trace: {e}")
            return {
                "conversation_id": conversation_id,
                "messages": [],
                "decisions": [],
                "negotiations": [],
                "audit_log": [],
                "error": str(e)
            }

# Global MCP server instance
mcp_server = PrivateMCPServer()
