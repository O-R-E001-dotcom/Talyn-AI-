"""
Talyn — Mission-Based Learning Router

Two endpoints:
  POST /mission/recommend  → Recommend the next mission for the learner
  POST /mission/guide      → Guide the learner through the next step of
                             their active mission
"""

from fastapi import APIRouter, HTTPException
from app.backend_client import BackendError, resolve_learner
from app.models.schemas import (
    RecommendMissionRequest, GuideMissionRequest,
    MissionRecommendationResponse, MissionGuidanceResponse,
)
from app.services import mission_service

router = APIRouter(prefix="/mission", tags=["Mission-Based Learning"])


@router.post(
    "/recommend",
    response_model=MissionRecommendationResponse,
    summary="Recommend the next mission for a learner",
)
async def recommend_mission(body: RecommendMissionRequest):
    """
    Analyses the learner's stage (onboarding, in-progress, returning after a
    break) and recommends a short, achievable mission designed to create a
    quick win.

    **When to call this:**
    - When a learner first joins the platform (First Mission)
    - After a learner completes their previous mission
    - When a learner requests something new to do
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return mission_service.recommend_mission(learner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/guide",
    response_model=MissionGuidanceResponse,
    summary="Guide the learner through the next step of their active mission",
)
async def guide_mission(body: GuideMissionRequest):
    """
    Looks at the learner's active mission (its steps and which are done) and
    returns warm, concrete coaching for the single next step.

    **When to call this:**
    - When a learner opens their active mission
    - After a mission step is completed (to surface the next step)
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return mission_service.guide_mission(learner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))