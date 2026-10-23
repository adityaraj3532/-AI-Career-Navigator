import logging
from typing import Optional
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


def log_telemetry(event: TelemetryEvent) -> None:
    """Emits structured audit log for LLM invocations without PII or prompt text."""
    logger.info(
        "AI_TELEMETRY prompt=%s_v%d model=%s status=%s fallback=%s latency_ms=%.2f attempts=%d in_tok=%d out_tok=%d cost=$%.6f error=%s",
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
        extra={"ai_telemetry": event.model_dump()},
    )
