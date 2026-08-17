"""
Progress Tracking Agent — generates analytics/trends for dashboards from
the events already logged by the Memory Agent (ErrorEvent, TopicMastery).

Deliberately NOT an LLM call: this is aggregation/analytics over structured
data already in the DB, so plain queries are faster and exactly reproducible
(important for "verifiable output" — judges can see the numbers are real,
not model-generated).
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from memory_agent import _session, TopicMastery, ErrorEvent


def get_mastery_overview(student_id: str) -> list[dict]:
    """Current mastery snapshot across all topics the student has touched."""
    db = _session()
    try:
        rows = db.query(TopicMastery).filter_by(student_id=student_id).all()
        return [
            {
                "topic": r.topic,
                "mastery": round(r.mastery, 3),
                "attempts": r.attempts,
                "last_updated": r.last_updated.isoformat(),
            }
            for r in sorted(rows, key=lambda x: x.mastery)
        ]
    finally:
        db.close()


def get_mastery_trend(student_id: str, topic: str, days: int = 30) -> list[dict]:
    """
    Time series of score/mastery_delta events for a topic, for charting
    (e.g. Recharts line chart on the frontend dashboard).
    """
    db = _session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.query(ErrorEvent)
            .filter(ErrorEvent.student_id == student_id, ErrorEvent.topic == topic,
                    ErrorEvent.timestamp >= cutoff, ErrorEvent.score.isnot(None))
            .order_by(ErrorEvent.timestamp.asc())
            .all()
        )
        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "score": r.score,
                "mastery_delta": r.mastery_delta,
                "method_used": r.method_used,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_error_type_breakdown(student_id: str, topic: str | None = None) -> dict:
    """Counts of error types (conceptual/procedural/prerequisite/careless_slip)."""
    db = _session()
    try:
        q = db.query(ErrorEvent).filter_by(student_id=student_id)
        if topic:
            q = q.filter_by(topic=topic)
        rows = q.all()
        counts = defaultdict(int)
        for r in rows:
            counts[r.error_type] += 1
        return dict(counts)
    finally:
        db.close()


def get_teaching_method_effectiveness(student_id: str) -> list[dict]:
    """
    Average score achieved after each teaching method was used — surfaces
    which explanation style actually works best for this student.
    """
    db = _session()
    try:
        rows = (
            db.query(ErrorEvent)
            .filter(ErrorEvent.student_id == student_id,
                     ErrorEvent.method_used.isnot(None),
                     ErrorEvent.score.isnot(None))
            .all()
        )
        by_method = defaultdict(list)
        for r in rows:
            by_method[r.method_used].append(r.score)
        return [
            {"method": method, "avg_score": round(sum(scores) / len(scores), 3),
             "times_used": len(scores)}
            for method, scores in by_method.items()
        ]
    finally:
        db.close()


def get_streak_and_activity(student_id: str, days: int = 14) -> dict:
    """Daily activity counts, for a streak/heatmap widget."""
    db = _session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.query(ErrorEvent)
            .filter(ErrorEvent.student_id == student_id, ErrorEvent.timestamp >= cutoff)
            .all()
        )
        daily_counts = defaultdict(int)
        for r in rows:
            day_key = r.timestamp.date().isoformat()
            daily_counts[day_key] += 1

        sorted_days = sorted(daily_counts.keys())
        current_streak = 0
        check_date = datetime.now(timezone.utc).date()
        while check_date.isoformat() in daily_counts:
            current_streak += 1
            check_date -= timedelta(days=1)

        return {
            "daily_activity": dict(daily_counts),
            "current_streak_days": current_streak,
            "total_events": len(rows),
        }
    finally:
        db.close()


def get_dashboard_summary(student_id: str) -> dict:
    """Single call that bundles everything a dashboard page typically needs."""
    mastery = get_mastery_overview(student_id)
    return {
        "mastery_overview": mastery,
        "weakest_topics": mastery[:3],  # already sorted ascending by mastery
        "error_breakdown": get_error_type_breakdown(student_id),
        "method_effectiveness": get_teaching_method_effectiveness(student_id),
        "activity": get_streak_and_activity(student_id),
    }


if __name__ == "__main__":
    sid = "student_001"
    print("Mastery overview:", get_mastery_overview(sid))
    print("Error breakdown:", get_error_type_breakdown(sid))
    print("Method effectiveness:", get_teaching_method_effectiveness(sid))
    print("Activity:", get_streak_and_activity(sid))
    print("Full dashboard summary:", get_dashboard_summary(sid))