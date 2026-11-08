import re

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

def mask_email_addresses(text):
    masked, count = EMAIL_PATTERN.subn("[EMAIL_REDACTED]", text)
    return masked, {
        "version": "email_mask_v1",
        "email_address_matches": count,
        "scope": "Email addresses only; other identifiers may remain.",
    }
