import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("app.llm.telemetry")


class TelemetryEvent(BaseModel):
    """Structured telemetry metadata for AI calls.
    
    STRICT SECURITY RULE:
    Never include prompts, user text, emails, tokens, or credentials in telemetry events.
    """
    prompt_name: str = Field(..., description="Name of the prompt template used")
    prompt_version: int = Field(..., description="Version of the prompt template used")
    model_name: str = Field(..., description="LLM model identifier")
    latency_ms: float = Field(..., description="Total execution duration in milliseconds")
    status: str = Field(..., description="'success', 'retry_success', or 'fallback'")
    fallback_used: bool = Field(..., description="Whether the deterministic fallback was activated")
    attempts: int = Field(default=1, description="Number of generation attempts made")
    error_type: Optional[str] = Field(default=None, description="Class name of any caught error")
    input_tokens: int = Field(default=0, description="Estimated prompt input tokens")
    output_tokens: int = Field(default=0, description="Estimated completion output tokens")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated API invocation cost in USD")


_fallback_counter: dict[str, int] = {}
_success_counter: dict[str, int] = {}


def record_telemetry_event(event: TelemetryEvent) -> None:
    """Records event in in-memory counters per prompt/feature."""
    feature = event.prompt_name
    if event.fallback_used or event.status == "fallback":
        _fallback_counter[feature] = _fallback_counter.get(feature, 0) + 1
    else:
        _success_counter[feature] = _success_counter.get(feature, 0) + 1


def get_fallback_counts() -> dict[str, int]:
    """Returns a snapshot of fallback activations keyed by prompt/feature."""
    return dict(_fallback_counter)


def get_telemetry_summary() -> dict[str, Any]:
    """Returns a summary of successes and fallbacks across features."""
    return {
        "fallbacks": dict(_fallback_counter),
        "successes": dict(_success_counter),
    }


def reset_telemetry_counters() -> None:
    """Resets counters (useful for isolated tests)."""
    _fallback_counter.clear()
    _success_counter.clear()


def log_telemetry(event: TelemetryEvent) -> None:
    """Emits structured audit log for LLM invocations without PII or prompt text."""
    record_telemetry_event(event)
    logger.info(
        "AI_TELEMETRY prompt=%s_v%d model=%s status=%s fallback=%s latency_ms=%.2f attempts=%d in_tok=%d out_tok=%d cost=$%.6f error=%s fallbacks_for_feature=%d",
        event.prompt_name,
        event.prompt_version,
        event.model_name,
        event.status,
        event.fallback_used,
        event.latency_ms,
        event.attempts,
        event.input_tokens,
        event.output_tokens,
        event.estimated_cost_usd,
        event.error_type or "none",
        _fallback_counter.get(event.prompt_name, 0),
        extra={"ai_telemetry": event.model_dump(), "telemetry_summary": get_telemetry_summary()},
    )
