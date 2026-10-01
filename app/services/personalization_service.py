
"""
Talyn â€” Content Personalization Service

Calls Claude to reframe course content through a learner's interests.
Handles both single and batch personalization requests.
"""

import json
import os
import anthropic

from app.models.schemas import (
    PersonalizationProfile, ContentType,
    PersonalizedContentResponse,
    BatchPersonalizedItem, BatchPersonalizedResponse,
)
from app.prompts.personalization_prompts import (
    personalize_content_prompt,
    batch_personalize_prompt,
)

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 2000


# â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _call_claude(system: str, messages: list[dict], max_tokens: int = MAX_TOKENS) -> str:
    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _clean_json(raw: str) -> str:
    """Strip markdown fences if Claude wraps the JSON despite instructions."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return clean.strip()


# â”€â”€ Public service functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def personalize_content(
    learner: PersonalizationProfile,
    content_type: ContentType,
    original_content: str,
) -> PersonalizedContentResponse:
    system, messages = personalize_content_prompt(learner, content_type, original_content)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return PersonalizedContentResponse(
        learner_id=learner.learner_id,
        content_type=content_type,
        original_content=original_content,
        personalized_content=data["personalized_content"],
        interest_used=data["interest_used"],
    )


def batch_personalize(
    learner: PersonalizationProfile,
    items: list[dict],
) -> BatchPersonalizedResponse:
    system, messages = batch_personalize_prompt(learner, items)
    # Batch responses can be long â€” scale tokens accordingly
    raw = _call_claude(system, messages, max_tokens=min(4000, 800 * len(items)))
    data = json.loads(_clean_json(raw))

    return BatchPersonalizedResponse(
        learner_id=learner.learner_id,
        items=[BatchPersonalizedItem(**item) for item in data],
    )
