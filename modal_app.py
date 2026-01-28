"""Modal deployment for Portfolio MCP server.

Deploy a remote, stateless MCP server on Modal using FastMCP.
Uses streamable-http transport for full bidirectional MCP communication.
Secured with Google OAuth authentication for mobile access.

Usage:
    # Local development (hot reload)
    modal serve modal_app.py
    
    # Production deployment
    modal deploy modal_app.py
    
    # Test with MCP inspector
    npx @modelcontextprotocol/inspector
    # Connect to: http://localhost:8000/mcp/ (local) or Modal URL (deployed)
    # Transport: Streamable HTTP

Prerequisites:
    # Install Modal CLI
    pip install modal
    
    # Authenticate
    modal token new
    
    # Create secrets
    modal secret create polygon-api-key POLYGON_API_KEY=your_key_here
    modal secret create google-oauth \
        GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com \
        GOOGLE_CLIENT_SECRET=GOCSPX-your_secret

Authentication:
    Uses Google OAuth via FastMCP's GoogleProvider.
    - Claude Desktop: Add connector URL, OAuth flow handled automatically
    - Claude Mobile: Add connector in app, login with Google when prompted
    - MCP Inspector: Use auth=oauth option
"""

import modal
from pathlib import Path

# Define the Modal app
# Updated: 2026-01-28 for OAuth storage fix
app = modal.App("portfolio-mcp")

# Get the local source directory
local_src = Path(__file__).parent / "src"

# Create a Dict for persistent OAuth client storage (shared across instances)
oauth_dict = modal.Dict.from_name("portfolio-mcp-oauth", create_if_missing=True)

# Build the container image with all dependencies
# Mount local source code for development
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastmcp>=2.12.0",  # 2.12.0+ required for GoogleProvider
        "fastapi>=0.115.0",
        "pandas>=2.0.0",
        "polygon-api-client>=1.14.0",
        # Langfuse observability
        "langfuse>=3.0.0",
    )
    .add_local_dir(local_src, remote_path="/root/src")
)

