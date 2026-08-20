"""
Extractors package export and factory.
"""

from property_archiver.extractors.base import BaseExtractor
from property_archiver.extractors.private_property import PrivatePropertyExtractor

# Registry of available extractors
EXTRACTORS: list[BaseExtractor] = [
    PrivatePropertyExtractor(),
]


def get_extractor_for_url_or_html(url_or_html: str) -> BaseExtractor:
    """Find and return the matching extractor for a URL or HTML document."""
    for extractor in EXTRACTORS:
        if extractor.can_handle(url_or_html):
            return extractor

    # Default to PrivatePropertyExtractor if none specifically match
    return EXTRACTORS[0]


__all__ = [
    "BaseExtractor",
    "PrivatePropertyExtractor",
    "get_extractor_for_url_or_html",
    "EXTRACTORS",
]
