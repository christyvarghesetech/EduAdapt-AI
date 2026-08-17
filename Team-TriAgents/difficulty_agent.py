"""
Difficulty Calibration Agent — adjusts question/content difficulty
dynamically based on mastery trajectory, similar to adaptive testing (IRT).

Deliberately NOT an LLM call: difficulty adjustment is a numeric decision
based on recent score history, so a lightweight deterministic rule (with an
optional logistic/IRT-style curve) is faster and more predictable than
asking a model to "guess" the right difficulty every time.
"""

import math

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]
DIFFICULTY_INDEX = {level: i for i, level in enumerate(DIFFICULTY_LEVELS)}


def _trajectory_signal(recent_scores: list[float]) -> float:
    """
    Weighted recent performance signal, -1 to 1.
    Recent attempts count more than older ones (simple recency weighting).
    """
    if not recent_scores:
        return 0.0
    weights = [i + 1 for i in range(len(recent_scores))]  # older -> smaller weight
    weighted_sum = sum(s * w for s, w in zip(recent_scores, weights))
    total_weight = sum(weights)
    avg = weighted_sum / total_weight  # 0-1 scale (assuming scores are 0-1)
    return (avg - 0.5) * 2  # rescale to -1..1


def calibrate_difficulty(current_difficulty: str, recent_scores: list[float],
                          current_mastery: float,
                          consecutive_correct: int = 0,
                          consecutive_wrong: int = 0) -> dict:
    """
    recent_scores: last N evaluator scores (0-1) for this topic, most recent last.
    Returns the next difficulty level + reasoning, IRT-inspired: move up on a
    streak of strong performance, move down on a streak of struggle, otherwise hold.
    """
    current_idx = DIFFICULTY_INDEX.get(current_difficulty, 1)
    signal = _trajectory_signal(recent_scores)

    # Strong streak -> step up; struggling streak -> step down; else hold.
    if consecutive_correct >= 2 and signal > 0.3 and current_mastery > 0.5:
        new_idx = min(current_idx + 1, len(DIFFICULTY_LEVELS) - 1)
        reason = "Consistent strong performance — increasing challenge."
    elif consecutive_wrong >= 2 or signal < -0.3:
        new_idx = max(current_idx - 1, 0)
        reason = "Recent struggle detected — reducing difficulty to rebuild confidence."
    else:
        new_idx = current_idx
        reason = "Performance stable — holding current difficulty."

    return {
        "difficulty": DIFFICULTY_LEVELS[new_idx],
        "previous_difficulty": current_difficulty,
        "trajectory_signal": round(signal, 3),
        "reason": reason,
    }


if __name__ == "__main__":
    result = calibrate_difficulty(
        current_difficulty="medium",
        recent_scores=[0.9, 1.0, 0.85],
        current_mastery=0.65,
        consecutive_correct=3,
    )
    print(result)

    result2 = calibrate_difficulty(
        current_difficulty="medium",
        recent_scores=[0.2, 0.1],
        current_mastery=0.25,
        consecutive_wrong=2,
    )
    print(result2)