"""Global error handlers for the Dual Agent Chat Platform."""
import logging
import traceback
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from api.exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    LLMServiceError
)
from utils.logging_config import log_error_with_context

# Configure logging
logger = logging.getLogger(__name__)


def create_error_response(
    error: str,
    detail: str,
    status_code: int
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error: Error type/category
        detail: Detailed error message
        status_code: HTTP status code
    
    Returns:
        JSONResponse with standardized error format
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


async def authentication_error_handler(
    request: Request,
    exc: AuthenticationError
) -> JSONResponse:
    """
    Handle AuthenticationError exceptions.
    
    Returns 401 Unauthorized with error details.
    """
    log_error_with_context(
        logger,
        exc,
        {
            "error_type": "authentication",
            "path": str(request.url),
            "method": request.method
        },
        "Authentication failed"
    )
    
    return create_error_response(
        error="Authentication failed",
        detail=str(exc.message),
        status_code=status.HTTP_401_UNAUTHORIZED
    )


async def validation_error_handler(
    request: Request,
    exc: ValidationError
) -> JSONResponse:
    """
    Handle ValidationError exceptions.
    
    Returns 400 Bad Request with error details.
    """
    return create_error_response(
        error="Validation failed",
        detail=str(exc.message),
        status_code=status.HTTP_400_BAD_REQUEST
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI RequestValidationError exceptions.
    
    Returns 422 Unprocessable Entity with validation error details.
    """
    # Extract validation error details
    errors = exc.errors()
    detail = "; ".join([
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
        for err in errors
    ])
    
    return create_error_response(
        error="Validation failed",
        detail=detail,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: PydanticValidationError
) -> JSONResponse:
    """
    Handle Pydantic ValidationError exceptions.
    
    Returns 400 Bad Request with validation error details.
    """
    return create_error_response(
        error="Validation failed",
        detail=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST
    )


async def not_found_error_handler(
    request: Request,
    exc: NotFoundError
) -> JSONResponse:
    """
    Handle NotFoundError exceptions.
    
    Returns 404 Not Found with error details.
    """
    return create_error_response(
        error="Resource not found",
        detail=str(exc.message),
        status_code=status.HTTP_404_NOT_FOUND
    )


async def llm_service_error_handler(
    request: Request,
    exc: LLMServiceError
) -> JSONResponse:
    """
    Handle LLMServiceError exceptions.
    
    Returns 503 Service Unavailable with error details.
    """
    log_error_with_context(
        logger,
        exc,
        {
            "error_type": "llm_service",
            "path": str(request.url),
            "method": request.method
        },
        "LLM service unavailable"
    )
    
    return create_error_response(
        error="LLM service unavailable",
        detail=str(exc.message),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle all other unhandled exceptions.
    
    Returns 500 Internal Server Error with generic error message.
    """
    # Log the full exception with structured logging
    log_error_with_context(
        logger,
        exc,
        {
            "error_type": "unhandled_exception",
            "path": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        "Unhandled exception occurred"
    )
    
    return create_error_response(
        error="Internal server error",
        detail="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
