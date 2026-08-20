"""
Tests for URL resolver, short listing ID detection, and clipboard helpers.
"""

from property_archiver.utils.url_resolver import (
    is_short_listing_id,
    resolve_short_id,
    resolve_input_targets,
)
from property_archiver.utils.clipboard import get_clipboard_text


def test_is_short_listing_id():
    assert is_short_listing_id("T4710876") is True
    assert is_short_listing_id("t4710876") is True
    assert is_short_listing_id("10524708") is True
    assert is_short_listing_id("/T4710876/") is True
    assert is_short_listing_id("https://www.privateproperty.co.za/1") is False
    assert is_short_listing_id("some-random-text") is False


def test_resolve_short_id():
    url = resolve_short_id("T4710876")
    assert url == "https://www.privateproperty.co.za/T4710876"

    url_lower = resolve_short_id("t4710876")
    assert url_lower == "https://www.privateproperty.co.za/T4710876"


def test_resolve_input_targets():
    inputs = [
        "T4710876",
        "privateproperty.co.za/for-sale/test",
        "https://www.privateproperty.co.za/for-sale/gauteng/test/T123",
    ]
    resolved = resolve_input_targets(inputs)
    assert len(resolved) == 3
    assert resolved[0] == "https://www.privateproperty.co.za/T4710876"
    assert resolved[1] == "https://privateproperty.co.za/for-sale/test"
    assert resolved[2] == "https://www.privateproperty.co.za/for-sale/gauteng/test/T123"


def test_clipboard_reader_safe():
    # Should execute safely without throwing uncaught exceptions
    text = get_clipboard_text()
    assert text is None or isinstance(text, str)
