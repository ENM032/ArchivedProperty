"""
Tests for Click CLI commands.
"""

from pathlib import Path
from click.testing import CliRunner

from property_archiver.cli import main


def test_cli_fetch_local_file(sample_html_path: Path, tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, [
        "fetch",
        str(sample_html_path),
        "--output", str(tmp_path),
        "--no-images"
    ])
    assert result.exit_code == 0
    assert "Listing Successfully Archived" in result.output

    # Check directory created
    archive_listing = tmp_path / "listings" / "T4710876"
    assert archive_listing.exists()
    assert (archive_listing / "listing.json").exists()
    assert (archive_listing / "checksums.json").exists()

    # Test inspect command
    inspect_res = runner.invoke(main, ["inspect", str(archive_listing)])
    assert inspect_res.exit_code == 0
    assert "T4710876" in inspect_res.output
    assert "4 Bedroom House in Rivonia" in inspect_res.output

    # Test validate command
    validate_res = runner.invoke(main, ["validate", str(archive_listing)])
    assert validate_res.exit_code == 0
    assert "integrity verified" in validate_res.output
