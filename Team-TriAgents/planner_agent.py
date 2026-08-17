"""
Planner / Scheduler Agent — builds and continuously updates the study
roadmap: sequences topics, allocates time, and handles REPLAN escalations
from the Orchestrator (when a gap won't close after all teaching methods
have been tried).
"""

import os
import json
from datetime import datetime, timedelta, timezone
from groq_client import Groq
from dotenv import load_dotenv
from memory_agent import get_due_for_review, get_recent_error_history
from curriculum_mapping_agent import get_all_syllabus_weights, get_prerequisite_chain

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "MOCK_KEY")

PLANNER_SYSTEM_PROMPT = """You are the Planner / Scheduler Agent in an adaptive tutoring system.

You will be given:
- the student's mastery map (topic -> mastery score 0-1)
- topics due for spaced review (retention has decayed)
- syllabus weight per topic (importance for the exam/course)
- days remaining until the target date
- any topics just escalated from REPLAN (student is stuck despite all teaching methods)

Build a prioritized study roadmap. Prioritize by:
1. REPLAN-escalated topics — flag these for a different intervention (e.g. lower
   difficulty, human/teacher review, or a prerequisite topic first) rather than
   more of the same loop
2. Low mastery x high syllabus weight topics
3. Topics due for spaced review before they decay further
4. Remaining time budget

Respond with ONLY valid JSON, no other text, matching this schema:
{
  "roadmap": [
    {
      "topic": "<topic>",
      "priority_rank": <int, 1 = highest>,
      "reason": "<short reason>",
      "recommended_action": "review|new_teaching|prerequisite_first|escalate_to_human",
      "suggested_time_minutes": <int>
    }
  ],
  "notes": "<any overall strategy notes, e.g. topics to defer>"
}
"""

def build_roadmap(student_id: str, mastery_map: dict[str, float],
                   days_remaining: int,
                   replanned_topics: list[dict] | None = None,
                   syllabus_weights: dict[str, float] | None = None) -> dict:
    due_for_review = get_due_for_review(student_id)
    weights = syllabus_weights or get_all_syllabus_weights()

    user_payload = {
        "mastery_map": mastery_map,
        "syllabus_weights": weights,
        "due_for_review": due_for_review,
        "days_remaining": days_remaining,
        "replanned_topics": replanned_topics or [],
    }

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # planning benefits from stronger reasoning
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def handle_replan(student_id: str, root_cause_topic: str,
                   methods_tried: list[str]) -> dict:
    """
    Called by the Orchestrator when REPLAN is triggered: all teaching
    methods exhausted and the gap is still open. Decides the escalation
    action for this specific topic rather than rebuilding the whole roadmap.
    """
    recent = get_recent_error_history(student_id, topic=root_cause_topic, limit=5)
    prerequisite_chain = get_prerequisite_chain(root_cause_topic)

    escalation_payload = {
        "root_cause_topic": root_cause_topic,
        "methods_tried": methods_tried,
        "recent_error_history": recent,
        "known_prerequisite_chain": prerequisite_chain,
    }

    system_prompt = """You are handling a REPLAN escalation: a student has failed
to close a learning gap after every available teaching method was tried.

Decide the best next action:
- "prerequisite_first": the real issue is likely a missing prerequisite skill —
  pick the most likely culprit from known_prerequisite_chain (if provided) and
  recommend teaching that first
- "lower_difficulty": student may be overwhelmed — recommend an easier on-ramp
- "escalate_to_human": pattern suggests something a human teacher should look at
  (e.g. persistent confusion across many attempts, possible misconception that
  needs live discussion)
- "defer": deprioritize this topic for now and revisit later in the roadmap

Respond with ONLY valid JSON:
{
  "action": "prerequisite_first|lower_difficulty|escalate_to_human|defer",
  "target_topic": "<topic to teach instead, if prerequisite_first>",
  "reason": "<short reason>"
}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(escalation_payload)},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    roadmap = build_roadmap(
        student_id="student_001",
        mastery_map={"linear_equations_isolation": 0.3, "quadratic_equations": 0.1},
        days_remaining=14,
    )
    print(json.dumps(roadmap, indent=2))

    escalation = handle_replan(
        student_id="student_001",
        root_cause_topic="linear_equations_isolation",
        methods_tried=["analogy", "visual", "worked_example", "socratic"],
    )
    print(json.dumps(escalation, indent=2))