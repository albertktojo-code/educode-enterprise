from __future__ import annotations

import re
from typing import Any

_PROMPT_INJECTION_PATTERNS = [
    r"ignore (all|any|the) previous instructions",
    r"ignore todas? as instruções",
    r"reveal (the )?(system|developer) prompt",
    r"mostre (o )?prompt (do sistema|interno)",
    r"execute (this )?command",
    r"exfiltrate|vaze|revele.*segredo",
]
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}(?!\d)")
_DOCUMENT_RE = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")


def scan_untrusted_text(text: str) -> dict[str, Any]:
    lowered = text.casefold()
    injection_hits = [pattern for pattern in _PROMPT_INJECTION_PATTERNS if re.search(pattern, lowered)]
    pii = {
        "email_count": len(_EMAIL_RE.findall(text)),
        "phone_count": len(_PHONE_RE.findall(text)),
        "document_count": len(_DOCUMENT_RE.findall(text)),
    }
    return {
        "prompt_injection_detected": bool(injection_hits),
        "prompt_injection_patterns": injection_hits,
        "pii_detected": any(pii.values()),
        "pii_summary": pii,
        "safe": not injection_hits,
    }


def redact_personal_data(value: Any) -> Any:
    if isinstance(value, str):
        value = _EMAIL_RE.sub("[EMAIL_REMOVIDO]", value)
        value = _PHONE_RE.sub("[TELEFONE_REMOVIDO]", value)
        return _DOCUMENT_RE.sub("[DOCUMENTO_REMOVIDO]", value)
    if isinstance(value, list):
        return [redact_personal_data(item) for item in value]
    if isinstance(value, dict):
        blocked_keys = {"email", "student_email", "phone", "cpf", "address", "full_name", "student_name"}
        return {
            key: "[DADO_PESSOAL_REMOVIDO]" if key.casefold() in blocked_keys else redact_personal_data(item)
            for key, item in value.items()
        }
    return value
