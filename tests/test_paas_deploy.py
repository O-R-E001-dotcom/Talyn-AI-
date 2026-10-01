"""Paas deploy shape: a backend that may be asleep when the coach calls it.

The coach's backend timeout was 5s, which is fine against a local backend and
fatal against a PaaS free tier: the backend sleeps after 15 idle minutes and
takes about a minute to wake, so every coach call made during that window
died with a 502 while both services were perfectly healthy.

Tested here with no network: httpx.get is replaced at the boundary, the same
way the other coach tests replace the Anthropic client.
"""
import httpx
import pytest

from app import backend_client
from app.backend_client import BackendError, fetch_learner_context


CONTEXT = {
    "learner_id": "1",
    "learner_name": "Demo Learner",
    "current_course": "UI/UX Design",
    "current_lesson": "Lesson 4",
    "current_topic": "Flexbox",
    "interests": ["design"],
    "difficulty_level": "beginner",
    "xp_total": 40,
    "xp_this_week": 40,
    "streak_days": 1,
    "lessons_completed": 1,
    "lessons_total": 6,
    "completion_percent": 16.7,
}


class _Response:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _Recorder:
    """Stands in for httpx.get and remembers how it was called."""

    def __init__(self):
        self.seen = {}
        self.response = _Response(200, CONTEXT)

    def __call__(self, url, headers=None, timeout=None, **kwargs):
        self.seen = {"url": url, "timeout": timeout, "headers": headers}
        return self.response


@pytest.fixture
def fake_get(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(backend_client.httpx, "get", recorder)
    return recorder


def test_default_timeout_outlasts_a_cold_backend_start():
    """A sleeping Render backend needs ~60s to wake. 5s could never cover it."""
    assert backend_client.TIMEOUT_SECONDS >= 30


def test_configured_timeout_reaches_the_request(fake_get, monkeypatch):
    """A constant nothing reads would leave the original bug in place."""
    monkeypatch.setattr(backend_client, "TIMEOUT_SECONDS", 42.0)

    fetch_learner_context("tok", backend_url="http://backend.test")

    assert fake_get.seen["timeout"] == 42.0


def test_token_is_forwarded_as_a_bearer_header(fake_get):
    fetch_learner_context("real-token", backend_url="http://backend.test")

    assert fake_get.seen["headers"] == {"Authorization": "Bearer real-token"}


def test_a_timeout_raises_backend_error_not_something_odd(monkeypatch):
    """Whatever httpx raises for a timeout must become a clean 5xx, not a
    traceback — the routers only handle BackendError."""
    def _boom(*a, **k):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(backend_client.httpx, "get", _boom)

    with pytest.raises(BackendError) as excinfo:
        fetch_learner_context("tok", backend_url="http://backend.invalid")

    assert excinfo.value.status_code == 502
    assert "backend.invalid" in str(excinfo.value)