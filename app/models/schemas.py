from pydantic import BaseModel, Field, model_validator
from typing import Any, Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class CoachAction(str, Enum):
    ANSWER_QUESTION   = "answer_question"
    CREATE_STUDY_PLAN = "create_study_plan"
    GENERATE_QUIZ     = "generate_quiz"
    ENCOURAGE         = "encourage"
    EXPLAIN_CONCEPT   = "explain_concept"


class PathAction(str, Enum):
    GENERATE_PATH  = "generate_learning_path"
    ADJUST_PATH    = "adjust_learning_path"


class DifficultyLevel(str, Enum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"


class XpActivityType(str, Enum):
    LESSON    = "lesson"
    QUIZ      = "quiz"
    CHALLENGE = "challenge"
    LIVE      = "live_participation"
    STREAK    = "streak"
    MISSION   = "mission"
    REVISION  = "revision"


class MissionAction(str, Enum):
    RECOMMEND = "recommend_mission"
    GUIDE     = "guide_mission"


class BuddyAction(str, Enum):
    FIND_BUDDY  = "find_buddy"
    ICEBREAKER  = "icebreaker"


class InsightsAction(str, Enum):
    GENERATE = "generate_insights"
    PRIORITY = "priority_focus"


# ── Learner Context (sent by backend on every request) ───────────────────────

class QuizPerformance(BaseModel):
    topic: str
    score_percent: float          # 0–100
    attempts: int
    last_attempt_date: str        # ISO date string


class StudyPlan(BaseModel):
    daily_goal_minutes: int
    weekly_target_lessons: int
    focus_topics: list[str]
    deadline: Optional[str] = None


class ConversationMessage(BaseModel):
    role: str                     # "user" or "assistant"
    content: str


class XpEarning(BaseModel):
    """A single XP award event for the learner."""
    activity: XpActivityType
    amount: int
    earned_date: str              # ISO date string
    note: Optional[str] = None


class Badge(BaseModel):
    badge_id: str
    name: str
    description: str
    earned_date: str              # ISO date string
    icon: Optional[str] = None


class LearnerLevel(BaseModel):
    """The learner's current level and progress to the next one."""
    level: int                    # 1-based level number
    title: str                    # e.g. "Curious Explorer"
    xp_this_level: int            # XP earned within the current level
    level_up_xp: int              # XP needed to reach the next level
    next_level_title: str         # Title of the level above


class MissionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"


class MissionStep(BaseModel):
    step_id: str
    title: str
    description: str              # What the learner needs to do
    order: int                    # 1-based position in the mission
    completed: bool = False


class Mission(BaseModel):
    mission_id: str
    title: str
    description: str
    purpose: str                  # The "quick win" this mission creates
    reward_xp: int
    badge: Optional[str] = None   # Badge name earned on completion
    status: MissionStatus = MissionStatus.NOT_STARTED
    steps: list[MissionStep] = []


class MissionContext(BaseModel):
    """Optional mission state passed in by the backend for mission-based learning."""
    active_mission: Optional[Mission] = None
    completed_mission_ids: list[str] = []
    completed_mission_count: int = 0


class LearnerContext(BaseModel):
    # Identity
    learner_name: str
    learner_id: str

    # Current position
    current_course: str
    current_lesson: str
    current_topic: str

    # Personalization
    interests: list[str]
    difficulty_level: DifficultyLevel
    goals: Optional[str] = None   # What the learner wants to achieve

    # Progress
    xp_total: int
    xp_this_week: int
    streak_days: int
    lessons_completed: int
    lessons_total: int
    completion_percent: float     # 0–100

    # Performance
    quiz_performance: list[QuizPerformance] = []

    # Plan
    study_plan: Optional[StudyPlan] = None

    # Conversation history (last N turns, managed by backend)
    conversation_history: list[ConversationMessage] = []

    # XP Economy (optional — filled in by the backend once XP tracking exists)
    level: Optional[LearnerLevel] = None
    badges: list[Badge] = []
    xp_breakdown: list[XpEarning] = []

    # Mission-Based Learning (optional — filled in by the backend)
    missions: Optional[MissionContext] = None


# ── Request Bodies ────────────────────────────────────────────────────────────

class BackendLinkedRequest(BaseModel):
    """
    Base for every request that needs a learner context.

    Callers may EITHER supply the full context inline (`learner`, as before)
    OR pass a backend JWT (`backend_token`) and let the coach load the live
    context from GET {backend}/me/context. Exactly one source is required.
    """
    learner: Optional[LearnerContext] = None
    backend_token: Optional[str] = Field(
        default=None,
        description="Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object",
    )

    @model_validator(mode="after")
    def _need_one_source(self):
        if self.learner is None and not self.backend_token:
            raise ValueError("Provide either 'learner' or 'backend_token'")
        return self


def _need_profile_or_token(self):
    """Shared validator for lighter-profile requests with backend linking."""
    if self.learner is None and not self.backend_token:
        raise ValueError("Provide either 'learner' or 'backend_token'")
    return self


class BackendProfileMixin(BaseModel):
    """Adds the backend_token alternative to lighter-profile requests."""
    learner: Optional[Any] = None
    backend_token: Optional[str] = Field(
        default=None,
        description="Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object",
    )


class AskQuestionRequest(BackendLinkedRequest):
    question: str


class StudyPlanRequest(BackendLinkedRequest):
    goals: str = Field(..., description="What the learner wants to achieve")


class QuizRequest(BackendLinkedRequest):
    topic: str
    num_questions: int = Field(default=5, ge=1, le=10)


class EncourageRequest(BackendLinkedRequest):
    trigger: str = Field(
        ...,
        description="What triggered this encouragement moment, e.g. 'completed lesson', 'low quiz score', 'streak at risk'"
    )


class ExplainConceptRequest(BackendLinkedRequest):
    concept: str


# ── Response Bodies ───────────────────────────────────────────────────────────

class CoachResponse(BaseModel):
    action: CoachAction
    learner_id: str
    response: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str]            # Always 4 options
    correct_answer: str           # Must match one of the options exactly
    explanation: str


