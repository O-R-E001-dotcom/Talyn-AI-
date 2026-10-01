"""
Talyn — Fake Anthropic client (MOCK_MODE)

Replaces anthropic.Anthropic so every endpoint returns schema-valid demo
responses. Used when TALYN_MOCK=1 (see app/config.py), so you can exercise
the API from Swagger UI and run the test suite without an
ANTHROPIC_API_KEY or network access.

Two kinds of payload:

  * Static  — fixed text good enough for manual demos (encourage, insights,
              buddies, missions, study plans).
  * Dynamic — built from the prompt, for anything a test asserts *about the
              request*: how many questions were asked, which interests the
              learner has, which courses are actually in the catalogue, which
              topics need revising.

The dynamic ones matter more than they look. A static reply cannot answer
"generate a 3-question quiz" with three questions, or recommend a course
that isn't in the catalogue, so tests asserting those guarantees would fail
against the mock even though real Claude would pass them. Returning something
derived from the prompt keeps mock-mode coverage meaningful.
"""

import json
import re
from types import SimpleNamespace


# ── Canned payloads (raw, JSON already parsed) ───────────────────────────────

_ANSWER_QUESTION = (
    "Great question! In Flexbox, `justify-content` aligns items along the "
    "main axis — `flex-start` packs them to the start, `center` centres them, "
    "and `space-between` pushes the first and last items to the edges. "
    "Try `justify-content: space-between` on your nav and you'll see the links "
    "spread evenly."
)

_EXPLAIN = _ANSWER_QUESTION  # same structure, fine for demo

_STUDY_PLAN = (
    "Adeola, here's your plan for the next 7 days:\n"
    "- Days 1-2: Revisit CSS Selectors (your weakest quiz: 55%). Aim for 70%+.\n"
    "- Days 3-4: Complete Lesson 5 on Flexbox layout.\n"
    "- Days 5-6: Practice with 2 quizzes + build the course mini-project.\n"
    "- Day 7: Revision + weekly quiz to close the week above 75%.\n"
    "You're on a 4-day streak — keep it going!"
)

_ENCOURAGE = (
    "Adeola, fantastic work out there — a 4-day streak shows serious "
    "consistency. You've already banked 320 XP this month. Keep showing up, "
    "even for 15 minutes, and you'll hit your 3-month goal faster than you "
    "think."
)

_QUIZ = {
    "questions": [
        {
            "question": "Which property controls whether flex items wrap to a new line?",
            "options": ["A. flex-direction", "B. flex-wrap", "C. align-items", "D. justify-content"],
            "correct_answer": "B. flex-wrap",
            "explanation": "flex-wrap: wrap lets items flow onto additional lines when they run out of space.",
        },
        {
            "question": "justify-content: space-between arranges items how?",
            "options": ["A. All items centred", "B. Gaps between all items equal", "C. First and last items at edges, equal gaps between", "D. Items stacked vertically"],
            "correct_answer": "C. First and last items at edges, equal gaps between",
            "explanation": "space-between puts the first and last items flush to the edges and distributes the rest evenly.",
        },
    ]
}

