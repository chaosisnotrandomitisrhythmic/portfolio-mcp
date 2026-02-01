# Claude Desktop Project Setup: Portfolio Monitor

## Daily Workflow

### Morning Routine
1. **Export CSV from Schwab** (Accounts → Positions → Export → CSV)
2. **Upload to Claude Desktop**
3. **Say "daily check"**

### Phase 1: Quick Analysis (Extended Thinking)
- Claude calls `get_market_time` → establishes NYC timestamp + session
- Claude calls `get_portfolio_context` → loads strategy memory from Obsidian (optional)
- Claude calls `analyze_portfolio` → shows prioritized alerts
- Claude calls `generate_research_prompts` → suggests deep research topics
- Review alerts and pick which research to run

### Phase 2: Deep Research (Research Mode)
- Enable Research mode in Claude Desktop
- Say "run the research" or pick specific prompts
- Claude searches web for: prices, IV, news, analyst ratings
- After research completes, click **"Add to Project"** on the output

### Phase 3: Save Learnings
- Claude calls `update_portfolio_context` → saves key insights to Obsidian
- Strategy memory persists across sessions without manual document management

### Over Time: Knowledge Accumulation
- Strategy memory stored in Obsidian at `~/Documents/obsedian/chaos_isrhythmic/portfolio-manager/`
- Research outputs saved as Project Documents
- Patterns emerge over weeks of daily analysis

---

## Project Configuration

### Project Name

```text
Portfolio Monitor
```

### Project Description

```text
Portfolio risk analysis for Charles Schwab options trading. MCP tools for CSV analysis, market data, and persistent strategy memory via Obsidian.
```

### Project Instructions

```text
<role>
You are my portfolio risk analyst for options trading on my Schwab account.

Your expertise includes:
- Options strategies: covered calls, cash-secured puts, the wheel
- Risk assessment: assignment probability, ITM/OTM analysis, delta risk
- Portfolio monitoring: expiration management, cash coverage, position sizing
- Market context: interpreting data across market sessions (pre-market, regular, after-hours)

You help me make informed decisions by analyzing positions, identifying risks, and finding optimal trades. You maintain persistent memory of strategies and learnings via Obsidian.

⚠️ ALL MARKET DATA IS 15-MINUTE DELAYED (Polygon.io Starter plan)
</role>

<available_tools>
You have access to these MCP tools:

**Context & Time**
- `get_market_time`: Get NYC timestamp and market session. ALWAYS CALL FIRST.
- `get_portfolio_context`: Load strategy memory from Obsidian (thesis, lessons, frameworks)
- `update_portfolio_context`: Save learnings back to Obsidian

**Portfolio Analysis**
- `analyze_portfolio`: Parse Schwab CSV, generate prioritized risk alerts
- `generate_research_prompts`: Create research suggestions based on alerts

**Market Data (15-min delayed)**
- `get_stock_quote`: Current price, change, volume, VWAP
- `get_option_chain`: Option chains with real Greeks (delta, gamma, theta, vega, IV)
- `find_covered_call`: Find optimal CC candidates for shares owned
- `find_cash_secured_put`: Find optimal CSP candidates for available cash

Tool selection guidance:
- Starting a session → `get_market_time` first, then optionally `get_portfolio_context`
- CSV uploaded or "daily check" → `analyze_portfolio`, then `generate_research_prompts`
- Finding trades → `find_covered_call` (if I own shares) or `find_cash_secured_put` (if I have cash)
- Researching a position → `get_stock_quote` and `get_option_chain`
- After insights gained → `update_portfolio_context` to save learnings
</available_tools>

<workflow>
**Phase 1: Analysis (when I upload CSV or say "daily check")**
1. Call `get_market_time` to establish session context
2. Optionally call `get_portfolio_context` to load strategy memory
3. Call `analyze_portfolio` with the CSV content
4. Present alerts first (prioritized by risk)
5. Call `generate_research_prompts` for research suggestions
6. Ask which prompts to run

**Phase 2: Research (when in Research Mode)**
Execute suggested prompts with web search:
- Look up current prices, IV rank, analyst ratings
- Check for earnings dates, dividends, news
- Synthesize into actionable recommendations
- Call `update_portfolio_context` to save key learnings

**Phase 3: Trade Finding (when asked)**
- Use `find_covered_call` when I own shares and want to sell calls
- Use `find_cash_secured_put` when I have cash and want to sell puts
- Default target delta: 0.20 (~80% probability OTM)
- Show candidates ranked by delta proximity, then annualized return
</workflow>

<alerts>
Alert interpretation:
- 🚨 ITM options: Assess assignment probability, suggest roll or close
- 💰 Cash shortage: Calculate how much more cash needed
- ⚠️ High delta: Assignment likely, consider rolling
- ⏰ Expiring soon: Roll, close, or let expire based on OTM/ITM
- 📉 Large losses: Review thesis, consider tax-loss harvesting
- ⚠️ Naked options: Higher risk, ensure intentional

Rolling guidelines:
- Target 21-45 DTE
- Same or lower strike for puts
- Consider current IV environment
</alerts>

<temporal_awareness>
All research output MUST include temporal context:

**Document naming**: `YYYY-MM-DD_HHMMSS_ET_[topic].md`
Example: `2026-01-17_143022_ET_NVDA_research.md`

**Research header format**:
# Research: [Topic]
Generated: 2026-01-17 14:30:22 ET (REGULAR session)
Market Status: Open

**Sections**:
1. **Data Snapshot** - date-stamped facts that will become stale (prices, IV, DTE)
2. **Observations** - patterns that may persist (thesis, historical patterns)
3. **Decisions Made** - what action was taken and rationale

**Using accumulated research**:
- Note age of referenced data: "Per research from Jan 10 (7 days ago)..."
- Weight recent research more heavily than old
- Flag contradictions: "Last week thesis was X, but new data suggests Y"
</temporal_awareness>

<output_preferences>
**Phase 1 (Analysis)**: Direct, concise, emoji-tagged alerts
**Phase 2 (Research)**: Thorough with sources cited
**Always**: Include timestamp in ET, end with specific actions (roll, close, hold, add)

When presenting trade candidates:
- Show key metrics: premium %, annualized return, breakeven, delta
- Compare to target parameters
- Note any concerns (earnings, low liquidity)
</output_preferences>
```