class QuizResponse(BaseModel):
    action: CoachAction = CoachAction.GENERATE_QUIZ
    learner_id: str
    topic: str
    questions: list[QuizQuestion]


# ── Learning Path Models ──────────────────────────────────────────────────────

class AvailableCourse(BaseModel):
    course_id: str
    title: str
    description: str
    skill_level: DifficultyLevel
    estimated_hours: float
    topics: list[str]


class LearnerPathProfile(BaseModel):
    """Lighter context object used specifically for path generation."""
    learner_id: str
    learner_name: str
    skill_level: DifficultyLevel
    interests: list[str]
    hours_per_week: float
    goals: str
    completed_course_ids: list[str] = []
    available_courses: list[AvailableCourse] = []


# ── Learning Path Request Bodies ──────────────────────────────────────────────

class GeneratePathRequest(BackendProfileMixin):
    learner: Optional[LearnerPathProfile] = None

    _check = model_validator(mode="after")(_need_profile_or_token)


class AdjustPathRequest(BackendProfileMixin):
    learner: Optional[LearnerPathProfile] = None
    current_path_course_ids: list[str] = Field(
        ..., description="The course IDs in the learner's current path, in order"
    )
    reason: str = Field(
        ..., description="Why the path needs adjusting, e.g. 'learner is ahead of schedule', 'learner struggling with current course', 'learner changed goals'"
    )

    _check = model_validator(mode="after")(_need_profile_or_token)


# ── Learning Path Response Bodies ─────────────────────────────────────────────

class Milestone(BaseModel):
    title: str
    description: str
    due_week: int                 # Week number from start (1-indexed)


class WeeklyScheduleEntry(BaseModel):
    week: int
    focus: str                    # Short description of what to do this week
    course_title: str
    hours_recommended: float


class RecommendedCourse(BaseModel):
    order: int                    # Position in the path (1 = first)
    course_id: str
    title: str
    why_recommended: str
    estimated_hours: float
    estimated_weeks: float        # Based on learner's hours_per_week


class LearningPathResponse(BaseModel):
    action: PathAction
    learner_id: str
    summary: str                  # 2-3 sentence overview of the path
    recommended_courses: list[RecommendedCourse]
    milestones: list[Milestone]
    weekly_schedule: list[WeeklyScheduleEntry]
    total_estimated_weeks: float


