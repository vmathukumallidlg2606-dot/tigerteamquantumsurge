import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import json
import os
from typing import Optional

# Firebase initialization
_firebase_app: Optional[firebase_admin.App] = None
_db: Optional[firestore.Client] = None
_using_local_store: bool = False

# Default service account path in project root (gitignored)
_DEFAULT_CRED_PATH = os.path.join(os.path.dirname(__file__), "firebase-service-account.json")


def is_using_local_store() -> bool:
    return _using_local_store


def _load_credentials():
    """
    Resolve Firebase Admin credentials from (in order of preference):
      1. FIREBASE_SERVICE_ACCOUNT_JSON  -> raw JSON string (ideal for Secret Manager / env var)
      2. FIREBASE_SERVICE_ACCOUNT_PATH -> path to a service-account JSON file
      3. firebase-service-account.json in project root
      4. Application Default Credentials (Cloud Run / Functions / gcloud auth)
    """
    raw_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    if raw_json:
        try:
            return credentials.Certificate(json.loads(raw_json))
        except Exception as e:
            raise RuntimeError(f"FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")

    cred_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH')
    if cred_path and os.path.exists(cred_path):
        return credentials.Certificate(cred_path)

    if os.path.exists(_DEFAULT_CRED_PATH):
        return credentials.Certificate(_DEFAULT_CRED_PATH)

    # Application Default Credentials (no explicit file needed)
    return credentials.ApplicationDefault()


def initialize_firebase():
    '''Initialize Firebase Admin SDK with service account credentials.'''
    global _firebase_app, _db, _using_local_store

    if _firebase_app is not None:
        return _db

    if _using_local_store:
        return None

    try:
        _firebase_app = firebase_admin.initialize_app(_load_credentials())
        _db = firestore.client()
        return _db
    except Exception:
        _using_local_store = True
        print("[Quantum Surge] Firebase not configured — using local file storage (local_data/users.json)")
        return None


def get_firestore_db() -> Optional[firestore.Client]:
    '''Get Firestore client, initializing if needed. Returns None when using local store.'''
    global _db
    if _using_local_store:
        return None
    if _db is None:
        initialize_firebase()
    return _db

# Collections
USERS_COLLECTION = 'users'
QUIZ_HISTORY_SUBCOLLECTION = 'quiz_history'

def _user_doc_ref(user_id: str):
    db = get_firestore_db()
    if db is None:
        raise RuntimeError("Firestore unavailable")
    return db.collection(USERS_COLLECTION).document(user_id)

def _quiz_history_col_ref(user_id: str):
    return _user_doc_ref(user_id).collection(QUIZ_HISTORY_SUBCOLLECTION)

def save_user_progress(user_progress, user_id: str) -> None:
    '''Save a user's progress, keyed by Firebase UID.'''
    if not user_id:
        raise ValueError("user_id (Firebase UID) is required to persist progress")

    if not _using_local_store and not firebase_admin._apps:
        initialize_firebase()

    if _using_local_store or not firebase_admin._apps:
        from local_store import save_user_progress_local
        save_user_progress_local(user_progress, user_id)
        return

    db = get_firestore_db()

    progress_data = {
        'username': user_progress.username,
        'user_id': user_id,
        'confidence_ratings': user_progress.confidence_ratings,
        'completed_topics': user_progress.completed_topics,
        'weak_areas': user_progress.weak_areas,
        'updated_at': firestore.SERVER_TIMESTAMP,
    }

    _user_doc_ref(user_id).set(progress_data, merge=True)

    if user_progress.quiz_history:
        batch = db.batch()
        for attempt in user_progress.quiz_history:
            attempt_ref = _quiz_history_col_ref(user_id).document()
            batch.set(attempt_ref, {
                'timestamp': attempt.timestamp,
                'score': attempt.score,
                'total_questions': attempt.total_questions,
                'correct_answers': attempt.correct_answers,
                'topic_breakdown': attempt.topic_breakdown,
            })
        batch.commit()

def load_user_progress(username: str = None, user_id: str = None):
    '''Load a user's progress from storage, keyed by Firebase UID.'''
    from quantum_surge.models import UserProgress, QuizAttempt

    if not user_id:
        user_id = username

    if not _using_local_store and not firebase_admin._apps:
        initialize_firebase()

    if _using_local_store or not firebase_admin._apps:
        from local_store import load_user_progress_local
        return load_user_progress_local(user_id)

    db = get_firestore_db()
    doc = _user_doc_ref(user_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    progress = UserProgress(username=data.get('username', user_id))
    progress.confidence_ratings = data.get('confidence_ratings', {})
    progress.completed_topics = data.get('completed_topics', [])
    progress.weak_areas = data.get('weak_areas', [])

    quiz_docs = _quiz_history_col_ref(user_id).order_by('timestamp').stream()
    progress.quiz_history = [
        QuizAttempt(
            timestamp=q.get('timestamp', ''),
            score=q.get('score', 0.0),
            total_questions=q.get('total_questions', 0),
            correct_answers=q.get('correct_answers', 0),
            topic_breakdown=q.get('topic_breakdown', {}),
        )
        for q in quiz_docs
    ]
    return progress

def get_all_user_progress():
    '''Get all user progress documents (for admin/analytics).'''
    if _using_local_store or not firebase_admin._apps:
        from local_store import _load_all_users
        return _load_all_users()

    db = get_firestore_db()
    docs = db.collection(USERS_COLLECTION).stream()
    return {doc.id: doc.to_dict() for doc in docs}


def touch_user_profile(user_id: str, email: str = "", name: str = "") -> None:
    """Persist the signed-in user's email/name on their user doc so the instructor roster can show it.

    No-op when the user is not signed in (empty uid or email).
    """
    if not user_id or not email:
        return

    if not _using_local_store and not firebase_admin._apps:
        initialize_firebase()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if _using_local_store or not firebase_admin._apps:
        from local_store import _load_all_users, _save_all_users
        data = _load_all_users()
        existing = data.get(user_id) or {}
        existing["user_id"] = user_id
        existing["email"] = (email or "").strip().lower()
        if name:
            existing["name"] = name
        elif not existing.get("username"):
            existing["username"] = name or email.split("@")[0]
        existing["last_seen"] = timestamp
        data[user_id] = existing
        _save_all_users(data)
        return

    db = get_firestore_db()
    _user_doc_ref(user_id).set({
        "user_id": user_id,
        "email": (email or "").strip().lower(),
        "name": name or "",
        "last_seen": firestore.SERVER_TIMESTAMP,
    }, merge=True)

