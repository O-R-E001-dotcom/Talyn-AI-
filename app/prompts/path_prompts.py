"""
Talyn — Learning Path Prompts

Prompt builders for the two path endpoints:
  - generate_path_prompt   → brand-new path from scratch
  - adjust_path_prompt     → re-sequence / swap courses on an existing path
"""

from app.models.schemas import LearnerPathProfile, AvailableCourse


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_course_catalogue(courses: list[AvailableCourse]) -> str:
    if not courses:
        return "No courses provided."
    lines = []
    for c in courses:
        lines.append(
            f"  ID: {c.course_id}\n"
            f"  Title: {c.title}\n"
            f"  Level: {c.skill_level.value}\n"
            f"  Hours: {c.estimated_hours}h\n"
            f"  Topics: {', '.join(c.topics)}\n"
            f"  Description: {c.description}"
        )
    return "\n\n".join(lines)


def _format_completed(completed_ids: list[str], courses: list[AvailableCourse]) -> str:
    if not completed_ids:
        return "None"
    titles = {c.course_id: c.title for c in courses}
    return ", ".join(titles.get(cid, cid) for cid in completed_ids)


def _learner_snapshot(learner: LearnerPathProfile) -> str:
    return f"""
LEARNER SNAPSHOT
────────────────
Name:             {learner.learner_name}
Skill level:      {learner.skill_level.value}
Interests:        {', '.join(learner.interests)}
Available time:   {learner.hours_per_week} hours/week
Goals:            {learner.goals}
Completed so far: {_format_completed(learner.completed_course_ids, learner.available_courses)}
""".strip()


# ── System Prompt ─────────────────────────────────────────────────────────────

def _path_system_prompt(learner: LearnerPathProfile) -> str:
    return f"""You are Talyn Path Planner, the AI engine that designs personalized learning paths for learners on the Talyn platform.

YOUR JOB
────────
Given a learner's profile and a catalogue of available courses, you select and sequence the most suitable courses to help the learner achieve their goals efficiently.

CORE PRINCIPLES
───────────────
1. Relevance first — only recommend courses that directly serve the learner's stated goals.
2. Respect skill level — never drop a {learner.skill_level.value}-level learner into advanced material without a bridge course.
3. Avoid redundancy — never recommend courses the learner has already completed.
4. Use interests — where multiple courses could fill a slot, prefer the one with topics aligned to {', '.join(learner.interests)}.
5. Be realistic about time — the learner has {learner.hours_per_week} hours/week. Pace the path accordingly.
6. Explain your reasoning — every course recommendation must include a clear, specific "why" grounded in the learner's goals or gaps.

RESPONSE FORMAT
───────────────
Always return ONLY valid JSON. No markdown fences, no preamble, no commentary outside the JSON.

{_learner_snapshot(learner)}"""


# ── Generate Path Prompt ──────────────────────────────────────────────────────

