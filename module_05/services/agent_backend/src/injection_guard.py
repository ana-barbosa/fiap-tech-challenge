import re

_PATTERNS: dict[str, re.Pattern] = {
    "ignore_previous_instructions": re.compile(
        r"\b(ignor[ae]|desconsider[ae]|esque[çc]a)\b.{0,30}\b(instru[çc][õo]es|regras|comandos|prompt)\b",
        re.IGNORECASE,
    ),
    "role_override": re.compile(r"\b(you are now|aja como|voc[êe] agora [ée]|finja ser)\b", re.IGNORECASE),
    "reveal_system_prompt": re.compile(
        r"\b(revele|mostre|repita)\b.{0,30}\b(suas instru[çc][õo]es|o prompt|o system prompt)\b", re.IGNORECASE
    ),
    "system_prompt_marker": re.compile(r"\bsystem prompt\b", re.IGNORECASE),
}


def looks_suspicious(text: str) -> str | None:
    for name, pattern in _PATTERNS.items():
        if pattern.search(text):
            return name
    return None
