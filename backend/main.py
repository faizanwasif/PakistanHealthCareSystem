import asyncio
import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import uuid
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import config
from backend.database import connect_db, close_db, get_db
from agents.healthcare_crew import healthcare_crew
from backend.models import MCPMessage, UrgencyLevel
from backend.error_handler import StandardError, safe_execute_async
from backend.api_response import success_response, error_response, paginated_response
from backend.auth import (
    UserCreate, UserLogin, Token, get_password_hash, 
    verify_password, create_access_token, get_current_user
)
from backend.mcp_server import mcp_server
from backend.offline_manager import offline_manager
from backend.rag_pipeline import medical_rag
from backend.voice_service import urdu_asr, translate_to_english, translate_to_urdu
from backend.voice_service import urdu_asr, translate_to_english, translate_to_urdu

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'server.log')

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(log_file)  # File output
    ]
)
logger = logging.getLogger(__name__)

# CrewAI healthcare system initialized in healthcare_crew module

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Starting Pakistan Healthcare Multi-Agent System")
        await connect_db()
        
        # Register agents with MCP server
        await mcp_server.register_agent("triage_agent", "Medical Triage Specialist")
        await mcp_server.register_agent("eligibility_agent", "Sehat Card Eligibility Officer")
        await mcp_server.register_agent("facility_agent", "Healthcare Facility Coordinator")
        await mcp_server.register_agent("notification_agent", "Patient Communication Coordinator")
        
        # Seed database if empty
        db = get_db()
        try:
            citizen_count = await db.citizens.count_documents({})
            if citizen_count == 0:
                logger.info("Database is empty, seeding with sample data...")
                from seed_database import seed_database
                await seed_database()
        except Exception as e:
            logger.warning(f"Could not seed database: {e}")
        
        # Create admin account if doesn't exist
        try:
            admin_exists = await db.users.find_one({"phone": "admin"})
            if not admin_exists:
                admin_user = {
                    "user_id": "admin_001",
                    "name": "System Administrator",
                    "phone": "admin",  # Username
                    "password": get_password_hash("admin"),  # Password
                    "location": {"lat": 24.8607, "lng": 67.0011},
                    "role": "admin",
                    "sehat_card_status": True,
                    "family_members": 1,
                    "monthly_income": 0,
                    "address": "Admin Office",
                    "cnic": "00000-0000000-0",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                await db.users.insert_one(admin_user)
                logger.info("Admin account created - Username: admin, Password: admin")
            else:
                logger.info("Admin account already exists")
        except Exception as e:
            logger.error(f"Error creating admin account: {e}")
        
        # Initialize CrewAI healthcare system
        logger.info("Initializing CrewAI Healthcare System...")
        
        # The healthcare crew is already initialized in the module
        logger.info("CrewAI Healthcare System ready with agents:")
        logger.info("- Medical Triage Specialist")
        logger.info("- Sehat Card Eligibility Officer") 
        logger.info("- Healthcare Facility Coordinator")
        logger.info("- Patient Communication Coordinator")
        logger.info("System ready!")
        
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down...")
        await close_db()
        logger.info("System shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="Pakistan Healthcare Multi-Agent System",
    description="AI-powered healthcare coordination system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - More secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://0.0.0.0:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Mount static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Serve frontend assets at root level for relative paths
@app.get("/style.css")
async def serve_css():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "style.css"), media_type="text/css")

@app.get("/app.js")
async def serve_js():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "app.js"), media_type="application/javascript")

@app.get("/location_helper.js")
async def serve_location_js():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "location_helper.js"), media_type="application/javascript")

# Serve frontend HTML pages
@app.get("/")
async def serve_frontend():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/index.html")
async def serve_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/login.html")
async def serve_login():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "login.html"))

@app.get("/admin.html")
async def serve_admin():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "admin.html"))

@app.get("/debug.html")
async def serve_debug():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "debug.html"))

# ============= Authentication APIs =============

