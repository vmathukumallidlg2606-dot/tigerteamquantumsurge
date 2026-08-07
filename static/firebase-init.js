// Firebase client SDK configuration
const firebaseConfig = {
    apiKey: "AIzaSyCF-YEp6cD24GfAMFYNEwkoQAZqTrmw0aE",
    authDomain: "quantumsurgevenkata.firebaseapp.com",
    projectId: "quantumsurgevenkata",
    storageBucket: "quantumsurgevenkata.firebasestorage.app",
    messagingSenderId: "358906832964",
    appId: "1:358906832964:web:cdef26da99c865a73a7411"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Google Authentication Provider
const googleProvider = new firebase.auth.GoogleAuthProvider();

// Auth state listener - automatically handle user login/logout
firebase.auth().onAuthStateChanged(async (user) => {
    if (user) {
        console.log("User authenticated:", user.displayName);
        const token = await user.getIdToken();
        localStorage.setItem("firebase_token", token);

        updateAuthUI(true, user.displayName, user.photoURL);

        // Reload personalized progress after sign-in
        if (typeof fetchProgressData === 'function') {
            fetchProgressData();
        }
    } else {
        console.log("No user authenticated");
        localStorage.removeItem("firebase_token");
        updateAuthUI(false);
        if (typeof renderSignInPrompt === 'function') {
            renderSignInPrompt();
        }
    }
});

// Google Sign In
async function signInWithGoogle() {
    try {
        console.log("Opening Google sign-in popup...");
        const result = await firebase.auth().signInWithPopup(googleProvider);
        console.log("Sign-in successful:", result.user?.displayName);
    } catch (error) {
        console.error("Google sign-in error:", error.code, error.message);
        alert(`Sign-in error: ${error.message || error.code}`);
    }
}

// Sign Out
async function signOut() {
    try {
        await firebase.auth().signOut();
    } catch (error) {
        console.error("Sign-out error:", error);
    }
}

// Build Authorization headers for API calls using the current Firebase ID token.
// Falls back to a stored token if the async refresh hasn't resolved yet.
async function getAuthHeaders() {
    const token = await getCurrentIdToken();
    if (!token) return {};
    return { 'Authorization': `Bearer ${token}` };
}

// Return a (fresh) Firebase ID token, or the cached one if not signed in yet.
async function getCurrentIdToken() {
    const user = firebase.auth().currentUser;
    if (!user) {
        return localStorage.getItem("firebase_token") || null;
    }
    // Force refresh so the server always gets a valid, unexpired token.
    const token = await user.getIdToken(true);
    localStorage.setItem("firebase_token", token);
    return token;
}

// Update authentication UI
function updateAuthUI(isLoggedIn, displayName, photoURL) {
    const authBtn = document.getElementById("auth-button");
    if (!authBtn) return;
    
    if (isLoggedIn && displayName) {
        authBtn.innerHTML = `
            <img src="${photoURL || '/static/default-avatar.png'}" class="auth-avatar" alt="Profile">
            <span>${escapeHtml(displayName)}</span>
            <button onclick="signOut()" class="sign-out-btn">Sign Out</button>
        `;
        authBtn.classList.add("logged-in");
    } else {
        authBtn.innerHTML = `<button onclick="signInWithGoogle()" class="google-signin-btn">🔒 Sign in with Google</button>`;
        authBtn.classList.remove("logged-in");
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}