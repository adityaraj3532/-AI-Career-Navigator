# Failure Modes, Resilience & Disaster Recovery (`FAILURE.md`)

This document provides a Failure Modes and Effects Analysis (**FMEA**) of the AI Career Navigator platform, detailing degradation paths, circuit-breaking boundaries, fallback behaviors, and disaster recovery procedures implemented in the codebase.

---

## 1. Failure Modes and Effects Analysis (FMEA) Matrix

| Component | Failure Mode | Root Cause | Detection Mechanism | Platform Mitigation / Fallback | User Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LLM Gateway** | Upstream 429 Quota Exhaustion | High concurrency or provider rate limits | `RateLimitError` caught in `LLMGateway` | Immediate degradation to feature deterministic fallback; **0 retries** | Seamless: user receives code-derived fallback response; telemetry increments fallback counter |
| **LLM Gateway** | Generation Timeout (>15.0s) | Model provider latency spike or hanging socket | Direct `asyncio.wait_for(..., timeout=call_timeout)` | Task cancelled immediately; yields to deterministic fallback model | Bounded latency: request completes within 15s instead of hanging indefinitely |
| **LLM Gateway** | Malformed JSON Output | Model omitted fields or generated invalid JSON | `OutputParsingError` / Pydantic `ValidationError` | **Exactly 1 retry** with schema correction; if second attempt fails, yields to fallback | Negligible: transparent single retry (<2s), graceful degradation on failure |
| **PostgreSQL** | Connection Pool Exhaustion / Partition | DB lockup, slow queries, or network split | `/ready` probe `asyncio.wait_for` (3.0s ceiling) | Probe returns `False`; orchestrator stops routing ingress traffic | Orchestrator routes around degraded nodes; user sees bounded 503 instead of hanging request |
| **Redis** | Redis Instance Crash / Unreachable | Redis process failure or node reboot | Redis ping timeout (2.0s ceiling) | Health check reports degraded; chat rate limiter fails open to in-memory sliding window cache | Chat continues operating using in-memory sliding window; background ARQ jobs pause until reconnect |
| **ARQ Workers** | Worker Job Exception / Crash | Task unhandled error or database lock | ARQ job exception handler | Job retry backoff; exception logged to telemetry; HTTP request thread unaffected | Background task delayed; user sees current database state until job completes |
| **Alembic** | Multi-Head Migration Divergence | Concurrent branch merges adding migrations | Automated test `alembic heads` check | CI pipeline fails immediately prior to deployment | Zero production impact: blocked at build pipeline |

---

## 2. Multi-Layer Deterministic Fallback Cascades

The core resilience principle of the platform is **Graceful Degradation to Deterministic Code**. User-facing operations never fail with raw 500 errors when external AI services degrade.

```mermaid
flowchart TD
    Req["AI Service Request"] --> GW["LLMGateway.generate()"]
    GW --> Budget{"Within 20s Overall Budget?"}
    Budget -->|No| Fallback["Activate Deterministic Fallback"]
    Budget -->|Yes| Provider["Call Provider with 15s Timeout"]
    
    Provider --> Res{"Provider Response"}
    Res -->|Timeout / RateLimit / Network Error| Fallback
    Res -->|Valid Output| SchemaCheck{"Pydantic Output Valid?"}
    
    SchemaCheck -->|Valid| Success["Return Valid Model (ai_status='ok')"]
    SchemaCheck -->|Invalid (Attempt 1)| Retry["Retry Once with Schema Correction"]
    Retry --> Res2{"Second Attempt"}
    Res2 -->|Valid| Success
    Res2 -->|Invalid| Fallback

    subgraph DeterministicFallbacks["Deterministic Fallback Engine"]
        Fallback --> F1["Mock Interview: Code-Calculated Keyword Scoring"]
        Fallback --> F2["Interview Follow-up: Return None (Skip gracefully)"]
        Fallback --> F3["Portfolio Pitch: Tech Stack Template Pitch"]
        Fallback --> F4["AI Chat: Canned Guidance (ai_status='fallback')"]
        Fallback --> F5["Weekly Summary Worker: Activity Ledger Markdown Breakdown"]
    end
```

