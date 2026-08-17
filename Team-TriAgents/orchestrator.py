"""
Orchestrator — deterministic state machine that routes between agents.
This is plain code, NOT an LLM call: routing logic doesn't need reasoning,
just state tracking and dispatch.
"""

from enum import Enum, auto
from diagnostic_agent import diagnose
from evaluator_agent import evaluate
from tutor_agent import teach
from quiz_agent import generate_quiz
from memory_agent import (
    get_mastery, update_mastery, log_error_event,
    get_recent_error_history, get_learning_style,
)
from planner_agent import handle_replan
from curriculum_mapping_agent import map_topic
from difficulty_agent import calibrate_difficulty


class LoopState(Enum):
    DIAGNOSE = auto()
    TEACH = auto()
    QUIZ = auto()
    EVALUATE = auto()
    REPLAN = auto()
    DONE = auto()


class SessionOrchestrator:
    def __init__(self, student_id: str, question: str, student_answer: str,
                 correct_answer: str, topic_hint: str | None = None):
        self.student_id = student_id
        self.state = LoopState.DIAGNOSE
        self.context = {
            "question": question,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "error_history": get_recent_error_history(student_id, topic=topic_hint),
            "learning_style": get_learning_style(student_id),
            "methods_tried": [],
            "difficulty": "medium",
            "recent_scores": [],
            "consecutive_correct": 0,
            "consecutive_wrong": 0,
        }

    def step(self):
        """Advance one step through the loop. Call repeatedly until DONE."""
        if self.state == LoopState.DIAGNOSE:
            diag = diagnose(
                self.context["question"],
                self.context["student_answer"],
                self.context["correct_answer"],
                self.context["error_history"],
            )
            self.context["diagnosis"] = diag
            self.context["curriculum_info"] = map_topic(diag["root_cause_topic"])
            log_error_event(
                self.student_id, diag["root_cause_topic"], diag["error_type"],
            )
            # Pull real current mastery for this topic (decayed for time elapsed)
            self.context["current_mastery"] = get_mastery(
                self.student_id, diag["root_cause_topic"]
            )
            self.state = LoopState.TEACH

        elif self.state == LoopState.TEACH:
            diag = self.context["diagnosis"]
            result = teach(
                root_cause_topic=diag["root_cause_topic"],
                error_type=diag["error_type"],
                diagnosis_reasoning=diag["reasoning"],
                methods_already_tried=self.context["methods_tried"],
                learning_style=self.context.get("learning_style"),
            )
            self.context["methods_tried"].append(result["method_used"])
            self.context["last_teach_result"] = result
            self.state = LoopState.QUIZ

        elif self.state == LoopState.QUIZ:
            calibration = calibrate_difficulty(
                current_difficulty=self.context.get("difficulty", "medium"),
                recent_scores=self.context.get("recent_scores", []),
                current_mastery=self.context.get("current_mastery", 0.4),
                consecutive_correct=self.context.get("consecutive_correct", 0),
                consecutive_wrong=self.context.get("consecutive_wrong", 0),
            )
            self.context["difficulty"] = calibration["difficulty"]
            self.context["calibration_reason"] = calibration["reason"]

            quiz = generate_quiz(
                root_cause_topic=self.context["diagnosis"]["root_cause_topic"],
                difficulty=self.context["difficulty"],
                previously_asked=self.context.get("previously_asked", []),
                num_questions=1,
            )
            self.context["quiz"] = quiz
            self.context.setdefault("previously_asked", []).append(
                quiz["questions"][0]["question_text"]
            )
            # In a live app, the Orchestrator pauses here and waits for the
            # student's response before moving to EVALUATE.
            self.state = LoopState.EVALUATE

        elif self.state == LoopState.EVALUATE:
            q = self.context["quiz"]["questions"][0]
            # student_response would come from the live UI in a real app;
            # here we assume it's been placed on the context by the caller.
            student_response = self.context.get("latest_student_response", "")

            eval_result = evaluate(
                question=q["question_text"],
                rubric_or_expected_answer=q["expected_answer_or_rubric"],
                student_response=student_response,
                target_skill=self.context["diagnosis"]["root_cause_topic"],
                current_mastery=self.context.get("current_mastery", 0.4),
            )
            if isinstance(eval_result, list) and len(eval_result) > 0:
                eval_result = eval_result[0]
            self.context["eval_result"] = eval_result
            self.context.setdefault("recent_scores", []).append(eval_result["score"])
            self.context["recent_scores"] = self.context["recent_scores"][-5:]  # keep last 5
            if eval_result["is_correct"]:
                self.context["consecutive_correct"] = self.context.get("consecutive_correct", 0) + 1
                self.context["consecutive_wrong"] = 0
            else:
                self.context["consecutive_wrong"] = self.context.get("consecutive_wrong", 0) + 1
                self.context["consecutive_correct"] = 0

            new_mastery = update_mastery(
                self.student_id, self.context["diagnosis"]["root_cause_topic"],
                mastery_delta=eval_result["mastery_delta"],
            )
            self.context["current_mastery"] = new_mastery
            log_error_event(
                self.student_id, self.context["diagnosis"]["root_cause_topic"],
                error_type=self.context["diagnosis"]["error_type"],
                method_used=self.context["methods_tried"][-1] if self.context["methods_tried"] else None,
                score=eval_result["score"], mastery_delta=eval_result["mastery_delta"],
            )
            if eval_result["gap_closed"]:
                self.state = LoopState.DONE
            elif len(self.context["methods_tried"]) >= len(
                ["analogy", "visual", "worked_example", "socratic"]
            ):
                # Every teaching method has been tried and the gap is still
                # open — escalate to the Planner instead of looping forever.
                self.state = LoopState.REPLAN
            else:
                self.state = LoopState.TEACH

        elif self.state == LoopState.REPLAN:
            escalation = handle_replan(
                student_id=self.student_id,
                root_cause_topic=self.context["diagnosis"]["root_cause_topic"],
                methods_tried=self.context["methods_tried"],
            )
            self.context["replan_result"] = escalation
            # Orchestrator itself doesn't act further here — it surfaces the
            # decision (e.g. teach a prerequisite topic, flag for a human,
            # or defer) back to whatever called it (API layer / frontend).
            self.state = LoopState.DONE

        return self.state


if __name__ == "__main__":
    orch = SessionOrchestrator(
        student_id="student_001",
        question="Solve for x: 2x + 5 = 15",
        student_answer="x = 10",
        correct_answer="x = 5",
        topic_hint="linear_equations_isolation",
    )

    while orch.state != LoopState.DONE:
        prev_state = orch.state
        new_state = orch.step()
        print(f"{prev_state.name} -> {new_state.name}")

        if new_state == LoopState.EVALUATE:
            # In production this comes from the live UI after the student
            # answers the quiz question just generated. Simulated here.
            orch.context["latest_student_response"] = "x = 5"

    print("\nFinal mastery:", orch.context.get("current_mastery"))
    print("Methods tried:", orch.context["methods_tried"])
    print("Final difficulty:", orch.context.get("difficulty"),
          "-", orch.context.get("calibration_reason"))