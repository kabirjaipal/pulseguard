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
- [x] **Phase 4 — Performance & Scalability**
  - Redis caching, rate limiting, database indexing.
- [x] **Phase 5 — AI Incident Analysis**
  - Groq API integration, log analysis, root-cause summaries.
- [x] **Phase 6 — Real-Time Dashboard**
  - Next.js frontend, WebSockets, live status updates.
- [x] **Phase 7 — Production Engineering**
  - Structured logging, testing with pytest, CI/CD.
- [ ] **Phase 8 — Deployment & Observability** 👈 *Next Step*
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

---

### Phase 4 — Performance & Scalability
*Status: Complete*

- [x] Database Indexing (Added `index=True` to `Project.owner_id`, `Endpoint.project_id`, `MonitoringResult.endpoint_id`, and `MonitoringResult.checked_at` in the SQLAlchemy models to optimize index lookup performance for SQL joins and orders).
- [x] Redis Client Setup (Created `app/core/redis_client.py` setting up a unified connection pool using configuration parameters).
- [x] Result Caching (Configured background tasks to save the latest JSON-serialized check result of each endpoint into Redis, using an automatic expire TTL based on the check interval).
- [x] Latest Result Route (Created `GET /api/endpoints/{endpoint_id}/latest` retrieving the cached status instantly from Redis, falling back to DB query on cache miss).
- [x] Rate Limiting (Implemented a custom, highly performant Redis-backed Rate Limiter dependency using atomic operations. Applied to public routes `/signup` and `/login` [10 req/min/IP] and endpoints router [60 req/min/user]).

#### Key Concept Explanations:
1. **Database Indexing**: Creates lookup tables to speed up query execution. By indexing fields used in `WHERE` clauses (e.g. `owner_id`, `project_id`) and sorting (e.g. `checked_at`), we ensure queries complete in sub-millisecond ranges instead of scanning entire tables.
2. **Caching**: Storing computation results in an ultra-fast, in-memory store (Redis) to serve subsequent queries quickly. This avoids repetitive queries to the primary database, lowering load and increasing throughput.
3. **Atomic Rate Limiting**: Restricting client requests by tracking counts over time. By using Redis's atomic `INCR` command and setting a short-lived key per request bucket, we can implement high-performance protection against DDoS, brute-force, or api abuse without adding custom locks.

---

### Phase 5 — AI Incident Analysis
*Status: Complete*

- [x] Dependencies (Added `groq>=0.9.0` to track the official Groq Python SDK).
- [x] Database Model (Created `IncidentAnalysis` table to persist root-cause summary, troubleshooting suggestions, and raw serialized logs).
- [x] Configuration Settings (Added `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `AI_MODEL` support in `.env` and `app/core/config.py`).
- [x] AI Core Integration (Created `app/core/ai.py` communicating with OpenRouter's completions endpoint in JSON Mode. Includes a smart mock fallback module that tailors local diagnostics based on HTTP error status or network logs if no key is present).
- [x] Auto-Triggered Background Analysis (Modified Celery task in `tasks.py` to automatically fetch logs, generate AI analyses, write to DB, and embed the analysis in alert notifications when an endpoint fails).
- [x] Router & Schema Setup (Built Pydantic schemas in `schemas/incident_analysis.py` and router `routers/incidents.py` enabling endpoints to retrieve analyses and manually trigger them).

#### Key Concept Explanations:
1. **OpenRouter API**: A unified routing interface to access various LLMs (like Llama 3). We leverage it to get real-time diagnostic summaries of why our servers are failing in milliseconds.
2. **OpenRouter JSON Mode**: Setting the response format type to `json_object` forces the LLM to output valid JSON matching our requested keys. This eliminates flaky regex parser errors in standard text outputs.
3. **Mock AI Fallback**: Providing high-quality placeholder mock diagnostics in development environments so the platform remains fully functional and informative without incurring immediate API key setup costs.

---

### Phase 6 — Real-Time Dashboard
*Status: Complete*

- [x] CORS Setup & WebSockets Integration (Configured `CORSMiddleware` in FastAPI and created `websocket_manager.py` with custom user-targeted registration mapping).
- [x] Background Event Propagation (Modified Celery background tasks to publish pings and AI diagnosis updates to Redis Pub/Sub channel `pulseguard_updates`).
- [x] Async Pub/Sub broadcast thread (Integrated an async Redis Pub/Sub subscriber listener to FastAPI startup lifespan, broadcasting live events instantly to active client WebSockets).
- [x] Client Theme & Authentication (Configured a premium dark theme CSS system inside `globals.css` and built Context-based JWT authentication handler `AuthContext.tsx`).
- [x] Real-time Dashboard (`/dashboard`) (Designed statistics cards, interactive modal forms for Project/Endpoint CRUD operations, and reactive websocket event handling).
- [x] Detailed Monitor view (`/endpoints/[id]`) (Built custom responsive SVG area charts to display response latency trend, history logs list, and AI diagnostic report timeline).

---

### Phase 7 — Production Engineering
*Status: Complete*

- [x] Centralized exception handlers (Added global decorators in `app/main.py` for `SQLAlchemyError` and unhandled standard Python `Exception`, returning standardized, sanitized JSON responses to clients).
- [x] Migrate stdout prints to structured logging (Replaced generic console print statements in routers, core tasks, notification flows, and connection managers with structured Python logger calls utilizing JSONFormatter).
- [x] Expand Pytest suites (Added comprehensive unit tests covering projects, incident analysis manual generation, Redis caching hit/miss behavior, and exception handlers).
- [x] Rate Limiter testing bypass (Added automated bypass of rate limiting in `conftest.py` using Redis client mock patching to ensure test speed and reliability without hitting HTTP 429).

#### Key Concept Explanations:
1. **Centralized Error Interception**: Global exception handlers in FastAPI act as middlewares intercepting exceptions raised inside routes or DB operations. This prevents internal database stack traces or server paths from leaking in API responses, improving application security.
2. **Structured Logging**: Formatting log messages in JSON format so log collectors (like Elasticsearch or Loki) can index parameters (such as `timestamp`, `level`, `line`, `message`, and `logger`) as queryable fields rather than raw block text.
3. **Mocking External Engines (Redis/Celery)**: Mocking network/broker layers in tests allows testing isolated routes locally without needing real operational workers, dramatically speeding up verification runs.
