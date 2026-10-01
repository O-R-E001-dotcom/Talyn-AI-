
"""
Talyn Content Personalization — Tests

Run with:
    pytest tests/test_personalization.py -v -s

Requires ANTHROPIC_API_KEY to be set in your environment.
"""

import pytest
from app.models.schemas import (
    PersonalizationProfile, DifficultyLevel, ContentType,
)
from app.services import personalization_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def football_learner() -> PersonalizationProfile:
    return PersonalizationProfile(
        learner_id="learner_001",
        learner_name="Adeola",
        interests=["football", "music", "technology"],
        difficulty_level=DifficultyLevel.BEGINNER,
        current_course="UI/UX Design Fundamentals",
        current_topic="CSS Flexbox",
    )


@pytest.fixture
def gaming_learner() -> PersonalizationProfile:
    return PersonalizationProfile(
        learner_id="learner_002",
        learner_name="Tunde",
        interests=["gaming", "fintech", "basketball"],
        difficulty_level=DifficultyLevel.INTERMEDIATE,
        current_course="UX Research Methods",
        current_topic="User Interviews",
    )


# ── Original content samples ──────────────────────────────────────────────────

ORIGINAL_EXPLANATION = """
CSS Flexbox is a one-dimensional layout model that allows you to distribute 
space and align items within a container. When you set a container to 
display: flex, its children become flex items. The main axis runs in the 
direction defined by flex-direction (row by default), and the cross axis 
runs perpendicular to it. You use justify-content to align items along 
the main axis and align-items to align them along the cross axis.
""".strip()

ORIGINAL_EXAMPLE = """
Imagine you have a navigation bar with a logo on the left and three menu 
links on the right. Using Flexbox, you would set the nav element to 
display: flex and justify-content: space-between. This pushes the logo 
to one end and the links cluster to the other, with all the available 
space distributed between them.
""".strip()

ORIGINAL_QUIZ_CONTEXT = """
A web developer is building a dashboard for a hospital management system. 
They need to display four equal-width metric cards side by side in a row. 
When the viewport is narrow, the cards should stack vertically. 
Which Flexbox properties would achieve this layout?
""".strip()

ORIGINAL_EXERCISE_BRIEF = """
Build a responsive product card grid for an e-commerce website. 
Your grid should display 3 cards per row on desktop, 2 on tablet, 
and 1 on mobile. Each card must contain a product image, title, 
price, and an 'Add to Cart' button pinned to the bottom. 
Use only Flexbox for the layout — no CSS Grid.
""".strip()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_personalize_explanation(football_learner):
    result = personalization_service.personalize_content(
        football_learner,
        ContentType.EXPLANATION,
        ORIGINAL_EXPLANATION,
    )

    assert result.learner_id == "learner_001"
    assert result.content_type == ContentType.EXPLANATION
    assert result.original_content == ORIGINAL_EXPLANATION
    assert len(result.personalized_content) > 50

    # Core CSS concepts must survive personalization
    content_lower = result.personalized_content.lower()
    assert "flex" in content_lower
    assert "justify" in content_lower or "align" in content_lower

    # Should reference at least one interest
    interests_found = [i for i in football_learner.interests if i in content_lower]
    assert len(interests_found) >= 1, "No learner interest found in personalized content"

    assert result.interest_used != ""

    print(f"\n[EXPLANATION — football learner]")
    print(f"Interest used: {result.interest_used}")
    print(f"\nOriginal:\n{result.original_content}")
    print(f"\nPersonalized:\n{result.personalized_content}")


def test_personalize_example(football_learner):
    result = personalization_service.personalize_content(
        football_learner,
        ContentType.EXAMPLE,
        ORIGINAL_EXAMPLE,
    )

    assert len(result.personalized_content) > 50
    # The original used a nav bar — personalized should use a different scenario
    assert result.personalized_content != ORIGINAL_EXAMPLE
    # But Flexbox properties should still appear
    assert "flex" in result.personalized_content.lower()

    print(f"\n[EXAMPLE — football learner]")
    print(f"Interest used: {result.interest_used}")
    print(f"\nPersonalized:\n{result.personalized_content}")


