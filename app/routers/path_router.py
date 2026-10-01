"""
Talyn — Learning Path Router

Two endpoints:
  POST /path/generate  → Build a new path from scratch
  POST /path/adjust    → Re-sequence an existing path based on a reason
"""

from fastapi import APIRouter, HTTPException
from app import backend_client
from app.backend_client import BackendError
from app.models.schemas import (
    GeneratePathRequest, AdjustPathRequest, LearningPathResponse,
)
from app.services import path_service

router = APIRouter(prefix="/path", tags=["Personalized Learning Path"])


@router.post(
    "/generate",
    response_model=LearningPathResponse,
    summary="Generate a personalized learning path for a learner",
)
async def generate_path(body: GeneratePathRequest):
    """
    Takes a learner profile (skill level, goals, interests, available time)
    and the full course catalogue, then returns an ordered path with:

    - Recommended courses (with reasoning per course)
    - Estimated time per course
    - Milestones & checkpoints
    - Week-by-week schedule

    **When to call this:**
    - When a new learner onboards and needs a path
    - When a learner resets or changes their goals entirely
    """
    try:
        learner = backend_client.resolve_profile(
            body.learner, body.backend_token, backend_client.fetch_path_profile
        )
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return path_service.generate_path(learner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/adjust",
    response_model=LearningPathResponse,
    summary="Adjust an existing learning path based on a trigger reason",
)
async def adjust_path(body: AdjustPathRequest):
    """
    Re-evaluates and updates an existing learning path given a reason for change.

    The AI may remove, add, reorder, or replace courses depending on the reason.

    **Example reasons:**
    - `"learner is progressing faster than expected"`
    - `"learner is struggling with current course and needs easier material first"`
    - `"learner changed goal from frontend to full-stack development"`
    - `"learner now has 10 hours/week instead of 5"`
    - `"learner completed an external course on Python basics"`

    **When to call this:**
    - When learner changes goals
    - After significant quiz performance changes
    - When learner requests a path review
    - On a scheduled monthly path review
    """
    try:
        learner = backend_client.resolve_profile(
            body.learner, body.backend_token, backend_client.fetch_path_profile
        )
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return path_service.adjust_path(
            learner,
            body.current_path_course_ids,
            body.reason,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
