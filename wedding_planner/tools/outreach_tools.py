"""Vendor Outreach and Human-in-the-Loop (HITL) Inquiry Staging Tool."""

import time
from typing import Any, Dict, List, Optional
from wedding_planner.tools.schemas import (
    VendorInquiryInput,
    VendorInquiryOutput,
)
from wedding_planner.observability.logging import log_intent, log_outcome
from wedding_planner.observability.tracing import trace_span


@trace_span("tool.stage_vendor_inquiry_email")
def stage_vendor_inquiry_email(
    vendor_name: str,
    recipient_email: str,
    wedding_date: str,
    estimated_guest_count: int,
    budget_range_usd: str,
    specific_questions: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Drafts and stages a vendor RFP inquiry email, enforcing a Human-in-the-Loop approval stop.

    Args:
        vendor_name (str): Name of the target venue or vendor business.
        recipient_email (str): Direct email address for the vendor contact.
        wedding_date (str): Target wedding date or season (e.g. 'October 17, 2026').
        estimated_guest_count (int): Anticipated guest count.
        budget_range_usd (str): Target budget bracket (e.g. '$12,000 - $16,000').
        specific_questions (List[str], optional): Key policy questions (catering, noise, deposit terms).
        session_id (str, optional): Active session identifier for telemetry and logging.

    Returns:
        Dict[str, Any]: Structured VendorInquiryOutput requiring explicit human confirmation.
    """
    start_time = time.time()
    input_params = {
        "vendor_name": vendor_name,
        "recipient_email": recipient_email,
        "wedding_date": wedding_date,
        "estimated_guest_count": estimated_guest_count,
        "budget_range_usd": budget_range_usd,
        "specific_questions": specific_questions or [],
    }
    log_intent("OutreachAgent", "stage_vendor_inquiry_email", input_params, session_id)

    # 1. Validation
    try:
        validated_input = VendorInquiryInput(**input_params)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"Schema validation error: {str(e)}"
        log_outcome("OutreachAgent", "stage_vendor_inquiry_email", "FAILED", None, duration_ms, session_id, error_msg)
        return VendorInquiryOutput(
            status="GUIDED_ERROR",
            requires_human_confirmation=False,
            staged_email_subject="",
            staged_email_body="",
            recipient=recipient_email,
            approval_prompt=f"Validation failed: {str(e)}. Please provide valid recipient email and wedding date.",
        ).model_dump()

    # 2. Draft generation
    subject = f"Wedding Date & Availability Inquiry — {validated_input.wedding_date} ({validated_input.estimated_guest_count} Guests)"

    bullet_points = ""
    if validated_input.specific_questions:
        bullet_points = "\nWe would love to get your confirmation on a few specific details:\n" + "\n".join(
            [f"- {q}" for q in validated_input.specific_questions]
        )

    body = f"""Dear {validated_input.vendor_name} Events Team,

I hope this email finds you well! We are currently planning our wedding celebration and are huge admirers of {validated_input.vendor_name}.

We are writing to check your availability and package options for:
- Target Date: {validated_input.wedding_date}
- Estimated Guest Count: {validated_input.estimated_guest_count} guests
- Target Budget Range: {validated_input.budget_range_usd}
{bullet_points}

Could you please share your latest pricing guide and schedule a brief consultation or walkthrough?

Warm regards,
[Couple's Names]
"""

    approval_prompt = (
        f"🚨 HUMAN APPROVAL REQUIRED: The inquiry email for '{validated_input.vendor_name}' "
        f"({validated_input.recipient_email}) has been drafted and staged. "
        f"Please review the draft above and reply 'CONFIRM' to dispatch, or specify any edits."
    )

    duration_ms = (time.time() - start_time) * 1000
    log_outcome(
        "OutreachAgent",
        "stage_vendor_inquiry_email",
        "SUCCESS",
        f"Email staged for {validated_input.vendor_name} (HITL stop active)",
        duration_ms,
        session_id,
    )

    return VendorInquiryOutput(
        status="STAGED_FOR_APPROVAL",
        requires_human_confirmation=True,
        staged_email_subject=subject,
        staged_email_body=body,
        recipient=validated_input.recipient_email,
        approval_prompt=approval_prompt,
    ).model_dump()
