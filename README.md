# Talyn AI Learning Coach — API

FastAPI service powering the AI Learning Coach on the Talyn platform.

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run the server
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

### Mock mode (no API key needed)

```bash
# Run with canned demo responses — no ANTHROPIC_API_KEY required
$env:TALYN_MOCK = "1"          # PowerShell
uvicorn app.main:app --reload
# Open http://localhost:8000/docs and try every endpoint
```

Or run the end-to-end mock smoke test:

```bash
$env:TALYN_MOCK = "1"
python -m tests.test_mock_e2e   # all 12 endpoints return 200
```

### Backend-linked context (real learner data, no API key needed)

Every endpoint that takes a learner context (`/coach/*`, `/mission/*`,
`/buddy/*`, `/insights/*`) accepts **either** an inline `learner` object
**or** a `backend_token` (a JWT from the Talyn backend). With a token, the
coach loads the live profile from the backend (`GET {TALYN_BACKEND_URL}/v1/me/context`
for the full context, `/v1/me/path-profile`, `/v1/me/personalization-profile`,
`/v1/me/revision-profile` for the lighter profiles) — real XP, streaks, quiz
history, badges, missions, courses, and topic records instead of
caller-supplied data. Every AI endpoint (all 17 across coach, mission,
buddy, insights, path, personalization, revision) accepts `backend_token`.

```bash
# 1. Start the backend (PostgreSQL running, migrations applied, seeded)
cd ../talyn-backend
python scripts/seed.py
python -m uvicorn app.main:app --port 8000

# 2. Log in as the demo learner -> JWT
# POST /auth/login {"email":"demo@talyn.dev","password":"demo12345"}

# 3. Call the coach with the token (coach in mock mode is fine)
$env:TALYN_MOCK = "1"
# POST /coach/ask {"backend_token":"<jwt>","question":"What is contrast?"}
```

```bash
python -m pytest tests/test_backend_link.py -v   # wiring tests (mocked fetch)
```

### Prompt-level tests (no API key, no network)

```bash
python -m pytest tests/test_xp.py tests/test_mission.py tests/test_buddy.py tests/test_insights.py -v
```

---

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
### AI Learning Coach
| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/coach/ask` | Answer a learner's free-form question |
| `POST` | `/coach/explain` | Explain a concept with interest-based examples |
| `POST` | `/coach/study-plan` | Generate a personalized study plan |
| `POST` | `/coach/encourage` | Send a contextual motivational message |
| `POST` | `/coach/quiz` | Generate a multiple-choice quiz |
| `GET`  | `/health` | Health check |

### Personalized Learning Path
| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/path/generate` | Build a new path from scratch |
| `POST` | `/path/adjust` | Re-sequence a path based on a trigger reason |

### Mission-Based Learning
| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/mission/recommend` | Recommend the next quick-win mission |
| `POST` | `/mission/guide` | Guide the learner through the next mission step |

### Study Buddy System
| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/buddy/match` | Rank a candidate pool into study buddy matches |
| `POST` | `/buddy/icebreaker` | Write a first message to a chosen buddy |

