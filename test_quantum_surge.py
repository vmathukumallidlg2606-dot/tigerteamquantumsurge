import unittest
import datetime
from quantum_surge.models import UserProgress, Topic
from quantum_surge.instructor import InstructorAgent
from quantum_surge.assessment_engine import AssessmentEngine
from quantum_surge.knowledge_base import TOPICS

class TestQuantumSurgePrototype(unittest.TestCase):
    def setUp(self):
        self.user = UserProgress(username="Test_Veteran")
        for tid in TOPICS.keys():
            self.user.confidence_ratings[tid] = 2  # Low initial confidence
        self.user.update_weak_areas(list(TOPICS.keys()))
        self.instructor = InstructorAgent("military_analogy")

    def test_instructor_agent_explanation_fallback(self):
        # Verify fallback or failure state if Ollama is not running
        # We pass dummy RAG and Search context parameters matching modified signature
        explanation = self.instructor.explain_topic(
            TOPICS["threat_vectors"], 
            self.user,
            rag_context="RAG details on threat vectors.",
            search_context="Recent threat news details."
        )
        # Should contain fallback or connection failure warning
        self.assertTrue("Ollama" in explanation or "Threat" in explanation)

if __name__ == "__main__":
    unittest.main()
