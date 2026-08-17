"""
Student Profile / Memory Agent

Persists:
- Topic mastery
- Forgetting-curve mastery decay
- Error history
- Learning style
- Student preferences

Uses SQLAlchemy with SQLite by default.
For production, change DATABASE_URL to PostgreSQL.
"""

import os
import math
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    DateTime,
    Integer,
    JSON,
)
from sqlalchemy.orm import declarative_base, sessionmaker


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./tutor_memory.db"
)

# Example PostgreSQL URL:
# DATABASE_URL = "postgresql://user:password@host:5432/tutor_db"


if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


def _session():
    """Create and return a new database session."""
    return SessionLocal()


# ============================================================
# FORGETTING CURVE CONFIGURATION
# ============================================================

# Ebbinghaus-style retention:
#
# R = e^(-t / S)
#
# R = retention
# t = time elapsed
# S = stability
#
# Higher mastery -> higher stability -> slower decay.

FORGETTING_BASE_STABILITY_DAYS = 4.0


# ============================================================
# DATABASE MODELS
# ============================================================

class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id = Column(
        Integer,
        primary_key=True
    )

    student_id = Column(
        String,
        index=True,
        nullable=False
    )

    topic = Column(
        String,
        index=True,
        nullable=False
    )

    # 0.0 - 1.0
    mastery = Column(
        Float,
        default=0.0
    )

    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    attempts = Column(
        Integer,
        default=0
    )


class ErrorEvent(Base):
    __tablename__ = "error_event"

    id = Column(
        Integer,
        primary_key=True
    )

    student_id = Column(
        String,
        index=True,
        nullable=False
    )

    topic = Column(
        String,
        index=True,
        nullable=False
    )

    error_type = Column(
        String
    )

    method_used = Column(
        String,
        nullable=True
    )

    score = Column(
        Float,
        nullable=True
    )

    mastery_delta = Column(
        Float,
        nullable=True
    )

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # Free-form extra context
    meta = Column(
        JSON,
        nullable=True
    )


class StudentProfile(Base):
    __tablename__ = "student_profile"

    student_id = Column(
        String,
        primary_key=True
    )

    # Example:
    # analogy
    # visual
    # worked_example
    # socratic

    learning_style = Column(
        String,
        nullable=True
    )

    preferences = Column(
        JSON,
        nullable=True
    )


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(engine)


# ============================================================
# INTERNAL TIME / MASTERY HELPERS
# ============================================================

def _get_utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    """
    Make sure a datetime is timezone-aware.

    SQLite can sometimes return DateTime values without
    timezone information.
    """

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def _calculate_decayed_mastery(row: TopicMastery) -> float:
    """
    Calculate current mastery after applying forgetting-curve decay.

    The database value remains unchanged.
    This function only calculates the temporary decayed value.
    """

    last_updated = _ensure_utc(row.last_updated)

    days_elapsed = (
        _get_utc_now() - last_updated
    ).total_seconds() / 86400

    # Higher mastery means slower forgetting.
    stability = (
        FORGETTING_BASE_STABILITY_DAYS
        * (1 + row.mastery * 2)
    )

    retention = math.exp(
        -days_elapsed / stability
    )

    decayed_mastery = row.mastery * retention

    return round(
        decayed_mastery,
        4
    )


# ============================================================
# MASTERY FUNCTIONS
# ============================================================

def get_mastery(
    student_id: str,
    topic: str
) -> float:
    """
    Return the student's current mastery for a topic.

    The stored mastery is decayed based on the time elapsed
    since the last practice.
    """

    db = _session()

    try:
        row = (
            db.query(TopicMastery)
            .filter_by(
                student_id=student_id,
                topic=topic
            )
            .first()
        )

        if not row:
            return 0.0

        return _calculate_decayed_mastery(row)

    finally:
        db.close()


