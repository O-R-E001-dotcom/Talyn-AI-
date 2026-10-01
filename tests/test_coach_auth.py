"""The coach is the one endpoint where an abusive caller costs real money.

Two holes are covered here, both of which existed long enough to be mistaken
for intended behaviour:

  1. A caller could POST a hand-written learner context with no token at all
     and get an answer. Nothing proved who they were.
  2. CORS was `*`, so any page on the internet could make the browser do it.
"""
import pytest
from fastapi.testclient import TestClient

from app import config as config_module
from app.backend_client import BackendError, resolve_learner, resolve_profile


LEARNER = {
    "learner_id": "learner_001",
    "learner_name": "Adeola",
    "current_course": "UI/UX Design",
    "current_lesson": "Lesson 4: Layout & Spacing",
    "current_topic": "CSS Flexbox",
    "interests": ["football"],
    "difficulty_level": "beginner",
    "xp_total": 320,
    "xp_this_week": 85,
    "streak_days": 4,
    "lessons_completed": 6,
    "lessons_total": 20,
    "completion_percent": 30.0,
}


# ── Token enforcement ────────────────────────────────────────────────────────


def test_caller_supplied_context_is_rejected_without_a_token(monkeypatch):
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", True)

    with pytest.raises(BackendError) as excinfo:
        resolve_learner(LEARNER, None)

    # 401, not 500: every router already maps BackendError to its status.
    assert excinfo.value.status_code == 401
    assert "backend_token" in str(excinfo.value)


def test_caller_supplied_context_still_works_in_mock_mode(monkeypatch):
    """Tests, Swagger demos and the README examples depend on this."""
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", False)

    assert resolve_learner(LEARNER, None)["learner_id"] == "learner_001"


def test_neither_source_is_a_401_not_a_500(monkeypatch):
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", True)

    with pytest.raises(BackendError) as excinfo:
        resolve_learner(None, None)

    assert excinfo.value.status_code == 401


def test_a_token_is_preferred_over_a_caller_supplied_context(monkeypatch):
    """Otherwise a caller could pass a token *and* a fabricated context, and
    the fabricated one would win — making the token pointless."""
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", True)

    calls = []

    def fake_fetch(token, backend_url=None):
        calls.append(token)
        return {"learner_id": "from-backend"}

    monkeypatch.setattr(
        "app.backend_client.fetch_learner_context", fake_fetch
    )

    result = resolve_learner(LEARNER, "real-token")

    assert calls == ["real-token"]
    assert result["learner_id"] == "from-backend"


def test_resolve_profile_enforces_the_same_rule(monkeypatch):
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", True)

    with pytest.raises(BackendError) as excinfo:
        resolve_profile(LEARNER, None, fetcher=lambda *a, **k: {})

    assert excinfo.value.status_code == 401


# ── End to end ───────────────────────────────────────────────────────────────


def test_endpoint_returns_401_for_an_unauthenticated_call(monkeypatch):
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", True)
    from app.main import app

    with TestClient(app) as client:
        r = client.post("/coach/ask", json={"learner": LEARNER,
                                            "question": "What is flexbox?"})
    assert r.status_code == 401
    assert "backend_token" in r.json()["detail"]


def test_endpoint_rejects_a_bogus_token(monkeypatch):
    """An invalid token must not fall through to the caller-supplied path."""
    monkeypatch.setattr(config_module, "REQUIRE_BACKEND_TOKEN", True)

    def refuse(token, backend_url=None):
        raise BackendError("Unauthorized", status_code=401)

    monkeypatch.setattr("app.backend_client.fetch_learner_context", refuse)
    from app.main import app

    with TestClient(app) as client:
        r = client.post("/coach/ask", json={
            "learner": LEARNER, "backend_token": "forged", "question": "hi",
        })
    assert r.status_code == 401


def test_health_is_not_rate_limited():
    """A load balancer polls health; a limiter would eventually 429 it and
    take the container out of rotation."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from app.core.rate_limit import CoachRateLimitMiddleware

    async def health(_request):
        return JSONResponse({"status": "ok"})

    probe = Starlette(routes=[Route("/health", health)])
    probe.add_middleware(CoachRateLimitMiddleware, limit=1)

    with TestClient(probe) as client:
        for _ in range(5):
            assert client.get("/health").status_code == 200


def test_repeated_calls_are_rate_limited():
    """The budget that blunts a loop against the Anthropic account."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from app.core.rate_limit import CoachRateLimitMiddleware

    async def coach(_request):
        return JSONResponse({"ok": True})

    probe = Starlette(routes=[Route("/coach/ask", coach, methods=["POST"])])
    probe.add_middleware(CoachRateLimitMiddleware, limit=3)

    with TestClient(probe) as client:
        assert [client.post("/coach/ask").status_code for _ in range(5)] == [
            200, 200, 200, 429, 429,
        ]


# ── CORS ─────────────────────────────────────────────────────────────────────


def test_cors_is_not_wildcard():
    from app.main import app

    origins = [
        o for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"
        for o in m.kwargs.get("allow_origins", [])
    ]
    assert "*" not in origins, (
        "wildcard CORS lets any page drive the coach and bill the account"
    )


def test_cors_defaults_to_deny_when_unset(monkeypatch):
    """An unconfigured CORS_ORIGINS must mean 'no browser may call this',
    not 'every browser may call this'."""
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    origins = config_module._origins()
    assert origins == []
    assert (origins or ["http://localhost:3000"]) == ["http://localhost:3000"]
