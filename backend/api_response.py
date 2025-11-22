"""
Standardized API response formats
"""
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime

class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = datetime.utcnow()
    version: str = "v1"

class PaginatedResponse(BaseModel):
    """Standard paginated response format"""
    success: bool
    message: str
    data: List[Any]
    pagination: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    version: str = "v1"

class ErrorResponse(BaseModel):
    """Standard error response format"""
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    version: str = "v1"

def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    return APIResponse(
        success=True,
        message=message,
        data=data
    ).dict()

def error_response(error: str, details: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    return ErrorResponse(
        error=error,
        details=details
    ).dict()

def paginated_response(
    data: List[Any], 
    page: int = 1, 
    limit: int = 10, 
    total: int = 0,
    message: str = "Success"
) -> Dict[str, Any]:
    """Create standardized paginated response"""
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    ).dict()
