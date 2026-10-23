from typing import Any, Dict, List, Tuple


def calculate_next_difficulty(current_difficulty: int, is_correct: bool) -> int:
    """
    Step ladder adaptive progression rule:
    - Difficulty is bounded in [1, 3] (1: Beginner, 2: Intermediate, 3: Advanced).
    - Correct answer: steps up (+1, capped at 3).
    - Incorrect answer: steps down (-1, floored at 1).
    """
    if is_correct:
        return min(3, current_difficulty + 1)
    else:
        return max(1, current_difficulty - 1)


def evaluate_final_level(
    answers: List[Dict[str, Any]],
) -> Tuple[str, str, int, int, List[str], str]:
    """
    Pure function to evaluate demonstrated proficiency level and confidence.

    Rules & Minimum Answers per Level:
    1. 'advanced':
       - Must have attempted at least 2 questions at difficulty 3.
       - Must achieve at least 60% accuracy on difficulty 3 questions.
       - Overall accuracy must be >= 60%.
    2. 'intermediate':
       - Must have attempted at least 2 questions at difficulty >= 2.
       - Must achieve at least 50% accuracy on difficulty >= 2 questions.
       - Overall accuracy must be >= 40%.
    3. 'beginner':
       - Default when higher thresholds or minimum answer counts are not satisfied.

    Confidence:
    - 'low': < 3 answers (insufficient statistical sample).
    - 'medium': 3 to 5 answers.
    - 'high': >= 6 answers with converged stability.

    Returns:
    (demonstrated_level, confidence, score_percentage, total_correct, recommendations, disclaimer_note)
    """
    disclaimer_note = "This level is a preliminary estimate from a short adaptive diagnostic test."

    total_answered = len(answers)
    if total_answered == 0:
        return (
            "beginner",
            "low",
            0,
            0,
            ["Complete diagnostic assessment to establish baseline skill proficiency."],
            disclaimer_note,
        )

    total_correct = sum(1 for a in answers if a.get("is_correct"))
    score_percentage = int(round((total_correct / total_answered) * 100.0))

    d3_answers = [a for a in answers if a.get("difficulty") == 3]
    d2_plus_answers = [a for a in answers if a.get("difficulty", 1) >= 2]

    d3_count = len(d3_answers)
    d3_correct = sum(1 for a in d3_answers if a.get("is_correct"))
    d3_acc = (d3_correct / d3_count) if d3_count > 0 else 0.0

    d2_plus_count = len(d2_plus_answers)
    d2_plus_correct = sum(1 for a in d2_plus_answers if a.get("is_correct"))
    d2_plus_acc = (d2_plus_correct / d2_plus_count) if d2_plus_count > 0 else 0.0

    overall_acc = total_correct / total_answered

    # Determine demonstrated level
    if d3_count >= 2 and d3_acc >= 0.60 and overall_acc >= 0.60:
        demonstrated_level = "advanced"
        recommendations = [
            "Demonstrated strong mastery of core principles and advanced problem patterns.",
            "Recommended next step: build production-grade end-to-end projects or tackle contest-level challenges.",
        ]
    elif d2_plus_count >= 2 and d2_plus_acc >= 0.50 and overall_acc >= 0.40:
        demonstrated_level = "intermediate"
        recommendations = [
            "Solid grasp of fundamental constructs with emerging intermediate fluency.",
            "Recommended next step: focus on edge cases, algorithmic complexity, and idiomatic design patterns.",
        ]
    else:
        demonstrated_level = "beginner"
        recommendations = [
            "Foundational familiarity established.",
            "Recommended next step: review core syntax, fundamental data types, and standard library primitives.",
        ]

    # Determine confidence
    if total_answered < 3:
        confidence = "low"
    elif total_answered < 6:
        confidence = "medium"
    else:
        # Check stability
        last_two = answers[-2:]
        if len(set(a.get("difficulty") for a in last_two)) == 1:
            confidence = "high"
        else:
            confidence = "medium"

    return (
        demonstrated_level,
        confidence,
        score_percentage,
        total_correct,
        recommendations,
        disclaimer_note,
    )
