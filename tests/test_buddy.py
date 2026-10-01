"""
Talyn Study Buddy System — Prompt-level tests

These tests validate that buddy matching context (candidate pool, criteria,
icebreaker guidance) is correctly rendered into buddy prompts WITHOUT calling
any external API. No ANTHROPIC_API_KEY is required.

Run with:
    pytest tests/test_buddy.py -v
"""

import pytest
from app.models.schemas import (
    LearnerContext, DifficultyLevel, BuddyCandidate,
)
from app.prompts.coach_prompts import _build_learner_profile
from app.prompts.buddy_prompts import (
    find_buddy_prompt,
    icebreaker_prompt,
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
    )
    defaults.update(overrides)
    return LearnerContext(**defaults)


@pytest.fixture
def learner() -> LearnerContext:
    return _base_learner()


@pytest.fixture
def candidates() -> list[BuddyCandidate]:
    return [
        BuddyCandidate(
            learner_id="cand_001",
            learner_name="Tunde",
            skill_level=DifficultyLevel.BEGINNER,
            interests=["music", "technology", "football"],
            current_course="UI/UX Design Fundamentals",
            goals="Become a UI/UX designer",
            hours_per_week=5.0,
            schedule="weekday evenings",
            xp_this_week=90,
            streak_days=3,
        ),
        BuddyCandidate(
            learner_id="cand_002",
            learner_name="Grace",
            skill_level=DifficultyLevel.ADVANCED,
            interests=["gaming"],
            current_course="Data Science",
            goals="Become a data scientist",
            hours_per_week=2.0,
            schedule="sunday mornings",
            xp_this_week=10,
            streak_days=0,
        ),
    ]


def test_profile_includes_goals(learner):
    profile = _build_learner_profile(learner)
    assert "Goals:            Become a junior UI/UX designer in 3 months" in profile


def test_profile_omits_goals_when_absent():
    profile = _build_learner_profile(_base_learner(goals=None))
    assert "Goals:" not in profile


def test_system_prompt_states_criteria(learner):
    system, messages = find_buddy_prompt(learner, [])
    assert "MATCHING CRITERIA" in system
    assert "Goals alignment (30)" in system
    assert "Course / topic overlap (20)" in system
    assert "never invent candidates" in system


def test_find_buddy_prompt_contains_candidate_pool(learner, candidates):
    system, messages = find_buddy_prompt(learner, candidates)
    content = messages[0]["content"]
    assert "CANDIDATE POOL" in content
    assert "cand_001" in content
    assert "Tunde" in content
    assert "UI/UX Design Fundamentals" in content
    assert "cand_002" in content
    assert "Grace" in content


def test_find_buddy_prompt_preserves_candidate_data(learner, candidates):
    system, messages = find_buddy_prompt(learner, candidates)
    content = messages[0]["content"]
    assert "match_score is 0-100" in content
    assert "interests present in BOTH profiles" in content
    assert "return at most 2 matches" in content


def test_find_buddy_prompt_addressed_to_learner(learner, candidates):
    system, messages = find_buddy_prompt(learner, candidates)
    content = messages[0]["content"]
    assert "Find study buddies for Adeola" in content
    assert "FROM Adeola TO the top match" in content


def test_icebreaker_prompt_references_buddy_profile(learner, candidates):
    buddy = candidates[0]
    system, messages = icebreaker_prompt(learner, buddy)
    content = messages[0]["content"]
    assert "icebreaker message from Adeola to Tunde" in content
    assert "BUDDY PROFILE" in content
    assert "football" in content
    assert "under 120 words" in content


def test_icebreaker_prompt_keeps_guidelines(learner, candidates):
    buddy = candidates[1]
    system, messages = icebreaker_prompt(learner, buddy)
    content = messages[0]["content"]
    assert "ONE shared interest or shared goal" in content
    assert "Do not invent facts about either learner" in content
    assert '"message": "..."' in content