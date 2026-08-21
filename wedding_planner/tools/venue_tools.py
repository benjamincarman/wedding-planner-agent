"""Wedding Venue Search and Pricing Evaluation Tools with Guided Error Handling."""

import time
from typing import Any, Dict, List, Optional
from wedding_planner.tools.schemas import (
    VenueSearchInput,
    VenueSearchOutput,
    VenueItem,
)
from wedding_planner.observability.logging import log_intent, log_outcome
from wedding_planner.observability.tracing import trace_span

# Comprehensive Curated Venue Database
SAMPLE_VENUES_DATABASE: List[Dict[str, Any]] = [
    # Austin, TX
    {
        "name": "Barr Mansion & Artisan Ballroom",
        "city": "Austin",
        "max_capacity": 250,
        "rental_fee_usd": 9500.0,
        "estimated_total_usd": 18500.0,
        "style": "rustic",
        "has_outdoor_space": True,
        "allows_outside_catering": False,
        "contact_email": "events@barrmansion.com",
    },
    {
        "name": "The Greenhouse at Driftwood",
        "city": "Austin",
        "max_capacity": 150,
        "rental_fee_usd": 8000.0,
        "estimated_total_usd": 15000.0,
        "style": "botanical",
        "has_outdoor_space": True,
        "allows_outside_catering": True,
        "contact_email": "inquiries@greenhousedriftwood.com",
    },
    {
        "name": "The Driskill Historic Hotel",
        "city": "Austin",
        "max_capacity": 300,
        "rental_fee_usd": 12000.0,
        "estimated_total_usd": 28000.0,
        "style": "ballroom",
        "has_outdoor_space": False,
        "allows_outside_catering": False,
        "contact_email": "weddings@driskillhotel.com",
    },
    {
        "name": "Prospect House",
        "city": "Austin",
        "max_capacity": 220,
        "rental_fee_usd": 8500.0,
        "estimated_total_usd": 17000.0,
        "style": "modern",
        "has_outdoor_space": True,
        "allows_outside_catering": True,
        "contact_email": "hello@prospecthousetx.com",
    },
    # Napa Valley / Sonoma, CA
    {
        "name": "Meadowood Napa Valley Estate",
        "city": "Napa Valley",
        "max_capacity": 180,
        "rental_fee_usd": 16000.0,
        "estimated_total_usd": 38000.0,
        "style": "vineyard",
        "has_outdoor_space": True,
        "allows_outside_catering": False,
        "contact_email": "weddings@meadowoodnapa.com",
    },
    {
        "name": "Tre Posti Garden Pavilion",
        "city": "Napa Valley",
        "max_capacity": 150,
        "rental_fee_usd": 9000.0,
        "estimated_total_usd": 22000.0,
        "style": "vineyard",
        "has_outdoor_space": True,
        "allows_outside_catering": False,
        "contact_email": "info@treposti.com",
    },
    # Denver / Colorado Mountains
    {
        "name": "Skylight Denver",
        "city": "Denver",
        "max_capacity": 200,
        "rental_fee_usd": 6500.0,
        "estimated_total_usd": 13000.0,
        "style": "industrial modern",
        "has_outdoor_space": False,
        "allows_outside_catering": True,
        "contact_email": "events@skylightdenver.com",
    },
    {
        "name": "Lionsgate Event Center & Chandelier Barn",
        "city": "Denver",
        "max_capacity": 300,
        "rental_fee_usd": 7500.0,
        "estimated_total_usd": 16500.0,
        "style": "rustic",
        "has_outdoor_space": True,
        "allows_outside_catering": True,
        "contact_email": "weddings@lionsgatecenter.com",
    },
    # Miami, FL
    {
        "name": "Vizcaya Museum & Gardens",
        "city": "Miami",
        "max_capacity": 250,
        "rental_fee_usd": 15000.0,
        "estimated_total_usd": 32000.0,
        "style": "waterfront historic",
        "has_outdoor_space": True,
        "allows_outside_catering": True,
        "contact_email": "rentals@vizcaya.org",
    },
]


