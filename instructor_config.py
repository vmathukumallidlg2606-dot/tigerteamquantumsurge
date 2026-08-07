import os

DEFAULT_INSTRUCTOR_EMAIL = "vmathukumalli.dlg.26.06@gmail.com"


def get_instructor_emails() -> set:
    """Instructors who can create assignments and view all scores on the dashboard."""
    raw = os.environ.get("INSTRUCTOR_EMAILS", DEFAULT_INSTRUCTOR_EMAIL)
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def is_instructor_email(email: str) -> bool:
    if not email:
        return False
    return email.strip().lower() in get_instructor_emails()
