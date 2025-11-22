import logging
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from datetime import datetime, timedelta
from backend.database import get_db

logger = logging.getLogger(__name__)

class NotificationAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a notification and follow-up agent for Pakistan's healthcare system.
        You send reminders, follow-ups, medicine alerts, and appointment confirmations.
        
        Your responsibilities:
        - Send SMS/notifications in Urdu or English
        - Schedule follow-up reminders based on diagnosis
        - Alert when medicines are restocked
        - Send vaccination reminders
        - Maintain conversation context
        
        Be clear, concise, and culturally appropriate in all communications."""
        
        super().__init__(
            agent_id="notification_agent",
            capabilities=["sms_notification", "follow_up_scheduling", "medicine_alerts"],
            system_prompt=system_prompt
        )
        
        self.notification_queue = []
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process notification request"""
        try:
            notification_type = input_data.get("type", "general")
            citizen_id = input_data.get("citizen_id")
            conversation_id = input_data.get("conversation_id", "")
            
            logger.info(f"Processing notification: {notification_type} for {citizen_id}")
            
            if notification_type == "facility_recommendation":
                return await self._send_facility_notification(input_data)
            elif notification_type == "follow_up":
                return await self._schedule_follow_up(input_data)
            elif notification_type == "medicine_alert":
                return await self._send_medicine_alert(input_data)
            elif notification_type == "appointment_confirmation":
                return await self._send_appointment_confirmation(input_data)
            else:
                return await self._send_general_notification(input_data)
                
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            raise
    
    async def _send_facility_notification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send facility recommendation notification"""
        try:
            facility_name = data.get("facility_name")
            distance_km = data.get("distance_km")
            services = data.get("services", [])
            medicine_available = data.get("medicine_available", {})
            timings = data.get("timings", "8am-2pm")
            
            # Generate Urdu message
            message_urdu = await self._generate_urdu_message(
                f"""Create a concise SMS in Urdu informing citizen about:
                Facility: {facility_name}
                Distance: {distance_km} km
                Services: {', '.join(services)}
                Timings: {timings}
                Medicine available: {', '.join([k for k, v in medicine_available.items() if v])}
                
                Keep it under 160 characters, friendly tone."""
            )
            
            # Create decision trace
            decision = await self.make_decision(
                decision_name="send_facility_notification",
                inputs=["facility_data", "citizen_preferences", "message_template"],
                alternatives=["sms", "app_notification", "both"],
                context={
                    "conversation_id": data.get("conversation_id"),
                    "notification_type": "facility_recommendation"
                }
            )
            
            # Queue notification
            notification = {
                "citizen_id": data.get("citizen_id"),
                "message": message_urdu,
                "type": "sms",
                "status": "queued",
                "created_at": datetime.utcnow()
            }
            
            self.notification_queue.append(notification)
            
            # Save to database
            db = get_db()
            await db.notifications.insert_one(notification)
            
            logger.info(f"Facility notification queued: {facility_name}")
            return {
                "status": "queued",
                "message": message_urdu,
                "reasoning": decision.reasoning
            }
            
        except Exception as e:
            logger.error(f"Error sending facility notification: {e}")
            raise
    
    async def _schedule_follow_up(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule follow-up reminder"""
        try:
            citizen_id = data.get("citizen_id")
            diagnosis = data.get("diagnosis", "")
            days_until_followup = data.get("days", 3)
            
            follow_up_date = datetime.utcnow() + timedelta(days=days_until_followup)
            
            message = await self._generate_urdu_message(
                f"""Create a follow-up reminder in Urdu:
                Diagnosis: {diagnosis}
                Follow-up in: {days_until_followup} days
                
                Remind them to check symptoms and contact if worse."""
            )
            
            # Create decision trace
            decision = await self.make_decision(
                decision_name="schedule_follow_up",
                inputs=["diagnosis", "medical_guidelines", "citizen_history"],
                alternatives=["3_days", "7_days", "14_days"],
                context={
                    "conversation_id": data.get("conversation_id"),
                    "follow_up_date": follow_up_date.isoformat()
                }
            )
            
            # Save follow-up
            db = get_db()
            await db.follow_ups.insert_one({
                "citizen_id": citizen_id,
                "message": message,
                "scheduled_date": follow_up_date,
                "status": "scheduled",
                "created_at": datetime.utcnow()
            })
            
            logger.info(f"Follow-up scheduled for {citizen_id} on {follow_up_date}")
            return {
                "status": "scheduled",
                "follow_up_date": follow_up_date.isoformat(),
                "message": message,
                "reasoning": decision.reasoning
            }
            
        except Exception as e:
            logger.error(f"Error scheduling follow-up: {e}")
            raise
    
    async def _send_medicine_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send medicine availability alert"""
        try:
            medicine_name = data.get("medicine_name")
            facility_name = data.get("facility_name")
            citizen_id = data.get("citizen_id")
            
            message = await self._generate_urdu_message(
                f"""Create SMS in Urdu:
                Medicine {medicine_name} is now available at {facility_name}.
                Inform citizen they can collect it."""
            )
            
            decision = await self.make_decision(
                decision_name="send_medicine_alert",
                inputs=["medicine_inventory", "citizen_prescription", "facility_location"],
                alternatives=["immediate_alert", "batch_alert", "no_alert"],
                context={
                    "conversation_id": data.get("conversation_id"),
                    "medicine": medicine_name
                }
            )
            
            notification = {
                "citizen_id": citizen_id,
                "message": message,
                "type": "medicine_alert",
                "status": "queued",
                "created_at": datetime.utcnow()
            }
            
            self.notification_queue.append(notification)
            
            db = get_db()
            await db.notifications.insert_one(notification)
            
            logger.info(f"Medicine alert sent for {medicine_name}")
            return {
                "status": "queued",
                "message": message,
                "reasoning": decision.reasoning
            }
            
        except Exception as e:
            logger.error(f"Error sending medicine alert: {e}")
            raise
    
    async def _send_appointment_confirmation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send appointment confirmation"""
        try:
            facility_name = data.get("facility_name")
            appointment_date = data.get("appointment_date")
            citizen_id = data.get("citizen_id")
            
            message = await self._generate_urdu_message(
                f"""Create appointment confirmation in Urdu:
                Facility: {facility_name}
                Date: {appointment_date}
                Remind to bring Sehat Card if applicable."""
            )
            
            notification = {
                "citizen_id": citizen_id,
                "message": message,
                "type": "appointment",
                "status": "queued",
                "created_at": datetime.utcnow()
            }
            
            self.notification_queue.append(notification)
            
            db = get_db()
            await db.notifications.insert_one(notification)
            
            return {"status": "queued", "message": message}
            
        except Exception as e:
            logger.error(f"Error sending appointment confirmation: {e}")
            raise
    
    async def _send_general_notification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send general notification"""
        message = data.get("message", "")
        citizen_id = data.get("citizen_id")
        
        notification = {
            "citizen_id": citizen_id,
            "message": message,
            "type": "general",
            "status": "queued",
            "created_at": datetime.utcnow()
        }
        
        self.notification_queue.append(notification)
        
        db = get_db()
        await db.notifications.insert_one(notification)
        
        return {"status": "queued", "message": message}
    
    async def _generate_urdu_message(self, prompt: str) -> str:
        """Generate Urdu message using AI"""
        try:
            response = await self.chat_completion([
                {"role": "user", "content": prompt}
            ])
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating Urdu message: {e}")
            return "Notification message"
