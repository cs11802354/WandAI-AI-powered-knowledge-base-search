"""
Task status API endpoints.
Check status of background tasks.
"""

from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from app.celery_app import celery_app
from app.api.schemas import TaskStatus

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    Get status of a background task.
    
    Use the task_id returned from /upload endpoint.
    
    Possible states:
    - PENDING: Task is queued, not started yet
    - PROGRESS: Task is running (check progress field)
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed
    """
    task = AsyncResult(task_id, app=celery_app)
    
    if task.state == 'PENDING':
        response = {
            "task_id": task_id,
            "status": "pending",
            "progress": {"step": "queued", "progress": 0}
        }
    elif task.state == 'PROGRESS':
        response = {
            "task_id": task_id,
            "status": "processing",
            "progress": task.info
        }
    elif task.state == 'SUCCESS':
        response = {
            "task_id": task_id,
            "status": "completed",
            "progress": {"step": "complete", "progress": 100},
            "result": task.result
        }
    elif task.state == 'FAILURE':
        response = {
            "task_id": task_id,
            "status": "failed",
            "progress": {"error": str(task.info)}
        }
    else:
        response = {
            "task_id": task_id,
            "status": task.state.lower()
        }
    
    return TaskStatus(**response)
