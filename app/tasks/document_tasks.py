"""
Celery tasks for document processing.
These run in the background so API responds quickly.
Now with enhanced chunking and metadata extraction.
"""

from celery import Task
from app.celery_app import celery_app
from app.models.database import SessionLocal, Document, DocumentChunk
from app.services.file_service import extract_text
from app.services.chunking_service import chunk_text_enhanced
from app.services.embedding_service import generate_embeddings_batch
from app.services.search_service import clear_search_cache
import os
import asyncio
import logging
import traceback

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Helper function to run async functions in Celery tasks.
    Celery doesn't natively support async, so we need this wrapper.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


class DatabaseTask(Task):
    """
    Base task that provides database session.
    """
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
def process_document(self, document_id: int, file_path: str, filename: str):
    """
    Main document processing task with enhanced chunking.
    
    Steps:
    1. Extract text from file
    2. Split into chunks WITH metadata
    3. Generate embeddings
    4. Save to database with metadata
    
    Args:
        document_id: Database ID of document
        file_path: Path to uploaded file
        filename: Original filename
    """
    try:
        # Update task state to show progress
        self.update_state(state='PROGRESS', meta={'step': 'extracting_text', 'progress': 10})
        
        # Step 1: Extract text
        text = extract_text(file_path, filename)
        
        # Update document with raw content
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        document.raw_content = text
        self.db.commit()
        
        self.update_state(state='PROGRESS', meta={'step': 'chunking_with_metadata', 'progress': 30})
        
        # Step 2: Enhanced chunking with metadata
        document_metadata = {
            "filename": filename,
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "document_id": document_id,
            "file_type": filename.split('.')[-1] if '.' in filename else 'unknown'
        }
        
        enhanced_chunks = chunk_text_enhanced(
            text=text,
            document_metadata=document_metadata
        )
        
        self.update_state(state='PROGRESS', meta={'step': 'generating_embeddings', 'progress': 50})
        
        # Step 3: Generate embeddings (batch for efficiency)
        chunk_texts = [chunk["text"] for chunk in enhanced_chunks]
        embeddings = run_async(generate_embeddings_batch(chunk_texts))
        
        self.update_state(state='PROGRESS', meta={'step': 'saving_to_database', 'progress': 80})
        
        # Step 4: Save chunks with embeddings AND metadata (with versioning support)
        # Get document version for chunk versioning
        document = self.db.query(Document).filter(Document.id == document_id).first()
        doc_version = document.version if document else 1
        
        for enhanced_chunk, embedding in zip(enhanced_chunks, embeddings):
            chunk_obj = DocumentChunk(
                document_id=document_id,
                chunk_text=enhanced_chunk["text"],
                chunk_index=enhanced_chunk["metadata"]["chunk_index"],
                embedding=embedding,
                document_metadata=enhanced_chunk["metadata"],  # Store ALL metadata
                recency_score=enhanced_chunk["metadata"]["recency_score"],  # Save as separate column for fast queries
                is_active=True,  # New chunks are active
                version=doc_version  # Match document version
            )
            self.db.add(chunk_obj)
        
        self.db.commit()
        
        # Clear search cache to ensure fresh results include new document
        clear_search_cache()
        logger.info(f"Search cache cleared after processing document {document_id}")
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        self.update_state(state='PROGRESS', meta={'step': 'complete', 'progress': 100})
        
        # Calculate statistics from metadata
        total_entities = sum(
            len(chunk["metadata"]["entities"]["ids"]) + 
            len(chunk["metadata"]["entities"]["names"]) +
            len(chunk["metadata"]["entities"]["amounts"])
            for chunk in enhanced_chunks
        )
        
        avg_recency_score = sum(
            chunk["metadata"]["recency_score"] 
            for chunk in enhanced_chunks
        ) / len(enhanced_chunks) if enhanced_chunks else 0
        
        return {
            'status': 'success',
            'document_id': document_id,
            'chunks_created': len(enhanced_chunks),
            'total_entities_extracted': total_entities,
            'average_recency_score': round(avg_recency_score, 2),
            'data_types_found': list(set(
                dt for chunk in enhanced_chunks 
                for dt in chunk["metadata"]["data_types"]
            ))
        }
    
    except Exception as exc:
        # Log detailed error information
        logger.error(f"Error processing document {document_id}: {str(exc)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Retry with exponential backoff
        self.db.rollback()
        
        # Clean up temp file on final failure
        if self.request.retries >= self.max_retries:
            logger.error(f"Max retries reached for document {document_id}. Giving up.")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    finally:
        self.db.close()


@celery_app.task(bind=True, base=DatabaseTask)
def batch_process_documents(self, file_info_list: list):
    """
    Process multiple documents in batch.
    
    Args:
        file_info_list: List of dicts with document_id, file_path, filename
    """
    results = []
    
    for file_info in file_info_list:
        # Queue each document for processing
        task = process_document.delay(
            file_info['document_id'],
            file_info['file_path'],
            file_info['filename']
        )
        results.append({'document_id': file_info['document_id'], 'task_id': task.id})
    
    return results