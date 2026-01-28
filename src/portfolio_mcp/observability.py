"""Langfuse observability for MCP tool calls.

Uses Langfuse SDK v3 API (get_client, start_as_current_span).
Tracing failures are silently ignored to prevent breaking the MCP server.

Usage:
    from portfolio_mcp.observability import init_langfuse, trace_tool, flush_traces

    # At startup
    init_langfuse()

    # Wrap tool calls
    result = trace_tool("get_stock_quote", {"symbol": "AAPL"}, user_email)(
        lambda: tools.get_stock_quote("AAPL")
    )

    # At end of request
    flush_traces()
"""

import os
import time
from typing import Any, Callable

# Global state
_langfuse = None
_enabled = False


def init_langfuse() -> bool:
    """Initialize Langfuse tracing for MCP tool calls.

    Uses Langfuse SDK v3 API with get_client().
    Returns True if enabled, False otherwise.
    """
    global _langfuse, _enabled

    secret = os.environ.get("LANGFUSE_SECRET_KEY", "")
    public = os.environ.get("LANGFUSE_PUBLIC_KEY", "")

    if not secret or not public:
        print("Langfuse: disabled (no credentials)")
        return False

    try:
        from langfuse import get_client

        # get_client() returns a singleton Langfuse instance
        _langfuse = get_client()

        # Verify auth works
        if not _langfuse.auth_check():
            print("Langfuse: auth failed - disabled")
            _langfuse = None
            return False

        _enabled = True
        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        print(f"Langfuse: enabled ({host})")
        return True

    except Exception as e:
        print(f"Langfuse: init failed ({e}) - disabled")
        _langfuse = None
        _enabled = False
        return False


def trace_tool(
    tool_name: str,
    inputs: dict[str, Any],
    user_id: str | None = None,
) -> Callable[[Callable[[], Any]], Any]:
    """Trace a tool call with Langfuse.

    Uses Langfuse SDK v3 context manager API.
    Failures are silently ignored to prevent breaking tools.
    """

    def execute(func: Callable[[], Any]) -> Any:
        if not _enabled or _langfuse is None:
            return func()

        try:
            return _traced_execute(func, tool_name, inputs, user_id)
        except Exception as e:
            print(f"Langfuse: trace error ignored ({e})")
            return func()

    return execute


def _traced_execute(
    func: Callable[[], Any],
    tool_name: str,
    inputs: dict[str, Any],
    user_id: str | None,
) -> Any:
    """Execute function with Langfuse tracing using SDK v3 API."""

    # Use the context manager API from SDK v3
    # start_as_current_span creates a span and sets it as the current context
    with _langfuse.start_as_current_span(
        name=f"mcp-tool-{tool_name}",
        input=inputs,
    ) as span:
        # Update trace-level attributes if we have user_id
        if user_id:
            span.update_trace(user_id=user_id)

        # Add metadata
        span.update(
            metadata={
                "tool": tool_name,
                "mcp_server": "portfolio-mcp",
            }
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

            # Update span with result or error
            if error:
                span.update(
                    output={"error": str(error)},
                    level="ERROR",
                    status_message=str(error),
                    metadata={
                        "tool": tool_name,
                        "duration_ms": round(duration_ms, 2),
                        "success": False,
                    },
                )
            else:
                span.update(
                    output=result,
                    metadata={
                        "tool": tool_name,
                        "duration_ms": round(duration_ms, 2),
                        "success": True,
                    },
                )


def flush_traces() -> None:
    """Flush all pending traces to Langfuse.

    Important for serverless environments!
    """
    if _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception:
            pass


def is_enabled() -> bool:
    """Check if Langfuse tracing is currently enabled."""
    return _enabled
