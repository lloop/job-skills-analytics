"""Extract technology skills from job description text."""

import re

SKILL_PATTERNS = {
    "Python": r"\bpython\b",
    "SQL": r"\bsql\b",
    "AWS": r"\baws\b|amazon web services",
    "Docker": r"\bdocker\b",
    "JavaScript": r"\bjavascript\b|\bjs\b",
    "Tableau": r"\btableau\b",
}


def extract_skills(text: str) -> list[str]:
    """Return known skills found in a description, preserving configured order."""
    return [skill for skill, pattern in SKILL_PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