_PATH_GENERATE = {
    "action": "generate_path",
    "learner_id": "learner_001",
    "summary": "Four-week path to UI/UX fundamentals, balanced with your 30%-completion pace.",
    "recommended_courses": [
        {
            "order": 1,
            "course_id": "course_10",
            "title": "Responsive Layouts with Flexbox",
            "why_recommended": "Directly targets your current lesson and your CSS Selectors gap.",
            "estimated_hours": 8,
            "estimated_weeks": 2,
        },
        {
            "order": 2,
            "course_id": "course_11",
            "title": "UI Design Principles",
            "why_recommended": "Matches your goal of becoming a junior UI/UX designer.",
            "estimated_hours": 10,
            "estimated_weeks": 2,
        },
    ],
    "milestones": [
        {"title": "Selectors milestone", "description": "Score 70%+ on CSS Selectors quizzes", "due_week": 1},
        {"title": "Flexbox milestone", "description": "Finish the Flexbox course with a passing quiz", "due_week": 2},
        {"title": "UI principles", "description": "Complete UI Design module 1 + mini-project", "due_week": 3},
        {"title": "Capstone", "description": "Submit a full landing page using flex layouts", "due_week": 4},
    ],
    "weekly_schedule": [
        {"week": 1, "focus": "Selectors + flex basics", "course_title": "Responsive Layouts with Flexbox", "hours_recommended": 5},
        {"week": 2, "focus": "Flexbox practice + quizzes", "course_title": "Responsive Layouts with Flexbox", "hours_recommended": 5},
        {"week": 3, "focus": "UI principles + project", "course_title": "UI Design Principles", "hours_recommended": 6},
        {"week": 4, "focus": "Capstone landing page", "course_title": "UI Design Principles", "hours_recommended": 6},
    ],
    "total_estimated_weeks": 4,
}

_PATH_ADJUST = {
    "action": "adjust_path",
    "learner_id": "learner_001",
    "summary": "Path adjusted: extra week on selectors because your retake scored 65% (still below 70%).",
    "recommended_courses": _PATH_GENERATE["recommended_courses"],
    "milestones": [
        {"title": "Selectors mastery", "description": "Score 70%+ on a fresh Selectors quiz", "due_week": 1},
        {"title": "Flexbox course", "description": "Finish the Flexbox course", "due_week": 2},
        {"title": "UI design", "description": "UI Design module 1 + mini-project", "due_week": 3},
        {"title": "Capstone", "description": "Capstone landing page", "due_week": 4},
    ],
    "weekly_schedule": [
        {"week": 1, "focus": "Selectors mastery", "course_title": "Responsive Layouts with Flexbox", "hours_recommended": 6},
        {"week": 2, "focus": "Flexbox + quizzes", "course_title": "Responsive Layouts with Flexbox", "hours_recommended": 5},
        {"week": 3, "focus": "UI principles", "course_title": "UI Design Principles", "hours_recommended": 6},
        {"week": 4, "focus": "Capstone", "course_title": "UI Design Principles", "hours_recommended": 6},
    ],
    "total_estimated_weeks": 4,
}

_PERSONALIZE = {
    "personalized_content": (
        "Think of CSS selectors like picking your starting lineup in football: "
        "`.nav a` selects every link in the nav (your attackers), "
        "`#header` grabs exactly the header (your captain). Specific selectors "
        "mean each element gets the right role — no substitutions required!"
    ),
    "interest_used": "football",
}

_BATCH = [
    {"content_type": "explanation", "original_content": "Explain CSS selectors", "personalized_content": _PERSONALIZE["personalized_content"], "interest_used": "football"},
    {"content_type": "example", "original_content": "Show a dropdown example", "personalized_content": "Your football app's team shortlist is a dropdown: hide the list, reveal it on click — same pattern as selectors.", "interest_used": "football"},
]

_REVISION_GENERATE = {
    "summary": "30-day revision plan prioritising CSS Selectors and layout.",
    "entries": [
        {"day": 1, "date": "2026-09-10", "topic": "CSS Selectors", "lesson": "Lesson 3", "method": "quiz", "estimated_minutes": 15, "reason": "Lowest quiz score (55%) — revisiting first while fresh."},
        {"day": 2, "date": "2026-09-11", "topic": "HTML Basics", "lesson": "Lesson 1", "method": "flashcard", "estimated_minutes": 10, "reason": "Strong topic, quick recall keeps it strong."},
        {"day": 3, "date": "2026-09-12", "topic": "CSS Selectors", "lesson": "Lesson 3", "method": "re-read", "estimated_minutes": 10, "reason": "Second pass within the week to lock it in."},
        {"day": 4, "date": "2026-09-13", "topic": "CSS Flexbox", "lesson": "Lesson 4", "method": "quiz", "estimated_minutes": 15, "reason": "Current lesson — test as you learn."},
    ],
}

