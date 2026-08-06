"""B-024 Secret redaction.

Scrubs tokens, keys, cookies and credential values from any text before it
is persisted (job records, discovery errors, stored URLs). ``token/cookie
不落盘`` (Phase 2 §13): a redacted value is never a real credential.
"""

from __future__ import annotations

import re

REDACTED = "<REDACTED>"

_SENSITIVE_QUERY_PARAM = re.compile(
    r"(?i)([?&](?:access_token|api_key|apikey|token|key|password|passwd|"
    r"secret|signature|sig|auth|session|cookie|credential)=)([^&\s]+)"
)
_BEARER_RE = re.compile(r"(?i)(\bBearer\s+)(\S+)")
_AUTH_HEADER_RE = re.compile(
    r"(?i)((?:authorization|proxy-authorization):\s*)(\S+)"
)
_COOKIE_HEADER_RE = re.compile(r"(?i)(cookie:\s*)([^\r\n]+)")


def redact_secrets(text: str) -> str:
    """Replace credential-shaped values with a redaction marker."""
    if not text:
        return text
    redacted = _SENSITIVE_QUERY_PARAM.sub(r"\g<1>" + REDACTED, text)
    redacted = _BEARER_RE.sub(r"\g<1>" + REDACTED, redacted)
    redacted = _AUTH_HEADER_RE.sub(r"\g<1>" + REDACTED, redacted)
    redacted = _COOKIE_HEADER_RE.sub(r"\g<1>" + REDACTED, redacted)
    return redacted