@trace_span("tool.search_wedding_venues")
def search_wedding_venues(
    city: str,
    guest_count: int,
    max_budget_usd: float,
    outdoor_required: bool = False,
    style_preference: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for wedding venues matching capacity, budget, and aesthetic preferences.

    Args:
        city (str): Target city or region (e.g. 'Austin', 'Napa Valley', 'Denver', 'Miami').
        guest_count (int): Expected number of attending guests.
        max_budget_usd (float): Maximum rental fee ceiling in USD.
        outdoor_required (bool): If True, filters strictly for venues with outdoor spaces.
        style_preference (str, optional): Preferred style (e.g. 'rustic', 'modern', 'vineyard', 'ballroom').
        session_id (str, optional): Active session identifier for telemetry and logging.

    Returns:
        Dict[str, Any]: Structured VenueSearchOutput containing matched venues or guided error instructions.
    """
    start_time = time.time()
    input_params = {
        "city": city,
        "guest_count": guest_count,
        "max_budget_usd": max_budget_usd,
        "outdoor_required": outdoor_required,
        "style_preference": style_preference,
    }
    log_intent("VenueScoutAgent", "search_wedding_venues", input_params, session_id)

    # 1. Input Schema Validation
    try:
        validated_input = VenueSearchInput(**input_params)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"Schema validation error: {str(e)}"
        log_outcome("VenueScoutAgent", "search_wedding_venues", "FAILED", None, duration_ms, session_id, error_msg)
        return VenueSearchOutput(
            status="GUIDED_ERROR",
            matched_count=0,
            venues=[],
            message=f"Validation failed: {str(e)}. Please provide valid numeric values for guest_count and max_budget_usd.",
        ).model_dump()

    # 2. Location matching with guided error handling
    normalized_city = validated_input.city.strip().lower()
    available_cities = list({v["city"].lower() for v in SAMPLE_VENUES_DATABASE})
    city_matches = [
        v for v in SAMPLE_VENUES_DATABASE if normalized_city in v["city"].lower() or v["city"].lower() in normalized_city
    ]

    if not city_matches:
        duration_ms = (time.time() - start_time) * 1000
        supported_str = ", ".join([v["city"] for v in SAMPLE_VENUES_DATABASE[:4]])
        recovery_message = (
            f"No venues found in '{validated_input.city}'. "
            f"Currently supported regions with verified pricing include: {supported_str}. "
            f"Suggested action: Ask the user if they'd consider exploring venues in Austin, Napa Valley, or Denver, "
            f"or adjust the search query to a nearby major metropolitan area."
        )
        log_outcome("VenueScoutAgent", "search_wedding_venues", "GUIDED_ERROR", recovery_message, duration_ms, session_id)
        return VenueSearchOutput(
            status="GUIDED_ERROR",
            matched_count=0,
            venues=[],
            message=recovery_message,
        ).model_dump()

    # 3. Filter criteria: Capacity, Budget, Outdoor space, Style
    filtered = []
    for venue in city_matches:
        if venue["max_capacity"] < validated_input.guest_count:
            continue
        if venue["rental_fee_usd"] > validated_input.max_budget_usd:
            continue
        if validated_input.outdoor_required and not venue["has_outdoor_space"]:
            continue
        if validated_input.style_preference:
            pref = validated_input.style_preference.lower()
            if pref not in venue["style"].lower():
                continue
        filtered.append(VenueItem(**venue))

    duration_ms = (time.time() - start_time) * 1000

    # 4. Guided Error Handling if zero results after filtering
    if not filtered:
        # Find closest bottleneck
        capacity_bottlenecks = [v for v in city_matches if v["max_capacity"] < validated_input.guest_count]
        budget_bottlenecks = [v for v in city_matches if v["rental_fee_usd"] > validated_input.max_budget_usd]

        guidance_parts = []
        if len(capacity_bottlenecks) == len(city_matches):
            guidance_parts.append(
                f"Guest count ({validated_input.guest_count}) exceeds capacities of all venues in {city}. Suggest trimming guest list under 250."
            )
        if len(budget_bottlenecks) == len(city_matches):
            min_fee = min(v["rental_fee_usd"] for v in city_matches)
            guidance_parts.append(
                f"Max budget (${validated_input.max_budget_usd:,.0f}) is below minimum venue rental in {city} (starting at ${min_fee:,.0f}). Suggest increasing venue allocation."
            )
        if validated_input.outdoor_required:
            guidance_parts.append("Consider relaxing the strict outdoor requirement or considering hybrid indoor/outdoor estates.")

        recovery_msg = (
            f"No venues matched all strict constraints in {validated_input.city}. "
            + " ".join(guidance_parts)
            + f" Suggested action: Present 1-2 venues that slightly exceed budget or offer hybrid configurations."
        )
        log_outcome("VenueScoutAgent", "search_wedding_venues", "GUIDED_ERROR", recovery_msg, duration_ms, session_id)
        return VenueSearchOutput(
            status="GUIDED_ERROR",
            matched_count=0,
            venues=[],
            message=recovery_msg,
        ).model_dump()

    # Success outcome
    success_msg = f"Successfully identified {len(filtered)} matching venue(s) in {validated_input.city}."
    log_outcome("VenueScoutAgent", "search_wedding_venues", "SUCCESS", success_msg, duration_ms, session_id)
    return VenueSearchOutput(
        status="SUCCESS",
        matched_count=len(filtered),
        venues=filtered,
        message=success_msg,
    ).model_dump()
