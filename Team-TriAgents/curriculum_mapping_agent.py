"""
Curriculum Mapping Agent — aligns identified gaps to specific syllabus
units/prerequisites (e.g. mapping a TCP/IP weakness back to networking
fundamentals).

Deliberately NOT an LLM call: this is a deterministic graph lookup, which
is faster, cheaper, and more reliable than asking a model to remember your
syllabus structure. Backed by a JSON/YAML syllabus graph loaded once at
startup. Swap SYLLABUS_PATH for a DB-backed version in production.
"""

import json
import os
from functools import lru_cache

SYLLABUS_PATH = os.environ.get("SYLLABUS_PATH", "syllabus_graph.json")

# Example syllabus graph shape:
# {
#   "linear_equations_isolation": {
#       "unit": "Algebra I - Linear Equations",
#       "syllabus_weight": 0.8,
#       "prerequisites": ["arithmetic_operations", "inverse_operations"]
#   },
#   "tcp_udp_reliability": {
#       "unit": "Networking - Transport Layer",
#       "syllabus_weight": 0.7,
#       "prerequisites": ["osi_model_basics", "packet_switching"]
#   }
# }


def _load_graph() -> dict:
    if not os.path.exists(SYLLABUS_PATH):
        # Fallback so the module is runnable standalone / in demos
        return {
            "linear_equations_isolation": {
                "unit": "Algebra I - Linear Equations",
                "syllabus_weight": 0.8,
                "prerequisites": ["arithmetic_operations", "inverse_operations"],
            },
            "arithmetic_operations": {
                "unit": "Pre-Algebra - Arithmetic",
                "syllabus_weight": 0.9,
                "prerequisites": [],
            },
            "inverse_operations": {
                "unit": "Pre-Algebra - Inverse Operations",
                "syllabus_weight": 0.6,
                "prerequisites": ["arithmetic_operations"],
            },
            "tcp_udp_reliability": {
                "unit": "Networking - Transport Layer",
                "syllabus_weight": 0.7,
                "prerequisites": ["osi_model_basics", "packet_switching"],
            },
            "osi_model_basics": {
                "unit": "Networking - Fundamentals",
                "syllabus_weight": 0.9,
                "prerequisites": [],
            },
            "packet_switching": {
                "unit": "Networking - Fundamentals",
                "syllabus_weight": 0.7,
                "prerequisites": ["osi_model_basics"],
            },
        }
    with open(SYLLABUS_PATH) as f:
        return json.load(f)


def map_topic(root_cause_topic: str) -> dict:
    """Returns syllabus unit, weight, and direct prerequisites for a topic."""
    graph = _load_graph()
    entry = graph.get(root_cause_topic)
    if not entry:
        return {
            "topic": root_cause_topic,
            "unit": "unmapped",
            "syllabus_weight": 0.5,  # neutral default
            "prerequisites": [],
            "found": False,
        }
    return {
        "topic": root_cause_topic,
        "unit": entry["unit"],
        "syllabus_weight": entry["syllabus_weight"],
        "prerequisites": entry["prerequisites"],
        "found": True,
    }


def get_prerequisite_chain(root_cause_topic: str) -> list[str]:
    """
    Walks the prerequisite graph recursively, returning the full chain in
    learn-this-order (deepest prerequisite first). Used by the Planner
    Agent's "prerequisite_first" REPLAN action.
    """
    graph = _load_graph()
    visited = []

    def _walk(topic: str):
        entry = graph.get(topic)
        if not entry:
            return
        for prereq in entry.get("prerequisites", []):
            if prereq not in visited:
                _walk(prereq)
                visited.append(prereq)

    _walk(root_cause_topic)
    return visited


def get_all_syllabus_weights() -> dict[str, float]:
    """Used by the Planner Agent to build the full roadmap."""
    graph = _load_graph()
    return {topic: entry["syllabus_weight"] for topic, entry in graph.items()}


if __name__ == "__main__":
    print(json.dumps(map_topic("linear_equations_isolation"), indent=2))
    print("Prerequisite chain:", get_prerequisite_chain("linear_equations_isolation"))
    print("All weights:", get_all_syllabus_weights())