# ── Content Personalization Models ────────────────────────────────────────────

class ContentType(str, Enum):
    EXPLANATION    = "explanation"
    EXAMPLE        = "example"
    QUIZ_CONTEXT   = "quiz_context"
    EXERCISE_BRIEF = "exercise_brief"


class PersonalizationProfile(BaseModel):
    """Minimal learner profile needed for content personalization."""
    learner_id: str
    learner_name: str
    interests: list[str]
    difficulty_level: DifficultyLevel
    current_course: str
    current_topic: str


class PersonalizeContentRequest(BackendProfileMixin):
    learner: Optional[PersonalizationProfile] = None
    content_type: ContentType
    original_content: str = Field(
        ...,
        description="The original course content to be personalized — explanation, example, quiz context, or exercise brief"
    )

    _check = model_validator(mode="after")(_need_profile_or_token)


class BatchPersonalizeRequest(BackendProfileMixin):
    """Personalize multiple content pieces in one call."""
    learner: Optional[PersonalizationProfile] = None
    items: list[dict] = Field(
        ...,
        description="List of {content_type, original_content} objects to personalize in batch"
    )

    _check = model_validator(mode="after")(_need_profile_or_token)


# ── Content Personalization Response Bodies ───────────────────────────────────

class PersonalizedContentResponse(BaseModel):
    learner_id: str
    content_type: ContentType
    original_content: str
    personalized_content: str
    interest_used: str            # Which interest was woven in


class BatchPersonalizedItem(BaseModel):
    content_type: ContentType
    original_content: str
    personalized_content: str
    interest_used: str


class BatchPersonalizedResponse(BaseModel):
    learner_id: str
    items: list[BatchPersonalizedItem]


# ── Revision Schedule Models ──────────────────────────────────────────────────

class RevisionMethod(str, Enum):
    REREAD    = "re-read"
    QUIZ      = "quiz"
    FLASHCARD = "flashcard"


class TopicRecord(BaseModel):
    """The backend's knowledge of a single topic the learner has encountered."""
    topic: str
    lesson: str                        # Which lesson this topic belongs to
    last_studied_date: str             # ISO date string e.g. "2026-06-01"
    days_since_studied: int
    times_reviewed: int                # How many revision sessions completed
    quiz_score_percent: Optional[float] = None   # None if never quizzed
    lesson_completed: bool = False


class RevisionScheduleProfile(BaseModel):
    """Context object for revision schedule generation."""
    learner_id: str
    learner_name: str
    difficulty_level: DifficultyLevel
    daily_study_minutes: int           # How many minutes per day the learner has
    topic_records: list[TopicRecord]
    schedule_start_date: str           # ISO date — usually today


# ── Revision Schedule Request Bodies ─────────────────────────────────────────

class GenerateRevisionScheduleRequest(BackendProfileMixin):
    learner: Optional[RevisionScheduleProfile] = None

    _check = model_validator(mode="after")(_need_profile_or_token)


class UpdateRevisionScheduleRequest(BackendProfileMixin):
    """Called after a learner completes a revision session to refresh the schedule."""
    learner: Optional[RevisionScheduleProfile] = None
    completed_topic: str               # Topic just revised
    session_quiz_score: Optional[float] = None   # Score if a quiz was done
    current_schedule_day: int          # Which day of the 30-day schedule they're on

    _check = model_validator(mode="after")(_need_profile_or_token)


# ── Revision Schedule Response Bodies ────────────────────────────────────────

class RevisionEntry(BaseModel):
    day: int                           # Day number (1–30)
    date: str                          # ISO date string
    topic: str
    lesson: str
    method: RevisionMethod
    estimated_minutes: int
    reason: str                        # Why this topic is surfaced today


class RevisionScheduleResponse(BaseModel):
    learner_id: str
    schedule_start_date: str
    total_days: int
    summary: str                       # Brief overview of the schedule strategy
    entries: list[RevisionEntry]       # One or more entries per day, up to 30 days


# ── Mission-Based Learning Request Bodies ─────────────────────────────────────

class RecommendMissionRequest(BackendLinkedRequest):
    pass


class GuideMissionRequest(BackendLinkedRequest):
    pass


# ── Mission-Based Learning Response Bodies ────────────────────────────────────

