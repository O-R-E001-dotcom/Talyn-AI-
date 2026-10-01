"""
Talyn — Study Buddy System Prompts

Prompt builders for matching learners into accountability pairs and writing
warm icebreakers to start the partnership. Two prompt builders:
  - find_buddy_prompt → rank a candidate pool for the learner
  - icebreaker_prompt → write a first message to a chosen buddy
"""

from app.models.schemas import LearnerContext, BuddyCandidate
from app.prompts.coach_prompts import _build_learner_profile


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_candidates(candidates: list[BuddyCandidate]) -> str:
    if not candidates:
        return "No candidates given."
    lines = []
    for c in candidates:
        lines.append(
            f"  ID: {c.learner_id}\n"
            f"  Name: {c.learner_name}\n"
            f"  Level: {c.skill_level.value}\n"
            f"  Interests: {', '.join(c.interests) if c.interests else 'not specified'}\n"
            f"  Current course: {c.current_course if c.current_course else 'not specified'}\n"
            f"  Goals: {c.goals if c.goals else 'not specified'}\n"
            f"  Hours/week: {c.hours_per_week}\n"
            f"  Schedule: {c.schedule if c.schedule else 'not specified'}\n"
            f"  XP this week: {c.xp_this_week}\n"
            f"  Streak: {c.streak_days} day(s)"
        )
    return "\n\n".join(lines)


# ── System Prompt ─────────────────────────────────────────────────────────────

def _buddy_system_prompt(learner: LearnerContext) -> str:
    return f"""You are Talyn Buddy Matcher, the AI engine that pairs learners on the Talyn platform so they can hold each other accountable and learn together.

YOUR JOB
────────
Given a learner and a pool of candidate buddies, rank the best matches and explain why. Matching is always based on academic and progress signals — never personal details.

MATCHING CRITERIA (weights sum to 100)
──────────────────────────────────────
1. Goals alignment (30) — candidates pursuing the same or complementary goals are strongest.
2. Course / topic overlap (20) — the same current course or overlapping topics mean they can study together.
3. Interest overlap (20) — shared interests make study sessions more engaging.
4. Skill level closeness (15) — similar levels keep sessions balanced; be honest about gaps.
5. Time availability (10) — compatible schedules and hours/week keep accountability realistic.
6. Consistency (5) — similar weekly XP or streaks, so one learner isn't always dragging the other.

RULES
─────
- Never reveal private or sensitive information about any learner.
- Never recommend a match that would shame either learner.
- Only rank the candidates given — never invent candidates.
- Return ONLY valid JSON. No markdown fences, no preamble.

{_build_learner_profile(learner)}"""


# ── Find Buddy Prompt ─────────────────────────────────────────────────────────

def find_buddy_prompt(
    learner: LearnerContext,
    candidates: list[BuddyCandidate],
) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for ranking study buddy candidates."""
    system = _buddy_system_prompt(learner)
    candidate_text = _format_candidates(candidates)

    messages = [{
        "role": "user",
        "content": (
            f"Find study buddies for {learner.learner_name} from the candidate pool below.\n\n"
            f"CANDIDATE POOL\n"
            f"──────────────\n"
            f"{candidate_text}\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "matches": [\n'
            f'    {{\n'
            f'      "buddy_id": "...",\n'
            f'      "learner_name": "...",\n'
            f'      "match_score": 0,\n'
            f'      "shared_interests": ["..."],\n'
            f'      "reasons": ["...", "..."],\n'
            f'      "caveat": "null or a brief honest note about a mismatch"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "intro_message": "A short, warm, first-person message FROM {learner.learner_name} TO the top match to start the conversation"\n'
            f'}}\n\n'
            f"Rules:\n"
            f"- match_score is 0-100 using the criteria weights\n"
            f"- rank candidates best-first; return at most {len(candidates)} matches\n"
            f"- if no candidate is a reasonable match (below ~55), return an empty matches array and make intro_message explain why and suggest retrying later\n"
            f"- reasons must be specific and grounded in the candidates' actual data\n"
            f"- shared_interests must list only interests present in BOTH profiles"
        )
    }]

    return system, messages


# ── Icebreaker Prompt ─────────────────────────────────────────────────────────

def icebreaker_prompt(
    learner: LearnerContext,
    buddy: BuddyCandidate,
) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for the first message to a buddy."""
    system = _buddy_system_prompt(learner)
    buddy_text = _format_candidates([buddy])

    messages = [{
        "role": "user",
        "content": (
            f"Write a warm, natural icebreaker message from {learner.learner_name} to {buddy.learner_name}, "
            f"who was just matched as their study buddy.\n\n"
            f"BUDDY PROFILE\n"
            f"─────────────\n"
            f"{buddy_text}\n\n"
            f"Guidelines:\n"
            f"- Friendly and genuine, like a message from one learner to another — not corporate.\n"
            f"- Reference ONE shared interest or shared goal to make it personal.\n"
            f"- Suggest one simple concrete first step (e.g. a time to check in, a topic to study together).\n"
            f"- Keep it under 120 words.\n"
            f"- Do not invent facts about either learner; only use the given data.\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{"message": "..."}}'
        )
    }]

    return system, messages