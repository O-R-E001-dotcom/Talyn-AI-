"""
Talyn â€” Mission-Based Learning Service

Calls Claude to recommend and guide learners through short, quick-win missions.
JSON parsing and validation happen here before returning typed response objects.
"""

import json
import os
import anthropic

from app.models.schemas import (
    LearnerContext,
    RecommendedMissionStep,
    MissionRecommendationResponse,
    MissionGuidanceResponse,
)
from app.prompts.mission_prompts import (
    recommend_mission_prompt,
    guide_mission_prompt,
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

def recommend_mission(learner: LearnerContext) -> MissionRecommendationResponse:
    system, messages = recommend_mission_prompt(learner)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return MissionRecommendationResponse(
        learner_id=learner.learner_id,
        mission_title=data["mission_title"],
        mission_description=data["mission_description"],
        purpose=data["purpose"],
        reward_xp=data["reward_xp"],
        badge=data.get("badge"),
        steps=[RecommendedMissionStep(**s) for s in data["steps"]],
        message=data["message"],
    )


def guide_mission(learner: LearnerContext) -> MissionGuidanceResponse:
    system, messages = guide_mission_prompt(learner)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return MissionGuidanceResponse(
        learner_id=learner.learner_id,
        mission_title=data["mission_title"],
        next_step=RecommendedMissionStep(**data["next_step"]),
        message=data["message"],
    )
