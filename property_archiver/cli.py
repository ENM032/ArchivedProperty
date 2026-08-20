"""
Click & Rich Command-Line Interface for Property Archiver.
"""

import logging
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from property_archiver import __version__
from property_archiver.config import settings
from property_archiver.core.change_detector import ChangeDetector
from property_archiver.core.exceptions import PropertyArchiverError
from property_archiver.core.fetcher import Fetcher
from property_archiver.extractors import get_extractor_for_url_or_html
from property_archiver.images.downloader import ImageDownloader
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter
from property_archiver.utils.clipboard import get_clipboard_text
from property_archiver.utils.url_resolver import resolve_input_targets

console = Console(safe_box=True, highlight=False)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@click.group()
@click.version_option(version=__version__, prog_name="property-archiver")
def main():
    """Property Archiver - Secure, resilient South African property listing archiver."""
    pass


def _fetch_single_target(target: str, output: str, no_images: bool, timeout: float, rate_limit: float, user_agent: str | None) -> bool:
    """Internal helper to fetch and archive a single resolved target."""
    cfg = settings.model_copy()
    cfg.archive_dir = Path(output)
    cfg.download_images = not no_images
    cfg.request_timeout_sec = timeout
    cfg.rate_limit_delay_sec = rate_limit
    if user_agent:
        cfg.user_agent = user_agent

    is_local_file = Path(target).exists()

    # Step 1: Ingestion
    console.print(f"[yellow]Ingesting source:[/yellow] [green]{target}[/green]")
    start_time = time.time()

    if is_local_file:
        with open(target, "rb") as f:
            raw_bytes = f.read()
        raw_html = raw_bytes.decode("utf-8", errors="ignore")
        url = f"file://{Path(target).resolve()}"
        http_status = 200
        headers = {}
        fetch_mode = "file"
        duration = time.time() - start_time
    else:
        fetcher = Fetcher(config=cfg)
        try:
            result = fetcher.fetch_url(target)
            raw_bytes = result.content
            raw_html = result.text
            url = result.url
            http_status = result.status_code
            headers = result.headers
            fetch_mode = "http"
            duration = result.duration_sec
        except Exception as exc:
            console.print(f"[bold red]Fetch failed for {target}:[/bold red] {exc}")
            return False

    # Step 2: Extraction
    extractor = get_extractor_for_url_or_html(url)
    try:
        listing = extractor.extract(raw_html, url)
    except Exception as exc:
        console.print(f"[bold red]Extraction failed for {target}:[/bold red] {exc}")
        return False

    status_str = f"Status: [bold cyan]{listing.listing_status.upper()}[/bold cyan]"
    if listing.status_badges:
        status_str += f" ({', '.join(listing.status_badges)})"
    console.print(f"[green]Data extracted for listing ID: {listing.listing_id}[/green] | {status_str}")

    # Prepare Staging Directory
    writer = ArchiveWriter(config=cfg)
    staging_dir, images_dir = writer.create_staging_dir(listing.listing_id, cfg.archive_dir)

    # Step 3: Images
    archived_images_count = 0
    if cfg.download_images and listing.images:
        console.print(f"[yellow]Downloading {len(listing.images)} gallery images...[/yellow]")
        downloader = ImageDownloader(config=cfg)
        listing.images = downloader.download_all(listing.images, images_dir)
        archived_images_count = sum(1 for img in listing.images if img.local_filename is not None)
        console.print(f"[green]Archived {archived_images_count}/{len(listing.images)} images.[/green]")

    # Step 4: Write Archive
    metadata = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id=listing.listing_id,
        source_url=url,
        archiver_version=__version__,
        fetch_mode=fetch_mode,
        http_status=http_status,
        response_headers=headers,
        fetch_duration_sec=duration,
        total_images_discovered=len(listing.images),
        total_images_archived=archived_images_count,
        content_fingerprint=listing.content_fingerprint,
    )

    try:
        archive_path = writer.commit_archive(
            staging_dir=staging_dir,
            listing=listing,
            raw_html=raw_bytes,
            metadata=metadata,
            output_base_dir=cfg.archive_dir
        )
    except Exception as exc:
        console.print(f"[bold red]Storage error for {target}:[/bold red] {exc}")
        return False

    # Display Summary Card
    badges_display = f" | Badges: {', '.join(listing.status_badges)}" if listing.status_badges else ""
    card_text = (
        f"[bold white]{listing.title or 'Property Listing'}[/bold white]\n"
        f"[cyan]ID:[/cyan] {listing.listing_id} | [cyan]Type:[/cyan] {listing.property_type or 'N/A'} | [cyan]Status:[/cyan] [bold]{listing.listing_status.upper()}[/bold]{badges_display}\n"
        f"[cyan]Price:[/cyan] {listing.price.formatted_display or 'N/A'}\n"
        f"[cyan]Location:[/cyan] {listing.location.street_address or ''}, {listing.location.suburb or ''}, {listing.location.city or ''}\n"
        f"[cyan]Specs:[/cyan] {listing.features.bedrooms or 0} Beds | {listing.features.bathrooms or 0} Baths | {listing.features.garages or 0} Garages | Erf: {listing.erf_size_m2 or 'N/A'} m2\n"
        f"[cyan]Images:[/cyan] {archived_images_count} archived / {len(listing.images)} found\n"
        f"[cyan]Archive Path:[/cyan] [green]{archive_path}[/green]"
    )
    console.print(Panel(
        card_text,
        title="[bold green] Listing Successfully Archived [/bold green]",
        expand=False
    ))
    return True


