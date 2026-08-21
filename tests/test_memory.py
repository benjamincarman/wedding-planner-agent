"""Unit tests for persistent SQLite memory, context compaction, and async consolidation."""

import os
import pytest
import tempfile
from wedding_planner.memory.session_store import PersistentSessionStore
from wedding_planner.memory.compaction import ContextCompactor, async_consolidate_memory


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_persistent_session_store_crud(temp_db):
    store = PersistentSessionStore(db_path=temp_db)
    session_id = "test_sister_wedding_001"

    # Get default profile
    profile = store.get_or_create_profile(session_id)
    assert profile["city"] is None

    # Update profile
    store.update_profile(session_id, {"city": "Austin", "total_budget_usd": 35000, "guest_count": 120})
    updated = store.get_or_create_profile(session_id)
    assert updated["city"] == "Austin"
    assert updated["total_budget_usd"] == 35000
    assert updated["guest_count"] == 120

    # Record message with PII (should be sanitized)
    store.record_message(session_id, "user", "My email is sister@example.com and phone is 512-555-0199")
    history = store.get_history(session_id)
    assert len(history) == 1
    assert "[REDACTED_EMAIL]" in history[0]["content"]
    assert "[REDACTED_PHONE]" in history[0]["content"]


def test_context_compaction():
    compactor = ContextCompactor(max_recent_turns=3)
    long_history = [
        {"role": "user", "content": f"Turn {i} about wedding logistics"} for i in range(10)
    ]
    compacted = compactor.compact_history(long_history)
    # Compaction replaces the first 7 turns with 1 summary turn, leaving 1 summary + 3 recent = 4 turns
    assert len(compacted) == 4
    assert compacted[0]["role"] == "system"
    assert "[Previous Context Summary]" in compacted[0]["content"]


@pytest.mark.asyncio
async def test_async_memory_consolidation(temp_db):
    store = PersistentSessionStore(db_path=temp_db)
    session_id = "test_async_extract"
    sample_turns = [
        {"role": "user", "content": "Hi! We are looking to host our wedding in Austin with about 120 guests."},
        {"role": "assistant", "content": "Austin is wonderful! What is your estimated total budget?"},
        {"role": "user", "content": "We have a total budget of $35,000 and love a rustic botanical vibe."},
    ]
    extracted = await async_consolidate_memory(session_id, sample_turns, store)
    assert extracted.get("city") == "Austin"
    assert extracted.get("guest_count") == 120
    assert extracted.get("total_budget_usd") == 35000.0
    assert extracted.get("style_preference") == "rustic"

    # Verify persisted in database
    saved_profile = store.get_or_create_profile(session_id)
    assert saved_profile["city"] == "Austin"
    assert saved_profile["guest_count"] == 120
