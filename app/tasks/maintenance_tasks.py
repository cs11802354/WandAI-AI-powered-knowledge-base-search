"""
Scheduled maintenance tasks.
These run automatically via Celery Beat.
"""

from app.celery_app import celery_app
from app.models.database import engine
from sqlalchemy import text
import os
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@celery_app.task
def rebuild_vector_index():
    """
    Rebuild vector index for optimal performance.
    Runs nightly at 2 AM (configured in celery_app.py).
    
    Why needed:
    As you add/delete vectors, the index becomes fragmented.
    REINDEX optimizes it for faster searches.
    """
    with engine.connect() as conn:
        # Reindex the vector similarity index
        conn.execute(text("REINDEX INDEX document_chunks_embedding_idx;"))
        conn.commit()
    
    return {"status": "success", "message": "Vector index rebuilt"}


@celery_app.task
def cleanup_temp_files():
    """
    Clean up orphaned temp files from interrupted uploads.
    Runs hourly (configured in celery_app.py).
    
    Why needed:
    - File uploads create temp files
    - If connection drops, partial files remain
    - Without cleanup, disk fills up over time
    """
    temp_dir = "/app/uploads"
    
    if not os.path.exists(temp_dir):
        logger.info("Temp directory doesn't exist yet")
        return {"status": "skipped", "message": "Temp directory doesn't exist"}
    
    current_time = datetime.utcnow()
    deleted_count = 0
    errors = 0
    
    logger.info("Starting orphaned file cleanup...")
    
    for filename in os.listdir(temp_dir):
        try:
            filepath = os.path.join(temp_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(filepath):
                continue
            
            # Get file modification time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            file_age = current_time - file_mtime
            
            # Delete files older than 24 hours
            if file_age > timedelta(hours=24):
                file_size = os.path.getsize(filepath)
                os.remove(filepath)
                deleted_count += 1
                logger.info(f"Cleaned up orphaned file: {filename} "
                           f"(age: {file_age}, size: {file_size} bytes)")
        
        except Exception as e:
            errors += 1
            logger.error(f"Error cleaning up {filename}: {str(e)}")
    
    logger.info(f"Cleanup complete: {deleted_count} files deleted, {errors} errors")
    
    return {
        "status": "success",
        "files_deleted": deleted_count,
        "errors": errors
    }
