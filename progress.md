# PulseGuard Progress Tracker

Welcome! This document tracks our progress as we build **PulseGuard**, an AI-Powered API Monitoring & Incident Analysis Platform. We will build this step-by-step, explaining every package and architectural decision as we go.

---

## 🚦 Overall Roadmap

- [x] **Phase 1 — Foundation**
  - FastAPI project setup, PostgreSQL connection, SQLAlchemy models, Docker basics, JWT authentication.
- [x] **Phase 2 — Core Monitoring System**
  - Celery workers, Redis setup, background jobs, automatic endpoint monitoring.
- [x] **Phase 3 — Alert System**
  - Failure detection, retry strategies, email/webhook alerts.
- [ ] **Phase 4 — Performance & Scalability** 👈 *Next Step*
  - Redis caching, rate limiting, database indexing.
- [ ] **Phase 5 — AI Incident Analysis**
  - OpenAI API integration, log analysis, root-cause summaries.
- [ ] **Phase 6 — Real-Time Dashboard**
  - Next.js frontend, WebSockets, live status updates.
- [ ] **Phase 7 — Production Engineering**
  - Structured logging, testing with pytest, CI/CD.
- [ ] **Phase 8 — Deployment & Observability**
  - Docker Compose, Prometheus, Grafana, Nginx.

---

## 📝 Phase-by-Phase Progress & Learning Log

### Phase 1 — Foundation
*Status: Complete*

- [x] Setup virtual environment and project structure (Created `.venv` and `app/main.py`)
- [x] Install FastAPI and explain its core features (Installed `fastapi` and `uvicorn`)
- [x] Connect to PostgreSQL with SQLAlchemy (explain ORM vs. Raw SQL) (Configured engine and session maker for PostgreSQL connection)
- [x] Create database models (User, Project, Endpoint) (Created SQLAlchemy models under `app/models/`)
- [x] Implement JWT authentication (explain password hashing and tokens) (Implemented secure password hashing via bcrypt, JWT token generation/verification, and route-level dependencies)

---

### Phase 2 — Core Monitoring System
*Status: Complete*

- [x] Install Celery, Redis, and HTTPX dependencies (explained in requirements.txt and below).
- [x] Create database models for monitoring logs (Created `MonitoringResult` model to store status codes, response time/latency, error messages, and timestamps).
- [x] Set up Redis connection & Celery worker configuration (Created `app/core/celery_app.py` utilizing dynamic Redis connections and configuring automatic Beat scheduling).
- [x] Implement periodic checks and pings (Created `app/core/tasks.py` with `scheduler_task` querying due endpoints every 10 seconds and spawning `ping_endpoint_task` asynchronously to execute pings via `httpx`).

#### Key Concept Explanations:
1. **Celery**: An asynchronous task queue based on distributed message passing. We use it to perform web requests (pings) outside of the main FastAPI thread, preventing the web server from blocking or slowing down during heavy traffic or slow external responses.
2. **Redis**: Used as a broker (transporting messages from our app to the Celery workers) and backend (holding task statuses/results).
3. **HTTPX**: A next-generation HTTP client for Python, supporting standard synchronous and asynchronous requests. We use it to measure request latencies and check HTTP status codes.
4. **Timezone Compatibility**: Used UTC standard time (`datetime.timezone.utc`) for all DB records and check comparisons to avoid timezone synchronization bugs.

---

### Phase 3 — Alert System
*Status: Complete*

- [x] Modify Project and Endpoint models (Added `webhook_url` to Projects; added `status` and `consecutive_failures` to Endpoints).
- [x] Configure SMTP environment variables (Added SMTP host, port, user, password, and from email configurations to config class and env files).
- [x] Implement notification dispatch engine (Created `app/core/notifications.py` supporting email notifications via SMTP with standard stdout console logging backup, alongside webhook HTTP POST alerts).
- [x] Configure worker task retry strategy (Modified `ping_endpoint_task` in `app/core/tasks.py` to catch network failures and bad status codes, retry up to 3 times, and trigger transitions).
- [x] Track endpoint states (Updates endpoint `status` to `"failing"` and alerts the user upon 3 consecutive check failures. Automatically resets to `"healthy"` and sends a recovery alert upon success).

#### Key Concept Explanations:
1. **Celery Retries (`self.retry`)**: Allows worker tasks to retry execution when they encounter recoverable exceptions (e.g. transient DNS glitches, timeouts). We use it to ensure we don't alert users on simple temporary blips.
2. **State Transition Alerts**: Alerts are only dispatched when the status actually changes (e.g. healthy $\rightarrow$ failing or failing $\rightarrow$ healthy). This avoids spamming notifications on every subsequent fail/success run.
3. **Webhooks**: HTTP POST callbacks that allow PulseGuard to integrate with external systems (like Slack, Discord, or custom servers) when incidents happen.
