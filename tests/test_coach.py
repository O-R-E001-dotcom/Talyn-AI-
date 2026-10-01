"""
Talyn AI Coach — Tests

Run with:
    pytest tests/test_coach.py -v

These tests call the real Claude API — set ANTHROPIC_API_KEY in your environment.
They validate structure and content quality, not exact string matches.
"""

import pytest
from app.models.schemas import (
    LearnerContext, DifficultyLevel, QuizPerformance, StudyPlan,
    ConversationMessage, AskQuestionRequest, ExplainConceptRequest,
    StudyPlanRequest, EncourageRequest, QuizRequest,
)
from app.services import coach_service


# ── Shared Fixture ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_learner() -> LearnerContext:
    return LearnerContext(
        learner_name="Adeola",
        learner_id="learner_001",
        current_course="UI/UX Design Fundamentals",
        current_lesson="Lesson 4: Layout & Spacing",
        current_topic="CSS Flexbox",
        interests=["football", "music", "technology"],
        difficulty_level=DifficultyLevel.BEGINNER,
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
        study_plan=StudyPlan(
            daily_goal_minutes=30,
            weekly_target_lessons=3,
            focus_topics=["CSS Flexbox", "Grid Layout"],
            deadline="2026-07-01",
        ),
        conversation_history=[
            ConversationMessage(role="user", content="What is the box model?"),
            ConversationMessage(
                role="assistant",
                content="Great question! The CSS box model describes how every element on a page is a rectangular box made up of content, padding, border, and margin...",
            ),
        ],
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_answer_question(sample_learner):
    result = coach_service.answer_question(
        sample_learner,
        "I don't understand justify-content vs align-items. What's the difference?"
    )
    assert result.learner_id == "learner_001"
    assert len(result.response) > 50
    # Should reference the concept from the question
    assert any(word in result.response.lower() for word in ["justify", "align", "axis", "flex"])
    print("\n[ANSWER QUESTION]\n", result.response)


def test_explain_concept(sample_learner):
    result = coach_service.explain_concept(sample_learner, "CSS Flexbox")
    assert result.learner_id == "learner_001"
    assert len(result.response) > 50
    # Should use an interest-based example
    assert any(
        interest in result.response.lower()
        for interest in ["football", "music", "technology", "game", "app"]
    )
    print("\n[EXPLAIN CONCEPT]\n", result.response)


def test_create_study_plan(sample_learner):
    result = coach_service.create_study_plan(
        sample_learner,
        "I want to become a junior UI/UX designer in 3 months"
    )
    assert result.learner_id == "learner_001"
    assert len(result.response) > 100
    # Should contain structured plan elements
    assert any(word in result.response.lower() for word in ["week", "daily", "plan", "focus"])
    print("\n[STUDY PLAN]\n", result.response)


def test_encourage_lesson_completed(sample_learner):
    result = coach_service.encourage(sample_learner, "completed lesson")
    assert result.learner_id == "learner_001"
    assert 20 < len(result.response) < 600   # Should be short but not empty
    print("\n[ENCOURAGE — lesson completed]\n", result.response)


def test_encourage_low_quiz_score(sample_learner):
    result = coach_service.encourage(sample_learner, "low quiz score on CSS Selectors — 55%")
    assert result.learner_id == "learner_001"
    assert len(result.response) > 20
    print("\n[ENCOURAGE — low score]\n", result.response)


def test_generate_quiz(sample_learner):
    result = coach_service.generate_quiz(sample_learner, "CSS Flexbox", 3)
    assert result.learner_id == "learner_001"
    assert result.topic == "CSS Flexbox"
    assert len(result.questions) == 3

    for q in result.questions:
        assert len(q.options) == 4
        assert q.correct_answer in q.options
        assert len(q.explanation) > 10

    print("\n[QUIZ]\n")
    for i, q in enumerate(result.questions, 1):
        print(f"Q{i}: {q.question}")
        for opt in q.options:
            marker = "✓" if opt == q.correct_answer else " "
            print(f"  [{marker}] {opt}")
        print(f"  Explanation: {q.explanation}\n")