class RecommendedMissionStep(BaseModel):
    order: int                    # 1-based position in the mission
    title: str
    description: str


class MissionRecommendationResponse(BaseModel):
    action: MissionAction = MissionAction.RECOMMEND
    learner_id: str
    mission_title: str
    mission_description: str
    purpose: str                  # The quick win this mission creates
    reward_xp: int
    badge: Optional[str] = None
    steps: list[RecommendedMissionStep]
    message: str                  # Motivational coaching message


class MissionGuidanceResponse(BaseModel):
    action: MissionAction = MissionAction.GUIDE
    learner_id: str
    mission_title: str
    next_step: RecommendedMissionStep
    message: str                  # Coaching message for this step


# ── Study Buddy Models ────────────────────────────────────────────────────────

class BuddyCandidate(BaseModel):
    """A learner in the matching pool. Only academic/progress signals — no personal data."""
    learner_id: str
    learner_name: str
    skill_level: DifficultyLevel
    interests: list[str] = []
    current_course: str = ""
    goals: str = ""
    hours_per_week: float = Field(default=0.0, ge=0)
    schedule: str = ""            # free text, e.g. "weekday evenings"
    xp_this_week: int = 0
    streak_days: int = 0


# ── Study Buddy Request Bodies ────────────────────────────────────────────────

class FindBuddyRequest(BackendLinkedRequest):
    candidates: list[BuddyCandidate] = Field(
        ...,
        description="The pool of learners the AI should rank as potential study buddies"
    )


class IcebreakerRequest(BackendLinkedRequest):
    buddy: BuddyCandidate = Field(
        ...,
        description="The buddy the learner chose to start a conversation with"
    )


# ── Study Buddy Response Bodies ───────────────────────────────────────────────

class BuddyMatch(BaseModel):
    buddy_id: str
    learner_name: str
    match_score: int              # 0-100 compatibility score
    shared_interests: list[str] = []
    reasons: list[str]
    caveat: Optional[str] = None  # Honest note about any mismatch (e.g. skill gap)


class BuddyMatchResponse(BaseModel):
    action: BuddyAction = BuddyAction.FIND_BUDDY
    learner_id: str
    matches: list[BuddyMatch]
    intro_message: str            # Opener the learner can send to the top match


class IcebreakerResponse(BaseModel):
    action: BuddyAction = BuddyAction.ICEBREAKER
    learner_id: str
    buddy_id: str
    buddy_name: str
    message: str


# ── AI Insights Models ────────────────────────────────────────────────────────

class Strength(BaseModel):
    area: str
    detail: str
    evidence: str                 # The data that supports this insight


class Weakness(BaseModel):
    area: str
    detail: str
    impact: str                   # How it holds the learner back
    evidence: str


class ImprovementSuggestion(BaseModel):
    title: str
    description: str              # Concrete next action
    expected_impact: str


class ProgressForecast(BaseModel):
    timeframe: str                # e.g. "next 4 weeks"
    projection: str
    confidence_level: str         # "high" | "medium" | "low"
    assumptions: list[str] = []


class InsightsReport(BaseModel):
    summary: str                  # 2-3 sentence overall assessment
    strengths: list[Strength]
    weaknesses: list[Weakness]
    suggestions: list[ImprovementSuggestion]
    forecast: ProgressForecast


class PriorityFocus(BaseModel):
    focus_area: str
    action: str                   # One concrete action for the week
    rationale: str                # Why this matters most right now
    suggested_metric: str         # How to measure success, e.g. "quiz >= 70%"


# ── AI Insights Request Bodies ────────────────────────────────────────────────

class GenerateInsightsRequest(BackendLinkedRequest):
    pass


class PriorityFocusRequest(BackendLinkedRequest):
    pass


# ── AI Insights Response Bodies ───────────────────────────────────────────────

class GenerateInsightsResponse(BaseModel):
    action: InsightsAction = InsightsAction.GENERATE
    learner_id: str
    report: InsightsReport


class PriorityFocusResponse(BaseModel):
    action: InsightsAction = InsightsAction.PRIORITY
    learner_id: str
    priorities: list[PriorityFocus]
    message: str                  # Short learner-facing framing of the top priority
