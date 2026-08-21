"""Unit tests for Guardrails, Policy Plugins, PII Redaction, and Self-Evaluation."""

import pytest
from wedding_planner.guardrails.policy_plugin import (
    BudgetSafetyGuardrail,
    HITLPolicyPlugin,
    SelfEvalGuardrail,
)
from wedding_planner.observability.pii_scrubber import redact_pii, redact_text


def test_budget_safety_guardrail():
    # Feasible budget spend
    allowed, err = BudgetSafetyGuardrail.validate_budget_proposal(total_budget_usd=30000, proposed_spend_usd=31000)
    assert allowed is True
    assert err is None

    # Catastrophic overrun (> 5% buffer)
    allowed, err = BudgetSafetyGuardrail.validate_budget_proposal(total_budget_usd=30000, proposed_spend_usd=38000)
    assert allowed is False
    assert "GUARDRAIL VIOLATION" in err


def test_hitl_guardrail_detection():
    assert HITLPolicyPlugin.inspect_tool_call("stage_vendor_inquiry_email", {}) is True
    assert HITLPolicyPlugin.inspect_tool_call("book_venue_reservation", {}) is True
    assert HITLPolicyPlugin.inspect_tool_call("search_wedding_venues", {}) is False


def test_pii_scrubber_deep_sanitization():
    raw_payload = {
        "user_name": "Sarah Connor",
        "contact_info": {
            "email": "sarah.connor@example.com",
            "phone": "415-555-2671",
            "notes": "Call after 5pm or send to sarah.connor@example.com",
        },
        "billing": {
            "credit_card": "4111-2222-3333-4444",
        },
    }

    sanitized = redact_pii(raw_payload)
    assert sanitized["contact_info"]["email"] == "[REDACTED_EMAIL]"
    assert sanitized["contact_info"]["phone"] == "[REDACTED_PHONE]"
    assert "[REDACTED_EMAIL]" in sanitized["contact_info"]["notes"]
    assert sanitized["billing"]["credit_card"] == "[REDACTED_SECRET]"


def test_self_eval_guardrail():
    good_response = "Here is an estimated breakdown for your $35,000 budget with 120 guests."
    eval_result = SelfEvalGuardrail.evaluate_response(good_response, {})
    assert eval_result["passed"] is True
    assert eval_result["score"] >= 0.66
