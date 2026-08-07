# Google Authentication Setup Guide

## Implementation Complete ✅

The following files have been created/updated for Google authentication:

| File | Purpose |
|------|---------|
| `firebase_auth.py` | Backend ID-token verification (`verify_firebase_token`, `require_auth`) |
| `firebase_config.py` | UID-keyed Firestore access + quiz-history subcollection + secret/env credentials |
| `server.py` | All user-data endpoints protected by `@require_auth` |
| `templates/index.html` | Firebase SDK + Sign-In button |
| `static/firebase-init.js` | Client-side auth + `getAuthHeaders()` Bearer-token helper |
| `static/style.css` | Auth button styling |
| `static/app.js` | Sends `Authorization: Bearer <idToken>` on every API call |

## Security Model

- **Service-account key is never committed.** It is supplied at runtime via one of:
  - `FIREBASE_SERVICE_ACCOUNT_JSON` — the raw service-account JSON (ideal for Secret Manager / CI secrets), or
  - `FIREBASE_SERVICE_ACCOUNT_PATH` — path to a local key file, or
  - Application Default Credentials (Cloud Run / Cloud Functions / `gcloud auth`).
  - The repo `.gitignore` blocks `*.service-account.json`, `*.bak`, `*.backup`, and `*.env`.
- **Every endpoint that touches user data is protected** by `@require_auth`:
  `/api/progress`, `/api/assess`, `/api/study/<topic_id>`, `/api/quiz/<topic_id>`,
  `/api/quiz/grade`, `/api/chat`, `/api/rewrite`.
- **ID token is sent from the client** as an `Authorization: Bearer <idToken>` header
  (via `getAuthHeaders()`). On `401` the client clears the cached token and prompts re-login.
- **Data is isolated per user by Firebase UID.** Progress is stored in
  `users/{uid}`. Quiz history lives in a **subcollection** `users/{uid}/quiz_history/{attemptId}`
  so it can scale independently of the user document.

## Your Remaining Steps

### 1. ✅ COMPLETED - Firebase Web API Key Already Configured!
The configuration in `static/firebase-init.js` has been updated with your actual values:
```javascript
const firebaseConfig = {
    apiKey: "AIzaSyCF-YEp6cD24GfAMFYNEwkoQAZqTrmw0aE",
    authDomain: "quantumsurgevenkata.firebaseapp.com",
    projectId: "quantumsurgevenkata",
    storageBucket: "quantumsurgevenkata.firebasestorage.app",
    messagingSenderId: "358906832964",
    appId: "1:358906832964:web:cdef26da99c865a73a7411"
};
```

### 2. Provide the Admin SDK credentials (do NOT commit a key file)
Set one of these in your environment / secret manager, e.g.:
```bash
export FIREBASE_SERVICE_ACCOUNT_JSON='{ "type": "service_account", ... }'
# or
export FIREBASE_SERVICE_ACCOUNT_PATH=/secure/path/firebase-service-account.json
```

### 3. Enable Google Sign-In Provider
Visit: **Firebase Console** → **Authentication** → **Sign-in method** tab

- Click **Google**
- Toggle **Enable**
- Click **Save**

### 4. Add Authorized Domains (CRITICAL)
In **Firebase Console** → **Authentication** → **Settings** tab → **Authorized domains**:

Add these domains:
- `localhost`
- `quantumsurge.mycpuinfo.com`

**This is required for the popup to work** - otherwise it closes immediately!

### 5. Test the Integration
1. Set the credentials env var (see step 2).
2. Restart the server: `python server.py`
3. Visit: http://127.0.0.1:5000
4. Click **"Sign in with Google"** in the top-right corner
5. Complete the Google sign-in flow

## How It Works

1. User clicks "Sign in with Google"
2. Firebase client SDK handles OAuth popup and returns an ID token
3. Client attaches the token as `Authorization: Bearer <idToken>` on every API call
4. Server's `@require_auth` decorator verifies the token with Firebase Admin SDK
5. Authenticated requests operate only on `users/{uid}` — the caller's own data

Each authenticated user has their own progress document and an isolated
`quiz_history` subcollection in Firestore.
