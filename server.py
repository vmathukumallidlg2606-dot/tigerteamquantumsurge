import datetime
from typing import List
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS

# Load .env from project root (FIREBASE_SERVICE_ACCOUNT_PATH, etc.)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from quantum_surge.models import UserProgress, Question
from quantum_surge.knowledge_base import DOMAINS, TOPICS
from quantum_surge.instructor import InstructorAgent
from quantum_surge.assessment_engine import AssessmentEngine
from quantum_surge.rag_service import RAGService
from quantum_surge.search_service import SearchService
from firebase_config import initialize_firebase, save_user_progress, load_user_progress
from firebase_auth import verify_firebase_token, require_auth, get_current_user, is_instructor, require_instructor
from instructor_store import (
    create_assignment,
    get_assignment,
    get_assignment_by_code,
    list_assignments_for_instructor,
    list_all_scores_for_instructor,
    list_students_for_instructor,
    list_submissions_for_assignment,
    list_assignments_for_student,
    ensure_enrollment,
    set_assignment_status,
    get_submission_for_student,
    save_submission,
    save_quiz_report,
    strip_answers_from_questions,
)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.secret_key = 'quantum-surge-secret-key-change-in-production'

# Firebase Admin SDK is initialized lazily on first use (see firebase_config /
# firebase_auth). This way the server still boots and serves the public
# catalog + static UI even when Admin credentials are not yet configured
# (e.g. before the FIREBASE_SERVICE_ACCOUNT_JSON / PATH env var is set).

def _static_asset_version(filename):
    """Return a cache-busting version token based on file modification time."""
    path = os.path.join(app.static_folder, filename)
    try:
        return str(int(os.path.getmtime(path)))
    except OSError:
        return '0'

@app.context_processor
def inject_static_url():
    def static_url(filename):
        return f"/static/{filename}?v={_static_asset_version(filename)}"
    return dict(static_url=static_url)

