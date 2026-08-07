#!/usr/bin/env python3
"""Test script to verify Firebase connection and basic operations."""

import sys
sys.path.insert(0, '.')

from firebase_config import initialize_firebase, save_user_progress, load_user_progress, get_firestore_db
from quantum_surge.models import UserProgress, QuizAttempt

def test_firebase_connection():
    """Test Firebase initialization and basic CRUD operations."""
    print("[TEST] Testing Firebase Integration...")
    
    try:
        # Initialize Firebase
        print("1. Initializing Firebase...")
        db = initialize_firebase()
        print("   [OK] Firebase initialized successfully!")
        print("   [OK] Project connected to Firestore")
        
        # Create a test user progress
        print("\n2. Creating test user progress...")
        test_progress = UserProgress(
            username="test_user_firebase",
            confidence_ratings={"se_1_1": 4, "se_1_2": 3},
            completed_topics=["se_1_1"],
            weak_areas=["se_1_2"]
        )
        
        # Add a quiz history entry
        test_progress.quiz_history.append(QuizAttempt(
            timestamp="2026-07-14 12:00:00",
            score=66.67,
            total_questions=3,
            correct_answers=2,
            topic_breakdown={"se_1_1": {"correct": 2, "total": 3}}
        ))
        
        print(f"   [OK] Test progress created for: {test_progress.username}")
        
        # Save to Firebase (keyed by Firebase UID for isolation)
        print("\n3. Saving to Firestore...")
        TEST_UID = "test_uid_firebase"
        save_user_progress(test_progress, TEST_UID)
        print("   [OK] Progress saved successfully!")
        
        # Load back
        print("\n4. Loading from Firestore...")
        loaded = load_user_progress(user_id=TEST_UID)
        
        if loaded:
            print("   [OK] Progress loaded successfully!")
            print(f"   - Username: {loaded.username}")
            print(f"   - Completed topics: {loaded.completed_topics}")
            print(f"   - Confidence ratings: {loaded.confidence_ratings}")
            print(f"   - Quiz history entries: {len(loaded.quiz_history)}")
        else:
            print("   [FAIL] Failed to load progress")
            return False
            
        print("\n[SUCCESS] Firebase integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Firebase test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_firebase_connection()
    sys.exit(0 if success else 1)