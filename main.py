"""Main application entry point for Dual Agent Chat Platform."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import ValidationError as PydanticValidationError

from config.settings import settings
from utils.logging_config import setup_logging

# Initialize structured logging
setup_logging(log_level="INFO")
from api.routes import router as api_router
from api.exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    LLMServiceError
)
from api.error_handlers import (
    authentication_error_handler,
    validation_error_handler,
    request_validation_error_handler,
    pydantic_validation_error_handler,
    not_found_error_handler,
    llm_service_error_handler,
    generic_exception_handler
)

# Create FastAPI application
app = FastAPI(
    title="Dual Agent Chat Platform",
    description="A lightweight AI collaboration discussion system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers
app.add_exception_handler(AuthenticationError, authentication_error_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)
app.add_exception_handler(NotFoundError, not_found_error_handler)
app.add_exception_handler(LLMServiceError, llm_service_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API routes
app.include_router(api_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Root endpoint - serve monitoring interface."""
    return FileResponse("frontend/monitor.html")


@app.get("/monitor.html")
async def monitor():
    """Serve monitoring interface (no authentication required)."""
    return FileResponse("frontend/monitor.html")


@app.get("/index.html")
async def index():
    """Serve chat interface (requires authentication)."""
    return FileResponse("frontend/index.html")


@app.get("/admin.html")
async def admin():
    """Serve admin interface."""
    return FileResponse("frontend/admin.html")


@app.get("/auth-info.html")
async def auth_info():
    """Serve authentication information page."""
    return FileResponse("frontend/auth-info.html")


@app.get("/api-docs")
async def api_docs():
    """Serve API documentation page."""
    return FileResponse("static/api-docs.html")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
