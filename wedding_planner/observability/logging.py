"""Structured JSON logging with Intent vs. Outcome capture and active PII redaction."""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from wedding_planner.observability.pii_scrubber import redact_pii


class JsonFormatter(logging.Formatter):
    """Custom logging formatter outputting single-line structured JSON logs with PII redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom structured payload if attached
        if hasattr(record, "structured_data") and isinstance(record.structured_data, dict):
            log_entry.update(record.structured_data)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Apply active PII scrubbing across the entire log dictionary
        scrubbed_entry = redact_pii(log_entry)
        return json.dumps(scrubbed_entry)


def setup_structured_logging(level: str = "INFO") -> logging.Logger:
    """Configures the root and package loggers to use structured JSON logging."""
    logger = logging.getLogger("wedding_planner")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Global logger instance
logger = setup_structured_logging()


def log_intent(agent_name: str, action: str, parameters: Dict[str, Any], session_id: Optional[str] = None) -> None:
    """Explicitly records the agent's intended action and inputs before tool execution."""
    logger.info(
        f"Agent '{agent_name}' initiated action: {action}",
        extra={
            "structured_data": {
                "phase": "INTENT",
                "agent": agent_name,
                "action": action,
                "parameters": parameters,
                "session_id": session_id or "default",
            }
        },
    )


def log_outcome(
    agent_name: str,
    action: str,
    status: str,
    result: Any,
    duration_ms: float,
    session_id: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Explicitly records the execution outcome, duration, and status after tool execution."""
    payload: Dict[str, Any] = {
        "phase": "OUTCOME",
        "agent": agent_name,
        "action": action,
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "session_id": session_id or "default",
        "result_preview": str(result)[:300] if result is not None else None,
    }
    if error:
        payload["error"] = error

    if status == "SUCCESS":
        logger.info(f"Action '{action}' succeeded in {duration_ms:.2f}ms", extra={"structured_data": payload})
    else:
        logger.error(f"Action '{action}' failed with status {status}", extra={"structured_data": payload})
