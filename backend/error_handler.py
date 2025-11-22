"""
Standardized error handling utilities
"""
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class StandardError:
    """Standard error response format"""
    
    @staticmethod
    def database_error(operation: str, details: str = None) -> HTTPException:
        """Standard database error"""
        logger.error(f"Database error in {operation}: {details}")
        return HTTPException(
            status_code=500,
            detail=f"Database operation failed: {operation}"
        )
    
    @staticmethod
    def validation_error(field: str, message: str) -> HTTPException:
        """Standard validation error"""
        logger.warning(f"Validation error - {field}: {message}")
        return HTTPException(
            status_code=400,
            detail=f"Validation failed for {field}: {message}"
        )
    
    @staticmethod
    def not_found_error(resource: str, identifier: str = None) -> HTTPException:
        """Standard not found error"""
        detail = f"{resource} not found"
        if identifier:
            detail += f" (ID: {identifier})"
        logger.warning(detail)
        return HTTPException(status_code=404, detail=detail)
    
    @staticmethod
    def auth_error(message: str = "Authentication required") -> HTTPException:
        """Standard authentication error"""
        logger.warning(f"Auth error: {message}")
        return HTTPException(status_code=401, detail=message)
    
    @staticmethod
    def permission_error(action: str = "access this resource") -> HTTPException:
        """Standard permission error"""
        logger.warning(f"Permission denied: {action}")
        return HTTPException(status_code=403, detail=f"Permission denied to {action}")
    
    @staticmethod
    def agent_error(agent_name: str, operation: str, details: str = None) -> Dict[str, Any]:
        """Standard agent error response (returns dict, not exception)"""
        error_msg = f"Agent {agent_name} failed: {operation}"
        if details:
            error_msg += f" - {details}"
        logger.error(error_msg)
        return {
            "error": True,
            "agent": agent_name,
            "operation": operation,
            "message": error_msg,
            "details": details
        }

def safe_execute(func, *args, default_return=None, log_errors=True, **kwargs):
    """Safely execute a function with consistent error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return default_return

async def safe_execute_async(func, *args, default_return=None, log_errors=True, **kwargs):
    """Safely execute an async function with consistent error handling"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return default_return
