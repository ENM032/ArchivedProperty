"""
Pydantic data models for archive manifests and provenance metadata.
"""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ArchiveManifest(BaseModel):
    """Manifest file recording cryptographic hashes for every file in the archive."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default="1.0.0", description="Manifest schema version")
    listing_id: str = Field(description="Listing ID")
    archived_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC archive timestamp")
    archiver_version: str = Field(description="Version of property-archiver used")
    files: dict[str, str] = Field(
        default_factory=dict,
        description="Relative filepath mapped to SHA-256 hexadecimal hash"
    )


class ArchiveMetadata(BaseModel):
    """Crawl and execution provenance metadata."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default="1.0.0", description="Metadata schema version")
    listing_id: str = Field(description="Listing ID")
    source_url: str = Field(description="Original URL or source file path")
    archived_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the archival run")
    archiver_version: str = Field(description="Version of property-archiver")
    fetch_mode: str = Field(default="http", description="'http' for live crawl or 'file' for local snapshot")
    http_status: int | None = Field(default=None, description="HTTP status code if fetched via network")
    response_headers: dict[str, str] = Field(default_factory=dict, description="Captured HTTP response headers")
    fetch_duration_sec: float | None = Field(default=None, description="Duration in seconds for fetch operation")
    total_images_discovered: int = Field(default=0, description="Number of images discovered in HTML")
    total_images_archived: int = Field(default=0, description="Number of images successfully archived")
    total_archive_size_bytes: int = Field(default=0, description="Total size in bytes of all files in archive")
    content_fingerprint: str | None = Field(default=None, description="Semantic fingerprint of the listing")
