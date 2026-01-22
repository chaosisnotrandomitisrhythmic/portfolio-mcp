# Portfolio MCP Server

MCP server for portfolio risk analysis with research mode integration. Upload Charles Schwab CSV exports through Claude Desktop to get alerts, then run deep research that accumulates over time.

Uses **Polygon.io** for market data (stock quotes, option chains with real Greeks from ORATS).

## Quick Start

```bash
cd portfolio-mcp
uv sync

# Set up API key
cp .env.example .env
# Edit .env and add your Polygon.io API key

# Test with MCP inspector
npx @modelcontextprotocol/inspector uv --directory . run portfolio-mcp
```

## API Key Setup

This server requires a [Polygon.io](https://polygon.io) API key for market data.

**Recommended plans:** Stocks Starter ($29/mo) + Options Starter ($29/mo) = $58/mo

1. Sign up at [polygon.io](https://polygon.io/pricing)
2. Get your API key from the dashboard
3. Create `.env` file: `cp .env.example .env`
4. Add your key: `POLYGON_API_KEY=your_key_here`

**Note:** All market data is 15-minute delayed on Starter plans. This is sufficient for daily analysis but not for real-time execution.

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

### Option Chain & Trade Finding (Polygon.io - 15-min delayed)
| Tool | Description |
|------|-------------|
| `get_stock_quote` | Current price, change, volume, VWAP, market cap |
| `get_option_chain` | Fetch calls/puts with real Greeks (delta, gamma, theta, vega) and IV |
| `find_covered_call` | Find optimal CC candidates ranked by target delta (default 0.20) |
| `find_cash_secured_put` | Find optimal CSP candidates for your available cash |

#### Example: Finding a Covered Call
```
"Find covered call options for my 100 NVDA shares targeting 0.20 delta"

Returns top 10 candidates with:
- Strike, expiration, DTE
- Last price, IV, real delta (from ORATS)
- Premium $, premium %, annualized return
- Upside to strike, max return, breakeven
```

#### Example: Finding a Cash-Secured Put
```
"Find a cash-secured put for NVDA with my $20k cash"

Returns top 10 candidates with:
- Strike, expiration, DTE
- Last price, IV, real delta (from ORATS)
- Collateral required, premium, annualized return
- Discount to current price, cost basis if assigned
```

## Alert Types

| Alert | Meaning |
|-------|---------|
| 🚨 ITM Options | Short options in the money |
| 💰 Cash Shortage | Not enough cash for short put exposure |
| ⚠️ High Delta | Assignment risk (delta > 0.5) |
| ⏰ Expiring Soon | Options expiring within 7 days |
| 📉 Large Losses | Positions down >10% |
| ⚠️ Naked Options | Short options without underlying |

## Research Document Format

All research outputs follow this naming convention:
```
YYYY-MM-DD_HHMMSS_ET_[topic].md
```

Example: `2026-01-17_143022_ET_NVDA_research.md`

Each document includes:
- **Header**: Timestamp + market session
- **Data Snapshot**: Facts that will become stale (prices, IV, targets)
- **Observations**: Patterns that may persist (thesis, risks)
- **Decisions Made**: Actions taken for tracking

## Claude Desktop Setup

1. Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "portfolio-mcp": {
      "command": "/Users/chaosisnotrandomitisrythmic/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/chaosisnotrandomitisrythmic/Desktop/prescientai/overspent_detector/portfolio-mcp",
        "run",
        "portfolio-mcp"
      ],
      "env": {}
    }
  }
}
```

2. Restart Claude Desktop

3. Create a project with settings from [CLAUDE_PROJECT.md](CLAUDE_PROJECT.md)

## Data Format

Expects Schwab "Individual Positions" CSV with columns:
- Symbol, Qty, Price, Mkt Val
- Gain %, Security Type, Delta

Handles Schwab's Excel-escaped format (`="$186.23"`).

## Temporal Awareness

The system is designed for time-series knowledge accumulation:

- **get_market_time**: Always called first to establish context
- **Document timestamps**: Every research output is dated with ET timestamp
- **Session awareness**: Distinguishes market open, pre-market, after-hours, weekend
- **Recency weighting**: Recent research weighted more heavily than old
- **Stale vs persistent**: Data snapshots age out; observations may persist

## Memory (Automatic)

Claude Desktop has **automatic memory** that synthesizes from your conversations:

- No manual configuration required
- Tell Claude your preferences naturally: "I use wheel strategy on tech stocks..."
- Claude learns your trading style, risk tolerances, and patterns over time
- Memory persists across sessions and updates automatically

See [CLAUDE_PROJECT.md](CLAUDE_PROJECT.md) for full setup instructions.