### 2.1 Mock Interview Scoring Degradation
- **Failure Trigger**: Provider timeout, 429 rate limit, or network disconnection during answer evaluation.
- **Fallback Implementation (`app/services/interview_scoring.py` -> `fallback_score_answer`)**:
  - Computes coverage score based on answer character length and candidate keyword matches against rubric criteria.
  - Returns valid `DimensionScores` with string flag `confidence="low"`.
  - The interview session proceeds smoothly without aborting or losing candidate progress.

### 2.2 Mock Interview Follow-up Degradation
- **Failure Trigger**: LLM failure during dynamic follow-up question synthesis.
- **Fallback Implementation (`app/services/interview_service.py`)**:
  - Catches gateway exception and returns `None`.
  - The interview engine simply skips the dynamic follow-up question and moves to the next structured rubric question.

### 2.3 Personalized Portfolio Pitch Degradation
- **Failure Trigger**: Gateway timeout or parsing error during pitch synthesis.
- **Fallback Implementation (`app/services/portfolio_service.py`)**:
  - Deterministically constructs elevator pitch highlights directly from the student's custom project list, technologies, and target career cluster.

### 2.4 Contextual AI Chat Degradation
- **Failure Trigger**: Provider unavailability or rate limiting during `/v1/ai/chat`.
- **Fallback Implementation (`app/services/chat_service.py`)**:
  - Returns a structured `ChatAnswer` with `ai_status="fallback"`.
  - Provides deterministic advice and links to the user's active roadmap, curriculum milestones, and catalog resources.

### 2.5 Weekly Progress Summary Background Worker Degradation
- **Failure Trigger**: Model outage during scheduled weekly summary generation job.
- **Fallback Implementation (`app/workers/tasks.py`)**:
  - Constructs a clean Markdown summary derived directly from PostgreSQL queries:
    - Counts completed roadmap items during the week.
    - Reports current and longest activity streak numbers.
    - Summarizes verified skill badges earned.
    - Compares completed minutes against weekly goal targets.

---

## 3. Health Checking, Readiness Probes & Telemetry

### 3.1 Health vs. Readiness Probe Separation
- **`GET /health` (Liveness)**:
  - Lightweight process check returning `{"status": "ok"}`.
  - Does not execute network or database I/O.
  - Used by container orchestrators (Kubernetes/Docker) to detect deadlocked Python processes.
- **`GET /ready` (Readiness)**:
  - Probes live database and Redis connectivity before routing ingress HTTP traffic.
  - **Bounded Execution**:
    - `check_db_health()`: wrapped in `asyncio.wait_for(..., timeout=3.0)` executing `SELECT 1`.
    - `check_redis_health()`: wrapped in `asyncio.wait_for(client.ping(), timeout=2.0)`.
  - **Gateway Configuration Probe**: In non-test environments, `/ready` verifies that `LLMGateway` has a valid API key configured. If unconfigured, `/ready` returns HTTP 503.

### 3.2 Telemetry Fallback Counters & Operational Logging
- Implemented in `app/core/telemetry.py`:
  - Every time an AI feature yields to its deterministic fallback, `telemetry.increment_fallback(feature_name)` is triggered.
  - Fallback counts are summarized periodically in structured logs (`logger.info("Telemetry Fallback Summary: %s", summary)`).
  - Enables Prometheus/Datadog log scraping to detect upstream provider outages without generating false-positive 500 alert noise.
- **Zero-PII Logging Invariant**:
  - All log entries are scrubbed of candidate names, emails, raw prompt inputs, and auth tokens.

---

## 4. Disaster Recovery & Data Restoration Procedures

### 4.1 Database Restoration & Schema Head Verification
1. **Restore PostgreSQL Dump**:
   ```bash
   pg_restore --clean --if-exists -d career_navigator backup.dump
   ```
2. **Verify Alembic Head Uniqueness**:
   ```bash
   python -m alembic heads
   ```
   *Must report exactly one single head revision (e.g., `015_chat_conversations_and_messages`).*
3. **Execute Pending Migrations**:
   ```bash
   python -m alembic upgrade head
   ```

### 4.2 Automated Demo Account Restoration
If staging, demo, or testing databases need to be reset to a fully verified state:
```bash
python scripts/seed_demo_account.py --force-refresh
```
- Re-seeds all 4 milestone rules, prerequisite careers, and Holland RIASEC questions.
- Wipes and rebuilds the demo user (`demo@career-navigator.io`) with active 7-day streak, completed assessment, active roadmap, and public portfolio.
- Validates database referential integrity in under 5 seconds.