### AI Insights
| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/insights/generate` | Full report: strengths, weaknesses, suggestions, forecast |
| `POST` | `/insights/priority` | Top 1-3 focus areas for the coming week |

---

## Learner Context Object

Every request body includes a `learner` object. This is the full context the AI needs.

```json
{
  "learner": {
    "learner_name": "Adeola",
    "learner_id": "learner_001",
    "current_course": "UI/UX Design Fundamentals",
    "current_lesson": "Lesson 4: Layout & Spacing",
    "current_topic": "CSS Flexbox",
    "interests": ["football", "music", "technology"],
    "difficulty_level": "beginner",
    "xp_total": 320,
    "xp_this_week": 85,
    "streak_days": 4,
    "lessons_completed": 6,
    "lessons_total": 20,
    "completion_percent": 30.0,
    "level": {
      "level": 3,
      "title": "Curious Explorer",
      "xp_this_level": 20,
      "level_up_xp": 100,
      "next_level_title": "Focused Achiever"
    },
    "badges": [
      {
        "badge_id": "badge_001",
        "name": "First Lesson Complete",
        "description": "Completed your first lesson",
        "earned_date": "2026-06-01"
      }
    ],
    "xp_breakdown": [
      {
        "activity": "lesson",
        "amount": 150,
        "earned_date": "2026-06-01"
      }
    ],
    "quiz_performance": [
      {
        "topic": "CSS Selectors",
        "score_percent": 55.0,
        "attempts": 2,
        "last_attempt_date": "2026-05-30"
      }
    ],
    "study_plan": {
      "daily_goal_minutes": 30,
      "weekly_target_lessons": 3,
      "focus_topics": ["CSS Flexbox", "Grid Layout"],
      "deadline": "2026-07-01"
    },
    "conversation_history": [
      { "role": "user", "content": "What is the box model?" },
      { "role": "assistant", "content": "The CSS box model describes..." }
    ]
  }
}
```

**`difficulty_level`** options: `"beginner"` | `"intermediate"` | `"advanced"`

**`conversation_history`**: Send the last 6–10 turns. The backend should store and manage this. Do not send the entire history of all time.

**XP Economy fields** (`level`, `badges`, `xp_breakdown`): Optional and non-blocking. When the backend implements XP tracking, it fills these in so the coach can reference levels, badges, and XP goals contextually. Until then, omit them — the coach simply won't reference XP progression.

---

## Endpoint Examples

### POST `/coach/ask`
```json
{
  "learner": { ... },
  "question": "I don't understand justify-content vs align-items. What's the difference?"
}
```

**Response:**
```json
{
  "action": "answer_question",
  "learner_id": "learner_001",
  "response": "Great question, Adeola! Think of it like a football pitch..."
}
```

---

### POST `/coach/explain`
```json
{
  "learner": { ... },
  "concept": "CSS Flexbox"
}
```

---

### POST `/coach/study-plan`
```json
{
  "learner": { ... },
  "goals": "I want to become a junior UI/UX designer in 3 months"
}
```

---

### POST `/coach/encourage`

Called by the **backend automatically** when events occur. The frontend doesn't need to call this — the backend triggers it and pushes the message to the user.

```json
{
  "learner": { ... },
  "trigger": "completed lesson"
}
```

**Trigger examples:**
- `"completed lesson"`
- `"low quiz score on CSS Flexbox — 55%"`
- `"streak at risk — hasn't studied today"`
- `"reached 50% course completion"`
- `"earned 500 XP this week"`
- `"returning after 3-day break"`

---

### POST `/coach/quiz`
```json
{
  "learner": { ... },
  "topic": "CSS Flexbox",
  "num_questions": 5
}
```

**Response:**
```json
{
  "action": "generate_quiz",
  "learner_id": "learner_001",
  "topic": "CSS Flexbox",
  "questions": [
    {
      "question": "Which property defines the direction of flex items?",
      "options": ["A. flex-wrap", "B. flex-direction", "C. align-items", "D. justify-content"],
      "correct_answer": "B. flex-direction",
      "explanation": "flex-direction sets whether items flow in a row or column."
    }
  ]
}
```

---

## Running Tests

The suite runs offline with no API key: `tests/conftest.py` installs the
fake Anthropic client before any test module is imported.

```powershell
python -m pytest tests/ -q            # 76 tests, no key, no network
python -m pytest tests/test_coach.py -v -s
```

To exercise the real API instead (costs tokens, and the assertions on
generated content can legitimately fail):

```powershell
$env:TALYN_MOCK = "0"
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python -m pytest tests/ -q
```

Mock replies are built from the prompt where the tests assert something
about the *request* — the requested question count, the learner's interests,
which courses are in the catalogue, which topics need revising. A fixed
canned reply would fail those assertions even when real Claude passes them,
which would make the mock actively misleading.

---

## Security posture

The coach holds `ANTHROPIC_API_KEY` and every call costs money, so two
things are load-bearing:

| Control | Default | Why |
|---------|---------|-----|
| Backend token required | On unless `TALYN_MOCK=1` | Without it, anyone can POST a hand-written learner context and be billed. The token path validates against the backend. |
| `CORS_ORIGINS` | `http://localhost:3000` when unset | This was `["*"]` behind a "tighten in production" comment. Combined with the gap above, any page on the internet could drive the coach. Unset now means *deny*, not *allow all*. |
| `COACH_RATE_LIMIT_PER_MINUTE` | 30 (0 in mock mode) | A learner asks a handful of questions a minute. A loop should not drain the account. |

The rate limiter is in-memory per instance. With several replicas the
effective limit is multiplied by the replica count — lower
`COACH_RATE_LIMIT_PER_MINUTE` if you scale out.

An inline `learner` is still accepted when `TALYN_MOCK=1`, because that is
how the tests and the Swagger examples work. There is no money involved and
no identity being claimed.

