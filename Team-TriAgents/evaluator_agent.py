"""
Evaluator Agent — grades student responses (including open-ended/subjective
answers) and produces a mastery score, not just right/wrong, using Groq.
"""

import os
import json
from groq_client import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "MOCK_KEY")

EVALUATOR_SYSTEM_PROMPT = """You are the Evaluator Agent in an adaptive tutoring system.

Grade the student's response against the rubric/expected answer. Support both
objective (single correct answer) and open-ended/subjective responses.

Do not just mark right/wrong — estimate MASTERY: how well the student's response
reflects real understanding of the target skill, on a continuous scale.

Respond with ONLY valid JSON, no other text, matching this schema:
{
  "is_correct": <bool>,
  "score": <float 0-1, partial credit allowed>,
  "mastery_delta": <float -1 to 1, how much this response should shift mastery estimate>,
  "gap_closed": <bool, true if this response demonstrates the previously identified gap is resolved>,
  "feedback": "<1-2 sentence feedback for the student>"
}
"""

def evaluate(question: str, rubric_or_expected_answer: str,
             student_response: str, target_skill: str,
             current_mastery: float) -> dict:
    user_payload = {
        "question": question,
        "rubric_or_expected_answer": rubric_or_expected_answer,
        "student_response": student_response,
        "target_skill": target_skill,
        "current_mastery": current_mastery,
    }

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        # Local Fallback Evaluator (used on rate limits or connection loss)
        import difflib
        
        ans_lower = student_response.lower().strip()
        expected_lower = rubric_or_expected_answer.lower().strip()
        
        # Check for empty or dummy placeholder inputs
        if len(ans_lower) < 2 or ans_lower in ["nonsense", "9999", "dunno", "don't know", "idk"]:
            is_correct = False
            score = 0.0
            feedback = "The answer was empty or identified as a placeholder response. Let's study this topic!"
        else:
            # Word overlap similarity
            expected_words = set(w for w in expected_lower.split() if len(w) > 3)
            ans_words = set(w for w in ans_lower.split() if len(w) > 3)
            
            overlap = 0.0
            if expected_words:
                matched_words = expected_words.intersection(ans_words)
                overlap = len(matched_words) / len(expected_words)
                
            similarity = difflib.SequenceMatcher(None, ans_lower, expected_lower).ratio()
            score = max(overlap, similarity)
            is_correct = score >= 0.35
            
            if is_correct:
                feedback = "Good answer! Concept match confirmed via text-overlap evaluation."
            else:
                feedback = "Review required. Some core elements were missing from your explanation."
                
        mastery_delta = 0.3 if is_correct else -0.2
        
        return {
            "is_correct": is_correct,
            "score": round(score, 2),
            "mastery_delta": mastery_delta,
            "gap_closed": is_correct,
            "feedback": f"[Local Evaluator] {feedback}"
        }


if __name__ == "__main__":
    result = evaluate(
        question="Explain why TCP guarantees delivery but UDP does not.",
        rubric_or_expected_answer="Should mention acknowledgments/retransmission "
                                   "(TCP) vs connectionless, no ack (UDP).",
        student_response="TCP checks if packets arrived and resends if not, "
                          "UDP just sends and doesn't check.",
        target_skill="tcp_udp_reliability",
        current_mastery=0.4,
    )
    print(json.dumps(result, indent=2))