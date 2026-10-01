# Mock mode: swap the real Anthropic client for a fake one BEFORE any service
# imports. Lets the whole API run without an ANTHROPIC_API_KEY.
from app.config import MOCK_MODE

if MOCK_MODE:
    import anthropic as _anthropic
    from app.fake_anthropic import FakeAnthropic
    _anthropic.Anthropic = FakeAnthropic

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.core.rate_limit import CoachRateLimitMiddleware
from app.routers.coach_router import router as coach_router
from app.routers.path_router import router as path_router
from app.routers.personalization_router import router as personalization_router
from app.routers.revision_router import router as revision_router
from app.routers.mission_router import router as mission_router
from app.routers.buddy_router import router as buddy_router
from app.routers.insights_router import router as insights_router

app = FastAPI(
    title="Talyn AI Learning Coach API",
    description="AI-powered coaching endpoints for the Talyn learning platform.",
    version="1.0.0",
)

# Rate limiting goes on before CORS so a rejected request still carries the
# right headers.
app.add_middleware(CoachRateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    # Explicit list, from CORS_ORIGINS. This was ["*"] behind a "tighten in
    # production" comment that survived several deploys — which is how an
    # open allowance becomes permanent. Combined with an unauthenticated
    # coach, any page could POST here and bill the Anthropic account.
    allow_origins=CORS_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(coach_router)
app.include_router(path_router)
app.include_router(personalization_router)
app.include_router(revision_router)
app.include_router(mission_router)
app.include_router(buddy_router)
app.include_router(insights_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "talyn-ai-coach"}