_REVISION_UPDATE = {
    "summary": "Day 3 logged. CSS Selectors still flagged — extends focus by one day.",
    "entries": [
        {"day": 4, "date": "2026-09-13", "topic": "CSS Selectors", "lesson": "Lesson 3", "method": "quiz", "estimated_minutes": 15, "reason": "Retake scored 65%, still below 70% target."},
        {"day": 5, "date": "2026-09-14", "topic": "CSS Flexbox", "lesson": "Lesson 4", "method": "quiz", "estimated_minutes": 15, "reason": "Back on schedule with the current lesson."},
    ],
}

_MISSION_RECOMMEND = {
    "mission_title": "Flexbox Field Marshal",
    "mission_description": "Master CSS Selectors and flex layout over the next 4 sessions.",
    "purpose": "Closes your weakest area (Selectors at 55%) before it blocks later lessons.",
    "reward_xp": 150,
    "badge": "Layout Commander",
    "steps": [
        {"order": 1, "title": "Selector sweep", "description": "Retake the Selectors quiz and reach 70%+."},
        {"order": 2, "title": "Flex line-up", "description": "Complete Lesson 4: Layout & Spacing."},
        {"order": 3, "title": "Championship build", "description": "Build a 3-column card layout with Flexbox."},
    ],
    "message": "Adeola, this mission turns your trickiest topic into a win — 4 sessions, 150 XP, and a badge on your profile.",
}

_MISSION_GUIDE = {
    "mission_title": "Flexbox Field Marshal",
    "next_step": {"order": 2, "title": "Flex line-up", "description": "Complete Lesson 4: Layout & Spacing."},
    "message": "Nice work locking in the 70% target with a retake. Next up, finish Lesson 4 — you're 2 sessions from earning the Layout Commander badge.",
}

_BUDDY_MATCH = {
    "matches": [
        {
            "buddy_id": "cand_002",
            "learner_name": "Tunde",
            "match_score": 92,
            "shared_interests": ["football", "technology"],
            "reasons": ["Same course, same beginner level", "Shares football as a study hook", "Complementary strengths (HTML basics/selectors)"],
            "caveat": "Tunde is strongest where you're weakest — great for pairing.",
        },
        {
            "buddy_id": "cand_005",
            "learner_name": "Chiamaka",
            "match_score": 84,
            "shared_interests": ["music", "technology"],
            "reasons": ["Similar study pace and streak habits", "Both targeting the UI/UX path"],
            "caveat": "Goals are aligned but schedules may differ slightly.",
        },
    ],
    "intro_message": "Adeola, Tunde is a 92% match — same course, same level, and a shared football hook. Say hi and try quizzing each other on selectors!",
}

_BUDDY_ICEBREAKER = {
    "message": (
        "Hey Tunde! I'm Adeola, also on the UI/UX path and stuck on CSS Selectors. "
        "I noticed we both follow football -- want to swap football-themed design "
        "tips this week and quiz each other on selectors? My streak says I'll show "
        "up daily!"
    )
}

_INSIGHTS_GENERATE = {
    "summary": "Adeola is off to a strong start with solid HTML fundamentals and a consistent streak. The main gap is CSS Selectors, which needs focused revision before it compounds.",
    "strengths": [
        {"area": "HTML fundamentals", "detail": "Scored 90% on first attempt", "evidence": "HTML Basics quiz: 90% (1 attempt)"},
        {"area": "Consistency", "detail": "4-day streak and steady weekly XP (85 this week)", "evidence": "streak_days=4, xp_this_week=85"},
    ],
    "weaknesses": [
        {"area": "CSS Selectors", "detail": "Scored 55% across two attempts", "impact": "Selectors underpin every layout task, so this will compound later", "evidence": "CSS Selectors quiz: 55% (2 attempts)"},
    ],
    "suggestions": [
        {"title": "Revise selectors this week", "description": "Run selector quizzes and aim for 70%+ before moving on", "expected_impact": "Removes the biggest risk to course momentum"},
    ],
    "forecast": {
        "timeframe": "next 4 weeks",
        "projection": "On track to reach ~55% course completion if pace holds",
        "confidence_level": "medium",
        "assumptions": ["30 min/day", "Selectors gap closed within a week"],
    },
}

