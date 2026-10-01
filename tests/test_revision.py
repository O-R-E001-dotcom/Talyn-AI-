
"""
Talyn Revision Schedules — Tests

Run with:
    pytest tests/test_revision.py -v -s

Requires ANTHROPIC_API_KEY to be set in your environment.
"""

import pytest
from app.models.schemas import (
    RevisionScheduleProfile, TopicRecord, DifficultyLevel, RevisionMethod,
)
from app.services import revision_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def topic_records() -> list[TopicRecord]:
    return [
        TopicRecord(
            topic="HTML Basics",
            lesson="Lesson 1: Getting Started with HTML",
            last_studied_date="2026-05-10",
            days_since_studied=45,
            times_reviewed=2,
            quiz_score_percent=88.0,
            lesson_completed=True,
        ),
        TopicRecord(
            topic="CSS Selectors",
            lesson="Lesson 2: Styling with CSS",
            last_studied_date="2026-05-20",
            days_since_studied=35,
            times_reviewed=1,
            quiz_score_percent=55.0,       # Weak — should be high priority
            lesson_completed=True,
        ),
        TopicRecord(
            topic="CSS Box Model",
            lesson="Lesson 2: Styling with CSS",
            last_studied_date="2026-05-25",
            days_since_studied=30,
            times_reviewed=1,
            quiz_score_percent=72.0,
            lesson_completed=True,
        ),
        TopicRecord(
            topic="CSS Flexbox",
            lesson="Lesson 3: Layout with Flexbox",
            last_studied_date="2026-06-10",
            days_since_studied=14,
            times_reviewed=0,
            quiz_score_percent=None,       # Never quizzed — high priority
            lesson_completed=False,
        ),
        TopicRecord(
            topic="Responsive Design",
            lesson="Lesson 4: Making Things Responsive",
            last_studied_date="2026-06-18",
            days_since_studied=6,
            times_reviewed=0,
            quiz_score_percent=None,       # Never quizzed
            lesson_completed=False,
        ),
        TopicRecord(
            topic="Typography Basics",
            lesson="Lesson 2: Styling with CSS",
            last_studied_date="2026-06-20",
            days_since_studied=4,
            times_reviewed=1,
            quiz_score_percent=91.0,       # Strong — low priority
            lesson_completed=True,
        ),
    ]


