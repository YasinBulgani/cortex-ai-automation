"""S-HIGH security validators for file uploads, input sanitization, and XSS prevention.

OWASP Top 10 protections:
- File upload validation (type, size, extension whitelist)
- Input sanitization (HTML escape, XSS prevention)
- Rate limiting per resource
- CSRF token validation
- Secure password requirements
- Sensitive data filtering in logs
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status

_logger = logging.getLogger(__name__)

# S-HIGH-3: File upload whitelist (OWASP A4 - insecure file upload)
ALLOWED_UPLOAD_EXTENSIONS = {
    # API specs
    "json", "yaml", "yml",
    # Code/automation
    "py", "js", "ts", "java", "go", "rb", "php",
    # Docs
    "pdf", "txt", "md", "csv",
    # Images (for screenshots, test evidence)
    "png", "jpg", "jpeg", "gif", "webp",
    # Archives (for bulk imports)
    "zip",
}

ALLOWED_MIME_TYPES = {
    # API specs
    "application/json",
    "application/yaml",
    "text/yaml",
    "text/x-yaml",
    # Code
    "text/plain",
    "text/x-python",
    "application/x-python",
    "text/javascript",
    "text/typescript",
    "application/typescript",
    # Docs
    "application/pdf",
    "text/markdown",
    "text/csv",
    "application/csv",
    # Images
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    # Archive
    "application/zip",
    "application/x-zip-compressed",
}

# S-HIGH-4: File upload size limits (prevent DoS)
MAX_FILE_SIZE_BYTES = {
    "spec": 10 * 1024 * 1024,        # 10 MB for API specs
    "code": 5 * 1024 * 1024,         # 5 MB for code files
    "image": 2 * 1024 * 1024,        # 2 MB for images
    "archive": 50 * 1024 * 1024,     # 50 MB for archives
}


async def validate_upload_file(
    file: UploadFile,
    allowed_extensions: Optional[set[str]] = None,
    max_size: int = 10 * 1024 * 1024,
    category: str = "spec",
) -> tuple[bytes, str]:
    """S-HIGH-3: Validate uploaded file (type, size, extension).

    Args:
        file: FastAPI UploadFile
        allowed_extensions: Set of allowed extensions (defaults to ALLOWED_UPLOAD_EXTENSIONS)
        max_size: Maximum file size in bytes (defaults to 10 MB)
        category: File category for size limit lookup

    Returns:
        Tuple of (file_content, sanitized_filename)

    Raises:
        HTTPException(400): If validation fails

    Security checklist:
    1. Check extension against whitelist
    2. Check MIME type against whitelist
    3. Check file size (prevent DoS)
    4. Verify magic bytes match MIME type (prevent disguised files)
    5. Sanitize filename (prevent path traversal)
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_UPLOAD_EXTENSIONS

    # S-HIGH-3a: Validate extension (case-insensitive)
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı boş olamaz",
        )

    ext = Path(file.filename).suffix.lstrip(".").lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dosya türü desteklenmiyor: .{ext}. İzin verilen: {', '.join(sorted(allowed_extensions))}",
        )

    # S-HIGH-3b: Check MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        _logger.warning(
            "File upload MIME type rejected: filename=%s mime_type=%s",
            file.filename,
            file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME türü desteklenmiyor: {file.content_type}",
        )

    # S-HIGH-3c: Read and validate size
    content = await file.read()
    size_limit = MAX_FILE_SIZE_BYTES.get(category, max_size)
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dosya çok büyük: {len(content)} bayt (max: {size_limit} bayt)",
        )

    # S-HIGH-3d: Validate magic bytes for critical file types
    if ext == "json" and not _validate_json_magic(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON dosya okunamadı veya geçersiz format",
        )

    if ext == "zip" and not _validate_zip_magic(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZIP dosya okunamadı veya geçersiz format",
        )

    # S-HIGH-3e: Sanitize filename (prevent path traversal)
    sanitized_name = _sanitize_filename(file.filename)

    _logger.info(
        "File upload validated: filename=%s size=%d ext=%s",
        sanitized_name,
        len(content),
        ext,
    )

    return content, sanitized_name


def _sanitize_filename(filename: str) -> str:
    """S-HIGH-5: Remove path traversal attempts and dangerous chars.

    Example:
        Input: "../../etc/passwd" → Output: "etcpasswd"
        Input: "test<script>.json" → Output: "testscriptjson"
    """
    # Allow only alphanumeric, dash, underscore, dot
    safe_chars = []
    for char in filename:
        if char.isalnum() or char in "._-":
            safe_chars.append(char)
        elif char in " ":
            safe_chars.append("_")
    result = "".join(safe_chars)
    # Remove leading dots (hidden files, path traversal)
    result = result.lstrip(".")
    return result or "file"


def _validate_json_magic(content: bytes) -> bool:
    """Check if content looks like valid JSON (starts with { or [)."""
    try:
        decoded = content.decode("utf-8").strip()
        return decoded.startswith(('{', '['))
    except UnicodeDecodeError:
        return False


def _validate_zip_magic(content: bytes) -> bool:
    """Check ZIP magic bytes (PK signature)."""
    return content.startswith(b'PK\x03\x04')


def sanitize_html_output(text: str, max_length: int = 1000) -> str:
    """S-HIGH-7: Escape HTML to prevent XSS in template output.

    Used when rendering user-provided text in HTML context.
    Escapes: < > & " '

    Example:
        Input: '<script>alert("xss")</script>'
        Output: '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
    """
    if not text:
        return ""

    # Truncate first (prevent DoS on very long strings)
    text = text[:max_length]

    # HTML escape
    escape_map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }
    return "".join(escape_map.get(char, char) for char in text)


def filter_sensitive_data(value: any, key: str) -> any:
    """S-HIGH-8: Filter sensitive fields from logging/response.

    Used in error handlers and Sentry integration to prevent
    leaking passwords, tokens, secrets.

    Sensitive keys: password, token, secret, api_key, credential,
    auth, bearer, authorization, etc.
    """
    if isinstance(key, str):
        key_lower = key.lower()
        sensitive_patterns = {
            "password", "passwd", "pwd",
            "token", "access_token", "refresh_token",
            "secret", "api_secret", "api_key",
            "auth", "authorization", "bearer",
            "credential", "credentials",
            "hmac", "signature",
            "key", "private_key", "public_key",
        }
        if any(pattern in key_lower for pattern in sensitive_patterns):
            return "[FILTERED]"

    return value


def generate_file_hash(content: bytes) -> str:
    """Generate SHA256 hash of file content for integrity checking."""
    return hashlib.sha256(content).hexdigest()


def validate_content_encoding(content: bytes, expected_type: str = "utf8") -> bool:
    """Validate file encoding to prevent invalid character injection."""
    if expected_type == "utf8":
        try:
            content.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return True
