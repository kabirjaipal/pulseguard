# PulseGuard 🛡️ — AI-Powered API Monitoring & Incident Analysis Platform

PulseGuard is an API monitoring platform that continuously checks the health of target APIs, triggers alerts when they go offline, and uses AI to diagnose why they failed.

It features a real-time Next.js dashboard that receives instant status updates via WebSockets when API health changes.

---

## 🏗️ How it Works

1. **Next.js Frontend**: Displays live API status, latency charts, and AI incident logs.
2. **FastAPI Backend**: Handles user authentication, configuration, and WebSocket streams.
3. **Celery Worker & Redis**: Runs API health checks in the background to keep the app fast.
4. **AI Diagnostics**: Queries LLMs to analyze logs and suggest troubleshooting steps.
5. **Nginx Proxy**: Routes frontend and backend traffic through a single port.
6. **Prometheus & Grafana**: Tracks API requests and response latencies.

---

## ⚡ Key Features

*   **Background Checks**: Offloads API checks to background workers (Celery + Redis) so the web server stays fast.
*   **Smart Alerts**: Sends emails and webhooks only when an API's status changes (e.g., goes offline or recovers) to avoid alert spam.
*   **AI Diagnostics**: Automatically generates root-cause analyses and suggestions using AI when an API fails.
*   **Fast Caching**: Caches the latest API check results in Redis for instant dashboard loads.
*   **API Protection**: Protects sign-up, login, and check routes with a custom Redis rate limiter.
*   **Real-time Streaming**: Streams live API updates directly to the browser client via WebSockets.

---

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI, SQLAlchemy ORM, PostgreSQL, Redis, Celery, HTTPX, Groq SDK
*   **Frontend**: Next.js (App Router), React, Tailwind CSS, WebSockets
*   **DevOps**: Docker, Nginx, Prometheus, Grafana
*   **Testing**: Pytest

---

## 🚀 How to Run

### Option A: With Docker (Recommended)
1. Clone the repository and run:
   ```bash
   docker compose up --build
   ```
2. Access the services:
   *   **Frontend UI**: `http://localhost`
   *   **Backend API Docs**: `http://localhost/api/docs`
   *   **Grafana Dashboard**: `http://localhost:3001` (Login: `admin` / `admin`)

---

### Option B: Local Setup (Without Docker)

#### 1. Backend Setup
```bash
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```
In separate terminals (with `.venv` active), run the background workers:
```bash
# Start Celery Worker
celery -A app.core.tasks.celery_app worker --loglevel=info

# Start Celery Beat
celery -A app.core.tasks.celery_app beat --loglevel=info
```

#### 2. Frontend Setup
```bash
cd client
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Running Tests
To run backend automated tests:
```bash
cd server
PYTHONPATH=. pytest
```