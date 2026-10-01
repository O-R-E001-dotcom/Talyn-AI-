"""
Talyn — AI Insights Prompts

Prompt builders that turn learner data into honest, useful, learner-facing
insights. Two prompt builders:
  - generate_insights_prompt → full report (strengths, weaknesses,
                               improvement suggestions, progress forecast)
  - priority_focus_prompt    → the 1-3 highest-impact actions for the week
"""

from app.models.schemas import LearnerContext
from app.prompts.coach_prompts import _build_learner_profile


# ── System Prompt ─────────────────────────────────────────────────────────────

def _insights_system_prompt(learner: LearnerContext) -> str:
    return f"""You are Talyn Insights Analyst, an AI engine that reads a learner's data on the Talyn platform and produces honest, useful insights to help them improve continuously.

YOUR JOB
────────
Analyse the learner's performance and behaviour data and produce:
1. LEARNING STRENGTHS — where the learner clearly does well (evidence-based).
2. WEAKNESSES — areas that consistently hold them back (evidence-based, never shaming).
3. IMPROVEMENT SUGGESTIONS — concrete, realistic next actions with expected impact.
4. PROGRESS FORECAST — a realistic projection of where they'll be in a given timeframe, with assumptions stated.

ANALYSIS PRINCIPLES
───────────────────
- Evidence over guesses: tie every insight to specific data (quiz scores, XP, streaks, lessons completed, mission progress).
- Honest but encouraging: be direct about weak areas without ever shaming the learner.
- Actionable: every suggestion must be something the learner can do this week.
- Realistic forecasts: base projections on pace so far and state assumptions (e.g. "assuming 30 min/day").

RULES
─────
- Never invent data that isn't in the learner snapshot.
- Return ONLY valid JSON. No markdown fences, no preamble.

{_build_learner_profile(learner)}"""


# ── Generate Insights Prompt ──────────────────────────────────────────────────

def generate_insights_prompt(learner: LearnerContext) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for a full insights report."""
    system = _insights_system_prompt(learner)

    messages = [{
        "role": "user",
        "content": (
            f"Generate a full insights report for {learner.learner_name}.\n\n"
            f"Use ONLY the data in the learner snapshot.\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "summary": "2-3 sentence overall assessment",\n'
            f'  "strengths": [\n'
            f'    {{"area": "...", "detail": "...", "evidence": "the data that supports this"}}\n'
            f'  ],\n'
            f'  "weaknesses": [\n'
            f'    {{"area": "...", "detail": "...", "impact": "how it holds the learner back", "evidence": "..."}}\n'
            f'  ],\n'
            f'  "suggestions": [\n'
            f'    {{"title": "...", "description": "Concrete next action", "expected_impact": "..."}}\n'
            f'  ],\n'
            f'  "forecast": {{\n'
            f'    "timeframe": "next 4 weeks",\n'
            f'    "projection": "...",\n'
            f'    "confidence_level": "high | medium | low",\n'
            f'    "assumptions": ["..."]\n'
            f'  }}\n'
            f'}}\n\n'
            f"Rules:\n"
            f"- 3-5 strengths\n"
            f"- 2-4 weaknesses, ordered by impact\n"
            f"- 3-5 suggestions, ordered by expected impact\n"
            f"- forecast must be grounded in the learner's pace and state its assumptions\n"
            f"- every entry's evidence must reference actual data from the snapshot"
        )
    }]

    return system, messages


# ── Priority Focus Prompt ─────────────────────────────────────────────────────

def priority_focus_prompt(learner: LearnerContext) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for the top weekly priorities."""
    system = _insights_system_prompt(learner)

    messages = [{
        "role": "user",
        "content": (
            f"Based on {learner.learner_name}'s data, identify the TOP priorities for the next week "
            f"that would most improve their learning outcomes.\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "priorities": [\n'
            f'    {{\n'
            f'      "focus_area": "...",\n'
            f'      "action": "One concrete action for this week",\n'
            f'      "rationale": "Why this matters most right now (grounded in data)",\n'
            f'      "suggested_metric": "How to measure success, e.g. quiz score >= 70%"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "message": "A short, encouraging message to {learner.learner_name} framing the top priority"\n'
            f'}}\n\n'
            f"Rules:\n"
            f"- 1-3 priorities, ordered by expected impact\n"
            f"- every priority must be grounded in the learner's actual data\n"
            f"- message must be specific, warm, and motivating"
        )
    }]

    return system, messages