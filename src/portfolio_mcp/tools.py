"""Portfolio analysis tools for risk monitoring and options tracking.

Functions for parsing Charles Schwab portfolio exports and generating alerts
for expiring options, assignment risk, ITM positions, and cash coverage.

Also includes market data tools using Polygon.io (Massive) API for fetching
option chains and finding optimal covered call / cash-secured put candidates.
"""

import io
import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from polygon import RESTClient


def _load_env_file():
    """Load environment variables from .env file if it exists."""
    # Look for .env file in portfolio-mcp directory
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', '.env'),  # portfolio-mcp/.env
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'),  # parent .env
    ]

    for env_path in env_paths:
        env_path = os.path.normpath(env_path)
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ:  # Don't override existing env vars
                            os.environ[key] = value
            break


def _get_polygon_client() -> RESTClient:
    """Get Polygon.io REST client using environment variable.

    Looks for POLYGON_API_KEY in:
    1. Environment variables (set in Claude Desktop config)
    2. .env file in portfolio-mcp directory

    Get your API key from https://polygon.io/dashboard/api-keys
    """
    # Try loading from .env file first
    _load_env_file()

    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise ValueError(
            "POLYGON_API_KEY not found. Set it in one of these ways:\n"
            "1. Create portfolio-mcp/.env file with: POLYGON_API_KEY=your_key_here\n"
            "2. Add to Claude Desktop config env section\n"
            "Get your API key from https://polygon.io/dashboard/api-keys"
        )
    return RESTClient(api_key)


