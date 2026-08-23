"""
Central configuration and runtime settings for Property Archiver.
"""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArchiverSettings(BaseSettings):
    """Runtime configuration model with validation and env-var overrides."""
    model_config = SettingsConfigDict(
        env_prefix="ARCHIVER_",
        env_file=".env",
        extra="ignore"
    )

    # Core Directories
    archive_dir: Path = Field(
        default=Path("./archive"),
        description="Root directory where all listings and assets are archived"
    )
    archive_layout: Literal["flat", "hierarchical"] = Field(
        default="flat",
        description="Storage directory layout: 'flat' (listings/<id>) or 'hierarchical' (listings/<prov>/<area>/<suburb>/<id>)"
    )

    # Network & Rate Limiting
    request_timeout_sec: float = Field(default=25.0, description="HTTP socket and connect timeout in seconds")
    rate_limit_delay_sec: float = Field(default=1.0, description="Polite delay between consecutive portal requests")
    max_retries: int = Field(default=3, description="Maximum HTTP retry attempts on transient network failures")
    retry_backoff_factor: float = Field(default=1.5, description="Exponential multiplier for retry wait times")

    # Media Downloader
    download_images: bool = Field(default=True, description="Whether to fetch and archive high-resolution listing images")
    image_concurrency: int = Field(default=6, description="Number of parallel worker threads for asset downloads")
    max_image_dimension: int = Field(default=1600, description="Preferred resolution cap for preserved photos")

    # Browser & User-Agent Identity
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 PropertyArchiver/1.0",
        description="Custom User-Agent header sent with outgoing requests"
    )


# Singleton instance
settings = ArchiverSettings()
