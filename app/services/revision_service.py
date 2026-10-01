
"""
Talyn â€” Revision Schedule Service

Calls Claude to generate and update 30-day spaced repetition schedules.
"""

import json
import os
import anthropic

from app.models.schemas import (
    RevisionScheduleProfile, RevisionEntry, RevisionMethod,
    RevisionScheduleResponse,
)
from app.prompts.revision_prompts import (
    generate_revision_schedule_prompt,
    update_revision_schedule_prompt,
)

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _call_claude(system: str, messages: list[dict]) -> str:
    response = _client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _clean_json(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return clean.strip()


def _parse_schedule(
    data: dict,
    learner_id: str,
    start_date: str,
    total_days: int = 30,
) -> RevisionScheduleResponse:
    entries = [
        RevisionEntry(
            day=e["day"],
            date=e["date"],
            topic=e["topic"],
            lesson=e["lesson"],
            method=RevisionMethod(e["method"]),
            estimated_minutes=e["estimated_minutes"],
            reason=e["reason"],
        )
        for e in data["entries"]
    ]
    return RevisionScheduleResponse(
        learner_id=learner_id,
        schedule_start_date=start_date,
        total_days=total_days,
        summary=data["summary"],
        entries=entries,
    )


# â”€â”€ Public service functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_revision_schedule(
    learner: RevisionScheduleProfile,
) -> RevisionScheduleResponse:
    system, messages = generate_revision_schedule_prompt(learner)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))
    return _parse_schedule(data, learner.learner_id, learner.schedule_start_date)


def update_revision_schedule(
    learner: RevisionScheduleProfile,
    completed_topic: str,
    session_quiz_score: float | None,
    current_schedule_day: int,
) -> RevisionScheduleResponse:
    system, messages = update_revision_schedule_prompt(
        learner, completed_topic, session_quiz_score, current_schedule_day
    )
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))
    # Remaining days only â€” total_days reflects what's left
    remaining_days = 30 - current_schedule_day
    return _parse_schedule(
        data, learner.learner_id, learner.schedule_start_date, remaining_days
    )
