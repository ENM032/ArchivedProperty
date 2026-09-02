"""
Custom exception hierarchy for Property Archiver.
"""


class PropertyArchiverError(Exception):
    """Base exception for all errors in Property Archiver."""
    pass


class SecurityError(PropertyArchiverError):
    """Raised when a security validation constraint is violated."""
    pass


class SSRFError(SecurityError):
    """Raised when a target URL violates SSRF safety rules (e.g. private IP/forbidden host)."""
    pass


class PathTraversalError(SecurityError):
    """Raised when an archive path or filename attempts directory traversal."""
    pass


class ResourceExhaustionError(SecurityError):
    """Raised when a response exceeds maximum safe payload size."""
    pass


class FetchError(PropertyArchiverError):
    """Raised when an HTTP request fails or encounters network errors."""
    def __init__(self, message: str, status_code: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class RateLimitExceededError(FetchError):
    """Raised when the target host responds with HTTP 429 Too Many Requests."""
    pass


class HTTPStatusError(FetchError):
    """Raised when an HTTP response has an error status code (4xx/5xx)."""
    pass


class ExtractionError(PropertyArchiverError):
    """Raised when parsing or extracting property data fails."""
    pass


class ValidationError(PropertyArchiverError):
    """Raised when extracted data fails schema validation."""
    pass


class StorageError(PropertyArchiverError):
    """Raised when reading or writing archive data fails."""
    pass


class CorruptedArchiveError(StorageError):
    """Raised when checksum verification fails for an existing archive."""
    pass
