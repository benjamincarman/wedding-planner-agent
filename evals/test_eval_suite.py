"""Automated Evaluation Suite executing regression tests against the Golden Dataset."""

import json
import os
import pytest
from wedding_planner.tools.venue_tools import search_wedding_venues
from wedding_planner.tools.budget_tools import calculate_budget_allocation
from wedding_planner.tools.outreach_tools import stage_vendor_inquiry_email
from wedding_planner.guardrails.policy_plugin import HITLPolicyPlugin, BudgetSafetyGuardrail


@pytest.fixture
def golden_dataset():
    filepath = os.path.join(os.path.dirname(__file__), "wedding_planner_eval_set_001.evalset.json")
    with open(filepath, "r") as f:
        return json.load(f)


def test_eval_case_001_austin_venue_search(golden_dataset):
    """TC_001: Golden eval test for venue search filtering."""
    case = next(c for c in golden_dataset["eval_cases"] if c["eval_case_id"] == "TC_001_AUSTIN_VENUE_SEARCH")
    params = case["expected_parameters"]

    result = search_wedding_venues(
        city=params["city"],
        guest_count=params["guest_count"],
        max_budget_usd=params["max_budget_usd"],
        outdoor_required=params["outdoor_required"],
    )

    assert result["status"] == case["expected_status"]
    assert result["matched_count"] > 0
    # Ensure all matched venues meet the constraints
    for venue in result["venues"]:
        assert venue["max_capacity"] >= params["guest_count"]
        assert venue["rental_fee_usd"] <= params["max_budget_usd"]
        assert venue["has_outdoor_space"] is True


def test_eval_case_002_budget_allocation(golden_dataset):
    """TC_002: Golden eval test for budget allocation and feasibility."""
    case = next(c for c in golden_dataset["eval_cases"] if c["eval_case_id"] == "TC_002_BUDGET_ALLOCATION")
    params = case["expected_parameters"]

    result = calculate_budget_allocation(
        total_budget_usd=params["total_budget_usd"],
        guest_count=params["guest_count"],
    )

    assert result["status"] == case["expected_status"]
    assert len(result["allocations"]) >= 6
    assert result["contingency_fund_usd"] > 0
    assert result["estimated_cost_per_guest_usd"] == pytest.approx(35000 / 120, rel=1e-2)

    # Check total of allocated portions + contingency equals total budget
    total_allocated = sum(a["allocated_usd"] for a in result["allocations"])
    assert total_allocated == pytest.approx(params["total_budget_usd"], rel=1e-1)


def test_eval_case_003_hitl_outreach_staging(golden_dataset):
    """TC_003: Golden eval test for HITL outreach staging."""
    case = next(c for c in golden_dataset["eval_cases"] if c["eval_case_id"] == "TC_003_HITL_OUTREACH_STAGING")

    result = stage_vendor_inquiry_email(
        vendor_name="Barr Mansion",
        recipient_email="events@barrmansion.com",
        wedding_date="October 17, 2026",
        estimated_guest_count=120,
        budget_range_usd="$10,000 - $14,000",
        specific_questions=["What is the deposit policy?", "Are outside caterers allowed?"],
    )

    assert result["status"] == case["expected_status"]
    assert result["requires_human_confirmation"] is True
    assert "Barr Mansion" in result["staged_email_body"]
    assert "October 17, 2026" in result["staged_email_body"]
    assert "HUMAN APPROVAL REQUIRED" in result["approval_prompt"]
    assert HITLPolicyPlugin.inspect_tool_call("stage_vendor_inquiry_email", {}) is True


def test_eval_case_004_guided_error_handling(golden_dataset):
    """TC_004: Golden eval test ensuring low budget triggers guided recovery guidance."""
    case = next(c for c in golden_dataset["eval_cases"] if c["eval_case_id"] == "TC_004_GUIDED_ERROR_LOW_BUDGET")

    # $5,000 for 400 guests is $12.50/guest -> below $80 minimum feasibility
    result = calculate_budget_allocation(
        total_budget_usd=5000,
        guest_count=400,
    )

    assert result["status"] == case["expected_status"]
    assert "Budget constraint warning" in result["message"]
    assert "Suggested recovery actions" in result["message"]
