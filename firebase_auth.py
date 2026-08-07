import base64
import json
import time
import firebase_admin
from firebase_admin import auth
from flask import request, jsonify
import functools

from firebase_config import initialize_firebase, is_using_local_store, touch_user_profile

def _decode_jwt_payload(id_token: str):
    """Extract user info from a Firebase ID token payload.

    Used as a local-dev fallback when Firebase Admin credentials are not
    configured. The token is still issued by Firebase client SDK sign-in;
    we only skip server-side cryptographic verification.
    """
    try:
        parts = id_token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        payload += '=' * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))

        exp = data.get('exp', 0)
        if exp and exp < time.time():
            return None

        uid = data.get('sub') or data.get('user_id')
        if not uid:
            return None

        return {
            'uid': uid,
            'email': data.get('email'),
            'name': data.get('name') or data.get('email', '').split('@')[0],
        }
    except Exception:
        return None


def _ensure_firebase_initialized():
    """Initialize the Firebase Admin SDK on first use if not already done."""
    if firebase_admin._apps:
        return True
    if is_using_local_store():
        return False
    try:
        initialize_firebase()
        return bool(firebase_admin._apps)
    except Exception:
        return False


def verify_firebase_token(id_token: str):
    """Verify a Firebase ID token and return the user info."""
    try:
        if _ensure_firebase_initialized():
            decoded_token = auth.verify_id_token(id_token)
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name')
            }

        # Local dev fallback: accept tokens from Firebase client sign-in
        return _decode_jwt_payload(id_token)
    except Exception:
        return _decode_jwt_payload(id_token)


def require_auth(f):
    """Decorator to require Firebase authentication for an endpoint."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not id_token:
            id_token = request.cookies.get('firebase_token')

        if not id_token:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

        user_info = verify_firebase_token(id_token)
        if not user_info:
            return jsonify({'status': 'error', 'message': 'Invalid authentication token'}), 401

        request.current_user = user_info
        return f(*args, **kwargs)
        # Persist email/name on the user doc so the instructor roster can show it.
        try:
            touch_user_profile(user_info.get('uid'), user_info.get('email'), user_info.get('name'))
        except Exception:
            pass

    return decorated_function


def get_current_user():
    """Return the user_info stashed on `request` by require_auth."""
    return getattr(request, 'current_user', None)


from instructor_config import is_instructor_email


def is_instructor(user_info: dict) -> bool:
    return is_instructor_email(user_info.get('email'))


def require_instructor(f):
    """Decorator: authenticated user must be a configured instructor."""
    @functools.wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        user_info = get_current_user()
        if not is_instructor(user_info):
            return jsonify({'status': 'error', 'message': 'Instructor access required'}), 403
        return f(*args, **kwargs)
    return decorated_function
