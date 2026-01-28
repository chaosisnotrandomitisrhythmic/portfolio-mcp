"""Langfuse observability for MCP tool calls.

This module provides tracing for MCP tool invocations using Langfuse.
When credentials are set, all tool calls are traced with their inputs,
outputs, duration, user, and any errors.

Usage:
    from portfolio_mcp.observability import init_langfuse, trace_tool, flush_traces

    # At startup
    init_langfuse()

    # Wrap tool calls
    result = trace_tool("get_stock_quote", {"symbol": "AAPL"}, user_email)(
        lambda: tools.get_stock_quote("AAPL")
    )

    # At end of request (important for serverless!)
    flush_traces()
"""

import os
import time
from typing import Any, Callable

# Global Langfuse client
_langfuse = None


def init_langfuse() -> bool:
    """Initialize Langfuse tracing for MCP tool calls.

    Call once at server startup. Returns True if enabled, False otherwise.

    Environment variables:
        LANGFUSE_SECRET_KEY: Secret key (required to enable)
        LANGFUSE_PUBLIC_KEY: Public key (required to enable)
        LANGFUSE_HOST: API URL (default: https://cloud.langfuse.com)
    """
    global _langfuse

    secret = os.environ.get("LANGFUSE_SECRET_KEY", "")
    public = os.environ.get("LANGFUSE_PUBLIC_KEY", "")

    if not secret or not public:
        print("Langfuse tracing disabled (no credentials)")
        return False

    try:
        from langfuse import Langfuse

        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        _langfuse = Langfuse(
            secret_key=secret,
            public_key=public,
            host=host,
        )

        # Verify auth works
        if not _langfuse.auth_check():
            print("⚠ Langfuse authentication failed - check your API keys")
            _langfuse = None
            return False

        print(f"✓ Langfuse tracing enabled ({host})")
        return True

    except ImportError as e:
        print(f"⚠ Langfuse not installed: {e}")
        return False
    except Exception as e:
        print(f"⚠ Langfuse initialization failed: {e}")
        return False


def trace_tool(
    tool_name: str,
    inputs: dict[str, Any],
    user_id: str | None = None,
) -> Callable[[Callable[[], Any]], Any]:
    """Trace a tool call with Langfuse.

    Usage:
        result = trace_tool("get_stock_quote", {"symbol": "AAPL"}, user_email)(
            lambda: tools.get_stock_quote("AAPL")
        )

    Args:
        tool_name: Name of the tool being called
        inputs: Dictionary of input arguments
        user_id: Optional user identifier (e.g., email)

    Returns:
        A callable that takes a function and executes it with tracing
    """

    def execute(func: Callable[[], Any]) -> Any:
        if _langfuse is None:
            return func()

        # Create a trace for this tool call
        trace = _langfuse.trace(
            name=f"mcp-tool-{tool_name}",
            user_id=user_id,
            metadata={"tool": tool_name},
        )

        # Create a span for the actual execution
        span = trace.span(
            name=tool_name,
            input=inputs,
        )

        start_time = time.time()
        error = None
        result = None

        try:
            result = func()
            return result
        except Exception as e:
            error = e
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # End the span with result or error
            if error:
                span.end(
                    output={"error": str(error)},
                    level="ERROR",
                    status_message=str(error),
                )
            else:
                span.end(output=result)

            # Update trace with duration
            trace.update(
                metadata={
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                    "success": error is None,
                }
            )

    return execute


def flush_traces() -> None:
    """Flush all pending traces to Langfuse.

    IMPORTANT: Call this at the end of each request in serverless environments!
    Otherwise traces may be lost when the container is recycled.
    """
    if _langfuse is not None:
        _langfuse.flush()


def is_enabled() -> bool:
    """Check if Langfuse tracing is currently enabled."""
    return _langfuse is not None