_INSIGHTS_PRIORITY = {
    "priorities": [
        {
            "focus_area": "CSS Selectors mastery",
            "action": "Revise selectors and retake the quiz until you score 70%+",
            "rationale": "Lowest quiz score (55%) directly blocks Flexbox and layout lessons",
            "suggested_metric": "CSS Selectors quiz >= 70%",
        }
    ],
    "message": "Adeola, focus this week on one thing: getting CSS Selectors above 70%. Your 4-day streak proves you're consistent — apply that here and the rest flows.",
}


# ── Prompt parsing ───────────────────────────────────────────────────────────
# The prompts are the contract: everything the model is asked for is written
# into the final user message. Mock mode reads them back out so the reply
# answers the actual question instead of a fixed one.

_INTERESTS_RE = re.compile(r"Interests:\s*(.+)", re.I)
_TOPIC_RE = re.compile(r"^\s*-\s*Topic:\s*(.+?)\s*$", re.M)
_LESSON_RE = re.compile(r"^\s*Lesson:\s*(.+?)\s*\(", re.M)
_QUIZ_COUNT_RE = re.compile(r"(\d+)-question multiple choice quiz")
_CATALOGUE_ID_RE = re.compile(r"^\s*ID:\s*(\S+)\s*$", re.M)
_CATALOGUE_TITLE_RE = re.compile(r"^\s*Title:\s*(.+?)\s*$", re.M)
_COMPLETED_RE = re.compile(r"Do not include any completed courses:\s*(.+)", re.I)
_ITEM_RE = re.compile(
    r"ITEM (\d+)\nContent type: (\w+)\nInstruction: .*?\nOriginal content:\n(.*?)\n\n",
    re.S,
)
_CURRENT_DAY_RE = re.compile(r"Current schedule day:\s*(\d+)\s*of", re.I)
_COMPLETED_TOPIC_RE = re.compile(r"Completed topic:\s*(.+)", re.I)
_SESSION_SCORE_RE = re.compile(r"Quiz score from this session:\s*([\d.]+)%", re.I)
_SCHEDULE_START_RE = re.compile(r"Schedule starts on:\s*(\d{4}-\d{2}-\d{2})", re.I)
_CONTENT_TYPE_RE = re.compile(r"Content type:\s*(\w+)")
_ORIGINAL_RE = re.compile(r"ORIGINAL CONTENT\n.*?\n(.*?)\n\nReturn ONLY", re.S)


def _interests(prompt: str) -> list[str]:
    """Read the learner's interests out of the prompt."""
    match = _INTERESTS_RE.search(prompt)
    if not match:
        return ["technology"]
    raw = match.group(1)
    # "Interests: football, music, technology" on the profile line, but the
    # personalization prompt continues into the next line, so stop at a
    # newline or a known follow-on label.
    line = raw.split("\n")[0]
    line = re.split(r"\b(Name|Difficulty|Course|Topic|Rules)\b\s*:", line)[0]
    items = [i.strip().strip(".").lower() for i in line.split(",")]
    return [i for i in items if i] or ["technology"]


def _catalogue(prompt: str) -> list[tuple[str, str]]:
    """(course_id, title) pairs actually offered in the prompt's catalogue."""
    ids = _CATALOGUE_ID_RE.findall(prompt)
    titles = _CATALOGUE_TITLE_RE.findall(prompt)
    return list(zip(ids, titles)) or [("course_001", "Foundations")]


