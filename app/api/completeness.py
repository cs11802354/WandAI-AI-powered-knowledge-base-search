"""
Completeness checking API endpoints.
Analyzes knowledge base coverage.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.api.schemas import CompletenessRequest, CompletenessResponse
from app.services.completeness_service import check_completeness

router = APIRouter(prefix="/api/v1", tags=["completeness"])


@router.post("/completeness-check", response_model=CompletenessResponse)
async def check_documentation_completeness(
    request: CompletenessRequest,
    db: Session = Depends(get_db)
):
    """
    Check if knowledge base covers all required topics.
    
    Example:
    POST /api/v1/completeness-check
    {
        "requirements": [
            "authentication",
            "payment processing",
            "user management",
            "API documentation"
        ]
    }
    
    Returns:
    - Completeness percentage
    - Which topics are covered
    - Which topics are missing (gaps)
    - Detailed analysis for each topic
    """
    result = await check_completeness(db, request.requirements)
    
    return CompletenessResponse(**result)
