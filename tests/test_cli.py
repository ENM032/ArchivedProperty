"""
Tests for Click CLI commands (fetch, inspect, validate, tree, reorganize, edit, delete).
"""

from pathlib import Path
from click.testing import CliRunner
import pytest

from property_archiver.cli import main
from property_archiver.storage.reader import ArchiveReader


def test_cli_fetch_edit_and_delete(sample_html_path: Path, tmp_path: Path):
    runner = CliRunner()
    
    # 1. Fetch
    res_fetch = runner.invoke(main, [
        "fetch",
        str(sample_html_path),
        "--output", str(tmp_path),
        "--no-images"
    ])
    assert res_fetch.exit_code == 0
    assert "Listing Successfully Archived" in res_fetch.output

    archive_listing = ArchiveReader.find_listing_dir(tmp_path, "T4710876")
    assert archive_listing is not None
    assert archive_listing.exists()

    # 2. Edit
    res_edit = runner.invoke(main, [
        "edit",
        "T4710876",
        "--status", "sold",
        "--notes", "CLI Edited Note",
        "--tags", "Shortlisted, Prime",
        "--rating", "5",
        "--archive-dir", str(tmp_path)
    ])
    assert res_edit.exit_code == 0
    assert "Successfully updated archive T4710876" in res_edit.output
    assert "SOLD" in res_edit.output

    # 3. Delete with --yes
    res_del = runner.invoke(main, [
        "delete",
        "T4710876",
        "--yes",
        "--archive-dir", str(tmp_path)
    ])
    assert res_del.exit_code == 0
    assert "Successfully deleted archive: T4710876" in res_del.output
    assert ArchiveReader.find_listing_dir(tmp_path, "T4710876") is None
