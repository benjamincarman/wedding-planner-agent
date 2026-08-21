"""PII Redaction Engine for scrubbing sensitive user information before logging and storage."""

import re
from typing import Any, Dict, List, Union

# Regex patterns for sensitive data
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_PATTERN = re.compile(r'(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')


def redact_text(text: str) -> str:
    """Redacts email addresses, phone numbers, and payment details from raw text strings."""
    if not isinstance(text, str):
        return text

    scrubbed = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    scrubbed = PHONE_PATTERN.sub("[REDACTED_PHONE]", scrubbed)
    scrubbed = CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", scrubbed)
    scrubbed = SSN_PATTERN.sub("[REDACTED_SSN]", scrubbed)
    return scrubbed


def redact_pii(data: Any) -> Any:
    """Recursively traverses dictionaries, lists, and strings to sanitize PII fields."""
    if isinstance(data, str):
        return redact_text(data)
    elif isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Check for sensitive key names
            if any(k in key.lower() for k in ["ssn", "credit_card", "password", "secret", "auth_token"]):
                sanitized[key] = "[REDACTED_SECRET]"
            else:
                sanitized[key] = redact_pii(value)
        return sanitized
    elif isinstance(data, list):
        return [redact_pii(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(redact_pii(item) for item in data)
    return data
