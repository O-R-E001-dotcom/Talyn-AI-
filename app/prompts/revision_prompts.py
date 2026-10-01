
"""
Talyn — Revision Schedule Prompts

Prompt builders for generating and updating 30-day spaced repetition
revision schedules based on learner topic history and performance.
"""

from app.models.schemas import RevisionScheduleProfile, TopicRecord
from typing import Optional

# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_topic_records(records: list[TopicRecord]) -> str:
    if not records:
        return "No topics studied yet."

    lines = []
    for r in records:
        score_text = f"{r.quiz_score_percent:.0f}%" if r.quiz_score_percent is not None else "not quizzed"
        completed_text = "lesson complete" if r.lesson_completed else "lesson in progress"
        lines.append(
            f"  - Topic: {r.topic}\n"
            f"    Lesson: {r.lesson} ({completed_text})\n"
            f"    Last studied: {r.last_studied_date} ({r.days_since_studied} days ago)\n"
            f"    Times reviewed: {r.times_reviewed}\n"
            f"    Quiz score: {score_text}"
        )
    return "\n\n".join(lines)


def _spaced_repetition_rules() -> str:
    return """
SPACED REPETITION RULES
───────────────────────
Use these rules to determine when a topic should be scheduled for revision:

1. RETENTION SCORING — Assign each topic a priority score (higher = needs revision sooner):
   - Quiz score below 60%:      HIGH priority  (schedule within days 1–5)
   - Quiz score 60–79%:         MEDIUM priority (schedule within days 3–10)
   - Quiz score 80%+:           LOW priority   (schedule within days 7–20)
   - Never quizzed:             HIGH priority  (treat as unknown)
   - Lesson not yet completed:  MEDIUM priority (light revision to reinforce)

2. FORGETTING CURVE — Factor in days since last studied:
   - Studied 1–3 days ago:     revisit in 3–5 days
   - Studied 4–7 days ago:     revisit in 2–4 days
   - Studied 8–14 days ago:    revisit in 1–3 days
   - Studied 15+ days ago:     revisit immediately (Day 1–2)

3. REVIEW FREQUENCY — Scale with how many times reviewed:
   - 0 reviews:   schedule 3x in 30 days
   - 1 review:    schedule 2x in 30 days
   - 2+ reviews:  schedule 1x in 30 days (unless score is low)

4. METHOD SELECTION:
   - High priority / low score:    quiz
   - Medium priority:              flashcard
   - Low priority / high score:    re-read (light reinforcement)
   - Never quizzed:                quiz (to establish a baseline)

5. TIME BUDGET — Respect the learner's daily_study_minutes limit per day.
   Do not schedule more combined estimated_minutes than the daily limit.
   Spread sessions so no single day is overloaded.

6. SPREAD — Do not cluster all high-priority topics in Day 1.
   Interleave topics across days to avoid fatigue.
""".strip()


# ── System Prompt ─────────────────────────────────────────────────────────────

def _revision_system_prompt(learner: RevisionScheduleProfile) -> str:
    return f"""You are Talyn Revision Planner, an AI engine that generates personalised spaced repetition revision schedules for learners on the Talyn platform.

YOUR JOB
────────
Analyse the learner's topic history (quiz scores, days since studied, review count, completion status) and generate a 30-day revision schedule that maximises long-term retention using spaced repetition principles.

LEARNER PROFILE
───────────────
Name:                {learner.learner_name}
Difficulty level:    {learner.difficulty_level.value}
Daily study budget:  {learner.daily_study_minutes} minutes/day
Schedule starts:     {learner.schedule_start_date}
Topics to cover:     {len(learner.topic_records)}

{_spaced_repetition_rules()}

RESPONSE FORMAT
───────────────
Return ONLY valid JSON. No markdown fences, no preamble, no commentary outside the JSON."""


# ── Generate Schedule Prompt ──────────────────────────────────────────────────

