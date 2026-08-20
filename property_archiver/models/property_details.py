"""
Pydantic data models for property specifications, location, pricing, and features.
"""

from datetime import date
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PriceInfo(BaseModel):
    """Pricing details and monthly costs."""
    model_config = ConfigDict(extra="allow")

    amount: float | None = Field(default=None, description="Listed asking price amount")
    currency: str = Field(default="ZAR", description="Currency ISO code (default ZAR)")
    formatted_display: str | None = Field(default=None, description="Original formatted price string (e.g. 'R 4 999 000')")
    rates_and_taxes_monthly: float | None = Field(default=None, description="Monthly rates and taxes in ZAR")
    levies_monthly: float | None = Field(default=None, description="Monthly body corporate levies in ZAR")


class LocationInfo(BaseModel):
    """Geographical and address details."""
    model_config = ConfigDict(extra="allow")

    street_address: str | None = Field(default=None, description="Street address (e.g. '13 Winston Avenue')")
    suburb: str | None = Field(default=None, description="Suburb name (e.g. 'Rivonia')")
    city: str | None = Field(default=None, description="City / Metropolitan area (e.g. 'Johannesburg')")
    region: str | None = Field(default=None, description="Region or municipality (e.g. 'Sandton')")
    province: str | None = Field(default=None, description="Province (e.g. 'Gauteng')")
    country: str = Field(default="South Africa", description="Country name")
    postal_code: str | None = Field(default=None, description="Postal code")
    latitude: float | None = Field(default=None, description="GPS Latitude coordinate")
    longitude: float | None = Field(default=None, description="GPS Longitude coordinate")
    breadcrumbs: list[str] = Field(default_factory=list, description="Hierarchical breadcrumb trail")


class AgentInfo(BaseModel):
    """Agent and real estate agency contact details."""
    model_config = ConfigDict(extra="allow")

    agent_name: str | None = Field(default=None, description="Name of the real estate agent")
    agency_name: str | None = Field(default=None, description="Name of the real estate agency/brand")
    agency_logo_url: str | None = Field(default=None, description="URL of the agency brand logo")
    agent_phone: str | None = Field(default=None, description="Contact telephone number")
    agent_email: str | None = Field(default=None, description="Contact email address")
    branch_name: str | None = Field(default=None, description="Agency branch name")


class PropertyFeatures(BaseModel):
    """Structured property features and amenities."""
    model_config = ConfigDict(extra="allow")

    # Counts & numerical specs
    bedrooms: float | None = Field(default=None, description="Number of bedrooms")
    bathrooms: float | None = Field(default=None, description="Number of bathrooms")
    en_suites: float | None = Field(default=None, description="Number of en-suite bathrooms")
    lounges: float | None = Field(default=None, description="Number of living rooms / lounges")
    dining_rooms: float | None = Field(default=None, description="Number of dining rooms")
    kitchens: float | None = Field(default=None, description="Number of kitchens")
    study_rooms: float | None = Field(default=None, description="Number of studies / home offices")
    garages: float | None = Field(default=None, description="Number of garage parking bays")
    open_parkings: float | None = Field(default=None, description="Number of open parking bays")
    covered_parkings: float | None = Field(default=None, description="Number of covered parking bays")

    # Common boolean amenities & features
    has_pool: bool | None = Field(default=None, description="Swimming pool")
    has_garden: bool | None = Field(default=None, description="Garden")
    has_security_post: bool | None = Field(default=None, description="Security post / guard house")
    has_access_gate: bool | None = Field(default=None, description="Automated access gate")
    has_alarm: bool | None = Field(default=None, description="Alarm system")
    has_intercom: bool | None = Field(default=None, description="Intercom system")
    has_fencing: bool | None = Field(default=None, description="Fenced boundary / walling")
    has_staff_quarters: bool | None = Field(default=None, description="Staff quarters / domestic accommodation")
    has_patio: bool | None = Field(default=None, description="Patio or deck")
    has_balcony: bool | None = Field(default=None, description="Balcony")
    has_built_in_cupboards: bool | None = Field(default=None, description="Built-in cupboards")
    has_walk_in_closet: bool | None = Field(default=None, description="Walk-in closet")
    has_kitchen: bool | None = Field(default=None, description="Kitchen")
    has_scullery: bool | None = Field(default=None, description="Scullery")
    has_laundry: bool | None = Field(default=None, description="Laundry room")
    has_entrance_hall: bool | None = Field(default=None, description="Entrance hall")
    has_family_tv_room: bool | None = Field(default=None, description="Family / TV room")
    has_fireplace: bool | None = Field(default=None, description="Fireplace")
    has_guest_toilet: bool | None = Field(default=None, description="Guest toilet / powder room")
    has_irrigation_system: bool | None = Field(default=None, description="Garden irrigation system")
    has_aircon: bool | None = Field(default=None, description="Air conditioning")
    has_storage: bool | None = Field(default=None, description="Storage room / shed")
    has_solar_inverter: bool | None = Field(default=None, description="Solar power or inverter system")
    is_pet_friendly: bool | None = Field(default=None, description="Pet friendly")
    is_furnished: bool | None = Field(default=None, description="Furnished")

    # Complete raw list and custom key-values
    raw_features_list: list[str] = Field(default_factory=list, description="All raw feature strings discovered in page")
    custom_details: dict[str, Any] = Field(default_factory=dict, description="Additional key-value specifications")
