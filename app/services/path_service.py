"""
Talyn â€” Learning Path Service

Calls Claude to generate and adjust personalized learning paths.
JSON parsing and validation are handled here before returning
typed response objects to the router.
"""

import json
import os
import anthropic

from app.models.schemas import (
    LearnerPathProfile, PathAction,
    RecommendedCourse, Milestone, WeeklyScheduleEntry,
    LearningPathResponse,
)
from app.prompts.path_prompts import generate_path_prompt, adjust_path_prompt

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000          # Paths can be long


# â”€â”€ Internal helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _call_claude(system: str, messages: list[dict]) -> str:
    response = _client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _parse_path_response(raw: str, learner_id: str, action: PathAction) -> LearningPathResponse:
    """Parse and validate the JSON response from Claude into a typed object."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    data = json.loads(clean)

    return LearningPathResponse(
        action=action,
        learner_id=learner_id,
        summary=data["summary"],
        recommended_courses=[RecommendedCourse(**c) for c in data["recommended_courses"]],
        milestones=[Milestone(**m) for m in data["milestones"]],
        weekly_schedule=[WeeklyScheduleEntry(**w) for w in data["weekly_schedule"]],
        total_estimated_weeks=data["total_estimated_weeks"],
    )


# â”€â”€ Public service functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_path(learner: LearnerPathProfile) -> LearningPathResponse:
    system, messages = generate_path_prompt(learner)
    raw = _call_claude(system, messages)
    return _parse_path_response(raw, learner.learner_id, PathAction.GENERATE_PATH)


def adjust_path(
    learner: LearnerPathProfile,
    current_path_course_ids: list[str],
    reason: str,
) -> LearningPathResponse:
    system, messages = adjust_path_prompt(learner, current_path_course_ids, reason)
    raw = _call_claude(system, messages)
    return _parse_path_response(raw, learner.learner_id, PathAction.ADJUST_PATH)
