"""
Pytest fixtures and configuration.
"""

from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_html_path() -> Path:
    return FIXTURES_DIR / "sample_listing.html"


@pytest.fixture
def sample_html_content(sample_html_path: Path) -> str:
    with open(sample_html_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


@pytest.fixture
def sample_url() -> str:
    return "https://www.privateproperty.co.za/for-sale/gauteng/johannesburg/sandton/rivonia/13-winston-avenue/T4710876"


@pytest.fixture
def malformed_html_content() -> str:
    return """<!DOCTYPE html>
    <html>
      <head><title>Incomplete Property</title></head>
      <body>
        <h1>Just a Title Without Data</h1>
        <p>No schema, no images, no price.</p>
      </body>
    </html>"""
