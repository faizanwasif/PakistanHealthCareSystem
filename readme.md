# Pakistan Healthcare Multi-Agent System - Complete Documentation

## 🏗️ **System Architecture**

### **Core Components**
- **Backend**: FastAPI-based REST API with CrewAI multi-agent system
- **Frontend**: HTML/CSS/JavaScript web interface  
- **Database**: Firebase Firestore (NoSQL)
- **AI Engine**: Google Gemini Pro (via CrewAI framework)
- **Maps Integration**: Google Maps MCP Server
- **Authentication**: JWT-based auth system with bcrypt password hashing
- **Multi-Agent Framework**: CrewAI with autonomous agent collaboration

---

## 📁 **File Structure & Modules**

### **🔧 Configuration Files**
| File | Path | Purpose |
|------|------|---------|
| Environment Config | `config/config.py` | API keys, database URLs, agent settings |
| Firebase Credentials | `config/firebase-credentials.json` | Firebase service account key |
| Firebase Config | `config/firebase.json` | Firebase project configuration |
| Dependencies | `requirements.txt` | Python package dependencies |
| Docker Config | `config/Dockerfile` | Container deployment configuration |

### **🤖 CrewAI Multi-Agent System**
| Agent | Path | Role & Capabilities |
|-------|------|-------------|
| **Medical Triage Specialist** | `agents/healthcare_crew.py` | Symptom analysis, urgency assessment (high/medium/low), medical triage with Pakistani healthcare protocols |
| **Sehat Card Eligibility Officer** | `agents/healthcare_crew.py` | Government health program verification, Sehat Card criteria checking, benefits assessment |
| **Healthcare Facility Coordinator** | `agents/healthcare_crew.py` | Hospital/BHU search, Google Maps integration, medicine availability, distance calculation |
| **Patient Communication Coordinator** | `agents/healthcare_crew.py` | SMS notifications, follow-up scheduling, patient alerts, multi-language support |
| **Base Agent Framework** | `agents/base_agent.py` | Core agent functionality, Gemini integration, decision logging |
| **Legacy Individual Agents** | `agents/triage_agent.py`, `agents/eligibility_agent.py`, etc. | Individual agent implementations (superseded by CrewAI) |

### **🔙 Backend Services**
| Service | Path | Features |
|---------|------|----------|
| **Main API** | `backend/main.py` | FastAPI app, REST endpoints, WebSocket support, CrewAI integration |
| **Database Layer** | `backend/database.py` | Firebase Firestore integration, async operations, connection pooling |
| **Authentication** | `backend/auth.py` | JWT tokens, user registration/login, bcrypt password hashing, role-based access |
| **Data Models** | `backend/models.py` | Pydantic models, enums (UrgencyLevel, MessageStatus), validation schemas |
| **MCP Server** | `backend/mcp_server.py` | Multi-agent communication protocol, message routing |
| **MCP Client** | `backend/mcp_client.py` | Google Maps MCP server integration, location services |
| **Location Service** | `backend/location_service.py` | Geolocation utilities, distance calculations |
| **Error Handler** | `backend/error_handler.py` | Centralized error handling, logging, safe execution wrappers |
| **API Response** | `backend/api_response.py` | Standardized response formats, success/error responses |
| **Database Seeder** | `backend/seed_database.py` | Initial data population, test data generation |

### **🎨 Frontend Interface**
| Component | Path | Features |
|-----------|------|----------|
| **Main App** | `frontend/index.html` | Dashboard, chat interface, user profile |
| **Login Page** | `frontend/login.html` | User authentication, registration |
| **Admin Panel** | `frontend/admin.html` | System management, user oversight |
| **Debug Console** | `frontend/debug.html` | System diagnostics, agent tracing |
| **Main Logic** | `frontend/app.js` | Chat functionality, API calls, UI interactions |
| **Location Helper** | `frontend/location_helper.js` | Geolocation services, map integration |
| **Styling** | `frontend/style.css` | UI design, responsive layout, themes |

