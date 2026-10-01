"""
Talyn XP Economy — Prompt-level tests

These tests validate that the XP Economy context (level, badges, XP breakdown)
is correctly rendered into coach prompts WITHOUT calling any external API.
No ANTHROPIC_API_KEY is required.

Run with:
    pytest tests/test_xp.py -v
"""

import pytest
from app.models.schemas import (
    LearnerContext, DifficultyLevel, XpActivityType, XpEarning,
    Badge, LearnerLevel,
)
from app.prompts.coach_prompts import (
    _build_learner_profile,
    _build_system_prompt,
    encourage_prompt,
    create_study_plan_prompt,
)

LEVEL_UP_XP = 100


@pytest.fixture
def xp_learner() -> LearnerContext:
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
        level=LearnerLevel(
            level=3,
            title="Curious Explorer",
            xp_this_level=20,
            level_up_xp=LEVEL_UP_XP,
            next_level_title="Focused Achiever",
        ),
        badges=[
            Badge(
                badge_id="badge_001",
                name="First Lesson Complete",
                description="Completed your first lesson",
                earned_date="2026-06-01",
            ),
        ],
        xp_breakdown=[
            XpEarning(activity=XpActivityType.LESSON, amount=150, earned_date="2026-06-01"),
            XpEarning(activity=XpActivityType.QUIZ, amount=120, earned_date="2026-06-05"),
            XpEarning(activity=XpActivityType.STREAK, amount=50, earned_date="2026-06-07"),
        ],
    )


@pytest.fixture
def bare_learner() -> LearnerContext:
    """A learner with no XP Economy data — prompts must still render cleanly."""
    return LearnerContext(
        learner_name="Bola",
        learner_id="learner_002",
        current_course="Intro to Programming",
        current_lesson="Lesson 1: Getting Started",
        current_topic="Variables",
        interests=["food", "music"],
        difficulty_level=DifficultyLevel.BEGINNER,
        xp_total=0,
        xp_this_week=0,
        streak_days=0,
        lessons_completed=0,
        lessons_total=10,
        completion_percent=0.0,
    )


def test_profile_contains_level(xp_learner):
    profile = _build_learner_profile(xp_learner)
    assert "Level:" in profile
    assert "Curious Explorer" in profile
    assert "Focused Achiever" in profile


def test_profile_contains_badges(xp_learner):
    profile = _build_learner_profile(xp_learner)
    assert "Badges earned:" in profile
    assert "First Lesson Complete" in profile


def test_profile_contains_xp_breakdown(xp_learner):
    profile = _build_learner_profile(xp_learner)
    assert "XP by activity" in profile
    assert "lesson: 150 XP" in profile
    assert "quiz: 120 XP" in profile
    assert "streak: 50 XP" in profile


def test_profile_renders_without_xp_data(bare_learner):
    profile = _build_learner_profile(bare_learner)
    assert "Not yet assigned" in profile
    assert "Badges earned: None yet" in profile
    assert "XP by activity: Not yet tracked" in profile


def test_system_prompt_injects_xp_profile(xp_learner):
    system = _build_system_prompt(xp_learner)
    assert "Curious Explorer" in system
    assert "First Lesson Complete" in system


def test_encourage_prompt_references_level_progress(xp_learner):
    system, messages = encourage_prompt(xp_learner, "completed lesson")
    expected_remaining = LEVEL_UP_XP - xp_learner.level.xp_this_level
    assert f"{expected_remaining} XP away from" in messages[0]["content"]
    assert "Focused Achiever" in messages[0]["content"]
    assert "earn more XP" in messages[0]["content"]


def test_encourage_prompt_works_without_level(bare_learner):
    system, messages = encourage_prompt(bare_learner, "first lesson done")
    assert "Adeola" not in messages[0]["content"]
    assert "Bola" in messages[0]["content"]


def test_study_plan_prompt_includes_xp_goals(xp_learner):
    system, messages = create_study_plan_prompt(
        xp_learner,
        "I want to become a junior UI/UX designer in 3 months",
    )
    content = messages[0]["content"]
    assert "320 XP total" in content
    assert "85 XP this week" in content
    assert "XP goals" in content