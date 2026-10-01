"""
Talyn AI Insights — Prompt-level tests

These tests validate that insights prompts (report structure, analysis
principles, priority guidance) are correctly rendered WITHOUT calling any
external API. No ANTHROPIC_API_KEY is required.

Run with:
    pytest tests/test_insights.py -v
"""

import pytest
from app.models.schemas import (
    LearnerContext, DifficultyLevel, QuizPerformance,
)
from app.prompts.insights_prompts import (
    generate_insights_prompt,
    priority_focus_prompt,
)


def _base_learner(**overrides) -> LearnerContext:
    defaults = dict(
        learner_name="Adeola",
        learner_id="learner_001",
        current_course="UI/UX Design Fundamentals",
        current_lesson="Lesson 4: Layout & Spacing",
        current_topic="CSS Flexbox",
        interests=["football", "music", "technology"],
        difficulty_level=DifficultyLevel.BEGINNER,
        goals="Become a junior UI/UX designer in 3 months",
        xp_total=320,
        xp_this_week=85,
        streak_days=4,
        lessons_completed=6,
        lessons_total=20,
        completion_percent=30.0,
        quiz_performance=[
            QuizPerformance(
                topic="HTML Basics",
                score_percent=90.0,
                attempts=1,
                last_attempt_date="2026-05-28",
            ),
            QuizPerformance(
                topic="CSS Selectors",
                score_percent=55.0,
                attempts=2,
                last_attempt_date="2026-05-30",
            ),
        ],
    )
    defaults.update(overrides)
    return LearnerContext(**defaults)


@pytest.fixture
def learner() -> LearnerContext:
    return _base_learner()


def test_generate_prompt_requests_all_report_sections(learner):
    system, messages = generate_insights_prompt(learner)
    content = messages[0]["content"]
    assert "strengths" in content
    assert "weaknesses" in content
    assert "suggestions" in content
    assert "forecast" in content
    assert "confidence_level" in content


def test_generate_prompt_uses_only_snapshot_data(learner):
    system, messages = generate_insights_prompt(learner)
    content = messages[0]["content"]
    assert "Use ONLY the data in the learner snapshot" in content
    assert "3-5 strengths" in content
    assert "2-4 weaknesses" in content
    assert "ordered by expected impact" in content


def test_system_prompt_contains_analysis_principles(learner):
    system, messages = generate_insights_prompt(learner)
    assert "Evidence over guesses" in system
    assert "without ever shaming" in system
    assert "something the learner can do this week" in system
    assert "Never invent data" in system


def test_system_prompt_injects_quiz_data(learner):
    system, messages = generate_insights_prompt(learner)
    assert "HTML Basics: 90% (1 attempt(s))" in system
    assert "CSS Selectors: 55% (2 attempt(s))" in system


def test_priority_prompt_grounds_in_learner_data(learner):
    system, messages = priority_focus_prompt(learner)
    content = messages[0]["content"]
    assert "TOP priorities for the next week" in content
    assert "grounded in the learner's actual data" in content
    assert "suggested_metric" in content


def test_priority_prompt_addressed_to_learner(learner):
    system, messages = priority_focus_prompt(learner)
    content = messages[0]["content"]
    assert "Based on Adeola's data" in content
    assert "encouraging message to Adeola" in content