@main.command(name="fetch")
@click.argument("targets", nargs=-1, type=str)
@click.option("--clipboard", "-c", is_flag=True, default=False, help="Read listing URL or ID from system clipboard")
@click.option("--output", "-o", type=click.Path(), default="./archive", help="Output archive directory")
@click.option("--no-images", is_flag=True, default=False, help="Disable downloading of listing images")
@click.option("--timeout", type=float, default=25.0, help="HTTP request timeout in seconds")
@click.option("--rate-limit", type=float, default=1.0, help="Polite delay between requests in seconds")
@click.option("--user-agent", type=str, default=None, help="Custom User-Agent string")
def fetch_command(
    targets: tuple[str, ...],
    clipboard: bool,
    output: str,
    no_images: bool,
    timeout: float,
    rate_limit: float,
    user_agent: str | None
):
    """
    Fetch and archive listings from URLs, short IDs (e.g. 'T4710876'), files, or clipboard.

    Examples:
      property-archiver fetch T4710876
      property-archiver fetch https://www.privateproperty.co.za/...
      property-archiver fetch -c
      property-archiver fetch ./snapshots/*.html
    """
    console.print(f"[bold cyan]Property Archiver[/bold cyan] v{__version__}")

    raw_targets = list(targets)

    # If clipboard flag requested or no arguments provided, attempt reading clipboard
    if clipboard or not raw_targets:
        clip_text = get_clipboard_text()
        if clip_text:
            console.print(f"[cyan]Ingesting from clipboard:[/cyan] [dim]{clip_text}[/dim]")
            raw_targets.append(clip_text)
        elif not raw_targets:
            console.print("[bold red]No target provided and clipboard is empty.[/bold red]")
            console.print("Usage: [green]property-archiver fetch <URL_OR_ID>[/green] or [green]property-archiver fetch -c[/green]")
            sys.exit(1)

    # Resolve IDs, URLs, and Globs
    resolved = resolve_input_targets(raw_targets)
    if not resolved:
        console.print("[bold red]No valid targets found to archive.[/bold red]")
        sys.exit(1)

    console.print(f"Resolved [bold cyan]{len(resolved)}[/bold cyan] target(s) to archive.")

    success_count = 0
    for idx, target in enumerate(resolved, 1):
        if len(resolved) > 1:
            console.print(f"\n[bold cyan]--- Processing [{idx}/{len(resolved)}] ---[/bold cyan]")
        if _fetch_single_target(target, output, no_images, timeout, rate_limit, user_agent):
            success_count += 1

    if len(resolved) > 1:
        console.print(f"\n[bold green]Batch complete: {success_count}/{len(resolved)} listings archived successfully.[/bold green]")


