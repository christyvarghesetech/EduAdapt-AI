"""
Assessment / Quiz Generator Agent — creates fresh, non-repetitive questions
targeting a specific identified gap, at a given difficulty level, using Groq.
"""

import os
import json
from groq_client import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "MOCK_KEY")

QUIZ_SYSTEM_PROMPT = """You are the Assessment / Quiz Generator Agent in an adaptive tutoring system.

Generate NEW practice questions that target a specific skill/topic gap.
Questions must NOT be near-duplicates (same numbers, same phrasing/structure)
of any question in previously_asked — vary the surface details while still
testing the same underlying skill.

Match the requested difficulty level:
- easy: single-step, minimal distraction
- medium: multi-step or requires combining two ideas
- hard: multi-step + requires transfer to an unfamiliar framing

Respond with ONLY valid JSON, no other text, matching this schema:
{
  "questions": [
    {
      "question_id": "<short unique id>",
      "question_text": "<the question>",
      "question_type": "objective|open_ended",
      "expected_answer_or_rubric": "<exact answer, or grading rubric if open_ended>",
      "difficulty": "easy|medium|hard"
    }
  ]
}
"""

def generate_quiz(root_cause_topic: str, difficulty: str,
                   previously_asked: list[str], num_questions: int = 3,
                   question_type: str = "objective") -> dict:
    user_payload = {
        "root_cause_topic": root_cause_topic,
        "difficulty": difficulty,
        "previously_asked_questions": previously_asked,
        "num_questions": num_questions,
        "question_type": question_type,
    }

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # fast — generated live between teach and evaluate
        messages=[
            {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        temperature=0.8,  # higher temp helps avoid repetitive question phrasing
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result


if __name__ == "__main__":
    result = generate_quiz(
        root_cause_topic="linear_equations_isolation",
        difficulty="medium",
        previously_asked=["Solve for x: 2x + 5 = 15"],
        num_questions=2,
        question_type="objective",
    )
    print(json.dumps(result, indent=2))