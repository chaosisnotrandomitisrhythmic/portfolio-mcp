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


# =============================================================================
# FastMCP Middleware for Auth + Tracing
# =============================================================================


class AuthAndTracingMiddleware:
    """FastMCP middleware that adds OAuth authorization and Langfuse tracing.

    This middleware intercepts all tool calls and:
    1. Checks that the user's email is in the allowed list
    2. Traces the call with Langfuse (if enabled)
    3. Flushes traces after each call (important for serverless)

    Usage:
        from portfolio_mcp.observability import AuthAndTracingMiddleware

        mcp.add_middleware(AuthAndTracingMiddleware(
            allowed_emails={"user@example.com"},
            require_auth=True,
        ))
    """

    def __init__(
        self,
        allowed_emails: set[str] | None = None,
        require_auth: bool = True,
    ):
        """Initialize the middleware.

        Args:
            allowed_emails: Set of allowed email addresses (lowercase).
                           If None, all authenticated users are allowed.
            require_auth: If True, require authentication. If False, allow
                         unauthenticated requests (useful for local dev).
        """
        self.allowed_emails = allowed_emails or set()
        self.require_auth = require_auth

    def _get_user_email(self) -> str | None:
        """Get the authenticated user's email from the access token.

        Returns the email if authenticated, None otherwise.
        Raises PermissionError if auth is required but not present.
        """
        try:
            from fastmcp.server.dependencies import get_access_token

            token = get_access_token()

            if not token or not token.claims:
                if self.require_auth:
                    raise PermissionError("No authentication token found")
                return None

            user_email = token.claims.get("email", "").lower()

            if not user_email:
                if self.require_auth:
                    raise PermissionError("No email found in token")
                return None

            # Check allowlist if configured
            if self.allowed_emails and user_email not in self.allowed_emails:
                raise PermissionError(
                    f"Access denied. Email '{user_email}' is not authorized."
                )

            return user_email

        except ImportError:
            # FastMCP dependencies not available (e.g., local stdio mode)
            if self.require_auth:
                raise PermissionError("Auth dependencies not available")
            return None

    async def on_call_tool(self, context, call_next):
        """Intercept tool calls to add auth check and tracing.

        Args:
            context: MiddlewareContext with message.name and message.arguments
            call_next: Function to call the next middleware/handler
        """
        tool_name = context.message.name
        arguments = dict(context.message.arguments) if context.message.arguments else {}

        # Check authorization
        user_email = self._get_user_email()

        # Execute with tracing
        if _enabled and _langfuse is not None:
            result = await self._traced_call(
                call_next, context, tool_name, arguments, user_email
            )
        else:
            result = await call_next(context)

        # Flush traces (important for serverless)
        flush_traces()

        return result

    async def _traced_call(
        self,
        call_next,
        context,
        tool_name: str,
        arguments: dict,
        user_email: str | None,
    ):
        """Execute tool call with Langfuse tracing."""
        import time

        with _langfuse.start_as_current_span(
            name=f"mcp-tool-{tool_name}",
            input=arguments,
        ) as span:
            if user_email:
                span.update_trace(user_id=user_email)

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
                result = await call_next(context)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000

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
                    # For async results, we may need to handle differently
                    span.update(
                        output=str(result)[:1000] if result else None,
                        metadata={
                            "tool": tool_name,
                            "duration_ms": round(duration_ms, 2),
                            "success": True,
                        },
                    )
