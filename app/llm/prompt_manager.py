import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class PromptInjectionDefense:
    """Sanitizes user input, clamps length, strips delimiter-looking tokens,
    and isolates untrusted data within <user_input> boundary XML blocks.
    """

    TAG_NAME = "user_input"
    DEFAULT_MAX_LENGTH = 2000
    DEFAULT_MAX_ITEM_LENGTH = 500

    # Delimiter-looking XML/HTML tags that an attacker might inject to breakout of XML blocks
    DELIMITER_TAG_PATTERN = re.compile(
        r"</?\s*(user_input|system|instruction|instructions|context|context_data|user_query|candidate_answer|user_fact|prompt|admin|assistant|user|rules|turn_start|turn_end)\b[^>]*>",
        re.IGNORECASE,
    )

    # LLM special control/chat tokens
    SPECIAL_TOKEN_PATTERNS = [
        re.compile(r"<\|im_start\|>", re.IGNORECASE),
        re.compile(r"<\|im_end\|>", re.IGNORECASE),
        re.compile(r"<\|endoftext\|>", re.IGNORECASE),
        re.compile(r"<\|system\|>", re.IGNORECASE),
        re.compile(r"<\|user\|>", re.IGNORECASE),
        re.compile(r"<\|assistant\|>", re.IGNORECASE),
        re.compile(r"\[INST\]", re.IGNORECASE),
        re.compile(r"\[/INST\]", re.IGNORECASE),
        re.compile(r"<<SYS>>", re.IGNORECASE),
        re.compile(r"<</SYS>>", re.IGNORECASE),
        re.compile(r"<s>", re.IGNORECASE),
        re.compile(r"</s>", re.IGNORECASE),
        re.compile(r"<turn_start>", re.IGNORECASE),
        re.compile(r"<turn_end>", re.IGNORECASE),
    ]

    # Common jailbreak and instruction-override bypass patterns
    INSTRUCTION_OVERRIDE_PATTERNS = [
        re.compile(r"(?i)\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|former)\s+(instructions|directives|rules|prompts|commands)\b"),
        re.compile(r"(?i)\b(system\s+override|admin\s+override|system\s+instruction|system\s+prompt|developer\s+mode|dan\s+mode)\b"),
        re.compile(r"(?i)\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(an?\s+)?(unrestricted|jailbroken|evil|unfiltered|dan|root|admin)\b"),
        re.compile(r"(?i)\b(output|print|display)\s+(the\s+)?(following\s+)?(exact\s+phrase|flag|secret|prompt|system\s+prompt)\b"),
    ]

    @classmethod
    def clamp_length(cls, text: str, max_length: int = DEFAULT_MAX_LENGTH) -> str:
        if not text:
            return ""
        if len(text) > max_length:
            return text[:max_length]
        return text

    @classmethod
    def strip_delimiters(cls, text: str) -> str:
        if not text:
            return ""
        sanitized = text

        # 1. Neutralize control/chat tokens
        for token_pat in cls.SPECIAL_TOKEN_PATTERNS:
            sanitized = token_pat.sub("[FILTERED_TOKEN]", sanitized)

        # 2. Neutralize XML delimiter tags
        sanitized = cls.DELIMITER_TAG_PATTERN.sub("[FILTERED_DELIMITER]", sanitized)

        # 3. Neutralize markdown code fences that attempt to break out
        sanitized = sanitized.replace("```", "'''")

        # 4. Neutralize common instruction override directives
        for override_pat in cls.INSTRUCTION_OVERRIDE_PATTERNS:
            sanitized = override_pat.sub("[FILTERED_OVERRIDE]", sanitized)

        return sanitized

    @classmethod
    def sanitize(cls, text: str, max_length: int = DEFAULT_MAX_LENGTH) -> str:
        if not text:
            return ""
        clamped = cls.clamp_length(text, max_length)
        return cls.strip_delimiters(clamped).strip()

    @classmethod
    def wrap_data(cls, key: str, data: Any, max_length: int = DEFAULT_MAX_LENGTH) -> str:
        if isinstance(data, list):
            sanitized_items: List[str] = []
            for item in data[:30]:  # Bound maximum list length
                clean_item = cls.sanitize(str(item), max_length=cls.DEFAULT_MAX_ITEM_LENGTH)
                sanitized_items.append(f"- {clean_item}")
            content = "\n".join(sanitized_items)
        elif isinstance(data, dict):
            clean_dict = {
                cls.sanitize(str(k), 100): cls.sanitize(str(v), 500)
                for k, v in list(data.items())[:30]
            }
            content = json.dumps(clean_dict, indent=2)
        else:
            content = cls.sanitize(str(data), max_length=max_length)

        return (
            f'<{cls.TAG_NAME} name="{key}">\n'
            f"{content}\n"
            f"</{cls.TAG_NAME}>"
        )


class PromptManager:
    """Loads and renders versioned prompt templates with prompt injection protection."""

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir = Path(prompts_dir)

    def _get_template_path(self, name: str, version: int) -> Path:
        if name.endswith(f"_v{version}"):
            filename = f"{name}.txt"
        else:
            filename = f"{name}_v{version}.txt"
        return self.prompts_dir / filename

    def load_template(self, name: str, version: int) -> str:
        path = self._get_template_path(name, version)
        if not path.is_file():
            raise FileNotFoundError(
                f"Prompt template '{name}' version {version} not found at {path}"
            )
        return path.read_text(encoding="utf-8")

    def render(
        self,
        name: str,
        version: int,
        system_variables: Optional[Dict[str, Any]] = None,
        user_inputs: Optional[Dict[str, Any]] = None,
        untrusted_inputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        template = self.load_template(name, version)
        rendered_vars: Dict[str, str] = {}

        if system_variables:
            for k, v in system_variables.items():
                if isinstance(v, (dict, list)):
                    rendered_vars[k] = json.dumps(v, indent=2)
                else:
                    rendered_vars[k] = str(v)

        # Merge untrusted user inputs
        all_untrusted: Dict[str, Any] = {}
        if user_inputs:
            all_untrusted.update(user_inputs)
        if untrusted_inputs:
            all_untrusted.update(untrusted_inputs)

        for k, v in all_untrusted.items():
            # Strictly isolate untrusted inputs inside designated XML block
            rendered_vars[k] = PromptInjectionDefense.wrap_data(k, v)

        # String template formatting that safely handles both {{var}} and {var}
        # without breaking on literal JSON braces { "foo": "bar" }
        rendered = template
        for k, v in rendered_vars.items():
            rendered = re.sub(rf"\{{\{{\s*{re.escape(k)}\s*\}}\}}", lambda m, val=v: val, rendered)
            rendered = re.sub(rf"\{{\s*{re.escape(k)}\s*\}}", lambda m, val=v: val, rendered)

        # Resolve simple legacy loops: {% for item in var %}...{% endfor %}
        def _replace_loop(match: re.Match) -> str:
            list_var = match.group(2)
            if list_var in rendered_vars:
                return rendered_vars[list_var]
            return match.group(0)

        loop_pattern = re.compile(
            r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}",
            re.DOTALL,
        )
        rendered = loop_pattern.sub(_replace_loop, rendered)

        return rendered