### **🚀 Deployment & Setup Scripts**
| Script | Path | Purpose |
|--------|------|---------|
| **Main Launcher** | `start.sh` | Complete system startup with venv, dependencies, MCP server (Linux/Mac) |
| **Windows Launcher** | `run.bat` | System startup for Windows |
| **Simple Runner** | `run.sh` | Basic server startup without full setup |
| **Maps Setup** | `setup-maps.sh` | Google Maps MCP server installation |
| **Firebase Indexes** | `setup_firebase_indexes.py` | Firebase composite index creation URLs |

---

## 🔥 **Core Features**

## 🔥 **Core Features**

### **1. 💬 CrewAI-Powered Healthcare Chatbot**
- **Location**: `agents/healthcare_crew.py`, `backend/main.py` (chat endpoint), `frontend/app.js`
- **Features**:
  - Multi-agent collaboration with CrewAI framework
  - Sequential task processing with agent memory
  - Natural language processing in English/Urdu
  - Autonomous agent decision-making and delegation
  - Context-aware conversation handling
  - Real-time agent interaction tracing

### **2. 🏥 Hospital & Facility Search**
- **Location**: `agents/facility_matcher_agent.py`, `backend/mcp_client.py`
- **Features**:
  - Real-time Google Maps integration
  - Distance-based hospital search
  - Service availability checking
  - Medicine inventory tracking
  - Sehat Card accepted facilities

### **3. 🔐 User Authentication System**
- **Location**: `backend/auth.py`, `frontend/login.html`
- **Features**:
  - JWT-based secure authentication
  - User registration and login
  - Password hashing with bcrypt
  - Session management
  - Role-based access control

### **4. 💳 Sehat Card Management**
- **Location**: `backend/main.py` (Sehat Card endpoints), `agents/eligibility_agent.py`
- **Features**:
  - Digital Sehat Card application
  - Eligibility verification
  - Program enrollment
  - Status tracking
  - Admin approval workflow

### **5. 📱 Notification System**
- **Location**: `agents/notification_agent.py`, `backend/main.py`
- **Features**:
  - SMS notifications
  - In-app alerts
  - Follow-up reminders
  - Emergency notifications
  - Multi-language support

### **6. 👨‍💼 Admin Dashboard**
- **Location**: `frontend/admin.html`, `backend/main.py` (admin endpoints)
- **Features**:
  - User management
  - Application approvals
  - System statistics
  - Agent monitoring
  - Decision logs review

### **7. 🗺️ Location Services**
- **Location**: `backend/location_service.py`, `frontend/location_helper.js`
- **Features**:
  - GPS location detection
  - Address geocoding
  - Distance calculations
  - Map integration
  - Location-based recommendations

### **8. 🔍 Agent Tracing & Debugging**
- **Location**: `frontend/debug.html`, `backend/mcp_server.py`
- **Features**:
  - Real-time agent interactions
  - Decision reasoning logs
  - Conversation tracing
  - Performance monitoring
  - Error diagnostics

---

## 🔌 **API Endpoints**

