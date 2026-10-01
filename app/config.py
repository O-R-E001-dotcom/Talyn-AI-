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
    return os.getenv(name, default).lower() in ("1", "true", "yes")


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
# POST to /coach/ask and bill you. Deny by default instead — an unset
# CORS_ORIGINS means no browser may call it, which is the correct reading of
# "I have not configured this yet".
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
RATE_LIMIT_PER_MINUTE = int(
    os.getenv("COACH_RATE_LIMIT_PER_MINUTE", "0" if MOCK_MODE else "30")
)
