"""
Top-level canonical listing model with multi-agent support and land size normalization.
"""

from datetime import date, datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from property_archiver.models.media import ImageRecord, VideoRecord
from property_archiver.models.property_details import (
    AgentInfo,
    LocationInfo,
    PriceInfo,
    PropertyFeatures,
)


class ListingRecord(BaseModel):
    """Complete, normalized, versioned representation of a property listing."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default="1.0.0", description="Schema specification version")
    portal_name: str = Field(default="privateproperty.co.za", description="Source portal identifier")
    listing_id: str = Field(description="Unique listing identifier on the portal (e.g. 'T4710876')")
    canonical_url: str = Field(description="Canonical web URL of the listing")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp when data was parsed")
    
    # Core listing attributes
    title: str | None = Field(default=None, description="Headline title of the listing")
    property_type: str | None = Field(default=None, description="Property type (e.g. 'House', 'Apartment', 'Townhouse')")
    
    # Lifecycle & Status Tracking
    listing_status: str = Field(
        default="active",
        description="Normalized listing lifecycle status ('active', 'under_offer', 'sold', 'pending', 'withdrawn', 'unknown')"
    )
    status_badges: list[str] = Field(
        default_factory=list,
        description="Raw visual badge labels discovered on page (e.g. 'Under Offer', 'Reduced', 'On Show', 'Auction')"
    )
    is_under_offer: bool = Field(default=False, description="True if listing is currently marked Under Offer / Contract Pending")
    is_sold: bool = Field(default=False, description="True if listing is marked Sold")
    is_on_show: bool = Field(default=False, description="True if listing has an active On Show viewing scheduled")
    is_price_reduced: bool = Field(default=False, description="True if listing price was marked as reduced/discounted")
    on_show_details: dict[str, Any] | None = Field(default=None, description="Structured date/time metadata for On Show viewings")

    listing_date: date | None = Field(default=None, description="Publication or listing date")
    description: str | None = Field(default=None, description="Full textual property description")

    # Sizes
    erf_size_m2: float | None = Field(default=None, description="Land / Erf size normalized to square meters")
    land_size_raw: str | None = Field(default=None, description="Original raw land size string (e.g. '2.5 ha' or '1983 m²')")
    floor_size_m2: float | None = Field(default=None, description="Floor / Building size in square meters")

    # Sub-models
    price: PriceInfo = Field(default_factory=PriceInfo, description="Pricing and levy details")
    location: LocationInfo = Field(default_factory=LocationInfo, description="Address and GPS location")
    features: PropertyFeatures = Field(default_factory=PropertyFeatures, description="Extracted features and amenities")
    
    # Agents
    agent: AgentInfo | None = Field(default=None, description="Primary listing agent")
    co_agents: list[AgentInfo] = Field(default_factory=list, description="Additional co-listing agents and team members")
    
    # Media
    images: list[ImageRecord] = Field(default_factory=list, description="Preserved listing images")
    videos: list[VideoRecord] = Field(default_factory=list, description="Embedded video media")

    # Raw metadata preserved for lossless reproducibility
    raw_json_ld: list[dict[str, Any]] = Field(default_factory=list, description="Raw JSON-LD structures from the page")
    open_graph: dict[str, str] = Field(default_factory=dict, description="OpenGraph meta tags")
    meta_tags: dict[str, str] = Field(default_factory=dict, description="Standard HTML meta tags")

    # Fingerprint for change detection
    content_fingerprint: str | None = Field(default=None, description="SHA-256 hash of semantic listing data")
