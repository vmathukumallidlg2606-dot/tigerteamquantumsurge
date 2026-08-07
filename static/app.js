// Local state tracking
let appData = {
    username: "Veteran Scholar",
    instructorMode: "military_analogy",
    averageMastery: 0,
    lessonsCompleted: 0,
    reviewsCompleted: 0,
    domains: [],
    weakAreas: [],
    activityLogs: []
};

let currentView = "dashboard";

// Study Workspace active parameters
let activeDomainId = null;
let activeTopicId = null;
let activeWorkspaceTab = "lesson";

// Active Quiz states
let quizQuestions = [];
let currentQuestionIndex = 0;
let selectedAnswers = {};

// Load elements on load
document.addEventListener("DOMContentLoaded", () => {
    // Load the public curriculum catalog first so the Topics/Progress pages
    // always render, then attempt the authenticated progress load.
    fetchCatalog();
    fetchProgressData();
    refreshRole();

    // Listen for text selection inside the lesson viewport
    document.addEventListener("mouseup", handleTextSelection);
});


// --- Role-aware UI: show the Instructor nav only for instructors ---
let _cachedRole = null;

async function fetchMyRole() {
    try {
        const authHeaders = await getAuthHeaders();
        const resp = await fetch("/api/me", { headers: Object.assign({ "Content-Type": "application/json" }, authHeaders) });
        if (!resp.ok) return null;
        const data = await resp.json();
        _cachedRole = {
            uid: data.uid,
            email: data.email,
            name: data.name,
            role: data.role,
            is_instructor: !!data.is_instructor,
        };
        return _cachedRole;
    } catch (err) {
        console.error("Error fetching /api/me:", err);
        return null;
    }
}

function applyInstructorRole() {
    const btn = document.getElementById("nav-instructor");
    if (!btn) return;
    const show = !!(appData && appData.is_instructor);
    if (show) {
        btn.classList.remove("hidden-by-role");
        btn.style.display = "";
    } else {
        btn.classList.add("hidden-by-role");
        btn.style.display = "none";
    }
}

async function refreshRole() {
    const role = await fetchMyRole();
    if (role) {
        appData.is_instructor = role.is_instructor;
        appData.role = role.role;
        if (role.email) appData.userEmail = role.email;
    } else {
        appData.is_instructor = false;
        appData.role = "student";
    }
    applyInstructorRole();
    return role;
}

const _origRenderSignInPromptR = window.renderSignInPrompt;
window.renderSignInPrompt = function () {
    if (typeof _origRenderSignInPromptR === "function") _origRenderSignInPromptR();
    const btn = document.getElementById("nav-instructor");
    if (btn) {
        btn.classList.add("hidden-by-role");
        btn.style.display = "none";
    }
};


// Load the static Security+ domain/topic catalog (no auth required).
// This is reference data shared by all users; it is NOT personalized progress.
async function fetchCatalog() {
    try {
        const response = await fetch('/api/catalog', { method: 'GET' });
        if (!response.ok) return;
        const data = await response.json();
        if (!data || !data.domains) return;
        appData.domains = data.domains;
        renderTopicsDirectory();
        renderProgressPage();
    } catch (err) {
        console.error("Error loading catalog:", err);
    }
}

// Selection range storage
let currentSelectionRange = null;
let currentSelectionText = "";

function handleTextSelection(e) {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    const tooltip = document.getElementById("text-select-tooltip");

    // We only display the tooltip if selection is non-empty and inside lesson workspace
    if (selectedText.length > 3 && isSelectionInsideLesson(selection)) {
        currentSelectionText = selectedText;
        currentSelectionRange = selection.getRangeAt(0).cloneRange();

        // Position tooltip slightly above the cursor/selection bounds
        const rect = currentSelectionRange.getBoundingClientRect();
        tooltip.style.left = `${rect.left + window.scrollX + (rect.width/2) - 60}px`;
        tooltip.style.top = `${rect.top + window.scrollY - 38}px`;
        tooltip.classList.remove("hidden");
    } else {
        // If clicking elsewhere, hide tooltip (unless clicking the tooltip button itself)
        if (!e.target.closest("#text-select-tooltip")) {
            tooltip.classList.add("hidden");
        }
    }
}

function isSelectionInsideLesson(selection) {
    if (!selection.anchorNode) return false;
    let node = selection.anchorNode.parentNode;
    while (node) {
        if (node.id === "lesson-content-viewport" || node.classList.contains("rendered-markdown")) {
            return true;
        }
        node = node.parentNode;
    }
    return false;
}


// Notify the user and prompt sign-in when the server rejects the ID token.
// We intentionally do NOT auto-open the Google popup here (browsers block
// programmatic popups on load), we just clear the bad token and show a prompt.
function handleAuthError() {
    localStorage.removeItem("firebase_token");
    renderSignInPrompt();
}

// Render a friendly "please sign in" state in the dashboard so the app never
// looks broken when the user is not authenticated.
function renderSignInPrompt() {
    const domainList = document.getElementById("dashboard-domain-list");
    const activityFeed = document.getElementById("dashboard-activity-list");
    const quickGrid = document.getElementById("quick-jump-grid");
    if (domainList) {
        domainList.innerHTML = `
            <div class="signin-prompt">
                <span class="empty-icon">🔒</span>
                <h4>Sign in to see your progress</h4>
                <p>Your personalized Security+ dashboard unlocks after you sign in with Google.</p>
                <button onclick="signInWithGoogle()" class="google-signin-btn">🔒 Sign in with Google</button>
            </div>`;
    }
    if (activityFeed) {
        activityFeed.innerHTML = `<div class="empty-feed">Sign in to track your activity.</div>`;
    }
    if (quickGrid) {
        quickGrid.innerHTML = "";
    }
    // Reset headline metrics to zero so the page looks intentional, not broken.
    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    setText("metric-readiness", "0%");
    setText("metric-mastery", "0%");
    setText("metric-reviews", "0");
    setText("metric-lessons", "0");
    const bar = document.getElementById("metric-readiness-bar");
    if (bar) bar.style.width = "0%";
}

// Primary server fetch call
async function fetchProgressData() {
    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch('/api/progress', {
            method: 'GET',
            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders)
        });

        if (response.status === 401) {
            // Not signed in (or token expired) — show the sign-in prompt.
            renderSignInPrompt();
            return;
        }

        const data = await response.json();
        if (!data || data.status === "error") return;

        appData.username = data.username || appData.username;
        appData.instructorMode = data.instructor_mode || appData.instructorMode;
        appData.averageMastery = data.average_mastery || 0;
        appData.lessonsCompleted = data.lessons_completed || 0;
        appData.reviewsCompleted = data.reviews_completed;
        appData.domains = data.domains;
        appData.weakAreas = data.weak_areas;
        appData.activityLogs = data.activity_logs;

        // Render UI
        renderDashboard();
        renderTopicsDirectory();
        renderProgressPage();
        syncInstructorModeToggles();
        
        if (activeTopicId) {
            // Keep workspace metrics updated if user is studying
            const activeTopic = findTopicById(activeTopicId);
            if (activeTopic) {
                updateWorkspaceTopicUI(activeTopic);
            }
        }
    } catch (err) {
        console.error("Error loading progress details:", err);
    }
}

