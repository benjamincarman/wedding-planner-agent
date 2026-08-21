"""Interactive CLI for the Tie-the-Knot Wedding Planner Multi-Agent System with Live Gemini Reasoning."""

import os
import sys
import uuid
import json
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

from wedding_planner.agent import get_strategic_model
from wedding_planner.constitution import WEDDING_PLANNER_CONSTITUTION
from wedding_planner.memory.session_store import PersistentSessionStore
from wedding_planner.memory.compaction import trigger_background_memory_consolidation, ContextCompactor
from wedding_planner.tools.venue_tools import search_wedding_venues
from wedding_planner.tools.budget_tools import calculate_budget_allocation
from wedding_planner.tools.outreach_tools import stage_vendor_inquiry_email
from wedding_planner.guardrails.policy_plugin import SelfEvalGuardrail
from wedding_planner.observability.logging import logger, setup_structured_logging


def print_banner():
    print("=" * 75)
    print("💍 Tie-the-Knot Concierge — Live Gemini 2.5 Multi-Agent Wedding Planner AI")
    print("   Powered by Google Gemini 2.5 Pro / Flash, Strategic Routing & Telemetry")
    print("=" * 75)
    print("Commands:")
    print("  • Type 'status' to view your persistent SQLite wedding profile")
    print("  • Type 'quit' or 'exit' to end session")
    print("-" * 75)


def get_genai_client():
    """Initializes Google GenAI Client via Gemini API Key or Vertex AI ADC."""
    project_id = os.getenv("GCP_PROJECT_ID", "wedding-planner-agent-506218")
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and api_key.startswith("AIza"):
        return genai.Client(api_key=api_key)
    try:
        # Connect via Google Cloud Vertex AI (Default Application Credentials)
        return genai.Client(vertexai=True, project=project_id, location="us-central1")
    except Exception as e:
        logger.warning(f"Could not connect to Vertex AI: {e}")
        return None


def execute_tool(func_name: str, args: dict, session_id: str) -> dict:
    """Dispatches tool execution to registered python tool functions."""
    args["session_id"] = session_id
    if func_name == "calculate_budget_allocation":
        return calculate_budget_allocation(**args)
    elif func_name == "search_wedding_venues":
        return search_wedding_venues(**args)
    elif func_name == "stage_vendor_inquiry_email":
        return stage_vendor_inquiry_email(**args)
    return {"status": "ERROR", "message": f"Unknown tool '{func_name}'"}


def interactive_cli():
    setup_structured_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    session_store = PersistentSessionStore()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    compactor = ContextCompactor()
    client = get_genai_client()

    print_banner()
    print(f"[Session ID: {session_id}]")
    if client:
        print("🟢 Live Gemini 2.5 Agent Connected (Vertex AI / Gemini API)")
    else:
        print("🟡 Running in offline fallback mode")

    print("\nTie-the-Knot Concierge: Welcome! Congratulations on the upcoming wedding! 🥂")
    print("I'm here to help plan every detail smoothly. Where are you thinking of hosting the wedding,")
    print("and do you have an estimated budget or guest count in mind?\n")

    # Maintain conversation state for live Gemini model
    chat_contents: list = []

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
                print("\n📋 Current Saved Wedding Profile (SQLite):")
                for k, v in profile.items():
                    print(f"  - {k}: {v}")
                print()
                continue

            # Record turn in persistent session storage
            session_store.record_message(session_id, "user", user_input)

            # Retrieve conversation history & trigger background memory extraction
            history = session_store.get_history(session_id)
            trigger_background_memory_consolidation(session_id, history, session_store)

            response_text = ""

            if client:
                # Add user turn to conversation history
                chat_contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
                )

                # Call Gemini 2.5 Pro with Tools
                model_name = get_strategic_model("orchestration")
                config = types.GenerateContentConfig(
                    system_instruction=WEDDING_PLANNER_CONSTITUTION,
                    tools=[calculate_budget_allocation, search_wedding_venues, stage_vendor_inquiry_email],
                    temperature=0.7,
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=chat_contents,
                    config=config,
                )

                # Multi-turn tool execution loop
                while response.function_calls:
                    chat_contents.append(response.candidates[0].content)
                    tool_parts = []
                    for fc in response.function_calls:
                        tool_result = execute_tool(fc.name, dict(fc.args), session_id)
                        tool_parts.append(
                            types.Part.from_function_response(name=fc.name, response={"result": tool_result})
                        )

                    chat_contents.append(types.Content(role="tool", parts=tool_parts))
                    response = client.models.generate_content(
                        model=model_name,
                        contents=chat_contents,
                        config=config,
                    )

                response_text = response.text or "I've processed your request. How else can I assist with your wedding plans?"
                chat_contents.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=response_text)])
                )

            else:
                # Intelligent offline fallback
                response_text = (
                    "I've noted your preferences! Let me analyze venue options and budget distributions "
                    "for your wedding."
                )

            # Record assistant turn in SQLite
            session_store.record_message(session_id, "assistant", response_text)
            eval_metrics = SelfEvalGuardrail.evaluate_response(response_text, session_store.get_or_create_profile(session_id))

            print(f"\nTie-the-Knot Concierge:\n{response_text}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Best wishes with the wedding planning!\n")
            break


if __name__ == "__main__":
    interactive_cli()

