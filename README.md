# Portfolio MCP Server

An MCP (Model Context Protocol) server for portfolio risk analysis and options monitoring. Integrates with Claude Desktop to analyze brokerage CSV exports, generate prioritized alerts, and find optimal options trades.

## Features

- **Portfolio Analysis** - Upload CSV exports to get instant risk alerts
- **Option Chain Data** - Real Greeks (delta, gamma, theta, vega) from ORATS via Polygon.io
- **Trade Finders** - Discover optimal covered calls and cash-secured puts
- **Research Integration** - Generate prompts for deep analysis in Claude's Research mode
- **Temporal Awareness** - Market session detection and timestamped research documents

## How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Schwab CSV     │────▶│  Portfolio MCP  │────▶│  Claude Desktop │
│  Export         │     │  Server         │     │  Analysis       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Polygon.io     │
                        │  Market Data    │
                        └─────────────────┘
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/yourusername/portfolio-mcp.git
cd portfolio-mcp
uv sync

# Configure API key
cp .env.example .env
# Edit .env and add your Polygon.io API key

# Test the server
npx @modelcontextprotocol/inspector uv --directory . run portfolio-mcp
```

## API Key Setup

This server requires a [Polygon.io](https://polygon.io) API key for market data.

**Recommended:** Stocks Starter ($29/mo) + Options Starter ($29/mo) = $58/mo

1. Sign up at [polygon.io](https://polygon.io/pricing)
2. Get your API key from the dashboard
3. Add to `.env`: `POLYGON_API_KEY=your_key_here`

> **Note:** All market data is 15-minute delayed on Starter plans. Sufficient for daily analysis but not real-time execution.

## Daily Workflow

### Phase 1: Quick Analysis
1. **Export from Schwab**: Accounts → Positions → Export → CSV
2. **Upload to Claude Desktop**: Use the attachment button
3. **Say "daily check"**: Get timestamp, alerts, and research suggestions

### Phase 2: Deep Research
4. **Enable Research mode** in Claude Desktop
5. **Run suggested prompts**: Web search for IV, news, analyst ratings
6. **Click "Add to Project"** on research output

### Phase 3: Knowledge Accumulation
- Research documents accumulate in project
- Claude's RAG retrieves them in future conversations
- Patterns emerge over weeks of daily analysis

## Tools

### Portfolio Analysis

| Tool | Description |
|------|-------------|
| `get_market_time` | NYC timestamp + market session (REGULAR/PRE_MARKET/AFTER_HOURS/WEEKEND) |
| `analyze_portfolio` | Alerts, summary, and holdings from CSV |
| `generate_research_prompts` | Research prompts based on alerts for Research mode |

### Options Data (15-min delayed)

| Tool | Description |
|------|-------------|
| `get_stock_quote` | Current price, change, volume, VWAP, market cap |
| `get_option_chain` | Fetch calls/puts with real Greeks and IV |
| `find_covered_call` | Find optimal CC candidates ranked by target delta |
| `find_cash_secured_put` | Find optimal CSP candidates for available cash |

### Example: Finding a Covered Call

```
User: "Find covered call options for my 100 NVDA shares targeting 0.20 delta"

Returns top 10 candidates with:
- Strike, expiration, DTE
- Last price, IV, real delta (from ORATS)
- Premium $, premium %, annualized return
- Upside to strike, max return, breakeven
```

## Alert Types

| Alert | Meaning |
|-------|---------|
| 🚨 ITM Options | Short options in the money - assignment risk |
| 💰 Cash Shortage | Not enough cash for short put exposure |
| ⚠️ High Delta | Assignment risk (delta > 0.5) |
| ⏰ Expiring Soon | Options expiring within 7 days |
| 📉 Large Losses | Positions down >10% |
| ⚠️ Naked Options | Short options without underlying |

## Setup Options

### Option 1: Cloud (Modal) - Recommended for Mobile

The MCP server is deployed to Modal with Google OAuth authentication, enabling access from Claude iOS/Android and Claude Desktop.

**Claude Desktop (remote):**
```json
{
  "mcpServers": {
    "portfolio-mcp-remote": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://chaosisnotrandomitisrhythmic--portfolio-mcp-web.modal.run/mcp"],
      "env": {}
    }
  }
}
```

**Claude iOS/Android:**
1. Open Claude app → Settings → Integrations
2. Add connector URL: `https://chaosisnotrandomitisrhythmic--portfolio-mcp-web.modal.run/mcp`
3. Login with authorized Google account when prompted

### Option 2: Local (stdio)

For local-only usage without cloud deployment:

```json
{
  "mcpServers": {
    "portfolio-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/portfolio-mcp", "run", "portfolio-mcp"],
      "env": {}
    }
  }
}
```

Replace `/path/to/portfolio-mcp` with your actual installation path.

See [CLAUDE_PROJECT.md](CLAUDE_PROJECT.md) for complete project setup instructions.

## Data Format

Supports Charles Schwab "Individual Positions" CSV exports with columns:
- Symbol, Qty, Price, Mkt Val
- Gain %, Security Type, Delta

Handles Schwab's Excel-escaped format (`="$186.23"`).

## Cloud Deployment (Modal)

The server can be deployed to [Modal](https://modal.com) for remote access with Google OAuth authentication.

### Prerequisites

```bash
pip install modal
modal token new
```

### Modal Secrets Required

```bash
# Polygon API key
modal secret create polygon-api-key POLYGON_API_KEY=your_key

# Google OAuth (from Google Cloud Console)
modal secret create google-oauth \
  GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com \
  GOOGLE_CLIENT_SECRET=GOCSPX-your_secret

# JWT signing key (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
modal secret create mcp-jwt-key JWT_SIGNING_KEY=your_random_key

# Allowed emails (comma-separated)
modal secret create mcp-allowed-emails ALLOWED_EMAILS=you@example.com
```

### Deploy

```bash
modal deploy modal_app.py
```

### Architecture

- **OAuth**: Google OAuth via FastMCP's GoogleProvider
- **Storage**: Modal Dict for persistent client registrations
- **Security**: Email allowlist restricts access to authorized users only

## Tech Stack

- **Python 3.11+** with [uv](https://github.com/astral-sh/uv) for dependency management
- **[FastMCP](https://github.com/jlowin/fastmcp)** for MCP server implementation
- **[Polygon.io](https://polygon.io)** for market data with ORATS Greeks
- **[Modal](https://modal.com)** for serverless cloud deployment
- **Pandas** for CSV parsing and data manipulation

## Architecture

```
src/portfolio_mcp/
├── __init__.py     # Package exports
├── server.py       # MCP tool definitions (FastMCP)
└── tools.py        # Core business logic
    ├── Market time & session detection
    ├── CSV parsing (Schwab format)
    ├── Alert generation & prioritization
    ├── Polygon.io API integration
    └── Trade finding algorithms
```

## Contributing

Contributions welcome! Please read the existing code style and add tests for new features.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Anthropic](https://anthropic.com) for Claude and the MCP protocol
- [Polygon.io](https://polygon.io) for market data APIs
- [ORATS](https://orats.com) for options analytics (via Polygon)
