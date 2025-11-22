import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "config/firebase-credentials.json")
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    MCP_GOOGLE_MAPS_URL = os.getenv("MCP_GOOGLE_MAPS_URL", "http://localhost:3000/mcp")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # Generate secure JWT secret if not provided
    _jwt_secret = os.getenv("JWT_SECRET")
    if not _jwt_secret or _jwt_secret == "change-this-secret":
        _jwt_secret = secrets.token_urlsafe(32)
        print("⚠️  WARNING: Using auto-generated JWT secret. Set JWT_SECRET in .env for production!")
    JWT_SECRET = _jwt_secret
    
    SMS_GATEWAY_KEY = os.getenv("SMS_GATEWAY_KEY")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Security Configuration
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    LOGIN_RATE_LIMIT = 5  # attempts per minute
    
    # Agent Configuration
    AGENT_TEMPERATURE = 0.4
    AGENT_MAX_TOKENS = 500
    AGENT_MODEL = "gemini-2.5-flash"
    
    # Cache Configuration
    CACHE_TTL = 3600  # 1 hour
    OFFLINE_MODE_ENABLED = True

config = Config()
