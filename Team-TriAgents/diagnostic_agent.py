"""
Diagnostic Agent — identifies root cause of a student's wrong answer
(conceptual / procedural / prerequisite gap / careless slip) using Groq.
"""

import os
import json
from groq_client import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "MOCK_KEY")

DIAGNOSTIC_SYSTEM_PROMPT = """You are the Diagnostic Agent in an adaptive tutoring system.

Given a student's question, their wrong answer, and their recent error history,
classify the ROOT CAUSE of the mistake. Do not just say it's "wrong" — determine WHY.

Categories:
- conceptual: student misunderstands the underlying idea
- procedural: student understands the idea but applies the steps incorrectly
- prerequisite: student is missing a foundational skill needed for this topic
- careless_slip: student likely knows this but made an execution error (typo, arithmetic slip)

Respond with ONLY valid JSON, no other text, matching this schema:
{
  "error_type": "conceptual|procedural|prerequisite|careless_slip",
  "root_cause_topic": "<specific topic/skill responsible>",
  "confidence_score": <float 0-1>,
  "reasoning": "<1-2 sentence explanation>"
}
"""

def diagnose(question: str, student_answer: str, correct_answer: str,
             recent_error_history: list[dict]) -> dict:
    """
    recent_error_history: list of {"topic": str, "error_type": str} from past attempts,
    used to detect recurring patterns (e.g. same prerequisite gap showing up repeatedly).
    """
    user_payload = {
        "question": question,
        "student_answer": student_answer,
        "correct_answer": correct_answer,
        "recent_error_history": recent_error_history,
    }

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": DIAGNOSTIC_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result


if __name__ == "__main__":
    result = diagnose(
        question="Solve for x: 2x + 5 = 15",
        student_answer="x = 10",
        correct_answer="x = 5",
        recent_error_history=[
            {"topic": "linear_equations_isolation", "error_type": "procedural"},
            {"topic": "linear_equations_isolation", "error_type": "procedural"},
        ],
    )
    print(json.dumps(result, indent=2))