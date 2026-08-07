import json
import requests
from typing import Dict, Any, Optional
from .models import Topic, UserProgress, Question

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma3:latest"  # Configured to use your downloaded gemma3 model

class InstructorAgent:
    def __init__(self, mode: str = "military_analogy"):
        self.mode = mode

    def set_mode(self, mode: str):
        if mode in ["military_analogy", "technical_breakdown"]:
            self.mode = mode

    def explain_topic(self, topic: Topic, user_progress: UserProgress, rag_context: str, search_context: str) -> str:
        """Calls local Ollama LLM to generate custom adaptive Security+ lessons."""
        confidence = user_progress.confidence_ratings.get(topic.id, 3)
        depth = "Foundational" if confidence <= 2 else ("Advanced" if confidence >= 5 else "Intermediate")
        
        style_instruction = (
            "You are a military commander translating technical concepts into army battle operations, physical base security (FOB checkpoints, patrols), and tactical situations."
            if self.mode == "military_analogy"
            else "You are a lead systems architect writing technical blueprints, protocol specs, RFC references, and deep code/configuration structures."
        )

        prompt = f"""
Domain Topic: {topic.name}
Explanation Depth: {depth}
Target Audience: Veteran preparing for CompTIA Security+ SY0-701 exam

Official Objective Reference (RAG):
{rag_context}

Live Threat Intelligence Context (Web Search):
{search_context}

Style Requirement:
{style_instruction}

Generate a beautiful Markdown study lesson explaining the topic. Keep the language direct and clear.
Provide:
1. A descriptive overview matching the {depth} depth.
2. A high-quality demonstration scenario based on the style requirement.
3. Exam Trap warning section for the CompTIA test.
"""

        try:
            payload = {
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an agentic cybersecurity instructor for Quantum Surge. Output explanations using clean GitHub Markdown. Use appropriate titles and bullet points."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=45)
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "Error: Empty response content.")
        except Exception as e:
            return f"**[Ollama local host connection failure]**\n\nUnable to generate AI explanation dynamically. Make sure Ollama is running (`ollama serve`).\n\n*Fallback Static Description:* {topic.description}\n\n*Error details:* `{str(e)}`"

        return f"Failed to generate lesson from local AI server. (HTTP status {response.status_code})"

    def explain_question_result(self, question: Question, was_correct: bool, selected_option: str) -> str:
        """Explains why a user was correct/incorrect using the local Ollama LLM."""
        status_header = "✅ Correct Answer" if was_correct else f"❌ Incorrect Answer (User selected: {selected_option})"
        
        prompt = f"""
Question Text: {question.question_text}
Selected Option: {selected_option} (Was Correct: {was_correct})
Correct Answer: {question.correct_option}: {question.options.get(question.correct_option)}
All Options: {json.dumps(question.options)}

Technical Explanation:
{question.technical_explanation}

Military Metaphor Reference:
{question.military_analogy}

Write a short, engaging explanation card for the student. Use the style mode: {self.mode}. Ensure the user understands why the correct option is right and other choices are wrong.
"""
        try:
            payload = {
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a veteran instructor explaining Security+ exam answers. Output cleanly formatted Markdown."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=25)
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "Error: Empty response content.")
        except Exception:
            pass

        # Fallback to local static text
        fallback = f"### {status_header}\n\n"
        if self.mode == "military_analogy":
            fallback += f"**Military Analogy:**\n{question.military_analogy}\n\n"
        fallback += f"**Technical Details:**\n{question.technical_explanation}"
        return fallback
