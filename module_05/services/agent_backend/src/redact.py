import re

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Matches 8+ digits with optional space/dash/paren/dot separators between them, rather than
# a specific phone format, so any commonly-typed Brazilian phone number is caught.
_PHONE_RE = re.compile(r"(?:\d[\s.\-()]*){8,}\d")

EMAIL_PLACEHOLDER = "[e-mail redatado]"
PHONE_PLACEHOLDER = "[telefone redatado]"
NAME_PLACEHOLDER = "[dado pessoal redatado]"


def redact(text: str | None, known_pii: list[str] = ()) -> str | None:
    if text is None:
        return None

    redacted = text
    for value in known_pii:
        value = value.strip()
        if value:
            redacted = redacted.replace(value, NAME_PLACEHOLDER)

    redacted = _EMAIL_RE.sub(EMAIL_PLACEHOLDER, redacted)
    redacted = _PHONE_RE.sub(PHONE_PLACEHOLDER, redacted)
    return redacted