def generate_revision_schedule_prompt(
    learner: RevisionScheduleProfile,
) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for generating a full 30-day revision schedule."""
    system = _revision_system_prompt(learner)
    topic_text = _format_topic_records(learner.topic_records)

    messages = [{
        "role": "user",
        "content": (
            f"Generate a 30-day revision schedule for {learner.learner_name}.\n\n"
            f"TOPIC HISTORY\n"
            f"─────────────\n"
            f"{topic_text}\n\n"
            f"REQUIREMENTS\n"
            f"────────────\n"
            f"- Schedule starts on {learner.schedule_start_date}\n"
            f"- Daily study budget: {learner.daily_study_minutes} minutes\n"
            f"- Cover all topics at least once\n"
            f"- High-priority topics (low scores, long gaps) must appear earlier\n"
            f"- Not every day needs a revision entry — rest days are fine\n"
            f"- A day can have multiple entries if the budget allows\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "summary": "2-3 sentences describing the schedule strategy and focus areas",\n'
            f'  "entries": [\n'
            f'    {{\n'
            f'      "day": 1,\n'
            f'      "date": "YYYY-MM-DD",\n'
            f'      "topic": "...",\n'
            f'      "lesson": "...",\n'
            f'      "method": "quiz | flashcard | re-read",\n'
            f'      "estimated_minutes": 10,\n'
            f'      "reason": "Specific reason this topic is scheduled today"\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"Rules:\n"
            f"- day is an integer from 1 to 30\n"
            f"- date must be calculated from start date {learner.schedule_start_date}\n"
            f"- method must be exactly one of: quiz, flashcard, re-read\n"
            f"- estimated_minutes should be 5–20 per entry\n"
            f"- reason must reference the actual data (e.g. score, days elapsed, review count)\n"
            f"- total entries across all 30 days should be proportional to number of topics"
        )
    }]

    return system, messages


# ── Update Schedule Prompt ────────────────────────────────────────────────────

def update_revision_schedule_prompt(
    learner: RevisionScheduleProfile,
    completed_topic: str,
    session_quiz_score: Optional[float],
    current_schedule_day: int,
) -> tuple[str, list[dict]]:
    """
    Returns (system_prompt, messages) for refreshing the remaining schedule
    after a learner completes a revision session.
    """
    system = _revision_system_prompt(learner)
    topic_text = _format_topic_records(learner.topic_records)

    score_text = (
        f"Quiz score from this session: {session_quiz_score:.0f}%"
        if session_quiz_score is not None
        else "No quiz was done in this session."
    )

    messages = [{
        "role": "user",
        "content": (
            f"{learner.learner_name} just completed a revision session.\n\n"
            f"Completed topic: {completed_topic}\n"
            f"{score_text}\n"
            f"Current schedule day: {current_schedule_day} of 30\n\n"
            f"UPDATED TOPIC HISTORY\n"
            f"─────────────────────\n"
            f"{topic_text}\n\n"
            f"Regenerate the REMAINING schedule for days {current_schedule_day + 1}–30.\n\n"
            f"Consider:\n"
            f"- If the quiz score was low (<60%), resurface '{completed_topic}' sooner\n"
            f"- If the quiz score was high (80%+), push '{completed_topic}' later or drop it\n"
            f"- Adjust all other topics based on the updated topic history\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "summary": "Brief note on what changed and why",\n'
            f'  "entries": [\n'
            f'    {{\n'
            f'      "day": {current_schedule_day + 1},\n'
            f'      "date": "YYYY-MM-DD",\n'
            f'      "topic": "...",\n'
            f'      "lesson": "...",\n'
            f'      "method": "quiz | flashcard | re-read",\n'
            f'      "estimated_minutes": 10,\n'
            f'      "reason": "..."\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"- Only include days {current_schedule_day + 1} to 30\n"
            f"- date must be calculated from {learner.schedule_start_date} + day offset\n"
            f"- method must be exactly: quiz, flashcard, or re-read"
        )
    }]

    return system, messages
