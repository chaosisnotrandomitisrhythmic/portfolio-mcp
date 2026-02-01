"""FastMCP server for portfolio risk analysis.

Exposes portfolio monitoring tools for use with Claude Desktop and remote MCP clients.
Supports both stdio (local) and HTTP (cloud) transports.

Upload your Schwab CSV through the UI, then use the analyze tool.
"""

import json
import os

from fastmcp import FastMCP

from .tools import (
    analyze_portfolio,
    find_cash_secured_put,
    find_covered_call,
    generate_research_prompts,
    get_market_time,
    get_option_chain,
    get_portfolio_context,
    get_stock_quote,
    update_portfolio_context,
)

mcp = FastMCP(
    name="portfolio-mcp",
    instructions="""
    Portfolio risk analysis for Charles Schwab accounts.

    **⚠️ IMPORTANT: ALL MARKET DATA IS 15-MINUTE DELAYED**

    This server uses Polygon.io Starter plan. Stock quotes, option chains,
    and Greeks are delayed by 15 minutes. Always mention this when presenting
    prices to users. Use for analysis and planning, NOT real-time execution.

    **Daily Workflow:**

    1. **ALWAYS call get_market_time first** - establishes NYC timestamp and market session
    2. **Optionally call get_portfolio_context** - load strategy memory from Obsidian
    3. Upload your Schwab CSV through Claude Desktop's file upload
    4. Call analyze_portfolio for alerts and summary
    5. Call generate_research_prompts for deep-dive topics
    6. Enable Research mode for web search on suggested prompts
    7. **Call update_portfolio_context** to save learnings back to Obsidian

    **Portfolio Context Memory:**
    - get_portfolio_context: Load strategy, thesis, lessons from Obsidian
    - update_portfolio_context: Save new learnings and updates to Obsidian
    
    The context document persists across sessions, replacing the need for
    ever-growing Claude Desktop project documents.

    **Alert types (priority order):**
    - 🚨 ITM short options (highest risk)
    - 💰 Insufficient cash for short puts
    - ⚠️ High delta positions (assignment risk)
    - ⏰ Options expiring within 7 days
    - 📉 Positions down >10%
    - ⚠️ Naked short options

    **Market Sessions:**
    - REGULAR: 9:30 AM - 4:00 PM ET (market open)
    - PRE_MARKET: 4:00 AM - 9:30 AM ET
    - AFTER_HOURS: 4:00 PM - 8:00 PM ET
    - OVERNIGHT/WEEKEND: market closed

    **Document naming for research outputs:**
    Use format: YYYY-MM-DD_HHMMSS_ET_[topic].md
    Example: 2026-01-17_143022_ET_NVDA_research.md

    **Option Chain Tools (all 15-min delayed):**
    - get_stock_quote: Get price and key stats (15-min delayed)
    - get_option_chain: Fetch calls/puts with Greeks (15-min delayed)
    - find_covered_call: Find optimal CC candidates (15-min delayed)
    - find_cash_secured_put: Find optimal CSP candidates (15-min delayed)
    """
)


@mcp.tool(annotations={"title": "Get Market Time", "readOnlyHint": True})
def mcp_get_market_time() -> str:
    """Get current NYC market time and session status.

    CALL THIS FIRST before any analysis to establish temporal context.

    Returns:
        JSON with timestamp, market status (open/closed/pre-market/after-hours),
        session type, and weekday. All times in Eastern Time (ET).
    """
    result = get_market_time()
    return json.dumps(result, indent=2)


@mcp.tool(annotations={"title": "Analyze Portfolio", "readOnlyHint": True})
def mcp_analyze_portfolio(csv_content: str) -> str:
    """Analyze portfolio CSV and return alerts, summary, and holdings.

    Args:
        csv_content: The full content of a Schwab CSV export (paste or upload)

    Returns:
        JSON with alerts (prioritized risks), summary (cash, values), and holdings
    """
    result = analyze_portfolio(csv_content)
    return json.dumps(result, indent=2)


