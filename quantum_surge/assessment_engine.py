import json
import requests
from typing import List, Dict, Tuple, Optional
from .models import Question, UserProgress, QuizAttempt
from .knowledge_base import TOPICS

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma3:latest"

class AssessmentEngine:
    @staticmethod
    def generate_ai_quiz(
        user_progress: UserProgress,
        target_topic_id: str,
        rag_context: str,
        difficulty: str = "medium",
        question_count: int = 3,
    ) -> List[Question]:
        """
        Calls local Ollama LLM to generate fresh scenario-based questions matching 
        a specific topic and user difficulty level.
        """
        topic = TOPICS.get(target_topic_id)
        topic_name = topic.name if topic else "General Security+"

        prompt = f"""
Generate {question_count} scenario-based CompTIA Security+ multiple-choice questions for the topic: {topic_name}.
Difficulty Level: {difficulty}

Objective Guidelines (RAG Reference):
{rag_context}

You MUST respond strictly with a valid JSON array of objects. Do not wrap in backticks or add introductory text.
Each object in the JSON array must follow this exact schema:
{{
    "id": "gen_q_<unique_string>",
    "topic_id": "{target_topic_id}",
    "difficulty": "{difficulty}",
    "scenario": "A descriptive cybersecurity corporate or operational incident scene...",
    "question_text": "The test question asking to identify the target protocol, attack, or mitigation...",
    "options": {{
        "A": "Option text A",
        "B": "Option text B",
        "C": "Option text C",
        "D": "Option text D"
    }},
    "correct_option": "A", // must be exactly 'A', 'B', 'C', or 'D'
    "technical_explanation": "Deep dive technical analysis of why the correct option is right and others are wrong.",
    "military_analogy": "A physical battlefield or base defense analogy translating the vulnerability or protocol mechanics."
}}
"""

        try:
            payload = {
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a professional CompTIA Security+ test generator. Output valid JSON list only. No markdown ticks block, no greeting, no conversational text."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=180)
            if response.status_code == 200:
                raw_content = response.json().get("message", {}).get("content", "").strip()
                # Clean up any potential markdown wrapper if outputted
                if raw_content.startswith("```json"):
                    raw_content = raw_content[7:]
                if raw_content.endswith("```"):
                    raw_content = raw_content[:-3]
                raw_content = raw_content.strip()

                parsed = json.loads(raw_content)
                questions = []
                for q_dict in parsed:
                    questions.append(Question(
                        id=q_dict["id"],
                        topic_id=q_dict["topic_id"],
                        difficulty=q_dict["difficulty"],
                        scenario=q_dict["scenario"],
                        question_text=q_dict["question_text"],
                        options=q_dict["options"],
                        correct_option=q_dict["correct_option"],
                        technical_explanation=q_dict["technical_explanation"],
                        military_analogy=q_dict["military_analogy"]
                    ))
                return questions
        except Exception as e:
            print(f"Ollama quiz generation error: {e}")

        # Dynamic offline mock fallback questions for the given topic if LLM fails
        topic_title = TOPICS[target_topic_id].name if target_topic_id in TOPICS else "General Concept"
        count = max(1, int(question_count or 1))
        return [
            Question(
                id=f"fallback_{target_topic_id}_{i+1}",
                topic_id=target_topic_id,
                difficulty=difficulty,
                scenario=f"Scenario {i+1}: a security engineer is reviewing controls related to {topic_title}.",
                question_text=f"Which option best addresses the security concern in scenario {i+1}?",
                options={
                    "A": "Apply the appropriate baseline control",
                    "B": "Disable authentication mechanisms",
                    "C": "Open all inbound firewall rules",
                    "D": "Hardcode credentials in source control",
                },
                correct_option="A",
                technical_explanation=f"Applying the appropriate control is the correct mitigation for the {topic_title} concern in scenario {i+1}.",
                military_analogy=f"Like reinforcing the perimeter with additional sentry checks in scenario {i+1}."
            )
            for i in range(count)
        ]

    @staticmethod
    def grade_quiz(
        user_progress: UserProgress,
        questions: List[Question],
        user_answers: Dict[str, str],
        timestamp: str,
        update_progress: bool = True,
    ) -> QuizAttempt:
        """Grades a completed quiz and optionally updates user confidence ratings."""
        correct_count = 0
        topic_breakdown: Dict[str, Dict[str, int]] = {}

        for question in questions:
            q_id = question.id
            t_id = question.topic_id

            if t_id not in topic_breakdown:
                topic_breakdown[t_id] = {"correct": 0, "total": 0}

            topic_breakdown[t_id]["total"] += 1

            user_choice = user_answers.get(q_id)
            if user_choice == question.correct_option:
                correct_count += 1
                topic_breakdown[t_id]["correct"] += 1

                if update_progress:
                    current_conf = user_progress.confidence_ratings.get(t_id, 3)
                    user_progress.confidence_ratings[t_id] = min(current_conf + 1, 5)
            else:
                if update_progress:
                    current_conf = user_progress.confidence_ratings.get(t_id, 3)
                    user_progress.confidence_ratings[t_id] = max(current_conf - 1, 1)

        score_pct = (correct_count / len(questions)) * 100 if questions else 0.0
        
        attempt = QuizAttempt(
            timestamp=timestamp,
            score=score_pct,
            total_questions=len(questions),
            correct_answers=correct_count,
            topic_breakdown=topic_breakdown
        )
        
        user_progress.quiz_history.append(attempt)
        return attempt
