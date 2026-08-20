"""
Security validation utilities: SSRF guard, safe filenames, safe path resolution.
"""

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

from property_archiver.core.exceptions import (
    PathTraversalError,
    SecurityError,
    SSRFError,
)

# Reserved Windows file names
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

# Regex to remove illegal filename characters across Windows/Unix
ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/*?:"<>|\x00-\x1f]')


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address string is private, loopback, link-local, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_url_security(
    url: str,
    allowed_domains: list[str] | None = None,
    allow_custom_domains: bool = False
) -> str:
    """
    Validate that a URL is safe to fetch and does not pose an SSRF risk.

    - Verifies scheme is http or https
    - Checks hostname against allowed list or verifies resolved IP is public
    - Blocks localhost, loopback, private IPv4/IPv6 ranges
    """
    if not url or not isinstance(url, str):
        raise SSRFError("URL must be a non-empty string.")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError(f"Invalid URL: missing hostname in '{url}'.")

    hostname_lower = hostname.lower()

    # Block obvious localhost names
    if hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise SSRFError(f"Access to localhost/loopback address is prohibited: '{hostname}'.")

    # If domain restriction is enforced
    if allowed_domains and not allow_custom_domains:
        is_allowed = any(
            hostname_lower == domain.lower() or hostname_lower.endswith("." + domain.lower())
            for domain in allowed_domains
        )
        if not is_allowed:
            raise SSRFError(
                f"Host '{hostname}' is not in the allowed domain list: {allowed_domains}"
            )

    # DNS check to ensure IP is not private/loopback
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            if is_private_ip(ip_str):
                raise SSRFError(
                    f"Host '{hostname}' resolved to restricted/private IP address: {ip_str}"
                )
    except socket.gaierror as e:
        # If DNS resolution fails, raise SSRFError / network failure
        raise SSRFError(f"Could not resolve hostname '{hostname}': {e}") from e

    return url.strip()


def sanitize_filename(filename: str, max_length: int = 120, default_ext: str = ".bin") -> str:
    """
    Sanitize a filename to prevent path traversal, reserved names, and invalid characters.
    """
    if not filename:
        return f"unnamed{default_ext}"

    # Extract basename only to prevent directory traversal
    base = os.path.basename(filename)

    # Replace illegal characters with underscore
    clean = ILLEGAL_FILENAME_CHARS.sub("_", base)

    # Strip leading/trailing dots and spaces
    clean = clean.strip(". ")

    # Check for empty after sanitization
    if not clean:
        return f"sanitized{default_ext}"

    # Check Windows reserved names
    stem = os.path.splitext(clean)[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        clean = f"safe_{clean}"

    # Truncate length if needed while preserving extension
    if len(clean) > max_length:
        name_stem, ext = os.path.splitext(clean)
        keep_len = max_length - len(ext)
        clean = name_stem[:max(1, keep_len)] + ext

    return clean


def safe_join_path(base_dir: Path | str, *subpaths: str) -> Path:
    """
    Safely join subpaths to a base directory, verifying that the result
    does not escape the base directory (preventing directory traversal).
    """
    base = Path(base_dir).resolve()
    target = base
    for part in subpaths:
        # Disallow absolute subpath components
        part_clean = os.path.normpath(part).lstrip("/\\")
        target = target.joinpath(part_clean)

    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(base)
    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: '{resolved_target}' is outside base directory '{base}'."
        )

    return resolved_target
