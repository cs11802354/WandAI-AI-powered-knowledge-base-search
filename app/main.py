"""
Main FastAPI application.
Brings together all API routers and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents, search, qa, completeness, tasks, health
from app.models.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="AI-Powered Knowledge Base",
    description="Semantic search and Q&A over documents",
    version="1.0.0"
)

# Add CORS middleware (allows frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(qa.router)
app.include_router(completeness.router)
app.include_router(tasks.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "AI-Powered Knowledge Base API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /api/v1/documents/upload",
            "search": "POST /api/v1/search",
            "qa": "POST /api/v1/qa",
            "completeness": "POST /api/v1/completeness-check",
            "task_status": "GET /api/v1/tasks/{task_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
