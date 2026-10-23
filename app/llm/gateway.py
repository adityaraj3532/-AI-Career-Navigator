import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.llm.prompt_manager import PromptManager
from app.llm.provider import BaseLLMProvider, GeminiProvider
from app.llm.telemetry import TelemetryEvent, log_telemetry

logger = logging.getLogger("app.llm.gateway")
T = TypeVar("T", bound=BaseModel)


class GatewayResponse(Generic[T]):
    """Response wrapper providing both the validated data and audit telemetry."""

    def __init__(self, data: T, telemetry: TelemetryEvent) -> None:
        self.data = data
        self.telemetry = telemetry


class PostValidationError(Exception):
    """Raised when an output fails post-validation rules (e.g. unverified DB IDs)."""
    pass


class LLMGateway:
    """Central gateway governing all AI invocations.
    
    Enforces:
    - Provider abstraction (Gemini / Mock)
    - 15s per-call timeout, 20s overall time budget
    - Pydantic schema validation
    - Exactly one retry on validation failure only
    - Post-validation callback (e.g. database entity ID verification)
    - Deterministic fallback on failures or timeout
    - Structured telemetry without PII or raw prompt leakage
    """

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        prompt_manager: Optional[PromptManager] = None,
        per_call_timeout: float = 15.0,
        overall_timeout: float = 20.0,
    ) -> None:
        self.provider = provider or GeminiProvider()
        self.prompt_manager = prompt_manager or PromptManager()
        self.per_call_timeout = per_call_timeout
        self.overall_timeout = overall_timeout
        self.last_telemetry: Optional[TelemetryEvent] = None
        settings = get_settings()
        self.model_name = getattr(self.provider, "model_name", settings.GEMINI_MODEL)

    # Known untrusted input variable names that must be treated as untrusted even if
    # passed in legacy `inputs` dictionary
    KNOWN_UNTRUSTED_KEYS = {
        "candidate_answer",
        "user_query",
        "question",
        "user_facts",
        "primary_goal",
        "prior_experience",
        "target_role",
        "user_profile_bio",
        "notes",
        "message",
        "query",
        "feedback",
    }

    async def execute_prompt(
        self,
        prompt_name: str,
        prompt_version: int,
        schema: Type[T],
        fallback_factory: Callable[[], T],
        system_variables: Optional[Dict[str, Any]] = None,
        user_inputs: Optional[Dict[str, str]] = None,
        untrusted_inputs: Optional[Dict[str, Any]] = None,
        post_validator: Optional[Callable[[T], bool]] = None,
    ) -> GatewayResponse[T]:
        start_time = time.monotonic()
        attempts = 0
        error_type: Optional[str] = None

        merged_untrusted = {}
        if user_inputs:
            merged_untrusted.update(user_inputs)
        if untrusted_inputs:
            merged_untrusted.update(untrusted_inputs)

        rendered_prompt = self.prompt_manager.render(
            name=prompt_name,
            version=prompt_version,
            system_variables=system_variables,
            untrusted_inputs=merged_untrusted,
        )

        async def _call_provider_with_budget() -> str:
            elapsed = time.monotonic() - start_time
            remaining_overall = self.overall_timeout - elapsed
            if remaining_overall <= 0:
                raise asyncio.TimeoutError("Overall time budget of 20s exceeded.")
            call_timeout = min(self.per_call_timeout, remaining_overall)
            return await asyncio.wait_for(
                self.provider.generate(
                    prompt=rendered_prompt,
                    schema=schema,
                    timeout=call_timeout,
                ),
                timeout=call_timeout,
            )

        # Attempt 1
        try:
            attempts += 1
            raw_response = await _call_provider_with_budget()
            parsed_data = self._validate_payload(raw_response, schema)

            # Post-validation check (e.g. DB ID verification)
            if post_validator is not None and not post_validator(parsed_data):
                raise PostValidationError("Post-validation failed: referenced IDs not found in database.")

            latency_ms = (time.monotonic() - start_time) * 1000
            in_tokens = max(1, len(rendered_prompt) // 4)
            out_tokens = max(1, len(raw_response) // 4)
            cost_usd = (in_tokens * 0.0000001) + (out_tokens * 0.0000004)

            telemetry = TelemetryEvent(
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                model_name=self.model_name,
                latency_ms=latency_ms,
                status="success",
                fallback_used=False,
                attempts=attempts,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                estimated_cost_usd=cost_usd,
            )
            self.last_telemetry = telemetry
            log_telemetry(telemetry)
            self._record_telemetry_metrics(in_tokens, out_tokens)
            return GatewayResponse(data=parsed_data, telemetry=telemetry)

        except (ValidationError, json.JSONDecodeError) as val_err:
            error_type = type(val_err).__name__
            logger.warning(
                "AI schema validation failed on attempt 1 (%s). Retrying once...",
                error_type,
            )

            # Retry attempt 2 (only on validation failure)
            try:
                attempts += 1
                raw_retry = await _call_provider_with_budget()
                parsed_data = self._validate_payload(raw_retry, schema)

                if post_validator is not None and not post_validator(parsed_data):
                    raise PostValidationError("Post-validation failed on retry: referenced IDs not found.")

                latency_ms = (time.monotonic() - start_time) * 1000
                telemetry = TelemetryEvent(
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    model_name=self.model_name,
                    latency_ms=latency_ms,
                    status="retry_success",
                    fallback_used=False,
                    attempts=attempts,
                )
                self.last_telemetry = telemetry
                log_telemetry(telemetry)
                return GatewayResponse(data=parsed_data, telemetry=telemetry)

            except Exception as retry_err:
                error_type = type(retry_err).__name__
                logger.warning(
                    "AI schema retry failed (%s). Activating deterministic fallback.",
                    error_type,
                )

        except Exception as first_attempt_err:
            error_type = type(first_attempt_err).__name__
            logger.warning(
                "AI generation failed without retry eligibility (%s). Activating deterministic fallback.",
                error_type,
            )

        # Fallback Activation
        fallback_data = fallback_factory()
        latency_ms = (time.monotonic() - start_time) * 1000
        telemetry = TelemetryEvent(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            model_name=self.model_name,
            latency_ms=latency_ms,
            status="fallback",
            fallback_used=True,
            attempts=attempts,
            error_type=error_type,
        )
        self.last_telemetry = telemetry
        log_telemetry(telemetry)
        return GatewayResponse(data=fallback_data, telemetry=telemetry)

    def _validate_payload(self, raw_text: str, schema: Type[T]) -> T:
        """Parses JSON text and validates against the target Pydantic schema."""
        raw_text = raw_text.strip()
        # Strip potential markdown code fence markers if model wrapped JSON
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        # Parse JSON
        parsed_json = json.loads(raw_text)
        return schema.model_validate(parsed_json)

    async def generate(
        self,
        prompt_name: str,
        inputs: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Type[T]] = None,
        fallback: Optional[T] = None,
        version: int = 1,
        post_validator: Optional[Callable[[T], bool]] = None,
        system_variables: Optional[Dict[str, Any]] = None,
        untrusted_inputs: Optional[Dict[str, Any]] = None,
    ) -> GatewayResponse[T]:
        """Convenience method to execute a prompt template by name and schema with fallback."""
        sys_vars: Dict[str, Any] = dict(system_variables or {})
        untrusted: Dict[str, Any] = dict(untrusted_inputs or {})

        if inputs:
            for k, v in inputs.items():
                if k in self.KNOWN_UNTRUSTED_KEYS:
                    if k not in untrusted:
                        untrusted[k] = v
                else:
                    if k not in sys_vars:
                        sys_vars[k] = v

        return await self.execute_prompt(
            prompt_name=prompt_name,
            prompt_version=version,
            schema=output_schema,
            fallback_factory=lambda: fallback,
            system_variables=sys_vars,
            untrusted_inputs=untrusted,
            post_validator=post_validator,
        )

    def _record_telemetry_metrics(self, in_tokens: int, out_tokens: int) -> None:
        import os
        settings = get_settings()
        if "PYTEST_CURRENT_TEST" in os.environ or settings.ENVIRONMENT.lower() in ("test", "testing"):
            return
        try:
            from app.core.redis import get_redis_client
            redis = get_redis_client()
            async def _bg() -> None:
                try:
                    await redis.incrby("llm:tokens:prompt", in_tokens)
                    await redis.incrby("llm:tokens:completion", out_tokens)
                except Exception:
                    pass
            loop = asyncio.get_running_loop()
            if loop.is_running():
                task = loop.create_task(_bg())
                task.add_done_callback(lambda _: None)
        except Exception:
            pass


_shared_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    """Dependency injection factory for LLMGateway singleton."""
    global _shared_gateway
    if _shared_gateway is None:
        _shared_gateway = LLMGateway()
    return _shared_gateway


def set_llm_gateway(gw: Optional[LLMGateway]) -> None:
    """Overrides the shared LLMGateway instance (e.g. for testing with MockLLMProvider)."""
    global _shared_gateway
    _shared_gateway = gw


def reset_llm_gateway() -> None:
    """Resets the shared gateway instance."""
    global _shared_gateway
    _shared_gateway = None


def is_gateway_configured() -> bool:
    """Validates that the LLM gateway is configured for the active environment.
    Fails in non-test environments if API key is missing.
    """
    settings = get_settings()
    env = settings.ENVIRONMENT.lower()
    if env in ("test", "testing"):
        return True
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
