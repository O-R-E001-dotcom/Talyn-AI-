"""
Talyn â€” Study Buddy System Service

Calls Claude to rank study buddy candidates and write icebreaker messages.
JSON parsing and validation happen here before returning typed response objects.
"""

import json
import os
import anthropic

from app.models.schemas import (
    LearnerContext, BuddyCandidate,
    BuddyMatch, BuddyMatchResponse, IcebreakerResponse,
)
from app.prompts.buddy_prompts import (
    find_buddy_prompt,
    icebreaker_prompt,
)

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500


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

def find_buddy(
    learner: LearnerContext,
    candidates: list[BuddyCandidate],
) -> BuddyMatchResponse:
    system, messages = find_buddy_prompt(learner, candidates)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return BuddyMatchResponse(
        learner_id=learner.learner_id,
        matches=[BuddyMatch(**m) for m in data["matches"]],
        intro_message=data["intro_message"],
    )


def icebreaker(
    learner: LearnerContext,
    buddy: BuddyCandidate,
) -> IcebreakerResponse:
    system, messages = icebreaker_prompt(learner, buddy)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return IcebreakerResponse(
        learner_id=learner.learner_id,
        buddy_id=buddy.learner_id,
        buddy_name=buddy.learner_name,
        message=data["message"],
    )
