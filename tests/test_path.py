"""
Talyn Learning Path — Tests

Run with:
    pytest tests/test_path.py -v -s

Requires ANTHROPIC_API_KEY to be set in your environment.
"""

import pytest
from app.models.schemas import (
    LearnerPathProfile, DifficultyLevel, AvailableCourse,
    GeneratePathRequest, AdjustPathRequest,
)
from app.services import path_service


# ── Shared Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_courses() -> list[AvailableCourse]:
    return [
        AvailableCourse(
            course_id="course_001",
            title="Design Thinking Fundamentals",
            description="Introduction to human-centered design, empathy mapping, and problem framing.",
            skill_level=DifficultyLevel.BEGINNER,
            estimated_hours=6.0,
            topics=["design thinking", "empathy mapping", "problem framing"],
        ),
        AvailableCourse(
            course_id="course_002",
            title="UI Design Basics",
            description="Core principles of visual design: layout, typography, colour, and spacing.",
            skill_level=DifficultyLevel.BEGINNER,
            estimated_hours=8.0,
            topics=["layout", "typography", "colour theory", "spacing"],
        ),
        AvailableCourse(
            course_id="course_003",
            title="Figma for Beginners",
            description="Hands-on introduction to Figma — frames, components, auto-layout, and prototyping.",
            skill_level=DifficultyLevel.BEGINNER,
            estimated_hours=10.0,
            topics=["figma", "prototyping", "components", "auto-layout"],
        ),
        AvailableCourse(
            course_id="course_004",
            title="UX Research Methods",
            description="How to plan and conduct user interviews, usability tests, and surveys.",
            skill_level=DifficultyLevel.INTERMEDIATE,
            estimated_hours=8.0,
            topics=["user research", "usability testing", "interviews", "surveys"],
        ),
        AvailableCourse(
            course_id="course_005",
            title="Interaction Design Patterns",
            description="Common UI patterns, micro-interactions, and designing for usability.",
            skill_level=DifficultyLevel.INTERMEDIATE,
            estimated_hours=10.0,
            topics=["interaction design", "micro-interactions", "UI patterns"],
        ),
        AvailableCourse(
            course_id="course_006",
            title="Portfolio Building for Designers",
            description="How to select projects, write case studies, and present your work to employers.",
            skill_level=DifficultyLevel.INTERMEDIATE,
            estimated_hours=6.0,
            topics=["portfolio", "case studies", "career", "job applications"],
        ),
        AvailableCourse(
            course_id="course_007",
            title="Advanced Prototyping in Figma",
            description="Complex prototypes with variables, conditionals, and advanced component states.",
            skill_level=DifficultyLevel.ADVANCED,
            estimated_hours=12.0,
            topics=["figma", "advanced prototyping", "variables", "component states"],
        ),
        AvailableCourse(
            course_id="course_008",
            title="HTML & CSS for Designers",
            description="Frontend basics for designers who want to understand how their designs get built.",
            skill_level=DifficultyLevel.BEGINNER,
            estimated_hours=10.0,
            topics=["html", "css", "flexbox", "responsive design"],
        ),
    ]


@pytest.fixture
def beginner_learner(sample_courses) -> LearnerPathProfile:
    return LearnerPathProfile(
        learner_id="learner_001",
        learner_name="Adeola",
        skill_level=DifficultyLevel.BEGINNER,
        interests=["football", "music", "technology"],
        hours_per_week=5.0,
        goals="Become a junior UI/UX designer in 3 months and land my first design job",
        completed_course_ids=[],
        available_courses=sample_courses,
    )


