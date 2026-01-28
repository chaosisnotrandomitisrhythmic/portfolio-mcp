"""Langfuse observability for MCP tool calls.

This module provides OPTIONAL tracing for MCP tool invocations.
Tracing failures are silently ignored to prevent breaking the MCP server.

Usage:
    from portfolio_mcp.observability import init_langfuse, trace_tool, flush_traces

    # At startup
    init_langfuse()

    # Wrap tool calls (fails gracefully if Langfuse not working)
    result = trace_tool("get_stock_quote", {"symbol": "AAPL"}, user_email)(
        lambda: tools.get_stock_quote("AAPL")
    )

    # At end of request
    flush_traces()
"""

import os
import time
from typing import Any, Callable

# Global Langfuse client
_langfuse = None
_enabled = False


def init_langfuse() -> bool:
    """Initialize Langfuse tracing for MCP tool calls.

    Call once at server startup. Returns True if enabled, False otherwise.
    Failures are caught and logged - never raises exceptions.
    """
    global _langfuse, _enabled

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
            print("Langfuse auth failed - tracing disabled")
            _langfuse = None
            return False

        _enabled = True
        print(f"Langfuse tracing enabled ({host})")
        return True

    except Exception as e:
        print(f"Langfuse init failed: {e} - tracing disabled")
        _langfuse = None
        _enabled = False
        return False


def trace_tool(
    tool_name: str,
    inputs: dict[str, Any],
    user_id: str | None = None,
) -> Callable[[Callable[[], Any]], Any]:
    """Trace a tool call with Langfuse.

    IMPORTANT: This function NEVER raises exceptions.
    If tracing fails, it silently continues without tracing.

    Usage:
        result = trace_tool("get_stock_quote", {"symbol": "AAPL"}, user_email)(
            lambda: tools.get_stock_quote("AAPL")
        )
    """

    def execute(func: Callable[[], Any]) -> Any:
        # If Langfuse not enabled, just run the function
        if not _enabled or _langfuse is None:
            return func()

        # Try to trace, but NEVER let tracing errors break the tool
        try:
            return _traced_execute(func, tool_name, inputs, user_id)
        except Exception as e:
            # Tracing failed - log and continue without tracing
            print(f"Langfuse trace error (ignored): {e}")
            return func()

    return execute


def _traced_execute(
    func: Callable[[], Any],
    tool_name: str,
    inputs: dict[str, Any],
    user_id: str | None,
) -> Any:
    """Internal traced execution - may raise exceptions."""
    # Try different Langfuse API versions
    trace = None
    span = None

    # Try to create a trace (API varies by version)
    if hasattr(_langfuse, 'trace'):
        trace = _langfuse.trace(
            name=f"mcp-tool-{tool_name}",
            user_id=user_id,
            metadata={"tool": tool_name},
        )
    elif hasattr(_langfuse, 'create_trace'):
        trace = _langfuse.create_trace(
            name=f"mcp-tool-{tool_name}",
            user_id=user_id,
            metadata={"tool": tool_name},
        )
    else:
        # No known trace method - just run function
        return func()

    # Create span if trace was created
    if trace and hasattr(trace, 'span'):
        span = trace.span(name=tool_name, input=inputs)

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

        # End span if it exists
        if span:
            try:
                if error:
                    span.end(output={"error": str(error)}, level="ERROR")
                else:
                    span.end(output=result)
            except Exception:
                pass  # Ignore span errors

        # Update trace if it exists
        if trace and hasattr(trace, 'update'):
            try:
                trace.update(metadata={
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                    "success": error is None,
                })
            except Exception:
                pass  # Ignore trace errors


def flush_traces() -> None:
    """Flush all pending traces to Langfuse.

    Safe to call even if Langfuse is not enabled - does nothing.
    """
    if _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception:
            pass  # Ignore flush errors


def is_enabled() -> bool:
    """Check if Langfuse tracing is currently enabled."""
    return _enabled
