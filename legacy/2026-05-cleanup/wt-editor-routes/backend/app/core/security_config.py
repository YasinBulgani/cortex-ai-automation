"""Security configuration constants for TestwrightAI Banking Platform.

Complies with: KVKK, BDDK, PCI-DSS security requirements.
"""

# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# Applied only when connection is over HTTPS
HSTS_HEADER = "max-age=31536000; includeSubDomains"

# Applied to API responses (non-HTML)
API_CACHE_CONTROL = "no-store, no-cache, must-revalidate"
API_CSP = "default-src 'self'"

# ---------------------------------------------------------------------------
# Content & Size Limits
# ---------------------------------------------------------------------------
ALLOWED_CONTENT_TYPES = ["application/json", "multipart/form-data", "text/plain"]
MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_DEFAULT = "60/minute"
RATE_LIMIT_AUTH = "10/minute"  # Stricter for auth endpoints
RATE_LIMIT_AI = "20/minute"  # AI endpoints

# ---------------------------------------------------------------------------
# JWT / Auth
# ---------------------------------------------------------------------------
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 30

# ---------------------------------------------------------------------------
# Password Policy
# ---------------------------------------------------------------------------
PASSWORD_MIN_LENGTH = 8

# ---------------------------------------------------------------------------
# Sensitive Field Patterns (for log masking / PII filtering)
# ---------------------------------------------------------------------------
SENSITIVE_FIELD_PATTERNS = [
    "password",
    "token",
    "secret",
    "key",
    "credit_card",
    "ssn",
    "tckn",
    "iban",
    "cvv",
    "pin",
]

# ---------------------------------------------------------------------------
# Banking Audit Log Fields (events that must be logged for compliance)
# ---------------------------------------------------------------------------
BANKING_LOG_FIELDS = {
    "payment",
    "transfer",
    "auth",
    "session",
    "kyc",
    "kvkk",
    "pii",
}