---

## Project Structure

```
talyn-ai-coach/
├── app/
│   ├── main.py                  # FastAPI app + CORS
│   ├── models/
│   │   └── schemas.py           # All Pydantic models
│   ├── prompts/
│   │   └── coach_prompts.py     # System prompt + all action prompts
│   ├── services/
│   │   └── coach_service.py     # Claude API calls
│   └── routers/
│       └── coach_router.py      # API endpoints
├── tests/
│   └── test_coach.py
├── requirements.txt
└── .env.example
```

**To adjust AI behavior** (tone, instructions, examples): edit `app/prompts/coach_prompts.py`.  
**To add a new endpoint**: add a schema in `schemas.py`, a prompt in `coach_prompts.py`, a function in `coach_service.py`, and a route in `coach_router.py`.

---

## Learning Path Endpoints

### POST `/path/generate`

Generates a brand-new personalized learning path.

```json
{
  "learner": {
    "learner_id": "learner_001",
    "learner_name": "Adeola",
    "skill_level": "beginner",
    "interests": ["football", "music", "technology"],
    "hours_per_week": 5.0,
    "goals": "Become a junior UI/UX designer in 3 months",
    "completed_course_ids": [],
    "available_courses": [
      {
        "course_id": "course_001",
        "title": "Design Thinking Fundamentals",
        "description": "Introduction to human-centered design.",
        "skill_level": "beginner",
        "estimated_hours": 6.0,
        "topics": ["design thinking", "empathy mapping"]
      }
    ]
  }
}
```

**Response:**
```json
{
  "action": "generate_learning_path",
  "learner_id": "learner_001",
  "summary": "Your path starts with design fundamentals and builds toward...",
  "recommended_courses": [
    {
      "order": 1,
      "course_id": "course_001",
      "title": "Design Thinking Fundamentals",
      "why_recommended": "Gives you the problem-framing mindset all UX work depends on.",
      "estimated_hours": 6.0,
      "estimated_weeks": 1.2
    }
  ],
  "milestones": [
    {
      "title": "Design Foundations Complete",
      "description": "You can apply design thinking and basic UI principles to real problems.",
      "due_week": 4
    }
  ],
  "weekly_schedule": [
    {
      "week": 1,
      "focus": "Complete Design Thinking Fundamentals — empathy mapping & problem framing",
      "course_title": "Design Thinking Fundamentals",
      "hours_recommended": 5.0
    }
  ],
  "total_estimated_weeks": 9.6
}
```

---

### POST `/path/adjust`

Re-sequences an existing path based on a reason.

```json
{
  "learner": { ... },
  "current_path_course_ids": ["course_001", "course_002", "course_003"],
  "reason": "Learner changed goal — now wants to focus on frontend development"
}
```

**Example reasons:**
- `"Learner is progressing faster than expected"`
- `"Learner is struggling and needs more foundational material first"`
- `"Learner changed goal from UI design to UX research"`
- `"Learner now has 10 hours/week instead of 5"`

---

## Mission-Based Learning Endpoints

Missions turn big courses into small, achievable "quick win" bundles. The AI
sizes each mission so the learner can finish it in one focused session and
feel immediate momentum.

### POST `/mission/recommend`

Recommend the next mission based on the learner's stage — onboarding,
in-progress, or returning after a break. New learners receive the **First
Mission** (complete profile → take assessment → start first lesson → complete
first quiz → earn first XP).

```json
{
  "learner": {
    "learner_name": "Adeola",
    "learner_id": "learner_001",
    "lessons_completed": 0,
    "lessons_total": 20,
    "completion_percent": 0.0,
    "xp_total": 0,
    "xp_this_week": 0,
    "streak_days": 0
  }
}
```

**Response:**
```json
{
  "action": "recommend_mission",
  "learner_id": "learner_001",
  "mission_title": "First Mission",
  "mission_description": "Your first few steps as a Talyn learner.",
  "purpose": "Create your first quick win and get immediate momentum.",
  "reward_xp": 100,
  "badge": null,
  "steps": [
    { "order": 1, "title": "Complete your profile", "description": "Tell Talyn your goals so it can personalise everything." },
    { "order": 2, "title": "Take the skill assessment", "description": "Answer a few questions so Talyn knows your level." },
    { "order": 3, "title": "Start your first lesson", "description": "Open your first lesson and complete it." },
    { "order": 4, "title": "Complete your first quiz", "description": "Take the quiz at the end of the lesson." },
    { "order": 5, "title": "Earn your first XP", "description": "Finish the lesson and quiz to bank your first XP." }
  ],
  "message": "Adeola, five tiny steps and you've officially started — let's go!"
}
```

