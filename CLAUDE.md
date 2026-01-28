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
- **Polygon.io** for market data (stocks + options with Greeks)
- **Modal** for serverless cloud deployment with Google OAuth
- **Pandas** for CSV parsing and data manipulation

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
│   ├── __init__.py      # Package init, exports run_server
│   ├── server.py        # FastMCP server definition and tool wrappers (local)
│   └── tools.py         # Core business logic (analysis, Polygon API)
├── modal_app.py          # Modal cloud deployment with Google OAuth
├── docs/
│   └── options_data_api_research.md  # API provider comparison
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

## Cloud Deployment (Modal)

The server is deployed to Modal for mobile/remote access with Google OAuth.

### Deployment URL
```
https://chaosisnotrandomitisrhythmic--portfolio-mcp-web.modal.run/mcp
```

### Key Files
- `modal_app.py` - Modal deployment configuration with OAuth

### Modal Secrets
- `polygon-api-key` - Polygon.io API key
- `google-oauth` - Google OAuth client ID and secret
- `mcp-jwt-key` - JWT signing key for token validation
- `mcp-allowed-emails` - Comma-separated list of authorized emails

### Modal Resources
- `portfolio-mcp-oauth` (Dict) - Persistent OAuth client storage

### Deploy Commands
```bash
# Deploy to Modal
modal deploy modal_app.py

# Check logs
modal app logs portfolio-mcp

# Test tools directly (bypasses OAuth)
modal run modal_app.py::test_tools
```

### Authentication Flow
1. User connects via Claude Desktop/iOS with connector URL
2. Server redirects to Google OAuth
3. User authenticates with Google
4. Server validates email against allowlist
5. If authorized, user can access tools

### Adding Authorized Users
```bash
modal secret create mcp-allowed-emails --force \
  ALLOWED_EMAILS=user1@example.com,user2@example.com
modal deploy modal_app.py
```

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
