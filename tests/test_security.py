"""
Tests for security mechanisms: SSRF validation, path traversal, filename sanitization.
"""

from pathlib import Path
import pytest

from property_archiver.core.exceptions import PathTraversalError, SSRFError
from property_archiver.core.security import (
    is_private_ip,
    safe_join_path,
    sanitize_filename,
    validate_url_security,
)


def test_is_private_ip():
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("192.168.1.1") is True
    assert is_private_ip("172.16.0.1") is True
    assert is_private_ip("169.254.1.1") is True
    assert is_private_ip("::1") is True
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("1.1.1.1") is False


def test_validate_url_security_allowed_domain():
    url = "https://www.privateproperty.co.za/for-sale/listing/T12345"
    res = validate_url_security(url, allowed_domains=["www.privateproperty.co.za"])
    assert res == url


def test_validate_url_security_blocks_localhost():
    with pytest.raises(SSRFError, match="prohibited"):
        validate_url_security("http://localhost:8080/secret")

    with pytest.raises(SSRFError, match="prohibited"):
        validate_url_security("http://127.0.0.1/admin")


def test_validate_url_security_blocks_disallowed_domain():
    with pytest.raises(SSRFError, match="not in the allowed domain list"):
        validate_url_security(
            "https://evil-site.com/listing",
            allowed_domains=["www.privateproperty.co.za"]
        )


def test_validate_url_security_blocks_invalid_scheme():
    with pytest.raises(SSRFError, match="Unsupported URL scheme"):
        validate_url_security("file:///etc/passwd")

    with pytest.raises(SSRFError, match="Unsupported URL scheme"):
        validate_url_security("ftp://server/data")


def test_sanitize_filename():
    assert sanitize_filename("normal_file.jpg") == "normal_file.jpg"
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("file?with*illegal:chars<.png") == "file_with_illegal_chars_.png"
    assert sanitize_filename("CON.txt") == "safe_CON.txt"
    assert sanitize_filename("NUL") == "safe_NUL"
    assert sanitize_filename("") == "unnamed.bin"


def test_safe_join_path(tmp_path: Path):
    base = tmp_path / "archive"
    base.mkdir()

    # Valid subpath
    valid_p = safe_join_path(base, "listings", "T123")
    assert str(valid_p).startswith(str(base))

    # Directory traversal attempt
    with pytest.raises(PathTraversalError):
        safe_join_path(base, "..", "..", "system32")
