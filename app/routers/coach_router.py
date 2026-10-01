"""
Talyn AI Coach — API Router

All five coach endpoints. Each endpoint:
  1. Receives learner context + action-specific payload
  2. Calls the coach service
  3. Returns a structured response
"""

from fastapi import APIRouter, HTTPException
from app.backend_client import BackendError, resolve_learner
from app.models.schemas import (
    AskQuestionRequest, StudyPlanRequest, QuizRequest,
    EncourageRequest, ExplainConceptRequest,
    CoachResponse, QuizResponse,
)
from app.services import coach_service

router = APIRouter(prefix="/coach", tags=["AI Learning Coach"])


@router.post(
    "/ask",
    response_model=CoachResponse,
    summary="Answer a learner's question about course content",
)
async def ask_question(body: AskQuestionRequest):
    """
    The learner asks a free-form question about their current course or topic.
    The coach responds with a personalized, context-aware answer.
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return coach_service.answer_question(learner, body.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/explain",
    response_model=CoachResponse,
    summary="Explain a concept using learner-relevant examples",
)
async def explain_concept(body: ExplainConceptRequest):
    """
    The coach explains a concept, adapting the example to the learner's
    declared interests and difficulty level.
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return coach_service.explain_concept(learner, body.concept)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/study-plan",
    response_model=CoachResponse,
    summary="Generate a personalized study plan",
)
async def create_study_plan(body: StudyPlanRequest):
    """
    Creates a structured study plan based on the learner's goals, current
    progress, quiz performance, and available time.
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return coach_service.create_study_plan(learner, body.goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/encourage",
    response_model=CoachResponse,
    summary="Send a contextual encouragement message",
)
async def encourage(body: EncourageRequest):
    """
    Triggered by backend events (lesson completed, quiz failed, streak at risk, etc.)
    Returns a short, personalized motivational message.

    Example triggers:
    - "completed lesson"
    - "low quiz score on CSS Flexbox"
    - "streak at risk — hasn't studied today"
    - "reached 50% course completion"
    - "earned 500 XP this week"
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return coach_service.encourage(learner, body.trigger)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/quiz",
    response_model=QuizResponse,
    summary="Generate a personalized quiz on a topic",
)
async def generate_quiz(body: QuizRequest):
    """
    Generates a multiple-choice quiz tailored to the learner's level and
    prior performance on the topic. Returns structured JSON for the frontend
    to render directly.
    """
    try:
        learner = resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return coach_service.generate_quiz(learner, body.topic, body.num_questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