@mcp.tool(annotations={"title": "Generate Research Prompts", "readOnlyHint": True})
def mcp_generate_research_prompts(csv_content: str) -> str:
    """Generate research prompts based on portfolio alerts for Research mode.

    Call this after analyze_portfolio to get suggested deep-dive topics.
    User can then enable Research mode and run these prompts with web search.

    Args:
        csv_content: The full content of a Schwab CSV export

    Returns:
        JSON list of research prompts with priority, category, symbol, and context
    """
    analysis = analyze_portfolio(csv_content)
    prompts = generate_research_prompts(analysis)
    return json.dumps(prompts, indent=2)


# =============================================================================
# Market Data Tools
# =============================================================================


@mcp.tool(annotations={"title": "Get Stock Quote", "readOnlyHint": True})
def mcp_get_stock_quote(symbol: str) -> str:
    """Get stock quote and key statistics (15-MINUTE DELAYED).

    ⚠️ Data is 15 minutes behind real-time. Use for analysis, not execution.

    Args:
        symbol: Stock ticker symbol (e.g., 'NVDA', 'AAPL')

    Returns:
        JSON with price, change, volume, PE ratio, 52-week range, etc.
    """
    result = get_stock_quote(symbol)
    return json.dumps(result, indent=2)


@mcp.tool(annotations={"title": "Get Option Chain", "readOnlyHint": True})
def mcp_get_option_chain(
    symbol: str,
    expiration: str = None,
    option_type: str = None,
    min_delta: float = None,
    max_delta: float = None,
    min_volume: int = None,
    near_the_money: int = None,
) -> str:
    """Get option chain for a symbol with optional filtering (15-MINUTE DELAYED).

    ⚠️ Data is 15 minutes behind real-time. Greeks are from ORATS.
    Bid/ask quotes require Advanced plan ($199/mo) - not available on Starter.

    Args:
        symbol: Stock ticker symbol (e.g., 'NVDA')
        expiration: Expiration date (YYYY-MM-DD). If omitted, returns available dates.
        option_type: 'call', 'put', or omit for both
        min_delta: Minimum delta filter (e.g., 0.15)
        max_delta: Maximum delta filter (e.g., 0.35)
        min_volume: Minimum volume filter
        near_the_money: Only show N strikes near current price

    Returns:
        JSON with stock price, expiration, and filtered option chains
    """
    result = get_option_chain(
        symbol=symbol,
        expiration=expiration,
        option_type=option_type,
        min_delta=min_delta,
        max_delta=max_delta,
        min_volume=min_volume,
        near_the_money=near_the_money,
    )
    return json.dumps(result, indent=2)


@mcp.tool(annotations={"title": "Find Covered Call", "readOnlyHint": True})
def mcp_find_covered_call(
    symbol: str,
    shares: int = 100,
    target_delta: float = 0.20,
    min_dte: int = 20,
    max_dte: int = 45,
    min_premium_pct: float = 0.5,
) -> str:
    """Find optimal covered call candidates for a stock position (15-MINUTE DELAYED).

    ⚠️ Data is 15 minutes behind real-time. Verify prices before executing trades.

    Args:
        symbol: Stock ticker symbol
        shares: Number of shares owned (default 100)
        target_delta: Target delta for short call (default 0.20 = ~80% prob OTM)
        min_dte: Minimum days to expiration (default 20)
        max_dte: Maximum days to expiration (default 45)
        min_premium_pct: Minimum premium as % of stock price (default 0.5%)

    Returns:
        JSON with stock info and top 10 call candidates ranked by delta proximity
    """
    result = find_covered_call(
        symbol=symbol,
        shares=shares,
        target_delta=target_delta,
        min_dte=min_dte,
        max_dte=max_dte,
        min_premium_pct=min_premium_pct,
    )
    return json.dumps(result, indent=2)


