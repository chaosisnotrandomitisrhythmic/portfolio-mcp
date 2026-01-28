"""Modal deployment for Portfolio MCP server.

Deploy a remote, stateless MCP server on Modal using FastMCP.
Uses streamable-http transport for full bidirectional MCP communication.

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
    
    # Create Polygon API secret
    modal secret create polygon-api-key POLYGON_API_KEY=your_key_here
"""

import modal

# Define the Modal app
app = modal.App("portfolio-mcp")

# Build the container image with all dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastmcp>=2.10.6",
    "fastapi>=0.115.0",
    "pandas>=2.0.0",
    "polygon-api-client>=1.14.0",
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("polygon-api-key")],
)
@modal.asgi_app()
def web():
    """ASGI web endpoint for the MCP server.
    
    Returns a FastAPI app with the MCP server mounted at /mcp/.
    Uses streamable-http transport with stateless_http=True for serverless.
    """
    from fastapi import FastAPI
    
    # Import the MCP server instance
    from src.portfolio_mcp.server import mcp
    
    # Create the MCP HTTP app with stateless mode for serverless
    mcp_app = mcp.http_app(
        transport="streamable-http",
        stateless_http=True,
    )
    
    # Mount in FastAPI with proper lifespan handling
    fastapi_app = FastAPI(
        title="Portfolio MCP",
        description="Portfolio risk analysis and options monitoring MCP server",
        lifespan=mcp_app.router.lifespan_context,
    )
    fastapi_app.mount("/", mcp_app, "mcp")
    
    return fastapi_app


# Optional: Test function to verify deployment
@app.function(image=image)
async def test_tools():
    """Test the MCP server tools after deployment.
    
    Run with: modal run modal_app.py::test_tools
    """
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport
    
    # Connect to the deployed server
    transport = StreamableHttpTransport(url=f"{web.get_web_url()}/mcp/")
    client = Client(transport)
    
    async with client:
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}")
        
        # Test get_market_time
        result = await client.call_tool("mcp_get_market_time")
        print(f"\nMarket time: {result.data}")