def _completed_ids(prompt: str) -> set[str]:
    match = _COMPLETED_RE.search(prompt)
    if not match:
        return set()
    # The prompt interpolates a Python list repr, e.g. "['course_001', 'course_002']".
    cleaned = match.group(1).replace("[", " ").replace("]", " ")
    return {
        p.strip().strip("'\"") for p in cleaned.split(",") if p.strip().strip("'\"")
    }


def _topics(prompt: str) -> list[tuple[str, str]]:
    """(topic, lesson) pairs from a TOPIC HISTORY block."""
    topics = _TOPIC_RE.findall(prompt)
    lessons = _LESSON_RE.findall(prompt)
    return [(t, lessons[i] if i < len(lessons) else "Lesson") for i, t in enumerate(topics)]


# ── Dynamic payloads ─────────────────────────────────────────────────────────


def _build_quiz(prompt: str) -> dict:
    """Honour the requested number of questions and name the topic."""
    match = _QUIZ_COUNT_RE.search(prompt)
    wanted = int(match.group(1)) if match else 2
    topic_match = re.search(r"quiz on '(.+?)'", prompt)
    topic = topic_match.group(1) if topic_match else "this topic"

    bank = list(_QUIZ["questions"])
    questions = []
    for i in range(max(1, wanted)):
        base = dict(bank[i % len(bank)])
        # Vary repeats so a 5-question quiz isn't three copies of one question.
        if i >= len(bank):
            base["question"] = (
                f"{base['question']} (variation {i // len(bank) + 1}: "
                f"where else does {topic} apply?)"
            )
        questions.append(base)
    return {"questions": questions}


def _build_path(prompt: str, *, adjusted: bool) -> dict:
    """Recommend only courses that are in the prompt's catalogue."""
    catalogue = _catalogue(prompt)
    done = _completed_ids(prompt)
    open_courses = [(cid, title) for cid, title in catalogue if cid not in done]
    if not open_courses:
        open_courses = catalogue[:1]

    recommended = [
        {
            "order": i + 1,
            "course_id": cid,
            "title": title,
            "why_recommended": f"Moves you toward your goal and builds on what you've already finished.",
            "estimated_hours": 8,
            "estimated_weeks": 2,
        }
        for i, (cid, title) in enumerate(open_courses[:4])
    ]
    weeks = sum(r["estimated_weeks"] for r in recommended) or 1

    prefix = (
        "Path adjusted: "
        if adjusted
        else "Path generated: "
    )
    return {
        "action": "adjust_path" if adjusted else "generate_path",
        "learner_id": "learner_001",
        "summary": (
            f"{prefix}{len(recommended)} course(s) over {weeks} weeks, "
            f"skipping what you've already completed."
        ),
        "recommended_courses": recommended,
        "milestones": [
            {
                "title": f"Finish {r['title']}",
                "description": f"Complete {r['title']} and its quiz.",
                "due_week": r["estimated_weeks"],
            }
            for r in recommended
        ],
        "weekly_schedule": [
            {
                "week": w,
                "focus": f"Week {w}: build and practise",
                "course_title": recommended[min(w - 1, len(recommended) - 1)]["title"],
                "hours_recommended": 5,
            }
            for w in range(1, weeks + 1)
        ],
        "total_estimated_weeks": weeks,
    }


def _personalize_text(original: str, interest: str, content_type: str) -> str:
    """Rewrite framing around `interest` while keeping the technical terms.

    Real Claude would genuinely rewrite the prose. The mock only has to prove
    the guarantees the service depends on: the original's technical content
    survives, the interest appears, and the text differs from the input.

    Quiz context is the one case needing more than a prefix. Its guarantee is
    that the *scenario* changes while the question under test does not, so
    the mock drops the old scenario sentence and reframes around the interest
    instead of keeping it and prefixing.
    """
    body = original.strip()
    if content_type == "quiz_context":
        sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", body) if s.strip()]
        if len(sentences) > 1:
            # First sentence sets the scene; the rest is the actual question.
            body = " ".join(sentences[1:])
        return f"Set this in {interest}: {body}"

    anchor = {
        "explanation": f"Think of it the way you'd think about {interest}: ",
        "example": f"Picture {interest} instead: ",
        "exercise_brief": f"Build it with {interest} in mind: ",
    }.get(content_type, f"Related to {interest}: ")
    return f"{anchor}{body}"


