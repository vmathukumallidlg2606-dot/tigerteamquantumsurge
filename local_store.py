"""Local JSON file storage for user progress when Firebase is not configured."""

import json
import os
from typing import Optional

from quantum_surge.models import UserProgress, QuizAttempt

DATA_DIR = os.path.join(os.path.dirname(__file__), "local_data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_all_users() -> dict:
    _ensure_data_dir()
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all_users(data: dict) -> None:
    _ensure_data_dir()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_user_progress_local(user_progress: UserProgress, user_id: str) -> None:
    if not user_id:
        raise ValueError("user_id is required")

    data = _load_all_users()
    data[user_id] = {
        "username": user_progress.username,
        "user_id": user_id,
        "confidence_ratings": user_progress.confidence_ratings,
        "completed_topics": user_progress.completed_topics,
        "weak_areas": user_progress.weak_areas,
        "quiz_history": [
            {
                "timestamp": attempt.timestamp,
                "score": attempt.score,
                "total_questions": attempt.total_questions,
                "correct_answers": attempt.correct_answers,
                "topic_breakdown": attempt.topic_breakdown,
            }
            for attempt in user_progress.quiz_history
        ],
    }
    _save_all_users(data)


def load_user_progress_local(user_id: str) -> Optional[UserProgress]:
    if not user_id:
        return None

    data = _load_all_users()
    user_data = data.get(user_id)
    if not user_data:
        return None

    progress = UserProgress(username=user_data.get("username", user_id))
    progress.confidence_ratings = user_data.get("confidence_ratings", {})
    progress.completed_topics = user_data.get("completed_topics", [])
    progress.weak_areas = user_data.get("weak_areas", [])
    progress.quiz_history = [
        QuizAttempt(
            timestamp=q.get("timestamp", ""),
            score=q.get("score", 0.0),
            total_questions=q.get("total_questions", 0),
            correct_answers=q.get("correct_answers", 0),
            topic_breakdown=q.get("topic_breakdown", {}),
        )
        for q in user_data.get("quiz_history", [])
    ]
    return progress
