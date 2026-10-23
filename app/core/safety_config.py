"""Safety configuration and distress / self-harm detection rules.

Pre-checks user queries before any AI call. If distress is triggered, the AI call
is completely bypassed, a supportive message with helpline resources is returned,
ai_status is set to 'safety', and no flag is ever stored on the user profile.
"""
import re
from typing import List

# Clearly marked placeholder for administrator / clinical helpline verification
# Do not invent arbitrary numbers; placeholder indicates emergency crisis resources
HELPLINE_CONFIG_PLACEHOLDER = (
    "[CRISIS_HELPLINE_INFO: If you are experiencing overwhelming distress, please connect with a trusted adult, "
    "counselor, or confidential helpline. In India: KIRAN Mental Health Helpline 1800-599-0019 (24/7) or "
    "Tele-MANAS 14416 / 1800-891-4416. In the US/Canada: 988. In the UK: 111. You are not alone.]"
)

SUPPORTIVE_SAFETY_MESSAGE = (
    "It sounds like you are carrying a lot right now, and your well-being is the most important thing. "
    "Please know that you do not have to go through this alone. We strongly encourage you to pause, reach out, "
    "and speak with a trusted adult, family member, teacher, or academic counselor. "
    f"\n\nFree and confidential support is available right now:\n{HELPLINE_CONFIG_PLACEHOLDER}"
)

# Comprehensive patterns covering English and Hinglish phrases
DISTRESS_PATTERNS: List[re.Pattern] = [
    # English
    re.compile(r"\b(kill\s+(my|one)?self|suicid(e|al)|want\s+to\s+die|end\s+my\s+life|end\s+it\s+all)\b", re.IGNORECASE),
    re.compile(r"\b(self[\s-]?harm|cut\s+myself|hurt\s+myself|hang\s+myself)\b", re.IGNORECASE),
    re.compile(r"\b(no\s+reason\s+to\s+live|better\s+off\s+dead|can'?t\s+go\s+on\s+living)\b", re.IGNORECASE),
    re.compile(r"\b(want\s+to\s+disappear\s+forever|wish\s+i\s+was\s+never\s+born)\b", re.IGNORECASE),
    # Hinglish
    re.compile(r"(jaan\s+de\s+dunga|mar\s+jana|marne\s+ka\s+man)", re.IGNORECASE),
    re.compile(r"(apne\s+aap\s+ko\s+khatam|khud\s+ko\s+khatam|khatam\s+kar)", re.IGNORECASE),
    re.compile(r"(zindagi\s+khatam|jeene\s+ka\s+koi\s+fayda)", re.IGNORECASE),
    re.compile(r"(suicide\s+karna|suicide\s+kar)", re.IGNORECASE),
]


def check_distress_safety(text: str) -> bool:
    """Return True if any self-harm or acute distress pattern is matched."""
    if not text:
        return False
    clean = text.strip()
    return any(p.search(clean) for p in DISTRESS_PATTERNS)
