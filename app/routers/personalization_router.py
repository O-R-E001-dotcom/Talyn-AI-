
"""
Talyn — Content Personalization Router

Two endpoints:
  POST /personalize/content  → Personalize a single piece of content
  POST /personalize/batch    → Personalize multiple pieces in one call
"""

from fastapi import APIRouter, HTTPException
from app import backend_client
from app.backend_client import BackendError
from app.models.schemas import (
    PersonalizeContentRequest, BatchPersonalizeRequest,
    PersonalizedContentResponse, BatchPersonalizedResponse,
)
from app.services import personalization_service

router = APIRouter(prefix="/personalize", tags=["Interest-Based Content Personalization"])


@router.post(
    "/content",
    response_model=PersonalizedContentResponse,
    summary="Personalize a single piece of course content",
)
async def personalize_content(body: PersonalizeContentRequest):
    """
    Takes an original piece of course content and rewrites it so the framing,
    analogies, and examples reflect the learner's personal interests — while
    keeping the concept, facts, and learning objective exactly intact.

    **Content types:**
    - `explanation` — A lesson explanation or concept introduction
    - `example` — A worked example illustrating a concept
    - `quiz_context` — The scenario/context of a quiz question
    - `exercise_brief` — A project or practice exercise brief

    **When to call this:**
    - When rendering a lesson for a specific learner
    - Before displaying a quiz question to add personal context
    - When showing an exercise brief
    """
    try:
        learner = backend_client.resolve_profile(
            body.learner, body.backend_token,
            backend_client.fetch_personalization_profile,
        )
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return personalization_service.personalize_content(
            learner,
            body.content_type,
            body.original_content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/batch",
    response_model=BatchPersonalizedResponse,
    summary="Personalize multiple content pieces in a single API call",
)
async def batch_personalize(body: BatchPersonalizeRequest):
    """
    Personalizes multiple pieces of content for the same learner in one call.
    More efficient than calling `/personalize/content` repeatedly when loading
    a full lesson (explanation + examples + exercise brief together).

    **Request body example:**
    ```json
    {
      "learner": { ... },
      "items": [
        { "content_type": "explanation", "original_content": "CSS Flexbox is a layout model..." },
        { "content_type": "example", "original_content": "Consider a navigation bar with..." },
        { "content_type": "exercise_brief", "original_content": "Build a responsive card grid..." }
      ]
    }
    ```

    **When to call this:**
    - On lesson load — send all content pieces at once
    - Maximum recommended batch size: 5 items
    """
    try:
        learner = backend_client.resolve_profile(
            body.learner, body.backend_token,
            backend_client.fetch_personalization_profile,
        )
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        if len(body.items) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum batch size is 5 items. Split into multiple requests."
            )
        return personalization_service.batch_personalize(learner, body.items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