### POST `/mission/guide`

Guide the learner through the **next step** of their active mission. The
request's `learner.missions.active_mission` holds the mission and which steps
are done; the AI surfaces the first incomplete step and motivates.

```json
{
  "learner": {
    "learner_name": "Adeola",
    "learner_id": "learner_001",
    "missions": {
      "active_mission": {
        "mission_id": "mission_001",
        "title": "Momentum Mission",
        "purpose": "Build a daily learning habit.",
        "reward_xp": 150,
        "status": "in_progress",
        "steps": [
          { "step_id": "s1", "title": "Finish Lesson 4", "description": "Complete the current lesson.", "order": 1, "completed": true },
          { "step_id": "s2", "title": "Take the CSS quiz", "description": "Score above 70% on the Flexbox quiz.", "order": 2, "completed": true },
          { "step_id": "s3", "title": "Complete a revision", "description": "Revise CSS Selectors.", "order": 3, "completed": false },
          { "step_id": "s4", "title": "Keep the streak", "description": "Study again tomorrow.", "order": 4, "completed": false }
        ]
      },
      "completed_mission_ids": ["mission_onboarding_001"],
      "completed_mission_count": 1
    }
  }
}
```

**Response:**
```json
{
  "action": "guide_mission",
  "learner_id": "learner_001",
  "mission_title": "Momentum Mission",
  "next_step": {
    "order": 3,
    "title": "Complete a revision",
    "description": "Revise CSS Selectors."
  },
  "message": "Nearly halfway, Adeola! Next up: a quick revision of CSS Selectors — 10 minutes, you've got this."
}
```

**When to call `/mission/recommend`:** on first onboarding, after a mission is
completed, or when a learner asks what to do next.
**When to call `/mission/guide`:** when a learner opens their active mission, or
after a step is completed to reveal the next one.

---

## Study Buddy System Endpoints

Pairs learners for accountability based on goals, courses, interests, skill
level, and study availability. Matching uses only academic/progress signals —
never personal data.

### POST `/buddy/match`

Rank a candidate pool for the learner using six weighted criteria — goals
alignment (30), course/topic overlap (20), interest overlap (20), skill level
closeness (15), time availability (10), consistency (5).

```json
{
  "learner": {
    "learner_name": "Adeola",
    "learner_id": "learner_001",
    "interests": ["football", "music", "technology"],
    "difficulty_level": "beginner",
    "goals": "Become a junior UI/UX designer in 3 months",
    "current_course": "UI/UX Design Fundamentals",
    "xp_this_week": 85,
    "streak_days": 4,
    "lessons_completed": 6,
    "lessons_total": 20
  },
  "candidates": [
    {
      "learner_id": "cand_001",
      "learner_name": "Tunde",
      "skill_level": "beginner",
      "interests": ["music", "technology", "football"],
      "current_course": "UI/UX Design Fundamentals",
      "goals": "Become a UI/UX designer",
      "hours_per_week": 5.0,
      "schedule": "weekday evenings",
      "xp_this_week": 90,
      "streak_days": 3
    }
  ]
}
```

**Response:**
```json
{
  "action": "find_buddy",
  "learner_id": "learner_001",
  "matches": [
    {
      "buddy_id": "cand_001",
      "learner_name": "Tunde",
      "match_score": 92,
      "shared_interests": ["music", "technology", "football"],
      "reasons": [
        "Same course, so you can study the exact same material together",
        "Overlapping interests make sessions more engaging",
        "Similar weekly XP and streaks — great for accountability"
      ],
      "caveat": null
    }
  ],
  "intro_message": "Hey Tunde! We're both working through UI/UX Fundamentals and into music & tech. Want to team up and keep each other on track this week?"
}
```

### POST `/buddy/icebreaker`

Write a warm, personal first message to a chosen buddy, grounded in one shared
interest or goal and suggesting one concrete next step.

```json
{
  "learner": { "learner_name": "Adeola", "learner_id": "learner_001", "...": "..." },
  "buddy": { "learner_id": "cand_001", "learner_name": "Tunde", "...": "..." }
}
```

**Response:**
```json
{
  "action": "icebreaker",
  "learner_id": "learner_001",
  "buddy_id": "cand_001",
  "buddy_name": "Tunde",
  "message": "Hey Tunde! Saw we're both grinding the UI/UX course and love tech. Want to check in on Wednesday evenings and quiz each other after each lesson?"
}
```

