"""
Talyn AI Coach â€” Claude API Service

Thin wrapper around the Anthropic SDK. All prompt construction
lives in app/prompts/coach_prompts.py â€” this module only handles
the API call and error handling.
"""

import json
import os
import anthropic
from app.models.schemas import (
    LearnerContext, CoachAction, CoachResponse, QuizResponse, QuizQuestion,
)
from app.prompts.coach_prompts import (
    answer_question_prompt,
    explain_concept_prompt,
    create_study_plan_prompt,
    encourage_prompt,
    generate_quiz_prompt,
)

# Initialise client once at import time (reads ANTHROPIC_API_KEY from env)
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL   = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500


# â”€â”€ Internal helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _call_claude(system: str, messages: list[dict], max_tokens: int = MAX_TOKENS) -> str:
    """Make a synchronous call to Claude and return the text response."""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


# â”€â”€ Public service functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def answer_question(learner: LearnerContext, question: str) -> CoachResponse:
    system, messages = answer_question_prompt(learner, question)
    text = _call_claude(system, messages)
    return CoachResponse(
        action=CoachAction.ANSWER_QUESTION,
        learner_id=learner.learner_id,
        response=text,
    )


def explain_concept(learner: LearnerContext, concept: str) -> CoachResponse:
    system, messages = explain_concept_prompt(learner, concept)
    text = _call_claude(system, messages)
    return CoachResponse(
        action=CoachAction.EXPLAIN_CONCEPT,
        learner_id=learner.learner_id,
        response=text,
    )


def create_study_plan(learner: LearnerContext, goals: str) -> CoachResponse:
    system, messages = create_study_plan_prompt(learner, goals)
    text = _call_claude(system, messages, max_tokens=2000)
    return CoachResponse(
        action=CoachAction.CREATE_STUDY_PLAN,
        learner_id=learner.learner_id,
        response=text,
    )


def encourage(learner: LearnerContext, trigger: str) -> CoachResponse:
    system, messages = encourage_prompt(learner, trigger)
    text = _call_claude(system, messages, max_tokens=300)
    return CoachResponse(
        action=CoachAction.ENCOURAGE,
        learner_id=learner.learner_id,
        response=text,
    )


def generate_quiz(learner: LearnerContext, topic: str, num_questions: int) -> QuizResponse:
    system, messages = generate_quiz_prompt(learner, topic, num_questions)
    raw = _call_claude(system, messages, max_tokens=2000)

    # Strip markdown fences if Claude wraps the JSON despite instructions
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    data = json.loads(clean)
    questions = [QuizQuestion(**q) for q in data["questions"]]

    return QuizResponse(
        learner_id=learner.learner_id,
        topic=topic,
        questions=questions,
    )
