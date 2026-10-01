"""
Talyn AI Learning Coach — Prompt Library

All prompts live here so the team can iterate on them independently
from the API logic. Each function returns a fully-formed string ready
to be passed to the Claude API.
"""

from app.models.schemas import LearnerContext


# ── Shared Helpers ────────────────────────────────────────────────────────────

def _build_learner_profile(learner: LearnerContext) -> str:
    """Renders a compact learner snapshot injected into every prompt."""
    quiz_summary = ""
    if learner.quiz_performance:
        lines = [
            f"  - {q.topic}: {q.score_percent:.0f}% ({q.attempts} attempt(s))"
            for q in learner.quiz_performance
        ]
        quiz_summary = "Quiz performance:\n" + "\n".join(lines)
    else:
        quiz_summary = "Quiz performance: No quizzes taken yet."

    plan_summary = ""
    if learner.study_plan:
        p = learner.study_plan
        plan_summary = (
            f"Study plan: {p.daily_goal_minutes} min/day, "
            f"{p.weekly_target_lessons} lessons/week, "
            f"focusing on: {', '.join(p.focus_topics)}"
            + (f", deadline: {p.deadline}" if p.deadline else "")
        )
    else:
        plan_summary = "Study plan: Not yet created."

    level_summary = ""
    if learner.level:
        lvl = learner.level
        level_summary = (
            f"{lvl.level} — {lvl.title} "
            f"({lvl.xp_this_level}/{lvl.level_up_xp} XP to {lvl.next_level_title})"
        )
    else:
        level_summary = "Not yet assigned"

    badge_summary = ""
    if learner.badges:
        badge_lines = [f"  - {b.name}: {b.description}" for b in learner.badges]
        badge_summary = "Badges earned:\n" + "\n".join(badge_lines)
    else:
        badge_summary = "Badges earned: None yet"

    xp_breakdown_summary = ""
    if learner.xp_breakdown:
        totals: dict[str, int] = {}
        for e in learner.xp_breakdown:
            totals[e.activity.value] = totals.get(e.activity.value, 0) + e.amount
        xp_lines = [f"  - {activity}: {amount} XP" for activity, amount in totals.items()]
        xp_breakdown_summary = "XP by activity (all time):\n" + "\n".join(xp_lines)
    else:
        xp_breakdown_summary = "XP by activity: Not yet tracked"

    mission_summary = ""
    if learner.missions:
        m = learner.missions
        if m.active_mission:
            mission = m.active_mission
            step_lines = "\n".join(
                f"    {'[x]' if s.completed else '[ ]'} {s.order}. {s.title}"
                for s in mission.steps
            )
            mission_summary = (
                f"Active mission: {mission.title} "
                f"(+{mission.reward_xp} XP on completion)\n"
                f"  {mission.purpose}\n"
                f"  Steps:\n{step_lines}"
            )
        elif m.completed_mission_count:
            mission_summary = (
                f"Missions completed: {m.completed_mission_count} — "
                f"No active mission."
            )
        else:
            mission_summary = "Missions: Not yet started."

    else:
        mission_summary = "Missions: Not yet tracked"

    goals_line = f"Goals:            {learner.goals}\n\n" if learner.goals else "\n"

    return f"""
LEARNER PROFILE
───────────────
Name:              {learner.learner_name}
Difficulty level:  {learner.difficulty_level.value}
Interests:         {', '.join(learner.interests)}
{goals_line}CURRENT POSITION
────────────────
Course:   {learner.current_course}
Lesson:   {learner.current_lesson}
Topic:    {learner.current_topic}

PROGRESS
────────
Completion:       {learner.completion_percent:.0f}% ({learner.lessons_completed}/{learner.lessons_total} lessons)
XP total:         {learner.xp_total} XP
XP this week:     {learner.xp_this_week} XP
Level:            {level_summary}
Streak:           {learner.streak_days} day(s)

{badge_summary}

{xp_breakdown_summary}

{mission_summary}

{quiz_summary}

{plan_summary}
""".strip()


def _build_system_prompt(learner: LearnerContext) -> str:
    """
    Core identity and behavioral rules for the Talyn AI Learning Coach.
    This is the system prompt — sent with every request.
    """
    return f"""You are Talyn Coach, an AI learning companion built into the Talyn learning platform.

YOUR CORE PURPOSE
─────────────────
Help {learner.learner_name} successfully complete their courses by providing
personalized support, clear explanations, motivation, and structured guidance.
You are not a generic chatbot — you are deeply aware of where this learner is
in their journey and tailor every response to their context.

YOUR PERSONALITY — ADAPTIVE
────────────────────────────
You read the learner's situation and shift your tone accordingly:

- Struggling or frustrated → Warm, patient, reassuring. Slow down, simplify.
- Doing well / on a streak → Energetic, celebratory, keep momentum going.
- Asking a technical question → Precise and clear, but never cold or robotic.
- Just starting out → Extra encouraging, make them feel capable.
- Returning after a break → Welcoming, zero judgment, ease them back in.

Always sound like a knowledgeable friend — never stiff, never preachy.
Use the learner's name naturally, but not in every sentence.

PERSONALIZATION RULES
──────────────────────
- The learner's interests are: {', '.join(learner.interests)}.
  Whenever you give examples, use these interests to make content feel relevant.
- Match explanation depth to their difficulty level: {learner.difficulty_level.value}.
- Reference their actual progress data when encouraging or advising — be specific,
  not generic ("You've completed 60% of this course" not "You're making progress").

BOUNDARIES
──────────
- Only discuss topics related to learning, the current course, study strategies,
  or motivation. Politely redirect anything unrelated.
- Never make up course content. If you don't know a specific fact about their
  course material, say so honestly and suggest where to find it.
- Keep responses focused. Do not pad with unnecessary filler or over-explain.

{_build_learner_profile(learner)}"""


