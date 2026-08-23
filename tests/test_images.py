"""
Tests for ImageDownloader and smart image caching.
"""

from pathlib import Path
import pytest

from property_archiver.images.downloader import ImageDownloader
from property_archiver.models.media import ImageRecord


def test_smart_image_cache_hit(tmp_path: Path):
    downloader = ImageDownloader()

    existing_dir = tmp_path / "existing_images"
    existing_dir.mkdir()
    sample_img_file = existing_dir / "001_ABC123XYZ.jpg"
    # Write a tiny valid 1x1 JPEG
    tiny_jpeg = bytes.fromhex(
        "ffd8ffe000104a46494600010101004800480000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffda0008010100003f007f00ffd9"
    )
    sample_img_file.write_bytes(tiny_jpeg)

    staging_dir = tmp_path / "staging_images"
    staging_dir.mkdir()

    record = ImageRecord(
        order_index=0,
        original_url="https://images.pp.co.za/listing/123/ABC123XYZ/600/400/contain/jpegorpng",
        resolved_url="https://images.pp.co.za/listing/123/ABC123XYZ/1600/1066/contain/jpegorpng",
    )

    # Calling download_all with existing_images_dir should reuse the local file without HTTP request
    results = downloader.download_all([record], staging_dir, existing_images_dir=existing_dir)
    assert len(results) == 1
    assert results[0].local_filename is not None
    assert results[0].sha256 is not None
    assert (staging_dir / results[0].local_filename).exists()
    assert (staging_dir / results[0].local_filename).read_bytes() == tiny_jpeg
