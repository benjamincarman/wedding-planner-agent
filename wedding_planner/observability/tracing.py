"""Distributed OpenTelemetry tracing implementation linking spans from user query to tool actions."""

from functools import wraps
from typing import Any, Callable, Dict, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# Initialize Tracer Provider with resource metadata
resource = Resource.create({"service.name": "wedding-planner-agent", "environment": "production"})
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# Obtain package tracer
tracer = trace.get_tracer("wedding_planner.tracer")


def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to trace function executions as OpenTelemetry spans."""
    def decorator(func: Callable):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, str(v))
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(trace.StatusCode.ERROR, description=str(e))
                    span.record_exception(e)
                    raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, str(v))
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(trace.StatusCode.ERROR, description=str(e))
                    span.record_exception(e)
                    raise

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
