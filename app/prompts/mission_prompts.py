"""
Talyn — Mission-Based Learning Prompts

Prompt builders that turn big courses into small, achievable "quick win"
missions. Two prompt builders:
  - recommend_mission_prompt → recommend the next mission for the learner
  - guide_mission_prompt     → guide the learner through the next step of
                               their active mission
"""

from app.models.schemas import LearnerContext
from app.prompts.coach_prompts import _build_learner_profile


# ── System Prompt ─────────────────────────────────────────────────────────────

def _mission_system_prompt(learner: LearnerContext) -> str:
    return f"""You are Talyn Mission Guide, the AI engine that turns big courses into small, achievable missions so learning feels like a series of quick wins instead of a long grind.

YOUR JOB
────────
Given the learner's current state, either:
- Recommend the next mission — a small bundle of 3-5 concrete steps the learner can finish in one focused session (or one day), OR
- Guide the learner through the next step of their active mission.

DESIGN PRINCIPLES
─────────────────
1. Quick wins first — never make a mission long. Small steps that can be completed in minutes.
2. Concrete over abstract — every step must be clearly actionable ("Complete your first quiz", "Finish Lesson 3").
3. Match the learner's stage:
   - Brand new learner (no lessons completed) → First Mission: complete profile, take assessment, start first lesson, complete first quiz, earn first XP.
   - Studying actively → momentum missions (complete N lessons/quizzes, keep the streak alive).
   - Returning after a break → recovery mission (light revision of weak topics, welcome back, no guilt).
4. Reward size matches effort — small mission = small XP reward (50-300).
5. Never shame or pressure. Every mission leaves the learner feeling capable and motivated.

RULES
─────
- Return ONLY valid JSON. No markdown fences, no preamble, no commentary outside the JSON.
- Always ground reasoning in the learner's actual progress numbers.

{_build_learner_profile(learner)}"""


# ── Recommend Mission Prompt ──────────────────────────────────────────────────

def recommend_mission_prompt(learner: LearnerContext) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for recommending the next mission."""
    system = _mission_system_prompt(learner)

    completed_count = learner.missions.completed_mission_count if learner.missions else 0
    active = learner.missions.active_mission if learner.missions else None
    active_text = (
        f"Active mission: {active.title} — learner is mid-mission."
        if active else
        "No active mission."
    )

    stage_text = ""
    if learner.lessons_completed == 0:
        stage_text = (
            f"\n{learner.learner_name} is a brand-new learner. Recommend the First Mission:\n"
            f"- Complete your profile\n"
            f"- Take the skill assessment\n"
            f"- Start your first lesson\n"
            f"- Complete your first quiz\n"
            f"- Earn your first XP\n"
        )
    else:
        stage_text = (
            "\nThis learner is already studying. Design a 3-5 step momentum or "
            "recovery mission sized for one focused session that creates a quick win.\n"
        )

    messages = [{
        "role": "user",
        "content": (
            f"Recommend the next mission for {learner.learner_name}.\n\n"
            f"{active_text}\n"
            f"Missions completed so far: {completed_count}\n"
            f"{stage_text}\n"
            f"Use the learner snapshot to judge their stage (onboarding, in-progress, returning after break).\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "mission_title": "...",\n'
            f'  "mission_description": "One sentence describing the mission",\n'
            f'  "purpose": "The quick win / feeling this mission creates",\n'
            f'  "reward_xp": 0,\n'
            f'  "badge": "badge name or null",\n'
            f'  "steps": [\n'
            f'    {{"order": 1, "title": "...", "description": "Concrete action"}}\n'
            f'  ],\n'
            f'  "message": "Short motivational message to {learner.learner_name} explaining the mission and why it matters"\n'
            f'}}\n\n'
            f"Rules:\n"
            f"- steps must have consecutive order numbers starting at 1, 3-5 steps total\n"
            f"- reward_xp is a small round number (50-300) proportional to effort\n"
            f"- badge is null unless the mission is a notable milestone\n"
            f"- message must be specific to {learner.learner_name}'s actual data, warm, and short"
        )
    }]

    return system, messages


# ── Guide Mission Prompt ──────────────────────────────────────────────────────

def guide_mission_prompt(learner: LearnerContext) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for guiding the next mission step."""
    system = _mission_system_prompt(learner)

    active = learner.missions.active_mission if learner.missions else None

    if active:
        mission_title = active.title
        completed = [s for s in active.steps if s.completed]
        remaining = [s for s in active.steps if not s.completed]
        completed_text = (
            "\n".join(f"  [x] {s.order}. {s.title}" for s in completed)
            if completed else "  (none yet)"
        )
        remaining_text = (
            "\n".join(f"  [ ] {s.order}. {s.title}" for s in remaining)
            if remaining else "  (all steps complete)"
        )
        mission_text = (
            f"ACTIVE MISSION: {active.title} (+{active.reward_xp} XP)\n"
            f"Purpose: {active.purpose}\n"
            f"Completed steps:\n{completed_text}\n"
            f"Remaining steps:\n{remaining_text}"
        )
    else:
        mission_title = "No active mission"
        mission_text = "The learner has NO active mission."

    messages = [{
        "role": "user",
        "content": (
            f"Guide {learner.learner_name} through their active mission.\n\n"
            f"{mission_text}\n\n"
            f"Identify the NEXT step — the first remaining (incomplete) step in order.\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "mission_title": "{mission_title}",\n'
            f'  "next_step": {{\n'
            f'    "order": 0,\n'
            f'    "title": "...",\n'
            f'    "description": "..."\n'
            f'  }},\n'
            f'  "message": "A warm, specific nudge for the next step"\n'
            f'}}\n\n'
            f"Rules:\n"
            f"- next_step must be the first incompleted step in order.\n"
            f"- If all steps are complete, congratulate the learner, mention the reward earned, and suggest requesting a new mission.\n"
            f"- If there is no active mission, ask {learner.learner_name} to request a mission recommendation (call /mission/recommend).\n"
            f"- message must be concrete, encouraging, and specific — reference the mission purpose and progress."
        )
    }]

    return system, messages