def update_mastery(
    student_id: str,
    topic: str,
    mastery_delta: float
) -> float:
    """
    Apply a mastery delta and persist the result.

    Example:

        Current decayed mastery = 0.50
        mastery_delta = +0.20

        New mastery = 0.70

    Mastery is always clamped between 0.0 and 1.0.
    """

    db = _session()

    try:
        row = (
            db.query(TopicMastery)
            .filter_by(
                student_id=student_id,
                topic=topic
            )
            .first()
        )

        # Create new topic record if it doesn't exist.
        if not row:
            row = TopicMastery(
                student_id=student_id,
                topic=topic,
                mastery=0.0,
                attempts=0
            )

            db.add(row)

            # Make sure the object is initialized.
            db.flush()

        # Calculate current mastery after forgetting.
        current = _calculate_decayed_mastery(row)

        # Apply evaluator's mastery delta.
        new_mastery = current + mastery_delta

        # Keep mastery between 0 and 1.
        row.mastery = max(
            0.0,
            min(1.0, new_mastery)
        )

        row.attempts += 1

        # Reset forgetting timer after practice.
        row.last_updated = _get_utc_now()

        db.commit()

        return round(
            row.mastery,
            4
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_due_for_review(
    student_id: str,
    retention_threshold: float = 0.6
) -> list[dict]:
    """
    Return topics whose retention has dropped below the
    specified threshold.

    Example:

        peak mastery = 0.80
        current mastery = 0.45

        retention ratio = 0.45 / 0.80
                         = 0.5625

        threshold = 0.60

        Topic is due for review.
    """

    db = _session()

    try:
        rows = (
            db.query(TopicMastery)
            .filter_by(
                student_id=student_id
            )
            .all()
        )

        due = []

        for row in rows:

            # Calculate mastery after forgetting.
            decayed_mastery = _calculate_decayed_mastery(row)

            # Calculate how much of the original mastery remains.
            if row.mastery > 0:
                retention_ratio = (
                    decayed_mastery / row.mastery
                )
            else:
                retention_ratio = 1.0

            # Topic needs review.
            if retention_ratio < retention_threshold:

                due.append({
                    "topic": row.topic,
                    "decayed_mastery": decayed_mastery,
                    "peak_mastery": round(row.mastery, 4),
                    "retention_ratio": round(
                        retention_ratio,
                        4
                    )
                })

        # Lowest mastery first.
        return sorted(
            due,
            key=lambda x: x["decayed_mastery"]
        )

    finally:
        db.close()


# ============================================================
# ERROR HISTORY
# ============================================================

def log_error_event(
    student_id: str,
    topic: str,
    error_type: str,
    method_used: str | None = None,
    score: float | None = None,
    mastery_delta: float | None = None,
    meta: dict | None = None
):
    """
    Store an error made by the student.

    This information can later be used by the
    Diagnostic Agent.
    """

    db = _session()

    try:
        event = ErrorEvent(
            student_id=student_id,
            topic=topic,
            error_type=error_type,
            method_used=method_used,
            score=score,
            mastery_delta=mastery_delta,
            meta=meta
        )

        db.add(event)

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_recent_error_history(
    student_id: str,
    topic: str | None = None,
    limit: int = 10
) -> list[dict]:
    """
    Return recent errors made by a student.

    If topic is provided, only errors for that topic
    are returned.
    """

    db = _session()

    try:
        query = (
            db.query(ErrorEvent)
            .filter_by(
                student_id=student_id
            )
        )

        if topic:
            query = query.filter_by(
                topic=topic
            )

        rows = (
            query
            .order_by(
                ErrorEvent.timestamp.desc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "topic": row.topic,
                "error_type": row.error_type,
                "method_used": row.method_used,
                "score": row.score,
                "mastery_delta": row.mastery_delta,
                "timestamp": (
                    _ensure_utc(row.timestamp)
                    .isoformat()
                ),
                "meta": row.meta
            }
            for row in rows
        ]

    finally:
        db.close()


# ============================================================
# LEARNING STYLE / STUDENT PROFILE
# ============================================================

def get_learning_style(
    student_id: str
) -> str | None:
    """
    Return the student's preferred learning style.

    Possible examples:

        analogy
        visual
        worked_example
        socratic
    """

    db = _session()

    try:
        row = (
            db.query(StudentProfile)
            .filter_by(
                student_id=student_id
            )
            .first()
        )

        if row:
            return row.learning_style

        return None

    finally:
        db.close()


def set_learning_style(
    student_id: str,
    style: str
):
    """
    Set or update the student's learning style.
    """

    db = _session()

    try:
        row = (
            db.query(StudentProfile)
            .filter_by(
                student_id=student_id
            )
            .first()
        )

        if not row:
            row = StudentProfile(
                student_id=student_id
            )

            db.add(row)

        row.learning_style = style

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ============================================================
# STUDENT PREFERENCES
# ============================================================

def get_preferences(
    student_id: str
) -> dict | None:
    """
    Return stored student preferences.
    """

    db = _session()

    try:
        row = (
            db.query(StudentProfile)
            .filter_by(
                student_id=student_id
            )
            .first()
        )

        if not row:
            return None

        return row.preferences

    finally:
        db.close()


def set_preferences(
    student_id: str,
    preferences: dict
):
    """
    Create or update student preferences.

    Example:

        {
            "difficulty": "medium",
            "preferred_language": "English",
            "explanation_length": "short"
        }
    """

    db = _session()

    try:
        row = (
            db.query(StudentProfile)
            .filter_by(
                student_id=student_id
            )
            .first()
        )

        if not row:
            row = StudentProfile(
                student_id=student_id
            )

            db.add(row)

        row.preferences = preferences

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ============================================================
# COMPLETE STUDENT MEMORY
# ============================================================

def get_student_memory(
    student_id: str,
    topic: str | None = None
) -> dict:
    """
    Return a combined snapshot of the student's memory.

    Useful for passing context to the Diagnostic Agent.
    """

    memory = {
        "student_id": student_id,
        "learning_style": get_learning_style(student_id),
        "preferences": get_preferences(student_id),
        "recent_errors": get_recent_error_history(
            student_id,
            topic=topic,
            limit=10
        ),
        "due_for_review": get_due_for_review(
            student_id
        )
    }

    if topic:
        memory["current_topic"] = topic
        memory["current_mastery"] = get_mastery(
            student_id,
            topic
        )

    return memory


# ============================================================
# TEST / DEMO
# ============================================================

if __name__ == "__main__":

    sid = "student_001"

    topic = "linear_equations_isolation"

    print("\n==============================")
    print(" STUDENT MEMORY AGENT TEST")
    print("==============================\n")

    # --------------------------------------------------------
    # 1. Set learning style
    # --------------------------------------------------------

    set_learning_style(
        sid,
        "worked_example"
    )

    print(
        "Learning style:",
        get_learning_style(sid)
    )

    # --------------------------------------------------------
    # 2. Store an error
    # --------------------------------------------------------

    log_error_event(
        student_id=sid,
        topic=topic,
        error_type="procedural",
        method_used="standard_isolation",
        score=0.4,
        mastery_delta=-0.1,
        meta={
            "question_id": "q001",
            "expected_answer": "x = 5",
            "student_answer": "x = -5"
        }
    )

    print("\nError logged.")

    # --------------------------------------------------------
    # 3. Update mastery
    # --------------------------------------------------------

    mastery = update_mastery(
        student_id=sid,
        topic=topic,
        mastery_delta=0.3
    )

    print(
        "Mastery after update:",
        mastery
    )

    # --------------------------------------------------------
    # 4. Get current decayed mastery
    # --------------------------------------------------------

    current_mastery = get_mastery(
        student_id=sid,
        topic=topic
    )

    print(
        "Current decayed mastery:",
        current_mastery
    )

    # --------------------------------------------------------
    # 5. Get recent errors
    # --------------------------------------------------------

    errors = get_recent_error_history(
        student_id=sid
    )

    print("\nRecent errors:")

    for error in errors:
        print(error)

    # --------------------------------------------------------
    # 6. Get topics due for review
    # --------------------------------------------------------

    due_topics = get_due_for_review(
        student_id=sid
    )

    print("\nDue for review:")

    for item in due_topics:
        print(item)

    # --------------------------------------------------------
    # 7. Get complete student memory
    # --------------------------------------------------------

    memory = get_student_memory(
        student_id=sid,
        topic=topic
    )

    print("\nComplete student memory:")
    print(memory)

    print("\n==============================")
    print(" TEST COMPLETE")
    print("==============================\n")