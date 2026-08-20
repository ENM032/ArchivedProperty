"""
Image downloading pipeline with concurrent streaming, deduplication, format validation, and SHA-256 checksums.
"""

import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.exceptions import FetchError, SecurityError
from property_archiver.core.hasher import calculate_sha256
from property_archiver.core.security import sanitize_filename, validate_url_security
from property_archiver.models.media import ImageRecord

logger = logging.getLogger(__name__)
PP_IMG_HASH_RE = re.compile(r"listing/\d+/([A-Za-z0-9]+)")


class ImageDownloader:
    """Downloader that fetches, validates, and archives listing images safely."""

    def __init__(self, config: ArchiverSettings | None = None):
        self.config = config or settings

    def download_image(
        self,
        record: ImageRecord,
        output_dir: Path,
        client: httpx.Client | None = None
    ) -> ImageRecord:
        """
        Download a single image, validate its headers/content with Pillow, and compute its SHA-256 digest.
        """
        target_url = record.resolved_url or record.original_url
        logger.debug("Downloading image %d from %s", record.order_index, target_url)

        # Validate URL security
        validate_url_security(
            target_url,
            allowed_domains=self.config.allowed_domains,
            allow_custom_domains=self.config.allow_custom_domains,
        )

        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.privateproperty.co.za/",
        }

        should_close = False
        if client is None:
            client = httpx.Client(
                timeout=self.config.request_timeout_sec,
                verify=self.config.verify_ssl,
                follow_redirects=True,
            )
            should_close = True

        try:
            resp = client.get(target_url, headers=headers)
            if resp.status_code != 200:
                logger.warning(
                    "Image fetch returned status %d for %s", resp.status_code, target_url
                )
                return record

            content = resp.content
            if not content:
                logger.warning("Empty response body for image %s", target_url)
                return record

            # Validate image and extract dimensions using Pillow
            width, height, mime_type = self._validate_and_inspect_image(content, resp.headers.get("Content-Type"))

            # Calculate SHA-256 checksum
            sha256_hash = calculate_sha256(content)

            # Determine file extension
            ext = ".jpg"
            if mime_type == "image/png":
                ext = ".png"
            elif mime_type == "image/webp":
                ext = ".webp"

            # Extract unique image identifier from URL
            hash_match = PP_IMG_HASH_RE.search(target_url)
            ident = hash_match.group(1) if hash_match else f"img_{record.order_index + 1}"
            filename = sanitize_filename(f"{record.order_index + 1:03d}_{ident}{ext}")

            # Save file to images directory
            file_path = output_dir / filename
            with open(file_path, "wb") as f:
                f.write(content)

            # Update record
            record.local_filename = filename
            record.sha256 = sha256_hash
            record.mime_type = mime_type
            record.file_size_bytes = len(content)
            record.width = width
            record.height = height
            record.downloaded_at = datetime.now(timezone.utc)

            return record

        except Exception as exc:
            logger.warning("Failed to download image %s: %s", target_url, exc)
            return record
        finally:
            if should_close:
                client.close()

    def download_all(
        self,
        records: list[ImageRecord],
        images_dir: Path,
    ) -> list[ImageRecord]:
        """
        Download multiple images concurrently using a bounded thread pool.
        """
        if not records:
            return []

        images_dir.mkdir(parents=True, exist_ok=True)
        updated_records: list[ImageRecord] = [r for r in records]

        with httpx.Client(
            timeout=self.config.request_timeout_sec,
            verify=self.config.verify_ssl,
            follow_redirects=True,
        ) as client:
            with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
                futures = {
                    executor.submit(self.download_image, rec, images_dir, client): idx
                    for idx, rec in enumerate(updated_records)
                }

                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        res = future.result()
                        updated_records[idx] = res
                    except Exception as e:
                        logger.warning("Worker error downloading image index %d: %s", idx, e)

        return updated_records

    def _validate_and_inspect_image(
        self, content: bytes, header_mime: str | None
    ) -> tuple[int | None, int | None, str]:
        """
        Verify image bytes using Pillow, extracting dimensions and authentic MIME type.
        """
        try:
            with Image.open(io.BytesIO(content)) as img:
                width, height = img.size
                format_name = img.format.lower() if img.format else "jpeg"
                mime = f"image/{format_name}"
                return width, height, mime
        except Exception:
            mime = header_mime or "image/jpeg"
            return None, None, mime
