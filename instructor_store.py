"""Persistence for quiz assignments, submissions, and ad-hoc quiz reports."""

import json
import os
import secrets
import string
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from firebase_config import get_firestore_db, is_using_local_store, initialize_firebase
import firebase_admin
from firebase_admin import firestore

DATA_DIR = os.path.join(os.path.dirname(__file__), "local_data")
INSTRUCTOR_FILE = os.path.join(DATA_DIR, "instructor.json")

ASSIGNMENTS_COLLECTION = "assignments"
SUBMISSIONS_COLLECTION = "assignment_submissions"
REPORTS_COLLECTION = "quiz_reports"


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _generate_access_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _ensure_local_file() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(INSTRUCTOR_FILE):
        data = {"assignments": {}, "submissions": {}, "quiz_reports": {}}
        with open(INSTRUCTOR_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data
    try:
        with open(INSTRUCTOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"assignments": {}, "submissions": {}, "quiz_reports": {}}


def _save_local_file(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INSTRUCTOR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _use_firestore() -> bool:
    if is_using_local_store():
        return False
    if not firebase_admin._apps:
        initialize_firebase()
    return bool(firebase_admin._apps) and not is_using_local_store()


def strip_answers_from_questions(questions: List[dict]) -> List[dict]:
    safe = []
    for q in questions:
        item = {k: v for k, v in q.items() if k not in (
            "correct_option", "technical_explanation", "military_analogy"
        )}
        safe.append(item)
    return safe


def create_assignment(
    instructor_uid: str,
    instructor_email: str,
    title: str,
    topic_ids: List[str],
    questions: List[dict],
    assignee_mode: str = "all",
    assignee_uids: Optional[List[str]] = None,
    status: str = "approved",
) -> dict:
    assignment_id = str(uuid.uuid4())
    access_code = _generate_access_code()
    while get_assignment_by_code(access_code):
        access_code = _generate_access_code()

    mode = (assignee_mode or "all").lower()
    if mode not in ("all", "specific"):
        mode = "all"
    if mode == "specific":
        targets = [str(uid).strip() for uid in (assignee_uids or []) if str(uid).strip()]
    else:
        targets = []
    record = {
        "id": assignment_id,
        "title": title,
        "access_code": access_code,
        "instructor_uid": instructor_uid,
        "instructor_email": instructor_email,
        "topic_ids": topic_ids,
        "questions": questions,
        "question_count": len(questions),
        "created_at": _now_iso(),
        "status": status,
        "assignee_mode": mode,
        "assignee_uids": targets,
        "enrollments": {uid: {"enrolled_at": _now_iso(), "status": "enrolled"} for uid in targets},
    }

    if _use_firestore():
        db = get_firestore_db()
        db.collection(ASSIGNMENTS_COLLECTION).document(assignment_id).set(record)
        return record

    data = _ensure_local_file()
    data["assignments"][assignment_id] = record
    _save_local_file(data)
    return record


def get_assignment(assignment_id: str) -> Optional[dict]:
    if _use_firestore():
        doc = get_firestore_db().collection(ASSIGNMENTS_COLLECTION).document(assignment_id).get()
        return doc.to_dict() if doc.exists else None

    data = _ensure_local_file()
    return data["assignments"].get(assignment_id)


def get_assignment_by_code(access_code: str) -> Optional[dict]:
    code = (access_code or "").strip().upper()
    if not code:
        return None

    if _use_firestore():
        docs = (
            get_firestore_db()
            .collection(ASSIGNMENTS_COLLECTION)
            .where("access_code", "==", code)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None

    data = _ensure_local_file()
    for assignment in data["assignments"].values():
        if assignment.get("access_code") == code and assignment.get("status") == "active":
            return assignment
    return None


def list_assignments_for_instructor(instructor_uid: str) -> List[dict]:
    if _use_firestore():
        docs = (
            get_firestore_db()
            .collection(ASSIGNMENTS_COLLECTION)
            .where("instructor_uid", "==", instructor_uid)
            .stream()
        )
        items = [doc.to_dict() for doc in docs]
        items.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return items

    data = _ensure_local_file()
    items = [
        a for a in data["assignments"].values()
        if a.get("instructor_uid") == instructor_uid
    ]
    items.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return items


def save_submission(submission: dict) -> dict:
    submission_id = submission.get("id") or str(uuid.uuid4())
    submission["id"] = submission_id
    if "submitted_at" not in submission:
        submission["submitted_at"] = _now_iso()

    if _use_firestore():
        get_firestore_db().collection(SUBMISSIONS_COLLECTION).document(submission_id).set(submission)
        return submission

    data = _ensure_local_file()
    data["submissions"][submission_id] = submission
    _save_local_file(data)
    return submission


def get_submission_for_student(assignment_id: str, student_uid: str) -> Optional[dict]:
    if _use_firestore():
        docs = (
            get_firestore_db()
            .collection(SUBMISSIONS_COLLECTION)
            .where("assignment_id", "==", assignment_id)
            .where("student_uid", "==", student_uid)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None

    data = _ensure_local_file()
    for sub in data["submissions"].values():
        if sub.get("assignment_id") == assignment_id and sub.get("student_uid") == student_uid:
            return sub
    return None


def list_submissions_for_assignment(assignment_id: str) -> List[dict]:
    if _use_firestore():
        docs = (
            get_firestore_db()
            .collection(SUBMISSIONS_COLLECTION)
            .where("assignment_id", "==", assignment_id)
            .stream()
        )
        items = [doc.to_dict() for doc in docs]
        items.sort(key=lambda s: s.get("submitted_at", ""), reverse=True)
        return items

    data = _ensure_local_file()
    items = [s for s in data["submissions"].values() if s.get("assignment_id") == assignment_id]
    items.sort(key=lambda s: s.get("submitted_at", ""), reverse=True)
    return items


def save_quiz_report(report: dict) -> dict:
    report_id = report.get("id") or str(uuid.uuid4())
    report["id"] = report_id
    if "submitted_at" not in report:
        report["submitted_at"] = _now_iso()

    if _use_firestore():
        get_firestore_db().collection(REPORTS_COLLECTION).document(report_id).set(report)
        return report

    data = _ensure_local_file()
    data["quiz_reports"][report_id] = report
    _save_local_file(data)
    return report


def list_quiz_reports() -> List[dict]:
    """All ad-hoc QuikQuiz reports — visible to any configured instructor."""
    if _use_firestore():
        docs = get_firestore_db().collection(REPORTS_COLLECTION).stream()
        items = [doc.to_dict() for doc in docs]
        items.sort(key=lambda r: r.get("submitted_at", ""), reverse=True)
        return items

    data = _ensure_local_file()
    items = list(data.get("quiz_reports", {}).values())
    items.sort(key=lambda r: r.get("submitted_at", ""), reverse=True)
    return items


def set_assignment_status(assignment_id: str, status: str) -> Optional[dict]:
    """Flip a published/draft assignment between approved/draft."""
    if _use_firestore():
        ref = get_firestore_db().collection(ASSIGNMENTS_COLLECTION).document(assignment_id)
        ref.set({"status": status, "updated_at": _now_iso()}, merge=True)
        doc = ref.get()
        return doc.to_dict() if doc.exists else None
    data = _ensure_local_file()
    rec = data["assignments"].get(assignment_id)
    if not rec:
        return None
    rec["status"] = status
    rec["updated_at"] = _now_iso()
    data["assignments"][assignment_id] = rec
    _save_local_file(data)
    return rec


def ensure_enrollment(assignment_id: str, student_uid: str) -> Optional[dict]:
    """Auto-enroll a student in an assignment. No-op if mode is "all" but student
    is not yet on the list; this function only adds them to the persistent
    enrollments dict. Returns the updated record, or None if missing.
    """
    if not student_uid:
        return None
    if _use_firestore():
        ref = get_firestore_db().collection(ASSIGNMENTS_COLLECTION).document(assignment_id)
        doc = ref.get()
        if not doc.exists:
            return None
        rec = doc.to_dict() or {}
        rec.setdefault("enrollments", {})
        if student_uid not in rec["enrollments"]:
            rec["enrollments"][student_uid] = {"enrolled_at": _now_iso(), "status": "enrolled"}
            ref.set({"enrollments": rec["enrollments"]}, merge=True)
        return rec
    data = _ensure_local_file()
    rec = data["assignments"].get(assignment_id)
    if not rec:
        return None
    rec.setdefault("enrollments", {})
    if student_uid not in rec["enrollments"]:
        rec["enrollments"][student_uid] = {"enrolled_at": _now_iso(), "status": "enrolled"}
        data["assignments"][assignment_id] = rec
        _save_local_file(data)
    return rec


def list_assignments_for_student(student_uid: str) -> List[dict]:
    """Approved assignments targeted at this student, plus their submission if any."""
    if not student_uid:
        return []
    targets: List[dict] = []
    if _use_firestore():
        docs = get_firestore_db().collection(ASSIGNMENTS_COLLECTION).stream()
        for d in docs:
            rec = d.to_dict() or {}
            if rec.get("status") != "approved":
                continue
            mode = (rec.get("assignee_mode") or "all").lower()
            if mode == "all" or student_uid in (rec.get("assignee_uids") or []):
                targets.append(rec)
    else:
        data = _ensure_local_file()
        for rec in (data.get("assignments") or {}).values():
            if rec.get("status") != "approved":
                continue
            mode = (rec.get("assignee_mode") or "all").lower()
            if mode == "all" or student_uid in (rec.get("assignee_uids") or []):
                targets.append(rec)
    targets.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return targets


def list_students_for_instructor() -> List[dict]:
    """All students who have ever signed in, plus per-student activity stats.

    Sources:
      - The `users` collection / `local_data/users.json` (everyone who has
        ever saved progress, regardless of whether they have submitted
        anything to an assignment).
      - Every `student_uid` referenced in `submissions` or `quiz_reports`
        (so signed-up students who never saved progress still appear).

    Returns a list of dicts sorted by email (case-insensitive ascending):
        {uid, email, name, last_seen, assignment_count, quiz_report_count,
         average_score, has_progress}
    """
    # Pull every user doc to seed the roster (incl. signed-up students with no activity).
    users_by_uid: Dict[str, dict] = {}
    try:
        from firebase_config import get_all_user_progress
        users_by_uid = get_all_user_progress() or {}
    except Exception:
        users_by_uid = {}

    by_uid: Dict[str, dict] = {}

    def _seed(uid: str, email: str = "", name: str = ""):
        if not uid:
            return
        row = by_uid.setdefault(uid, {
            "uid": uid,
            "email": (email or "").strip().lower(),
            "name": (name or "").strip(),
            "last_seen": "",
            "assignment_count": 0,
            "quiz_report_count": 0,
            "_score_sum": 0.0,
            "_score_count": 0,
            "has_progress": False,
        })
        if email and not row["email"]:
            row["email"] = email.strip().lower()
        if name and not row["name"]:
            row["name"] = name.strip()
        return row

    for uid, data in users_by_uid.items():
        if not isinstance(data, dict):
            continue
        row = _seed(uid, data.get("email") or "", data.get("username") or "")
        if row is None:
            continue
        row["has_progress"] = True
        # quiz_history is a list of {timestamp, score, ...}; use the latest as last_seen.
        for attempt in data.get("quiz_history") or []:
            ts = attempt.get("timestamp") if isinstance(attempt, dict) else None
            if ts and ts > row["last_seen"]:
                row["last_seen"] = ts

    # Walk every submission / report so we never miss a student whose progress
    # doc hasn't been written yet (e.g. they joined an assignment immediately
    # after sign-in but never generated a study lesson).
    if _use_firestore():
        db = get_firestore_db()
        for sub in db.collection(SUBMISSIONS_COLLECTION).stream():
            d = sub.to_dict() or {}
            uid = d.get("student_uid") or ""
            row = _seed(uid, d.get("student_email") or "", d.get("student_name") or "")
            if row is None:
                continue
            row["assignment_count"] += 1
            if d.get("score") is not None:
                row["_score_sum"] += float(d["score"])
                row["_score_count"] += 1
            ts = d.get("submitted_at") or ""
            if ts and ts > row["last_seen"]:
                row["last_seen"] = ts
        for rep in db.collection(REPORTS_COLLECTION).stream():
            d = rep.to_dict() or {}
            uid = d.get("student_uid") or ""
            row = _seed(uid, d.get("student_email") or "", d.get("student_name") or "")
            if row is None:
                continue
            row["quiz_report_count"] += 1
            if d.get("score") is not None:
                row["_score_sum"] += float(d["score"])
                row["_score_count"] += 1
            ts = d.get("submitted_at") or ""
            if ts and ts > row["last_seen"]:
                row["last_seen"] = ts
    else:
        data = _ensure_local_file()
        for sub in (data.get("submissions") or {}).values():
            uid = sub.get("student_uid") or ""
            row = _seed(uid, sub.get("student_email") or "", sub.get("student_name") or "")
            if row is None:
                continue
            row["assignment_count"] += 1
            if sub.get("score") is not None:
                row["_score_sum"] += float(sub["score"])
                row["_score_count"] += 1
            ts = sub.get("submitted_at") or ""
            if ts and ts > row["last_seen"]:
                row["last_seen"] = ts
        for rep in (data.get("quiz_reports") or {}).values():
            uid = rep.get("student_uid") or ""
            row = _seed(uid, rep.get("student_email") or "", rep.get("student_name") or "")
            if row is None:
                continue
            row["quiz_report_count"] += 1
            if rep.get("score") is not None:
                row["_score_sum"] += float(rep["score"])
                row["_score_count"] += 1
            ts = rep.get("submitted_at") or ""
            if ts and ts > row["last_seen"]:
                row["last_seen"] = ts

    # Finalize: compute average, derive a name fallback, strip scratch fields.
    out: List[dict] = []
    for row in by_uid.values():
        if not row["name"] and row["email"]:
            row["name"] = row["email"].split("@")[0]
        if row["_score_count"]:
            row["average_score"] = round(row["_score_sum"] / row["_score_count"], 1)
        else:
            row["average_score"] = None
        row.pop("_score_sum", None)
        row.pop("_score_count", None)
        out.append(row)

    out.sort(key=lambda r: (r.get("email") or "").lower())
    return out



def list_all_scores_for_instructor(instructor_uid: str) -> dict:
    """Combined dashboard feed: assignment submissions + quikquiz reports."""
    assignments = list_assignments_for_instructor(instructor_uid)
    assignment_rows = []
    for assignment in assignments:
        subs = list_submissions_for_assignment(assignment["id"])
        for sub in subs:
            assignment_rows.append({
                "type": "assignment",
                "assignment_id": assignment["id"],
                "assignment_title": assignment.get("title"),
                "access_code": assignment.get("access_code"),
                **sub,
            })

    reports = list_quiz_reports()
    return {
        "assignments": assignments,
        "assignment_submissions": assignment_rows,
        "quiz_reports": reports,
    }
