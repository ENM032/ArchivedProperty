"""
Comprehensive tests for Click CLI commands (fetch, inspect, validate, tree, reorganize, compare, export, batch, edit, delete).
"""

import json
from pathlib import Path
from click.testing import CliRunner
import pytest

from property_archiver.cli import main
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter
from property_archiver.models.listing import ListingRecord
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.property_details import LocationInfo, PriceInfo, PropertyFeatures


@pytest.fixture
def populated_archive(tmp_path: Path) -> Path:
    """Fixture creating two structured archives for CLI testing."""
    writer = ArchiveWriter()
    
    # 1. Listing 1 in Gauteng / Sandton / Rivonia
    rec1 = ListingRecord(
        listing_id="T4710876",
        canonical_url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/house/T4710876",
        title="4 Bedroom House in Rivonia",
        price=PriceInfo(amount=4999000.0, formatted_display="R 4 999 000"),
        location=LocationInfo(province="Gauteng", region="Sandton", suburb="Rivonia", latitude=-26.0437, longitude=28.0554),
        features=PropertyFeatures(bedrooms=4, bathrooms=3, garages=2),
        listing_status="active"
    )
    meta1 = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T4710876",
        source_url=rec1.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )
    writer.write_archive(rec1, "<html><body>Listing 1</body></html>", meta1, output_base_dir=tmp_path)

    # 2. Listing 2 in Western Cape / Cape Town / Camps Bay
    rec2 = ListingRecord(
        listing_id="T5599999",
        canonical_url="https://www.privateproperty.co.za/for-sale/western-cape/cape-town/camps-bay/villa/T5599999",
        title="5 Bedroom Luxury Villa in Camps Bay",
        price=PriceInfo(amount=25000000.0, formatted_display="R 25 000 000"),
        location=LocationInfo(province="Western Cape", region="Cape Town", suburb="Camps Bay", latitude=-33.9510, longitude=18.3780),
        features=PropertyFeatures(bedrooms=5, bathrooms=5, garages=3),
        listing_status="under_offer",
        is_under_offer=True
    )
    meta2 = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T5599999",
        source_url=rec2.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )
    writer.write_archive(rec2, "<html><body>Listing 2</body></html>", meta2, output_base_dir=tmp_path)

    return tmp_path


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


def test_cli_inspect_and_validate(populated_archive: Path):
    runner = CliRunner()
    dir1 = ArchiveReader.find_listing_dir(populated_archive, "T4710876")
    assert dir1 is not None

    # 1. Inspect
    res_inspect = runner.invoke(main, ["inspect", str(dir1)])
    assert res_inspect.exit_code == 0
    assert "4 Bedroom House in Rivonia" in res_inspect.output
    assert "Gauteng" in res_inspect.output

    # 2. Validate
    res_val = runner.invoke(main, ["validate", str(dir1)])
    assert res_val.exit_code == 0
    assert "Archive integrity verified" in res_val.output


def test_cli_tree_commands(populated_archive: Path):
    runner = CliRunner()

    # 1. Complete Tree
    res_tree = runner.invoke(main, ["tree", "--archive-dir", str(populated_archive)])
    assert res_tree.exit_code == 0
    assert "Gauteng" in res_tree.output
    assert "Western Cape" in res_tree.output
    assert "Rivonia" in res_tree.output
    assert "Camps Bay" in res_tree.output

    # 2. Filtered by Province
    res_tree_gauteng = runner.invoke(main, ["tree", "--province", "Gauteng", "--archive-dir", str(populated_archive)])
    assert res_tree_gauteng.exit_code == 0
    assert "Gauteng" in res_tree_gauteng.output
    assert "Western Cape" not in res_tree_gauteng.output

    # 3. Filtered by Status
    res_tree_offer = runner.invoke(main, ["tree", "--status", "under_offer", "--archive-dir", str(populated_archive)])
    assert res_tree_offer.exit_code == 0
    assert "Camps Bay" in res_tree_offer.output


def test_cli_compare_command(populated_archive: Path):
    runner = CliRunner()
    dir1 = ArchiveReader.find_listing_dir(populated_archive, "T4710876")
    dir2 = ArchiveReader.find_listing_dir(populated_archive, "T5599999")
    assert dir1 and dir2

    res_comp = runner.invoke(main, ["compare", str(dir1), str(dir2)])
    assert res_comp.exit_code == 0
    assert "Comparing" in res_comp.output or "Changes Detected" in res_comp.output


