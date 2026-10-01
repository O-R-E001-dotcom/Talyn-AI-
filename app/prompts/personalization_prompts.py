
"""
Talyn — Content Personalization Prompts

Prompt builders for reframing course content through a learner's interests.
Covers four content types: explanation, example, quiz_context, exercise_brief.
"""

from app.models.schemas import PersonalizationProfile, ContentType


# ── System Prompt ─────────────────────────────────────────────────────────────

def _personalization_system_prompt(learner: PersonalizationProfile) -> str:
    return f"""You are Talyn Content Personalizer, an AI engine that rewrites course content so it resonates personally with each learner.

YOUR TASK
─────────
Take original course content and rewrite it so the core concept, facts, and learning objective remain 100% intact — but the framing, examples, and analogies are drawn from the learner's personal interests.

LEARNER PROFILE
───────────────
Name:            {learner.learner_name}
Interests:       {', '.join(learner.interests)}
Difficulty:      {learner.difficulty_level.value}
Course:          {learner.current_course}
Topic:           {learner.current_topic}

RULES
─────
1. NEVER change the factual content, core concept, or learning objective.
2. ALWAYS anchor at least one concrete analogy or example to the learner's interests.
3. Match the depth and vocabulary to the learner's difficulty level ({learner.difficulty_level.value}).
4. Do not force every interest — pick whichever fits most naturally for the content.
5. Keep the same approximate length as the original unless the content type requires otherwise.
6. Do not add fluff, filler, or unrelated tangents.
7. Write in second person ("you", "your") to feel direct and personal.
8. Return ONLY valid JSON — no markdown fences, no preamble."""


# ── Content-Type Instructions ─────────────────────────────────────────────────

_CONTENT_TYPE_INSTRUCTIONS = {
    ContentType.EXPLANATION: (
        "Rewrite this lesson explanation so it uses analogies from the learner's interests "
        "to make the concept click. The technical accuracy must be preserved exactly."
    ),
    ContentType.EXAMPLE: (
        "Rewrite this example so the scenario or context is drawn from the learner's interests. "
        "The concept being illustrated must remain identical — only the real-world context changes."
    ),
    ContentType.QUIZ_CONTEXT: (
        "Rewrite this quiz question's scenario/context so it uses a setting from the learner's interests. "
        "The question being tested, the correct answer, and the difficulty must not change."
    ),
    ContentType.EXERCISE_BRIEF: (
        "Rewrite this exercise or project brief so the task is set in a context the learner finds "
        "personally relevant. The skills being practiced and deliverables must remain identical."
    ),
}


# ── Single Personalization Prompt ─────────────────────────────────────────────

def personalize_content_prompt(
    learner: PersonalizationProfile,
    content_type: ContentType,
    original_content: str,
) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for personalizing a single piece of content."""
    system = _personalization_system_prompt(learner)
    instruction = _CONTENT_TYPE_INSTRUCTIONS[content_type]

    messages = [{
        "role": "user",
        "content": (
            f"Content type: {content_type.value}\n\n"
            f"Instruction: {instruction}\n\n"
            f"ORIGINAL CONTENT\n"
            f"────────────────\n"
            f"{original_content}\n\n"
            f"Return ONLY this JSON structure:\n"
            f'{{\n'
            f'  "personalized_content": "The full rewritten content",\n'
            f'  "interest_used": "The specific interest you wove in (single word or short phrase)"\n'
            f'}}'
        )
    }]

    return system, messages


# ── Batch Personalization Prompt ──────────────────────────────────────────────

def batch_personalize_prompt(
    learner: PersonalizationProfile,
    items: list[dict],
) -> tuple[str, list[dict]]:
    """
    Returns (system_prompt, messages) for personalizing multiple pieces in one call.
    Each item in `items` must have keys: content_type, original_content.
    """
    system = _personalization_system_prompt(learner)

    items_text = ""
    for i, item in enumerate(items):
        ct = ContentType(item["content_type"])
        instruction = _CONTENT_TYPE_INSTRUCTIONS[ct]
        items_text += (
            f"ITEM {i + 1}\n"
            f"Content type: {ct.value}\n"
            f"Instruction: {instruction}\n"
            f"Original content:\n{item['original_content']}\n\n"
        )

    messages = [{
        "role": "user",
        "content": (
            f"Personalize each of the following {len(items)} content items "
            f"for {learner.learner_name} using their interests: {', '.join(learner.interests)}.\n\n"
            f"{items_text}"
            f"Return ONLY a JSON array with exactly {len(items)} objects, in the same order:\n"
            f'[\n'
            f'  {{\n'
            f'    "content_type": "...",\n'
            f'    "original_content": "...(copy the original exactly)",\n'
            f'    "personalized_content": "...",\n'
            f'    "interest_used": "..."\n'
            f'  }}\n'
            f']'
        )
    }]

    return system, messages
