"""
Resilient, secure HTTP fetcher with retries, jitter, polite rate limiting, and SSRF validation.
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.exceptions import (
    FetchError,
    RateLimitExceededError,
    ResourceExhaustionError,
    SSRFError,
)
from property_archiver.core.security import validate_url_security

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of an HTTP fetch operation."""
    url: str
    status_code: int
    content: bytes
    text: str
    headers: dict[str, str]
    duration_sec: float
    is_live: bool = True


class Fetcher:
    """Production-grade HTTP client enforcing safety, bounded retries, and rate limits."""

    def __init__(self, config: ArchiverSettings | None = None):
        self.config = config or settings
        self._last_request_time: dict[str, float] = {}

    def _enforce_rate_limit(self, hostname: str) -> None:
        """Enforce a polite delay between consecutive requests to the same domain."""
        if self.config.rate_limit_delay_sec <= 0:
            return

        now = time.time()
        last_time = self._last_request_time.get(hostname, 0.0)
        elapsed = now - last_time
        if elapsed < self.config.rate_limit_delay_sec:
            sleep_time = self.config.rate_limit_delay_sec - elapsed
            time.sleep(sleep_time)

        self._last_request_time[hostname] = time.time()

    def fetch_url(self, url: str) -> FetchResult:
        """
        Fetch a URL safely with SSRF validation, rate limiting, and exponential backoff.
        """
        # Step 1: Validate URL security (SSRF prevention)
        validated_url = validate_url_security(
            url,
            allowed_domains=self.config.allowed_domains,
            allow_custom_domains=self.config.allow_custom_domains,
        )

        hostname = urlparse(validated_url).hostname or "unknown"
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-ZA,en-GB;q=0.9,en;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        retries = 0
        max_retries = self.config.max_retries
        backoff = self.config.retry_backoff_factor

        while True:
            self._enforce_rate_limit(hostname)
            start_time = time.time()

            try:
                with httpx.Client(
                    timeout=self.config.request_timeout_sec,
                    verify=self.config.verify_ssl,
                    follow_redirects=True,
                ) as client:
                    response = client.get(validated_url, headers=headers)
                    duration = time.time() - start_time

                    # Check for rate limiting
                    if response.status_code == 429:
                        if retries < max_retries:
                            retries += 1
                            sleep_duration = (backoff ** retries) + random.uniform(0.5, 1.5)
                            logger.warning(
                                "Rate limited (429) fetching %s. Retrying (%d/%d) in %.2fs...",
                                validated_url, retries, max_retries, sleep_duration
                            )
                            time.sleep(sleep_duration)
                            continue
                        raise RateLimitExceededError(
                            f"HTTP 429 Too Many Requests after {max_retries} retries.",
                            status_code=429,
                            url=validated_url
                        )

                    # Check for server errors
                    if response.status_code >= 500:
                        if retries < max_retries:
                            retries += 1
                            sleep_duration = (backoff ** retries) + random.uniform(0.5, 1.0)
                            logger.warning(
                                "Server error (%d) fetching %s. Retrying (%d/%d) in %.2fs...",
                                response.status_code, validated_url, retries, max_retries, sleep_duration
                            )
                            time.sleep(sleep_duration)
                            continue
                        raise FetchError(
                            f"HTTP error {response.status_code} fetching {validated_url}.",
                            status_code=response.status_code,
                            url=validated_url
                        )

                    # Validate response size
                    content_length = len(response.content)
                    if content_length > self.config.max_response_size_bytes:
                        raise ResourceExhaustionError(
                            f"Response size ({content_length} bytes) exceeds limit of "
                            f"{self.config.max_response_size_bytes} bytes."
                        )

                    return FetchResult(
                        url=str(response.url),
                        status_code=response.status_code,
                        content=response.content,
                        text=response.text,
                        headers=dict(response.headers),
                        duration_sec=duration,
                        is_live=True,
                    )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if retries < max_retries:
                    retries += 1
                    sleep_duration = (backoff ** retries) + random.uniform(0.5, 1.0)
                    logger.warning(
                        "Network error (%s) fetching %s. Retrying (%d/%d) in %.2fs...",
                        type(exc).__name__, validated_url, retries, max_retries, sleep_duration
                    )
                    time.sleep(sleep_duration)
                    continue
                raise FetchError(
                    f"Failed to fetch {validated_url} after {max_retries} attempts: {exc}",
                    url=validated_url
                ) from exc
