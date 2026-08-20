"""
Abstract base class for property portal extractors.
"""

from abc import ABC, abstractmethod
from typing import Any

from property_archiver.models.listing import ListingRecord


class BaseExtractor(ABC):
    """Abstract interface defining extractor capabilities."""

    @abstractmethod
    def can_handle(self, url_or_html: str) -> bool:
        """Determine if this extractor can parse the given URL or HTML content."""
        pass

    @abstractmethod
    def extract(self, html: str, url: str) -> ListingRecord:
        """
        Extract property listing data from HTML content and source URL.
        Returns a normalized ListingRecord instance.
        """
        pass