# Langfuse secret for observability
langfuse_secret = modal.Secret.from_name("langfuse")


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("polygon-api-key"),
        modal.Secret.from_name("google-oauth"),
        modal.Secret.from_name("mcp-allowed-emails"),
        modal.Secret.from_name("mcp-jwt-key"),
        langfuse_secret,
    ],
)
@modal.asgi_app()
def web():
    """ASGI web endpoint for the MCP server.

    Returns a FastAPI app with the MCP server mounted at /mcp/.
    Uses streamable-http transport with stateless_http=True for serverless.
    Secured with Google OAuth + email allowlist.
    Uses Modal Dict for persistent OAuth client storage.
    """
    import os
    import sys

    # Add source path for imports
    sys.path.insert(0, "/root/src")

    from typing import Any

    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.google import GoogleProvider

    # Import tools and observability from our package
    from portfolio_mcp import tools
    from portfolio_mcp.observability import init_langfuse, trace_tool, flush_traces

    # Initialize Langfuse tracing (no-op if credentials not set)
    init_langfuse()

    # Load allowed emails from environment (comma-separated)
    ALLOWED_EMAILS = set(
        email.strip().lower()
        for email in os.environ.get("ALLOWED_EMAILS", "").split(",")
        if email.strip()
    )

    class ModalDictStore:
        """Async key-value store using Modal Dict.

        Implements the interface expected by FastMCP's client_storage parameter.
        Modal Dict provides persistent, shared storage across all function instances.

        Interface methods: get, put, delete, exists (per pydocket/key_value)
        """

        async def get(self, key: str, **kwargs) -> Any:
            """Get a value by key."""
            # kwargs may include 'collection' which we ignore (single namespace)
            try:
                return oauth_dict[key]
            except KeyError:
                return None

        async def put(self, key: str, value: Any, **kwargs) -> None:
            """Store a value by key."""
            # kwargs may include 'collection', 'ttl' which we ignore
            oauth_dict[key] = value

        async def delete(self, key: str, **kwargs) -> None:
            """Delete a key."""
            try:
                del oauth_dict[key]
            except KeyError:
                pass

        async def exists(self, key: str, **kwargs) -> bool:
            """Check if a key exists."""
            return key in oauth_dict

        async def keys(self, **kwargs) -> list:
            """List all keys."""
            return list(oauth_dict.keys())

    # Create persistent store using Modal Dict
    client_store = ModalDictStore()

    # Configure Google OAuth with Modal Volume storage
    auth_provider = GoogleProvider(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        base_url="https://chaosisnotrandomitisrhythmic--portfolio-mcp-web.modal.run",
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        # JWT signing key for consistent token validation
        jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
        # Persistent client storage using Modal Volume
        client_storage=client_store,
    )

    # Create MCP server with OAuth authentication
    mcp = FastMCP(
        name="portfolio-mcp",
        auth=auth_provider,
        instructions="""
        Portfolio risk analysis for Charles Schwab accounts.

        **⚠️ IMPORTANT: ALL MARKET DATA IS 15-MINUTE DELAYED**

        This server uses Polygon.io Starter plan. Stock quotes, option chains,
        and Greeks are delayed by 15 minutes. Always mention this when presenting
        prices to users. Use for analysis and planning, NOT real-time execution.
        """,
    )

    def check_email_authorized() -> str:
        """Check if the authenticated user's email is in the allowlist.

        Returns the user's email if authorized.
        Raises PermissionError if not authorized.
        """
        from fastmcp.server.dependencies import get_access_token

        token = get_access_token()

        if not token or not token.claims:
            raise PermissionError("No authentication token found")

        user_email = token.claims.get("email", "").lower()

        if not user_email:
            raise PermissionError("No email found in token")

        if user_email not in ALLOWED_EMAILS:
            raise PermissionError(
                f"Access denied. Email '{user_email}' is not authorized."
            )

        return user_email

    # Register all tools with email authorization and observability tracing
    @mcp.tool()
    def mcp_get_market_time() -> dict:
        """Get current NYC market time and session status."""
        user_email = check_email_authorized()
        result = trace_tool("get_market_time", {}, user_email)(
            lambda: tools.get_market_time()
        )
        flush_traces()
        return result

    @mcp.tool()
    def mcp_analyze_portfolio(csv_content: str) -> dict:
        """Analyze a Charles Schwab portfolio CSV export."""
        user_email = check_email_authorized()
        result = trace_tool(
            "analyze_portfolio", {"csv_length": len(csv_content)}, user_email
        )(lambda: tools.analyze_portfolio(csv_content))
        flush_traces()
        return result

    @mcp.tool()
    def mcp_generate_research_prompts(analysis: dict) -> dict:
        """Generate research prompts based on portfolio analysis."""
        user_email = check_email_authorized()
        result = trace_tool(
            "generate_research_prompts",
            {"analysis_keys": list(analysis.keys())},
            user_email,
        )(lambda: tools.generate_research_prompts(analysis))
        flush_traces()
        return result

    @mcp.tool()
    def mcp_get_stock_quote(symbol: str) -> dict:
        """Get stock quote from Polygon.io (15-min delayed)."""
        user_email = check_email_authorized()
        result = trace_tool("get_stock_quote", {"symbol": symbol}, user_email)(
            lambda: tools.get_stock_quote(symbol)
        )
        flush_traces()
        return result

    @mcp.tool()
    def mcp_get_option_chain(
        symbol: str,
        expiration_date: str | None = None,
        option_type: str | None = None,
        strike_price_gte: float | None = None,
        strike_price_lte: float | None = None,
        limit: int = 20,
    ) -> dict:
        """Get option chain with Greeks from Polygon.io (15-min delayed)."""
        user_email = check_email_authorized()
        inputs = {
            "symbol": symbol,
            "expiration_date": expiration_date,
            "option_type": option_type,
            "strike_price_gte": strike_price_gte,
            "strike_price_lte": strike_price_lte,
            "limit": limit,
        }
        result = trace_tool("get_option_chain", inputs, user_email)(
            lambda: tools.get_option_chain(
                symbol,
                expiration_date,
                option_type,
                strike_price_gte,
                strike_price_lte,
                limit,
            )
        )
        flush_traces()
        return result

    @mcp.tool()
    def mcp_find_covered_call(
        symbol: str,
        shares: int = 100,
        min_premium: float = 0.50,
        max_delta: float = 0.30,
        min_days: int = 7,
        max_days: int = 45,
    ) -> dict:
        """Find optimal covered call candidates."""
        user_email = check_email_authorized()
        inputs = {
            "symbol": symbol,
            "shares": shares,
            "min_premium": min_premium,
            "max_delta": max_delta,
            "min_days": min_days,
            "max_days": max_days,
        }
        result = trace_tool("find_covered_call", inputs, user_email)(
            lambda: tools.find_covered_call(
                symbol, shares, min_premium, max_delta, min_days, max_days
            )
        )
        flush_traces()
        return result

    @mcp.tool()
    def mcp_find_cash_secured_put(
        symbol: str,
        cash_available: float,
        min_premium: float = 0.50,
        max_delta: float = -0.30,
        min_days: int = 7,
        max_days: int = 45,
    ) -> dict:
        """Find optimal cash-secured put candidates."""
        user_email = check_email_authorized()
        inputs = {
            "symbol": symbol,
            "cash_available": cash_available,
            "min_premium": min_premium,
            "max_delta": max_delta,
            "min_days": min_days,
            "max_days": max_days,
        }
        result = trace_tool("find_cash_secured_put", inputs, user_email)(
            lambda: tools.find_cash_secured_put(
                symbol, cash_available, min_premium, max_delta, min_days, max_days
            )
        )
        flush_traces()
        return result

    # Create the HTTP app with OAuth
    return mcp.http_app(
        transport="streamable-http",
        stateless_http=True,
    )


# Optional: Test function to verify deployment (without OAuth)
@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("polygon-api-key"),
    ],
)
async def test_tools():
    """Test the MCP server tools directly (bypasses OAuth).

    Run with: modal run modal_app.py::test_tools

    Note: This tests the tool functions directly, not through the
    OAuth-protected HTTP endpoint. For full OAuth testing, use
    Claude Desktop or the MCP inspector with auth=oauth.
    """
    import sys

    sys.path.insert(0, "/root/src")

    from portfolio_mcp import tools

    print("Testing tools directly...")

    # Test get_market_time
    result = tools.get_market_time()
    print(f"\nMarket time: {result}")

    # Test get_stock_quote
    result = tools.get_stock_quote("AAPL")
    print(f"\nAAPL quote: {result}")
