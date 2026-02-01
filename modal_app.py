"""Modal deployment for Portfolio MCP server.

Deploy a remote, stateless MCP server on Modal using FastMCP.
Uses streamable-http transport for full bidirectional MCP communication.
Secured with Google OAuth authentication for mobile access.

Architecture:
    - Tools are defined ONCE in server.py (single source of truth)
    - This file imports the mcp instance and adds:
        - Google OAuth authentication
        - Langfuse tracing via middleware
        - Email allowlist authorization

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
    modal secret create mcp-allowed-emails ALLOWED_EMAILS=user@example.com
    modal secret create mcp-jwt-key JWT_SIGNING_KEY=$(openssl rand -base64 32)
    modal secret create langfuse \
        LANGFUSE_SECRET_KEY=sk-lf-xxx \
        LANGFUSE_PUBLIC_KEY=pk-lf-xxx

Authentication:
    Uses Google OAuth via FastMCP's GoogleProvider.
    - Claude Desktop: Add connector URL, OAuth flow handled automatically
    - Claude Mobile: Add connector in app, login with Google when prompted
    - MCP Inspector: Use auth=oauth option
"""

import modal
from pathlib import Path

# Define the Modal app
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
    
    Tools are imported from server.py (single source of truth).
    Auth and tracing are added via middleware.
    """
    import os
    import sys

    # Add source path for imports
    sys.path.insert(0, "/root/src")

    from typing import Any

    from fastmcp.server.auth.providers.google import GoogleProvider

    # Import the MCP server with all tools already registered
    from portfolio_mcp.server import mcp

    # Import observability utilities
    from portfolio_mcp.observability import (
        init_langfuse,
        AuthAndTracingMiddleware,
    )

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
        """

        async def get(self, key: str, **kwargs) -> Any:
            try:
                return oauth_dict[key]
            except KeyError:
                return None

        async def put(self, key: str, value: Any, **kwargs) -> None:
            oauth_dict[key] = value

        async def delete(self, key: str, **kwargs) -> None:
            try:
                del oauth_dict[key]
            except KeyError:
                pass

        async def exists(self, key: str, **kwargs) -> bool:
            return key in oauth_dict

        async def keys(self, **kwargs) -> list:
            return list(oauth_dict.keys())

    # Configure Google OAuth
    auth_provider = GoogleProvider(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        base_url="https://chaosisnotrandomitisrhythmic--portfolio-mcp-web.modal.run",
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
        client_storage=ModalDictStore(),
    )

    # Configure the imported MCP server with auth and middleware
    mcp.auth = auth_provider

    # Add auth + tracing middleware
    mcp.add_middleware(
        AuthAndTracingMiddleware(
            allowed_emails=ALLOWED_EMAILS,
            require_auth=True,
        )
    )

    # Create the HTTP app
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
