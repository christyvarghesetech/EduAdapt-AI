"""
Tutor / Re-teaching Agent — re-explains a concept using a DIFFERENT method
than what already failed (analogy, visual description, worked example,
Socratic dialogue), using Groq.
"""

import os
import json
from groq_client import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "MOCK_KEY")

TEACHING_METHODS = ["analogy", "visual", "worked_example", "socratic"]

TUTOR_SYSTEM_PROMPT = """You are the Tutor / Re-teaching Agent in an adaptive tutoring system.

You will be given:
- the topic/skill the student is struggling with
- why they got it wrong (error_type + reasoning from the Diagnostic Agent)
- which teaching methods have ALREADY been tried and failed for this student
- the student's learning-style preference, if known

Pick ONE teaching method from this list that has NOT already been tried:
["analogy", "visual", "worked_example", "socratic"]

- analogy: explain via a relatable real-world comparison
- visual: describe a diagram/visual mental model in words (frontend can render it)
- worked_example: step-by-step solved example, then a near-identical practice step
- socratic: guide the student to the answer via a sequence of leading questions

Respond with ONLY valid JSON, no other text, matching this schema:
{
  "method_used": "analogy|visual|worked_example|socratic",
  "explanation": "<the actual teaching content shown to the student>",
  "check_for_understanding_question": "<a quick low-stakes question to confirm the explanation landed, before moving to the full quiz>"
}
"""

def teach(root_cause_topic: str, error_type: str, diagnosis_reasoning: str,
          methods_already_tried: list[str], learning_style: str | None = None) -> dict:
    user_payload = {
        "root_cause_topic": root_cause_topic,
        "error_type": error_type,
        "diagnosis_reasoning": diagnosis_reasoning,
        "methods_already_tried": methods_already_tried,
        "learning_style_preference": learning_style or "unknown",
        "available_methods": [m for m in TEACHING_METHODS if m not in methods_already_tried],
    }

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # fast — student is waiting live
        messages=[
            {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        temperature=0.6,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result


if __name__ == "__main__":
    result = teach(
        root_cause_topic="linear_equations_isolation",
        error_type="procedural",
        diagnosis_reasoning="Student added 5 instead of subtracting it when isolating x.",
        methods_already_tried=["worked_example"],
        learning_style="visual",
    )
    print(json.dumps(result, indent=2))