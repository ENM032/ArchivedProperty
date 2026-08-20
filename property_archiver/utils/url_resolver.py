"""
Smart input resolver for Property Archiver.
Translates short listing IDs (e.g. 'T4710876', '4710876'), partial URLs,
and file globs into standardized target descriptors.
"""

import glob
import re
from pathlib import Path
from urllib.parse import urlparse

# Matches short listing ID formats like 'T4710876', 't12345', '10524708', '/T4710876'
SHORT_ID_RE = re.compile(r"^/?(T?\d+)/?$", re.I)


def is_short_listing_id(input_str: str) -> bool:
    """Check if the string matches a standalone listing ID pattern."""
    clean = input_str.strip()
    return bool(SHORT_ID_RE.match(clean))


def resolve_short_id(listing_id: str, portal_base: str = "https://www.privateproperty.co.za") -> str:
    """
    Resolve a short listing ID (e.g. 'T4710876') into a canonical portal URL.
    Private Property redirects https://www.privateproperty.co.za/<ID> to the full canonical path.
    """
    clean_id = listing_id.strip().strip("/").upper()
    return f"{portal_base.rstrip('/')}/{clean_id}"


def resolve_input_targets(targets: list[str]) -> list[str]:
    """
    Expand and normalize a list of input target strings into standardized URLs or file paths.
    Supports:
    - Standalone listing IDs (e.g. 'T4710876' -> 'https://www.privateproperty.co.za/T4710876')
    - URLs without scheme (e.g. 'privateproperty.co.za/...' -> 'https://privateproperty.co.za/...')
    - Glob patterns (e.g. 'snapshots/*.html' -> list of file paths)
    - Full HTTP/HTTPS URLs
    - Local file paths
    """
    resolved: list[str] = []

    for raw_target in targets:
        target = raw_target.strip()
        if not target:
            continue

        # 1. Check if it's a glob pattern or existing local file
        if any(char in target for char in ("*", "?", "[")):
            matched_files = glob.glob(target)
            if matched_files:
                resolved.extend(matched_files)
                continue

        if Path(target).exists():
            resolved.append(str(Path(target).resolve()))
            continue

        # 2. Check if it's a short listing ID (e.g. 'T4710876')
        if is_short_listing_id(target):
            resolved.append(resolve_short_id(target))
            continue

        # 3. Check if it's a URL missing http(s) scheme
        if target.startswith("www.") or target.startswith("privateproperty.co.za"):
            target = f"https://{target}"

        # 4. Standard URL
        parsed = urlparse(target)
        if parsed.scheme in ("http", "https"):
            resolved.append(target)
        else:
            # Fallback as literal target
            resolved.append(target)

    return resolved
