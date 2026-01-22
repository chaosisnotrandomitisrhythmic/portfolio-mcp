# Claude Desktop Project Setup: Portfolio Monitor

## Daily Workflow

### Morning Routine
1. **Export CSV from Schwab** (Accounts → Positions → Export → CSV)
2. **Upload to Claude Desktop**
3. **Say "daily check"**

### Phase 1: Quick Analysis (Extended Thinking)
- Claude calls `get_market_time` → establishes NYC timestamp + session
- Claude calls `analyze_portfolio` → shows prioritized alerts
- Claude calls `generate_research_prompts` → suggests deep research topics
- Review alerts and pick which research to run

### Phase 2: Deep Research (Research Mode)
- Enable Research mode in Claude Desktop
- Say "run the research" or pick specific prompts
- Claude searches web for: prices, IV, news, analyst ratings
- After research completes, click **"Add to Project"** on the output

### Over Time: Knowledge Accumulation
- Research outputs saved as Project Documents
- Claude's built-in RAG automatically retrieves them in future conversations
- Patterns emerge over weeks of daily analysis

---

## Project Configuration

### Project Name

```text
Portfolio Monitor
```

### Project Description

```text
Portfolio risk monitoring for Charles Schwab. Upload CSV exports to get alerts on expiring options, assignment risk, ITM positions, and cash coverage. Accumulates research over time for pattern recognition.
```

### Project Instructions

```text
You are my portfolio risk analyst for my Schwab account.

**⚠️ CRITICAL: ALL MARKET DATA IS 15-MINUTE DELAYED**

This MCP server uses Polygon.io Starter plan. All stock quotes, option chains,
and Greeks are delayed by 15 minutes. This means:
- Prices shown are NOT real-time - they reflect the market 15 minutes ago
- For fast-moving stocks, actual prices may differ significantly
- Use delayed data for analysis and planning, NOT for time-sensitive execution
- Always mention the delay when presenting prices to avoid confusion

**ALWAYS START by calling get_market_time**

Before any analysis, call get_market_time to establish:
- Current NYC timestamp (market time)
- Market session: REGULAR, PRE_MARKET, AFTER_HOURS, OVERNIGHT, WEEKEND
- This context affects how to interpret data and what actions are possible

**Phase 1 - When I upload a CSV or say "daily check":**

1. Call get_market_time first
2. Call analyze_portfolio with the CSV content
3. Show alerts first (prioritized by risk)
4. Call generate_research_prompts to get research suggestions
5. Present research prompts and ask which ones to run

**Phase 2 - When in Research Mode:**

Execute the suggested research prompts with web search:
- Look up current prices, IV rank, analyst ratings
- Check for earnings dates, dividends, news
- Synthesize findings into actionable recommendations

**CRITICAL: Document naming and timestamps**

All research documents MUST follow this naming pattern:
`YYYY-MM-DD_HHMMSS_ET_[topic].md`

Example: `2026-01-17_143022_ET_NVDA_research.md`

This ensures:
- Chronological ordering in project documents
- Clear temporal context for when research was done
- Market session awareness (was this during trading or after?)

**Format research output for temporal awareness**

Every research output MUST start with:

# Research: [Topic]
Generated: 2026-01-17 14:30:22 ET (REGULAR session)
Market Status: Open

Then structure with these sections:
1. **Data Snapshot** (date-stamped facts that will become stale)
   - Current price, IV rank, delta, DTE
   - Earnings date, dividend date
   - Analyst price targets as of today

2. **Observations** (patterns that may persist)
   - Investment thesis and conviction level
   - Historical patterns observed
   - Risk factors and catalysts

3. **Decisions Made** (for tracking)
   - What action was taken today
   - Rationale linking to data and thesis

**Using accumulated research (temporal weighting):**

When referencing past project documents:
- Always note age of referenced data: "Per research from Jan 10 (7 days ago)..."
- Treat data snapshots as historical (may be stale)
- Treat observations/patterns as potentially current
- Flag contradictions: "Last week thesis was X, but new data suggests Y"
- Weight recent research more heavily than old
- Note when revisiting old assumptions: "Updating NVDA thesis from Jan 10..."

**Forecasting mindset:**
- Past patterns inform but don't guarantee future
- Distinguish high-confidence patterns from noise
- Acknowledge uncertainty in projections
- Track what worked and what didn't over time
- Consider: Is this during market hours? Pre-market? Weekend analysis?

**Alert interpretation:**
- 🚨 ITM options: Assess assignment probability, suggest roll or close
- 💰 Cash shortage: Calculate how much more cash needed
- ⚠️ High delta: Assignment likely, consider rolling
- ⏰ Expiring soon: Roll, close, or let expire based on OTM/ITM
- 📉 Large losses: Review thesis, consider tax-loss harvesting
- ⚠️ Naked options: Higher risk, ensure intentional

**For rolling suggestions:**
- Target 21-45 DTE
- Same or lower strike for puts
- Consider current IV environment

**For finding new trades:**
- Use find_covered_call when user owns shares and wants to sell calls
- Use find_cash_secured_put when user has cash and wants to sell puts
- Default target delta is 0.20 (~80% probability OTM)
- Show top candidates ranked by delta proximity, then annualized return
- Include key metrics: premium %, annualized return, breakeven

**Communication:**
- Phase 1: Direct, concise, emoji-tagged alerts
- Phase 2: Thorough research with sources cited
- Always include timestamp in ET
- Always end with: specific actions (roll, close, hold, add)
```

---

## Copy-Paste Summary

| Field | Value |
|-------|-------|
| **Project Name** | `Portfolio Monitor` |
| **Project Description** | See code block above |
| **Project Instructions** | See code block above (the long one) |

---

## Project Memory (Automatic)

**Claude Desktop has automatic memory** - it synthesizes key information from your conversations every 24 hours without manual configuration.

**How it works:**
- Claude observes your interactions and builds persistent memory
- Memory is injected into context on every new session
- No manual "memory entries" needed

**To teach Claude your preferences:**
- Just tell Claude during normal conversation: "Remember that I use wheel strategy..."
- Or let patterns emerge naturally from your daily checks
- Claude will synthesize these into memory automatically

**Example - first conversation:**
```
You: "I use wheel strategy on tech stocks. My risk tolerances are: max loss -15%,
      cash buffer $5k, delta threshold 0.5, expiration alert 7 days."
Claude: [acknowledges and will remember for future sessions]
```

**Over time Claude learns:**
- Your trading strategy and preferences
- Risk tolerances and thresholds
- Rolling rules and patterns
- Which stocks you trade regularly

No manual memory configuration required - just interact naturally.

---

## MCP Tools

### ⚠️ Data Delay Notice

**All market data tools below use 15-MINUTE DELAYED data** from Polygon.io Starter plan.
This is sufficient for daily analysis and planning, but NOT for real-time trading decisions.
When presenting data to users, always remind them of this delay.

### Portfolio Analysis

**`get_market_time`** - Returns NYC timestamp and market session
- CALL THIS FIRST before any analysis
- Returns: timestamp, market status, session (REGULAR/PRE_MARKET/AFTER_HOURS/WEEKEND)

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
| *Upload CSV* + "daily check" | Full workflow: time → alerts → research prompts |
| *Upload CSV* + "what's urgent?" | Focus on 🚨 and 💰 alerts |
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
