"""Interactive CLI demo for the Tie-the-Knot Wedding Planner Multi-Agent System."""

import os
import sys
import uuid
from wedding_planner.agent import root_agent, get_strategic_model
from wedding_planner.memory.session_store import PersistentSessionStore
from wedding_planner.memory.compaction import trigger_background_memory_consolidation, ContextCompactor
from wedding_planner.tools.venue_tools import search_wedding_venues
from wedding_planner.tools.budget_tools import calculate_budget_allocation
from wedding_planner.tools.outreach_tools import stage_vendor_inquiry_email
from wedding_planner.guardrails.policy_plugin import BudgetSafetyGuardrail, HITLPolicyPlugin, SelfEvalGuardrail
from wedding_planner.observability.logging import logger, setup_structured_logging
from wedding_planner.secret_manager import get_secret


def print_banner():
    print("=" * 70)
    print("💍 Tie-the-Knot Concierge — Multi-Agent Wedding Planner AI")
    print("   Built with Google ADK, Gemini Strategic Routing, and OpenTelemetry")
    print("=" * 70)
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'status' to view the current saved wedding profile.")
    print("-" * 70)


def interactive_cli():
    setup_structured_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    session_store = PersistentSessionStore()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    compactor = ContextCompactor()

    print_banner()
    print(f"[Session ID: {session_id}]")
    print("\nTie-the-Knot Concierge: Welcome! Congratulations on the upcoming wedding!")
    print("I'm here to help plan everything smoothly. Where are you thinking of hosting the wedding,")
    print("and do you have an estimated budget or guest count in mind?\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit"]:
                print("\nThank you for using Tie-the-Knot Concierge! Best wishes for the wedding! 🥂\n")
                break
            if user_input.lower() == "status":
                profile = session_store.get_or_create_profile(session_id)
                print("\n📋 Current Saved Wedding Profile:")
                for k, v in profile.items():
                    print(f"  - {k}: {v}")
                print()
                continue

            # Record turn in persistent session storage
            session_store.record_message(session_id, "user", user_input)

            # Retrieve conversation history
            history = session_store.get_history(session_id)
            compacted_history = compactor.compact_history(history)

            # Trigger non-blocking async memory consolidation
            trigger_background_memory_consolidation(session_id, history, session_store)

            # Process intent and route tool calls based on user input
            text_lower = user_input.lower()
            response_text = ""

            if any(w in text_lower for w in ["venue", "place", "location", "hall", "mansion", "barn"]):
                profile = session_store.get_or_create_profile(session_id)
                city = profile.get("city") or ("Austin" if "austin" in text_lower else "Austin")
                guest_count = profile.get("guest_count") or 120
                budget = profile.get("total_budget_usd") or 15000.0
                outdoor = "outdoor" in text_lower or True

                res = search_wedding_venues(
                    city=city,
                    guest_count=guest_count,
                    max_budget_usd=budget if budget < 20000 else budget * 0.4,
                    outdoor_required=outdoor,
                    session_id=session_id,
                )

                if res["status"] == "SUCCESS":
                    response_text = f"🏰 Found {res['matched_count']} matching venue(s) in {city}:\n"
                    for v in res["venues"]:
                        response_text += (
                            f"\n• {v['name']} ({v['style'].title()})\n"
                            f"  - Capacity: {v['max_capacity']} guests | Base Rental: ${v['rental_fee_usd']:,.0f}\n"
                            f"  - Estimated Total: ${v['estimated_total_usd']:,.0f}\n"
                            f"  - Outdoor Space: {'Yes' if v['has_outdoor_space'] else 'No'} | Outside Catering: {'Allowed' if v['allows_outside_catering'] else 'In-house only'}\n"
                            f"  - Contact: {v['contact_email']}\n"
                        )
                else:
                    response_text = f"ℹ️ {res['message']}"

            elif any(w in text_lower for w in ["budget", "cost", "breakdown", "allocate", "dollars", "$"]):
                profile = session_store.get_or_create_profile(session_id)
                budget = profile.get("total_budget_usd") or 35000.0
                guest_count = profile.get("guest_count") or 120

                res = calculate_budget_allocation(
                    total_budget_usd=budget,
                    guest_count=guest_count,
                    session_id=session_id,
                )

                if res["status"] == "SUCCESS":
                    response_text = (
                        f"📊 Budget Allocation for ${res['total_budget_usd']:,.0f} ({guest_count} guests - ~${res['estimated_cost_per_guest_usd']:,.2f}/guest):\n"
                    )
                    for alloc in res["allocations"]:
                        response_text += f"  • {alloc['category']} ({alloc['percentage_of_total']}%): ${alloc['allocated_usd']:,.2f}\n"
                    response_text += f"\n💡 Feasibility: {res['feasibility_assessment']} (Includes ${res['contingency_fund_usd']:,.2f} contingency reserve)."
                else:
                    response_text = f"⚠️ {res['message']}"

            elif any(w in text_lower for w in ["email", "inquiry", "draft", "contact", "reach out"]):
                res = stage_vendor_inquiry_email(
                    vendor_name="Barr Mansion",
                    recipient_email="events@barrmansion.com",
                    wedding_date="October 17, 2026",
                    estimated_guest_count=120,
                    budget_range_usd="$12,000 - $16,000",
                    specific_questions=["What is the deposit schedule?", "Do you provide on-site day-of coordination?"],
                    session_id=session_id,
                )
                response_text = (
                    f"✉️ Staged Draft for '{res['recipient']}':\n\n"
                    f"Subject: {res['staged_email_subject']}\n\n"
                    f"{res['staged_email_body']}\n"
                    f"{res['approval_prompt']}"
                )

            else:
                response_text = (
                    "I've updated your wedding planning notes! Would you like me to:\n"
                    "1. Search top venues in your preferred city (`search_wedding_venues`)\n"
                    "2. Generate an itemized 7-category budget breakdown (`calculate_budget_allocation`)\n"
                    "3. Draft a vendor inquiry RFP email for your review (`stage_vendor_inquiry_email`)"
                )

            # Self-Evaluation Guardrail check
            eval_metrics = SelfEvalGuardrail.evaluate_response(response_text, session_store.get_or_create_profile(session_id))
            session_store.record_message(session_id, "assistant", response_text)

            print(f"\nTie-the-Knot Concierge:\n{response_text}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Best wishes with the wedding planning!\n")
            break


if __name__ == "__main__":
    interactive_cli()