@app.after_request
def add_tunnel_headers(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['Access-Control-Allow-Origin'] = '*'
    if request.path.startswith('/static/') and request.path.endswith(('.js', '.css')):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Global (shared) resources that are not per-user
instructor = InstructorAgent("military_analogy")
rag_service = RAGService()

# Temporary per-user caches for generated quiz questions, keyed by Firebase UID
quiz_cache = {}  # uid -> list of generated Question objects
report_cache = {}  # uid -> graded QuikQuiz payload awaiting "Send Report"

def load_or_seed_user_progress(uid: str, username: str = None):
    """Load a user's progress from Firestore, keyed by Firebase UID.

    If no document exists yet, seed default confidence ratings and return a
    fresh UserProgress so the user starts with a clean slate.
    """
    progress = load_user_progress(user_id=uid)
    if progress is None:
        progress = UserProgress(username=username or uid)
        for tid in TOPICS.keys():
            progress.confidence_ratings[tid] = 2  # default confidence score (needs improvement)
        progress.update_weak_areas(list(TOPICS.keys()))
    return progress

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/catalog', methods=['GET'])
def get_catalog():
    """Public catalog of Security+ domains/topics (static reference data).

    This does NOT require authentication because it contains no user data —
    it is the same curriculum catalog shown to every visitor. Personalized
    confidence/mastery is layered on top by the authenticated /api/progress call.
    """
    serialized_domains = []
    for domain in DOMAINS:
        serialized_topics = []
        for topic in domain.topics:
            serialized_topics.append({
                "id": topic.id,
                "name": topic.name,
                "description": topic.description,
                "key_concepts": topic.key_concepts,
                "confidence": 0
            })
        serialized_domains.append({
            "id": domain.id,
            "name": domain.name,
            "description": domain.description,
            "mastery": 0,
            "topics": serialized_topics
        })
    return jsonify({"domains": serialized_domains})

@app.route('/api/progress', methods=['GET'])
@require_auth
def get_progress():
    user = get_current_user()
    uid = user['uid']
    user_progress = load_or_seed_user_progress(uid, user.get('name') or user.get('email'))
    user_progress.update_weak_areas(list(TOPICS.keys()))

    # Calculate statistics matching the reference screenshots
    total_materials = len(user_progress.completed_topics)

    # Count of reviews taken
    reviews_count = len(user_progress.quiz_history)

    # Average confidence rating translated to a mastery percentage
    total_score = sum(user_progress.confidence_ratings.values())
    max_possible = len(TOPICS) * 5
    average_mastery = int((total_score / max_possible) * 100) if max_possible > 0 else 0

    # Build domain breakdown metrics
    serialized_domains = []
    for domain in DOMAINS:
        domain_confidence = 0
        domain_max = len(domain.topics) * 5
        serialized_topics = []
        for topic in domain.topics:
            conf = user_progress.confidence_ratings.get(topic.id, 2)
            domain_confidence += conf
            serialized_topics.append({
                "id": topic.id,
                "name": topic.name,
                "description": topic.description,
                "key_concepts": topic.key_concepts,
                "confidence": conf
            })

        domain_mastery_pct = int((domain_confidence / domain_max) * 100) if domain_max > 0 else 0

        serialized_domains.append({
            "id": domain.id,
            "name": domain.name,
            "description": domain.description,
            "mastery": domain_mastery_pct,
            "topics": serialized_topics
        })

    # Prepare recommended focus list
    recommended_focus = []
    for wa in user_progress.weak_areas:
        if wa in TOPICS:
            recommended_focus.append({
                "id": wa,
                "name": TOPICS[wa].name,
                "confidence": user_progress.confidence_ratings.get(wa, 2)
            })

    # Prepare activity logs
    activity_logs = []
    for q_attempt in user_progress.quiz_history:
        activity_logs.append({
            "timestamp": q_attempt.timestamp,
            "score": q_attempt.score,
            "total_questions": q_attempt.total_questions,
            "correct_answers": q_attempt.correct_answers,
            "breakdown": [
                {
                    "topic_name": TOPICS[tid].name if tid in TOPICS else tid,
                    "correct": stats["correct"],
                    "total": stats["total"]
                }
                for tid, stats in q_attempt.topic_breakdown.items()
            ]
        })

    return jsonify({
        "username": user_progress.username,
        "instructor_mode": instructor.mode,
        "average_mastery": average_mastery,
        "lessons_completed": total_materials,
        "reviews_completed": reviews_count,
        "domains": serialized_domains,
        "weak_areas": recommended_focus,
        "activity_logs": activity_logs
    })

@app.route('/api/instructor/mode', methods=['POST'])
def update_instructor_mode():
    data = request.json or {}
    mode = data.get("mode")
    if mode in ["military_analogy", "technical_breakdown"]:
        instructor.set_mode(mode)
        return jsonify({"status": "success", "mode": instructor.mode})
    return jsonify({"status": "error", "message": "Invalid mode"}), 400

@app.route('/api/assess', methods=['POST'])
@require_auth
def update_assessment():
    user = get_current_user()
    uid = user['uid']
    data = request.json or {}
    topic_id = data.get("topic_id")
    confidence = data.get("confidence")

    if topic_id in TOPICS and isinstance(confidence, int) and 1 <= confidence <= 5:
        user_progress = load_or_seed_user_progress(uid, user.get('name') or user.get('email'))
        user_progress.confidence_ratings[topic_id] = confidence
        user_progress.update_weak_areas(list(TOPICS.keys()))
        # Persist to Firestore, keyed by Firebase UID
        try:
            save_user_progress(user_progress, uid)
        except Exception as e:
            pass  # Silent fail for prototype
        return jsonify({"status": "success", "confidence": confidence})
    return jsonify({"status": "error", "message": "Invalid parameters"}), 400

@app.route('/api/study/<topic_id>', methods=['GET'])
@require_auth
def get_explanation(topic_id):
    user = get_current_user()
    uid = user['uid']
    if topic_id not in TOPICS:
        return jsonify({"status": "error", "message": "Topic not found"}), 404

    user_progress = load_or_seed_user_progress(uid, user.get('name') or user.get('email'))
    topic = TOPICS[topic_id]

    # 1. RAG retrieval context from ChromaDB
    rag_context = rag_service.query_context(topic_id)

    # 2. DuckDuckGo search context
    search_context = SearchService.search_recent_threats(topic.name)

    # 3. Dynamic LLM Generation
    explanation = instructor.explain_topic(topic, user_progress, rag_context, search_context)

    # Track completion
    if topic_id not in user_progress.completed_topics:
        user_progress.completed_topics.append(topic_id)
        try:
            save_user_progress(user_progress, uid)
        except Exception as e:
            pass  # Silent fail for prototype

    return jsonify({
        "topic_id": topic_id,
        "topic_name": topic.name,
        "explanation": explanation
    })

@app.route('/api/quiz/<topic_id>', methods=['GET'])
@require_auth
def get_quiz(topic_id):
    user = get_current_user()
    uid = user['uid']
    if topic_id not in TOPICS:
        return jsonify({"status": "error", "message": "Topic not found"}), 404

    user_progress = load_or_seed_user_progress(uid, user.get('name') or user.get('email'))

    # Get current user confidence on this topic to determine quiz difficulty
    confidence = user_progress.confidence_ratings.get(topic_id, 3)
    difficulty = "easy" if confidence <= 2 else ("hard" if confidence >= 4 else "medium")

    # Query ChromaDB RAG content for this topic
    rag_context = rag_service.query_context(topic_id)

    # Generate quiz dynamically using Ollama LLM
    questions = AssessmentEngine.generate_ai_quiz(user_progress, topic_id, rag_context, difficulty)

    # Cache generated questions for grading (keyed by UID to isolate users)
    quiz_cache[uid] = questions

    serialized_questions = []
    for q in questions:
        serialized_questions.append({
            "id": q.id,
            "topic_id": q.topic_id,
            "topic_name": TOPICS[q.topic_id].name,
            "difficulty": q.difficulty,
            "scenario": q.scenario,
            "question_text": q.question_text,
            "options": q.options
        })

    return jsonify({"questions": serialized_questions})

def _serialize_quiz_questions(questions):
    serialized_questions = []
    for q in questions:
        serialized_questions.append({
            "id": q.id,
            "topic_id": q.topic_id,
            "topic_name": TOPICS[q.topic_id].name,
            "difficulty": q.difficulty,
            "scenario": q.scenario,
            "question_text": q.question_text,
            "options": q.options
        })
    return serialized_questions


def _questions_from_dicts(raw_questions):
    return [
        Question(
            id=q["id"],
            topic_id=q["topic_id"],
            difficulty=q.get("difficulty", "medium"),
            scenario=q.get("scenario", ""),
            question_text=q.get("question_text", ""),
            options=q.get("options", {}),
            correct_option=q.get("correct_option", "A"),
            technical_explanation=q.get("technical_explanation", ""),
            military_analogy=q.get("military_analogy", ""),
        )
        for q in raw_questions
    ]


def _questions_to_dicts(questions):
    return [
        {
            "id": q.id,
            "topic_id": q.topic_id,
            "topic_name": TOPICS[q.topic_id].name if q.topic_id in TOPICS else q.topic_id,
            "difficulty": q.difficulty,
            "scenario": q.scenario,
            "question_text": q.question_text,
            "options": q.options,
            "correct_option": q.correct_option,
            "technical_explanation": q.technical_explanation,
            "military_analogy": q.military_analogy,
        }
        for q in questions
    ]


def _build_question_results(questions, user_answers):
    results = []
    for q in questions:
        user_answer = user_answers.get(q.id, "")
        was_correct = user_answer == q.correct_option
        results.append({
            "id": q.id,
            "topic_id": q.topic_id,
            "topic_name": TOPICS[q.topic_id].name if q.topic_id in TOPICS else q.topic_id,
            "was_correct": was_correct,
            "user_answer": user_answer,
            "correct_answer": q.correct_option,
            "question_text": q.question_text,
            "scenario": q.scenario,
        })
    return results


def _generate_questions_for_topics(user_progress, topic_ids):
    all_questions = []
    for topic_id in topic_ids:
        confidence = user_progress.confidence_ratings.get(topic_id, 3)
        difficulty = "easy" if confidence <= 2 else ("hard" if confidence >= 4 else "medium")
        rag_context = rag_service.query_context(topic_id)
        generated = AssessmentEngine.generate_ai_quiz(user_progress, topic_id, rag_context, difficulty)

        if len(topic_ids) == 1:
            all_questions.extend(generated)
        elif generated:
            all_questions.append(generated[0])
    return all_questions

@app.route('/api/quiz/generate', methods=['POST'])
@require_auth
def generate_quiz():
    user = get_current_user()
    uid = user['uid']
    data = request.json or {}
    topic_ids = data.get("topic_ids", [])

    if not topic_ids:
        return jsonify({"status": "error", "message": "Select at least one topic"}), 400

    topic_ids = [tid for tid in topic_ids if tid in TOPICS]
    if not topic_ids:
        return jsonify({"status": "error", "message": "No valid topics selected"}), 404

    user_progress = load_or_seed_user_progress(uid, user.get('name') or user.get('email'))

    all_questions = _generate_questions_for_topics(user_progress, topic_ids)

    if not all_questions:
        return jsonify({"status": "error", "message": "Failed to generate quiz questions"}), 500

    quiz_cache[uid] = all_questions
    return jsonify({
        "questions": _serialize_quiz_questions(all_questions),
        "topic_ids": topic_ids,
    })

@app.route('/api/quiz/grade', methods=['POST'])
@require_auth
def grade_quiz():
    user = get_current_user()
    uid = user['uid']
    data = request.json or {}
    user_answers = data.get("answers", {})  # e.g., {"q_se_1": "A"}
    report_mode = data.get("report_mode", False)

    # Retrieve cached generated questions for THIS user only
    cached_questions = quiz_cache.get(uid, [])

    if not cached_questions:
        return jsonify({"status": "error", "message": "No active quiz session found"}), 400

    user_progress = load_or_seed_user_progress(uid, user.get('name') or user.get('email'))

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attempt = AssessmentEngine.grade_quiz(
        user_progress,
        cached_questions,
        user_answers,
        timestamp,
        update_progress=not report_mode,
    )

    if report_mode:
        question_results = _build_question_results(cached_questions, user_answers)
        topic_ids = list({q.topic_id for q in cached_questions})
        report_cache[uid] = {
            "student_uid": uid,
            "student_email": user.get("email"),
            "student_name": user.get("name") or user.get("email", uid),
            "topic_ids": topic_ids,
            "topic_names": [TOPICS[tid].name for tid in topic_ids if tid in TOPICS],
            "score": attempt.score,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "topic_breakdown": attempt.topic_breakdown,
            "question_results": question_results,
            "source": "quikquiz",
        }
        quiz_cache.pop(uid, None)
        return jsonify({
            "status": "ready",
            "message": "Quiz graded. Send your report to the instructor when ready.",
        })

    # Prepare result explanations via AI
    explanations = []
    for q in cached_questions:
        ans = user_answers.get(q.id, "")
        was_correct = ans == q.correct_option
        explanations.append({
            "id": q.id,
            "was_correct": was_correct,
            "user_answer": ans,
            "correct_answer": q.correct_option,
            # Calls LLM to explain the result
            "explanation": instructor.explain_question_result(q, was_correct, ans)
        })

    user_progress.update_weak_areas(list(TOPICS.keys()))

    # Persist to Firestore, keyed by Firebase UID (quiz attempt goes to subcollection)
    try:
        save_user_progress(user_progress, uid)
    except Exception as e:
        pass  # Silent fail for prototype

    return jsonify({
        "score": attempt.score,
        "correct_answers": attempt.correct_answers,
        "total_questions": attempt.total_questions,
        "results": explanations
    })

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    data = request.json or {}
    query = data.get("query", "")
    context_label = data.get("context", "Dashboard")
    topic_id = data.get("topic_id")

    # Retrieve RAG context if querying inside a specific topic
    rag_context = ""
    search_context = ""
    if topic_id and topic_id in TOPICS:
        rag_context = rag_service.query_context(topic_id)
        search_context = SearchService.search_recent_threats(TOPICS[topic_id].name)

    system_instruction = (
        f"You are the Quantum Surge AI Security+ digital instructor. "
        f"The user is currently viewing: {context_label}. "
        f"Answer their questions concisely and clearly. Format your answers in markdown. "
    )
    if instructor.mode == "military_analogy":
        system_instruction += "Use military analogies or operations models where appropriate."
    else:
        system_instruction += "Focus on precise computer science/technical specifications."

    prompt = f"""
Query: {query}
ChromaDB Objective Context (RAG): {rag_context}
Live Threat context: {search_context}
"""
    try:
        payload = {
            "model": "gemma3:latest",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        import requests
        response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=30)
        if response.status_code == 200:
            ans = response.json().get("message", {}).get("content", "Error generating response.")
            return jsonify({"answer": ans})
    except Exception as e:
        return jsonify({"answer": f"**[Ollama local host connection failure]**\n\nUnable to reach LLM. Error details: `{str(e)}`"}), 500

    return jsonify({"answer": "Failed to complete generation."}), 500

@app.route('/api/me', methods=['GET'])
@require_auth
def get_me():
    user = get_current_user()
    return jsonify({
        "uid": user["uid"],
        "email": user.get("email"),
        "name": user.get("name"),
        "role": "instructor" if is_instructor(user) else "student",
        "is_instructor": is_instructor(user),
    })

@app.route('/api/quiz/report', methods=['POST'])
@require_auth
def send_quiz_report():
    user = get_current_user()
    uid = user['uid']
    pending = report_cache.pop(uid, None)
    if not pending:
        return jsonify({"status": "error", "message": "No graded quiz ready to send. Finish a quiz first."}), 400

    pending["student_uid"] = uid
    pending["student_email"] = user.get("email")
    pending["student_name"] = user.get("name") or user.get("email", uid)
    save_quiz_report(pending)
    return jsonify({"status": "sent", "message": "Quiz report sent to your instructor."})

@app.route('/api/instructor/dashboard', methods=['GET'])
@require_instructor
def instructor_dashboard():
    user = get_current_user()
    data = list_all_scores_for_instructor(user["uid"])
    for assignment in data["assignments"]:
        subs = list_submissions_for_assignment(assignment["id"])
        assignment["submission_count"] = len(subs)
        assignment["average_score"] = (
            round(sum(s["score"] for s in subs) / len(subs), 1) if subs else None
        )
    return jsonify(data)


@app.route('/api/instructor/students', methods=['GET'])
@require_instructor
def instructor_students():
    """Roster of every student who has ever signed in, alphabetical by email.

    Falls back to local JSON store when Firebase Admin is not configured.
    """
    students = list_students_for_instructor()
    return jsonify({"students": students, "count": len(students)})


QUIZ_QUESTION_COUNT_PER_TOPIC = 20  # how many questions to generate per topic in an assignment


def _assignment_topic_question_count(total_topics: int) -> int:
    """Even-split helper.

    Total = QUIZ_QUESTION_COUNT_PER_TOPIC (20) questions, distributed evenly across
    the chosen topics. Leftover (when 20 does not divide evenly) is added to the
    first few topics so the total is exactly 20.
    """
    total = QUIZ_QUESTION_COUNT_PER_TOPIC
    n = max(1, total_topics)
    per, extra = divmod(total, n)
    if per < 1:
        per = 1
        extra = 0
    # The caller handles the per-topic count via index ordering, so we just return
    # the base per-topic number. The +1 distribution is handled inside the loop.
    return per


def _generate_questions_for_assignment(user_progress, topic_ids: List[str]):
    """Generate a single shared question set for the assignment.

    Each topic gets a per-topic count (even split), and each Question is tagged
    with `domain_id` and `difficulty` so the instructor can review by category.
    """
    from quantum_surge.knowledge_base import TOPICS, DOMAINS
    from quantum_surge.assessment_engine import AssessmentEngine

    total_topics = max(1, len(topic_ids))
    per_topic = _assignment_topic_question_count(total_topics)
    leftover = QUIZ_QUESTION_COUNT_PER_TOPIC - (per_topic * total_topics)
    if leftover < 0:
        leftover = 0
    all_questions = []
    for index, topic_id in enumerate(topic_ids):
        topic = TOPICS.get(topic_id)
        if topic is None:
            continue
        this_count = per_topic + (1 if index < leftover else 0)
        # Resolve the domain name for the marker.
        domain_name = None
        for dom in DOMAINS:
            if any(t.id == topic_id for t in dom.topics):
                domain_name = dom.name
                break
        confidence = user_progress.confidence_ratings.get(topic_id, 3)
        difficulty = "easy" if confidence <= 2 else ("hard" if confidence >= 4 else "medium")
        rag_context = rag_service.query_context(topic_id)
        generated = AssessmentEngine.generate_ai_quiz(
            user_progress,
            topic_id,
            rag_context,
            difficulty,
            question_count=this_count,
        )
        for q in generated:
            # Tag each question for the instructor review UI.
            q.domain_id = next((d.id for d in DOMAINS if any(t.id == topic_id for t in d.topics)), None)
            q.domain_name = domain_name
            q.difficulty = difficulty
        all_questions.extend(generated)
    return all_questions



@app.route('/api/instructor/assignments', methods=['POST'])
@require_instructor
def create_instructor_assignment():
    """Create a QuikQuiz assignment with a single shared question set.

    Body:
      title (str)
      topic_ids (list[str])
      assignee_mode ("all" | "specific")
      assignee_uids (list[str]) - required when assignee_mode == "specific"
      status ("draft" | "approved", default "draft" so the instructor can review before publishing)
    """
    user = get_current_user()
    data = request.json or {}
    title = (data.get("title") or "").strip()
    topic_ids = data.get("topic_ids", []) or []
    assignee_mode = (data.get("assignee_mode") or "all").lower()
    assignee_uids = data.get("assignee_uids", []) or []
    status = (data.get("status") or "draft").lower()
    if status not in ("draft", "approved"):
        status = "draft"

    if not title:
        return jsonify({"status": "error", "message": "Assignment title is required"}), 400
    topic_ids = [tid for tid in topic_ids if tid in TOPICS]
    if not topic_ids:
        return jsonify({"status": "error", "message": "Select at least one valid topic"}), 400
    if assignee_mode not in ("all", "specific"):
        assignee_mode = "all"
    if assignee_mode == "specific" and not assignee_uids:
        return jsonify({"status": "error", "message": "Select at least one student for specific targeting"}), 400

    user_progress = load_or_seed_user_progress(user["uid"], user.get("name") or user.get("email"))
    try:
        questions = _generate_questions_for_assignment(user_progress, topic_ids)
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Failed to generate quiz: {exc}"}), 500
    if not questions:
        return jsonify({"status": "error", "message": "Failed to generate quiz questions"}), 500

    assignment = create_assignment(
        instructor_uid=user["uid"],
        instructor_email=user.get("email"),
        title=title,
        topic_ids=topic_ids,
        questions=_questions_to_dicts(questions),
        assignee_mode=assignee_mode,
        assignee_uids=assignee_uids,
        status=status,
    )
    return jsonify({
        "status": "success",
        "assignment": {
            "id": assignment["id"],
            "title": assignment["title"],
            "access_code": assignment["access_code"],
            "question_count": assignment["question_count"],
            "topic_ids": assignment["topic_ids"],
            "assignee_mode": assignment["assignee_mode"],
            "assignee_uids": assignment["assignee_uids"],
            "created_at": assignment["created_at"],
            "status": assignment["status"],
        },
        "questions": assignment["questions"],
    })


@app.route('/api/instructor/assignments/<assignment_id>/approve', methods=['POST'])
@require_instructor
def approve_instructor_assignment(assignment_id):
    """Flip a draft assignment to approved so students can start it."""
    rec = set_assignment_status(assignment_id, "approved")
    if not rec:
        return jsonify({"status": "error", "message": "Assignment not found"}), 404
    return jsonify({"status": "success", "assignment": {"id": rec["id"], "status": rec["status"]}})


@app.route('/api/instructor/assignments/<assignment_id>/draft', methods=['POST'])
@require_instructor
def revert_instructor_assignment(assignment_id):
    """Move an approved assignment back to draft."""
    rec = set_assignment_status(assignment_id, "draft")
    if not rec:
        return jsonify({"status": "error", "message": "Assignment not found"}), 404
    return jsonify({"status": "success", "assignment": {"id": rec["id"], "status": rec["status"]}})


@app.route('/api/instructor/assignments', methods=['GET'])
@require_instructor
def list_my_instructor_assignments():
    user = get_current_user()
    items = list_assignments_for_instructor(user["uid"])
    out = []
    for a in items:
        out.append({
            "id": a["id"],
            "title": a["title"],
            "access_code": a.get("access_code"),
            "question_count": a.get("question_count"),
            "topic_ids": a.get("topic_ids", []),
            "assignee_mode": a.get("assignee_mode", "all"),
            "assignee_uids": a.get("assignee_uids", []),
            "status": a.get("status", "approved"),
            "created_at": a.get("created_at"),
        })
    return jsonify({"assignments": out})


@app.route('/api/my/assignments', methods=['GET'])
@require_auth
def my_assignments():
    user = get_current_user()
    items = list_assignments_for_student(user["uid"])
    out = []
    for a in items:
        submission = get_submission_for_student(a["id"], user["uid"])
        out.append({
            "id": a["id"],
            "title": a.get("title"),
            "access_code": a.get("access_code"),
            "question_count": a.get("question_count"),
            "topic_ids": a.get("topic_ids", []),
            "topic_names": [TOPICS[t].name for t in a.get("topic_ids", []) if t in TOPICS],
            "created_at": a.get("created_at"),
            "status": a.get("status"),
            "submission": {
                "score": submission.get("score"),
                "submitted_at": submission.get("submitted_at"),
            } if submission else None,
        })
    return jsonify({"assignments": out, "count": len(out)})


@app.route('/api/assignments/<assignment_id>/start', methods=['POST'])
@require_auth
def start_assigned_quiz(assignment_id):
    """Student-side entry point: gate on approval + targeting, then cache the shared questions."""
    user = get_current_user()
    uid = user["uid"]
    assignment = get_assignment(assignment_id)
    if not assignment:
        return jsonify({"status": "error", "message": "Assignment not found"}), 404
    if assignment.get("status") != "approved":
        return jsonify({"status": "error", "message": "This assignment has not been published yet."}), 403

    mode = (assignment.get("assignee_mode") or "all").lower()
    if mode == "specific" and uid not in (assignment.get("assignee_uids") or []):
        return jsonify({"status": "error", "message": "You are not on the recipient list for this assignment."}), 403

    # Auto-enroll for "all" so future analytics can see them.
    ensure_enrollment(assignment_id, uid)

    existing = get_submission_for_student(assignment_id, uid)
    if existing:
        return jsonify({"status": "error", "message": "You have already submitted this assignment."}), 409

    # Reuse the assignment's pre-generated shared question set.
    questions = _questions_from_dicts(assignment.get("questions") or [])
    if not questions:
        return jsonify({"status": "error", "message": "This assignment has no questions yet."}), 500
    quiz_cache[uid] = questions

    safe_questions = strip_answers_from_questions(assignment.get("questions") or [])
    return jsonify({
        "status": "success",
        "assignment": {
            "id": assignment["id"],
            "title": assignment.get("title"),
            "question_count": len(safe_questions),
        },
        "questions": safe_questions,
    })

@app.route('/api/assignments/join', methods=['POST'])
@require_auth
def join_assignment():
    """Code-entry fallback. Same approval + targeting gates as the targeted start endpoint."""
    user = get_current_user()
    data = request.json or {}
    access_code = (data.get("access_code") or "").strip().upper()
    if not access_code:
        return jsonify({"status": "error", "message": "Enter an assignment code"}), 400

    assignment = get_assignment_by_code(access_code)
    if not assignment:
        return jsonify({"status": "error", "message": "Invalid or expired assignment code"}), 404
    if assignment.get("status") != "approved":
        return jsonify({"status": "error", "message": "This assignment has not been published yet."}), 403

    mode = (assignment.get("assignee_mode") or "all").lower()
    if mode == "specific" and user["uid"] not in (assignment.get("assignee_uids") or []):
        return jsonify({"status": "error", "message": "You are not on the recipient list for this assignment."}), 403

    ensure_enrollment(assignment["id"], user["uid"])

    existing = get_submission_for_student(assignment["id"], user["uid"])
    if existing:
        return jsonify({"status": "error", "message": "You have already submitted this assignment."}), 409

    safe_questions = strip_answers_from_questions(assignment["questions"])
    quiz_cache[user["uid"]] = _questions_from_dicts(assignment["questions"])
    return jsonify({
        "status": "success",
        "assignment": {
            "id": assignment["id"],
            "title": assignment["title"],
            "question_count": len(safe_questions),
        },
        "questions": safe_questions,
    })

@app.route('/api/assignments/submit', methods=['POST'])
@require_auth
def submit_assignment():
    user = get_current_user()
    uid = user["uid"]
    data = request.json or {}
    assignment_id = data.get("assignment_id")
    user_answers = data.get("answers", {})

    if not assignment_id:
        return jsonify({"status": "error", "message": "Missing assignment_id"}), 400

    assignment = get_assignment(assignment_id)
    if not assignment:
        return jsonify({"status": "error", "message": "Assignment not found"}), 404

    existing = get_submission_for_student(assignment_id, uid)
    if existing:
        return jsonify({"status": "error", "message": "You have already submitted this assignment."}), 409

    questions = _questions_from_dicts(assignment["questions"])
    user_progress = load_or_seed_user_progress(uid, user.get("name") or user.get("email"))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attempt = AssessmentEngine.grade_quiz(
        user_progress, questions, user_answers, timestamp, update_progress=False
    )
    question_results = _build_question_results(questions, user_answers)

    save_submission({
        "assignment_id": assignment_id,
        "assignment_title": assignment.get("title"),
        "student_uid": uid,
        "student_email": user.get("email"),
        "student_name": user.get("name") or user.get("email", uid),
        "score": attempt.score,
        "correct_answers": attempt.correct_answers,
        "total_questions": attempt.total_questions,
        "topic_breakdown": attempt.topic_breakdown,
        "question_results": question_results,
        "submitted_at": timestamp,
    })

    quiz_cache.pop(uid, None)
    return jsonify({
        "status": "submitted",
        "message": "Your quiz has been submitted to your instructor.",
    })

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Verify Firebase ID token and return user info."""
    data = request.json or {}
    id_token = data.get("id_token")

    if not id_token:
        return jsonify({"status": "error", "message": "Missing ID token"}), 400

    user_info = verify_firebase_token(id_token)
    if not user_info:
        return jsonify({"status": "error", "message": "Invalid ID token"}), 401

    return jsonify({
        "status": "success",
        "user": user_info
    })

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Handle user logout (frontend handles Firebase signOut)."""
    return jsonify({"status": "success"})

@app.route('/api/rewrite', methods=['POST'])
@require_auth
def rewrite_sentence():
    user = get_current_user()
    data = request.json or {}
    text = data.get("text", "")

    if not text.strip():
        return jsonify({"status": "error", "message": "No text provided"}), 400

    prompt = f"""
Rewrite the following sentence or paragraph to be much simpler ("dumb it down"), easy to understand, and conversational.
Do not output introductory greetings, conversational context, or markdown headers. Just return the rewritten text directly.

Text to rewrite:
"{text}"
"""
    try:
        payload = {
            "model": "gemma3:latest",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that simplifies technical language. Return ONLY the simplified text. No quotes, no prefix."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        import requests
        response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=20)
        if response.status_code == 200:
            simplified = response.json().get("message", {}).get("content", "").strip()
            # Clean wrapping quotes if returned by the LLM
            if simplified.startswith('"') and simplified.endswith('"'):
                simplified = simplified[1:-1]
            return jsonify({"simplified": simplified})
    except Exception as e:
        return jsonify({"simplified": f"[AI error: {str(e)}]"}), 500

    return jsonify({"simplified": "[Failed to generate]"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)