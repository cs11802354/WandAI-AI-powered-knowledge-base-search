"""
Pydantic schemas for API request/response validation.
These define the "shape" of data going in and out of APIs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Upload responses
class UploadResponse(BaseModel):
    """Response when a document is uploaded."""
    status: str
    message: str
    document_id: Optional[int] = None
    task_id: Optional[str] = None


# Search schemas
class SearchRequest(BaseModel):
    """Request body for semantic search."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, description="Number of results to return", ge=1, le=100)


class SearchResult(BaseModel):
    """Single search result with conflict resolution metadata."""
    chunk_id: int
    text: str
    chunk_index: int
    document_id: int
    filename: str
    uploaded_at: Optional[str]
    created_at: Optional[str] = None
    similarity: float
    recency_score: Optional[float] = 0.5
    hybrid_score: Optional[float] = None
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    """Response from semantic search."""
    query: str
    results: List[SearchResult]
    total_results: int


# Q&A schemas
class QARequest(BaseModel):
    """Request body for Q&A."""
    question: str = Field(..., description="Question to answer")
    top_k: int = Field(5, description="Number of context chunks to use", ge=1, le=20)


class Source(BaseModel):
    """Source document for Q&A answer."""
    filename: str
    text: str
    similarity: float


class QAResponse(BaseModel):
    """Response from Q&A with provider info."""
    question: str
    answer: str
    sources: List[Source]
    provider: Optional[str] = None


# Completeness check schemas
class CompletenessRequest(BaseModel):
    """Request body for completeness check."""
    requirements: List[str] = Field(..., description="List of required topics to check")


class RequirementAnalysis(BaseModel):
    """Analysis of a single requirement."""
    requirement: str
    covered: bool
    confidence: float
    summary: str
    sources: List[dict]


class CompletenessResponse(BaseModel):
    """Response from completeness check."""
    completeness_percentage: float
    total_requirements: int
    covered_count: int
    gaps: List[str]
    detailed_analysis: List[RequirementAnalysis]


# Task status schemas
class TaskStatus(BaseModel):
    """Status of a background task."""
    task_id: str
    status: str
    progress: Optional[dict] = None
    result: Optional[dict] = None


# Document list schemas
class DocumentInfo(BaseModel):
    """Basic document information."""
    id: int
    filename: str
    file_size: int
    uploaded_at: datetime
    chunk_count: int
    
    class Config:
        from_attributes = True
