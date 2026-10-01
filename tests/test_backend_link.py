"""
Tests for backend-linked learner context (the backend -> AI coach wiring).

No real backend or API key needed:
  - TALYN_MOCK=1 fakes the Anthropic client.
  - httpx is monkeypatched so no network calls happen.

Covers:
  - resolve_learner: the token wins over an inline learner, the token path
      fetches, neither source is a 401. An inline learner is accepted only in
      mock mode — see tests/test_coach_auth.py.
  - Backend payload shape validates into the coach's LearnerContext
    (contract test against the real backend /me/context shape).
  - Endpoints accept `backend_token` (200 with mocked fetch).
  - Missing both sources -> 422. Bad token -> 401. Backend down -> 502.
"""
import os

os.environ["TALYN_MOCK"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.main as m  # noqa: E402
from app import backend_client  # noqa: E402
from app.backend_client import BackendError, resolve_learner  # noqa: E402
from app.models.schemas import LearnerContext  # noqa: E402

client = TestClient(m.app)


# ── Fixture: what the real backend GET /me/context returns ───────────────────
# Mirrors talyn-backend's LearnerContextOut (verified live against the seeded
# dev DB: demo user, 1 lesson completed, 1 quiz submitted).

BACKEND_CONTEXT = {
    "learner_id": "1",
    "learner_name": "Demo Learner",
    "current_course": "",
    "current_lesson": "",
    "current_topic": "",
    "interests": ["web development", "design"],
    "difficulty_level": "beginner",
    "goals": "Get comfortable building real web projects",
    "xp_total": 40,
    "xp_this_week": 40,
    "streak_days": 1,
    "lessons_completed": 1,
    "lessons_total": 6,
    "completion_percent": 16.7,
    "quiz_performance": [
        {
            "topic": "Design Principles",
            "score_percent": 55.0,
            "attempts": 2,
            "last_attempt_date": "2026-09-25",
        }
    ],
    "level": {
        "level": 1,
        "title": "Curious Explorer",
        "xp_this_level": 40,
        "level_up_xp": 60,
        "next_level_title": "Rising Star",
    },
    "badges": [],
    "xp_breakdown": [
        {
            "activity": "quiz",
            "amount": 15,
            "note": "Quiz: Design Principles (55%)",
            "earned_date": "2026-09-25T14:00:00+00:00",
        },
        {
            "activity": "lesson",
            "amount": 25,
            "note": "Completed lesson: Design Basics: Typography",
            "earned_date": "2026-09-25T13:00:00+00:00",
        },
    ],
    "missions": None,
}


def _patch_fetch(monkeypatch, payload=None, error=None):
    """Replace the network fetch with a canned result."""
    def _fake(token, backend_url=None):
        if error is not None:
            raise error
        return LearnerContext.model_validate(payload or BACKEND_CONTEXT)

    monkeypatch.setattr(backend_client, "fetch_learner_context", _fake)


# ── resolve_learner unit tests ────────────────────────────────────────────────

def test_backend_token_wins_over_an_inline_learner(monkeypatch):
    """The token is the only proof of identity, so it must win.

    This used to be the other way round: an inline `learner` took priority,
    which meant a caller could attach a forged context to a real request and
    have the backend ignore the account entirely. See test_coach_auth.py.
    """
    def _fake(token, backend_url=None):
        assert token == "some-token"
        return LearnerContext.model_validate(BACKEND_CONTEXT)

    monkeypatch.setattr(backend_client, "fetch_learner_context", _fake)
    inline = LearnerContext.model_validate({**BACKEND_CONTEXT, "learner_id": "9"})
    out = resolve_learner(inline, backend_token="some-token")
    assert out.learner_id == "1"


def test_token_path_fetches(monkeypatch):
    _patch_fetch(monkeypatch)
    out = resolve_learner(None, backend_token="tok")
    assert out.learner_name == "Demo Learner"
    assert out.xp_total == 40


def test_neither_source_raises_401():
    """BackendError, not ValueError: the routers turn it into a 401. A bare
    ValueError escaped as an unhandled 500."""
    with pytest.raises(BackendError) as excinfo:
        resolve_learner(None, None)
    assert excinfo.value.status_code == 401
    assert "backend_token" in str(excinfo.value)


# ── Contract: backend shape validates as coach LearnerContext ────────────────

def test_backend_payload_validates_as_learner_context():
    ctx = LearnerContext.model_validate(BACKEND_CONTEXT)
    assert ctx.difficulty_level.value == "beginner"
    assert ctx.quiz_performance[0].score_percent == 55.0
    assert ctx.level.title == "Curious Explorer"
    assert ctx.xp_breakdown[0].activity.value == "quiz"
    assert ctx.missions is None


# ── Endpoints with backend_token (mocked fetch) ──────────────────────────────

def test_coach_ask_with_backend_token(monkeypatch):
    _patch_fetch(monkeypatch)
    r = client.post(
        "/coach/ask",
        json={"backend_token": "tok", "question": "What is contrast?"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["learner_id"] == "1"


def test_insights_generate_with_backend_token(monkeypatch):
    _patch_fetch(monkeypatch)
    r = client.post("/insights/generate", json={"backend_token": "tok"})
    assert r.status_code == 200, r.text
    assert "report" in r.json()


def test_mission_recommend_with_backend_token(monkeypatch):
    _patch_fetch(monkeypatch)
    r = client.post("/mission/recommend", json={"backend_token": "tok"})
    assert r.status_code == 200, r.text


def test_buddy_match_with_backend_token(monkeypatch):
    _patch_fetch(monkeypatch)
    buddy = {
        "buddy_id": "cand_002", "learner_id": "learner_002",
        "learner_name": "Tunde", "interests": ["design"],
        "current_course": "UI/UX Design Fundamentals", "skill_level": "beginner",
    }
    r = client.post(
        "/buddy/match", json={"backend_token": "tok", "candidates": [buddy]}
    )
    assert r.status_code == 200, r.text


# ── Error paths ─────────────────────────────────────────────────────────────

def test_missing_both_sources_is_422():
    r = client.post("/coach/ask", json={"question": "hi"})
    assert r.status_code == 422


def test_backend_rejects_token_is_401(monkeypatch):
    _patch_fetch(monkeypatch, error=BackendError("rejected", status_code=401))
    r = client.post("/coach/ask", json={"backend_token": "bad", "question": "hi"})
    assert r.status_code == 401


def test_backend_down_is_502(monkeypatch):
    _patch_fetch(monkeypatch, error=BackendError("unreachable"))
    r = client.post("/coach/ask", json={"backend_token": "tok", "question": "hi"})
    assert r.status_code == 502


# ── Lighter profiles via backend_token ────────────────────────────────────────
# Shapes mirror the backend's /v1/me/*-profile endpoints.

PATH_PROFILE = {
    "learner_id": "3",
    "learner_name": "Demo Learner",
    "skill_level": "beginner",
    "interests": ["design"],
    "hours_per_week": 7.0,
    "goals": "Ship projects",
    "completed_course_ids": [],
    "available_courses": [
        {
            "course_id": "1",
            "title": "Design Basics",
            "description": "d",
            "skill_level": "beginner",
            "estimated_hours": 1.0,
            "topics": ["Typography", "Color Theory"],
        }
    ],
}

PERSONALIZATION_PROFILE = {
    "learner_id": "3",
    "learner_name": "Demo Learner",
    "interests": ["design"],
    "difficulty_level": "beginner",
    "current_course": "Design Basics",
    "current_topic": "Typography",
}

REVISION_PROFILE = {
    "learner_id": "3",
    "learner_name": "Demo Learner",
    "difficulty_level": "beginner",
    "daily_study_minutes": 60,
    "topic_records": [
        {
            "topic": "Typography",
            "lesson": "Type",
            "last_studied_date": "2026-09-27",
            "days_since_studied": 0,
            "times_reviewed": 1,
            "quiz_score_percent": 70.0,
            "lesson_completed": True,
        }
    ],
    "schedule_start_date": "2026-09-27",
}


def _patch_profile(monkeypatch, name, payload):
    from app.models import schemas as S

    model = {
        "fetch_path_profile": S.LearnerPathProfile,
        "fetch_personalization_profile": S.PersonalizationProfile,
        "fetch_revision_profile": S.RevisionScheduleProfile,
    }[name]

    def _fake(token, backend_url=None):
        return model.model_validate(payload)

    monkeypatch.setattr(backend_client, name, _fake)


def test_path_generate_with_backend_token(monkeypatch):
    _patch_profile(monkeypatch, "fetch_path_profile", PATH_PROFILE)
    r = client.post("/path/generate", json={"backend_token": "tok"})
    assert r.status_code == 200, r.text
    assert r.json()["learner_id"] == "3"


def test_path_adjust_with_backend_token(monkeypatch):
    _patch_profile(monkeypatch, "fetch_path_profile", PATH_PROFILE)
    r = client.post(
        "/path/adjust",
        json={"backend_token": "tok", "current_path_course_ids": ["1"],
              "reason": "learner is ahead of schedule"},
    )
    assert r.status_code == 200, r.text


def test_personalize_with_backend_token(monkeypatch):
    _patch_profile(monkeypatch, "fetch_personalization_profile",
                   PERSONALIZATION_PROFILE)
    r = client.post(
        "/personalize/content",
        json={"backend_token": "tok", "content_type": "explanation",
              "original_content": "Contrast guides attention."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["learner_id"] == "3"


def test_revision_generate_with_backend_token(monkeypatch):
    _patch_profile(monkeypatch, "fetch_revision_profile", REVISION_PROFILE)
    r = client.post("/revision/generate", json={"backend_token": "tok"})
    assert r.status_code == 200, r.text
    assert r.json()["learner_id"] == "3"


def test_profile_missing_both_sources_is_422():
    assert client.post("/path/generate", json={}).status_code == 422
    assert client.post(
        "/personalize/content",
        json={"content_type": "explanation", "original_content": "x"},
    ).status_code == 422
    assert client.post("/revision/generate", json={}).status_code == 422


def test_profile_backend_down_is_502(monkeypatch):
    monkeypatch.setattr(
        backend_client, "fetch_path_profile",
        lambda token, backend_url=None: (_ for _ in ()).throw(
            BackendError("unreachable")),
    )
    r = client.post("/path/generate", json={"backend_token": "tok"})
    assert r.status_code == 502
