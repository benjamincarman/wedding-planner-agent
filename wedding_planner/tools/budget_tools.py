"""Wedding Budget Allocation and Feasibility Analysis Tools with Guided Error Recovery."""

import time
from typing import Any, Dict, List, Optional
from wedding_planner.tools.schemas import (
    BudgetAllocationInput,
    BudgetAllocationOutput,
    CategoryAllocation,
)
from wedding_planner.observability.logging import log_intent, log_outcome
from wedding_planner.observability.tracing import trace_span

# Industry standard percentage splits for wedding budgets
BASE_ALLOCATION_PERCENTAGES = {
    "Venue & Facility Rental": (0.35, "Covers site rental, tables, chairs, and standard setup fees."),
    "Catering, Food & Open Bar": (0.28, "Estimated per-person food service, drinks, staffing, and bar packages."),
    "Photography & Videography": (0.12, "Full-day coverage, edited high-res gallery, and highlight reel."),
    "Floral Design & Decor": (0.09, "Ceremony arch, bridal bouquets, boutonnieres, and table centerpieces."),
    "Entertainment & Music": (0.07, "DJ/MC service, sound equipment, ceremony audio."),
    "Attire, Hair & Makeup": (0.05, "Dress, tuxedo, alterations, bridal party styling."),
    "Contingency Reserve": (0.04, "Unforeseen expenses, gratuities, last-minute additions."),
}


@trace_span("tool.calculate_budget_allocation")
def calculate_budget_allocation(
    total_budget_usd: float,
    guest_count: int,
    priorities: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate recommended line-item wedding budget splits and evaluate cost-per-guest feasibility.

    Args:
        total_budget_usd (float): Total overall wedding budget in USD.
        guest_count (int): Anticipated number of wedding guests.
        priorities (List[str], optional): High-priority categories to receive boosted allocations.
        session_id (str, optional): Active session identifier for telemetry and logging.

    Returns:
        Dict[str, Any]: Structured BudgetAllocationOutput with itemized allocations or guided recovery guidance.
    """
    start_time = time.time()
    input_params = {
        "total_budget_usd": total_budget_usd,
        "guest_count": guest_count,
        "priorities": priorities,
    }
    log_intent("BudgetSpecialistAgent", "calculate_budget_allocation", input_params, session_id)

    # 1. Schema Validation
    try:
        validated_input = BudgetAllocationInput(**input_params)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"Schema validation error: {str(e)}"
        log_outcome("BudgetSpecialistAgent", "calculate_budget_allocation", "FAILED", None, duration_ms, session_id, error_msg)
        return BudgetAllocationOutput(
            status="GUIDED_ERROR",
            total_budget_usd=total_budget_usd,
            estimated_cost_per_guest_usd=0.0,
            allocations=[],
            contingency_fund_usd=0.0,
            feasibility_assessment="Invalid Input",
            message=f"Validation failed: {str(e)}. Total budget must exceed $1,000 USD.",
        ).model_dump()

    cost_per_guest = validated_input.total_budget_usd / max(1, validated_input.guest_count)

    # 2. Guided Error Handling for unrealistically low budgets
    if cost_per_guest < 80.0:
        duration_ms = (time.time() - start_time) * 1000
        recovery_message = (
            f"Budget constraint warning: ${validated_input.total_budget_usd:,.0f} for {validated_input.guest_count} guests "
            f"averages ${cost_per_guest:,.2f}/guest, which is below standard catering & venue minimums ($150-$300/guest). "
            f"Suggested recovery actions: 1) Trim guest list to {int(validated_input.total_budget_usd / 180)} guests, "
            f"2) Increase budget to at least ${validated_input.guest_count * 150:,.0f}, or 3) Consider an intimate backyard/micro-wedding format."
        )
        log_outcome("BudgetSpecialistAgent", "calculate_budget_allocation", "GUIDED_ERROR", recovery_message, duration_ms, session_id)
        return BudgetAllocationOutput(
            status="GUIDED_ERROR",
            total_budget_usd=validated_input.total_budget_usd,
            estimated_cost_per_guest_usd=round(cost_per_guest, 2),
            allocations=[],
            contingency_fund_usd=0.0,
            feasibility_assessment="Tight / High Risk",
            message=recovery_message,
        ).model_dump()

    # 3. Dynamic adjustment based on user priorities
    weights = {k: v[0] for k, v in BASE_ALLOCATION_PERCENTAGES.items()}
    if validated_input.priorities:
        for p in validated_input.priorities:
            p_lower = p.lower()
            for cat in weights:
                if any(kw in cat.lower() for kw in p_lower.split()):
                    weights[cat] += 0.05

    # Re-normalize weights to 1.0
    total_weight = sum(weights.values())
    normalized_weights = {k: v / total_weight for k, v in weights.items()}

    allocations: List[CategoryAllocation] = []
    for cat, weight in normalized_weights.items():
        allocated_amount = round(validated_input.total_budget_usd * weight, 2)
        base_desc = BASE_ALLOCATION_PERCENTAGES[cat][1]
        allocations.append(
            CategoryAllocation(
                category=cat,
                allocated_usd=allocated_amount,
                percentage_of_total=round(weight * 100, 1),
                notes=base_desc,
            )
        )

    contingency = round(validated_input.total_budget_usd * normalized_weights["Contingency Reserve"], 2)
    feasibility = "Comfortable" if cost_per_guest >= 250.0 else "Moderate / Feasible with smart vendor choices"

    duration_ms = (time.time() - start_time) * 1000
    success_msg = (
        f"Budget allocated successfully: ${validated_input.total_budget_usd:,.0f} across {len(allocations)} categories "
        f"(${cost_per_guest:,.2f}/guest). Feasibility: {feasibility}."
    )

    log_outcome("BudgetSpecialistAgent", "calculate_budget_allocation", "SUCCESS", success_msg, duration_ms, session_id)

    return BudgetAllocationOutput(
        status="SUCCESS",
        total_budget_usd=validated_input.total_budget_usd,
        estimated_cost_per_guest_usd=round(cost_per_guest, 2),
        allocations=allocations,
        contingency_fund_usd=contingency,
        feasibility_assessment=feasibility,
        message=success_msg,
    ).model_dump()
