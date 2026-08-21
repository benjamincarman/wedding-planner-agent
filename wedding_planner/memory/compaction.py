"""Context Bloat Management and Async Background Memory Consolidation."""

import asyncio
import re
from typing import Any, Dict, List, Optional
from wedding_planner.observability.logging import logger
from wedding_planner.observability.tracing import trace_span


class ContextCompactor:
    """Manages token bloat through sliding window history compaction and structured summaries."""

    def __init__(self, max_tokens: int = 4000, max_recent_turns: int = 6):
        self.max_tokens = max_tokens
        self.max_recent_turns = max_recent_turns

    def estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation (~4 chars per token)."""
        return len(text) // 4

    def compact_history(
        self,
        history: List[Dict[str, str]],
        existing_summary: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Compacts long conversation turns using sliding window and prepended summary.

        Args:
            history: Full list of message turn dicts [{'role': 'user', 'content': '...'}]
            existing_summary: Previously extracted conversation summary or facts.

        Returns:
            List of message dicts fitting comfortably within token budget.
        """
        if len(history) <= self.max_recent_turns:
            return history

        # Split into older turns to compact and recent turns to preserve
        older_turns = history[:-self.max_recent_turns]
        recent_turns = history[-self.max_recent_turns:]

        # Create quick compaction snippet
        condensed_snippets = []
        if existing_summary:
            condensed_snippets.append(f"[Existing Summary]: {existing_summary}")

        for turn in older_turns:
            role = turn.get("role", "unknown")
            snippet = turn.get("content", "")[:120].replace("\n", " ")
            condensed_snippets.append(f"- {role.capitalize()}: {snippet}...")

        compacted_summary_turn = {
            "role": "system",
            "content": "[Previous Context Summary]\n" + "\n".join(condensed_snippets),
        }

        return [compacted_summary_turn] + recent_turns


@trace_span("memory.async_consolidate_memory")
async def async_consolidate_memory(
    session_id: str,
    history: List[Dict[str, str]],
    session_store: Any,
) -> Dict[str, Any]:
    """Background asynchronous task that extracts wedding facts and consolidates profile state without blocking UI."""
    logger.info(f"Starting async memory consolidation for session {session_id}")

    # Simulated async LLM extraction or lightweight heuristic consolidation
    await asyncio.sleep(0.05)  # Yield to event loop to simulate non-blocking async task

    extracted_updates: Dict[str, Any] = {}
    combined_text = " ".join([turn.get("content", "") for turn in history])

    # Extract City
    for city in ["Austin", "Napa Valley", "Denver", "Miami", "New York", "Seattle", "Chicago", "Nashville"]:
        if city.lower() in combined_text.lower():
            extracted_updates["city"] = city
            break

    # Extract Budget
    budget_match = re.search(r'\$?(\d{2,3}(?:,\d{3})+|\d{4,6})\s*(?:budget|total|\$|dollars)?', combined_text, re.IGNORECASE)
    if budget_match:
        try:
            val = float(budget_match.group(1).replace(",", ""))
            if val >= 5000:
                extracted_updates["total_budget_usd"] = val
        except ValueError:
            pass

    # Extract Guest Count
    guest_match = re.search(r'(\d{2,4})\s*(?:guests|people|heads|attendees)', combined_text, re.IGNORECASE)
    if guest_match:
        try:
            val = int(guest_match.group(1))
            if 10 <= val <= 1000:
                extracted_updates["guest_count"] = val
        except ValueError:
            pass

    # Extract Aesthetic / Style
    for style in ["rustic", "modern", "ballroom", "vineyard", "botanical", "industrial", "waterfront"]:
        if style in combined_text.lower():
            extracted_updates["style_preference"] = style
            break

    if extracted_updates:
        session_store.update_profile(session_id, extracted_updates)
        logger.info(
            f"Async memory consolidated profile updates for session {session_id}",
            extra={"structured_data": {"extracted_updates": extracted_updates}},
        )

    return extracted_updates


def trigger_background_memory_consolidation(
    session_id: str,
    history: List[Dict[str, str]],
    session_store: Any,
) -> None:
    """Safely spawns async memory consolidation in background task."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_consolidate_memory(session_id, history, session_store))
    except RuntimeError:
        # If running outside async loop (e.g. CLI thread), run directly or in new loop
        asyncio.run(async_consolidate_memory(session_id, history, session_store))
