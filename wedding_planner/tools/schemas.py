"""Strict Pydantic schemas defining inputs and outputs for all wedding planning tools."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, conint, confloat


# --- Venue Search Schemas ---
class VenueSearchInput(BaseModel):
    """Input parameters for searching wedding venues."""
    city: str = Field(
        ...,
        description="The target city or metropolitan area (e.g., 'Austin', 'Napa Valley', 'Denver', 'Miami').",
        examples=["Austin", "Napa Valley"],
    )
    guest_count: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Estimated number of attending wedding guests.",
        examples=[120],
    )
    max_budget_usd: float = Field(
        ...,
        gt=0,
        description="Maximum venue rental budget in USD.",
        examples=[15000.0],
    )
    outdoor_required: bool = Field(
        default=False,
        description="Whether outdoor ceremony or reception spaces are strictly required.",
    )
    style_preference: Optional[str] = Field(
        default=None,
        description="Preferred aesthetic (e.g., 'rustic', 'modern', 'ballroom', 'vineyard', 'waterfront').",
    )


class VenueItem(BaseModel):
    """Details of an individual wedding venue."""
    name: str = Field(..., description="Name of the venue.")
    city: str = Field(..., description="City location.")
    max_capacity: int = Field(..., description="Maximum guest capacity.")
    rental_fee_usd: float = Field(..., description="Base venue rental fee in USD.")
    estimated_total_usd: float = Field(..., description="Estimated total cost including standard food/beverage minimums.")
    style: str = Field(..., description="Architectural / aesthetic style.")
    has_outdoor_space: bool = Field(..., description="True if outdoor spaces are available.")
    allows_outside_catering: bool = Field(..., description="True if outside caterers are permitted.")
    contact_email: str = Field(..., description="Primary contact email for inquiries.")


class VenueSearchOutput(BaseModel):
    """Output structure returned from venue search operations."""
    status: str = Field(..., description="Execution status: 'SUCCESS' or 'GUIDED_ERROR'.")
    matched_count: int = Field(..., description="Total number of matching venues found.")
    venues: List[VenueItem] = Field(default_factory=list, description="List of matching venue options.")
    message: str = Field(..., description="Summary or guided recovery guidance for the agent.")


# --- Budget Allocation Schemas ---
class BudgetAllocationInput(BaseModel):
    """Input parameters for calculating wedding budget distribution."""
    total_budget_usd: float = Field(
        ...,
        gt=1000,
        description="Total overall wedding budget in USD.",
        examples=[35000.0],
    )
    guest_count: int = Field(
        ...,
        ge=1,
        description="Anticipated guest count.",
        examples=[120],
    )
    priorities: Optional[List[str]] = Field(
        default=None,
        description="Top priorities to allocate extra budget towards (e.g., ['photography', 'catering', 'music']).",
    )


class CategoryAllocation(BaseModel):
    """Budget allocation for a specific wedding expense category."""
    category: str = Field(..., description="Expense category name (e.g., 'Venue & Catering', 'Photography').")
    allocated_usd: float = Field(..., description="Dollar amount allocated.")
    percentage_of_total: float = Field(..., description="Percentage of total budget.")
    notes: str = Field(..., description="Planning guidance and trade-off considerations for this category.")


class BudgetAllocationOutput(BaseModel):
    """Output containing structured category allocations and feasibility metrics."""
    status: str = Field(..., description="Execution status: 'SUCCESS' or 'GUIDED_ERROR'.")
    total_budget_usd: float = Field(..., description="Total budget analyzed.")
    estimated_cost_per_guest_usd: float = Field(..., description="Estimated total spend per guest.")
    strategy_mode: str = Field(default="STANDARD_PERCENTAGE", description="Allocation strategy: 'STANDARD_PERCENTAGE' or 'UNBUNDLED_COMPONENT_TARGET'.")
    target_venue_rental_ceiling_usd: Optional[float] = Field(default=None, description="Recommended maximum venue rental fee to leave room for food/services.")
    target_catering_per_guest_usd: Optional[float] = Field(default=None, description="Recommended per-person food & beverage ceiling.")
    allocations: List[CategoryAllocation] = Field(default_factory=list, description="Category-by-category breakdown.")
    contingency_fund_usd: float = Field(..., description="Recommended emergency reserve (typically 5-10%).")
    feasibility_assessment: str = Field(..., description="Evaluation of budget feasibility for guest count.")
    message: str = Field(..., description="Summary or guided error instructions.")


# --- Geographic Distance Verification Schemas ---
class DistanceVerificationInput(BaseModel):
    """Input parameters for verifying venue distance and drive time from an anchor location."""
    origin_city: str = Field(..., description="The user's starting or anchor city/metro (e.g. 'Akron, OH' or 'Austin, TX').")
    destination_venue_or_city: str = Field(..., description="The destination venue or city to measure distance to.")
    max_radius_miles: float = Field(default=120.0, gt=0, description="Maximum acceptable driving radius in miles.")


class DistanceVerificationOutput(BaseModel):
    """Output verifying distance, drive time, and radius compliance."""
    status: str = Field(..., description="'SUCCESS' or 'GUIDED_ERROR'.")
    origin: str = Field(..., description="Resolved starting origin.")
    destination: str = Field(..., description="Resolved destination venue/city.")
    distance_miles: float = Field(..., description="Calculated driving distance in miles.")
    estimated_drive_time_minutes: int = Field(..., description="Estimated drive time in minutes.")
    within_radius: bool = Field(..., description="True if distance <= max_radius_miles.")
    message: str = Field(..., description="Summary evaluation or radius guidance.")


# --- Vendor Outreach & Human-in-the-Loop Schemas ---
class VendorInquiryInput(BaseModel):
    """Input for drafting and staging a vendor inquiry email."""
    vendor_name: str = Field(..., description="Name of the venue or vendor.")
    recipient_email: str = Field(..., description="Contact email address of the vendor.")
    wedding_date: str = Field(..., description="Target wedding date or season (e.g., 'October 17, 2026' or 'Fall 2026').")
    estimated_guest_count: int = Field(..., description="Estimated guest count.")
    budget_range_usd: str = Field(..., description="Target budget range for this service (e.g., '$10,000 - $14,000').")
    specific_questions: List[str] = Field(
        default_factory=list,
        description="Specific questions to ask the vendor (e.g., noise ordinances, outside catering policy).",
    )


class VendorInquiryOutput(BaseModel):
    """Output structure representing a staged inquiry requiring human approval."""
    status: str = Field(..., description="'STAGED_FOR_APPROVAL' or 'GUIDED_ERROR'.")
    requires_human_confirmation: bool = Field(
        default=True,
        description="Explicit flag enforcing that human review is required before email dispatch.",
    )
    staged_email_subject: str = Field(..., description="Generated subject line.")
    staged_email_body: str = Field(..., description="Generated email body content.")
    recipient: str = Field(..., description="Target recipient email.")
    approval_prompt: str = Field(
        ...,
        description="Instruction prompting the user to review and confirm or modify the draft.",
    )
