"""Reference recursive sanitizer for ATP event payload metadata.

This module owns the value-level checks that JSON Schema cannot reliably express,
especially credentials placed below benign field names. It has no I/O and mutates
neither its input nor runtime state.
"""

from __future__ import annotations

import re
from typing import Any, Literal


class SanitizationError(ValueError):
    """Raised when reject mode encounters sensitive content."""


_FORBIDDEN_KEY = re.compile(
    r"(?:prompt|secret|credential|token|password|session_?key|private_?var_?value|"
    r"raw_?content|absolute_?path|operator_?identity)",
    re.IGNORECASE,
)
_PRIVATE_PATH = re.compile(r"^(?:/home/|/Users/|[A-Za-z]:[\\/]Users[\\/])")
_CREDENTIALS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\b(?:ghp|github_pat|xox[baprs])_[A-Za-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"\btoken\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b"),
)
_REDACTION = "[REDACTED_SENSITIVE]"


def sanitize_payload(value: Any, *, mode: Literal["reject", "redact"] = "reject") -> Any:
    """Return a recursively checked copy, rejecting or redacting sensitive data."""
    if mode not in {"reject", "redact"}:
        raise ValueError("mode must be 'reject' or 'redact'")
    return _sanitize(value, mode=mode, path="payload")


def _sanitize(value: Any, *, mode: str, path: str) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise SanitizationError(f"non-string key at {path}")
            if _FORBIDDEN_KEY.search(key):
                if mode == "reject":
                    raise SanitizationError(f"sensitive key at {path}")
                continue
            clean[key] = _sanitize(child, mode=mode, path=f"{path}.{key}")
        return clean
    if isinstance(value, list):
        return [_sanitize(child, mode=mode, path=f"{path}[]") for child in value]
    if isinstance(value, str):
        sensitive = _PRIVATE_PATH.search(value) is not None or any(pattern.search(value) for pattern in _CREDENTIALS)
        if sensitive and mode == "reject":
            raise SanitizationError(f"sensitive value at {path}")
        if sensitive:
            redacted = value
            if _PRIVATE_PATH.search(redacted):
                return _REDACTION
            for pattern in _CREDENTIALS:
                redacted = pattern.sub(_REDACTION, redacted)
            return redacted
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise SanitizationError(f"unsupported value type at {path}")