@pytest.fixture
def learner(topic_records) -> RevisionScheduleProfile:
    return RevisionScheduleProfile(
        learner_id="learner_001",
        learner_name="Adeola",
        difficulty_level=DifficultyLevel.BEGINNER,
        daily_study_minutes=30,
        topic_records=topic_records,
        schedule_start_date="2026-06-24",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_generate_schedule_structure(learner):
    result = revision_service.generate_revision_schedule(learner)

    assert result.learner_id == "learner_001"
    assert result.schedule_start_date == "2026-06-24"
    assert result.total_days == 30
    assert len(result.summary) > 30
    assert len(result.entries) > 0

    # All entries must be within day range
    for entry in result.entries:
        assert 1 <= entry.day <= 30, f"Day {entry.day} out of range"
        assert entry.topic != ""
        assert entry.lesson != ""
        assert entry.method in [m for m in RevisionMethod]
        assert 5 <= entry.estimated_minutes <= 20
        assert len(entry.reason) > 10

    print(f"\n[GENERATE SCHEDULE]")
    print(f"Summary: {result.summary}")
    print(f"Total entries: {len(result.entries)}")
    print(f"\nFirst 7 days:")
    week_one = [e for e in result.entries if e.day <= 7]
    for e in week_one:
        print(f"  Day {e.day} ({e.date}): [{e.method.value}] {e.topic} — {e.estimated_minutes}min")
        print(f"    Reason: {e.reason}")


def test_high_priority_topics_scheduled_early(learner):
    """CSS Selectors (55%) and never-quizzed topics should appear in the first 5 days."""
    result = revision_service.generate_revision_schedule(learner)

    early_entries = [e for e in result.entries if e.day <= 5]
    early_topics = {e.topic for e in early_entries}

    # At least one high-priority topic should appear early
    high_priority = {"CSS Selectors", "CSS Flexbox", "Responsive Design"}
    overlap = high_priority & early_topics
    assert len(overlap) >= 1, (
        f"Expected at least one high-priority topic in first 5 days. "
        f"Found: {early_topics}"
    )

    print(f"\n[PRIORITY CHECK] High-priority topics in first 5 days: {overlap}")


def test_daily_budget_not_exceeded(learner):
    """No single day should exceed the learner's daily_study_minutes budget."""
    result = revision_service.generate_revision_schedule(learner)

    daily_totals: dict[int, int] = {}
    for entry in result.entries:
        daily_totals[entry.day] = daily_totals.get(entry.day, 0) + entry.estimated_minutes

    violations = {
        day: total for day, total in daily_totals.items()
        if total > learner.daily_study_minutes
    }

    assert not violations, (
        f"Daily budget exceeded on days: {violations} "
        f"(budget: {learner.daily_study_minutes} min)"
    )

    print(f"\n[BUDGET CHECK] Max daily load: {max(daily_totals.values())} min "
          f"(budget: {learner.daily_study_minutes} min) ✓")


def test_all_topics_covered(learner):
    """Every topic in the learner's history should appear at least once."""
    result = revision_service.generate_revision_schedule(learner)

    scheduled_topics = {e.topic for e in result.entries}
    all_topics = {r.topic for r in learner.topic_records}

    missing = all_topics - scheduled_topics
    assert not missing, f"Topics not scheduled: {missing}"

    print(f"\n[COVERAGE CHECK] All {len(all_topics)} topics scheduled ✓")


def test_update_schedule_after_low_score(learner):
    """After a low quiz score, the topic should resurface sooner."""
    # First generate a base schedule
    original = revision_service.generate_revision_schedule(learner)

    # Simulate: learner completed Day 3, scored poorly on CSS Flexbox
    updated = revision_service.update_revision_schedule(
        learner,
        completed_topic="CSS Flexbox",
        session_quiz_score=42.0,       # Low score
        current_schedule_day=3,
    )

    assert updated.learner_id == "learner_001"
    assert len(updated.entries) > 0

    # All entries must be for days 4–30
    for entry in updated.entries:
        assert entry.day > 3, f"Updated schedule contains day {entry.day} <= 3"

    # CSS Flexbox should be rescheduled soon given the low score
    flexbox_days = [e.day for e in updated.entries if e.topic == "CSS Flexbox"]
    if flexbox_days:
        assert min(flexbox_days) <= 10, (
            f"CSS Flexbox not rescheduled soon enough after low score. "
            f"Next appearance: Day {min(flexbox_days)}"
        )

    print(f"\n[UPDATE SCHEDULE — low score on CSS Flexbox (42%)]")
    print(f"Summary: {updated.summary}")
    print(f"CSS Flexbox next appears on days: {flexbox_days}")
    print(f"Remaining entries: {len(updated.entries)}")


def test_update_schedule_after_high_score(learner):
    """After a high quiz score, the topic should be pushed back or de-prioritised."""
    original = revision_service.generate_revision_schedule(learner)

    updated = revision_service.update_revision_schedule(
        learner,
        completed_topic="CSS Selectors",
        session_quiz_score=92.0,       # High score — was previously weak
        current_schedule_day=5,
    )

    assert updated.learner_id == "learner_001"
    assert len(updated.entries) > 0

    for entry in updated.entries:
        assert entry.day > 5

    # CSS Selectors should not appear immediately after a high score
    selectors_days = [e.day for e in updated.entries if e.topic == "CSS Selectors"]
    if selectors_days:
        assert min(selectors_days) >= 10, (
            f"CSS Selectors rescheduled too soon after high score (92%). "
            f"Next appearance: Day {min(selectors_days)}"
        )

    print(f"\n[UPDATE SCHEDULE — high score on CSS Selectors (92%)]")
    print(f"Summary: {updated.summary}")
    print(f"CSS Selectors next appears on days: {selectors_days or 'not scheduled (dropped)'}")


def test_methods_match_priority(learner):
    """High-priority (low-score / unquizzed) topics should be assigned 'quiz' method."""
    result = revision_service.generate_revision_schedule(learner)

    # Find CSS Selectors entries (score 55% — should be quiz)
    selectors_entries = [e for e in result.entries if e.topic == "CSS Selectors"]
    if selectors_entries:
        first_method = selectors_entries[0].method
        assert first_method == RevisionMethod.QUIZ, (
            f"Expected 'quiz' for low-score topic CSS Selectors, got '{first_method}'"
        )

    # Find Typography entries (score 91% — should be re-read or flashcard)
    typography_entries = [e for e in result.entries if e.topic == "Typography Basics"]
    if typography_entries:
        first_method = typography_entries[0].method
        assert first_method in [RevisionMethod.REREAD, RevisionMethod.FLASHCARD], (
            f"Expected lighter method for high-score topic Typography Basics, got '{first_method}'"
        )

    print(f"\n[METHOD CHECK]")
    for e in result.entries[:8]:
        print(f"  Day {e.day}: {e.topic} → {e.method.value}")
