"""
Talyn — Study Buddy System Router

Two endpoints:
  POST /buddy/match    → Rank a candidate pool into study buddy matches
  POST /buddy/icebreaker → Write a first message to a chosen buddy
"""

from fastapi import APIRouter, HTTPException
from app.backend_client import BackendError, resolve_learner
from app.models.schemas import (
    FindBuddyRequest, IcebreakerRequest,
    BuddyMatchResponse, IcebreakerResponse,
)
from app.services import buddy_service

router = APIRouter(prefix="/buddy", tags=["Study Buddy System"])


@router.post(
    "/match",
    response_model=BuddyMatchResponse,
    summary="Find the best study buddy matches for a learner",
)
async def find_buddy(body: FindBuddyRequest):
    """
    Ranks the given candidate pool for the learner using six weighted criteria:
    goals alignment, course/topic overlap, interest overlap, skill level
    closeness, time availability, and consistency.

    Returns matches best-first with a compatibility score, reasons, shared
    interests, and a ready-to-send intro message for the top match.

    **When to call this:**
    - When a learner opts into the Study Buddy System
    - Periodically to refresh suggestions as learners progress
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return buddy_service.find_buddy(learner, body.candidates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/icebreaker",
    response_model=IcebreakerResponse,
    summary="Write a warm first message to a chosen buddy",
)
async def icebreaker(body: IcebreakerRequest):
    """
    Generates a natural, personal opening message for the learner to send their
    chosen buddy — grounded in shared interests/goals, with one concrete next
    step to get the partnership moving.

    **When to call this:**
    - When the learner picks a buddy from the match results
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return buddy_service.icebreaker(learner, body.buddy)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))