# AI Career Navigator – Project Handover & State Ledger

This document tracks the ongoing operational state of the codebase across engineering sessions. Every session logs its latest status on top with the model name and date.

---

## Session: 2026-10-23 (Gemini 3.8 Flash (Medium)) – LLM Gateway Step 1

### Done
- Implemented `BaseLLMProvider`, `GeminiProvider` (using official `google-genai==2.29.0`), and `MockLLMProvider` in `app/llm/provider.py`.
- Verified and pinned `google-genai==2.29.0` (released 2026-10-07, >14 days stable on PyPI) with `pydantic==2.14.1` and `httpx==0.28.1`. Logged in `docs/DEPENDENCIES.md`.
- Implemented `PromptManager` in `app/llm/prompt_manager.py` with versioned file template loading from `app/llm/prompts/` (e.g. `career_explainer_v1.txt`).
- Implemented strict prompt injection defense (`PromptInjectionDefense`), neutralizing delimiter breakouts and wrapping all untrusted user text inside `<user_input name="...">...</user_input>`.
- Implemented `LLMGateway` in `app/llm/gateway.py` with:
  - 15-second per-call timeout.
  - 20-second overall time budget for entire operation.
  - Pydantic schema validation.
  - Exactly one retry on validation failure only (no retries on timeout or network exceptions).
  - Optional `post_validator` callback rejecting outputs with hallucinated/unverified database IDs.
  - Guaranteed deterministic fallback via `fallback_factory`.
- Implemented zero-PII telemetry in `app/llm/telemetry.py` recording `prompt_name`, `version`, `model`, `status`, `fallback_used`, `latency_ms`, and `attempts` with strict exclusion of prompt text and user inputs.
- Authored comprehensive test suite in `tests/test_llm_gateway.py` (invalid JSON retry/fallback, timeout fallback, unknown-ID rejection, prompt injection defense, zero user text in telemetry, and optional live Gemini smoke test). Real test run: 13 passed, 1 skipped (live key).
- Documented gateway fallback resilience in `docs/DECISIONS.md` (ADR-007).

### In progress
- LLM Gateway Step 1 complete. Awaiting review before Step 2.

### Broken or risky
- Live Gemini API calls require setting `GEMINI_API_KEY` in environment; CI and local tests safely mock provider execution.

### Next (LLM Gateway Step 2 upon approval)
- Implement Redis-based per-user sliding window and global rate limiting.
- Implement token usage and estimated cost tracking in telemetry.
- Implement streaming for chat endpoints (`StreamingResponse` / SSE).
- Implement fail-closed fallback execution when Redis is unreachable.

### Do not touch
- `docs/CONSTRAINTS.md`: All security and product constraints are locked.
- Prompt injection delimitation boundary (`<user_input>...</user_input>`).
- Zero PII / raw text logging policy in `app/llm/telemetry.py`.
