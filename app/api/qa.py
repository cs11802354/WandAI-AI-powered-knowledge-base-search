"""
Q&A API endpoints.
Provides question-answering using RAG.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.api.schemas import QARequest, QAResponse
from app.services.qa_service import answer_question

router = APIRouter(prefix="/api/v1", tags=["qa"])


@router.post("/qa", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question and get an answer based on knowledge base.
    
    Uses RAG (Retrieval-Augmented Generation):
    1. Searches for relevant content
    2. Sends to LLM with context
    3. Returns answer with sources
    
    Example:
    POST /api/v1/qa
    {
        "question": "What are the API rate limits?",
        "top_k": 5
    }
    """
    result = await answer_question(db, request.question, request.top_k)
    
    return QAResponse(**result)
