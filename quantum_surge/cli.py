import sys
import datetime
from typing import Optional
from .models import UserProgress
from .knowledge_base import DOMAINS, TOPICS, QUESTIONS
from .instructor import InstructorAgent
from .assessment_engine import AssessmentEngine

def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class QuantumSurgeCLI:
    def __init__(self):
        self.user: Optional[UserProgress] = None
        self.instructor = InstructorAgent("military_analogy")

    def run(self):
        print("="*60)
        print("          QUANTUM SURGE LEARNING ACCELERATOR          ")
        print("          AI-Powered Security+ Prep for Veterans      ")
        print("="*60)
        
        username = input("Enter your username to begin: ").strip()
        if not username:
            username = "Veteran_Learner"
        
        # Initialize default progress
        self.user = UserProgress(username=username)
        # Default self-assessments at the start: set all confidence to 2 (needs work)
        for domain in DOMAINS:
            for topic in domain.topics:
                self.user.confidence_ratings[topic.id] = 2
                
        self.user.update_weak_areas(list(TOPICS.keys()))

        while True:
            self.show_dashboard()
            choice = input("\nSelect an option [1-6]: ").strip()
            
            if choice == "1":
                self.study_topic()
            elif choice == "2":
                self.take_quiz()
            elif choice == "3":
                self.self_assess_confidence()
            elif choice == "4":
                self.toggle_instructor_mode()
            elif choice == "5":
                self.show_progress_history()
            elif choice == "6" or choice.lower() == "exit":
                print("\nThank you for utilizing Quantum Surge. Good luck with your CompTIA Security+ prep!")
                break
            else:
                print("Invalid selection. Please choose a number from 1 to 6.")

    def show_dashboard(self):
        print("\n" + "="*50)
        print(f"               LEARNER DASHBOARD: {self.user.username}")
        print("="*50)
        print(f"Current Instructor Explanation Mode: {self.instructor.mode.upper().replace('_', ' ')}")
        
        # Recommendations
        self.user.update_weak_areas(list(TOPICS.keys()))
        print("\n[🎯 Recommended Focus Areas]")
        if self.user.weak_areas:
            for wa in self.user.weak_areas:
                topic = TOPICS.get(wa)
                conf = self.user.confidence_ratings.get(wa, 3)
                print(f" - {topic.name} (Topic ID: {wa}) | Confidence: {conf}/5")
        else:
            print(" - All areas look solid! Take a review quiz to verify.")

        # Progress Overview
        print("\n[📚 Curriculum Domains]")
        for domain in DOMAINS:
            print(f"\n* {domain.name}")
            for topic in domain.topics:
                conf = self.user.confidence_ratings.get(topic.id, 2)
                status_icon = "🟢" if conf >= 4 else ("🟡" if conf == 3 else "🔴")
                print(f"   [{status_icon}] {topic.name:<35} | Confidence: {conf}/5")

        print("\n" + "-"*50)
        print("1. Select a Topic to Study & Adapt Explanations")
        print("2. Take an Adaptive Quiz")
        print("3. Self-Assess and Update Confidence Scores")
        print("4. Toggle Instructor Mode (Military Analogy vs Tech Breakdown)")
        print("5. View Quiz History")
        print("6. Exit")
        print("="*50)

    def study_topic(self):
        print("\nSelect a Topic ID to study:")
        for idx, (tid, topic) in enumerate(TOPICS.items(), 1):
            print(f"{idx}. {topic.name} (ID: {tid})")
        
        choice = input("Enter Topic ID or Number: ").strip()
        
        # Resolve by number or string ID
        target_topic = None
        if choice.isdigit():
            idx = int(choice) - 1
            tids = list(TOPICS.keys())
            if 0 <= idx < len(tids):
                target_topic = TOPICS[tids[idx]]
        else:
            target_topic = TOPICS.get(choice)

        if not target_topic:
            print("Topic not found.")
            return

        print("\nGenerating adaptive explanation...")
        explanation = self.instructor.explain_topic(target_topic, self.user)
        print("\n" + "="*50)
        print(explanation)
        print("="*50)
        
        # Mark as studied
        if target_topic.id not in self.user.completed_topics:
            self.user.completed_topics.append(target_topic.id)
            
        input("\nPress Enter to return to Dashboard...")

    def take_quiz(self):
        print("\nGenerating adaptive quiz based on your profile...")
        questions = AssessmentEngine.select_questions_for_quiz(self.user, num_questions=3)
        
        if not questions:
            print("No questions found.")
            return

        user_answers = {}
        print("\n" + "-"*50)
        print("                 ADAPTIVE QUIZ                 ")
        print("-"*50)

        for i, question in enumerate(questions, 1):
            print(f"\n[Question {i} of {len(questions)}] (Difficulty: {question.difficulty.upper()})")
            print(f"Scenario: {question.scenario}")
            print(f"Question: {question.question_text}")
            for opt_key, opt_val in sorted(question.options.items()):
                print(f"   {opt_key}. {opt_val}")
            
            ans = ""
            while ans not in ["A", "B", "C", "D"]:
                ans = input("Your Answer (A, B, C, or D): ").strip().upper()
            
            user_answers[question.id] = ans

        # Grade
        attempt = AssessmentEngine.grade_quiz(self.user, questions, user_answers, get_timestamp())
        
        print("\n" + "="*50)
        print("                 QUIZ RESULTS                 ")
        print("="*50)
        print(f"Score: {attempt.score:.1f}% ({attempt.correct_answers}/{attempt.total_questions})")
        print("="*50)

        # Show explanations for each question
        for i, question in enumerate(questions, 1):
            user_choice = user_answers[question.id]
            was_correct = user_choice == question.correct_option
            explanation = self.instructor.explain_question_result(question, was_correct, user_choice)
            print(f"\n--- Question {i} Explanation ---")
            print(explanation)
            print("-"*50)

        input("\nPress Enter to return to Dashboard...")

    def self_assess_confidence(self):
        print("\nSelect a Topic ID to self-assess:")
        for idx, (tid, topic) in enumerate(TOPICS.items(), 1):
            conf = self.user.confidence_ratings.get(tid, 2)
            print(f"{idx}. {topic.name} (Current Confidence: {conf}/5)")
        
        choice = input("Enter Topic Number to modify: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            tids = list(TOPICS.keys())
            if 0 <= idx < len(tids):
                tid = tids[idx]
                val = 0
                while val not in [1, 2, 3, 4, 5]:
                    try:
                        val = int(input(f"Enter new confidence score for '{TOPICS[tid].name}' (1-5): "))
                    except ValueError:
                        pass
                self.user.confidence_ratings[tid] = val
                print(f"Confidence score for '{TOPICS[tid].name}' updated to {val}/5.")
            else:
                print("Invalid number selection.")
        else:
            print("Invalid input.")
        
        input("\nPress Enter to return to Dashboard...")

    def toggle_instructor_mode(self):
        print("\nChoose an explanation style:")
        print("1. Military Analogy (Translates concepts to military scenarios)")
        print("2. Technical Breakdown (Rigorous direct terminology)")
        choice = input("Choose style [1 or 2]: ").strip()
        
        if choice == "1":
            self.instructor.set_mode("military_analogy")
            print("Mode set to: Military Analogy")
        elif choice == "2":
            self.instructor.set_mode("technical_breakdown")
            print("Mode set to: Technical Breakdown")
        else:
            print("Invalid selection.")
        
        input("\nPress Enter to return to Dashboard...")

    def show_progress_history(self):
        print("\n" + "="*50)
        print("                 QUIZ HISTORY                 ")
        print("="*50)
        if not self.user.quiz_history:
            print("No quizzes taken yet.")
        else:
            for idx, attempt in enumerate(self.user.quiz_history, 1):
                print(f"Quiz #{idx} ({attempt.timestamp})")
                print(f" - Score: {attempt.score:.1f}% ({attempt.correct_answers}/{attempt.total_questions})")
                print(" - Topics Checked:")
                for tid, stats in attempt.topic_breakdown.items():
                    topic = TOPICS.get(tid)
                    print(f"   * {topic.name}: {stats['correct']}/{stats['total']} correct")
                print("-"*30)
        
        input("\nPress Enter to return to Dashboard...")

if __name__ == "__main__":
    cli = QuantumSurgeCLI()
    cli.run()
