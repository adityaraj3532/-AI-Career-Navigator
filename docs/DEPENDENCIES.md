# Approved Dependencies

This document records all approved Python and runtime dependencies. No new dependency may be introduced to the project without prior discussion, rationale review, and explicit approval.

**Base Runtime**: Python 3.11+

---

## 1. Core Framework & Web
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `fastapi` | `~=0.115.0` | Core high-performance async REST API framework. |
| `uvicorn[standard]` | `~=0.32.0` | Production-grade ASGI server with uvloop/httptools support. |
| `pydantic` | `~=2.9.2` | Data validation and JSON schema enforcement for APIs and LLM payloads. |
| `pydantic-settings` | `~=2.6.0` | Environment variable management and validation using Pydantic V2 models. |

## 2. Database & Migrations
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `sqlalchemy` | `~=2.0.36` | Industry-standard async ORM and query abstraction layer. |
| `asyncpg` | `~=0.30.0` | High-performance asynchronous PostgreSQL database driver for runtime API. |
| `psycopg2-binary` | `~=2.9.10` | Synchronous PostgreSQL driver used by Alembic for schema migrations. |
| `alembic` | `~=1.13.3` | Deterministic, version-controlled database schema migration engine. |

## 3. Caching, Queue & Background Processing
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `redis` | `~=5.2.0` | High-performance Redis client for caching, tokens, and rate-limiting. |
| `arq` | `~=0.26.1` | Native asyncio job queue built on Redis; robust, fast, and Windows-compatible. |

## 4. Security & Authentication
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `python-jose[cryptography]` | `~=3.3.0` | Cryptographic JWT creation, signing, claims validation, and parsing. |
| `passlib[bcrypt]` | `~=1.7.4` | Secure password hashing algorithm (bcrypt) and verification. |
| `python-multipart` | `~=0.0.12` | Form data and OAuth2 password flow parsing for login endpoints. |

## 5. AI & LLM Gateway
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `google-genai` | `~=0.1.1` | Official Google GenAI SDK for Gemini models with structured JSON support. |

## 6. Testing & Quality Assurance
| Dependency | Version Pin | Architectural Rationale |
| :--- | :--- | :--- |
| `pytest` | `~=8.3.3` | Testing framework for unit and integration test suites. |
| `pytest-asyncio` | `~=0.24.0` | Asyncio test runner support for async FastAPI endpoints and repositories. |
| `httpx` | `~=0.27.2` | Async HTTP client for end-to-end API route testing via FastAPI TestClient. |
