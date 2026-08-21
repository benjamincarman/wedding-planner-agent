"""Unit tests for wedding planning tools, schemas, and guided error handling."""

import pytest
from wedding_planner.tools.venue_tools import search_wedding_venues, verify_venue_distance
from wedding_planner.tools.budget_tools import calculate_budget_allocation
from wedding_planner.tools.outreach_tools import stage_vendor_inquiry_email


def test_venue_search_guided_error_unsupported_city():
    result = search_wedding_venues(
        city="Honolulu",
        guest_count=100,
        max_budget_usd=10000,
    )
    assert result["status"] == "GUIDED_ERROR"
    assert result["matched_count"] == 0
    assert "No venues found in 'Honolulu'" in result["message"]
    assert "Austin" in result["message"]


def test_venue_search_guided_error_tight_budget():
    result = search_wedding_venues(
        city="Napa Valley",
        guest_count=100,
        max_budget_usd=2000,  # Napa starts at $9000
    )
    assert result["status"] == "GUIDED_ERROR"
    assert "below minimum venue rental" in result["message"]


def test_verify_venue_distance_within_radius():
    result = verify_venue_distance(
        origin_city="Akron, OH",
        destination_venue_or_city="Stan Hywet Hall & Gardens",
        max_radius_miles=50.0,
    )
    assert result["status"] == "SUCCESS"
    assert result["within_radius"] is True
    assert result["distance_miles"] < 50.0
    assert result["estimated_drive_time_minutes"] > 0


def test_verify_venue_distance_exceeds_radius():
    result = verify_venue_distance(
        origin_city="Akron, OH",
        destination_venue_or_city="Columbus, OH",
        max_radius_miles=50.0,
    )
    assert result["status"] == "GUIDED_ERROR"
    assert result["within_radius"] is False
    assert result["distance_miles"] > 50.0
    assert "exceeds" in result["message"]


def test_budget_allocation_custom_priorities():
    result = calculate_budget_allocation(
        total_budget_usd=40000,
        guest_count=100,
        priorities=["Photography", "Catering"],
    )
    assert result["status"] == "SUCCESS"
    assert result["total_budget_usd"] == 40000
    assert result["estimated_cost_per_guest_usd"] == 400.0
    assert result["feasibility_assessment"] == "Comfortable"


def test_stage_vendor_inquiry_email_hitl():
    result = stage_vendor_inquiry_email(
        vendor_name="The Greenhouse at Driftwood",
        recipient_email="inquiries@greenhousedriftwood.com",
        wedding_date="November 7, 2026",
        estimated_guest_count=140,
        budget_range_usd="$14,000 - $18,000",
        specific_questions=["Is there a preferred vendor list for catering?"],
    )
    assert result["status"] == "STAGED_FOR_APPROVAL"
    assert result["requires_human_confirmation"] is True
    assert "The Greenhouse at Driftwood" in result["staged_email_body"]
    assert "preferred vendor list" in result["staged_email_body"]