def _build_personalize(prompt: str) -> dict:
    """Echo the actual original content, woven around a real interest."""
    interests = _interests(prompt)
    # Rotate by learner name so two learners with the same content still get
    # different framings — the point of the feature is per-learner variety.
    name_match = re.search(r"Name:\s*(.+)", prompt)
    name = name_match.group(1).strip().split("\n")[0] if name_match else ""
    offset = sum(ord(c) for c in name) % len(interests)
    interest = interests[offset]
    type_match = _CONTENT_TYPE_RE.search(prompt)
    content_type = type_match.group(1) if type_match else "explanation"
    original_match = _ORIGINAL_RE.search(prompt)
    original = original_match.group(1).strip() if original_match else _PERSONALIZE[
        "personalized_content"
    ]
    return {
        "personalized_content": _personalize_text(original, interest, content_type),
        "interest_used": interest,
    }


def _build_batch(prompt: str) -> list[dict]:
    """One item per ITEM block in the prompt, in order."""
    interests = _interests(prompt)
    items = []
    for index, content_type, original in _ITEM_RE.findall(prompt):
        # Rotate interests so a batch doesn't look like one template repeated.
        interest = interests[(int(index) - 1) % len(interests)]
        items.append({
            "content_type": content_type,
            "original_content": original.strip(),
            "personalized_content": _personalize_text(
                original.strip(), interest, content_type
            ),
            "interest_used": interest,
        })
    return items or [dict(_BATCH[0])]


def _add_days(start: str, offset: int) -> str:
    from datetime import date, timedelta

    year, month, day = (int(p) for p in start.split("-"))
    return (date(year, month, day) + timedelta(days=offset)).isoformat()


def _build_explain(prompt: str) -> str:
    """Explain the concept using one of the learner's actual interests.

    The prompt names both the concept and the interests, so the reply can
    honour both. A fixed explanation can't, so it fails the "use my interests"
    guarantee that is the entire point of the endpoint.
    """
    concept_match = re.search(r"Can you explain '(.+?)' to me", prompt)
    concept = concept_match.group(1) if concept_match else "this concept"
    interests = _interests(prompt)
    interest = interests[0]
    return (
        f"{concept} is easier to see once it has a shape. Picture {interest}: "
        f"the things you care about are the flex items, and the rules you set "
        f"decide how they line up. `justify-content` distributes them along "
        f"the main axis, `align-items` handles the cross axis, and `gap` keeps "
        f"the spacing even. Try it with {interest} and it stops being a rule "
        f"you memorise."
    )