---

## Quick Copy-Paste Setup

> **Tip:** Click the copy icon (📋) in the top-right corner of each code block to copy to clipboard.

### 1. Project Name
```text
Portfolio Monitor
```

### 2. Project Description
```text
Portfolio risk analysis for Charles Schwab options trading. MCP tools for CSV analysis, market data, and persistent strategy memory via Obsidian.
```

### 3. Project Instructions

👆 Scroll up to the [Project Instructions](#project-instructions) section and copy the full code block.

---

## Project Memory

### Obsidian-Based Context Memory (New!)

The MCP server now includes **persistent context memory** via Obsidian:

**Document location:**
```
~/Documents/obsedian/chaos_isrhythmic/portfolio-manager/Portfolio_Context.md
```

**Sections available:**
- Strategy Overview
- Current Holdings & Thesis
- Decision Framework
- Risk Management
- Lessons Learned
- Operational Procedures
- Open Questions

**How to use:**
- Call `get_portfolio_context` to load strategy memory at session start
- Call `update_portfolio_context` to save learnings after research
- Document is editable in Obsidian for manual updates

**Benefits over Claude Desktop project documents:**
- Programmatic read/write access
- Structured sections for targeted retrieval
- Version tracking
- Lives in your Obsidian vault (searchable, linkable)

### Claude Desktop Automatic Memory

Claude Desktop also has **automatic memory** that synthesizes key information from conversations every 24 hours.

**How it works:**
- Claude observes your interactions and builds persistent memory
- Memory is injected into context on every new session
- No manual configuration needed

**Both systems complement each other:**
- Obsidian context = structured strategy documentation you control
- Claude memory = automatic pattern recognition from conversations

---

## MCP Tools

### ⚠️ Data Delay Notice

**All market data tools below use 15-MINUTE DELAYED data** from Polygon.io Starter plan.
This is sufficient for daily analysis and planning, but NOT for real-time trading decisions.
When presenting data to users, always remind them of this delay.

### Context & Time

**`get_market_time`** - Returns NYC timestamp and market session
- CALL THIS FIRST before any analysis
- Returns: timestamp, market status, session (REGULAR/PRE_MARKET/AFTER_HOURS/WEEKEND)

**`get_portfolio_context`** - Load strategy memory from Obsidian
- Args: section (optional) - specific section to retrieve
- Returns: full document or specific section content
- Sections: Strategy Overview, Current Holdings & Thesis, Decision Framework, Risk Management, Lessons Learned, Operational Procedures, Open Questions
- Auto-creates template if document doesn't exist

**`update_portfolio_context`** - Save learnings to Obsidian
- Args: section (required), content (required), mode (replace/append/prepend)
- Returns: updated section content with version info
- Auto-updates last_updated timestamp

### Portfolio Analysis

**`analyze_portfolio`** - Analyzes uploaded CSV content
- Returns: alerts (prioritized), summary (cash/values), and holdings

**`generate_research_prompts`** - Generates research prompts based on alerts
- Returns: list of prompts for Research mode with priority and context

### Option Chain & Trade Finding (Polygon.io)

**`get_stock_quote`** - Get current stock price and key stats
- Returns: price, change, volume, vwap, market cap
- ⏱️ **Data: 15-minute delayed**

**`get_option_chain`** - Fetch option chain with filtering
- Args: symbol, expiration (optional), option_type, delta filters, volume filter
- Returns: calls and/or puts with strike, last price, IV, volume, Greeks
- ⏱️ **Data: 15-minute delayed** (Greeks from ORATS)
- Note: Bid/ask requires Advanced plan ($199/mo)

**`find_covered_call`** - Find optimal covered call candidates
- Args: symbol, shares, target_delta (default 0.20), DTE range, min premium
- Returns: top 10 candidates ranked by closeness to target delta
- Includes: premium %, annualized return, upside to strike, breakeven
- ⏱️ **Data: 15-minute delayed**

**`find_cash_secured_put`** - Find optimal cash-secured put candidates
- Args: symbol, cash_available, target_delta (default 0.20), DTE range
- Returns: top 10 candidates ranked by closeness to target delta
- Includes: collateral, premium, annualized return, cost basis if assigned
- ⏱️ **Data: 15-minute delayed**

---

## Example Prompts

| You Say | What Happens |
|---------|--------------|
| *Upload CSV* + "daily check" | Full workflow: time → context → alerts → research prompts |
| *Upload CSV* + "what's urgent?" | Focus on 🚨 and 💰 alerts |
| "load my strategy context" | Reads strategy memory from Obsidian |
| "what's my thesis on NVDA?" | Retrieves Current Holdings & Thesis section |
| "save this lesson" + insight | Updates Lessons Learned in Obsidian |
| "run the research" | Execute suggested prompts in Research mode |
| "what should I roll?" | Suggestions for high delta / near expiry |
| "find covered call for NVDA" | Shows top CC candidates at target 0.20 delta |
| "find CSP for NVDA with $20k" | Shows top put candidates within your cash |
| "show NVDA option chain for Feb 20" | Full chain with IV, delta, volume |
| "get NVDA quote" | Current price, change, PE, 52-week range |

---

## How to Set Up in Claude Desktop

### Step 1: Get Polygon.io API Key

This MCP server uses **Polygon.io** (now Massive) for real-time market data and option chains.

#### Required Plans

You need **both** a Stocks plan and an Options plan:

**Stocks Plans:**
| Tier | Price | Data Delay | Notes |
|------|-------|------------|-------|
| **Starter** | $29/mo | 15-min delayed | Stock quotes, market cap |

**Options Plans:**
| Tier | Price | Data Delay | Features |
|------|-------|------------|----------|
| **Basic** | $0/mo | EOD only | Reference data only, NO Greeks |
| **Starter** | $29/mo | 15-min delayed | Greeks, IV, snapshots, volume |
| **Developer** | $79/mo | 15-min delayed | + Trades data |
| **Advanced** | $199/mo | Real-time | + Bid/Ask quotes |

**Recommended setup: Stocks Starter ($29) + Options Starter ($29) = $58/mo**

This gives you:
- Real Greeks (delta, gamma, theta, vega) from ORATS
- Implied Volatility
- Open Interest
- Volume
- 15-min delayed data (sufficient for daily analysis)

#### Get Your API Key
1. Sign up at [polygon.io](https://polygon.io/pricing) (or [massive.com](https://massive.com/pricing))
2. Choose your tier (Starter recommended to start)
3. Go to Dashboard → API Keys
4. Copy your API key

### Step 2: Add MCP Server
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
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

**Note:** The API key is loaded from `.env` file in the portfolio-mcp directory. No need to add it to the config.

### Step 3: Restart Claude Desktop
Quit and reopen Claude Desktop to load the MCP server.

### Step 4: Create New Project
1. Click **"Projects"** in the sidebar
2. Click **"New Project"**
3. Enter **Project Name**: `Portfolio Monitor`
4. Enter **Project Description** (copy from above)
5. Paste the **Project Instructions** (copy from above)

### Step 5: Enable Extended Thinking (Optional)
For Phase 1 analysis with deeper reasoning:
- Go to Project Settings
- Enable "Extended thinking" if available

### Step 6: First Conversation - Teach Your Preferences
In your first conversation, tell Claude about your trading style:

```
"I use wheel strategy on tech stocks. My risk tolerances are:
- Max unrealized loss before review: -15%
- Cash buffer: $5k above short put exposure
- Delta concern threshold: 0.5
- Expiration alert: 7 days

For rolling: roll when delta > 0.6 OR DTE < 5 with profit < 50%.
Target 21-45 DTE, same or lower strike for puts."
```

Claude will remember this automatically for future sessions.

Now you're ready to use the daily workflow!

---

## Exporting from Schwab

1. Log into schwab.com
2. Go to Accounts → Positions
3. Click "Export" (top right)
4. Choose "CSV"
5. Upload directly to Claude Desktop
