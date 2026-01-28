# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Portfolio MCP Server** - An MCP server for portfolio risk analysis and options monitoring. Integrates with Claude Desktop to analyze Charles Schwab CSV exports, generate alerts, and find optimal options trades.

**Key features:**
- Portfolio analysis with prioritized risk alerts
- Option chain data with real Greeks (from Polygon.io/ORATS)
- Covered call and cash-secured put trade finders
- Research prompt generation for deep analysis

## Tech Stack

- **Python 3.11+** with `uv` for dependency management
- **FastMCP** for MCP server implementation
- **Modal** for serverless cloud deployment
- **Polygon.io** for market data (stocks + options with Greeks)
- **Pandas** for CSV parsing and data manipulation
- **Langfuse** for observability and tracing

## Quick Commands

```bash
# Install dependencies
uv sync

# Run the MCP server directly
uv run portfolio-mcp

# Test with MCP inspector
npx @modelcontextprotocol/inspector uv --directory . run portfolio-mcp

# Run a specific function for testing
uv run python -c "from src.portfolio_mcp.tools import get_stock_quote; print(get_stock_quote('AAPL'))"
```

## Project Structure

```
portfolio-mcp/
├── src/portfolio_mcp/
│   ├── __init__.py       # Package init, exports run_server
│   ├── server.py         # FastMCP server (local stdio mode)
│   ├── tools.py          # Core business logic (analysis, Polygon API)
│   └── observability.py  # Langfuse tracing for tool calls
├── docs/
│   ├── options_data_api_research.md  # API provider comparison
│   └── langfuse/         # Langfuse integration docs
├── modal_app.py          # Modal cloud deployment (OAuth + HTTP)
├── .env                  # API keys (gitignored)
├── .env.example          # Template for .env
├── CLAUDE_PROJECT.md     # Claude Desktop project setup instructions
├── README.md             # User-facing documentation
└── pyproject.toml        # Python project config
```

## Key Files

### src/portfolio_mcp/tools.py
Core business logic including:
- `get_market_time()` - NYC timestamp and market session
- `analyze_portfolio(csv_content)` - Parse Schwab CSV, generate alerts
- `generate_research_prompts(analysis)` - Create research suggestions
- `get_stock_quote(symbol)` - Polygon.io stock data
- `get_option_chain(symbol, ...)` - Option chains with Greeks
- `find_covered_call(symbol, ...)` - Optimal CC candidates
- `find_cash_secured_put(symbol, ...)` - Optimal CSP candidates

### src/portfolio_mcp/server.py
FastMCP server that wraps tools.py functions as MCP tools.

## Environment Variables

Required in `.env`:
```
POLYGON_API_KEY=your_polygon_api_key_here
```

The code loads from `.env` file automatically. No need to set in Claude Desktop config.

## Data Provider: Polygon.io

- **Recommended plan:** Stocks Starter ($29/mo) + Options Starter ($29/mo) = $58/mo
- **Data delay:** 15 minutes (Starter plan limitation)
- **Greeks source:** ORATS (via Polygon snapshot API)

## Important Notes

1. **All market data is 15-minute delayed** - Always mention this when presenting prices
2. **Greeks are real** (from ORATS), not estimated
3. **Bid/ask quotes require Advanced plan** ($199/mo) - not available on Starter
4. **API key in .env is gitignored** - Never commit actual keys

## Testing Changes

After modifying tools.py or server.py:

```bash
# Quick test of a function
uv run python -c "from src.portfolio_mcp.tools import get_stock_quote; print(get_stock_quote('NVDA'))"

# Test with MCP inspector (interactive)
npx @modelcontextprotocol/inspector uv --directory . run portfolio-mcp

# Restart Claude Desktop to pick up changes
# Cmd+Q then reopen
```

## Claude Desktop Integration

The MCP server is configured in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "portfolio-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/portfolio-mcp",
        "run",
        "portfolio-mcp"
      ],
      "env": {}
    }
  }
}
```

Replace `/path/to/portfolio-mcp` with the actual path where you cloned this repository.

## Common Tasks

### Adding a new tool
1. Add function to `tools.py`
2. Add MCP wrapper in `server.py` with `@mcp.tool()` decorator
3. Update CLAUDE_PROJECT.md and README.md with tool description
4. Test with MCP inspector

### Updating Polygon.io integration
- API client created in `_get_polygon_client()` in tools.py
- Loads key from `.env` file automatically
- See Polygon Python client docs: https://polygon-api-client.readthedocs.io/

### Debugging MCP server issues
Check Claude Desktop logs:
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp-server-portfolio-mcp.log
```

## Cloud Deployment (Modal)

The server can be deployed to Modal for remote/mobile access.

### URL
https://chaosisnotrandomitisrhythmic--portfolio-mcp-web.modal.run

### Modal Secrets Required
```bash
# Market data
modal secret create polygon-api-key POLYGON_API_KEY=your_key

# Google OAuth
modal secret create google-oauth \
    GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com \
    GOOGLE_CLIENT_SECRET=GOCSPX-your_secret

# Allowed emails (comma-separated)
modal secret create mcp-allowed-emails ALLOWED_EMAILS=user@example.com

# JWT signing key
modal secret create mcp-jwt-key JWT_SIGNING_KEY=$(openssl rand -base64 32)

# Langfuse observability
modal secret create langfuse \
    LANGFUSE_SECRET_KEY=sk-lf-xxx \
    LANGFUSE_PUBLIC_KEY=pk-lf-xxx \
    LANGFUSE_HOST=https://cloud.langfuse.com
```

### Deploy Commands
```bash
# Local development (hot reload)
modal serve modal_app.py

# Production deployment
modal deploy modal_app.py

# Test tools directly (bypasses OAuth)
modal run modal_app.py::test_tools

# View logs
modal app logs portfolio-mcp
```

### Authentication
Uses Google OAuth via FastMCP's GoogleProvider:
- Claude Desktop: Add connector URL, OAuth flow handled automatically
- Claude Mobile: Add connector in app, login with Google when prompted
- Access restricted to emails in `mcp-allowed-emails` secret

## Observability (Langfuse)

Tool calls are traced with Langfuse when credentials are configured.

### What's Traced
- Tool name and duration
- Input arguments
- Output results
- User ID (from OAuth email)
- Errors

### View Traces
https://cloud.langfuse.com → Select project → Traces

### Key Files
- `src/portfolio_mcp/observability.py` - Tracing setup and decorators
- `modal_app.py` - Initializes tracing, applies `@observe_tool` to all tools

### Disabling Tracing
Simply remove the `langfuse` secret from Modal to disable tracing.
No code changes needed.
