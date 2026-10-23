import re
from pathlib import Path
from typing import Any, Dict, Optional


class PromptInjectionDefense:
    """Sanitizes user input and isolates it within XML-style boundary delimiters."""

    TAG_NAME = "user_input"

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return ""
        # Neutralize any attempts to close or re-open the delimiter tag
        sanitized = re.sub(
            rf"</?\s*{cls.TAG_NAME}(\s+[^>]*)?>",
            "[FILTERED_DELIMITER]",
            text,
            flags=re.IGNORECASE,
        )
        return sanitized.strip()

    @classmethod
    def wrap_data(cls, key: str, text: str) -> str:
        cleaned = cls.sanitize(text)
        return (
            f'<{cls.TAG_NAME} name="{key}">\n'
            f"{cleaned}\n"
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
        user_inputs: Optional[Dict[str, str]] = None,
    ) -> str:
        template = self.load_template(name, version)
        rendered_vars: Dict[str, str] = {}

        if system_variables:
            for k, v in system_variables.items():
                rendered_vars[k] = str(v)

        if user_inputs:
            for k, v in user_inputs.items():
                # Strictly isolate user inputs via PromptInjectionDefense
                rendered_vars[k] = PromptInjectionDefense.wrap_data(k, v)

        # String template formatting that safely handles both {{var}} and {var}
        # without breaking on literal JSON braces { "foo": "bar" }
        rendered = template
        for k, v in rendered_vars.items():
            # First replace double braces {{ k }}
            rendered = re.sub(rf"\{{\{{\s*{re.escape(k)}\s*\}}\}}", lambda m, val=v: val, rendered)
            # Then replace single braces { k }
            rendered = re.sub(rf"\{{\s*{re.escape(k)}\s*\}}", lambda m, val=v: val, rendered)
        return rendered
