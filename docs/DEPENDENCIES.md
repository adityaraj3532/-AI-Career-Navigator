# Approved Dependencies

This document records all approved Python and runtime dependencies. No new dependency may be introduced to the project without prior discussion, rationale review, and explicit approval.

**Base Runtime**: Python 3.11+ (Active local runtime: Python 3.12.2)

---

## 1. Core Framework & Web
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `fastapi` | `==0.115.0` | Core high-performance async REST API framework. |
| `uvicorn[standard]` | `==0.32.0` | Production-grade ASGI server with uvloop/httptools support. |
| `pydantic` | `==2.9.2` | Data validation and JSON schema enforcement for APIs and LLM payloads. |
| `pydantic-settings` | `==2.6.0` | Environment variable management and validation using Pydantic V2 models. |

## 2. Database & Migrations (asyncpg only)
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `sqlalchemy` | `==2.0.36` | Industry-standard async ORM and query abstraction layer. |
| `asyncpg` | `==0.30.0` | High-performance asynchronous PostgreSQL database driver for both runtime API and Alembic migrations. |
| `alembic` | `==1.13.3` | Deterministic database schema migration engine configured with native async runner (`run_async_migrations`). |

## 3. Caching, Queue & Background Processing
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `redis` | `==5.2.0` | High-performance Redis client for caching, tokens, and rate-limiting. |
| `arq` | `==0.26.1` | Native asyncio job queue built on Redis; robust, fast, and Windows-compatible. |

## 4. Testing & Code Quality
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `pytest` | `==8.3.3` | Testing framework for unit and integration test suites. |
| `pytest-asyncio` | `==0.24.0` | Asyncio test runner support for async FastAPI endpoints and repositories. |
| `httpx` | `==0.27.2` | Async HTTP client for end-to-end API route testing via FastAPI TestClient. |
| `ruff` | `==0.7.1` | High-speed Python linter for automated CI pipelines. |

## 5. Upcoming Phase Dependencies (Locked for Phase 2 & LLM Gateway)
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `python-jose[cryptography]` | `==3.3.0` | Cryptographic JWT creation, signing, claims validation, and parsing. |
| `passlib[bcrypt]` | `==1.7.4` | Secure password hashing algorithm (bcrypt) and verification. |
| `python-multipart` | `==0.0.12` | Form data parsing for login endpoints. |
| `google-genai` | `==0.1.1` | Official Google GenAI SDK for Gemini models with structured JSON support. |
