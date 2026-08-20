"""
Pydantic data models for media assets (images, videos).
"""

from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ImageRecord(BaseModel):
    """Metadata and integrity information for an archived listing image."""
    order_index: int = Field(description="Zero-based ordering of the image in the listing gallery")
    original_url: str = Field(description="Original image URL as discovered in the HTML")
    resolved_url: str = Field(description="Resolved high-resolution URL fetched for archiving")
    local_filename: str | None = Field(default=None, description="Filename stored within the images/ subfolder")
    sha256: str | None = Field(default=None, description="SHA-256 digest of the downloaded image file")
    mime_type: str | None = Field(default=None, description="Verified MIME type (e.g. image/jpeg, image/png)")
    file_size_bytes: int | None = Field(default=None, description="File size in bytes")
    width: int | None = Field(default=None, description="Pixel width of the image")
    height: int | None = Field(default=None, description="Pixel height of the image")
    alt_text: str | None = Field(default=None, description="Alt text or caption associated with the image")
    is_hero: bool = Field(default=False, description="True if this is the primary hero image")
    downloaded_at: datetime | None = Field(default=None, description="Timestamp when the image was archived")


class VideoRecord(BaseModel):
    """Metadata for embedded listing video."""
    provider: str = Field(description="Video provider (e.g. YouTube, Vimeo, Matterport)")
    url: str = Field(description="URL or embed source of the video")
    title: str | None = Field(default=None, description="Title of the video if available")
