"""
Authentication and authorization utilities
"""

import re
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from config.config import config

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < config.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long"
    
    if config.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if config.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if config.PASSWORD_REQUIRE_NUMBERS and not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Security scheme
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    name: str

class TokenData(BaseModel):
    user_id: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    phone: str
    password: str
    location: dict = {"lat": 24.8607, "lng": 67.0011}

class UserLogin(BaseModel):
    phone: str
    password: str

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verify a password - simple comparison"""
    return plain_password == stored_password

def get_password_hash(password: str) -> str:
    """Return password as-is (no hashing for demo)"""
    return password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        return TokenData(user_id=user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token"""
    token = credentials.credentials
    token_data = decode_token(token)
    return token_data.user_id