def test_cli_export_command(populated_archive: Path, tmp_path: Path):
    runner = CliRunner()

    # 1. Export CSV
    csv_file = tmp_path / "cli_export.csv"
    res_csv = runner.invoke(main, ["export", "--format", "csv", "--output", str(csv_file), "--archive-dir", str(populated_archive)])
    assert res_csv.exit_code == 0
    assert csv_file.exists()

    # 2. Export SQLite
    sqlite_file = tmp_path / "cli_export.db"
    res_sql = runner.invoke(main, ["export", "--format", "sqlite", "--output", str(sqlite_file), "--archive-dir", str(populated_archive)])
    assert res_sql.exit_code == 0
    assert sqlite_file.exists()

    # 3. Export GeoJSON
    geojson_file = tmp_path / "cli_export.geojson"
    res_geo = runner.invoke(main, ["export", "--format", "geojson", "--output", str(geojson_file), "--archive-dir", str(populated_archive)])
    assert res_geo.exit_code == 0
    assert geojson_file.exists()

    # 4. Export JSONL
    jsonl_file = tmp_path / "cli_export.jsonl"
    res_jsonl = runner.invoke(main, ["export", "--format", "jsonl", "--output", str(jsonl_file), "--archive-dir", str(populated_archive)])
    assert res_jsonl.exit_code == 0
    assert jsonl_file.exists()


def test_cli_reorganize_command(tmp_path: Path):
    runner = CliRunner()

    # Create a flat archive
    flat_archive_dir = tmp_path / "flat_test_archive"
    writer = ArchiveWriter()
    rec = ListingRecord(
        listing_id="T_FLAT_1",
        canonical_url="https://test.com/T_FLAT_1",
        title="Flat House",
        price=PriceInfo(amount=1000000.0),
        location=LocationInfo(province="Gauteng", region="Midrand", suburb="Waterfall"),
        listing_status="active"
    )
    meta = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T_FLAT_1",
        source_url=rec.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )
    
    # Commit directly as flat directory
    staging_dir, _ = writer.create_staging_dir("T_FLAT_1", flat_archive_dir)
    flat_target = flat_archive_dir / "listings" / "T_FLAT_1"
    flat_target.parent.mkdir(parents=True, exist_ok=True)
    (staging_dir / "raw.html").write_text("<html>test</html>", encoding="utf-8")
    (staging_dir / "listing.json").write_text(rec.model_dump_json(), encoding="utf-8")
    (staging_dir / "metadata.json").write_text(meta.model_dump_json(), encoding="utf-8")
    staging_dir.rename(flat_target)

    # Test reorganize --dry-run
    res_dry = runner.invoke(main, ["reorganize", "--layout", "hierarchical", "--dry-run", "--archive-dir", str(flat_archive_dir)])
    assert res_dry.exit_code == 0
    assert "DRY RUN MODE" in res_dry.output or "Planned" in res_dry.output

    # Test live reorganize
    res_live = runner.invoke(main, ["reorganize", "--layout", "hierarchical", "--archive-dir", str(flat_archive_dir)])
    assert res_live.exit_code == 0
    assert "Successfully reorganized" in res_live.output


def test_cli_batch_fetch(sample_html_path: Path, tmp_path: Path):
    runner = CliRunner()
    
    # Create batch list file
    batch_file = tmp_path / "batch_targets.txt"
    batch_file.write_text(f"{sample_html_path}\n", encoding="utf-8")

    out_dir = tmp_path / "batch_archive"
    res_batch = runner.invoke(main, ["batch", str(batch_file), "--output", str(out_dir)])
    assert res_batch.exit_code == 0
    assert "Batch complete" in res_batch.output or "Archived" in res_batch.output


def test_cli_delete_cancelled(populated_archive: Path):
    runner = CliRunner()
    # User inputs 'n' to confirmation prompt
    res = runner.invoke(main, ["delete", "T4710876", "--archive-dir", str(populated_archive)], input="n\n")
    assert res.exit_code == 0
    assert "cancelled" in res.output.lower()
    assert ArchiveReader.find_listing_dir(populated_archive, "T4710876") is not None


def test_cli_error_handlers(populated_archive: Path):
    runner = CliRunner()

    # 1. Non-existent listing inspection
    res_insp = runner.invoke(main, ["inspect", str(populated_archive / "non_existent_folder")])
    assert res_insp.exit_code != 0

    # 2. Non-existent listing deletion
    res_del = runner.invoke(main, ["delete", "NON_EXISTENT_ID", "--yes", "--archive-dir", str(populated_archive)])
    assert res_del.exit_code != 0
    assert "not found" in res_del.output.lower()

    # 3. Edit with no fields provided
    res_edit_empty = runner.invoke(main, ["edit", "T4710876", "--archive-dir", str(populated_archive)])
    assert "No updates specified" in res_edit_empty.output