// Render Dashboard Panel
function renderDashboard() {
    // Upper statistics
    document.getElementById("metric-readiness").textContent = `${appData.averageMastery}%`;
    document.getElementById("metric-readiness-bar").style.width = `${appData.averageMastery}%`;
    document.getElementById("metric-mastery").textContent = `${appData.averageMastery}%`;
    document.getElementById("metric-reviews").textContent = appData.reviewsCompleted;
    document.getElementById("metric-lessons").textContent = appData.lessonsCompleted;

    // Domain Progress Bars
    const domainList = document.getElementById("dashboard-domain-list");
    domainList.innerHTML = "";
    appData.domains.forEach(domain => {
        const row = document.createElement("div");
        row.className = "domain-progress-row";
        row.innerHTML = `
            <div class="domain-progress-meta">
                <span>${domain.name}</span>
                <span>${domain.mastery}%</span>
            </div>
            <div class="domain-bar-bg">
                <div class="domain-bar-fill" style="width: ${domain.mastery}%;"></div>
            </div>
        `;
        domainList.appendChild(row);
    });

    // Recent Activity Feed
    const activityFeed = document.getElementById("dashboard-activity-list");
    activityFeed.innerHTML = "";
    if (appData.activityLogs && appData.activityLogs.length > 0) {
        appData.activityLogs.slice(0, 5).forEach(log => {
            const item = document.createElement("div");
            item.className = "activity-item";
            
            // Generate list of topics tested
            const topicsTested = log.breakdown.map(b => b.topic_name).join(", ");
            
            item.innerHTML = `
                <div class="activity-header-meta">
                    <span class="activity-title">Practice Quiz Taken</span>
                    <span class="activity-score">${log.score.toFixed(0)}% Score</span>
                </div>
                <div style="font-size:0.8rem; color:#64748b; margin-top:4px;">
                    Tested: ${topicsTested}
                </div>
                <span class="activity-date">${log.timestamp}</span>
            `;
            activityFeed.appendChild(item);
        });
    } else {
        activityFeed.innerHTML = `<div class="empty-feed">No activity yet. Start studying!</div>`;
    }

    // Quick Jump Grid (lists 4 topics matching focus priority)
    const quickGrid = document.getElementById("quick-jump-grid");
    quickGrid.innerHTML = "";
    
    // Flatten topics
    let quickTopics = [];
    appData.domains.forEach(domain => {
        domain.topics.forEach(t => {
            quickTopics.push({
                domainId: domain.id,
                domainName: domain.name,
                ...t
            });
        });
    });

    // Take first 4 topics
    quickTopics.slice(0, 4).forEach(topic => {
        const card = document.createElement("div");
        card.className = "quick-card";
        card.onclick = () => {
            switchNav("topics");
            enterTopicWorkspace(topic.domainId, topic.id);
        };
        
        // Translate confidence 1-5 into a mastery percentage
        const masteryPct = topic.confidence * 20;
        
        card.innerHTML = `
            <span class="quick-card-tag">${topic.domainName.split(",")[0]}</span>
            <h4>${topic.name}</h4>
            <div class="quick-card-footer">
                <span style="color:#64748b; font-size:0.75rem;">Mastery</span>
                <strong>${masteryPct}%</strong>
            </div>
        `;
        quickGrid.appendChild(card);
    });
}

