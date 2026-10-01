"""
Talyn â€” AI Insights Service

Calls Claude to turn learner data into honest, useful insights and weekly
priority focus. JSON parsing and validation happen here before returning
typed response objects.
"""

import json
import os
import anthropic

from app.models.schemas import (
    LearnerContext,
    InsightsReport, PriorityFocus,
    GenerateInsightsResponse, PriorityFocusResponse,
)
from app.prompts.insights_prompts import (
    generate_insights_prompt,
    priority_focus_prompt,
)

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 3000          # Insights reports can be long


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

def generate_insights(learner: LearnerContext) -> GenerateInsightsResponse:
    system, messages = generate_insights_prompt(learner)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return GenerateInsightsResponse(
        learner_id=learner.learner_id,
        report=InsightsReport(**data),
    )


def priority_focus(learner: LearnerContext) -> PriorityFocusResponse:
    system, messages = priority_focus_prompt(learner)
    raw = _call_claude(system, messages)
    data = json.loads(_clean_json(raw))

    return PriorityFocusResponse(
        learner_id=learner.learner_id,
        priorities=[PriorityFocus(**p) for p in data["priorities"]],
        message=data["message"],
    )