### **Authentication APIs**
- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/history` - Get conversation history

### **Chat & Health APIs**
- `POST /api/chat/message` - Process health queries
- `GET /api/citizen/eligibility` - Check program eligibility
- `GET /api/facilities/nearby` - Find nearby hospitals

### **Sehat Card APIs**
- `POST /api/sehat-card/apply` - Apply for Sehat Card
- `GET /api/sehat-card/status` - Check application status
- `PUT /api/sehat-card/update-profile` - Update user profile

### **Admin APIs**
- `GET /api/admin/applications` - Get all applications
- `POST /api/admin/applications/{id}/approve` - Approve application
- `POST /api/admin/applications/{id}/reject` - Reject application
- `GET /api/admin/stats` - Get system statistics

### **System APIs**
- `GET /health` - System health check
- `GET /api/admin/agents/status` - Agent status
- `GET /api/notifications` - Get user notifications
- `POST /api/notifications/mark-read` - Mark notifications read

---

## 🛠️ **Technology Stack**

## 🛠️ **Technology Stack**

### **Backend Technologies**
- **FastAPI**: Modern Python web framework with async support
- **CrewAI**: Multi-agent AI framework for autonomous collaboration
- **Uvicorn**: ASGI server for production deployment
- **Firebase Firestore**: NoSQL database with real-time sync
- **Google Gemini Pro**: Advanced AI language model
- **LangChain Google GenAI**: LLM integration layer
- **JWT + bcrypt**: Secure authentication and password hashing
- **Pydantic**: Data validation and serialization
- **AsyncIO**: Asynchronous programming support

### **Frontend Technologies**
- **HTML5**: Modern web markup
- **CSS3**: Responsive styling
- **Vanilla JavaScript**: No framework dependencies
- **Fetch API**: HTTP requests
- **WebSocket**: Real-time communication

### **External Integrations**
- **Google Maps API**: Location services and facility search
- **Google Maps MCP Server**: Hospital search with real-time data
- **Firebase Admin SDK**: Database operations and authentication
- **SMS Gateway**: Notification delivery (configurable)
- **CrewAI Tools**: Database queries and notification tools

---

## 🚀 **Deployment & Setup**

### **Quick Start**
1. Run `./start.sh` (Linux/Mac) or `run.bat` (Windows)
2. Configure `.env` file with API keys
3. Set up Firebase credentials
4. Access at `http://localhost:8000`

### **Requirements**
- Python 3.8+ (tested with 3.12)
- Node.js (for Google Maps MCP server)
- Firebase project with Firestore enabled
- Google Maps API key with Places API enabled
- Gemini API key from Google AI Studio
- Virtual environment (venv) support

### **Environment Variables**
```env
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com/
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
MCP_GOOGLE_MAPS_URL=http://localhost:3000/mcp
JWT_SECRET=your_jwt_secret_key
ENVIRONMENT=development
LOG_LEVEL=INFO
SMS_GATEWAY_KEY=your_sms_gateway_key
```

---

## 📊 **Database Collections**

### **Firebase Firestore Collections**
- `users` - User accounts, profiles, and authentication data
- `citizens` - Legacy citizen data (maintained for compatibility)
- `facilities` - Healthcare facilities, BHUs, hospitals with services
- `conversations` - Chat history with agent interactions
- `notifications` - User notifications and alerts
- `sehat_card_applications` - Sehat Card applications and status
- `agent_decisions` - AI decision logs with reasoning
- `follow_ups` - Follow-up reminders and scheduling
- `mcp_messages` - Inter-agent communications (CrewAI)

### **Required Firebase Indexes**
- `notifications`: (user_id, created_at)
- `conversations`: (citizen_id, created_at)  
- `sehat_card_applications`: (user_id, applied_at)

**Setup**: Run `python3 setup_firebase_indexes.py` to create indexes

---

## 🔧 **Configuration Options**

### **Agent Configuration** (`config/config.py`)
- `AGENT_TEMPERATURE`: AI creativity level (0.4)
- `AGENT_MAX_TOKENS`: Response length limit (500)
- `AGENT_MODEL`: AI model name (gemini-2.5-flash)

### **Security Configuration**
- `PASSWORD_MIN_LENGTH`: Minimum password length (8)
- `PASSWORD_REQUIRE_UPPERCASE`: Require uppercase letters (True)
- `PASSWORD_REQUIRE_LOWERCASE`: Require lowercase letters (True)
- `PASSWORD_REQUIRE_NUMBERS`: Require numbers (True)
- `LOGIN_RATE_LIMIT`: Login attempts per minute (5)

### **System Configuration**
- `ENVIRONMENT`: Development/production mode
- `LOG_LEVEL`: Logging verbosity (INFO)
- `CACHE_TTL`: Cache expiration time (3600s)
- `OFFLINE_MODE_ENABLED`: Offline functionality (True)

---

## 🎯 **Key Features Summary**