**When to call `/buddy/match`:** when a learner opts into the Study Buddy
System, or to refresh suggestions as learners progress.
**When to call `/buddy/icebreaker`:** when the learner picks a buddy from the
match results.

---

## AI Insights Endpoints

Turns learner data (quiz scores, XP, streaks, lessons completed, mission
progress) into honest, learner-facing insights that help continuous
improvement. Every insight is evidence-based and never shaming.

### POST `/insights/generate`

Full report with strengths, weaknesses, improvement suggestions, and a
progress forecast (with stated assumptions).

```json
{
  "learner": {
    "learner_name": "Adeola",
    "learner_id": "learner_001",
    "difficulty_level": "beginner",
    "goals": "Become a junior UI/UX designer in 3 months",
    "completion_percent": 30.0,
    "lessons_completed": 6,
    "lessons_total": 20,
    "xp_total": 320,
    "xp_this_week": 85,
    "streak_days": 4,
    "quiz_performance": [
      { "topic": "HTML Basics", "score_percent": 90.0, "attempts": 1, "last_attempt_date": "2026-05-28" },
      { "topic": "CSS Selectors", "score_percent": 55.0, "attempts": 2, "last_attempt_date": "2026-05-30" }
    ]
  }
}
```

**Response:**
```json
{
  "action": "generate_insights",
  "learner_id": "learner_001",
  "report": {
    "summary": "Adeola is off to a strong start — great HTML fundamentals and a consistent study streak. The main gap is CSS Selectors, which needs focused revision.",
    "strengths": [
      { "area": "HTML fundamentals", "detail": "Scored 90% on first attempt", "evidence": "HTML Basics quiz: 90%" }
    ],
    "weaknesses": [
      {
        "area": "CSS Selectors",
        "detail": "Scored 55% across two attempts",
        "impact": "Selectors underpin every layout task, so this will compound later",
        "evidence": "CSS Selectors quiz: 55% (2 attempts)"
      }
    ],
    "suggestions": [
      {
        "title": "Revise CSS Selectors this week",
        "description": "Run the selectors quizzes and aim for 70%+ before moving on",
        "expected_impact": "Removes the biggest risk to your course momentum"
      }
    ],
    "forecast": {
      "timeframe": "next 4 weeks",
      "projection": "On track to reach ~55% course completion if pace holds",
      "confidence_level": "medium",
      "assumptions": ["30 min/day", "Selectors gap closed within a week"]
    }
  }
}
```

### POST `/insights/priority`

The 1-3 highest-impact actions for the coming week, ordered by expected
impact, each with a success metric and a warm framing message.

```json
{
  "learner": { "...": "same LearnerContext as above" }
}
```

**Response:**
```json
{
  "action": "priority_focus",
  "learner_id": "learner_001",
  "priorities": [
    {
      "focus_area": "CSS Selectors mastery",
      "action": "Revise selectors and retake the quiz until you score 70%+",
      "rationale": "Lowest quiz score directly blocks Flexbox and layout lessons",
      "suggested_metric": "CSS Selectors quiz >= 70%"
    }
  ],
  "message": "Adeola, focus this week on one thing: getting CSS Selectors above 70%. Your 4-day streak means you're consistent — apply that to this topic and the rest flows."
}
```

**When to call `/insights/generate`:** weekly check-ins, or when a learner
opens a progress/dashboard view.
**When to call `/insights/priority`:** at the start of each week, and after
significant progress or performance changes.

---

## Project Structure

```
talyn-ai-coach/
├── app/
│   ├── main.py                    # FastAPI app + router registration
│   ├── models/
│   │   └── schemas.py             # All Pydantic models (coach + path)
│   ├── prompts/
│   │   ├── coach_prompts.py       # Coach system prompt + action prompts
│   │   └── path_prompts.py        # Path generation + adjustment prompts
│   ├── services/
│   │   ├── coach_service.py       # Claude API calls for coach
│   │   └── path_service.py        # Claude API calls for path
│   └── routers/
│       ├── coach_router.py        # /coach/* endpoints
│       └── path_router.py         # /path/* endpoints
├── tests/
│   ├── test_coach.py
│   └── test_path.py
├── requirements.txt
└── .env.example
```

**To adjust AI behavior:** edit the relevant file in `app/prompts/`.
**To add a new endpoint:** schema → prompt → service → router.
