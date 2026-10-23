# Approved Dependencies

This document records all approved Python and runtime dependencies. No new dependency may be introduced to the project without prior discussion, rationale review, and explicit approval.

**Base Runtime**: Python 3.11+ (Active local runtime: Python 3.12.2)

---

## 1. Core Framework & Web
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `fastapi` | `==0.115.0` | Core high-performance async REST API framework. |
| `uvicorn[standard]` | `==0.32.0` | Production-grade ASGI server with uvloop/httptools support. |
| `pydantic` | `==2.14.1` | Data validation and JSON schema enforcement for APIs and LLM payloads. |
| `pydantic-settings` | `==2.6.0` | Environment variable management and validation using Pydantic V2 models. |
| `python-multipart` | `==0.0.32` | Form data and multipart parsing for authentication (released 2026-06-04; >14 days stable). |

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

## 4. Security & Authentication
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `PyJWT` | `==2.15.1` | RFC 7519 compliant JWT library for signing and validating access tokens with algorithm pinning (released 2026-09-28; >14 days stable). Replaced python-jose. |
| `bcrypt` | `==5.0.0` | Modern, standalone bcrypt password hashing engine without legacy passlib wrappers (released 2025-09-25; >14 days stable). |

## 5. Artificial Intelligence & LLM Gateway
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `google-genai` | `==2.29.0` | Official Google GenAI SDK for Gemini models with structured JSON schema support (released 2026-10-07; >14 days stable). |

## 6. Testing & Code Quality
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `pytest` | `==8.3.3` | Testing framework for unit and integration test suites. |
| `pytest-asyncio` | `==0.24.0` | Asyncio test runner support for async FastAPI endpoints and repositories. |
| `httpx` | `==0.28.1` | Async HTTP client for end-to-end API route testing via FastAPI TestClient and provider calls. |
| `ruff` | `==0.7.1` | High-speed Python linter for automated CI pipelines. |
