"""
Database models using SQLAlchemy ORM.
Enhanced to support rich metadata for conflict resolution.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, BigInteger, DateTime, ForeignKey, Index, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.config import get_settings

settings = get_settings()

# Create database engine
engine = create_engine(settings.database_url)

# Session factory (creates database connections)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


class Document(Base):
    """
    Represents a document in the knowledge base.
    Each document can have many chunks.
    Supports versioning for incremental updates.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)  # Added index for filename lookup
    content_hash = Column(String(64), nullable=False, index=True)  # Removed unique constraint
    raw_content = Column(Text)
    file_size = Column(BigInteger)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    document_metadata = Column(JSONB)
    
    # Versioning columns (NEW)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    replaced_at = Column(DateTime, nullable=True)
    
    # Relationship: one document has many chunks
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """
    Represents a chunk of text from a document with its vector embedding.
    Includes rich metadata for conflict resolution and versioning support.
    """
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Vector embedding - dimension can vary by provider
    embedding = Column(Vector(1536))  # Default OpenAI dimension
    
    # Metadata for conflict resolution
    document_metadata = Column(JSONB)  # Stores: entities, data_types, temporal_info, recency_score, etc.
    
    # Recency score as separate column for faster queries
    recency_score = Column(Float, default=0.5, index=True)  # 0.0-1.0, higher = more recent
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Versioning columns (NEW)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    replaced_at = Column(DateTime, nullable=True)
    
    # Relationship: chunk belongs to one document
    document = relationship("Document", back_populates="chunks")
    
    # Indexes for faster metadata queries
    __table_args__ = (
        # Index for JSONB metadata queries (PostgreSQL GIN index)
        Index('ix_document_chunks_metadata', 'document_metadata', postgresql_using='gin'),
        Index('ix_document_chunks_active_doc', 'is_active', 'document_id'),  # For active chunk queries
    )


# Database helper functions
def get_db():
    """
    Creates a database session.
    Use with 'with' statement to auto-close connection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()