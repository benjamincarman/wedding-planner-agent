"""Multi-Agent Orchestration, Strategic Model Routing, and ADK Root Agent Setup."""

import os
from typing import List, Optional
from google.adk import Agent
from wedding_planner.constitution import WEDDING_PLANNER_CONSTITUTION
from wedding_planner.tools.venue_tools import search_wedding_venues
from wedding_planner.tools.budget_tools import calculate_budget_allocation
from wedding_planner.tools.outreach_tools import stage_vendor_inquiry_email
from wedding_planner.guardrails.policy_plugin import HITLPolicyPlugin
from wedding_planner.observability.logging import logger, log_intent, log_outcome


def get_strategic_model(task_type: str = "general") -> str:
    """Strategic Model Routing: Routes requests to the most appropriate Gemini model.

    - Flash ('gemini-2.5-flash'): Fast sub-agent tool lookups, guest list parsing, email drafting.
    - Pro ('gemini-2.5-pro'): Coordinator orchestration, complex trade-off analysis, multi-vendor synthesis.
    """
    routing_table = {
        "planning": "gemini-2.5-pro",
        "orchestration": "gemini-2.5-pro",
        "trade_off_analysis": "gemini-2.5-pro",
        "fast_lookup": "gemini-2.5-flash",
        "venue_search": "gemini-2.5-flash",
        "budget_calculation": "gemini-2.5-flash",
        "email_drafting": "gemini-2.5-flash",
        "general": "gemini-2.5-flash",
    }
    selected_model = routing_table.get(task_type.lower(), "gemini-2.5-flash")
    logger.info(
        f"Strategic model routing selected '{selected_model}' for task type '{task_type}'",
        extra={"structured_data": {"task_type": task_type, "model": selected_model}},
    )
    return selected_model


# --- 1. Venue & Vendor Scout Specialist Agent ---
venue_scout_agent = Agent(
    name="venue_scout_agent",
    description="Specialist agent that searches, filters, and ranks wedding venues and vendors matching capacity, budget, and style.",
    model=get_strategic_model("venue_search"),
    instruction="""
    You are the Venue & Vendor Scouting Specialist.
    Your responsibility is to query wedding venue databases using the `search_wedding_venues` tool.
    Always prioritize venues that fit strictly within the couple's guest capacity and budget ceiling.
    Highlight key amenities such as outdoor space, outside catering permissions, and estimated total costs.
    If no venues match, provide constructive, guided alternative suggestions.
    """,
    tools=[search_wedding_venues],
)

# --- 2. Budget & Cost Specialist Agent ---
budget_specialist_agent = Agent(
    name="budget_specialist_agent",
    description="Specialist agent that calculates itemized budget distributions, evaluates per-guest feasibility, and identifies trade-offs.",
    model=get_strategic_model("budget_calculation"),
    instruction="""
    You are the Wedding Budget & Financial Specialist.
    Your responsibility is to calculate industry-standard line-item allocations using `calculate_budget_allocation`.
    Evaluate whether the per-guest spend is realistic for the target region.
    Flag over-budget risks early and suggest smart re-allocations based on the couple's top priorities.
    """,
    tools=[calculate_budget_allocation],
)

# --- 3. Vendor Outreach & HITL Communication Agent ---
outreach_agent = Agent(
    name="outreach_agent",
    description="Specialist agent that drafts professional RFP inquiry emails to venues and vendors with Human-in-the-Loop review stops.",
    model=get_strategic_model("email_drafting"),
    instruction="""
    You are the Vendor Communications Specialist.
    Your responsibility is to draft professional, personalized inquiry emails using `stage_vendor_inquiry_email`.
    CRITICAL POLICY: All drafted emails are STAGED FOR HUMAN APPROVAL. You must never execute or claim an email was dispatched without the couple's explicit confirmation.
    """,
    tools=[stage_vendor_inquiry_email],
)


# --- 4. Root Coordinator Agent (Tie-the-Knot Concierge) ---
root_agent = Agent(
    name="wedding_planner_coordinator",
    description="Lead Wedding Planning Coordinator that manages the couple's profile, conducts discovery interviews, and delegates to specialist agents.",
    model=get_strategic_model("orchestration"),
    instruction=WEDDING_PLANNER_CONSTITUTION,
    sub_agents=[venue_scout_agent, budget_specialist_agent, outreach_agent],
    tools=[search_wedding_venues, calculate_budget_allocation, stage_vendor_inquiry_email],
)
