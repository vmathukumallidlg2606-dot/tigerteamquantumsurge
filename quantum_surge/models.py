import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class Topic:
    id: str
    name: str
    description: str
    key_concepts: List[str] = field(default_factory=list)

@dataclass
class ExamDomain:
    id: str
    name: str
    description: str
    topics: List[Topic] = field(default_factory=list)

@dataclass
class Question:
    id: str
    topic_id: str
    difficulty: str  # "easy", "medium", "hard"
    scenario: str
    question_text: str
    options: Dict[str, str]  # e.g. {"A": "...", "B": "..."}
    correct_option: str  # e.g. "A"
    technical_explanation: str
    military_analogy: str

@dataclass
class QuizAttempt:
    timestamp: str
    score: float  # percentage correct
    total_questions: int
    correct_answers: int
    topic_breakdown: Dict[str, Dict[str, int]]  # topic_id -> {"correct": int, "total": int}

@dataclass
class UserProgress:
    username: str
    confidence_ratings: Dict[str, int] = field(default_factory=dict)  # topic_id -> confidence (1-5)
    completed_topics: List[str] = field(default_factory=list)
    quiz_history: List[QuizAttempt] = field(default_factory=list)
    weak_areas: List[str] = field(default_factory=list)

    def update_weak_areas(self, all_topics: List[str]):
        """Determines weak areas based on low confidence scores (< 3) and poor quiz results."""
        self.weak_areas = []
        for topic_id in all_topics:
            confidence = self.confidence_ratings.get(topic_id, 3)
            # Find recent quiz accuracy for this topic
            total_attempts = 0
            total_correct = 0
            for attempt in self.quiz_history[-5:]:  # Check last 5 quizzes
                if topic_id in attempt.topic_breakdown:
                    total_attempts += attempt.topic_breakdown[topic_id]["total"]
                    total_correct += attempt.topic_breakdown[topic_id]["correct"]
            
            accuracy = (total_correct / total_attempts) if total_attempts > 0 else 1.0
            
            if confidence < 3 or (total_attempts > 0 and accuracy < 0.7):
                if topic_id not in self.weak_areas:
                    self.weak_areas.append(topic_id)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=4)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProgress":
        progress = cls(username=data["username"])
        progress.confidence_ratings = data.get("confidence_ratings", {})
        progress.completed_topics = data.get("completed_topics", [])
        progress.weak_areas = data.get("weak_areas", [])
        
        quiz_history_data = data.get("quiz_history", [])
        progress.quiz_history = [QuizAttempt(**q) for q in quiz_history_data]
        return progress