def get_market_time() -> dict:
    """Get current NYC market time and session status.

    Returns:
        Dict with timestamp, market status, and trading session info
    """
    from zoneinfo import ZoneInfo

    nyc = ZoneInfo("America/New_York")
    now = datetime.now(nyc)

    # Market hours (Eastern Time)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    pre_market_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
    after_hours_end = now.replace(hour=20, minute=0, second=0, microsecond=0)

    # Determine session
    weekday = now.weekday()
    is_weekend = weekday >= 5

    if is_weekend:
        session = "WEEKEND"
        market_status = "closed"
    elif now < pre_market_start:
        session = "OVERNIGHT"
        market_status = "closed"
    elif now < market_open:
        session = "PRE_MARKET"
        market_status = "pre-market trading"
    elif now < market_close:
        session = "REGULAR"
        market_status = "open"
    elif now < after_hours_end:
        session = "AFTER_HOURS"
        market_status = "after-hours trading"
    else:
        session = "OVERNIGHT"
        market_status = "closed"

    return {
        "timestamp": now.isoformat(),
        "timestamp_display": now.strftime("%Y-%m-%d %H:%M:%S ET"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "session": session,
        "market_status": market_status,
        "timezone": "America/New_York",
    }


def clean_currency(val) -> float:
    """Parse currency string to float, handling Schwab's Excel escaping."""
    if pd.isna(val):
        return 0.0
    s = str(val)
    # Handle Schwab's Excel-escaped format: =""$186.23"" or ="186.23"
    s = s.replace('=""', '').replace('""', '').replace('="', '').replace('"', '')
    s = s.replace('$', '').replace(',', '').replace('--', '0').replace('N/A', '0')
    s = s.strip()
    return float(s) if s else 0.0


def clean_pct(val) -> float:
    """Parse percentage string to float, handling Schwab's Excel escaping."""
    if pd.isna(val):
        return 0.0
    s = str(val)
    # Handle Schwab's Excel-escaped format
    s = s.replace('=""', '').replace('""', '')
    s = s.replace('%', '').replace('--', '0').replace('N/A', '0')
    return float(s) / 100 if s else 0.0


def clean_delta(val) -> float:
    """Parse delta value, handling N/A and Schwab formatting."""
    if pd.isna(val) or str(val).strip() in ('N/A', '--', ''):
        return 0.0
    return abs(float(val))


def parse_option_symbol(sym: str) -> dict:
    """Parse option symbol into components.

    Example: 'NVDA 01/23/2026 200.00 C' -> {underlying, exp, strike, opt_type}
    """
    parts = sym.split()
    return {
        'underlying': parts[0],
        'exp': parts[1],
        'strike': float(parts[2]),
        'opt_type': parts[3]
    }


def parse_portfolio_from_csv(csv_content: str) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Parse portfolio CSV content and return equities, options, and cash.

    Args:
        csv_content: Raw CSV content as string (from uploaded file)

    Returns:
        Tuple of (equities_df, options_df, cash_balance)
    """
    df = pd.read_csv(io.StringIO(csv_content), skiprows=1)

    # Extract cash before filtering
    cash_row = df[df['Symbol'] == 'Cash & Cash Investments']
    cash = clean_currency(cash_row.iloc[0]['Mkt Val (Market Value)']) if len(cash_row) > 0 else 0.0

    # Filter out summary rows
    df = df[~df['Symbol'].isin(['Cash & Cash Investments', 'Account Total'])].copy()

    equities = df[df['Security Type'].isin(['Equity', 'ETFs & Closed End Funds'])].copy()
    options = df[df['Security Type'] == 'Option'].copy()

    return equities, options, cash


def analyze_portfolio(csv_content: str) -> dict:
    """Main analysis function - takes CSV content, returns full analysis.

    Args:
        csv_content: Raw CSV content as string (uploaded through Claude Desktop)

    Returns:
        Dict with alerts, summary, and holdings
    """
    equities, options, cash = parse_portfolio_from_csv(csv_content)

    alerts = []

    # Check ITM options (highest priority)
    for _, opt in options.iterrows():
        if int(opt['Qty (Quantity)']) >= 0:
            continue
        o = parse_option_symbol(opt['Symbol'])
        eq = equities[equities['Symbol'] == o['underlying']]
        if len(eq) == 0:
            continue
        price = clean_currency(eq.iloc[0]['Price'])
        itm = (
            (o['opt_type'] == 'C' and price > o['strike']) or
            (o['opt_type'] == 'P' and price < o['strike'])
        )
        if itm:
            alerts.append(f"🚨 {o['underlying']}: Short {o['opt_type']} ${o['strike']} is ITM (price=${price:.2f})")

    # Check short puts cash coverage
    total_put_exposure = 0
    for _, opt in options.iterrows():
        if int(opt['Qty (Quantity)']) >= 0:
            continue
        o = parse_option_symbol(opt['Symbol'])
        if o['opt_type'] == 'P':
            qty = abs(int(opt['Qty (Quantity)']))
            total_put_exposure += qty * o['strike'] * 100

    if total_put_exposure > cash:
        shortage = total_put_exposure - cash
        alerts.append(f"💰 Short puts require ${total_put_exposure:,.0f} cash but only ${cash:,.0f} available (${shortage:,.0f} short)")

    # Check high delta
    for _, opt in options.iterrows():
        if int(opt['Qty (Quantity)']) >= 0:
            continue
        o = parse_option_symbol(opt['Symbol'])
        delta = clean_delta(opt['Delta'])
        if delta > 0.5:
            alerts.append(f"⚠️ {o['underlying']}: High Δ={delta:.2f} on short {o['opt_type']} ${o['strike']} - assignment risk")

    # Check expiring options (7 days)
    for _, opt in options.iterrows():
        o = parse_option_symbol(opt['Symbol'])
        exp_date = pd.to_datetime(o['exp']).normalize()
        today = pd.Timestamp.now().normalize()
        dte = (exp_date - today).days

        if dte > 7:
            continue

        eq = equities[equities['Symbol'] == o['underlying']]
        price = clean_currency(eq.iloc[0]['Price']) if len(eq) > 0 else None
        qty = int(opt['Qty (Quantity)'])

        if qty < 0 and price:
            if o['opt_type'] == 'C':
                otm = price < o['strike'] * 0.95
            else:
                otm = price > o['strike'] * 1.05

            if otm:
                gain = clean_pct(opt['Gain % (Gain/Loss %)'])
                alerts.append(f"⏰ {o['underlying']}: {o['opt_type']} ${o['strike']} expires in {dte}d - deep OTM, let expire (+{gain*100:.0f}% profit)")
            else:
                alerts.append(f"⏰ {o['underlying']}: {o['opt_type']} ${o['strike']} expires in {dte}d - consider rolling or closing")
        else:
            alerts.append(f"⏰ {o['underlying']}: {o['opt_type']} ${o['strike']} expires in {dte}d")

    # Check unrealized losses
    for _, eq in equities.iterrows():
        gain_pct = clean_pct(eq['Gain % (Gain/Loss %)'])
        if gain_pct < -0.10:
            alerts.append(f"📉 {eq['Symbol']}: Down {gain_pct*100:.1f}% - review position")

    # Check naked options
    for _, opt in options.iterrows():
        if int(opt['Qty (Quantity)']) >= 0:
            continue
        o = parse_option_symbol(opt['Symbol'])
        eq = equities[equities['Symbol'] == o['underlying']]
        if len(eq) == 0:
            alerts.append(f"⚠️ {o['underlying']}: Naked short {o['opt_type']} ${o['strike']} - no underlying held")

    if not alerts:
        alerts = ["✅ No immediate alerts"]

    # Build summary
    equity_value = equities['Mkt Val (Market Value)'].apply(clean_currency).sum()
    option_value = options['Mkt Val (Market Value)'].apply(clean_currency).sum()

    holdings = []
    for _, eq in equities.iterrows():
        holdings.append({
            'symbol': eq['Symbol'],
            'type': 'equity',
            'qty': int(float(eq['Qty (Quantity)'])),
            'price': clean_currency(eq['Price']),
            'value': clean_currency(eq['Mkt Val (Market Value)']),
            'gain_pct': clean_pct(eq['Gain % (Gain/Loss %)']),
        })

    for _, opt in options.iterrows():
        o = parse_option_symbol(opt['Symbol'])
        holdings.append({
            'symbol': opt['Symbol'],
            'type': 'option',
            'underlying': o['underlying'],
            'strike': o['strike'],
            'opt_type': o['opt_type'],
            'expiration': o['exp'],
            'qty': int(opt['Qty (Quantity)']),
            'price': clean_currency(opt['Price']),
            'value': clean_currency(opt['Mkt Val (Market Value)']),
            'delta': clean_delta(opt['Delta']) if str(opt['Delta']).strip() not in ('N/A', '--', '') else None,
            'gain_pct': clean_pct(opt['Gain % (Gain/Loss %)']),
        })

    return {
        'alerts': alerts,
        'summary': {
            'cash': cash,
            'equity_value': equity_value,
            'option_value': option_value,
            'total_value': cash + equity_value + option_value,
        },
        'holdings': holdings,
    }


def generate_research_prompts(analysis_result: dict) -> list[dict]:
    """Generate research prompts based on portfolio alerts.

    Maps each alert type to a contextual research prompt that Claude
    can execute in Research mode with web search.

    Args:
        analysis_result: Output from analyze_portfolio()

    Returns:
        List of research prompts sorted by priority
    """
    prompts = []

    for alert in analysis_result['alerts']:
        # Extract symbol from alert text (emoji followed by symbol:)
        # Handle various emoji formats including compound emojis
        symbol_match = re.search(r'^\W*(\w+):', alert)
        symbol = symbol_match.group(1) if symbol_match else None

        if '🚨' in alert and 'ITM' in alert:
            prompts.append({
                'priority': 1,
                'category': 'assignment_risk',
                'symbol': symbol,
                'prompt': f"""Research {symbol} assignment risk and near-term outlook:
- Current stock price vs option strike
- Upcoming earnings, dividends, or catalysts
- Technical support/resistance levels
- Should I roll, close, or accept assignment?""",
                'context': alert
            })

        elif '💰' in alert and 'cash' in alert.lower():
            prompts.append({
                'priority': 2,
                'category': 'cash_management',
                'symbol': None,
                'prompt': """Research short put assignment timing:
- When do brokers typically exercise ITM puts?
- Market conditions affecting early assignment
- Cash management strategies for wheel traders""",
                'context': alert
            })

        elif '⚠️' in alert and 'High' in alert and 'Δ' in alert:
            prompts.append({
                'priority': 3,
                'category': 'delta_risk',
                'symbol': symbol,
                'prompt': f"""Research {symbol} short-term price action:
- Current IV rank and IV percentile
- Analyst price targets and recent ratings changes
- Technical momentum indicators
- Roll candidates: same strike further out, or lower strike?""",
                'context': alert
            })

        elif '⏰' in alert:
            prompts.append({
                'priority': 4,
                'category': 'expiration',
                'symbol': symbol,
                'prompt': f"""Research {symbol} for expiration decision:
- Current implied volatility vs historical
- Any news or events before expiration
- Roll vs let expire analysis
- If rolling: optimal DTE and strike selection""",
                'context': alert
            })

        elif '📉' in alert:
            prompts.append({
                'priority': 5,
                'category': 'loss_review',
                'symbol': symbol,
                'prompt': f"""Research {symbol} thesis review:
- What caused the decline?
- Is the original investment thesis still valid?
- Analyst consensus and price targets
- Tax-loss harvesting considerations""",
                'context': alert
            })

    # Add general market context if we have positions
    if analysis_result.get('holdings'):
        symbols = list(set(
            h.get('symbol') if h.get('type') == 'equity' else h.get('underlying')
            for h in analysis_result['holdings']
            if h.get('symbol') or h.get('underlying')
        ))
        # Filter out None values
        symbols = [s for s in symbols if s]
        if symbols:
            prompts.append({
                'priority': 10,
                'category': 'market_context',
                'symbol': None,
                'prompt': f"""Research current market environment for my positions ({', '.join(symbols[:5])}):
- Overall market sentiment (VIX, put/call ratios)
- Sector rotation trends affecting tech
- Upcoming macro events (Fed, earnings season)
- IV environment: elevated or depressed?""",
                'context': 'General market context'
            })

    return sorted(prompts, key=lambda x: x['priority'])


# =============================================================================
# Market Data Tools (Polygon.io / Massive API)
# =============================================================================


def safe_float(val, default: float = 0.0) -> float:
    """Safely convert a value to float, handling NaN and None."""
    if val is None:
        return default
    try:
        result = float(val)
        if pd.isna(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def safe_int(val, default: int = 0) -> int:
    """Safely convert a value to int, handling NaN and None."""
    if val is None:
        return default
    try:
        result = float(val)  # Convert via float first to handle "1.0" strings
        if pd.isna(result):
            return default
        return int(result)
    except (ValueError, TypeError):
        return default


def get_stock_quote(symbol: str) -> dict:
    """Get current stock quote and key statistics using Polygon.io.

    Args:
        symbol: Stock ticker symbol (e.g., 'NVDA', 'AAPL')

    Returns:
        Dict with price, change, volume, and key stats
    """
    client = _get_polygon_client()
    symbol = symbol.upper()

    try:
        # Get snapshot for current price data
        snapshot = client.get_snapshot_ticker("stocks", symbol)

        if not snapshot:
            return {"error": f"No data found for {symbol}"}

        # Extract data from snapshot
        day = snapshot.day if hasattr(snapshot, 'day') else None
        prev_day = snapshot.prev_day if hasattr(snapshot, 'prev_day') else None

        current_price = safe_float(day.close if day else None) or safe_float(snapshot.min.close if hasattr(snapshot, 'min') and snapshot.min else None)
        prev_close = safe_float(prev_day.close if prev_day else None)

        if current_price == 0:
            # Try to get from last trade
            if hasattr(snapshot, 'last_trade') and snapshot.last_trade:
                current_price = safe_float(snapshot.last_trade.price)

        change = current_price - prev_close if prev_close else 0
        change_pct = (change / prev_close) * 100 if prev_close else 0

        result = {
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "prev_close": round(prev_close, 2) if prev_close else None,
            "volume": safe_int(day.volume if day else None),
            "vwap": round(safe_float(day.vwap if day else None), 2) or None,
        }

        # Try to get additional info from ticker details
        try:
            details = client.get_ticker_details(symbol)
            if details:
                result["market_cap"] = safe_int(details.market_cap) or None
                result["description"] = details.description[:200] + "..." if details.description and len(details.description) > 200 else details.description
        except Exception:
            pass  # Ticker details may not be available on all plans

        return result

    except Exception as e:
        return {"error": f"Failed to fetch quote for {symbol}: {str(e)}"}


def get_option_expirations(symbol: str) -> list[str]:
    """Get available option expiration dates for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        List of expiration dates in YYYY-MM-DD format
    """
    client = _get_polygon_client()
    symbol = symbol.upper()

    try:
        # Get options contracts to find available expirations
        expirations = set()
        for contract in client.list_options_contracts(
            underlying_ticker=symbol,
            expired=False,
            limit=1000,
        ):
            if hasattr(contract, 'expiration_date'):
                expirations.add(contract.expiration_date)

        return sorted(list(expirations))
    except Exception as e:
        return []


def _estimate_delta(current_price: float, strike: float, dte: int, opt_type: str) -> float:
    """Estimate delta from moneyness (rough approximation).

    Uses a simplified model based on moneyness and time to expiration.
    For more accurate Greeks, upgrade to Polygon Developer plan.
    """
    import math

    moneyness = (current_price - strike) / current_price

    # Adjust for time - options closer to expiry have more extreme deltas
    time_factor = max(0.1, min(1.0, dte / 30))  # Normalize around 30 DTE

    if opt_type == 'call':
        # Call delta: 0.5 at ATM, higher for ITM, lower for OTM
        raw_delta = 0.5 + moneyness * 2 * (1 / time_factor)
    else:
        # Put delta: -0.5 at ATM, use absolute value
        raw_delta = 0.5 - moneyness * 2 * (1 / time_factor)

    return min(0.99, max(0.01, raw_delta))


def _get_option_prev_day(client, option_ticker: str) -> Optional[dict]:
    """Get previous day aggregate data for an option contract."""
    try:
        aggs = client.get_previous_close_agg(option_ticker)
        if aggs and len(aggs) > 0:
            agg = aggs[0]
            return {
                "open": safe_float(agg.open),
                "high": safe_float(agg.high),
                "low": safe_float(agg.low),
                "close": safe_float(agg.close),
                "volume": safe_int(agg.volume),
                "vwap": safe_float(agg.vwap),
            }
    except Exception:
        pass
    return None


def get_option_chain(
    symbol: str,
    expiration: Optional[str] = None,
    option_type: Optional[str] = None,
    min_delta: Optional[float] = None,
    max_delta: Optional[float] = None,
    min_volume: Optional[int] = None,
    near_the_money: Optional[int] = None,
) -> dict:
    """Get option chain for a symbol with optional filtering using Polygon.io.

    Uses snapshot API with real Greeks (delta, gamma, theta, vega) and IV.
    Note: Bid/ask quotes require Advanced plan ($199/mo).

    Args:
        symbol: Stock ticker symbol
        expiration: Expiration date (YYYY-MM-DD). If None, returns available dates.
        option_type: 'call', 'put', or None for both
        min_delta: Minimum absolute delta filter
        max_delta: Maximum absolute delta filter
        min_volume: Minimum volume filter
        near_the_money: Only show N strikes above/below current price

    Returns:
        Dict with stock price, expirations, and option chains with Greeks
    """
    client = _get_polygon_client()
    symbol = symbol.upper()

    # Get current stock price first
    quote = get_stock_quote(symbol)
    if "error" in quote:
        return quote
    current_price = quote["price"]

    # Get available expirations
    expirations = get_option_expirations(symbol)

    if not expirations:
        return {"error": f"No options available for {symbol}"}

    # If no expiration specified, return available dates
    if expiration is None:
        return {
            "symbol": symbol,
            "price": current_price,
            "expirations": expirations[:20],  # Limit to next 20 expirations
            "message": "Specify an expiration date to get the option chain"
        }

    # Calculate DTE
    exp_date = datetime.strptime(expiration, "%Y-%m-%d")
    dte = (exp_date - datetime.now()).days

    # Build params for option chain snapshot
    params = {"expiration_date": expiration}
    if option_type:
        params["contract_type"] = option_type.lower()

    # Fetch option chain using snapshot API (requires Options Starter+)
    try:
        options_data = []

        for opt in client.list_snapshot_options_chain(symbol, params=params):
            details = opt.details if hasattr(opt, 'details') else None
            greeks = opt.greeks if hasattr(opt, 'greeks') else None
            last_quote = opt.last_quote if hasattr(opt, 'last_quote') else None
            day = opt.day if hasattr(opt, 'day') else None

            if not details:
                continue

            strike = safe_float(details.strike_price)
            opt_type = details.contract_type if hasattr(details, 'contract_type') else 'unknown'

            # Get delta from greeks (use absolute value)
            delta = abs(safe_float(greeks.delta if greeks else None))

            # Calculate if ITM
            itm = (opt_type == 'call' and current_price > strike) or \
                  (opt_type == 'put' and current_price < strike)

            # Get bid/ask if available (requires Advanced plan)
            bid = safe_float(last_quote.bid if last_quote else None) or None
            ask = safe_float(last_quote.ask if last_quote else None) or None

            # Get price - prefer last trade, fall back to day close
            last_price = safe_float(opt.last_trade.price if hasattr(opt, 'last_trade') and opt.last_trade else None)
            if not last_price and day:
                last_price = safe_float(day.close)

            # Get IV (convert from decimal to percentage)
            iv = safe_float(opt.implied_volatility) * 100 if opt.implied_volatility else None

            option = {
                "strike": strike,
                "type": opt_type,
                "last": round(last_price, 2) if last_price else None,
                "bid": round(bid, 2) if bid else None,
                "ask": round(ask, 2) if ask else None,
                "volume": safe_int(day.volume if day else None),
                "open_interest": safe_int(opt.open_interest) or None,
                "iv": round(iv, 1) if iv else None,
                "itm": itm,
                "delta": round(delta, 3) if delta else None,
                "gamma": round(safe_float(greeks.gamma if greeks else None), 4) or None,
                "theta": round(safe_float(greeks.theta if greeks else None), 4) or None,
                "vega": round(safe_float(greeks.vega if greeks else None), 4) or None,
            }

            # Apply filters
            if near_the_money is not None:
                if abs(strike - current_price) > near_the_money * (current_price * 0.025):
                    continue
            if min_delta is not None and delta and delta < min_delta:
                continue
            if max_delta is not None and delta and delta > max_delta:
                continue
            if min_volume is not None and option["volume"] < min_volume:
                continue

            options_data.append(option)

    except Exception as e:
        error_msg = str(e)
        if "NOT_AUTHORIZED" in error_msg:
            return {"error": "Options snapshot requires Options Starter plan ($29/mo). Upgrade at polygon.io/pricing"}
        return {"error": f"Failed to fetch option chain: {error_msg}"}

    result = {
        "symbol": symbol,
        "price": current_price,
        "expiration": expiration,
        "dte": dte,
    }

    # Split into calls and puts
    calls = sorted([o for o in options_data if o["type"] == "call"], key=lambda x: x["strike"])
    puts = sorted([o for o in options_data if o["type"] == "put"], key=lambda x: x["strike"])

    if option_type is None or option_type.lower() == 'call':
        result["calls"] = calls
    if option_type is None or option_type.lower() == 'put':
        result["puts"] = puts

    return result


def find_covered_call(
    symbol: str,
    shares: int = 100,
    target_delta: float = 0.20,
    min_dte: int = 20,
    max_dte: int = 45,
    min_premium_pct: float = 0.5,
) -> dict:
    """Find optimal covered call candidates for a stock position using Polygon.io.

    Uses snapshot API with real Greeks. Ranks by closeness to target delta.

    Args:
        symbol: Stock ticker symbol
        shares: Number of shares owned (default 100)
        target_delta: Target delta for short call (default 0.20 = ~80% OTM prob)
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration
        min_premium_pct: Minimum premium as % of stock price

    Returns:
        Dict with stock info and ranked call candidates
    """
    client = _get_polygon_client()
    symbol = symbol.upper()

    # Get current stock price
    quote = get_stock_quote(symbol)
    if "error" in quote:
        return quote
    current_price = quote["price"]
    position_value = current_price * shares

    # Get available expirations
    expirations = get_option_expirations(symbol)
    if not expirations:
        return {"error": f"No options available for {symbol}"}

    candidates = []
    today = datetime.now()

    for exp in expirations:
        exp_date = datetime.strptime(exp, "%Y-%m-%d")
        dte = (exp_date - today).days

        if dte < min_dte or dte > max_dte:
            continue

        # Get option chain snapshot for this expiration
        try:
            for opt in client.list_snapshot_options_chain(
                symbol,
                params={
                    "expiration_date": exp,
                    "contract_type": "call",
                },
            ):
                details = opt.details if hasattr(opt, 'details') else None
                greeks = opt.greeks if hasattr(opt, 'greeks') else None

                if not details:
                    continue

                strike = safe_float(details.strike_price)

                # Skip ITM calls for covered call strategy
                if strike <= current_price:
                    continue

                # Get delta from greeks
                delta = abs(safe_float(greeks.delta if greeks else None))
                if delta == 0:
                    continue

                # Get price - prefer last trade, fall back to day close
                day = opt.day if hasattr(opt, 'day') else None
                last_price = safe_float(opt.last_trade.price if hasattr(opt, 'last_trade') and opt.last_trade else None)
                if not last_price and day:
                    last_price = safe_float(day.close)
                if last_price <= 0:
                    continue

                # Get IV
                iv = safe_float(opt.implied_volatility) * 100 if opt.implied_volatility else None

                # Calculate metrics
                num_contracts = shares // 100
                premium = last_price * 100 * num_contracts
                premium_pct = (last_price / current_price) * 100
                annualized_return = (premium_pct / dte) * 365 if dte > 0 else 0
                upside_to_strike = ((strike - current_price) / current_price) * 100
                max_return_pct = premium_pct + upside_to_strike
                breakeven = current_price - last_price

                if premium_pct < min_premium_pct:
                    continue

                # Score based on closeness to target delta
                delta_diff = abs(delta - target_delta)

                candidates.append({
                    "expiration": exp,
                    "dte": dte,
                    "strike": strike,
                    "last": round(last_price, 2),
                    "volume": safe_int(opt.day.volume if hasattr(opt, 'day') and opt.day else None),
                    "open_interest": safe_int(opt.open_interest) or None,
                    "iv": round(iv, 1) if iv else None,
                    "delta": round(delta, 3),
                    "contracts": num_contracts,
                    "premium": round(premium, 2),
                    "premium_pct": round(premium_pct, 2),
                    "annualized_return": round(annualized_return, 1),
                    "upside_to_strike": round(upside_to_strike, 1),
                    "max_return_pct": round(max_return_pct, 1),
                    "breakeven": round(breakeven, 2),
                    "delta_diff": delta_diff,
                })

        except Exception:
            continue

    # Sort by closeness to target delta, then by annualized return
    candidates.sort(key=lambda x: (x['delta_diff'], -x['annualized_return']))

    return {
        "symbol": symbol,
        "price": round(current_price, 2),
        "shares": shares,
        "position_value": round(position_value, 2),
        "target_delta": target_delta,
        "candidates": candidates[:10],
    }


def find_cash_secured_put(
    symbol: str,
    cash_available: float,
    target_delta: float = 0.20,
    min_dte: int = 20,
    max_dte: int = 45,
    min_premium_pct: float = 0.5,
) -> dict:
    """Find optimal cash-secured put candidates using Polygon.io.

    Uses snapshot API with real Greeks. Ranks by closeness to target delta.

    Args:
        symbol: Stock ticker symbol
        cash_available: Cash available for securing puts
        target_delta: Target delta for short put (default 0.20 = ~80% OTM prob)
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration
        min_premium_pct: Minimum premium as % of strike price

    Returns:
        Dict with stock info and ranked put candidates
    """
    client = _get_polygon_client()
    symbol = symbol.upper()

    # Get current stock price
    quote = get_stock_quote(symbol)
    if "error" in quote:
        return quote
    current_price = quote["price"]

    # Get available expirations
    expirations = get_option_expirations(symbol)
    if not expirations:
        return {"error": f"No options available for {symbol}"}

    candidates = []
    today = datetime.now()

    for exp in expirations:
        exp_date = datetime.strptime(exp, "%Y-%m-%d")
        dte = (exp_date - today).days

        if dte < min_dte or dte > max_dte:
            continue

        # Get option chain snapshot for this expiration
        try:
            for opt in client.list_snapshot_options_chain(
                symbol,
                params={
                    "expiration_date": exp,
                    "contract_type": "put",
                },
            ):
                details = opt.details if hasattr(opt, 'details') else None
                greeks = opt.greeks if hasattr(opt, 'greeks') else None

                if not details:
                    continue

                strike = safe_float(details.strike_price)

                # Skip ITM puts for CSP strategy
                if strike >= current_price:
                    continue

                # Check if we can afford this put
                collateral = strike * 100
                if collateral > cash_available:
                    continue

                # Get delta from greeks (use absolute value for puts)
                delta = abs(safe_float(greeks.delta if greeks else None))
                if delta == 0:
                    continue

                # Get price - prefer last trade, fall back to day close
                day = opt.day if hasattr(opt, 'day') else None
                last_price = safe_float(opt.last_trade.price if hasattr(opt, 'last_trade') and opt.last_trade else None)
                if not last_price and day:
                    last_price = safe_float(day.close)
                if last_price <= 0:
                    continue

                # Get IV
                iv = safe_float(opt.implied_volatility) * 100 if opt.implied_volatility else None

                # Calculate metrics
                num_contracts = int(cash_available // collateral)
                if num_contracts < 1:
                    continue

                premium = last_price * 100 * num_contracts
                premium_pct = (last_price / strike) * 100
                annualized_return = (premium_pct / dte) * 365 if dte > 0 else 0
                discount_to_current = ((current_price - strike) / current_price) * 100
                breakeven = strike - last_price
                cost_basis_if_assigned = breakeven

                if premium_pct < min_premium_pct:
                    continue

                # Score based on closeness to target delta
                delta_diff = abs(delta - target_delta)

                candidates.append({
                    "expiration": exp,
                    "dte": dte,
                    "strike": strike,
                    "last": round(last_price, 2),
                    "volume": safe_int(opt.day.volume if hasattr(opt, 'day') and opt.day else None),
                    "open_interest": safe_int(opt.open_interest) or None,
                    "iv": round(iv, 1) if iv else None,
                    "delta": round(delta, 3),
                    "contracts": num_contracts,
                    "collateral": round(collateral * num_contracts, 2),
                    "premium": round(premium, 2),
                    "premium_pct": round(premium_pct, 2),
                    "annualized_return": round(annualized_return, 1),
                    "discount_to_current": round(discount_to_current, 1),
                    "breakeven": round(breakeven, 2),
                    "cost_basis_if_assigned": round(cost_basis_if_assigned, 2),
                    "delta_diff": delta_diff,
                })

        except Exception:
            continue

    # Sort by closeness to target delta, then by annualized return
    candidates.sort(key=lambda x: (x['delta_diff'], -x['annualized_return']))

    return {
        "symbol": symbol,
        "price": round(current_price, 2),
        "cash_available": round(cash_available, 2),
        "target_delta": target_delta,
        "candidates": candidates[:10],
    }