@mcp.tool(annotations={"title": "Find Cash-Secured Put", "readOnlyHint": True})
def mcp_find_cash_secured_put(
    symbol: str,
    cash_available: float,
    target_delta: float = 0.20,
    min_dte: int = 20,
    max_dte: int = 45,
    min_premium_pct: float = 0.5,
) -> str:
    """Find optimal cash-secured put candidates (15-MINUTE DELAYED).

    ⚠️ Data is 15 minutes behind real-time. Verify prices before executing trades.

    Args:
        symbol: Stock ticker symbol
        cash_available: Cash available for securing puts
        target_delta: Target delta for short put (default 0.20 = ~80% prob OTM)
        min_dte: Minimum days to expiration (default 20)
        max_dte: Maximum days to expiration (default 45)
        min_premium_pct: Minimum premium as % of strike price (default 0.5%)

    Returns:
        JSON with stock info and top 10 put candidates ranked by delta proximity
    """
    result = find_cash_secured_put(
        symbol=symbol,
        cash_available=cash_available,
        target_delta=target_delta,
        min_dte=min_dte,
        max_dte=max_dte,
        min_premium_pct=min_premium_pct,
    )
    return json.dumps(result, indent=2)


# =============================================================================
# Portfolio Context Memory Tools
# =============================================================================


@mcp.tool(annotations={"title": "Get Portfolio Context", "readOnlyHint": True})
def mcp_get_portfolio_context(section: str = None) -> str:
    """Read investment strategy context from Obsidian memory document.

    Call this BEFORE portfolio analysis to load existing strategy, holdings
    thesis, decision frameworks, and accumulated learnings. The context
    helps maintain consistency across sessions.

    Args:
        section: Optional section to retrieve. If omitted, returns full document.
                 Valid sections:
                 - "Strategy Overview" - Core investment approach
                 - "Current Holdings & Thesis" - Position details and rationale
                 - "Decision Framework" - Trading rules and triggers
                 - "Risk Management" - Position limits and cash rules
                 - "Lessons Learned" - What's working and adjustments
                 - "Operational Procedures" - Workflows and guidelines
                 - "Open Questions" - Items to research

    Returns:
        JSON with document content, metadata, and available sections
    """
    result = get_portfolio_context(section=section)
    return json.dumps(result, indent=2)


@mcp.tool(annotations={"title": "Update Portfolio Context"})
def mcp_update_portfolio_context(
    section: str,
    content: str,
    mode: str = "replace",
) -> str:
    """Update a section of the portfolio context document in Obsidian.

    Use this to save new learnings, update holdings thesis, add decision
    outcomes, or record lessons learned. Updates persist across sessions.

    Args:
        section: Section name to update (e.g., "Lessons Learned", "Open Questions")
        content: New content for the section (markdown supported)
        mode: How to apply the update:
              - "replace" (default): Replace section content entirely
              - "append": Add content to end of section
              - "prepend": Add content to beginning of section

    Returns:
        JSON with updated section content, version, and timestamp
    """
    result = update_portfolio_context(
        section=section,
        content=content,
        mode=mode,
    )
    return json.dumps(result, indent=2)


def run_server() -> None:
    """Entry point for the MCP server.
    
    Supports multiple transports via MCP_TRANSPORT env var:
    - "stdio" (default): Local stdio transport for Claude Desktop
    - "http": HTTP transport for cloud deployment (use with Modal/ASGI)
    
    For HTTP transport, prefer using modal_app.py which provides
    proper ASGI setup with stateless_http=True for serverless.
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "stdio":
        mcp.run()
    elif transport == "http":
        # HTTP transport - run with default settings
        # For production, use modal_app.py with proper ASGI setup
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        raise ValueError(
            f"Unknown transport: {transport}. "
            "Use 'stdio' (default) or 'http'."
        )


if __name__ == "__main__":
    run_server()