@main.command(name="inspect")
@click.argument("archive_path", type=click.Path(exists=True))
def inspect_command(archive_path: str):
    """Inspect and display structured data from an existing archive."""
    path = Path(archive_path)
    try:
        listing = ArchiveReader.load_listing(path)
        metadata = ArchiveReader.load_metadata(path)
    except Exception as exc:
        console.print(f"[bold red]Failed to inspect archive:[/bold red] {exc}")
        sys.exit(1)

    table = Table(title=f"Archived Listing: {listing.listing_id}", show_header=True)
    table.add_column("Attribute", style="cyan", width=25)
    table.add_column("Value", style="white")

    table.add_row("Title", listing.title or "N/A")
    table.add_row("Listing ID", listing.listing_id)
    table.add_row("Portal", listing.portal_name)
    table.add_row("Status", listing.listing_status.upper())
    table.add_row("Badges", ", ".join(listing.status_badges) if listing.status_badges else "None")
    table.add_row("Under Offer?", "Yes" if listing.is_under_offer else "No")
    table.add_row("Sold?", "Yes" if listing.is_sold else "No")
    table.add_row("Price", listing.price.formatted_display or str(listing.price.amount))
    table.add_row("Rates & Taxes", f"R {listing.price.rates_and_taxes_monthly}" if listing.price.rates_and_taxes_monthly else "N/A")
    table.add_row("Address", f"{listing.location.street_address or ''}, {listing.location.suburb or ''}, {listing.location.city or ''}")
    table.add_row("Province / Country", f"{listing.location.province or ''}, {listing.location.country}")
    table.add_row("GPS Coordinates", f"{listing.location.latitude}, {listing.location.longitude}" if listing.location.latitude else "N/A")
    table.add_row("Bedrooms / Bathrooms", f"{listing.features.bedrooms} Beds / {listing.features.bathrooms} Baths")
    table.add_row("Garages / Lounges", f"{listing.features.garages} Garages / {listing.features.lounges} Lounges")
    table.add_row("Erf / Land Size", f"{listing.erf_size_m2} m2" if listing.erf_size_m2 else "N/A")
    table.add_row("Listing Date", str(listing.listing_date) if listing.listing_date else "N/A")
    table.add_row("Total Features", str(len(listing.features.raw_features_list)))
    table.add_row("Archived Images", str(len(listing.images)))
    table.add_row("Archived At", str(metadata.archived_at))
    table.add_row("Fingerprint", (listing.content_fingerprint or "")[:16] + "...")

    console.print(table)

    if listing.features.raw_features_list:
        console.print("\n[bold cyan]Features & Amenities:[/bold cyan]")
        console.print(", ".join(listing.features.raw_features_list))


@main.command(name="validate")
@click.argument("archive_path", type=click.Path(exists=True))
def validate_command(archive_path: str):
    """Verify cryptographic integrity (SHA-256) of all files in an archive."""
    path = Path(archive_path)
    console.print(f"Validating archive integrity for: [cyan]{path}[/cyan]...")

    is_valid, errors = ArchiveReader.validate_integrity(path)
    if is_valid:
        console.print("[bold green]Archive integrity verified. All SHA-256 checksums match.[/bold green]")
    else:
        console.print("[bold red]Archive validation failed:[/bold red]")
        for err in errors:
            console.print(f"  * [red]{err}[/red]")
        sys.exit(1)


@main.command(name="compare")
@click.argument("archive_a", type=click.Path(exists=True))
@click.argument("archive_b", type=click.Path(exists=True))
def compare_command(archive_a: str, archive_b: str):
    """Compare two archived listing snapshots and display changes."""
    diff = ChangeDetector.compare_archives(archive_a, archive_b)

    console.print(f"[bold cyan]Comparing Listings for ID: {diff.listing_id}[/bold cyan]\n")

    if diff.is_identical:
        console.print("[bold green]Snapshots are semantically IDENTICAL.[/bold green]")
        return

    console.print("[bold yellow]Listing Changes Detected:[/bold yellow]")
    if diff.price_changed:
        sign = "+" if (diff.price_diff or 0) > 0 else ""
        console.print(f"  * [bold]Price:[/bold] R {diff.old_price:,} -> R {diff.new_price:,} ({sign}{diff.price_diff:,})")
    if diff.status_changed:
        console.print(f"  * [bold]Status Transition:[/bold] [yellow]{diff.old_status}[/yellow] -> [bold green]{diff.new_status}[/bold green]")
    if diff.badges_added:
        console.print(f"  * [bold green]New Badges:[/bold green] {', '.join(diff.badges_added)}")
    if diff.badges_removed:
        console.print(f"  * [bold red]Removed Badges:[/bold red] {', '.join(diff.badges_removed)}")
    if diff.spec_changes:
        for spec in diff.spec_changes:
            console.print(f"  * [bold]Specification:[/bold] {spec}")
    if diff.added_features:
        console.print(f"  * [bold green]Added Features:[/bold green] {', '.join(diff.added_features)}")
    if diff.removed_features:
        console.print(f"  * [bold red]Removed Features:[/bold red] {', '.join(diff.removed_features)}")
    if diff.images_count_change[0] != diff.images_count_change[1]:
        console.print(f"  * [bold]Images Count:[/bold] {diff.images_count_change[0]} -> {diff.images_count_change[1]}")
    if diff.description_changed:
        console.print("  * [bold]Description:[/bold] Text content modified")


@main.command(name="batch")
@click.argument("file_list", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="./archive", help="Output archive directory")
def batch_command(file_list: str, output: str):
    """Archive multiple listings from a newline-separated file of URLs or IDs."""
    with open(file_list, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    console.print(f"[bold cyan]Starting batch archive for {len(urls)} target(s)...[/bold cyan]")
    fetch_command.callback(targets=tuple(urls), clipboard=False, output=output, no_images=False, timeout=25.0, rate_limit=1.0, user_agent=None)


if __name__ == "__main__":
    main()
