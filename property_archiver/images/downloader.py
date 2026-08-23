"""
Image downloading pipeline with concurrent streaming, smart deduplication/caching,
format validation, and SHA-256 checksums.
"""

import io
import logging
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import httpx
from PIL import Image

from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.exceptions import FetchError, SecurityError
from property_archiver.core.hasher import calculate_file_sha256, calculate_sha256
from property_archiver.core.security import sanitize_filename, validate_url_security
from property_archiver.models.media import ImageRecord

logger = logging.getLogger(__name__)
PP_IMG_HASH_RE = re.compile(r"listing/\d+/([A-Za-z0-9]+)")


class ImageDownloader:
    """Downloader that fetches, validates, caches, and archives listing images safely."""

    def __init__(self, config: ArchiverSettings | None = None):
        self.config = config or settings

    def download_image(
        self,
        record: ImageRecord,
        output_dir: Path,
        client: httpx.Client | None = None,
        existing_images_dir: Path | None = None,
    ) -> ImageRecord:
        """
        Download a single image, or reuse/copy from existing_images_dir if hash matches.
        """
        target_url = record.resolved_url or record.original_url
        logger.debug("Processing image %d from %s", record.order_index, target_url)

        # Extract unique image identifier from URL
        hash_match = PP_IMG_HASH_RE.search(target_url)
        ident = hash_match.group(1) if hash_match else f"img_{record.order_index + 1}"

        # Step 1: Check Local Cache / Existing Archive
        if existing_images_dir and existing_images_dir.exists():
            for existing_file in existing_images_dir.iterdir():
                if existing_file.is_file() and f"_{ident}" in existing_file.name and existing_file.stat().st_size > 0:
                    try:
                        ext = existing_file.suffix or ".jpg"
                        target_filename = sanitize_filename(f"{record.order_index + 1:03d}_{ident}{ext}")
                        dest_path = output_dir / target_filename
                        shutil.copy2(existing_file, dest_path)

                        # Inspect local cached image
                        sha256_hash = calculate_file_sha256(dest_path)
                        with open(dest_path, "rb") as f:
                            content = f.read()
                        width, height, mime_type = self._validate_and_inspect_image(content, None)

                        record.local_filename = target_filename
                        record.sha256 = sha256_hash
                        record.mime_type = mime_type
                        record.file_size_bytes = len(content)
                        record.width = width
                        record.height = height
                        record.downloaded_at = datetime.now(timezone.utc)
                        logger.debug("Cache hit for image %s -> %s", ident, target_filename)
                        return record
                    except Exception as exc:
                        logger.debug("Failed reusing cached image %s, falling back to HTTP: %s", existing_file.name, exc)

        # Step 2: Fallback to HTTP download
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
                logger.warning("Image fetch returned status %d for %s", resp.status_code, target_url)
                return record

            content = resp.content
            if not content:
                logger.warning("Empty response body for image %s", target_url)
                return record

            width, height, mime_type = self._validate_and_inspect_image(content, resp.headers.get("Content-Type"))
            sha256_hash = calculate_sha256(content)

            ext = ".jpg"
            if mime_type == "image/png":
                ext = ".png"
            elif mime_type == "image/webp":
                ext = ".webp"

            filename = sanitize_filename(f"{record.order_index + 1:03d}_{ident}{ext}")
            file_path = output_dir / filename
            with open(file_path, "wb") as f:
                f.write(content)

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
        existing_images_dir: Path | None = None,
    ) -> list[ImageRecord]:
        """
        Download multiple images concurrently with smart local cache deduplication.
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
                    executor.submit(self.download_image, rec, images_dir, client, existing_images_dir): idx
                    for idx, rec in enumerate(updated_records)
                }

                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        res = future.result()
                        updated_records[idx] = res
                    except Exception as e:
                        logger.warning("Worker error processing image index %d: %s", idx, e)

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
