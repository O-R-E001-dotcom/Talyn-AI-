"""Test configuration for the coach.

The fake Anthropic client used to be installed only in app/main.py, which
means a test that imported a service directly skipped the swap and called the
real API — 12 tests failed with a 401 whenever ANTHROPIC_API_KEY was absent.

Installing it here, before any test module is imported, fixes that: the
whole suite now runs offline with no key. Set TALYN_MOCK=0 to opt out and
exercise the real API (needs a key, and costs tokens).
"""
import os

import pytest

# Must happen before app.services.* are imported by any test module, because
# those modules capture `anthropic.Anthropic` at call time via the package
# attribute we are replacing here.
os.environ.setdefault("TALYN_MOCK", "1")

if os.getenv("TALYN_MOCK", "1").lower() in ("1", "true", "yes"):
    import anthropic

    from app.fake_anthropic import FakeAnthropic

    anthropic.Anthropic = FakeAnthropic


@pytest.fixture(scope="session", autouse=True)
def _report_mock_mode():
    """Make it obvious in the log which mode the suite ran in."""
    mode = "mock" if os.getenv("TALYN_MOCK", "1") == "1" else "live API"
    print(f"\n[coach tests] Anthropic client: {mode}")
