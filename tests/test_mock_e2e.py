"""
End-to-end smoke test for MOCK_MODE — verifies every endpoint returns
valid data with NO API key and NO network calls.

Run with:
    python -m tests.test_mock_e2e
"""
import os
os.environ["TALYN_MOCK"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
import app.main as m  # noqa: E402

client = TestClient(m.app)


def L(**kw):
    base = dict(
        learner_name="Adeola", learner_id="learner_001",
        current_course="UI/UX Design Fundamentals",
        current_lesson="Lesson 4: Layout & Spacing",
        current_topic="CSS Flexbox",
        interests=["football", "music", "technology"],
        difficulty_level="beginner",
        goals="Become a junior UI/UX designer",
        xp_total=320, xp_this_week=85, streak_days=4,
        lessons_completed=6, lessons_total=20, completion_percent=30.0,
        quiz_performance=[
            {"topic": "HTML Basics", "score_percent": 90.0,
             "attempts": 1, "last_attempt_date": "2026-05-28"},
            {"topic": "CSS Selectors", "score_percent": 55.0,
             "attempts": 2, "last_attempt_date": "2026-05-30"},
        ],
    )
    base.update(kw)
    return base


BUDDY = dict(
    buddy_id="cand_002", learner_id="learner_002", learner_name="Tunde",
    interests=["football", "technology"],
    current_course="UI/UX Design Fundamentals",
    skill_level="beginner",
)

REVISION_PROFILE = dict(
    learner_id="learner_001", learner_name="Adeola",
    difficulty_level="beginner", daily_study_minutes=25,
    topic_records=[
        {"topic": "HTML Basics",   "lesson": "Lesson 1", "last_studied_date": "2026-05-28", "days_since_studied": 14, "times_reviewed": 2, "quiz_score_percent": 90.0, "lesson_completed": True},
        {"topic": "CSS Selectors", "lesson": "Lesson 3", "last_studied_date": "2026-05-30", "days_since_studied": 12, "times_reviewed": 0, "quiz_score_percent": 55.0, "lesson_completed": False},
    ],
    schedule_start_date="2026-06-10",
)

PATH_PROFILE = dict(
    learner_id="learner_001", learner_name="Adeola",
    skill_level="beginner", interests=["football", "music", "technology"],
    hours_per_week=5.0, goals="Become a junior UI/UX designer",
    completed_course_ids=[], available_courses=[],
)


CHECKS = [
    ("health",        lambda: client.get("/health")),
    ("quiz",          lambda: client.post("/coach/quiz",        json={"learner": L(), "topic": "CSS Flexbox", "question_count": 2})),
    ("encourage",     lambda: client.post("/coach/encourage",   json={"learner": L(), "trigger": "4-day streak reached"})),
    ("mission rec",   lambda: client.post("/mission/recommend", json={"learner": L()})),
    ("mission guide", lambda: client.post("/mission/guide",    json={"learner": L(), "current_mission": None})),
    ("buddy match",   lambda: client.post("/buddy/match",      json={"learner": L(), "candidates": [BUDDY], "max_matches": 2})),
    ("icebreaker",    lambda: client.post("/buddy/icebreaker",  json={"learner": L(), "buddy": BUDDY})),
    ("insights gen",  lambda: client.post("/insights/generate", json={"learner": L()})),
    ("insights pri",  lambda: client.post("/insights/priority", json={"learner": L()})),
    ("revision",      lambda: client.post("/revision/generate", json={"learner": REVISION_PROFILE})),
    ("path generate", lambda: client.post("/path/generate",    json={"learner": PATH_PROFILE})),
    ("personalize",   lambda: client.post("/personalize/content", json={"learner": L(), "content_type": "explanation", "original_content": "Explain CSS"})),
]


def _summarise(name: str, j: dict) -> str:
    if name == "health":
        return j.get("status")
    if name == "quiz":
        return f"questions={len(j.get('questions', []))}"
    if name == "buddy match":
        m = j.get("matches", [])
        return f"matches={len(m)}, top={m[0]['learner_name'] if m else 'none'}"
    if name == "insights gen":
        rpt = j.get("report", {})
        return f"strengths={len(rpt.get('strengths', []))}, forecast={rpt.get('forecast', {}).get('confidence_level')}"
    if name == "insights pri":
        return f"priorities={len(j.get('priorities', []))}"
    if name == "revision":
        return f"entries={len(j.get('entries', []))}"
    if name == "path generate":
        return f"courses={len(j.get('recommended_courses', []))}"
    return str(j.get("action") or j.get("response", ""))[:40]


def test_mock_endpoints_return_200():
    failures = []
    for name, fn in CHECKS:
        r = fn()
        if r.status_code != 200:
            failures.append(f"{name}: {r.status_code} {r.text[:100]}")
    assert not failures, "\n".join(failures)


def test_mock_buddy_match_has_matches():
    r = client.post("/buddy/match", json={"learner": L(), "candidates": [BUDDY], "max_matches": 2})
    assert r.status_code == 200
    data = r.json()
    assert len(data["matches"]) >= 1
    assert data["matches"][0]["learner_name"] == "Tunde"


def test_mock_insights_generate_has_report():
    r = client.post("/insights/generate", json={"learner": L()})
    assert r.status_code == 200
    report = r.json()["report"]
    assert len(report["strengths"]) >= 1
    assert len(report["weaknesses"]) >= 1
    assert "forecast" in report


def test_mock_quiz_returns_questions():
    # Field is num_questions, not question_count. Passing the wrong name was
    # silently ignored and the default of 5 applied, so this test only ever
    # passed because the canned payload happened to contain 2 questions.
    r = client.post("/coach/quiz", json={"learner": L(), "topic": "CSS Flexbox", "num_questions": 3})
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 3


def test_mock_revision_has_entries():
    r = client.post("/revision/generate", json={"learner": REVISION_PROFILE})
    assert r.status_code == 200
    assert len(r.json()["entries"]) >= 1


def test_mock_path_generate_has_courses():
    r = client.post("/path/generate", json={"learner": PATH_PROFILE})
    assert r.status_code == 200
    assert len(r.json()["recommended_courses"]) >= 1


def main():
    print(f"{'Endpoint':16s} {'Status':6s} Summary")
    print("-" * 72)
    all_pass = True
    for name, fn in CHECKS:
        r = fn()
        if r.status_code == 200:
            print(f"{name:16s} 200    {_summarise(name, r.json())}")
        else:
            all_pass = False
            detail = r.json().get("detail", r.text)
            print(f"{name:16s} {r.status_code}    FAIL: {str(detail)[:50]}")
    print("-" * 72)
    print(f"\n{'ALL OK' if all_pass else 'SOME FAILED'}")


if __name__ == "__main__":
    main()
