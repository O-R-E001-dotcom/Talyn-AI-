"""
Talyn Mission-Based Learning — Prompt-level tests

These tests validate that mission context (active mission, steps, completed
missions) is correctly rendered into mission prompts WITHOUT calling any
external API. No ANTHROPIC_API_KEY is required.

Run with:
    pytest tests/test_mission.py -v
"""

import pytest
from app.models.schemas import (
    LearnerContext, DifficultyLevel, Mission, MissionStep, MissionContext,
    MissionStatus,
)
from app.prompts.coach_prompts import _build_learner_profile
from app.prompts.mission_prompts import (
    recommend_mission_prompt,
    guide_mission_prompt,
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
def new_learner() -> LearnerContext:
    """A brand-new learner with no missions — should get the First Mission."""
    return _base_learner(
        learner_name="Bola",
        learner_id="learner_002",
        xp_total=0,
        xp_this_week=0,
        streak_days=0,
        lessons_completed=0,
        lessons_total=10,
        completion_percent=0.0,
    )


@pytest.fixture
def learner_with_active_mission() -> LearnerContext:
    """A learner mid-way through a mission with 2 of 4 steps done."""
    mission = Mission(
        mission_id="mission_001",
        title="Momentum Mission",
        description="Complete three quick wins this week.",
        purpose="Build a daily learning habit.",
        reward_xp=150,
        badge=None,
        status=MissionStatus.IN_PROGRESS,
        steps=[
            MissionStep(step_id="s1", title="Finish Lesson 4", description="Complete the current lesson.", order=1, completed=True),
            MissionStep(step_id="s2", title="Take the CSS quiz", description="Score above 70% on the Flexbox quiz.", order=2, completed=True),
            MissionStep(step_id="s3", title="Complete a revision", description="Revise CSS Selectors.", order=3, completed=False),
            MissionStep(step_id="s4", title="Keep the streak", description="Study again tomorrow.", order=4, completed=False),
        ],
    )
    return _base_learner(
        missions=MissionContext(
            active_mission=mission,
            completed_mission_ids=["mission_onboarding_001"],
            completed_mission_count=1,
        )
    )


def test_profile_renders_without_missions(new_learner):
    profile = _build_learner_profile(new_learner)
    assert "Missions: Not yet tracked" in profile


def test_profile_renders_active_mission(learner_with_active_mission):
    profile = _build_learner_profile(learner_with_active_mission)
    assert "Active mission: Momentum Mission" in profile
    assert "+150 XP on completion" in profile
    assert "[x] 1. Finish Lesson 4" in profile
    assert "[ ] 3. Complete a revision" in profile


def test_recommend_prompt_suggests_first_mission_for_new_learner(new_learner):
    system, messages = recommend_mission_prompt(new_learner)
    content = messages[0]["content"]
    assert "First Mission" in content
    assert "Earn your first XP" in content
    assert "3-5 steps total" in content
    assert "Bola" in content


def test_recommend_prompt_reflects_active_mission(learner_with_active_mission):
    system, messages = recommend_mission_prompt(learner_with_active_mission)
    content = messages[0]["content"]
    assert "Active mission: Momentum Mission" in content
    assert "Missions completed so far: 1" in content


def test_recommend_prompt_uses_profile_snapshot(learner_with_active_mission):
    system, messages = recommend_mission_prompt(learner_with_active_mission)
    assert "Momentum Mission" in system  # injected via learner profile
    assert "CSS Flexbox" in system


def test_guide_prompt_identifies_first_incomplete_step(learner_with_active_mission):
    system, messages = guide_mission_prompt(learner_with_active_mission)
    content = messages[0]["content"]
    assert "ACTIVE MISSION: Momentum Mission" in content
    assert "[x] 1. Finish Lesson 4" in content
    assert "[ ] 3. Complete a revision" in content
    assert "first remaining (incomplete) step in order" in content
    assert "call /mission/recommend" in content


def test_guide_prompt_handles_no_active_mission(new_learner):
    system, messages = guide_mission_prompt(new_learner)
    content = messages[0]["content"]
    assert "No active mission" in content
    assert "request a mission recommendation" in content