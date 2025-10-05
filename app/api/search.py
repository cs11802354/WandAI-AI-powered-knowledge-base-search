"""
Search API endpoints.
Provides semantic search capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.api.schemas import SearchRequest, SearchResponse, SearchResult
from app.services.search_service import semantic_search

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search across all documents.
    
    Example:
    POST /api/v1/search
    {
        "query": "How does authentication work?",
        "top_k": 10
    }
    
    Returns relevant chunks ranked by similarity.
    """
    # Perform semantic search
    results = await semantic_search(db, request.query, request.top_k)
    
    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results)
    )
