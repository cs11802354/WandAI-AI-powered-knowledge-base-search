"""
Document management API endpoints.
Handles upload, listing, and deletion of documents.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db, Document, DocumentChunk
from app.api.schemas import UploadResponse, DocumentInfo
from app.services.file_service import calculate_file_hash
from app.services.search_service import clear_search_cache
from app.tasks.document_tasks import process_document
from typing import List
from datetime import datetime
import os
import shutil
import asyncio
import aiofiles
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload with content-based duplicate detection.
    Handles disconnection with automatic cleanup.
    
    Process:
    1. Stream file to disk (handles large files)
    2. Calculate content hash
    3. Check for content duplicates
    4. Create database record
    5. Queue for background processing
    """
    temp_file_path = None
    
    try:
        # Validate file size limit
        max_size = 100 * 1024 * 1024  # 100MB
        
        # Step 1: Stream to temp file (handles large files + disconnection)
        upload_id = str(uuid4())
        temp_file_path = f"/app/uploads/{upload_id}_{file.filename}"
        
        logger.info(f"Starting upload: {file.filename}")
        
        # Create upload directory if not exists
        os.makedirs("/app/uploads", exist_ok=True)
        
        # Stream file to disk with disconnection detection
        total_bytes = 0
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while True:
                try:
                    # Read chunk with timeout (detect disconnection)
                    chunk = await asyncio.wait_for(
                        file.read(5 * 1024 * 1024),  # 5MB chunks
                        timeout=30  # 30 seconds timeout per chunk
                    )
                    
                    if not chunk:  # End of file
                        break
                    
                    total_bytes += len(chunk)
                    
                    # Check size limit
                    if total_bytes > max_size:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"File too large. Max size: {max_size} bytes"
                        )
                    
                    await f.write(chunk)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Upload timeout for {file.filename}")
                    raise HTTPException(
                        status_code=408, 
                        detail="Upload timeout - connection too slow or interrupted"
                    )
        
        logger.info(f"Upload complete: {file.filename} ({total_bytes} bytes)")
        
        # Step 2: Calculate hash for content-based duplicate detection
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
            content_hash = calculate_file_hash(file_content)
        
        # Step 3: Check if FILENAME exists (for versioning)
        existing_by_filename = db.query(Document).filter(
            Document.filename == file.filename,
            Document.is_active == True
        ).first()
        
        if existing_by_filename:
            # Same filename found - check if content changed
            
            if existing_by_filename.content_hash == content_hash:
                # Same filename, same content - no change needed
                logger.info(f"No change detected: {file.filename} content unchanged")
                
                # Cleanup temp file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                
                return UploadResponse(
                    status="no_change",
                    message=f"File '{file.filename}' content unchanged. Current version: {existing_by_filename.version}",
                    document_id=existing_by_filename.id
                )
            
            # Same filename, different content - CREATE NEW VERSION!
            logger.info(f"Updating {file.filename}: v{existing_by_filename.version} → v{existing_by_filename.version + 1}")
            
            # Soft delete old document
            existing_by_filename.is_active = False
            existing_by_filename.replaced_at = datetime.utcnow()
            
            # Soft delete old chunks
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == existing_by_filename.id,
                DocumentChunk.is_active == True
            ).update({
                "is_active": False,
                "replaced_at": datetime.utcnow()
            })
            
            # Create new version
            document = Document(
                filename=file.filename,
                content_hash=content_hash,
                file_size=total_bytes,
                version=existing_by_filename.version + 1,  # Increment version
                is_active=True,
                document_metadata={
                    "original_filename": file.filename,
                    "content_type": file.content_type,
                    "upload_id": upload_id,
                    "previous_version": existing_by_filename.id,
                    "previous_version_number": existing_by_filename.version
                }
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Clear search cache immediately to ensure old version is excluded from search results
            clear_search_cache()
            logger.info(f"Search cache cleared after deactivating old version")
            
            logger.info(f"New version created: id={document.id}, version={document.version}")
            
            # Queue for processing
            task = process_document.delay(document.id, temp_file_path, file.filename)
            
            return UploadResponse(
                status="updated",
                message=f"Document updated to version {document.version}. Previous version archived.",
                document_id=document.id,
                task_id=task.id
            )
        
        # Step 4: Check if CONTENT exists with different filename (duplicate detection)
        existing_by_content = db.query(Document).filter(
            Document.content_hash == content_hash,
            Document.is_active == True
        ).first()
        
        if existing_by_content:
            # Same content, different filename - this is a duplicate
            logger.info(f"Duplicate content detected: {file.filename} matches {existing_by_content.filename}")
            
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return UploadResponse(
                status="duplicate",
                message=f"This content already exists as '{existing_by_content.filename}'. "
                        f"Same content with different filename is treated as duplicate.",
                document_id=existing_by_content.id
            )
        
        # Step 5: Truly new file - create new document
        document = Document(
            filename=file.filename,
            content_hash=content_hash,
            file_size=total_bytes,
            version=1,  # First version
            is_active=True,
            document_metadata={
                "original_filename": file.filename,
                "content_type": file.content_type,
                "upload_id": upload_id
            }
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"New document created: id={document.id}, filename={file.filename}, version=1")
        
        # Step 6: Queue for background processing
        task = process_document.delay(document.id, temp_file_path, file.filename)
        
        return UploadResponse(
            status="processing",
            message="Document uploaded successfully. Processing in background.",
            document_id=document.id,
            task_id=task.id
        )
    
    except HTTPException:
        # Known error - cleanup and re-raise
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Cleaned up temp file after error: {temp_file_path}")
        raise
    
    except Exception as e:
        # Unexpected error - cleanup
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Cleaned up temp file after unexpected error: {temp_file_path}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/batch-upload", response_model=List[UploadResponse])
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload multiple documents at once.
    """
    responses = []
    
    for file in files:
        # Reuse single upload logic
        response = await upload_document(file, db)
        responses.append(response)
    
    return responses


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all documents in the knowledge base.
    """
    documents = db.query(Document).offset(skip).limit(limit).all()
    
    # Add chunk count for each document
    result = []
    for doc in documents:
        result.append({
            "id": doc.id,
            "filename": doc.filename,
            "file_size": doc.file_size,
            "uploaded_at": doc.uploaded_at,
            "chunk_count": len(doc.chunks)
        })
    
    return result


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all its chunks.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(document)
    db.commit()
    
    return {"status": "success", "message": f"Document {document_id} deleted"}
