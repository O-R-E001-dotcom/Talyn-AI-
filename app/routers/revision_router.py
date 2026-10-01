
"""
Talyn — Revision Schedule Router

Two endpoints:
  POST /revision/generate  → Generate a full 30-day spaced repetition schedule
  POST /revision/update    → Refresh remaining schedule after a session is completed
"""

from fastapi import APIRouter, HTTPException
from app import backend_client
from app.backend_client import BackendError
from app.models.schemas import (
    GenerateRevisionScheduleRequest,
    UpdateRevisionScheduleRequest,
    RevisionScheduleResponse,
)
from app.services import revision_service

router = APIRouter(prefix="/revision", tags=["AI-Generated Revision Schedules"])


@router.post(
    "/generate",
    response_model=RevisionScheduleResponse,
    summary="Generate a 30-day personalised revision schedule",
)
async def generate_revision_schedule(body: GenerateRevisionScheduleRequest):
    """
    Analyses the learner's full topic history — quiz scores, days since studied,
    review counts, and lesson completion — and generates a 30-day spaced repetition
    schedule that maximises long-term retention.

    Each entry in the schedule includes:
    - The topic to revise and which lesson it belongs to
    - The suggested revision method (quiz / flashcard / re-read)
    - Estimated time in minutes
    - The specific reason this topic was scheduled on this day

    **When to call this:**
    - When a learner first requests a revision schedule
    - At the start of a new month / study period
    - When a learner's topic history changes significantly (e.g. completed many new lessons)

    **Spaced repetition logic applied:**
    - Topics with low quiz scores are scheduled sooner and more frequently
    - Topics studied long ago are prioritised over recently studied ones
    - Daily session length is capped to the learner's `daily_study_minutes` budget
    - Rest days are included naturally — not every day has a revision task
    """
    try:
        learner = backend_client.resolve_profile(
            body.learner, body.backend_token,
            backend_client.fetch_revision_profile,
        )
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return revision_service.generate_revision_schedule(learner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/update",
    response_model=RevisionScheduleResponse,
    summary="Refresh the remaining schedule after a revision session",
)
async def update_revision_schedule(body: UpdateRevisionScheduleRequest):
    """
    Called by the backend immediately after a learner completes a revision session.
    Re-evaluates and regenerates the schedule for the remaining days based on the
    outcome of the session.

    **Adaptive behaviour:**
    - If the quiz score was **low (<60%)**: the topic is resurfaced sooner in the
      remaining schedule with a higher-intensity method (quiz)
    - If the quiz score was **high (80%+)**: the topic is pushed later or dropped,
      freeing up time for weaker areas
    - All other topics are also re-evaluated against the updated topic history

    **When to call this:**
    - After every completed revision session
    - Pass the current day number (1–29) so the AI only regenerates what's left

    **Returns:** The updated schedule for days `current_schedule_day + 1` to 30
    """
    try:
        learner = backend_client.resolve_profile(
            body.learner, body.backend_token,
            backend_client.fetch_revision_profile,
        )
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return revision_service.update_revision_schedule(
            learner,
            body.completed_topic,
            body.session_quiz_score,
            body.current_schedule_day,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