// Render Topics list page
function renderTopicsDirectory() {
    const grid = document.getElementById("domain-cards-grid");
    grid.innerHTML = "";

    appData.domains.forEach(domain => {
        const card = document.createElement("div");
        card.className = "domain-card";
        
        // Sum total topics and completed topics
        const total = domain.topics.length;
        let completed = 0;
        domain.topics.forEach(t => {
            // Count as completed if confidence >= 3
            if (t.confidence >= 3) completed++;
        });

        card.innerHTML = `
            <div>
                <span class="domain-tag">${domain.id.toUpperCase().replace("_", " ")}</span>
                <h3>${domain.name}</h3>
                <p class="domain-desc">${domain.description}</p>
                
                <div class="domain-stats-grid">
                    <div class="domain-stat-block">
                        <span>Lessons</span>
                        <strong>${total}</strong>
                    </div>
                    <div class="domain-stat-block">
                        <span>Mastered</span>
                        <strong>${completed}</strong>
                    </div>
                    <div class="domain-stat-block">
                        <span>Confidence</span>
                        <strong>${(domain.mastery / 20).toFixed(1)}/5</strong>
                    </div>
                </div>
            </div>
            
            <div>
                <div style="margin-bottom:12px;">
                    <div class="domain-mastery-slider-meta">
                        <span>Mastery</span>
                        <span>${domain.mastery}%</span>
                    </div>
                    <div class="progress-track" style="height:6px;">
                        <div class="progress-fill" style="width: ${domain.mastery}%;"></div>
                    </div>
                </div>
                <button class="continue-btn" onclick="enterTopicWorkspace('${domain.id}', '${domain.topics[0].id}')">
                    Continue Learning →
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

// Render Progress report page
function renderProgressPage() {
    document.getElementById("prog-metric-readiness").textContent = `${appData.averageMastery}%`;
    
    const container = document.getElementById("progress-report-list");
    container.innerHTML = "";

    appData.domains.forEach(domain => {
        const group = document.createElement("div");
        group.className = "report-row-group";
        
        group.innerHTML = `<h4>${domain.name}</h4>`;
        
        const list = document.createElement("div");
        list.className = "report-item-list";
        
        domain.topics.forEach(topic => {
            const masteryPct = topic.confidence * 20;
            const item = document.createElement("div");
            item.className = "report-row-item";
            item.innerHTML = `
                <span class="report-item-title">${topic.name}</span>
                <div class="report-item-bar-container">
                    <div class="report-item-bar-bg">
                        <div class="report-item-bar-fill" style="width: ${masteryPct}%;"></div>
                    </div>
                    <span>${masteryPct}%</span>
                </div>
            `;
            list.appendChild(item);
        });
        
        group.appendChild(list);
        container.appendChild(group);
    });
}

// Navigation switch views
function switchNav(viewId) {
    currentView = viewId;

    // Sidebar navigation states
    document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`nav-${viewId}`).classList.add("active");

    // Toggle viewport views
    document.querySelectorAll(".viewport-view").forEach(view => view.classList.remove("active"));
    document.getElementById(`view-${viewId}`).classList.add("active");
    
    // Automatically close workspace window if returning to topic directory
    if(viewId === "topics") {
        exitTopicWorkspace();
    }
    updateChatContextLabel();
}

// Enter workspace study panel
function enterTopicWorkspace(domainId, topicId) {
    activeDomainId = domainId;
    activeTopicId = topicId;

    // Toggle DOM panels
    document.getElementById("topics-directory-container").classList.add("hidden");
    const ws = document.getElementById("topic-workspace-container");
    ws.classList.remove("hidden");

    // Fetch topic info
    const topic = findTopicById(topicId);
    const domain = appData.domains.find(d => d.id === domainId);

    if (topic && domain) {
        document.getElementById("ws-domain-name").textContent = domain.name;
        updateWorkspaceTopicUI(topic);
    }
    
    // Load initial tab views
    switchWorkspaceTab("lesson");
    
    // Clear viewport and reset to empty state first
    resetLessonViewport();
    resetQuizWorkspace();
    updateChatContextLabel();
}

function exitTopicWorkspace() {
    activeDomainId = null;
    activeTopicId = null;
    document.getElementById("topic-workspace-container").classList.add("hidden");
    document.getElementById("topics-directory-container").classList.remove("hidden");
    updateChatContextLabel();
}

function findTopicById(topicId) {
    let target = null;
    appData.domains.forEach(d => {
        d.topics.forEach(t => {
            if (t.id === topicId) target = t;
        });
    });
    return target;
}

function updateWorkspaceTopicUI(topic) {
    document.getElementById("ws-topic-name").textContent = topic.name;
    document.getElementById("ws-topic-desc").textContent = topic.description;
    
    const masteryPct = topic.confidence * 20;
    document.getElementById("ws-mastery-level").textContent = `${masteryPct}%`;
    
    // Slider values
    document.getElementById("ws-confidence-slider").value = topic.confidence;
    document.getElementById("ws-confidence-indicator").textContent = `${topic.confidence}/5`;
}

// Send confidence rating directly from slider
async function adjustConfidence() {
    if (!activeTopicId) return;
    const confidenceVal = parseInt(document.getElementById("ws-confidence-slider").value);

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/assess", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({
                topic_id: activeTopicId,
                confidence: confidenceVal
            })
        });

        if (response.status === 401) { handleAuthError(); return; }
        if (response.ok) {
            fetchProgressData();
        }
    } catch (err) {
        console.error("Error setting slider value:", err);
    }
}

// Workspace tab sheets switcher
function switchWorkspaceTab(tabId) {
    activeWorkspaceTab = tabId;
    
    // Tabs state
    document.querySelectorAll(".ws-tab").forEach(tab => tab.classList.remove("active"));
    document.getElementById(`ws-tab-${tabId}`).classList.add("active");

    // Panes state
    document.querySelectorAll(".ws-pane").forEach(pane => pane.classList.remove("active"));
    document.getElementById(`pane-ws-${tabId}`).classList.add("active");
}

// Reset lesson panel
function resetLessonViewport() {
    document.getElementById("lesson-content-viewport").innerHTML = `
        <div class="empty-view-state">
            <span class="empty-icon">📖</span>
            <h4>No lessons yet</h4>
            <p>Have the AI tutor generate a comprehensive lesson for this topic to start your study journey.</p>
            <button class="accent-action-btn" onclick="generateLesson()">Generate Your First Lesson</button>
        </div>
    `;
}

// Call Ollama backend dynamically to explain topic
async function generateLesson() {
    if (!activeTopicId) return;
    const viewport = document.getElementById("lesson-content-viewport");
    
    viewport.innerHTML = `
        <div class="empty-view-state">
            <span class="empty-icon">📖</span>
            <h4>Agentic AI is formulating lesson...</h4>
            <p>Evaluating ChromaDB vector objectives and querying live threat indicators via DuckDuckGo. Please wait...</p>
        </div>
    `;

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch(`/api/study/${activeTopicId}`, {
            method: "GET",
            headers: authHeaders
        });
        if (response.status === 401) { handleAuthError(); return; }
        const data = await response.json();
        
        if (data.explanation) {
            viewport.innerHTML = `
                <div class="rendered-markdown">
                    ${marked.parse(data.explanation)}
                </div>
            `;
            fetchProgressData();
        } else {
            viewport.innerHTML = `<p style="color:var(--color-danger);">Failed to generate lesson content.</p>`;
        }
    } catch (err) {
        viewport.innerHTML = `<p style="color:var(--color-danger);">Local host connection error or Ollama timeout.</p>`;
        console.error(err);
    }
}

// Toggle instructor mode style
async function setInstructorMode(mode) {
    appData.instructorMode = mode;
    syncInstructorModeToggles();

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/instructor/mode", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({ mode: mode })
        });
        
        if (response.ok) {
            // Re-render lesson if already open
            const viewport = document.getElementById("lesson-content-viewport");
            const isLessonGenerated = viewport.querySelector(".rendered-markdown") !== null;
            if(activeTopicId && isLessonGenerated) {
                generateLesson();
            }
            fetchProgressData();
        }
    } catch(err) {
        console.error("Error setting instructor mode:", err);
    }
}

function syncInstructorModeToggles() {
    document.querySelectorAll(".mode-select").forEach(b => b.classList.remove("active"));
    if(appData.instructorMode === "military_analogy") {
        document.getElementById("mode-mil").classList.add("active");
    } else {
        document.getElementById("mode-tech").classList.add("active");
    }
}


// --- Instructor dashboard data loaders + renderers ---
async function loadInstructorDashboard() {
    // Render the create-form lists from the catalog + roster (idempotent).
    try { renderInstructorTopicList(); } catch (e) { console.error(e); }
    const assignmentsEl = document.getElementById("instructor-assignments-list");
    const scoresEl = document.getElementById("instructor-scores-list");
    const studentsEl = document.getElementById("instructor-students-list");
    if (assignmentsEl) assignmentsEl.innerHTML = '<div class="empty-feed">Loading assignments\u2026</div>';
    if (scoresEl) scoresEl.innerHTML = '<div class="empty-feed">Loading scores\u2026</div>';
    if (studentsEl) studentsEl.innerHTML = '<div class="empty-feed">Loading students\u2026</div>';

    try {
        const authHeaders = await getAuthHeaders();
        const [dashResp, studentsResp] = await Promise.all([
            fetch("/api/instructor/dashboard", { headers: Object.assign({ "Content-Type": "application/json" }, authHeaders) }),
            fetch("/api/instructor/students", { headers: Object.assign({ "Content-Type": "application/json" }, authHeaders) }),
        ]);

        if (dashResp.status === 401 || studentsResp.status === 401) {
            renderSignInPrompt();
            return;
        }
        if (dashResp.status === 403 || studentsResp.status === 403) {
            const msg = "Instructor access required. Sign in with the configured instructor account.";
            if (assignmentsEl) assignmentsEl.innerHTML = '<div class="empty-feed">' + msg + '</div>';
            if (scoresEl) scoresEl.innerHTML = '<div class="empty-feed">' + msg + '</div>';
            if (studentsEl) studentsEl.innerHTML = '<div class="empty-feed">' + msg + '</div>';
            return;
        }

        const dash = await dashResp.json();
        const studentsPayload = await studentsResp.json();
        renderInstructorAssignments(dash.assignments || []);
        renderInstructorScores(dash.assignment_submissions || [], dash.quiz_reports || []);
        renderInstructorStudents(studentsPayload.students || []);
    try { renderInstructorStudentList(); } catch (e) { console.error(e); }
    } catch (err) {
        console.error("Error loading instructor dashboard:", err);
        const studentsEl2 = document.getElementById("instructor-students-list");
        if (studentsEl2) studentsEl2.innerHTML = '<div class="empty-feed">Failed to load students.</div>';
    }
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatScore(value) {
    if (value === null || value === undefined) return "\u2014";
    if (typeof value !== "number") return escapeHtml(value);
    return value.toFixed(1) + "%";
}

function renderInstructorAssignments(assignments) {
    const el = document.getElementById("instructor-assignments-list");
    if (!el) return;
    if (!assignments.length) {
        el.innerHTML = '<div class="empty-feed">No assignments yet. Create one above.</div>';
        return;
    }
    const rows = assignments.map(function (a) {
        return (
            '<tr>' +
                '<td>' + escapeHtml(a.title) + '</td>' +
                '<td><span class="badge">' + escapeHtml(a.access_code || "") + '</span></td>' +
                '<td>' + (a.question_count || 0) + '</td>' +
                '<td>' + (a.submission_count || 0) + '</td>' +
                '<td>' + formatScore(a.average_score) + '</td>' +
                '<td class="student-meta">' + escapeHtml(a.created_at || "") + '</td>' +
            '</tr>'
        );
    }).join("");
    el.innerHTML =
        '<table class="instructor-table">' +
            '<thead><tr><th>Title</th><th>Code</th><th>Qs</th><th>Subs</th><th>Avg</th><th>Created</th></tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
        '</table>';
}

function renderInstructorScores(submissions, reports) {
    const el = document.getElementById("instructor-scores-list");
    if (!el) return;
    const rows = [];
    submissions.forEach(function (s) {
        rows.push(
            '<tr>' +
                '<td><span class="badge muted">ASSIGN</span> ' + escapeHtml(s.assignment_title || s.assignment_id || "") + '</td>' +
                '<td>' + escapeHtml(s.student_email || s.student_uid || "") + '</td>' +
                '<td>' + formatScore(s.score) + '</td>' +
                '<td class="student-meta">' + escapeHtml(s.submitted_at || "") + '</td>' +
            '</tr>'
        );
    });
    reports.forEach(function (r) {
        const topic = (r.topic_ids && r.topic_ids.length) ? r.topic_ids.join(", ") : "Quick Quiz";
        rows.push(
            '<tr>' +
                '<td><span class="badge">QUIZ</span> ' + escapeHtml(topic) + '</td>' +
                '<td>' + escapeHtml(r.student_email || r.student_uid || "") + '</td>' +
                '<td>' + formatScore(r.score) + '</td>' +
                '<td class="student-meta">' + escapeHtml(r.submitted_at || "") + '</td>' +
            '</tr>'
        );
    });
    if (!rows.length) {
        el.innerHTML = '<div class="empty-feed">No scores yet. Once students submit, they will appear here.</div>';
        return;
    }
    el.innerHTML =
        '<table class="instructor-table">' +
            '<thead><tr><th>Source</th><th>Student</th><th>Score</th><th>Submitted</th></tr></thead>' +
            '<tbody>' + rows.join("") + '</tbody>' +
        '</table>';
}

function renderInstructorStudents(students) {
    const el = document.getElementById("instructor-students-list");
    if (!el) return;
    if (!students.length) {
        el.innerHTML = '<div class="empty-feed">No students have signed up yet.</div>';
        return;
    }
    const rows = students.map(function (s) {
        const email = s.email || "(no email)";
        const name = s.name ? '<div class="student-meta">' + escapeHtml(s.name) + '</div>' : "";
        const activity = [];
        activity.push('<span class="badge">' + (s.assignment_count || 0) + ' assignments</span>');
        activity.push('<span class="badge muted">' + (s.quiz_report_count || 0) + ' quick quizzes</span>');
        if (s.average_score !== null && s.average_score !== undefined) {
            activity.push('<span class="badge muted">avg ' + formatScore(s.average_score) + '</span>');
        }
        if (!s.has_progress) {
            activity.unshift('<span class="badge muted">just signed up</span>');
        }
        return (
            '<tr>' +
                '<td><div class="student-email">' + escapeHtml(email) + '</div>' + name + '</td>' +
                '<td>' + activity.join(" ") + '</td>' +
                '<td class="student-meta">' + escapeHtml(s.last_seen || "—") + '</td>' +
            '</tr>'
        );
    }).join("");
    el.innerHTML =
        '<table class="instructor-table">' +
            '<thead><tr><th>Email</th><th>Activity</th><th>Last seen</th></tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
        '</table>';
}

const _origSwitchNav = window.switchNav;
window.switchNav = function (viewId) {
    if (typeof _origSwitchNav === "function") _origSwitchNav(viewId);
    if (viewId === "instructor") {
        loadInstructorDashboard();
    }
};


// ====================================================================
// QuikQuiz Assignment flow (instructor side)
// ====================================================================
let _instructorTopics = [];
let _instructorStudents = [];
let _pendingAssignment = null; // last-created assignment, awaiting approve/draft

function renderInstructorTopicList() {
    const el = document.getElementById("instructor-topic-list");
    if (!el) return;
    el.innerHTML = "";
    const topics = (appData.domains || []).flatMap((d) => (d.topics || []).map((t) => ({ ...t, domainName: d.name, domainId: d.id })));
    _instructorTopics = topics;
    if (!topics.length) {
        el.innerHTML = '<div class="empty-feed">Topics will appear once the catalog loads.</div>';
        return;
    }
    topics.forEach((t) => {
        const wrap = document.createElement("label");
        wrap.className = "qq-topic-option";
        wrap.innerHTML = (
            '<input type="checkbox" data-topic-id="' + escapeAttr(t.id) + '">' +
            '<span><strong>' + escapeHtml(t.name) + '</strong><br>' +
            '<span class="student-meta">' + escapeHtml(t.domainName) + '</span></span>'
        );
        el.appendChild(wrap);
    });
    el.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.addEventListener("change", updateInstructorTopicCount);
    });
    updateInstructorTopicCount();
}

function updateInstructorTopicCount() {
    const el = document.getElementById("instructor-topic-count");
    if (!el) return;
    const checked = document.querySelectorAll('#instructor-topic-list input[type="checkbox"]:checked').length;
    el.textContent = checked + ' topic' + (checked === 1 ? '' : 's') + ' selected';
}

function selectAllInstructorTopics(checked) {
    document.querySelectorAll('#instructor-topic-list input[type="checkbox"]').forEach((cb) => { cb.checked = !!checked; });
    updateInstructorTopicCount();
}

function renderInstructorStudentList() {
    const el = document.getElementById("instructor-students-list-target");
    if (!el) return;
    el.innerHTML = "";
    if (!_instructorStudents.length) {
        el.innerHTML = '<div class="empty-feed">No students yet. Switch to "All students" to assign universally.</div>';
        updateInstructorStudentCount();
        return;
    }
    _instructorStudents.forEach((s) => {
        const wrap = document.createElement("label");
        wrap.className = "qq-topic-option";
        const display = s.email || s.uid;
        wrap.innerHTML = (
            '<input type="checkbox" data-uid="' + escapeAttr(s.uid) + '">' +
            '<span><strong>' + escapeHtml(display) + '</strong>' +
            (s.name ? '<br><span class="student-meta">' + escapeHtml(s.name) + '</span>' : '') +
            '</span>'
        );
        el.appendChild(wrap);
    });
    el.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.addEventListener("change", updateInstructorStudentCount);
    });
    updateInstructorStudentCount();
}

function updateInstructorStudentCount() {
    const el = document.getElementById("instructor-students-count");
    if (!el) return;
    const checked = document.querySelectorAll('#instructor-students-list-target input[type="checkbox"]:checked').length;
    el.textContent = checked + ' student' + (checked === 1 ? '' : 's') + ' selected';
}

function filterInstructorStudentList(query) {
    const q = (query || "").trim().toLowerCase();
    document.querySelectorAll('#instructor-students-list-target .qq-topic-option').forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.style.display = !q || text.indexOf(q) !== -1 ? "" : "none";
    });
}

function setAssigneeMode(mode) {
    const target = document.getElementById("instructor-students-target");
    if (!target) return;
    if (mode === "specific") {
        target.classList.remove("hidden");
    } else {
        target.classList.add("hidden");
    }
}

function setCreateProgress(visible, label, percent) {
    const wrap = document.getElementById("create-assignment-progress");
    const fill = document.getElementById("create-assignment-progress-fill");
    const lab = document.getElementById("create-assignment-progress-label");
    if (lab && label !== undefined) lab.textContent = label;
    if (fill && percent !== undefined) fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
    if (wrap) wrap.classList.toggle("hidden", !visible);
}

function setCreateBusy(busy) {
    const btn = document.getElementById("create-assignment-btn");
    if (!btn) return;
    btn.disabled = !!busy;
    btn.textContent = busy ? "Generating…" : "Create QuikQuiz";
}

function setStatus(elId, message, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("error", !!isError);
    el.classList.toggle("success", !isError && !!message);
    el.classList.toggle("hidden", !message);
}

async function createInstructorAssignment() {
    const title = (document.getElementById("assignment-title-input").value || "").trim();
    const topicIds = Array.from(document.querySelectorAll('#instructor-topic-list input[type="checkbox"]:checked')).map((cb) => cb.dataset.topicId);
    const modeRadio = document.querySelector('input[name="assignee-mode"]:checked');
    const mode = modeRadio ? modeRadio.value : "all";
    const assigneeUids = mode === "specific"
        ? Array.from(document.querySelectorAll('#instructor-students-list-target input[type="checkbox"]:checked')).map((cb) => cb.dataset.uid)
        : [];

    if (!title) { setStatus("create-assignment-status", "Enter a title.", true); return; }
    if (!topicIds.length) { setStatus("create-assignment-status", "Select at least one topic.", true); return; }
    if (mode === "specific" && !assigneeUids.length) { setStatus("create-assignment-status", "Select at least one student, or switch to All students.", true); return; }

    setStatus("create-assignment-status", "");
    setCreateBusy(true);
    setCreateProgress(true, "Starting generation…", 1);

    const totalTopics = topicIds.length;
    let step = 0;

    function tick() {
        step += 1;
        const pct = Math.min(95, Math.round((step / Math.max(1, totalTopics * 2)) * 100));
        setCreateProgress(true, "Generating questions for " + totalTopics + " topic" + (totalTopics === 1 ? "" : "s") + "…", pct);
    }

    // Simulate progress while the request is in flight (Gemma is slow).
    const tickInterval = setInterval(tick, 1500);

    try {
        const authHeaders = await getAuthHeaders();
        const resp = await fetch("/api/instructor/assignments", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({
                title: title,
                topic_ids: topicIds,
                assignee_mode: mode,
                assignee_uids: assigneeUids,
                status: "draft",
            }),
        });
        clearInterval(tickInterval);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            setCreateProgress(false);
            setStatus("create-assignment-status", err.message || "Failed to generate quiz (" + resp.status + ").", true);
            return;
        }
        const data = await resp.json();
        setCreateProgress(true, "Done.", 100);
        setTimeout(() => setCreateProgress(false), 600);
        _pendingAssignment = data;
        openReviewAssignmentModal();
        setStatus("create-assignment-status", "Draft created. Review the questions and choose Approve or Save as Draft.");
    } catch (err) {
        clearInterval(tickInterval);
        setCreateProgress(false);
        setStatus("create-assignment-status", "Network error: " + (err && err.message ? err.message : err), true);
    } finally {
        setCreateBusy(false);
    }
}

function openReviewAssignmentModal() {
    if (!_pendingAssignment) return;
    const a = _pendingAssignment.assignment;
    const qs = _pendingAssignment.questions || [];
    const meta = document.getElementById("review-meta");
    const list = document.getElementById("review-questions-list");
    if (meta) {
        const targets = a.assignee_mode === "all"
            ? '<span class="badge">All students</span>'
            : '<span class="badge">' + (a.assignee_uids || []).length + ' specific</span>';
        meta.innerHTML = (
            '<span class="badge">' + escapeHtml(a.title) + '</span>' +
            '<span class="badge muted">Code ' + escapeHtml(a.access_code) + '</span>' +
            '<span class="badge muted">' + qs.length + ' questions</span>' +
            targets
        );
    }
    if (list) {
        list.innerHTML = qs.map(function (q, i) {
            const opts = ["A", "B", "C", "D"].map(function (k) {
                const txt = (q.options || {})[k] || "";
                const cls = (k === q.correct_option) ? "correct" : "";
                return '<li class="' + cls + '">' + escapeHtml(k + ". " + txt) + '</li>';
            }).join("");
            const tags = [];
            if (q.topic_id) tags.push('<span class="badge muted">' + escapeHtml(q.topic_id) + '</span>');
            if (q.difficulty) tags.push('<span class="badge">' + escapeHtml(q.difficulty) + '</span>');
            return (
                '<div class="review-question">' +
                '<div class="rq-meta">' + tags.join(" ") + '<span class="student-meta">Q' + (i + 1) + '</span></div>' +
                '<div class="rq-scenario">' + escapeHtml(q.scenario || "") + '</div>' +
                '<div class="rq-text">' + escapeHtml(q.question_text || "") + '</div>' +
                '<ul class="rq-options">' + opts + '</ul>' +
                '</div>'
            );
        }).join("");
    }
    const m = document.getElementById("review-assignment-modal");
    if (m) m.classList.remove("hidden");
}

function closeReviewAssignmentModal() {
    const m = document.getElementById("review-assignment-modal");
    if (m) m.classList.add("hidden");
}

async function approveReviewedAssignment() {
    if (!_pendingAssignment) return;
    const id = _pendingAssignment.assignment.id;
    try {
        const authHeaders = await getAuthHeaders();
        const resp = await fetch("/api/instructor/assignments/" + encodeURIComponent(id) + "/approve", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            setStatus("create-assignment-status", err.message || "Failed to approve.", true);
            return;
        }
        setStatus("create-assignment-status", "Approved. Students can now see this assignment in My Assignments.");
        _pendingAssignment.assignment.status = "approved";
        closeReviewAssignmentModal();
        if (typeof loadInstructorDashboard === "function") loadInstructorDashboard();
    } catch (err) {
        setStatus("create-assignment-status", "Network error: " + err, true);
    }
}

async function saveReviewedAssignmentAsDraft() {
    setStatus("create-assignment-status", "Saved as draft. Students will not see this until you approve it.");
    closeReviewAssignmentModal();
}

function regenerateReviewedAssignment() {
    closeReviewAssignmentModal();
    const btn = document.getElementById("create-assignment-btn");
    if (btn) btn.click();
}

function escapeAttr(s) { return String(s == null ? "" : s).replace(/"/g, "&quot;"); }


// ====================================================================
// Student side: My Assignments + Start
// ====================================================================
async function loadMyAssignments() {
    const list = document.getElementById("my-assignments-list");
    if (!list) return;
    list.innerHTML = '<div class="empty-feed">Loading assignments…</div>';
    try {
        const authHeaders = await getAuthHeaders();
        const resp = await fetch("/api/my/assignments", { headers: Object.assign({ "Content-Type": "application/json" }, authHeaders) });
        if (resp.status === 401) { list.innerHTML = '<div class="empty-feed">Sign in to see your assignments.</div>'; return; }
        if (!resp.ok) { list.innerHTML = '<div class="empty-feed">Failed to load assignments.</div>'; return; }
        const data = await resp.json();
        const items = data.assignments || [];
        if (!items.length) { list.innerHTML = '<div class="empty-feed">No assignments assigned to you yet.</div>'; return; }
        list.innerHTML = items.map(function (a) {
            const status = a.submission
                ? '<span class="badge muted">Submitted ' + formatScore(a.submission.score) + '</span>'
                : '<span class="badge">Not started</span>';
            return (
                '<div class="my-assignment-row">' +
                    '<div>' +
                        '<div><strong>' + escapeHtml(a.title) + '</strong> ' + status + '</div>' +
                        '<div class="my-assignment-meta">' +
                            (a.topic_names || []).join(", ") + ' · ' +
                            (a.question_count || 0) + ' questions · ' +
                            'Code ' + escapeHtml(a.access_code || "") +
                        '</div>' +
                    '</div>' +
                    (a.submission
                        ? '<span class="student-meta">' + escapeHtml(a.submission.submitted_at || "") + '</span>'
                        : '<button class="primary-action-btn" data-start-assignment="' + escapeAttr(a.id) + '">Start</button>') +
                '</div>'
            );
        }).join("");
        list.querySelectorAll('button[data-start-assignment]').forEach(function (b) {
            b.addEventListener("click", function () { startAssignedQuiz(b.getAttribute("data-start-assignment")); });
        });
    } catch (err) {
        list.innerHTML = '<div class="empty-feed">Failed to load assignments.</div>';
    }
}

async function startAssignedQuiz(assignmentId) {
    try {
        const authHeaders = await getAuthHeaders();
        const resp = await fetch("/api/assignments/" + encodeURIComponent(assignmentId) + "/start", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert(err.message || "Failed to start assignment.");
            return;
        }
        // Reuse the existing QuikQuiz player: it already drives off /api/quiz/grade and quiz_cache.
        if (typeof window.beginQuikQuizWithQuestions === "function") {
            window.beginQuikQuizWithQuestions(await resp.json());
        } else {
            // Fall back: switch to the QuikQuiz view so the cached questions are used by the existing UI.
            switchNav("quikquiz");
            alert("Assignment queued. Click 'Start Assigned Quiz' is not available; the questions are cached for the next grading call.");
        }
    } catch (err) {
        alert("Network error: " + err);
    }
}



// --- QuikQuiz (standalone quick quiz) ---
let quikQuizSelectedTopics = [];

function showQuikQuizTopicPicker() {
    if (!appData.domains || appData.domains.length === 0) {
        alert("Topics are still loading. Please wait a moment and try again.");
        return;
    }

    const list = document.getElementById("quikquiz-topic-list");
    list.innerHTML = "";

    appData.domains.forEach(domain => {
        const group = document.createElement("div");
        group.className = "qq-topic-domain-group";

        const heading = document.createElement("h4");
        heading.className = "qq-topic-domain-name";
        heading.textContent = domain.name;
        group.appendChild(heading);

        const topicsWrap = document.createElement("div");
        topicsWrap.className = "qq-topic-options";

        (domain.topics || []).forEach(topic => {
            const label = document.createElement("label");
            label.className = "qq-topic-option";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "qq-topic-checkbox";
            checkbox.value = topic.id;

            const span = document.createElement("span");
            span.textContent = topic.name;

            label.appendChild(checkbox);
            label.appendChild(span);
            topicsWrap.appendChild(label);
        });

        group.appendChild(topicsWrap);
        list.appendChild(group);
    });

    document.getElementById("quikquiz-topic-modal").classList.remove("hidden");
}

function closeQuikQuizTopicPicker() {
    document.getElementById("quikquiz-topic-modal").classList.add("hidden");
}

function selectAllQuikQuizTopics(checked) {
    document.querySelectorAll(".qq-topic-checkbox").forEach(cb => {
        cb.checked = checked;
    });
}

function getSelectedQuikQuizTopicIds() {
    return Array.from(document.querySelectorAll(".qq-topic-checkbox:checked")).map(cb => cb.value);
}

function confirmQuikQuizTopics() {
    const topicIds = getSelectedQuikQuizTopicIds();
    if (topicIds.length === 0) {
        alert("Please select at least one topic to quiz on.");
        return;
    }
    closeQuikQuizTopicPicker();
    launchQuikQuiz(topicIds);
}

function resetQuikQuiz() {
    closeQuikQuizTopicPicker();
    document.getElementById("quikquiz-init").classList.remove("hidden");
    document.getElementById("quikquiz-active").classList.add("hidden");
    document.getElementById("quikquiz-results").classList.add("hidden");
}

async function launchQuikQuiz(topicIds) {
    quikQuizSelectedTopics = topicIds;
    activeTopicId = topicIds[0];

    const topicLabel = topicIds.length === 1
        ? (findTopicById(topicIds[0])?.name || "Quick Quiz")
        : `${topicIds.length} topics selected`;

    document.getElementById("quikquiz-init").classList.add("hidden");
    document.getElementById("quikquiz-results").classList.add("hidden");
    const activePane = document.getElementById("quikquiz-active");
    activePane.classList.remove("hidden");
    activePane.innerHTML = `
        <div class="quiz-workspace-init">
            <div class="empty-icon">🎯</div>
            <h4>Synthesizing AI practice questions...</h4>
            <p>Generating questions for your selected topics. Please wait...</p>
        </div>
    `;

    quizQuestions = [];
    currentQuestionIndex = 0;
    selectedAnswers = {};

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/quiz/generate", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({ topic_ids: topicIds })
        });
        if (response.status === 401) { handleAuthError(); resetQuikQuiz(); return; }
        const data = await response.json();
        if (!response.ok || data.status === "error") {
            alert(data.message || "Failed to generate quiz.");
            resetQuikQuiz();
            return;
        }
        quizQuestions = data.questions;

        if (quizQuestions && quizQuestions.length > 0) {
            activePane.innerHTML = `
                <div class="quiz-meta-header">
                    <span id="qq-quiz-topic">${topicLabel}</span>
                    <span id="qq-quiz-index">Question 1 of ${quizQuestions.length}</span>
                    <span id="qq-quiz-diff" class="difficulty-tag">medium</span>
                </div>
                <div class="quiz-card-body">
                    <div class="scenario-panel">
                        <strong>Scenario:</strong>
                        <p id="qq-quiz-scenario"></p>
                    </div>
                    <h4 id="qq-quiz-question-text">Question text?</h4>
                    <div id="qq-quiz-options" class="quiz-options-layout"></div>
                </div>
                <div class="quiz-controls-row">
                    <button id="qq-quiz-next-btn" class="primary-action-btn" onclick="nextQuikQuizQuestion()">Next Question</button>
                </div>
            `;
            showQuikQuizQuestion(0);
        } else {
            alert("LLM failed to output JSON list questions. Check Ollama server console.");
            resetQuikQuiz();
        }
    } catch (err) {
        console.error("Failed to generate QuikQuiz:", err);
        resetQuikQuiz();
    }
}

function showQuikQuizQuestion(index) {
    currentQuestionIndex = index;
    const q = quizQuestions[index];

    document.getElementById("qq-quiz-index").textContent = `Question ${index + 1} of ${quizQuestions.length}`;
    const topicEl = document.getElementById("qq-quiz-topic");
    if (topicEl) {
        topicEl.textContent = quikQuizSelectedTopics.length > 1
            ? (q.topic_name || "Quick Quiz")
            : (findTopicById(quikQuizSelectedTopics[0])?.name || q.topic_name || "Quick Quiz");
    }
    document.getElementById("qq-quiz-diff").textContent = q.difficulty;
    document.getElementById("qq-quiz-scenario").textContent = q.scenario;
    document.getElementById("qq-quiz-question-text").textContent = q.question_text;

    const optionsContainer = document.getElementById("qq-quiz-options");
    optionsContainer.innerHTML = "";

    Object.entries(q.options).forEach(([key, val]) => {
        const card = document.createElement("button");
        card.className = `option-card ${selectedAnswers[q.id] === key ? "selected" : ""}`;
        card.onclick = () => {
            selectedAnswers[q.id] = key;
            showQuikQuizQuestion(currentQuestionIndex);
        };
        card.innerHTML = `
            <span class="option-letter">${key}</span>
            <span>${val}</span>
        `;
        optionsContainer.appendChild(card);
    });

    const nextBtn = document.getElementById("qq-quiz-next-btn");
    nextBtn.textContent = index === quizQuestions.length - 1 ? "Finish & Grade Quiz" : "Next Question";
}

function nextQuikQuizQuestion() {
    const q = quizQuestions[currentQuestionIndex];
    if (!selectedAnswers[q.id]) {
        alert("Please choose an answer card to proceed.");
        return;
    }

    if (currentQuestionIndex < quizQuestions.length - 1) {
        showQuikQuizQuestion(currentQuestionIndex + 1);
    } else {
        gradeQuikQuiz();
    }
}

async function gradeQuikQuiz() {
    const activePane = document.getElementById("quikquiz-active");
    const resultsPane = document.getElementById("quikquiz-results");

    activePane.classList.add("hidden");
    resultsPane.classList.remove("hidden");
    resultsPane.innerHTML = `<h3>Grading Quiz & analyzing response cards...</h3>`;

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/quiz/grade", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({ answers: selectedAnswers })
        });

        if (response.status === 401) { handleAuthError(); return; }
        const data = await response.json();

        resultsPane.innerHTML = `
            <div class="quiz-results-banner">
                <h3 id="qq-results-score">Quiz Complete: ${data.score.toFixed(0)}%</h3>
                <p id="qq-results-summary">You answered ${data.correct_answers} out of ${data.total_questions} questions correctly.</p>
                <button class="primary-action-btn" onclick="showQuikQuizTopicPicker()">Generate Another</button>
                <button class="text-link-btn" onclick="resetQuikQuiz()">Back to Start</button>
            </div>
            <div id="qq-results-breakdown" class="results-explanations-list"></div>
        `;

        const breakdown = document.getElementById("qq-results-breakdown");
        data.results.forEach((res, index) => {
            const card = document.createElement("div");
            card.className = "result-explanation-card";

            const qMeta = quizQuestions[index];
            const statusClass = res.was_correct ? "correct" : "incorrect";
            const statusLabel = res.was_correct ? "✓ Correct" : "✗ Incorrect";

            card.innerHTML = `
                <div class="result-status-header ${statusClass}">
                    <span>${statusLabel} | Question ${index + 1}</span>
                </div>
                <div class="scenario-panel" style="margin-bottom:12px;">
                    <strong>Scenario context:</strong>
                    <p>${qMeta.scenario}</p>
                </div>
                <h4 style="margin-bottom:8px;">Q: ${qMeta.question_text}</h4>
                <p><strong>Your Selection:</strong> ${res.user_answer ? res.user_answer + ": " + qMeta.options[res.user_answer] : "None"}</p>
                <p style="margin-bottom:16px;"><strong>Correct Selection:</strong> ${res.correct_answer + ": " + qMeta.options[res.correct_answer]}</p>
                <div class="divider" style="margin:12px 0; height:1px; background:#e2e8f0;"></div>
                <div class="rendered-markdown" style="padding:0; border:none; background:transparent;">
                    ${marked.parse(res.explanation)}
                </div>
            `;
            breakdown.appendChild(card);
        });

        fetchProgressData();
    } catch (err) {
        console.error("QuikQuiz grading error:", err);
        resultsPane.innerHTML = `<p>Error retrieving graded statistics.</p>`;
    }
}

// --- Live AI Quiz Generator ---
function resetQuizWorkspace() {
    document.getElementById("quiz-workspace-init").classList.remove("hidden");
    document.getElementById("quiz-workspace-active").classList.add("hidden");
    document.getElementById("quiz-workspace-results").classList.add("hidden");
}

async function startWorkspaceQuiz() {
    if (!activeTopicId) return;
    
    const initPane = document.getElementById("quiz-workspace-init");
    const activePane = document.getElementById("quiz-workspace-active");
    const resultsPane = document.getElementById("quiz-workspace-results");
    
    initPane.classList.add("hidden");
    resultsPane.classList.add("hidden");
    activePane.classList.remove("hidden");
    
    activePane.innerHTML = `
        <div class="quiz-workspace-init">
            <div class="empty-icon">🎯</div>
            <h4>Synthesizing AI practice questions...</h4>
            <p>Structuring multiple choice JSON vectors via local LLM. Please wait...</p>
        </div>
    `;

    quizQuestions = [];
    currentQuestionIndex = 0;
    selectedAnswers = {};

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch(`/api/quiz/${activeTopicId}`, {
            method: "GET",
            headers: authHeaders
        });
        if (response.status === 401) { handleAuthError(); return; }
        const data = await response.json();
        quizQuestions = data.questions;
        
        if(quizQuestions && quizQuestions.length > 0) {
            // Re-render structural elements
            activePane.innerHTML = `
                <div class="quiz-meta-header">
                    <span id="ws-quiz-index">Question 1 of 3</span>
                    <span id="ws-quiz-diff" class="difficulty-tag">medium</span>
                </div>
                <div class="quiz-card-body">
                    <div class="scenario-panel">
                        <strong>Scenario:</strong>
                        <p id="ws-quiz-scenario"></p>
                    </div>
                    <h4 id="ws-quiz-question-text">Question text?</h4>
                    <div id="ws-quiz-options" class="quiz-options-layout"></div>
                </div>
                <div class="quiz-controls-row">
                    <button id="ws-quiz-next-btn" class="primary-action-btn" onclick="nextWorkspaceQuestion()">Next Question</button>
                </div>
            `;
            showWorkspaceQuestion(0);
        } else {
            alert("LLM failed to output JSON list questions. Check Ollama server console.");
            resetQuizWorkspace();
        }
    } catch(err) {
        console.error("Failed to generate AI quiz:", err);
        resetQuizWorkspace();
    }
}

function showWorkspaceQuestion(index) {
    currentQuestionIndex = index;
    const q = quizQuestions[index];

    document.getElementById("ws-quiz-index").textContent = `Question ${index + 1} of ${quizQuestions.length}`;
    
    const diffTag = document.getElementById("ws-quiz-diff");
    diffTag.textContent = q.difficulty;
    
    document.getElementById("ws-quiz-scenario").textContent = q.scenario;
    document.getElementById("ws-quiz-question-text").textContent = q.question_text;

    const optionsContainer = document.getElementById("ws-quiz-options");
    optionsContainer.innerHTML = "";

    Object.entries(q.options).forEach(([key, val]) => {
        const card = document.createElement("button");
        card.className = `option-card ${selectedAnswers[q.id] === key ? 'selected' : ''}`;
        card.onclick = () => {
            selectedAnswers[q.id] = key;
            showWorkspaceQuestion(currentQuestionIndex);
        };
        card.innerHTML = `
            <span class="option-letter">${key}</span>
            <span>${val}</span>
        `;
        optionsContainer.appendChild(card);
    });

    const nextBtn = document.getElementById("ws-quiz-next-btn");
    if(index === quizQuestions.length - 1) {
        nextBtn.textContent = "Finish & Grade Quiz";
    } else {
        nextBtn.textContent = "Next Question";
    }
}

function nextWorkspaceQuestion() {
    const q = quizQuestions[currentQuestionIndex];
    if(!selectedAnswers[q.id]) {
        alert("Please choose an answer card to proceed.");
        return;
    }

    if (currentQuestionIndex < quizQuestions.length - 1) {
        showWorkspaceQuestion(currentQuestionIndex + 1);
    } else {
        gradeWorkspaceQuiz();
    }
}

async function gradeWorkspaceQuiz() {
    const activePane = document.getElementById("quiz-workspace-active");
    const resultsPane = document.getElementById("quiz-workspace-results");
    
    activePane.classList.add("hidden");
    resultsPane.classList.remove("hidden");
    
    resultsPane.innerHTML = `<h3>Grading Quiz & analyzing response cards...</h3>`;

    const payload = {
        answers: selectedAnswers
    };

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/quiz/grade", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify(payload)
        });

        if (response.status === 401) { handleAuthError(); return; }
        const data = await response.json();
        
        resultsPane.innerHTML = `
            <div class="quiz-results-banner">
                <h3 id="ws-results-score">Quiz Complete: ${data.score.toFixed(0)}%</h3>
                <p>You answered ${data.correct_answers} out of ${data.total_questions} questions correctly.</p>
                <button class="primary-action-btn" onclick="startWorkspaceQuiz()">Retake Practice Quiz</button>
            </div>
            <div id="ws-results-breakdown" class="results-explanations-list"></div>
        `;

        const breakdown = document.getElementById("ws-results-breakdown");
        data.results.forEach((res, index) => {
            const card = document.createElement("div");
            card.className = "result-explanation-card";
            
            const qMeta = quizQuestions[index];
            const statusClass = res.was_correct ? "correct" : "incorrect";
            const statusLabel = res.was_correct ? "✓ Correct" : "✗ Incorrect";

            card.innerHTML = `
                <div class="result-status-header ${statusClass}">
                    <span>${statusLabel} | Question ${index + 1}</span>
                </div>
                <div class="scenario-panel" style="margin-bottom:12px;">
                    <strong>Scenario context:</strong>
                    <p>${qMeta.scenario}</p>
                </div>
                <h4 style="margin-bottom:8px;">Q: ${qMeta.question_text}</h4>
                <p><strong>Your Selection:</strong> ${res.user_answer ? res.user_answer + ": " + qMeta.options[res.user_answer] : "None"}</p>
                <p style="margin-bottom:16px;"><strong>Correct Selection:</strong> ${res.correct_answer + ": " + qMeta.options[res.correct_answer]}</p>
                <div class="divider" style="margin:12px 0; height:1px; background:#e2e8f0;"></div>
                <div class="rendered-markdown" style="padding:0; border:none; background:transparent;">
                    ${marked.parse(res.explanation)}
                </div>
            `;
            breakdown.appendChild(card);
        });

        // Pull final stats refresh
        fetchProgressData();
    } catch(err) {
        console.error("Quiz grading error:", err);
        resultsPane.innerHTML = `<p>Error retrieving graded statistics.</p>`;
    }
}

// --- Floating AI Chat Widget Handlers ---
function toggleChatWidget() {
    const widget = document.getElementById("ai-chat-widget");
    const icon = document.getElementById("chat-toggle-icon");
    if(widget.classList.contains("collapsed")) {
        widget.classList.remove("collapsed");
        icon.textContent = "✕";
    } else {
        widget.classList.add("collapsed");
        icon.textContent = "💬";
    }
}

function handleChatSubmit(e) {
    if(e.key === "Enter") {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const input = document.getElementById("chat-input-field");
    const query = input.value.trim();
    if(!query) return;

    // Append user message
    const msgContainer = document.getElementById("chat-messages-container");
    const userDiv = document.createElement("div");
    userDiv.className = "chat-message user";
    userDiv.textContent = query;
    msgContainer.appendChild(userDiv);
    input.value = "";
    msgContainer.scrollTop = msgContainer.scrollHeight;

    // Loading agent state
    const agentDiv = document.createElement("div");
    agentDiv.className = "chat-message agent";
    agentDiv.innerHTML = "<em>Typing answer...</em>";
    msgContainer.appendChild(agentDiv);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    // Define context payload
    let activeContext = "Dashboard Overview";
    if (activeTopicId) {
        const topic = findTopicById(activeTopicId);
        if (topic) activeContext = `Topic: ${topic.name}`;
    }

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({
                query: query,
                context: activeContext,
                topic_id: activeTopicId
            })
        });
        if (response.status === 401) { handleAuthError(); return; }
        const data = await response.json();
        agentDiv.innerHTML = marked.parse(data.answer);
    } catch(err) {
        agentDiv.textContent = "Connection issue. Make sure Ollama LLM server is running.";
    }
    msgContainer.scrollTop = msgContainer.scrollHeight;
}

// Update Context Label based on active view/topics
function updateChatContextLabel() {
    const label = document.getElementById("chat-context-label");
    if (activeTopicId) {
        const topic = findTopicById(activeTopicId);
        if (topic) {
            label.textContent = `Topic: ${topic.name}`;
            return;
        }
    }
    const viewLabels = {
        dashboard: "Dashboard Overview",
        topics: "Topics & Domains",
        progress: "Progress",
        quikquiz: "QuikQuiz",
    };
    label.textContent = viewLabels[currentView] || currentView + " View";
}

async function requestDumbDown() {
    const tooltip = document.getElementById("text-select-tooltip");
    tooltip.classList.add("hidden");

    if (!currentSelectionText || !currentSelectionRange) return;

    const originalText = currentSelectionText;

    // Create wrapper node with loading style
    const span = document.createElement("span");
    span.className = "rewritten-highlight";
    
    // Store original text in a data attribute
    span.setAttribute("data-original", originalText);
    span.textContent = "[Rewriting...]";
    
    // Delete target selection and insert placeholder
    currentSelectionRange.deleteContents();
    currentSelectionRange.insertNode(span);
    
    // Clear browser selection highlights
    window.getSelection().removeAllRanges();

    try {
        const authHeaders = await getAuthHeaders();
        const response = await fetch("/api/rewrite", {
            method: "POST",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders),
            body: JSON.stringify({ text: originalText })
        });
        if (response.status === 401) { handleAuthError(); return; }
        const data = await response.json();
        
        if (data.simplified) {
            span.innerHTML = `
                <span class="rewritten-text-content">${data.simplified}</span>
                <button class="undo-rewrite-btn" title="Undo simplification" onclick="undoRewrite(this, event)">↩</button>
            `;
        } else {
            span.textContent = originalText; // fallback
        }
    } catch(err) {
        console.error(err);
        span.textContent = originalText; // fallback on connection error
    }
    
    // Reset temporary states
    currentSelectionText = "";
    currentSelectionRange = null;
}

function undoRewrite(btn, event) {
    event.stopPropagation();
    const highlightSpan = btn.closest(".rewritten-highlight");
    if (highlightSpan) {
        const originalText = highlightSpan.getAttribute("data-original");
        const simplifiedContent = highlightSpan.querySelector(".rewritten-text-content").textContent;

        // Replace highlightSpan with a temporary container that allows redoing
        const redoContainer = document.createElement("span");
        redoContainer.className = "undone-rewrite-container";
        redoContainer.setAttribute("data-original", originalText);
        redoContainer.setAttribute("data-simplified", simplifiedContent);
        
        redoContainer.innerHTML = `
            <span class="original-text-content">${originalText}</span>
            <button class="redo-rewrite-btn" title="Redo simplification" onclick="redoRewrite(this, event)">↪</button>
        `;

        highlightSpan.parentNode.replaceChild(redoContainer, highlightSpan);
    }
}

function redoRewrite(btn, event) {
    event.stopPropagation();
    const container = btn.closest(".undone-rewrite-container");
    if (container) {
        const originalText = container.getAttribute("data-original");
        const simplifiedText = container.getAttribute("data-simplified");

        const span = document.createElement("span");
        span.className = "rewritten-highlight";
        span.setAttribute("data-original", originalText);
        span.innerHTML = `
            <span class="rewritten-text-content">${simplifiedText}</span>
            <button class="undo-rewrite-btn" title="Undo simplification" onclick="undoRewrite(this, event)">↩</button>
        `;

        container.parentNode.replaceChild(span, container);
    }
}






document.addEventListener("DOMContentLoaded", () => {
    // Wire Create QuikQuiz controls.
    const createBtn = document.getElementById("create-assignment-btn");
    if (createBtn) createBtn.addEventListener("click", createInstructorAssignment);
    const topicsAll = document.getElementById("instructor-topics-all");
    const topicsNone = document.getElementById("instructor-topics-none");
    if (topicsAll) topicsAll.addEventListener("click", () => selectAllInstructorTopics(true));
    if (topicsNone) topicsNone.addEventListener("click", () => selectAllInstructorTopics(false));
    document.querySelectorAll('input[name="assignee-mode"]').forEach((r) => {
        r.addEventListener("change", () => setAssigneeMode(r.value));
    });
    const search = document.getElementById("instructor-students-search");
    if (search) search.addEventListener("input", () => filterInstructorStudentList(search.value));
    const studentsAll = document.getElementById("instructor-students-all");
    const studentsNone = document.getElementById("instructor-students-none");
    if (studentsAll) studentsAll.addEventListener("click", () => {
        document.querySelectorAll('#instructor-students-list-target input[type="checkbox"]').forEach((cb) => { cb.checked = true; cb.closest(".qq-topic-option") && (cb.closest(".qq-topic-option").style.display = ""); });
        updateInstructorStudentCount();
    });
    if (studentsNone) studentsNone.addEventListener("click", () => {
        document.querySelectorAll('#instructor-students-list-target input[type="checkbox"]').forEach((cb) => { cb.checked = false; });
        updateInstructorStudentCount();
    });
});

document.addEventListener("DOMContentLoaded", () => {
    // Load My Assignments whenever the QuikQuiz view becomes active.
    const _origSwitch2 = window.switchNav;
    if (typeof _origSwitch2 === "function" && !window._myAssignmentsWired) {
        window._myAssignmentsWired = true;
        window.switchNav = function (viewId) {
            _origSwitch2(viewId);
            if (viewId === "quikquiz") loadMyAssignments();
        };
    }
});
