"""
Health check endpoints for monitoring system status.
Shows AI provider status and overall system health.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.services import embedding_service, qa_service
from app.config import get_settings
import time

router = APIRouter(prefix="/api/v1", tags=["health"])
settings = get_settings()


@router.get("/health/providers")
async def check_providers():
    """
    Check health of all AI providers.
    
    Returns status of:
    - Embedding provider
    - Completion provider
    - Overall system health
    """
    start_time = time.time()
    
    # Check embedding provider
    embedding_health = await embedding_service.health_check()
    
    # Check completion provider (Q&A)
    completion_health = await qa_service.health_check()
    
    # Overall status
    all_healthy = (
        embedding_health.get("status") in ["healthy", "degraded"] and
        completion_health.get("status") in ["healthy", "degraded"]
    )
    
    elapsed_time = time.time() - start_time
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": time.time(),
        "response_time_ms": round(elapsed_time * 1000, 2),
        "configuration": {
            "ai_provider": settings.ai_provider,
            "embedding_model": settings.embedding_model,
            "llm_model": settings.llm_model
        },
        "providers": {
            "embedding": embedding_health,
            "completion": completion_health
        }
    }


@router.get("/health/detailed")
async def detailed_health(db: Session = Depends(get_db)):
    """
    Detailed health check including database and all services.
    
    Checks:
    - Database connectivity
    - AI providers
    - Configuration
    """
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    
    # Check database
    try:
        # Simple query to verify DB connection
        db.execute("SELECT 1")
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check AI providers
    try:
        provider_health = await check_providers()
        health_status["checks"]["ai_providers"] = provider_health
        
        if provider_health["status"] != "healthy":
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["ai_providers"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check pgvector extension
    try:
        result = db.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if result.fetchone():
            health_status["checks"]["pgvector"] = {
                "status": "healthy",
                "message": "pgvector extension installed"
            }
        else:
            health_status["status"] = "degraded"
            health_status["checks"]["pgvector"] = {
                "status": "warning",
                "message": "pgvector extension not found"
            }
    except Exception as e:
        health_status["checks"]["pgvector"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    return health_status


@router.get("/health/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get system metrics and statistics.
    
    Returns:
    - Document count
    - Chunk count
    - Provider information
    """
    try:
        # Count documents
        doc_count = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        
        # Count chunks
        chunk_count = db.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
        
        # Get provider info
        provider_name = embedding_service.get_provider_name()
        embedding_dim = embedding_service.get_embedding_dimension()
        
        return {
            "status": "success",
            "metrics": {
                "documents": {
                    "total": doc_count
                },
                "chunks": {
                    "total": chunk_count
                },
                "provider": {
                    "name": provider_name,
                    "embedding_dimension": embedding_dim
                },
                "configuration": {
                    "ai_provider": settings.ai_provider,
                    "chunk_size": settings.chunk_size,
                    "chunk_overlap": settings.chunk_overlap
                }
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }