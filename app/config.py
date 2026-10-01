"""
Talyn — App Configuration

MOCK_MODE lets you run every endpoint with canned demo responses instead of
calling the real Claude API. Enable with the TALYN_MOCK environment variable:

    $env:TALYN_MOCK = "1"
    uvicorn app.main:app --reload

No ANTHROPIC_API_KEY is needed while MOCK_MODE is on.
"""

import os


def _flag(name: str, default: str = "0") -> bool:
    """Read a boolean env var, treating blank as "not provided".

    This matters more than it looks. PaaS dashboards express "no opinion"
    by leaving a variable empty rather than deleting it, and os.getenv's
    default only applies to a genuinely *unset* variable — an empty string
    sails straight past it and then reads as false.

    That is how TALYN_REQUIRE_TOKEN ended up disabled in production: the
    Blueprint said "leave empty to get the safe default", and empty is
    exactly what turned it off. For a security flag, blank must mean "use
    the default", never "off".
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        raw = default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    """Read an int env var, falling back on blank or unparseable values.

    int("") raises at import, which would take the whole service down
    because someone cleared a field in a dashboard.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


MOCK_MODE = _flag("TALYN_MOCK")

# Where the Talyn backend (auth, courses, XP ledger) lives. Used only when a
# caller passes `backend_token` instead of a full learner context — the coach
# then loads the real LearnerContext from GET {BACKEND_URL}/me/context.
BACKEND_URL = os.getenv("TALYN_BACKEND_URL", "http://localhost:8000").rstrip("/")


def _origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


# Origins allowed to call the coach from a browser.
#
# This was ["*"] with a "tighten in production" comment. That comment sat
# through several deploys, which is exactly how an allowance like that
# becomes permanent. The coach holds ANTHROPIC_API_KEY and every call costs
# money, so an open CORS is an open wallet: any page on the internet could
# POST to /coach/ask and bill you. Unset therefore falls back to localhost
# only — the narrowest allowance that still lets local development work. It is
# not "deny": an earlier comment here claimed it was, which was wrong, and a
# comment that misdescribes a security control is worse than none.
CORS_ORIGINS = _origins() or ["http://localhost:3000"]

# Require a valid backend token on every coach call.
#
# Without this, any caller can POST a hand-written learner context and get an
# answer — no account, no session, no proof of anything. The token path
# validates against the backend, so requiring it is what makes the coach cost
# attributable and the rate limit meaningful.
#
# Mock mode keeps accepting caller-supplied contexts: that is how the tests
# and the README examples work, and there is no real money involved.
REQUIRE_BACKEND_TOKEN = _flag("TALYN_REQUIRE_TOKEN", "0" if MOCK_MODE else "1")

# Per-IP budget for coach calls (60s window). Generous for a learner asking
# a handful of questions, low enough that a loop cannot drain the account.
# Set to 0 to disable (the test suite does; ~80 endpoint calls from one IP
# would otherwise trip it).
RATE_LIMIT_PER_MINUTE = _int(
    "COACH_RATE_LIMIT_PER_MINUTE", 0 if MOCK_MODE else 30
)