def _build_revision(prompt: str, *, update: bool) -> dict:
    """Cover every topic the prompt asked about, respecting day constraints.

    On an update the completed topic is dropped when the learner scored well
    and brought forward when they didn't — the behaviour the tests assert.
    """
    topics = _topics(prompt)
    start_match = _SCHEDULE_START_RE.search(prompt)
    start = start_match.group(1) if start_match else "2026-09-10"

    first_day = 1
    completed_topic = ""
    score = None
    if update:
        day_match = _CURRENT_DAY_RE.search(prompt)
        first_day = int(day_match.group(1)) + 1 if day_match else 1
        topic_match = _COMPLETED_TOPIC_RE.search(prompt)
        completed_topic = topic_match.group(1).strip() if topic_match else ""
        score_match = _SESSION_SCORE_RE.search(prompt)
        score = float(score_match.group(1)) if score_match else None

    def rank(topic: str) -> tuple:
        """Weakest and least-recently-studied first; completed topic per score."""
        is_completed = topic == completed_topic
        if is_completed and score is not None and score >= 80:
            return (3, topic)          # mastered: push to the back
        if is_completed and score is not None and score < 60:
            return (0, topic)          # shaky: bring forward
        return (1, topic)

    ordered = sorted(topics, key=lambda t: rank(t[0]))

    entries = []
    for i, (topic, lesson) in enumerate(ordered):
        day = first_day + i
        if day > 30:
            break
        entries.append({
            "day": day,
            "date": _add_days(start, day - 1),
            "topic": topic,
            "lesson": lesson,
            "method": "quiz" if i % 2 == 0 else "flashcard",
            "estimated_minutes": 15,
            "reason": (
                f"Scheduled early: {topic} is your highest-priority gap right now."
            ),
        })

    if not entries:
        entries = [dict(_REVISION_GENERATE["entries"][0], day=first_day)]

    summary = (
        f"Regenerated days {first_day}-30 covering {len(entries)} topic(s); "
        f"'{completed_topic}' placed according to your {score:.0f}% score."
        if update and score is not None
        else f"30-day plan covering {len(entries)} topic(s), weakest first."
    )
    return {"summary": summary, "entries": entries}


# ── Marker table (first match wins, most specific first) ─────────────────────
# Each entry is (marker, payload). A payload may be a dict/list (returned
# as-is) or a callable taking the prompt (built per request).

_PAYLOADS = [
    ("Find study buddies for", _BUDDY_MATCH),
    ("icebreaker message from", _BUDDY_ICEBREAKER),
    ("Recommend the next mission", _MISSION_RECOMMEND),
    ("through their active mission", _MISSION_GUIDE),
    ("Generate a full insights report", _INSIGHTS_GENERATE),
    ("TOP priorities for the next week", _INSIGHTS_PRIORITY),
    ("-question multiple choice quiz", _build_quiz),
    ("Please create a personalized study plan", _STUDY_PLAN),
    ("Can you explain", _build_explain),
    ("[SYSTEM TRIGGER", _ENCOURAGE),
    ("I'm currently studying", _ANSWER_QUESTION),
    ("Generate a personalized learning path", lambda p: _build_path(p, adjusted=False)),
    ("existing learning path", lambda p: _build_path(p, adjusted=True)),
    ("Personalize each of the following", _build_batch),
    ("Content type:", _build_personalize),
    ("Generate a 30-day revision schedule", lambda p: _build_revision(p, update=False)),
    ("just completed a revision session", lambda p: _build_revision(p, update=True)),
]

_FALLBACK = (
    "MOCK MODE: no canned payload matched this request. Use the prompt-level "
    "tests (tests/test_*.py) to verify prompt construction instead."
)


# ── Fake client matching the anthropic.Anthropic surface ─────────────────────

class FakeAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        user_msgs = [
            m.get("content", "") for m in kwargs.get("messages", [])
            if m.get("role") == "user"
        ]
        last_user = user_msgs[-1] if user_msgs else ""
        # Markers live in the user message, but the learner profile (interests,
        # level, completed courses) is in the system prompt. Builders need
        # both, so hand them one string with the system prompt first.
        system = kwargs.get("system") or ""
        full_prompt = f"{system}\n{last_user}" if isinstance(system, str) else last_user

        for marker, payload in _PAYLOADS:
            if marker in last_user:
                break
        else:
            payload = _FALLBACK
        if callable(payload):
            payload = payload(full_prompt)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return SimpleNamespace(
            content=[SimpleNamespace(text=text)],
            # Services read response.content[0].text and nothing else, but a
            # real reply has these fields and a future caller might. Keep the
            # shape honest so mock mode doesn't hide a missing attribute.
            stop_reason="end_turn",
            model="mock-claude",
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
        )