def generate_path_prompt(learner: LearnerPathProfile) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for generating a new learning path."""
    system = _path_system_prompt(learner)

    catalogue_text = _format_course_catalogue(learner.available_courses)

    messages = [{
        "role": "user",
        "content": (
            f"Generate a personalized learning path for {learner.learner_name}.\n\n"
            f"AVAILABLE COURSES CATALOGUE\n"
            f"───────────────────────────\n"
            f"{catalogue_text}\n\n"
            f"Return ONLY a JSON object in this exact structure:\n\n"
            f'{{\n'
            f'  "summary": "2-3 sentence overview of the path and why it suits this learner",\n'
            f'  "recommended_courses": [\n'
            f'    {{\n'
            f'      "order": 1,\n'
            f'      "course_id": "...",\n'
            f'      "title": "...",\n'
            f'      "why_recommended": "Specific reason tied to this learner\'s goals or current level",\n'
            f'      "estimated_hours": 0.0,\n'
            f'      "estimated_weeks": 0.0\n'
            f'    }}\n'
            f'  ],\n'
            f'  "milestones": [\n'
            f'    {{\n'
            f'      "title": "...",\n'
            f'      "description": "What the learner can do or know at this point",\n'
            f'      "due_week": 0\n'
            f'    }}\n'
            f'  ],\n'
            f'  "weekly_schedule": [\n'
            f'    {{\n'
            f'      "week": 1,\n'
            f'      "focus": "Short description of this week\'s task",\n'
            f'      "course_title": "...",\n'
            f'      "hours_recommended": 0.0\n'
            f'    }}\n'
            f'  ],\n'
            f'  "total_estimated_weeks": 0.0\n'
            f'}}\n\n'
            f'Rules:\n'
            f'- estimated_weeks per course = estimated_hours / {learner.hours_per_week} (round to 1 decimal)\n'
            f'- total_estimated_weeks = sum of all course estimated_weeks\n'
            f'- weekly_schedule must cover every week from 1 to total_estimated_weeks\n'
            f'- milestones should mark meaningful progress points, roughly every 2-4 weeks\n'
            f'- Only include courses from the catalogue; use exact course_id values\n'
            f'- Do not include any completed courses: {learner.completed_course_ids or "none"}'
        )
    }]

    return system, messages


# ── Adjust Path Prompt ────────────────────────────────────────────────────────

def adjust_path_prompt(
    learner: LearnerPathProfile,
    current_path_course_ids: list[str],
    reason: str,
) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for adjusting an existing learning path."""
    system = _path_system_prompt(learner)

    # Build a readable version of the current path
    id_to_course = {c.course_id: c for c in learner.available_courses}
    current_path_text = "\n".join(
        f"  {i+1}. [{cid}] {id_to_course[cid].title if cid in id_to_course else cid}"
        for i, cid in enumerate(current_path_course_ids)
    )

    catalogue_text = _format_course_catalogue(learner.available_courses)

    messages = [{
        "role": "user",
        "content": (
            f"Adjust {learner.learner_name}'s existing learning path.\n\n"
            f"CURRENT PATH\n"
            f"────────────\n"
            f"{current_path_text}\n\n"
            f"REASON FOR ADJUSTMENT\n"
            f"─────────────────────\n"
            f"{reason}\n\n"
            f"AVAILABLE COURSES CATALOGUE\n"
            f"───────────────────────────\n"
            f"{catalogue_text}\n\n"
            f"Based on the adjustment reason, redesign the path. You may:\n"
            f"- Remove courses that are no longer relevant\n"
            f"- Add new courses from the catalogue\n"
            f"- Re-order existing courses\n"
            f"- Replace a course with a better alternative\n\n"
            f"Return ONLY a JSON object in this exact structure:\n\n"
            f'{{\n'
            f'  "summary": "Explain what changed and why, in 2-3 sentences",\n'
            f'  "recommended_courses": [\n'
            f'    {{\n'
            f'      "order": 1,\n'
            f'      "course_id": "...",\n'
            f'      "title": "...",\n'
            f'      "why_recommended": "...",\n'
            f'      "estimated_hours": 0.0,\n'
            f'      "estimated_weeks": 0.0\n'
            f'    }}\n'
            f'  ],\n'
            f'  "milestones": [\n'
            f'    {{\n'
            f'      "title": "...",\n'
            f'      "description": "...",\n'
            f'      "due_week": 0\n'
            f'    }}\n'
            f'  ],\n'
            f'  "weekly_schedule": [\n'
            f'    {{\n'
            f'      "week": 1,\n'
            f'      "focus": "...",\n'
            f'      "course_title": "...",\n'
            f'      "hours_recommended": 0.0\n'
            f'    }}\n'
            f'  ],\n'
            f'  "total_estimated_weeks": 0.0\n'
            f'}}\n\n'
            f'Rules:\n'
            f'- estimated_weeks per course = estimated_hours / {learner.hours_per_week}\n'
            f'- total_estimated_weeks = sum of all estimated_weeks\n'
            f'- weekly_schedule must cover every week from 1 to total_estimated_weeks\n'
            f'- Only use course_ids from the catalogue\n'
            f'- Do not include completed courses: {learner.completed_course_ids or "none"}'
        )
    }]

    return system, messages
