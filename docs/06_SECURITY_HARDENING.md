# Neurex Security Hardening Guide

**Last Updated:** 2026-06-09  
**Status:** Production-Hardened  
**Standards:** OWASP Top 10, NIST Cybersecurity Framework  
**Compliance:** SOC 2, GDPR-ready

---

## Table of Contents

1. [OWASP Top 10 Checklist](#owasp-top-10-checklist)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Protection](#data-protection)
4. [API Security](#api-security)
5. [Infrastructure Security](#infrastructure-security)
6. [Secret Rotation](#secret-rotation)
7. [Security Monitoring](#security-monitoring)
8. [Incident Response](#incident-response)

---

## OWASP Top 10 Checklist

### A1: Broken Access Control

**Vulnerability:** Users access data they shouldn't (IDOR, RBAC bypass)

**Mitigations:**
```python
# ✅ Implement Row Level Security (RLS)
# Every query filters by tenant_id automatically

# ✅ Check permissions explicitly
from app.deps import require_permission

@router.patch("/defects/{defect_id}")
async def update_defect(
    defect_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("defect:write"))
):
    defect = await get_defect(defect_id)
    
    # ✅ Verify ownership (IDOR prevention)
    if defect.project.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not your defect")
    
    # Update...
    return defect

# ✅ Test IDOR with different user tokens
# In tests/security/test_idor.py
async def test_cannot_access_other_tenant_defect():
    # User from org-1 tries to access org-2's defect
    async with client:
        response = await client.patch(
            f"/defects/{org2_defect_id}",
            json={"status": "resolved"},
            headers={"Authorization": f"Bearer {org1_token}"}
        )
    
    assert response.status_code == 403
```

**Verification:**
```bash
# Audit RBAC permissions
SELECT role, permissions FROM roles;

# Check for overly permissive policies
SELECT * FROM pg_policies WHERE permissive = false;
```

---

### A2: Cryptographic Failures

**Vulnerability:** Sensitive data exposed in transit or at rest

**Mitigations:**
```bash
# ✅ Use HTTPS only (production)
# nginx config:
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}

# ✅ Enable HSTS (force HTTPS for 1 year)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# ✅ Encrypt sensitive data at rest
# Use PostgreSQL transparent encryption:
# PostgreSQL pgcrypto extension for field-level encryption

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Store encrypted API keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    key_encrypted BYTEA NOT NULL,  -- Encrypted with pgp_sym_encrypt
    created_at TIMESTAMP NOT NULL
);

-- Insert encrypted key
INSERT INTO api_keys (id, user_id, key_encrypted, created_at)
VALUES (
    gen_random_uuid(),
    'user-id',
    pgp_sym_encrypt('my-secret-key', 'encryption-passphrase'),
    NOW()
);

# ✅ Enable SSL for database connections
DATABASE_URL=postgresql+psycopg2://user:pass@db.com/db?sslmode=require

# ✅ Use secure JWT signing (minimum 256-bit key)
JWT_SECRET=<64-character-random-string>  # Min 256 bits = 32 bytes = 44 base64 chars
```

**Verification:**
```bash
# Check encryption in transit
curl -v https://api.neurex.ai/health 2>&1 | grep "TLSv\|SSL"

# Verify minimum TLS version
openssl s_client -connect api.neurex.ai:443 -tls1_2

# Test for weak ciphers
nmap --script ssl-enum-ciphers -p 443 api.neurex.ai
```

---

### A3: Injection

**Vulnerability:** SQL injection, command injection, LDAP injection

**Mitigations:**
```python
# ❌ NEVER use string concatenation for SQL
query = f"SELECT * FROM test_cases WHERE id = '{case_id}'"  # Vulnerable!

# ✅ Always use parameterized queries
from sqlalchemy import text

query = text("SELECT * FROM test_cases WHERE id = :case_id")
result = await session.execute(query, {"case_id": case_id})

# ✅ Use ORM to prevent SQL injection
case = await session.query(TestCase).filter_by(id=case_id).first()

# ✅ Validate and sanitize inputs
from pydantic import BaseModel, Field, validator

class CreateTestCaseRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    priority: str = Field(..., regex="^(critical|high|medium|low)$")
    
    @validator('title')
    def title_no_sql_keywords(cls, v):
        # Additional validation beyond type checking
        dangerous = [';', '--', '/*', '*/']
        if any(d in v for d in dangerous):
            raise ValueError("Invalid characters in title")
        return v

# ✅ Use allow-list for allowed values (no user input)
ALLOWED_PRIORITIES = ["critical", "high", "medium", "low"]
priority = request.priority
if priority not in ALLOWED_PRIORITIES:
    raise ValueError("Invalid priority")
```

**Verification:**
```bash
# Test for SQL injection vulnerabilities
# Use OWASP SQLMap tool
sqlmap -u "http://localhost:8000/api/v1/test-cases?title=" \
       --data="title=test" \
       --dbs

# Audit code for dangerous patterns
grep -r "f\".*{" backend/app/domains/*/router.py  # String formatting in queries
```

---

### A4: Insecure Design

**Vulnerability:** Weak authentication, no rate limiting, predictable tokens

**Mitigations:**
```python
# ✅ Enforce strong password policy
from app.domains.auth.service import validate_password

def validate_password(password: str):
    if len(password) < 12:
        raise ValueError("Password must be 12+ characters")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain uppercase")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain digits")
    if not any(c in "!@#$%^&*" for c in password):
        raise ValueError("Password must contain special character")

# ✅ Implement rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(credentials: LoginRequest):
    ...

# ✅ Use cryptographically secure random tokens
import secrets

refresh_token = secrets.token_urlsafe(32)  # 256 bits of entropy

# ✅ Implement MFA (TOTP)
from pyotp import TOTP

def generate_mfa_secret():
    return TOTP.new(provisioning_uri=True).secret

def verify_mfa_code(secret: str, code: str) -> bool:
    return TOTP(secret).verify(code)

# ✅ Implement session timeout
ACCESS_TOKEN_EXPIRE_MINUTES = 30
IDLE_TIMEOUT_MINUTES = 15  # Auto-logout after 15 min inactivity

# ✅ Use CSRF tokens for state-changing operations
from fastapi_csrf_protect import CsrfProtect

@router.post("/test-cases")
async def create_case(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    await csrf_protect.validate_csrf(request)
    # Process request
```

---

### A5: Broken Authentication

**Vulnerability:** Weak passwords, session hijacking, credential exposure

**Mitigations:**
```python
# ✅ Secure password hashing (not reversible)
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Increase rounds if password checking takes <100ms
)

# Hash password
hashed = pwd_context.hash("user-password")

# Verify password
is_correct = pwd_context.verify("user-password", hashed)

# ✅ Use secure session handling
# Session stored in Redis (not in database for speed)
# Set HTTPONLY flag to prevent XSS access
# Set SECURE flag for HTTPS only
# Set SAMESITE=Strict to prevent CSRF

response = JSONResponse(content={"token": access_token})
response.set_cookie(
    "session",
    session_id,
    httponly=True,      # JavaScript can't access
    secure=True,        # HTTPS only
    samesite="strict",  # CSRF protection
    max_age=3600        # 1 hour
)

# ✅ Implement credential stuffing protection
from slowapi import Limiter

@router.post("/auth/login")
@limiter.limit("5/minute")  # Rate limit per IP
@limiter.limit("10/hour")   # Rate limit per username
async def login(credentials: LoginRequest):
    ...

# ✅ Enforce password rotation (every 90 days)
USER_PASSWORD_EXPIRY_DAYS = 90

# ✅ Monitor for suspicious authentication patterns
async def log_suspicious_activity(user_id: str, event: str):
    # Log all auth events for audit trail
    await audit_service.log_auth_event(user_id, event)
    
    # Alert if > 5 failed login attempts in 5 minutes
    failed_attempts = await cache.get(f"failed-logins:{user_id}")
    if failed_attempts > 5:
        alert_team(f"Possible credential attack on {user_id}")
```

---

### A6: Sensitive Data Exposure

**Vulnerability:** Personal data, secrets in logs/error messages

**Mitigations:**
```python
# ✅ Filter sensitive fields from logs
import logging
from pythonjsonlogger import jsonlogger

class SensitiveDataFilter(logging.Filter):
    SENSITIVE_FIELDS = ['password', 'secret', 'token', 'api_key', 'ssn', 'credit_card']
    
    def filter(self, record):
        for field in self.SENSITIVE_FIELDS:
            if field in record.__dict__:
                record.__dict__[field] = '[REDACTED]'
        return True

logger = logging.getLogger()
logger.addFilter(SensitiveDataFilter())

# ✅ Mask sensitive data in error responses
try:
    # Database operation
    case = await db.query(TestCase).filter_by(id=case_id).first()
except Exception as e:
    # Don't expose database error details to client
    logger.error(f"Database error: {e}")  # Log full error internally
    raise HTTPException(
        status_code=500,
        detail="Internal server error"  # Generic message to client
    )

# ✅ Use Sentry to filter sensitive data
import sentry_sdk

sentry_sdk.init(
    dsn=SENTRY_DSN,
    before_send=lambda event, hint: filter_sensitive_data(event)
)

def filter_sensitive_data(event):
    # Redact sensitive fields in exception context
    if 'exception' in event:
        for exc in event['exception'].get('values', []):
            for frame in exc.get('stacktrace', {}).get('frames', []):
                if 'vars' in frame:
                    for key in frame['vars']:
                        if any(s in key.lower() for s in ['password', 'secret']):
                            frame['vars'][key] = '[Filtered]'
    return event

# ✅ Minimize PII in database
# Store email hash instead of email for searches
import hashlib

email_hash = hashlib.sha256(email.lower().encode()).hexdigest()

# ✅ Data retention policy
# Delete logs after 90 days
# Delete old test artifacts after 180 days
# Delete inactive user data after 1 year
```

---

### A7: Identification & Authentication Failures

**Vulnerability:** Broken account recovery, weak session IDs

**Mitigations:**
```python
# ✅ Use cryptographically secure session IDs
import secrets

session_id = secrets.token_urlsafe(32)  # 256-bit entropy

# ✅ Implement secure password reset
async def request_password_reset(email: str):
    user = await db.query(User).filter_by(email=email).first()
    
    if not user:
        # Don't reveal if email exists (timing attack prevention)
        return {"detail": "If email exists, password reset sent"}
    
    # Generate secure reset token (expires in 15 minutes)
    reset_token = secrets.token_urlsafe(32)
    reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
    
    await db.update(User).where(User.id == user.id).values(
        password_reset_token=reset_token_hash,
        password_reset_token_expires=datetime.utcnow() + timedelta(minutes=15)
    )
    await db.commit()
    
    # Send email with reset link
    reset_url = f"https://app.neurex.ai/reset-password?token={reset_token}"
    await email_service.send_password_reset(user.email, reset_url)

async def reset_password(token: str, new_password: str):
    # Verify token hasn't expired
    user = await db.query(User).filter(
        User.password_reset_token == hashlib.sha256(token.encode()).hexdigest(),
        User.password_reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Update password
    user.password_hash = pwd_context.hash(new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None
    await db.commit()

# ✅ Implement account lockout after failed attempts
async def track_login_attempt(email: str, success: bool):
    if not success:
        key = f"failed-login:{email}"
        attempts = await redis.incr(key)
        await redis.expire(key, 900)  # Expire after 15 min
        
        if attempts > 5:
            # Lock account for 1 hour
            await redis.setex(f"locked:{email}", 3600, "1")
            raise HTTPException(status_code=429, detail="Account locked. Try again later.")

# ✅ Monitor for account takeover
async def detect_anomalous_login(user_id: str, ip_address: str, user_agent: str):
    # Check if login from unusual location
    previous_locations = await db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.action == "login"
    ).order_by(AuditLog.created_at.desc()).limit(10).all()
    
    previous_ips = [log.ip_address for log in previous_locations]
    
    if ip_address not in previous_ips:
        # Send verification email to user
        await email_service.send_suspicious_login_alert(
            user.email,
            ip_address,
            user_agent
        )
```

---

### A8: Software & Data Integrity Failures

**Vulnerability:** Unsafe CI/CD, unsigned updates, vulnerable dependencies

**Mitigations:**
```bash
# ✅ Verify code integrity (git commit signing)
git config user.signingkey <GPG-KEY-ID>
git commit -S -m "Secure commit"

# Require signed commits in production branches
# GitHub Settings → Branches → Require signed commits

# ✅ Scan dependencies for vulnerabilities
pip install safety
safety check  # Check for known vulnerable packages

# npm
npm audit  # Built-in npm vulnerability scanner

# ✅ Use dependency locking
pip freeze > requirements.txt  # Pin exact versions
package-lock.json  # npm lock file

# ✅ Implement SBOM (Software Bill of Materials)
pip list --format=json > sbom.json

# ✅ Code review required before merge
# GitHub settings: Require pull request reviews

# ✅ Static code analysis (SAST)
bandit backend/  # Python security linter
eslint --ext .ts apps/web/  # TypeScript security

# ✅ Container image scanning
docker scan neurex/backend:1.0.0
# Or use Trivy
trivy image neurex/backend:1.0.0

# ✅ Immutable builds
# Tag images with commit SHA, not latest
docker build -t neurex/backend:$(git rev-parse --short HEAD) .
docker build -t neurex/backend:1.0.0 .
# Never rebuild image with same tag
```

---

### A9: Logging & Monitoring Failures

**Vulnerability:** Attacks not detected, no audit trail

**Mitigations:**
```python
# ✅ Log all security-relevant events
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    user_id: UUID = Column(UUID(as_uuid=True), nullable=True)
    action: str = Column(String(100))  # login, create, update, delete
    entity_type: str = Column(String(100))  # test_case, defect
    entity_id: UUID = Column(UUID(as_uuid=True))
    changes: dict = Column(JSONB)  # Before/after
    ip_address: str = Column(INET)
    user_agent: str = Column(String(500))
    timestamp: datetime = Column(DateTime, default=datetime.utcnow)

# ✅ Alert on suspicious activities
async def check_security_alerts(alert_type: str):
    alerts = {
        "failed_logins": "SELECT COUNT(*) FROM audit_logs WHERE action='login_failed' AND created_at > NOW() - INTERVAL '5 min'",
        "permission_denied": "SELECT COUNT(*) FROM audit_logs WHERE action='permission_denied' AND created_at > NOW() - INTERVAL '5 min'",
        "data_export": "SELECT COUNT(*) FROM audit_logs WHERE action='export' AND created_at > NOW() - INTERVAL '1 hour'",
    }
    
    count = await db.execute(alerts[alert_type])
    
    if count > ALERT_THRESHOLD[alert_type]:
        await alert_security_team(alert_type, count)

# ✅ Use centralized logging (ELK Stack, Datadog)
import logging.handlers

handler = logging.handlers.SysLogHandler(address=('syslog.example.com', 514))
logger.addHandler(handler)

# ✅ Enable database audit logging
# PostgreSQL: enable pgaudit extension
CREATE EXTENSION pgaudit;
SET pgaudit.log = 'ALL';

# ✅ Monitor for attacks
# Install Wazuh agent for HIDS (Host-based Intrusion Detection)
```

---

### A10: Server-Side Request Forgery (SSRF)

**Vulnerability:** App makes requests to unintended targets (localhost, internal IPs)

**Mitigations:**
```python
# ✅ Validate redirect URLs
from urllib.parse import urlparse

def is_safe_redirect_url(url: str, allowed_hosts: list) -> bool:
    parsed = urlparse(url)
    
    # Block local/private IPs
    blocked_patterns = [
        "localhost", "127.0.0.1", "0.0.0.0",  # Localhost
        "192.168.", "10.", "172.16.",  # Private ranges
        "169.254.",  # Link-local
    ]
    
    for pattern in blocked_patterns:
        if pattern in parsed.hostname:
            return False
    
    # Only allow whitelisted domains
    return parsed.hostname in allowed_hosts

# ✅ Validate webhook URLs
async def create_webhook(url: str, events: list):
    if not is_safe_redirect_url(url, ALLOWED_WEBHOOK_DOMAINS):
        raise HTTPException(status_code=400, detail="Invalid webhook URL")
    
    # Verify URL is reachable
    try:
        response = await httpx.head(url, timeout=5)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Webhook URL not reachable")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot reach webhook URL: {e}")

# ✅ Use allowlist for external API calls
ALLOWED_API_HOSTS = {
    "jira.atlassian.net",
    "api.github.com",
    "gitlab.com",
    "api.slack.com",
}

async def call_external_api(url: str):
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_API_HOSTS:
        raise HTTPException(status_code=403, detail="External API not allowed")
    
    response = await httpx.get(url, timeout=10)
    return response

# ✅ Disable dangerous HTTP methods if not needed
ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE"]

@app.middleware("http")
async def validate_http_method(request: Request, call_next):
    if request.method not in ALLOWED_METHODS:
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    return await call_next(request)
```

---

## Authentication & Authorization

### JWT Best Practices

```python
# ✅ Use strong signing algorithm
JWT_ALGORITHM = "HS256"  # Symmetric, fast

# Or ECDSA for asymmetric (public key verification)
JWT_ALGORITHM = "ES256"  # Elliptic Curve, slower but more secure

# ✅ Include required claims
def create_access_token(user_id: str, org_id: str, role: str) -> str:
    payload = {
        "sub": user_id,              # Subject (user ID)
        "org": org_id,               # Organization (for RLS)
        "role": role,                # User role
        "iat": datetime.utcnow(),    # Issued at
        "exp": datetime.utcnow() + timedelta(minutes=30),  # Expiration
        "nbf": datetime.utcnow(),    # Not before
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

# ✅ Verify all claims
def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True, "verify_nbf": True}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload

# ✅ Use separate refresh tokens
def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",  # Distinguish from access token
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

# ✅ Revoke tokens on logout (store in blacklist)
async def logout(token: str):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    exp = payload['exp']
    
    # Add to Redis blacklist until expiration
    await redis.setex(
        f"blacklist:{token}",
        exp - datetime.utcnow().timestamp(),
        "1"
    )

async def verify_not_blacklisted(token: str):
    if await redis.get(f"blacklist:{token}"):
        raise HTTPException(status_code=401, detail="Token has been revoked")
```

---

## Data Protection

### Encryption at Rest

```python
# ✅ Use database-level encryption
# PostgreSQL pgcrypto extension

from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    key_encrypted = Column(String, nullable=False)
    
    @staticmethod
    def encrypt_key(key: str, passphrase: str) -> str:
        # Use pgp_sym_encrypt in SQL:
        # pgp_sym_encrypt('key-value', 'passphrase')
        pass
    
    @staticmethod
    def decrypt_key(encrypted: str, passphrase: str) -> str:
        # Use pgp_sym_decrypt in SQL:
        # pgp_sym_decrypt(encrypted_column, 'passphrase')
        pass

# ✅ Encrypt sensitive configuration
from cryptography.fernet import Fernet

key = Fernet.generate_key()  # Store in AWS Secrets Manager
cipher = Fernet(key)

encrypted_api_key = cipher.encrypt(b"secret-api-key")
decrypted_api_key = cipher.decrypt(encrypted_api_key)

# ✅ Use field-level encryption for PII
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True)
    email = Column(String, nullable=False)
    email_hash = Column(String, nullable=False, unique=True)  # For searching
    phone_encrypted = Column(String)  # Encrypted
    ssn_encrypted = Column(String)    # Encrypted
    
    @staticmethod
    def hash_email(email: str) -> str:
        return hashlib.sha256(email.encode()).hexdigest()
```

### GDPR Compliance

```python
# ✅ Data Subject Access Request (DSAR)
async def export_user_data(user_id: str) -> bytes:
    """Export all user data in GDPR-compliant format."""
    
    user_data = {
        "user": await db.query(User).filter_by(id=user_id).first(),
        "test_cases": await db.query(TestCase).filter_by(created_by=user_id).all(),
        "defects": await db.query(Defect).filter_by(reported_by=user_id).all(),
        "audit_logs": await db.query(AuditLog).filter_by(user_id=user_id).all(),
    }
    
    # Export as JSON
    export_json = json.dumps(
        user_data,
        default=str,
        indent=2
    )
    
    # Compress and encrypt
    encrypted = cipher.encrypt(export_json.encode())
    
    return encrypted

# ✅ Right to be forgotten (data deletion)
async def delete_user_data(user_id: str):
    """Permanently delete user data."""
    
    # Delete user records
    await db.query(User).filter_by(id=user_id).delete()
    
    # Soft-delete user content (keep audit trail)
    await db.query(TestCase).filter_by(created_by=user_id).update({
        "deleted_at": datetime.utcnow()
    })
    
    # Keep audit logs for legal purposes (anonymize user_id)
    await db.query(AuditLog).filter_by(user_id=user_id).update({
        "user_id": None,
        "user_name": "[Deleted]"
    })
    
    await db.commit()

# ✅ Consent management
class ConsentLog(Base):
    __tablename__ = "consent_logs"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, nullable=False)
    consent_type = Column(String)  # marketing, analytics, third_party
    consent_value = Column(Boolean)  # True = granted, False = revoked
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user_agent = Column(String)

async def check_consent(user_id: str, consent_type: str) -> bool:
    latest = await db.query(ConsentLog).filter(
        ConsentLog.user_id == user_id,
        ConsentLog.consent_type == consent_type
    ).order_by(ConsentLog.timestamp.desc()).first()
    
    return latest.consent_value if latest else False
```

---

## API Security

### Input Validation

```python
# ✅ Use Pydantic for schema validation
from pydantic import BaseModel, Field, EmailStr, validator

class CreateTestCaseRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., max_length=10000)
    priority: str = Field(..., pattern="^(critical|high|medium|low)$")
    tags: list[str] = Field(default=[], max_items=10)
    
    @validator('title')
    def title_no_html(cls, v):
        if '<' in v or '>' in v:
            raise ValueError('HTML not allowed')
        return v

# ✅ Limit request size
app.add_middleware(
    "http",
    middleware=RequestSizeLimitMiddleware,
    max_size=1_000_000  # 1MB max request body
)

# ✅ Sanitize file uploads
import magic

async def upload_artifact(file: UploadFile):
    # Check file type
    file_content = await file.read()
    mime = magic.from_buffer(file_content, mime=True)
    
    ALLOWED_TYPES = ["image/png", "image/jpeg", "text/plain", "application/pdf"]
    if mime not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Check file size
    if len(file_content) > 10_000_000:  # 10MB
        raise HTTPException(status_code=400, detail="File too large")
    
    # Scan with antivirus (ClamAV)
    is_clean = await clamav.scan(file_content)
    if not is_clean:
        raise HTTPException(status_code=400, detail="File contains malware")
    
    # Store in S3
    s3_key = f"artifacts/{uuid.uuid4()}/{file.filename}"
    await s3_client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=file_content)
```

---

## Infrastructure Security

### Network Security

```bash
# ✅ Use security groups / network policies
# AWS Security Group:
resource "aws_security_group" "neurex_backend" {
  name = "neurex-backend"
  
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Internal VPC only
  }
  
  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8", "0.0.0.0/0"]  # VPC + specific external
  }
}

# ✅ DDoS protection
# Enable AWS Shield Advanced (automatic)
# Or Cloudflare WAF

# ✅ VPN for internal communication
# Use service mesh (Istio) with mTLS

# ✅ Firewall rules
# Block all ports except: 80 (HTTP), 443 (HTTPS), 22 (SSH admin-only)
```

### Container Security

```dockerfile
# ✅ Use minimal base image
FROM python:3.11-slim

# ✅ Don't run as root
RUN useradd -m -u 1000 appuser
USER appuser

# ✅ Remove unnecessary packages
RUN apt-get purge -y apt-utils
RUN apt-get autoremove -y

# ✅ Scan image for vulnerabilities
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh - b /usr/local/bin
RUN trivy image .

# ✅ Sign images
# docker trust sign neurex/backend:1.0.0
```

---

## Secret Rotation

### Automated Secret Rotation

```bash
#!/bin/bash
# scripts/rotate-secrets.sh

# Rotate JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 64)
aws secretsmanager update-secret \
  --secret-id neurex/prod/jwt-secret \
  --secret-string "$NEW_JWT_SECRET"

# Update application without restart
# (depends on app to poll for secrets)

# Rotate database password
NEW_DB_PASSWORD=$(openssl rand -base64 32)
aws rds modify-db-instance \
  --db-instance-identifier neurex-prod \
  --master-user-password "$NEW_DB_PASSWORD" \
  --apply-immediately

# Rotate S3 access keys
aws iam create-access-key --user-name neurex-app
aws iam delete-access-key --user-name neurex-app --access-key-id <OLD_KEY_ID>

# Frequency: Monthly for JWT, Quarterly for DB/S3
```

---

## Security Monitoring

### Security Information & Event Management (SIEM)

```python
# ✅ Centralize security logs
import logging
import json
from datetime import datetime

class SecurityEventLogger:
    def __init__(self, siem_endpoint: str):
        self.siem = siem_endpoint
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: str,
        details: dict
    ):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,  # login_failed, permission_denied, etc
            "severity": severity,  # critical, high, medium, low
            "user_id": user_id,
            "details": details,
            "service": "neurex-api"
        }
        
        # Send to SIEM (Splunk, ELK, etc)
        await httpx.post(self.siem, json=event)

# ✅ Alert on suspicious activities
ALERT_RULES = {
    "login_failed": {"threshold": 5, "time_window": 300},  # 5 failures in 5 min
    "permission_denied": {"threshold": 10, "time_window": 600},  # 10 in 10 min
    "data_export": {"threshold": 1, "time_window": 3600},  # Any export
}
```

---

## Incident Response

### Incident Response Procedure

```bash
# 1. Detect incident (alert fires)
# 2. Contain: Take affected service offline
docker-compose stop backend

# 3. Preserve evidence
docker logs backend > /evidence/logs.txt
docker cp backend:/var/log /evidence/

# 4. Investigate
# Check audit logs
psql -c "SELECT * FROM audit_logs WHERE created_at > NOW() - INTERVAL '1 hour' ORDER BY created_at DESC;"

# Check for malicious changes
git log --oneline | head -20
git diff HEAD~5 HEAD

# 5. Remediate
# Change compromised credentials
aws secretsmanager update-secret --secret-id neurex/prod/jwt-secret --secret-string "$(openssl rand -base64 64)"

# 6. Restore
docker-compose up backend

# 7. Verify
curl http://localhost:8000/health

# 8. Post-mortem
# Document: what happened, when, impact, root cause, prevention
```

---

**End of Security Hardening Guide**
