"""
Syllabus Parser — converts a raw syllabus (pasted text or extracted from an
uploaded file) into the structured topic -> {unit, syllabus_weight,
prerequisites} graph that curriculum_mapping_agent.py reads.

This is the missing link between "user uploads/pastes a syllabus" and the
Curriculum Mapping Agent, which itself stays a plain lookup (no LLM) once
this structured graph exists.
"""

import os
import json
from groq_client import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "MOCK_KEY")

SYLLABUS_PATH = os.environ.get("SYLLABUS_PATH", "syllabus_graph.json")

PARSE_SYSTEM_PROMPT = """You convert a raw course syllabus into a structured
topic graph for an adaptive tutoring system.

For each distinct testable topic/skill in the syllabus, output:
- a short snake_case topic id (used as a key elsewhere in the system)
- the unit/chapter it belongs to
- a syllabus_weight 0-1 (relative importance/exam weight — infer from
  emphasis, credit hours, or stated weightage if given, else estimate
  reasonably)
- prerequisites: topic ids of other topics in this same list that must be
  learned first (use [] if none, or if a prerequisite isn't in this syllabus)

Respond with ONLY valid JSON, no other text, matching this schema:
{
  "topic_id_1": {
    "unit": "<unit/chapter name>",
    "syllabus_weight": <float>,
    "prerequisites": ["topic_id_x", ...]
  },
  ...
}
"""

def parse_syllabus_text(raw_text: str) -> dict:
    """
    raw_text: the syllabus content as plain text (already extracted from
    PDF/DOCX by the caller — see file-reading step below).
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # extraction quality matters here
        messages=[
            {"role": "system", "content": PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def save_syllabus_graph(graph: dict, path: str = SYLLABUS_PATH):
    with open(path, "w") as f:
        json.dump(graph, f, indent=2)


def parse_and_save(raw_text: str, path: str = SYLLABUS_PATH) -> dict:
    graph = parse_syllabus_text(raw_text)
    save_syllabus_graph(graph, path)
    return graph


if __name__ == "__main__":
    sample = """
    Unit 1: Pre-Algebra
    - Arithmetic operations (foundational, heavily tested)
    - Inverse operations (builds on arithmetic)

    Unit 2: Algebra I
    - Linear equations: isolating variables (depends on arithmetic and
      inverse operations). Major exam topic.
    """
    graph = parse_and_save(sample, path="syllabus_graph_test.json")
    print(json.dumps(graph, indent=2))