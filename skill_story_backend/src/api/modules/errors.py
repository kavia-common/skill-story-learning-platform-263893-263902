from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTH_ERROR"
    AUTHORIZATION_ERROR = "AUTHZ_ERROR"
    RESOURCE_NOT_FOUND = "NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApplicationError(Exception):
    """Base application exception with code and HTTP status."""

    def __init__(self, message: str, error_code: ErrorCode, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


def success(data: Any):
    """Return a success envelope."""
    return {"success": True, "data": data}