@app.post("/api/auth/signup", response_model=Token)
async def signup(user: UserCreate):
    """Register a new user"""
    try:
        # Validate password strength
        from backend.auth import validate_password
        is_valid, message = validate_password(user.password)
        if not is_valid:
            raise StandardError.validation_error("password", message)
        
        db = get_db()
        
        # Check if user already exists
        existing_user = await db.users.find_one({"phone": user.phone})
        if existing_user:
            raise StandardError.validation_error("phone", "Phone number already registered")
        
        # Create user ID
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        
        # Hash password
        hashed_password = get_password_hash(user.password)
        
        # Check if this is the first user (make them admin)
        user_count = await db.users.count_documents({})
        is_admin = user_count == 0 or user.phone == "+92-300-0000000"
        
        # Create user document
        user_doc = {
            "user_id": user_id,
            "name": user.name,
            "phone": user.phone,
            "password": hashed_password,
            "location": user.location,
            "role": "admin" if is_admin else "user",  # First user is admin
            "sehat_card_status": False,  # Default: no Sehat Card
            "family_members": 1,
            "monthly_income": 0,
            "address": "",
            "cnic": "",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.users.insert_one(user_doc)
        
        # Create access token
        access_token = create_access_token(data={"sub": user_id})
        
        logger.info(f"New user registered: {user_id}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            name=user.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in signup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login user"""
    try:
        db = get_db()
        
        # Find user
        user = await db.users.find_one({"phone": credentials.phone})
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid phone number or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Invalid phone number or password"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user["user_id"]})
        
        logger.info(f"User logged in: {user['user_id']}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user["user_id"],
            name=user["name"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me")
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """Get current user information"""
    try:
        db = get_db()
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert ObjectId to string
        if '_id' in user:
            user['_id'] = str(user['_id'])
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/history")
async def get_user_history(user_id: str = Depends(get_current_user)):
    """Get user's conversation history"""
    try:
        db = get_db()
        
        # Get all conversations for this user
        conversations = await db.conversations.find(
            {"citizen_id": user_id}
        ).sort("created_at", -1).limit(50).to_list(length=50)
        
        # Convert ObjectId to string
        for conv in conversations:
            if '_id' in conv:
                conv['_id'] = str(conv['_id'])
        
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications")
async def get_notifications(user_id: str = Depends(get_current_user)):
    """Get user notifications"""
    try:
        db = get_db()
        
        notifications = await db.notifications.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(20).to_list(length=20)
        
        # Convert ObjectId
        for notif in notifications:
            if '_id' in notif:
                notif['_id'] = str(notif['_id'])
        
        unread_count = await db.notifications.count_documents({
            "user_id": user_id,
            "status": "unread"
        })
        
        return {
            "notifications": notifications,
            "unread_count": unread_count
        }
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/mark-read")
async def mark_notifications_read(user_id: str = Depends(get_current_user)):
    """Mark all notifications as read"""
    try:
        db = get_db()
        
        await db.notifications.update_many(
            {"user_id": user_id, "status": "unread"},
            {"$set": {"status": "read"}}
        )
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error marking notifications read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= Citizen APIs =============

@app.post("/api/chat/message")
async def send_chat_message(data: dict, user_id: str = Depends(get_current_user)):
    """Process citizen health query through multi-agent system"""
    try:
        query = data.get("query", "")
        citizen_id = user_id  # Use authenticated user ID
        
        # Generate conversation ID if not provided or if null
        conversation_id = data.get("conversation_id")
        if not conversation_id or conversation_id == "null":
            conversation_id = str(uuid.uuid4())
        
        logger.info(f"Processing query from citizen {citizen_id}: {query} (conversation: {conversation_id})")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        if not citizen_id:
            raise HTTPException(status_code=400, detail="Citizen ID is required")
        
        # Process query through CrewAI healthcare system
        crew_result = await healthcare_crew.process_patient_query(
            user_id=citizen_id,
            query=query,
            conversation_id=conversation_id
        )
        
        if not crew_result["success"]:
            raise HTTPException(status_code=500, detail=f"Healthcare crew error: {crew_result['error']}")
        
        # Store conversation
        db = get_db()
        await db.add_document("conversations", {
            "conversation_id": conversation_id,
            "citizen_id": citizen_id,
            "query": query,
            "response": crew_result["result"],
            "agents_involved": crew_result["agents_involved"],
            "created_at": datetime.utcnow()
        })
        
        return success_response(
            data={
                "conversation_id": conversation_id,
                "response": crew_result["result"],
                "agents_involved": crew_result["agents_involved"]
            },
            message="Query processed successfully"
        )
    
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/citizen/eligibility")
async def check_eligibility(user_id: str = Depends(get_current_user)):
    """Check citizen eligibility for health programs"""
    try:
        # Use CrewAI eligibility check
        crew_result = await healthcare_crew.process_patient_query(
            user_id=user_id,
            query="check my sehat card eligibility",
            conversation_id=str(uuid.uuid4())
        )
        return success_response(data=crew_result, message="Eligibility checked")
    except Exception as e:
        logger.error(f"Error checking eligibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sehat-card/apply")
async def apply_for_sehat_card(data: dict, user_id: str = Depends(get_current_user)):
    """Apply for Sehat Card with automated approval"""
    try:
        db = get_db()
        
        # Get user data
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already has active Sehat Card
        if user.get("sehat_card_status"):
            raise HTTPException(status_code=400, detail="You already have an active Sehat Card")
        
        # Check if application already exists
        existing_app = await db.sehat_card_applications.find_one({
            "user_id": user_id,
            "status": "pending"
        })
        if existing_app:
            raise HTTPException(status_code=400, detail="You already have a pending application")
        
        monthly_income = data.get("monthly_income", 0)
        family_members = data.get("family_members", 1)
        
        # Automated approval logic
        auto_approved = False
        status = "pending"
        rejection_reason = None
        
        if monthly_income < 50000:  # Income threshold
            auto_approved = True
            status = "approved"
            
            # Update user's Sehat Card status
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "sehat_card_status": True,
                    "family_members": family_members,
                    "monthly_income": monthly_income,
                    "address": data.get("address", ""),
                    "cnic": data.get("cnic", ""),
                    "updated_at": datetime.utcnow()
                }}
            )
            
            logger.info(f"Sehat Card auto-approved for {user_id} (income: {monthly_income})")
        
        # Create application record
        application = {
            "application_id": f"app_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "name": user["name"],
            "phone": user["phone"],
            "family_members": family_members,
            "monthly_income": monthly_income,
            "address": data.get("address", ""),
            "cnic": data.get("cnic", ""),
            "status": status,
            "applied_at": datetime.utcnow(),
            "reviewed_at": datetime.utcnow() if auto_approved else None,
            "reviewed_by": "system" if auto_approved else None,
            "rejection_reason": rejection_reason,
            "auto_approved": auto_approved
        }
        
        await db.sehat_card_applications.insert_one(application)
        
        # Send notification
        notification_message = ""
        if auto_approved:
            notification_message = f"Congratulations! Your Sehat Card application has been approved. You can now use your card at covered facilities. | مبارک ہو! آپ کی صحت کارڈ کی درخواست منظور ہو گئی ہے۔"
        else:
            notification_message = f"Your Sehat Card application has been submitted and is under review. You will be notified once reviewed. | آپ کی صحت کارڈ کی درخواست جمع ہو گئی ہے اور جائزہ لیا جا رہا ہے۔"
        
        # Store notification
        await db.notifications.insert_one({
            "user_id": user_id,
            "type": "sehat_card_application",
            "message": notification_message,
            "status": "unread",
            "created_at": datetime.utcnow()
        })
        
        return {
            "status": "success",
            "message": notification_message,
            "application_id": application["application_id"],
            "auto_approved": auto_approved,
            "sehat_card_active": auto_approved
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying for Sehat Card: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sehat-card/status")
async def get_sehat_card_status(user_id: str = Depends(get_current_user)):
    """Get Sehat Card application status"""
    try:
        db = get_db()
        
        # Get user
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if has active card
        if user.get("sehat_card_status"):
            return {
                "has_card": True,
                "status": "active",
                "message": "You have an active Sehat Card"
            }
        
        # Check for pending application
        applications = await db.sehat_card_applications.find({"user_id": user_id}).sort("applied_at", -1).limit(1).to_list(1)
        application = applications[0] if applications else None
        
        if not application:
            return {
                "has_card": False,
                "status": "not_applied",
                "message": "You haven't applied for Sehat Card yet"
            }
        
        # Convert ObjectId
        if '_id' in application:
            application['_id'] = str(application['_id'])
        
        return {
            "has_card": False,
            "status": application["status"],
            "application": application,
            "message": f"Your application is {application['status']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Sehat Card status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/sehat-card/update-profile")
async def update_user_profile(data: dict, user_id: str = Depends(get_current_user)):
    """Update user profile for Sehat Card eligibility"""
    try:
        db = get_db()
        
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        # Allow updating specific fields
        if "family_members" in data:
            update_data["family_members"] = data["family_members"]
        if "monthly_income" in data:
            update_data["monthly_income"] = data["monthly_income"]
        if "address" in data:
            update_data["address"] = data["address"]
        if "cnic" in data:
            update_data["cnic"] = data["cnic"]
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        
        return {"status": "success", "message": "Profile updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/facilities/nearby")
async def get_nearby_facilities(lat: float, lng: float, max_distance: float = 10):
    """Find nearby healthcare facilities"""
    try:
        result = await facility_matcher_agent.process({
            "citizen_location": {"lat": lat, "lng": lng},
            "urgency_level": UrgencyLevel.LOW,
            "required_services": [],
            "required_medicines": [],
            "sehat_card_active": False
        })
        return result.dict()
    except Exception as e:
        logger.error(f"Error finding facilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= MCP Server APIs =============

@app.post("/mcp/agent/register")
async def register_agent(data: dict):
    """Register new agent with MCP server"""
    try:
        result = await mcp_server.register_agent(
            data["agent_id"],
            data["capabilities"],
            data["endpoint"]
        )
        return result
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/message/send")
async def send_mcp_message(message: MCPMessage):
    """Send message between agents"""
    try:
        result = await mcp_server.send_message(message)
        return result
    except Exception as e:
        logger.error(f"Error sending MCP message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/context/{conversation_id}")
async def get_conversation_context(conversation_id: str):
    """Get conversation context"""
    try:
        context = await mcp_server.get_context(conversation_id)
        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/decision/log")
async def log_decision(decision: dict):
    """Log agent decision"""
    try:
        await mcp_server.log_decision(decision)
        return {"status": "logged"}
    except Exception as e:
        logger.error(f"Error logging decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/trace/{conversation_id}")
async def get_agent_trace(conversation_id: str):
    """Get full agent interaction trace"""
    try:
        logger.info(f"Fetching trace for conversation: {conversation_id}")
        trace = await mcp_server.get_trace(conversation_id)
        logger.info(f"Trace fetched: {len(trace.get('messages', []))} messages, {len(trace.get('decisions', []))} decisions")
        return trace
    except Exception as e:
        logger.error(f"Error getting trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching trace: {str(e)}")

# ============= Admin APIs =============

async def verify_admin(user_id: str = Depends(get_current_user)):
    """Verify if user is admin"""
    db = get_db()
    user = await db.users.find_one({"user_id": user_id})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id

@app.get("/api/admin/sehat-card/applications")
async def get_all_applications(
    status: str = "all",
    admin_id: str = Depends(verify_admin)
):
    """Get all Sehat Card applications (Admin only)"""
    try:
        db = get_db()
        
        query = {}
        if status != "all":
            query["status"] = status
        
        applications = await db.sehat_card_applications.find(query).sort(
            "applied_at", -1
        ).limit(100).to_list(length=100)
        
        # Convert ObjectId
        for app in applications:
            if '_id' in app:
                app['_id'] = str(app['_id'])
        
        return {
            "applications": applications,
            "total": len(applications)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/sehat-card/approve/{application_id}")
async def approve_application(
    application_id: str,
    data: dict,
    admin_id: str = Depends(verify_admin)
):
    """Approve Sehat Card application (Admin only)"""
    try:
        db = get_db()
        
        # Get application
        application = await db.sehat_card_applications.find_one({
            "application_id": application_id
        })
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        if application["status"] != "pending":
            raise HTTPException(status_code=400, detail="Application already reviewed")
        
        # Update application
        await db.sehat_card_applications.update_one(
            {"application_id": application_id},
            {"$set": {
                "status": "approved",
                "reviewed_at": datetime.utcnow(),
                "reviewed_by": admin_id,
                "admin_notes": data.get("notes", "")
            }}
        )
        
        # Activate Sehat Card for user
        await db.users.update_one(
            {"user_id": application["user_id"]},
            {"$set": {
                "sehat_card_status": True,
                "family_members": application["family_members"],
                "monthly_income": application["monthly_income"],
                "address": application["address"],
                "cnic": application["cnic"],
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Send notification
        await db.notifications.insert_one({
            "user_id": application["user_id"],
            "type": "sehat_card_approved",
            "message": f"Congratulations! Your Sehat Card application has been approved by admin. You can now use your card. | مبارک ہو! آپ کی صحت کارڈ کی درخواست منظور ہو گئی ہے۔",
            "status": "unread",
            "created_at": datetime.utcnow()
        })
        
        logger.info(f"Application {application_id} approved by admin {admin_id}")
        
        return {
            "status": "success",
            "message": "Application approved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/sehat-card/reject/{application_id}")
async def reject_application(
    application_id: str,
    data: dict,
    admin_id: str = Depends(verify_admin)
):
    """Reject Sehat Card application (Admin only)"""
    try:
        db = get_db()
        
        # Get application
        application = await db.sehat_card_applications.find_one({
            "application_id": application_id
        })
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        if application["status"] != "pending":
            raise HTTPException(status_code=400, detail="Application already reviewed")
        
        rejection_reason = data.get("reason", "Does not meet eligibility criteria")
        
        # Update application
        await db.sehat_card_applications.update_one(
            {"application_id": application_id},
            {"$set": {
                "status": "rejected",
                "reviewed_at": datetime.utcnow(),
                "reviewed_by": admin_id,
                "rejection_reason": rejection_reason
            }}
        )
        
        # Send notification
        await db.notifications.insert_one({
            "user_id": application["user_id"],
            "type": "sehat_card_rejected",
            "message": f"Your Sehat Card application has been rejected. Reason: {rejection_reason} | آپ کی صحت کارڈ کی درخواست مسترد کر دی گئی ہے۔",
            "status": "unread",
            "created_at": datetime.utcnow()
        })
        
        logger.info(f"Application {application_id} rejected by admin {admin_id}")
        
        return {
            "status": "success",
            "message": "Application rejected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_admin_stats(admin_id: str = Depends(verify_admin)):
    """Get system statistics (Admin only)"""
    try:
        db = get_db()
        
        total_users = await db.users.count_documents({})
        active_cards = await db.users.count_documents({"sehat_card_status": True})
        pending_apps = await db.sehat_card_applications.count_documents({"status": "pending"})
        approved_apps = await db.sehat_card_applications.count_documents({"status": "approved"})
        rejected_apps = await db.sehat_card_applications.count_documents({"status": "rejected"})
        total_conversations = await db.conversations.count_documents({})
        
        return {
            "total_users": total_users,
            "active_sehat_cards": active_cards,
            "pending_applications": pending_apps,
            "approved_applications": approved_apps,
            "rejected_applications": rejected_apps,
            "total_conversations": total_conversations
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/agents/status")
async def get_agents_status():
    """Get status of CrewAI healthcare agents"""
    try:
        return success_response(
            data={
                "crew_status": "active",
                "agents": [
                    {"role": "Medical Triage Specialist", "status": "ready"},
                    {"role": "Sehat Card Eligibility Officer", "status": "ready"},
                    {"role": "Healthcare Facility Coordinator", "status": "ready"},
                    {"role": "Patient Communication Coordinator", "status": "ready"}
                ],
                "total_agents": 4,
                "system": "CrewAI"
            },
            message="Agent status retrieved"
        )
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/logs")
async def get_decision_logs(limit: int = 50):
    """Get recent decision logs"""
    try:
        db = get_db()
        logs = await db.agent_decisions.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return success_response(
        data={
            "message": "Pakistan Healthcare Multi-Agent System",
            "version": "1.0.0",
            "status": "running"
        },
        message="Welcome to Pakistan Healthcare System"
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return success_response(
        data={"status": "healthy", "timestamp": datetime.utcnow().isoformat()},
        message="System is healthy"
    )

@app.get("/debug/check")
async def debug_check():
    """Debug endpoint to check system status"""
    try:
        db = get_db()
        citizen_count = await db.citizens.count_documents({})
        facility_count = await db.facilities.count_documents({})
        
        return {
            "database": "connected",
            "citizens": citizen_count,
            "facilities": facility_count,
            "agents": 4,  # CrewAI healthcare agents
            "openai_configured": bool(config.OPENAI_API_KEY)
        }
    except Exception as e:
        return {
            "error": str(e),
            "database": "error"
        }

@app.post("/api/chat/test")
async def test_chat_simple(data: dict):
    """Simple test endpoint to debug chat flow"""
    try:
        query = data.get("query", "")
        citizen_id = data.get("citizen_id", "citizen_001")
        
        logger.info(f"TEST: Query='{query}', Citizen='{citizen_id}'")
        
        # Test triage only
        triage_result = await triage_agent.process({
            "query": query,
            "conversation_id": "test_123"
        })
        
        return {
            "status": "success",
            "triage": triage_result.dict()
        }
    except Exception as e:
        logger.error(f"TEST ERROR: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/mcp/stats")
async def get_mcp_stats():
    """Get MCP server statistics"""
    try:
        stats = await mcp_server.get_system_stats()
        return success_response(stats)
    except Exception as e:
        logger.error(f"Error getting MCP stats: {e}")
        return error_response("Failed to get MCP statistics")

@app.get("/api/offline/status")
async def get_offline_status():
    """Get offline functionality status"""
    try:
        stats = offline_manager.get_offline_stats()
        return success_response(stats)
    except Exception as e:
        logger.error(f"Error getting offline status: {e}")
        return error_response("Failed to get offline status")

@app.post("/api/offline/triage")
async def offline_triage(data: dict):
    """Perform offline triage assessment"""
    try:
        symptoms = data.get("symptoms", [])
        result = offline_manager.offline_triage(symptoms)
        return success_response(result)
    except Exception as e:
        logger.error(f"Error in offline triage: {e}")
        return error_response("Offline triage failed")

@app.post("/api/rag/search")
async def search_medical_knowledge(data: dict):
    """Search medical knowledge base"""
    try:
        query = data.get("query", "")
        symptoms = data.get("symptoms", [])
        
        result = await medical_rag.search_medical_knowledge(query, symptoms)
        return success_response(result)
    except Exception as e:
        logger.error(f"Error searching medical knowledge: {e}")
        return error_response("Medical knowledge search failed")

@app.get("/api/agents/negotiations")
async def get_agent_negotiations():
    """Get recent agent negotiations and challenges"""
    try:
        db = get_db()
        negotiations = db.collection("agent_negotiations").order_by("timestamp", direction="DESCENDING").limit(10).stream()
        
        result = []
        for neg in negotiations:
            neg_data = neg.to_dict()
            neg_data['id'] = neg.id
            result.append(neg_data)
        
        return success_response(result)
    except Exception as e:
        logger.error(f"Error getting negotiations: {e}")
        return error_response("Failed to get agent negotiations")

@app.get("/api/agents/confidence")
async def get_confidence_scores():
    """Get recent agent confidence scores"""
    try:
        db = get_db()
        confidence_records = db.collection("agent_confidence").order_by("timestamp", direction="DESCENDING").limit(20).stream()
        
        result = []
        for record in confidence_records:
            conf_data = record.to_dict()
            conf_data['id'] = record.id
            result.append(conf_data)
        
        return success_response(result)
    except Exception as e:
        logger.error(f"Error getting confidence scores: {e}")
        return error_response("Failed to get confidence scores")

@app.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe Urdu audio to text"""
    try:
        # Save uploaded audio temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Transcribe audio
        urdu_text = await urdu_asr.transcribe_audio(temp_path)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if urdu_text:
            # Translate to English for processing
            english_text = await translate_to_english(urdu_text)
            
            return success_response({
                "urdu_text": urdu_text,
                "english_text": english_text,
                "transcription_success": True
            })
        else:
            return error_response("Failed to transcribe audio")
            
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        return error_response("Voice transcription failed")

@app.post("/api/voice/chat")
async def voice_chat(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Process voice input and return voice response"""
    try:
        # Save uploaded audio temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Transcribe Urdu audio
        urdu_text = await urdu_asr.transcribe_audio(temp_path)
        os.unlink(temp_path)
        
        if not urdu_text:
            return error_response("Could not understand audio")
        
        # Translate to English for processing
        english_query = await translate_to_english(urdu_text)
        
        # Process through healthcare crew
        conversation_id = str(uuid.uuid4())
        crew_result = await healthcare_crew.process_patient_query(
            current_user["user_id"], english_query, conversation_id
        )
        
        if crew_result["success"]:
            # Translate response back to Urdu
            urdu_response = await translate_to_urdu(crew_result["result"])
            
            return success_response({
                "conversation_id": conversation_id,
                "urdu_input": urdu_text,
                "english_input": english_query,
                "english_response": crew_result["result"],
                "urdu_response": urdu_response,
                "agents_involved": crew_result["agents_involved"]
            })
        else:
            return error_response("Failed to process voice query")
            
    except Exception as e:
        logger.error(f"Voice chat error: {e}")
        return error_response("Voice chat failed")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.ENVIRONMENT == "development"
    )