✅ **CrewAI Multi-Agent System** with autonomous collaboration  
✅ **Multi-language support** (English/Urdu)  
✅ **Real-time hospital search** via Google Maps MCP  
✅ **AI-powered medical triage** with Gemini Pro  
✅ **Secure authentication** with JWT + bcrypt  
✅ **Digital Sehat Card** application system  
✅ **SMS notifications** and alerts  
✅ **Admin dashboard** for management  
✅ **Conversation history** tracking  
✅ **Agent decision** tracing and debugging  
✅ **Responsive web interface**  
✅ **Cross-platform deployment**  
✅ **Firebase composite indexes** for optimized queries  
✅ **Async database operations** with connection pooling  
✅ **Centralized error handling** and logging  

---

## 🚨 **Known Issues & Setup Requirements**

### **Critical Setup Steps**
1. **Firebase Indexes**: Run `python3 setup_firebase_indexes.py` to create required composite indexes
2. **Google Maps MCP**: Ensure Node.js is installed for MCP server
3. **API Keys**: Configure all API keys in `.env` file
4. **Firebase Credentials**: Place valid `firebase-credentials.json` in `config/` directory

### **Current Limitations**
- SMS gateway integration requires external service configuration
- Google Maps MCP server must be running on port 3000
- Firebase indexes must be manually created via console
- Some legacy agent files maintained for compatibility

---

## 🤖 **CrewAI Multi-Agent Implementation**

### **Agent Roles & Responsibilities**

#### **Medical Triage Specialist**
- **Role**: Primary medical assessment and symptom analysis
- **Capabilities**: 
  - Pakistani healthcare protocol expertise
  - Urgency level determination (high/medium/low)
  - BHU/hospital referral recommendations
  - Local medical condition knowledge
- **Tools**: Database query access for medical history

#### **Sehat Card Eligibility Officer**  
- **Role**: Government health program verification
- **Capabilities**:
  - Sehat Card criteria assessment
  - Program eligibility verification
  - Benefits calculation and explanation
  - Policy compliance checking
- **Tools**: Database access for user eligibility data

#### **Healthcare Facility Coordinator**
- **Role**: Facility search and resource matching
- **Capabilities**:
  - Hospital/BHU location services
  - Medicine availability checking
  - Service matching to patient needs
  - Distance and accessibility analysis
- **Tools**: Database queries for facility information

#### **Patient Communication Coordinator**
- **Role**: Notifications and follow-up management
- **Capabilities**:
  - SMS notification dispatch
  - Follow-up scheduling
  - Multi-language communication
  - Emergency alert handling
- **Tools**: Notification system and database access

### **Agent Collaboration Flow**
1. **Query Reception**: Patient query received by system
2. **Triage Assessment**: Medical Triage Specialist analyzes symptoms
3. **Conditional Routing**: Based on query content, additional agents activated:
   - Eligibility check for Sehat Card queries
   - Facility search for location-based queries
4. **Communication**: Patient Communication Coordinator handles notifications
5. **Memory Persistence**: All agent interactions stored for context

### **CrewAI Configuration**
- **Process**: Sequential execution with agent delegation
- **Memory**: Enabled for context retention across conversations
- **LLM**: Google Gemini Pro with temperature 0.3
- **Tools**: Custom database and notification tools
- **Verbose Mode**: Enabled for debugging and tracing

---

## 📝 **Development Notes**

### **Architecture Decisions**
- **CrewAI Framework**: Chosen for true multi-agent collaboration vs. fake MCP system
- **Firebase Firestore**: NoSQL for flexible healthcare data structures
- **FastAPI**: Modern async Python framework for high performance
- **JWT Authentication**: Stateless authentication for scalability

### **Code Organization**
- **Modular Design**: Separate concerns (auth, database, agents, API)
- **Async Operations**: Non-blocking database and API calls
- **Error Handling**: Centralized error management with logging
- **Type Safety**: Pydantic models for data validation

---

*Last Updated: November 22, 2025*  
*System Version: 2.0 (CrewAI Implementation)*  
*Documentation Status: Complete & Current*
