"""
Talyn — AI Insights Router

Two endpoints:
  POST /insights/generate  → Full insights report (strengths, weaknesses,
                             improvement suggestions, progress forecast)
  POST /insights/priority  → Top 1-3 focus areas for the coming week
"""

from fastapi import APIRouter, HTTPException
from app.backend_client import BackendError, resolve_learner
from app.models.schemas import (
    GenerateInsightsRequest, PriorityFocusRequest,
    GenerateInsightsResponse, PriorityFocusResponse,
)
from app.services import insights_service

router = APIRouter(prefix="/insights", tags=["AI Insights"])


@router.post(
    "/generate",
    response_model=GenerateInsightsResponse,
    summary="Generate a full AI insights report for a learner",
)
async def generate_insights(body: GenerateInsightsRequest):
    """
    Analyses the learner's performance and behaviour data (quiz scores, XP,
    streaks, lessons completed, mission progress) into an honest report with:

    - Learning strengths (evidence-based)
    - Weaknesses (honest, never shaming)
    - Improvement suggestions (actionable this week)
    - Progress forecast (with stated assumptions)

    **When to call this:**
    - On a weekly check-in
    - When a learner opens a dashboard / progress view
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return insights_service.generate_insights(learner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/priority",
    response_model=PriorityFocusResponse,
    summary="Recommend the top focus areas for the coming week",
)
async def priority_focus(body: PriorityFocusRequest):
    """
    Returns the 1-3 highest-impact actions the learner should focus on this
    week, each with a concrete action and a success metric, plus a short
    encouraging framing message.

    **When to call this:**
    - At the start of each week
    - After significant progress or performance changes
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return insights_service.priority_focus(learner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))