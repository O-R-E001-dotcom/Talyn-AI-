"""
Talyn — Backend client.

Lets every AI endpoint accept a backend JWT (`backend_token`) INSTEAD of a
caller-supplied learner context. The coach loads the real, current
LearnerContext from the backend:

    GET {backend_url}/v1/me/context                  -> LearnerContext
    GET {backend_url}/v1/me/path-profile             -> LearnerPathProfile
    GET {backend_url}/v1/me/personalization-profile  -> PersonalizationProfile
    GET {backend_url}/v1/me/revision-profile         -> RevisionScheduleProfile

and validates each into the coach's own schemas. The backend endpoints were
built to mirror these schemas, so validation is direct — no field mapping.

Errors surface as BackendError with an HTTP status the routers translate:
  - 401: token invalid/expired on the backend
  - 502: backend unreachable or returned an unexpected error
"""

from typing import Optional, TypeVar

import os

import httpx
from pydantic import BaseModel

from app import config
from app.models.schemas import (
    LearnerContext,
    LearnerPathProfile,
    PersonalizationProfile,
    RevisionScheduleProfile,
)

CONTEXT_PATH = "/v1/me/context"
PATH_PROFILE_PATH = "/v1/me/path-profile"
PERSONALIZATION_PROFILE_PATH = "/v1/me/personalization-profile"
REVISION_PROFILE_PATH = "/v1/me/revision-profile"

# Timeout for backend profile fetches.
#
# This was 5s, which assumed a local backend answering instantly. On a PaaS
# with a free tier the backend sleeps after 15 idle minutes and takes roughly
# a minute to wake — so every coach call made while the backend slept failed
# with a 502, even though both services were healthy. 30s covers a cold start
# while still bounding a genuinely dead backend.
#
# Backends on the same private network answer in milliseconds, so this only
# ever waits as long as it actually has to.
TIMEOUT_SECONDS = float(os.getenv("BACKEND_TIMEOUT_SECONDS", "30"))

ModelT = TypeVar("ModelT", bound=BaseModel)


class BackendError(Exception):
    """The learner context could not be loaded from the backend."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _fetch(
    token: str,
    path: str,
    model: type[ModelT],
    backend_url: Optional[str] = None,
) -> ModelT:
    """GET a backend profile path and validate it into a coach schema."""
    base = (backend_url or config.BACKEND_URL).rstrip("/")
    try:
        response = httpx.get(
            f"{base}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as e:
        raise BackendError(f"Backend unreachable at {base}: {e}") from e

    if response.status_code == 401:
        raise BackendError("Backend rejected the token (invalid or expired)", status_code=401)
    if response.status_code != 200:
        raise BackendError(
            f"Backend returned {response.status_code}: {response.text[:200]}"
        )

    try:
        return model.model_validate(response.json())
    except Exception as e:
        raise BackendError(f"Backend profile failed validation: {e}") from e


def fetch_learner_context(
    token: str,
    backend_url: Optional[str] = None,
) -> LearnerContext:
    """Load the real learner context from the backend for this token."""
    return _fetch(token, CONTEXT_PATH, LearnerContext, backend_url)


def fetch_path_profile(
    token: str,
    backend_url: Optional[str] = None,
) -> LearnerPathProfile:
    """Load the real learning-path profile from the backend."""
    return _fetch(token, PATH_PROFILE_PATH, LearnerPathProfile, backend_url)


def fetch_personalization_profile(
    token: str,
    backend_url: Optional[str] = None,
) -> PersonalizationProfile:
    """Load the real personalization profile from the backend."""
    return _fetch(token, PERSONALIZATION_PROFILE_PATH, PersonalizationProfile, backend_url)


def fetch_revision_profile(
    token: str,
    backend_url: Optional[str] = None,
) -> RevisionScheduleProfile:
    """Load the real revision profile from the backend."""
    return _fetch(token, REVISION_PROFILE_PATH, RevisionScheduleProfile, backend_url)


def resolve_learner(
    learner: Optional[LearnerContext],
    backend_token: Optional[str] = None,
    backend_url: Optional[str] = None,
) -> LearnerContext:
    """
    Return the effective learner context for a request.

    - With a backend token (the production path) the context is loaded from
      the backend, which validates the token. This is the only mode that
      proves who is asking.
    - A caller-supplied `learner` is accepted only when
      `REQUIRE_BACKEND_TOKEN` is off, i.e. in mock mode and tests. It is
      unauthenticated by nature: anyone can claim to be any learner.
    - Raises ValueError when neither source is usable.

    Why this is gated rather than left as-is: the coach is reachable from
    the browser through the web container's /coach routes, and every call
    bills the Anthropic account. Accepting an unverified self-description
    meant anyone could spend that money.
    """
    from app import config as config_module

    if backend_token:
        return fetch_learner_context(backend_token, backend_url=backend_url)

    if learner is not None and not config_module.REQUIRE_BACKEND_TOKEN:
        return learner

    if learner is not None:
        # BackendError, not ValueError: every router already catches this and
        # turns it into the right HTTP status, so the caller gets a clean 401
        # instead of a 500 from an unhandled exception.
        raise BackendError(
            "This service requires a valid backend_token. Sending a learner "
            "context directly is only accepted in mock mode.",
            status_code=401,
        )
    raise BackendError("Provide either 'learner' or 'backend_token'", status_code=401)


def resolve_profile(
    learner: Optional[ModelT],
    backend_token: Optional[str] = None,
    fetcher=None,
    backend_url: Optional[str] = None,
) -> ModelT:
    """Generic resolve_learner for the lighter profile types.

    Same token-first rule as resolve_learner — see the note there on why an
    unauthenticated caller-supplied context is not accepted in production.
    """
    from app import config as config_module

    if backend_token:
        if fetcher is None:
            raise ValueError("No backend fetcher for this profile type")
        return fetcher(backend_token, backend_url=backend_url)

    if learner is not None and not config_module.REQUIRE_BACKEND_TOKEN:
        return learner

    if learner is not None:
        # BackendError, not ValueError: every router already catches this and
        # turns it into the right HTTP status, so the caller gets a clean 401
        # instead of a 500 from an unhandled exception.
        raise BackendError(
            "This service requires a valid backend_token. Sending a learner "
            "context directly is only accepted in mock mode.",
            status_code=401,
        )
    raise BackendError("Provide either 'learner' or 'backend_token'", status_code=401)