def test_personalize_quiz_context(gaming_learner):
    result = personalization_service.personalize_content(
        gaming_learner,
        ContentType.QUIZ_CONTEXT,
        ORIGINAL_QUIZ_CONTEXT,
    )

    assert len(result.personalized_content) > 50
    # Must still be asking about Flexbox layout
    content_lower = result.personalized_content.lower()
    assert "flex" in content_lower
    # Should not still be about a hospital — context should change
    assert "hospital" not in content_lower

    print(f"\n[QUIZ CONTEXT — gaming learner]")
    print(f"Interest used: {result.interest_used}")
    print(f"\nOriginal:\n{result.original_content}")
    print(f"\nPersonalized:\n{result.personalized_content}")


def test_personalize_exercise_brief(football_learner):
    result = personalization_service.personalize_content(
        football_learner,
        ContentType.EXERCISE_BRIEF,
        ORIGINAL_EXERCISE_BRIEF,
    )

    assert len(result.personalized_content) > 50
    content_lower = result.personalized_content.lower()

    # The technical requirements must survive
    assert "flex" in content_lower
    assert "mobile" in content_lower or "responsive" in content_lower

    # Should not still be about e-commerce generically
    interests_found = [i for i in football_learner.interests if i in content_lower]
    assert len(interests_found) >= 1

    print(f"\n[EXERCISE BRIEF — football learner]")
    print(f"Interest used: {result.interest_used}")
    print(f"\nPersonalized:\n{result.personalized_content}")


def test_batch_personalize(football_learner):
    items = [
        {"content_type": "explanation",    "original_content": ORIGINAL_EXPLANATION},
        {"content_type": "example",        "original_content": ORIGINAL_EXAMPLE},
        {"content_type": "exercise_brief", "original_content": ORIGINAL_EXERCISE_BRIEF},
    ]

    result = personalization_service.batch_personalize(football_learner, items)

    assert result.learner_id == "learner_001"
    assert len(result.items) == 3

    for item in result.items:
        assert len(item.personalized_content) > 30
        assert item.interest_used != ""
        assert item.original_content != ""

    print(f"\n[BATCH — football learner, {len(result.items)} items]")
    for i, item in enumerate(result.items):
        print(f"\n  Item {i+1} ({item.content_type}) — interest: {item.interest_used}")
        print(f"  {item.personalized_content[:200]}...")


def test_same_concept_different_interests(football_learner, gaming_learner):
    """The same content should produce meaningfully different outputs per learner."""
    result_football = personalization_service.personalize_content(
        football_learner, ContentType.EXAMPLE, ORIGINAL_EXAMPLE
    )
    result_gaming = personalization_service.personalize_content(
        gaming_learner, ContentType.EXAMPLE, ORIGINAL_EXAMPLE
    )

    assert result_football.personalized_content != result_gaming.personalized_content
    assert result_football.interest_used != result_gaming.interest_used

    print(f"\n[SAME CONTENT, DIFFERENT LEARNERS]")
    print(f"\nFootball learner ({result_football.interest_used}):\n{result_football.personalized_content}")
    print(f"\nGaming learner ({result_gaming.interest_used}):\n{result_gaming.personalized_content}")


def test_batch_size_validation():
    """Batch endpoint should reject requests with more than 5 items."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {
        "learner": {
            "learner_id": "learner_001",
            "learner_name": "Adeola",
            "interests": ["football"],
            "difficulty_level": "beginner",
            "current_course": "UI/UX Design",
            "current_topic": "Flexbox",
        },
        "items": [
            {"content_type": "explanation", "original_content": f"Content {i}"}
            for i in range(6)   # 6 items — should be rejected
        ]
    }
    response = client.post("/personalize/batch", json=payload)
    assert response.status_code == 400
    assert "Maximum batch size" in response.json()["detail"]
    print("\n[BATCH VALIDATION] Correctly rejected oversized batch ✓")