@pytest.fixture
def intermediate_learner(sample_courses) -> LearnerPathProfile:
    """A learner who has already completed the beginner courses."""
    return LearnerPathProfile(
        learner_id="learner_002",
        learner_name="Tunde",
        skill_level=DifficultyLevel.INTERMEDIATE,
        interests=["gaming", "fintech", "basketball"],
        hours_per_week=8.0,
        goals="Specialise in UX research and get hired at a fintech company",
        completed_course_ids=["course_001", "course_002", "course_003"],
        available_courses=sample_courses,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_generate_path_beginner(beginner_learner):
    result = path_service.generate_path(beginner_learner)

    assert result.learner_id == "learner_001"
    assert len(result.summary) > 30
    assert len(result.recommended_courses) >= 2

    # All returned course IDs must come from the catalogue
    valid_ids = {c.course_id for c in beginner_learner.available_courses}
    for course in result.recommended_courses:
        assert course.course_id in valid_ids, f"Unknown course_id: {course.course_id}"
        assert len(course.why_recommended) > 10
        assert course.estimated_hours > 0
        assert course.estimated_weeks > 0

    # Milestones should exist and be ordered
    assert len(result.milestones) >= 1
    weeks = [m.due_week for m in result.milestones]
    assert weeks == sorted(weeks), "Milestones should be in chronological order"

    # Weekly schedule should be continuous
    assert len(result.weekly_schedule) >= 1
    week_numbers = [w.week for w in result.weekly_schedule]
    assert week_numbers == list(range(1, len(week_numbers) + 1)), \
        "Weekly schedule should be continuous from week 1"

    assert result.total_estimated_weeks > 0

    # Print for visual inspection
    print(f"\n[GENERATE PATH — Beginner]")
    print(f"Summary: {result.summary}")
    print(f"\nCourses ({len(result.recommended_courses)}):")
    for c in result.recommended_courses:
        print(f"  {c.order}. {c.title} ({c.estimated_weeks}w) — {c.why_recommended}")
    print(f"\nMilestones:")
    for m in result.milestones:
        print(f"  Week {m.due_week}: {m.title} — {m.description}")
    print(f"\nWeekly Schedule (first 4 weeks):")
    for w in result.weekly_schedule[:4]:
        print(f"  Week {w.week}: {w.focus} ({w.hours_recommended}h)")
    print(f"\nTotal: {result.total_estimated_weeks} weeks")


def test_generate_path_excludes_completed(intermediate_learner):
    result = path_service.generate_path(intermediate_learner)

    completed = set(intermediate_learner.completed_course_ids)
    returned_ids = {c.course_id for c in result.recommended_courses}

    overlap = completed & returned_ids
    assert not overlap, f"Path included already-completed courses: {overlap}"

    print(f"\n[GENERATE PATH — Intermediate, completed courses excluded correctly]")
    for c in result.recommended_courses:
        print(f"  {c.order}. {c.title}")


def test_adjust_path_goal_change(beginner_learner):
    # First generate a base path
    original = path_service.generate_path(beginner_learner)
    original_ids = [c.course_id for c in original.recommended_courses]

    # Now adjust because the learner changed goals
    result = path_service.adjust_path(
        beginner_learner,
        current_path_course_ids=original_ids,
        reason="Learner changed goal — now wants to focus on frontend development, not UI/UX design",
    )

    assert result.learner_id == "learner_001"
    assert len(result.recommended_courses) >= 1
    assert len(result.summary) > 30

    valid_ids = {c.course_id for c in beginner_learner.available_courses}
    for course in result.recommended_courses:
        assert course.course_id in valid_ids

    print(f"\n[ADJUST PATH — Goal change]")
    print(f"Original path: {[c.title for c in original.recommended_courses]}")
    print(f"Adjusted path: {[c.title for c in result.recommended_courses]}")
    print(f"Summary: {result.summary}")


def test_adjust_path_struggling(beginner_learner):
    original = path_service.generate_path(beginner_learner)
    original_ids = [c.course_id for c in original.recommended_courses]

    result = path_service.adjust_path(
        beginner_learner,
        current_path_course_ids=original_ids,
        reason="Learner is struggling with Figma and needs more foundational design theory before continuing",
    )

    assert result.learner_id == "learner_001"
    assert len(result.recommended_courses) >= 1

    print(f"\n[ADJUST PATH — Struggling learner]")
    print(f"Adjusted path: {[c.title for c in result.recommended_courses]}")
    print(f"Summary: {result.summary}")