# ── Action Prompts ────────────────────────────────────────────────────────────

def answer_question_prompt(learner: LearnerContext, question: str) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for answering a learner question."""
    system = _build_system_prompt(learner)

    # Replay conversation history so the coach has full context
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in learner.conversation_history
    ]

    # Append the new question
    messages.append({
        "role": "user",
        "content": (
            f"I'm currently studying '{learner.current_topic}' in the lesson "
            f"'{learner.current_lesson}'. Here's my question:\n\n{question}"
        )
    })

    return system, messages


def explain_concept_prompt(learner: LearnerContext, concept: str) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for explaining a concept."""
    system = _build_system_prompt(learner)

    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in learner.conversation_history
    ]
    messages.append({
        "role": "user",
        "content": (
            f"Can you explain '{concept}' to me? I'm at the {learner.difficulty_level.value} level. "
            f"Please use an example related to one of my interests ({', '.join(learner.interests)}) "
            f"if it helps make it clearer."
        )
    })

    return system, messages


def create_study_plan_prompt(learner: LearnerContext, goals: str) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for generating a study plan."""
    system = _build_system_prompt(learner)

    weak_topics = [
        q.topic for q in learner.quiz_performance if q.score_percent < 70
    ]
    weak_topics_text = (
        f"Topics where I've scored below 70%: {', '.join(weak_topics)}."
        if weak_topics else ""
    )

    messages = [{
        "role": "user",
        "content": (
            f"Please create a personalized study plan for me.\n\n"
            f"My goals: {goals}\n"
            f"Course progress: {learner.completion_percent:.0f}% complete "
            f"({learner.lessons_completed}/{learner.lessons_total} lessons done).\n"
            f"{weak_topics_text}\n\n"
            f"Structure the plan with:\n"
            f"1. A brief assessment of where I stand\n"
            f"2. Daily recommended study time and focus\n"
            f"3. Weekly milestones\n"
            f"4. Specific topics to prioritize\n"
            f"5. A motivating closing note\n\n"
            f"Account for their XP status ({learner.xp_total} XP total, "
            f"{learner.xp_this_week} XP this week) and include realistic XP goals "
            f"or mini-milestones (e.g. 'earn X XP this week', 'reach the next level') "
            f"where they help maintain momentum.\n\n"
            f"Be specific and realistic. Don't be generic."
        )
    }]

    return system, messages


def encourage_prompt(learner: LearnerContext, trigger: str) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for a contextual encouragement message."""
    system = _build_system_prompt(learner)

    level_ref = ""
    if learner.level:
        lvl = learner.level
        remaining = max(0, lvl.level_up_xp - lvl.xp_this_level)
        level_ref = (
            f" They are {remaining} XP away from reaching '{lvl.next_level_title}'."
        )

    messages = [{
        "role": "user",
        "content": (
            f"[SYSTEM TRIGGER: {trigger}]\n\n"
            f"Generate an encouragement message for {learner.learner_name} "
            f"based on this trigger. Be specific to their actual data — reference "
            f"their streak ({learner.streak_days} days), XP ({learner.xp_total}), "
            f"completion ({learner.completion_percent:.0f}%), or badges where relevant."
            f"{level_ref}\n\n"
            f"If appropriate, suggest one concrete next action to earn more XP "
            f"(e.g. finish a lesson, retake a quiz, keep the streak alive). "
            f"Keep it short, warm, and genuine. No hollow cheerleading."
        )
    }]

    return system, messages


def generate_quiz_prompt(learner: LearnerContext, topic: str, num_questions: int) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for generating a quiz."""
    system = _build_system_prompt(learner)

    # Check prior performance on this topic
    prior = next(
        (q for q in learner.quiz_performance if q.topic.lower() == topic.lower()),
        None
    )
    prior_context = (
        f"The learner has attempted this topic before and scored {prior.score_percent:.0f}%. "
        f"Adjust difficulty accordingly — focus on areas likely to be weak."
        if prior else
        "This is the learner's first quiz on this topic."
    )

    messages = [{
        "role": "user",
        "content": (
            f"Generate a {num_questions}-question multiple choice quiz on '{topic}' "
            f"for a {learner.difficulty_level.value}-level learner.\n\n"
            f"{prior_context}\n\n"
            f"Return ONLY valid JSON. No markdown, no explanation, no preamble.\n\n"
            f"Format:\n"
            f'{{\n'
            f'  "questions": [\n'
            f'    {{\n'
            f'      "question": "...",\n'
            f'      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],\n'
            f'      "correct_answer": "A. ...",\n'
            f'      "explanation": "..."\n'
            f'    }}\n'
            f'  ]\n'
            f'}}'
        )
    }]

    return system, messages
