# Quantum Surge — Full System Workflow Documentation

> **CompTIA Security+ SY0-701 AI-Powered Study Platform**

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tool Stack](#tool-stack)
3. [Workflow Diagram](#workflow-diagram)
4. [Component Deep Dive](#component-deep-dive)
   - [Ollama — Local AI Server](#1-ollama--local-ai-server)
   - [Gemma 3 — LLM Model](#2-gemma-3--llm-model)
   - [ChromaDB — Vector Database (RAG)](#3-chromadb--vector-database-rag)
   - [DuckDuckGo Search — Live Threat Intel](#4-duckduckgo-search--live-threat-intel)
   - [Flask — Web Application Server](#5-flask--web-application-server)
   - [Cloudflare Tunnel — Public Exposure](#6-cloudflare-tunnel--public-exposure)
   - [Watchdog — Auto-Recovery](#7-watchdog--auto-recovery)
5. [How to Start Everything](#how-to-start-everything)
6. [API Endpoints](#api-endpoints)

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                              │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                  Cloudflare Tunnel (trycloudflare.com)              │
│               https://xxxx.trycloudflare.com ──► localhost:5000    │
└────────────────────────────────────────────────────────────────────┘
                           │ HTTP
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Flask Web Server (Port 5000)                    │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ index.html│  │ app.js   │  │style.css │  │  API Routes      │  │
│  │ (UI)      │  │(Frontend)│  │(Styling) │  │  /api/*          │  │
│  └───────────┘  └──────────┘  └──────────┘  └────────┬─────────┘  │
└────────────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌──────────┐ ┌──────────────────┐
│   Ollama Server  │ │ ChromaDB │ │ DuckDuckGo       │
│   (Port 11434)   │ │ (Vector  │ │ Search (Live     │
│   ┌───────────┐  │ │  Store)  │ │  Threat Intel)   │
│   │ Gemma 3   │  │ │          │ │                  │
│   │ 4.3B Q4_K │  │ │ RAG      │ │ Recent attacks   │
│   │ (NVIDIA   │  │ │ context  │ │ news for topic   │
│   │  GPU)     │  │ │ retrieval│ │                  │
│   └───────────┘  │ └──────────┘ └──────────────────┘
└─────────────────┘
```

---

## Tool Stack

| Layer | Tool | Version | Purpose |
|-------|------|---------|---------|
| **AI Engine** | Ollama | 0.17.1 | Local LLM server hosting models |
| **LLM Model** | Gemma 3 | 4.3B Q4_K_M | AI explanation & quiz generation |
| **GPU Acceleration** | NVIDIA CUDA | 12.7 | Run AI models on RTX 4060 GPU |
| **Vector Database** | ChromaDB | — | RAG context storage for SY0-701 objectives |
| **Web Search** | DuckDuckGo (ddgs) | — | Live threat intelligence retrieval |
| **Web Framework** | Flask | — | Python web server & REST API |
| **Frontend** | Vanilla JS + CSS | — | Dashboard UI in browser |
| **Tunneling** | Cloudflare (cloudflared) | 2026.6.1 | Public URL via trycloudflare.com |
| **Auto-Recovery** | PowerShell Watchdog | — | Monitors & restarts all services |

---

## Component Deep Dive

### 1. Ollama — Local AI Server

**Purpose:** Runs large language models locally on your machine without sending data to external APIs.

**Start Command:**
```powershell
C:\Users\saisu\AppData\Local\Programs\Ollama\ollama.exe serve
```

**Verification:**
```powershell
curl http://localhost:11434/api/tags
```

**Output (11 models available):**
```
gemma3:latest          4.3B  Q4_K_M  ← Primary model used
qwen2.5:14b            14.8B Q4_K_M
qwen2.5:7b-instruct    7.6B  Q4_K_M
phi3:mini              3.8B  Q4_0
smollm2:135m           135M  F16
qwen3-vl:latest        8.8B  Q4_K_M
glm-4.7-flash:latest   29.9B Q4_K_M
llava:latest           7B    Q4_0
DeepSeek-OCR:latest    3.3B  F16
...plus cloud models
```

**GPU Acceleration (CUDA):**
```
GPU: NVIDIA GeForce RTX 4060 Laptop GPU (8.0 GB VRAM)
Compute Capability: 8.9
Model offloaded: 35/35 layers to GPU
Inference: Running on CUDA v12
```

---

### 2. Gemma 3 — LLM Model

**Purpose:** The AI brain that generates Security+ explanations, quiz questions, and answers.

**Used by:**
- `InstructorAgent.explain_topic()` — Generates adaptive study lessons
- `InstructorAgent.explain_question_result()` — Explains quiz answers
- `AssessmentEngine.generate_ai_quiz()` — Creates practice questions
- `/api/chat` — Interactive chat with AI tutor

**Configuration** (in `quantum_surge/instructor.py` and `quantum_surge/assessment_engine.py`):
```python
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma3:latest"
```

**Two Teaching Modes:**
| Mode | Style |
|------|-------|
| `military_analogy` | Military commander → Army battle operations, FOB security |
| `technical_breakdown` | Systems architect → Protocol specs, RFC references |

---

### 3. ChromaDB — Vector Database (RAG)

**Purpose:** Stores CompTIA Security+ SY0-701 exam objectives as vector embeddings for Retrieval-Augmented Generation (RAG).

**Database Location:** `./chroma_db/chroma.sqlite3`

**Collection:** `security_plus_objectives`

**Data Seeded (28 topics covering 5 domains):**
| Domain | Topics |
|--------|--------|
| 1.0 General Security Concepts | Security controls, CIA triad, Change management, Cryptography |
| 2.0 Threats & Mitigations | Threat actors, Vectors, Vulnerabilities, Malicious indicators |
| 3.0 Security Architecture | Architecture models, Infrastructure, Data protection, Resilience |
| 4.0 Security Operations | Computing resources, Asset mgmt, Vulnerability mgmt, SIEM, IAM |
| 5.0 Program Management | Governance, Risk management, Third-party, Compliance, Audits |

**How it's used** (`rag_service.py`):
```python
results = self.collection.query(query_texts=[topic_id], n_results=1)
# Returns relevant SY0-701 objective text → fed into LLM prompt
```

---

### 4. DuckDuckGo Search — Live Threat Intel

**Purpose:** Fetches recent real-world cybersecurity news related to the topic being studied.

**Implementation** (`search_service.py`):
```python
def search_recent_threats(topic_name: str) -> str:
    query = f"recent {topic_name} cybersecurity attack news"
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
```

**Example:** When studying "Threat Vectors" → searches for "recent threat vectors cybersecurity attack news"

---

### 5. Flask — Web Application Server

**Purpose:** Serves the web UI and REST API endpoints.

**Start Command:**
```powershell
cd C:\Users\saisu\Downloads\QuantumSurgeCode
python server.py
```

**Served on:** `http://127.0.0.1:5000`

**File Structure:**
```
QuantumSurgeCode/
├── server.py                    # Flask app & API routes
├── templates/index.html         # Dashboard UI
├── static/app.js                # Frontend logic
├── static/style.css             # Styling
├── quantum_surge/
│   ├── __init__.py
│   ├── models.py                # Data models
│   ├── knowledge_base.py        # SY0-701 curriculum
│   ├── instructor.py            # AI lesson generator
│   ├── assessment_engine.py     # Quiz generator & grader
│   ├── rag_service.py           # ChromaDB vector search
│   └── search_service.py        # DuckDuckGo threat intel
```

---

### 6. Cloudflare Tunnel — Public Exposure

**Purpose:** Creates a publicly accessible HTTPS URL that forwards traffic to your local Flask server — no port forwarding needed.

**Start Command:**
```powershell
cloudflared.exe tunnel --url http://localhost:5000 --protocol http2
```

**Connection Flow:**
```
User → https://xxxx.trycloudflare.com → Cloudflare Edge → cloudflared.exe → localhost:5000
```

**Connectivity Pre-checks (all PASS):**
| Check | Status |
|-------|--------|
| DNS Resolution (region1) | ✅ PASS |
| DNS Resolution (region2) | ✅ PASS |
| UDP Connectivity (region1) | ✅ PASS (QUIC) |
| UDP Connectivity (region2) | ✅ PASS (QUIC) |
| TCP Connectivity (region1) | ✅ PASS (HTTP/2) |
| TCP Connectivity (region2) | ✅ PASS (HTTP/2) |
| Cloudflare API reachability | ✅ PASS |

**Tunnel Endpoint:** `iad05` (Ashburn, VA datacenter)

---

### 7. Watchdog — Auto-Recovery

**Purpose:** PowerShell script that monitors all 3 services and auto-restarts any that crash.

**File:** `watchdog.ps1`

**Logic:**
```
Loop every 15 seconds:
  1. Check if Ollama process is running → If not, restart it
  2. Check if Flask responds on port 5000 → If not, restart via waitress
  3. Check if cloudflared is running → If not, restart & get new URL
```

---

## How to Start Everything

### Method 1: One-Command Watchdog (Recommended)
```powershell
powershell -File "C:\Users\saisu\Downloads\QuantumSurgeCode\watchdog.ps1"
```

### Method 2: Manual Start (3 Terminals)
```powershell
# Terminal 1: Ollama
C:\Users\saisu\AppData\Local\Programs\Ollama\ollama.exe serve

# Terminal 2: Flask
cd C:\Users\saisu\Downloads\QuantumSurgeCode && python server.py

# Terminal 3: Cloudflare Tunnel
cd C:\Users\saisu\Downloads\QuantumSurgeCode && cloudflared.exe tunnel --url http://localhost:5000
```

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Dashboard UI (index.html) |
| GET | `/api/progress` | User progress, mastery %, weak areas |
| GET | `/api/study/<topic_id>` | AI-generated study lesson for a topic |
| GET | `/api/quiz/<topic_id>` | AI-generated quiz questions |
| POST | `/api/quiz/grade` | Submit & grade quiz answers |
| POST | `/api/assess` | Update confidence rating for a topic |
| POST | `/api/instructor/mode` | Switch between teaching styles |
| POST | `/api/chat` | Interactive AI tutor chat |
| POST | `/api/rewrite` | Simplify ("dumb down") technical text |

---

## Current Live URL

**🔗 https://ambassador-makeup-designation-pie.trycloudflare.com**

*Note: This URL changes each time cloudflared restarts. Check `cloudflared.log` for the current URL.*
