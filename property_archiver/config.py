"""
Configuration management for Property Archiver.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArchiverSettings(BaseSettings):
    """Global configuration settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="ARCHIVER_",
        env_file=".env",
        extra="ignore"
    )

    archive_dir: Path = Field(
        default=Path("./archive"),
        description="Base directory for storing listing archives"
    )
    user_agent: str = Field(
        default="PropertyArchiver/1.0 (+https://github.com/data-eng/property-archiver; archival research)",
        description="User-Agent header sent with HTTP requests"
    )
    request_timeout_sec: float = Field(
        default=25.0,
        description="Timeout for HTTP requests in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of HTTP request retries"
    )
    retry_backoff_factor: float = Field(
        default=1.5,
        description="Exponential backoff factor for retries"
    )
    rate_limit_delay_sec: float = Field(
        default=1.0,
        description="Polite delay between consecutive requests to the same host"
    )
    max_concurrency: int = Field(
        default=4,
        description="Maximum concurrent image downloads"
    )
    max_response_size_bytes: int = Field(
        default=50 * 1024 * 1024,  # 50 MB
        description="Maximum allowed HTTP response body size to prevent resource exhaustion"
    )
    download_images: bool = Field(
        default=True,
        description="Whether to download and archive listing images"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to enforce SSL certificate verification"
    )
    allowed_domains: list[str] = Field(
        default=[
            "www.privateproperty.co.za",
            "privateproperty.co.za",
            "images.pp.co.za",
            "images.privateproperty.co.za",
        ],
        description="Allowed hostnames for fetching to prevent SSRF"
    )
    allow_custom_domains: bool = Field(
        default=False,
        description="If True, allows any public non-private domain"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )


# Default shared settings instance
settings = ArchiverSettings()
