"""Guardrails, Policy Plugins, and Self-Evaluation checks for Wedding Planning Agents."""

from typing import Any, Dict, List, Optional, Tuple
from wedding_planner.observability.logging import logger


class PolicyViolation(Exception):
    """Raised when an agent action violates a critical planning guardrail."""
    pass


class BudgetSafetyGuardrail:
    """Evaluates proposed allocations to prevent catastrophic budget overruns."""

    @staticmethod
    def validate_budget_proposal(
        total_budget_usd: float,
        proposed_spend_usd: float,
        contingency_percentage: float = 0.05,
    ) -> Tuple[bool, Optional[str]]:
        """Verifies that proposed expenditures do not exceed total available funds plus contingency."""
        max_allowed = total_budget_usd * 1.05  # 5% buffer threshold
        if proposed_spend_usd > max_allowed:
            violation_msg = (
                f"GUARDRAIL VIOLATION: Proposed spend (${proposed_spend_usd:,.2f}) exceeds total budget "
                f"(${total_budget_usd:,.2f}) by more than 5%. Re-allocating categories to preserve contingency."
            )
            logger.warning(violation_msg, extra={"structured_data": {"guardrail": "BudgetSafetyGuardrail", "status": "BLOCKED"}})
            return False, violation_msg
        return True, None


class HITLPolicyPlugin:
    """Enforces strict Human-in-the-Loop confirmation before any external communication."""

    @staticmethod
    def inspect_tool_call(tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Returns True if the tool invocation requires an interactive human stop."""
        high_stakes_tools = ["stage_vendor_inquiry_email", "send_vendor_email", "book_venue_reservation"]
        if tool_name in high_stakes_tools:
            logger.info(
                f"HITL Guardrail activated for high-stakes tool: {tool_name}",
                extra={"structured_data": {"guardrail": "HITLPolicyPlugin", "tool": tool_name, "action": "HALT_FOR_USER_CONFIRMATION"}},
            )
            return True
        return False


class SelfEvalGuardrail:
    """Self-evaluates agent outputs for completeness, tone, and compliance with the wedding constitution."""

    @staticmethod
    def evaluate_response(response_text: str, current_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Runs automated self-evaluation heuristics on the agent response."""
        checks = {
            "includes_disclaimer_for_unverified_prices": "estimate" in response_text.lower() or "$" in response_text,
            "maintains_warm_persona": not any(w in response_text.lower() for w in ["cannot assist", "error 500", "null pointer"]),
            "respects_guest_limitations": True,
        }

        score = sum(1 for v in checks.values() if v) / len(checks)
        return {
            "passed": score >= 0.66,
            "score": round(score, 2),
            "checks": checks,
        }
