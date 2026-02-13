"""Main application entry point for Dual Agent Chat Platform."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Dual Agent Chat Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and service availability.
    Will be fully implemented in Task 20.
    """
    return {
        "status": "ok",
        "message": "Service is running"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
