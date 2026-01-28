"""Modal deployment for Portfolio MCP server.

Deploy a remote, stateless MCP server on Modal using FastMCP.
Uses streamable-http transport for full bidirectional MCP communication.
Secured with Bearer token authentication.

Usage:
    # Local development (hot reload)
    modal serve modal_app.py
    
    # Production deployment
    modal deploy modal_app.py
    
    # Test with MCP inspector
    npx @modelcontextprotocol/inspector
    # Connect to: http://localhost:8000/mcp/ (local) or Modal URL (deployed)
    # Transport: Streamable HTTP
    # Header: Authorization: Bearer <your-token>

Prerequisites:
    # Install Modal CLI
    pip install modal
    
    # Authenticate
    modal token new
    
    # Create secrets
    modal secret create polygon-api-key POLYGON_API_KEY=your_key_here
    modal secret create mcp-auth-token MCP_AUTH_TOKEN=your_secure_token_here

Authentication:
    All requests must include an Authorization header:
    Authorization: Bearer <MCP_AUTH_TOKEN>
    
    For Claude Desktop, use mcp-remote with --header flag:
    npx mcp-remote https://...modal.run/mcp --header "Authorization:Bearer <token>"
"""

import modal
from pathlib import Path

# Define the Modal app
app = modal.App("portfolio-mcp")

# Get the local source directory
local_src = Path(__file__).parent / "src"

# Build the container image with all dependencies
# Mount local source code for development
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastmcp>=2.10.6",
        "fastapi>=0.115.0",
        "pandas>=2.0.0",
        "polygon-api-client>=1.14.0",
    )
    .add_local_dir(local_src, remote_path="/root/src")
)


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("polygon-api-key"),
        modal.Secret.from_name("mcp-auth-token"),
    ],
)
@modal.asgi_app()
def web():
    """ASGI web endpoint for the MCP server.
    
    Returns a FastAPI app with the MCP server mounted at /mcp/.
    Uses streamable-http transport with stateless_http=True for serverless.
    Secured with Bearer token authentication.
    """
    import os
    import sys
    # Add source path for imports
    sys.path.insert(0, "/root/src")
    
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware
    
    # Import the MCP server instance
    from portfolio_mcp.server import mcp
    
    # Get auth token from environment
    AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN")
    
    class BearerAuthMiddleware(BaseHTTPMiddleware):
        """Middleware to check for Bearer token authentication."""
        
        async def dispatch(self, request: Request, call_next):
            # Skip auth for health check endpoint
            if request.url.path == "/health":
                return await call_next(request)
            
            # Check Authorization header
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing Authorization header"},
                )
            
            # Validate Bearer token
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid Authorization header format. Use: Bearer <token>"},
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            if token != AUTH_TOKEN:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid token"},
                )
            
            return await call_next(request)
    
    # Create the MCP HTTP app with stateless mode for serverless
    mcp_app = mcp.http_app(
        transport="streamable-http",
        stateless_http=True,
    )
    
    # Mount in FastAPI with proper lifespan handling
    fastapi_app = FastAPI(
        title="Portfolio MCP",
        description="Portfolio risk analysis and options monitoring MCP server (authenticated)",
        lifespan=mcp_app.router.lifespan_context,
    )
    
    # Add authentication middleware
    fastapi_app.add_middleware(BearerAuthMiddleware)
    
    # Add health check endpoint (unauthenticated)
    @fastapi_app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    fastapi_app.mount("/", mcp_app, "mcp")
    
    return fastapi_app


# Optional: Test function to verify deployment
@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("polygon-api-key"),
        modal.Secret.from_name("mcp-auth-token"),
    ],
)
async def test_tools():
    """Test the MCP server tools after deployment.
    
    Run with: modal run modal_app.py::test_tools
    """
    import os
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport
    
    # Get auth token
    auth_token = os.environ.get("MCP_AUTH_TOKEN")
    
    # Connect to the deployed server with auth header
    transport = StreamableHttpTransport(
        url=f"{web.get_web_url()}/mcp/",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    client = Client(transport)
    
    async with client:
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}")
        
        # Test get_market_time
        result = await client.call_tool("mcp_get_market_time")
        print(f"\nMarket time: {result.data}")
