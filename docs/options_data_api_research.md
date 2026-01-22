# US Options Data APIs with Greeks

A comprehensive comparison of options data providers for retail traders who need real Greeks (delta, gamma, theta, vega) without enterprise pricing.

---

**TL;DR:** Polygon.io + ORATS at $58/month is competitive, but two alternatives offer meaningful savings: Theta Data ($40/month) and Interactive Brokers (~$12/month with account). The decision hinges on whether you're willing to open a minimal brokerage account (IBKR) or prefer a pure data API (Theta Data). Most other providers either exceed budget, lack real Greeks, or require brokerage accounts with hidden fees.

---

## The verdict on your seven candidates

### Tradier: Brokerage required, hidden inactivity fees

Tradier does **not** offer data-only API plans. Real-time market data requires an active brokerage account. While Spain residents can open accounts, there's a **$20/month inactivity fee** for international users making fewer than 2 trades monthly—effectively adding to the cost. Greeks come from ORATS but update only **hourly**, not real-time. The API itself is free with an account, and documentation is excellent. However, EU residents cannot trade US ETFs due to PRIIPs regulations. **Verdict**: Not viable for pure data use without trading commitment.

### Alpha Vantage: Historical options on cheap tiers, real-time prohibitively expensive

Alpha Vantage provides options data with full Greeks (delta, gamma, theta, vega, rho) and is NASDAQ-licensed. However, **real-time options require their $199.99+/month tier** (600 requests/minute). Lower tiers only provide historical end-of-day options data or return placeholder data for real-time requests. For historical analysis, even the $49.99/month tier works, but this doesn't meet your 15-minute delayed requirement for live trading analysis. No geographic restrictions exist for Spain. **Verdict**: Too expensive for real-time; only useful for historical backtesting.

### Finnhub: Documented data quality problems

Finnhub's options chain endpoint includes implied volatility, but **Greeks availability is inconsistent** and appears to be a feature request rather than core functionality. More concerning, a GitHub issue from April 2025 documents severe price accuracy problems: an NVDA ATM call showing $0.85 ask versus $5.55 actual market (80%+ error). Users report "Greeks and contract metadata appear accurate, but bid/ask/last prices are not reliable." At ~$50/month per market, this isn't worth the risk. **Verdict**: Not recommended due to documented reliability issues.

### CBOE LiveVol: Enterprise pricing puts retail users out of reach

LiveVol (now Cboe DataShop) provides professional-grade Greeks calculated via the Cboe Hanweck analytics engine using binomial tree models with discrete dividends. However, **API access starts at $599/month** (Tier 1) plus potential SIP fees. The LiveVol Core platform is $105/month plus ~$5 non-professional OPRA fees, which approaches $110/month—nearly double your budget. No brokerage account required, and Spain access appears available. The data quality is institutional-grade, but pricing targets hedge funds, not retail traders. **Verdict**: Too expensive for retail budget.

### ORATS Direct: More features but higher cost than Polygon

Since Polygon licenses ORATS for Greeks anyway, going direct seems logical. ORATS's Delayed Data API costs **$99/month** (or $49/month with Reddit/EliteTrader discount) for 15-minute delayed data with 20,000 requests monthly. You get the same SMV (Smoothed Market Values) Greeks that Polygon provides, plus 500+ proprietary indicators, historical data back to 2007, and direct support. For **pure Greeks data**, Polygon at $58/month is cheaper—the Greeks quality is identical since both use ORATS SMV calculations. ORATS direct makes sense only if you need their advanced analytics, backtesting tools, or deeper historical data. No brokerage required, and international access appears fine though not explicitly confirmed. **Verdict**: Better features but $41/month more expensive for similar Greeks.

### Interactive Brokers: Cheapest option but requires brokerage account

IBKR offers the lowest-cost path: **~$11.50/month** for OPRA options data ($1.50) plus US Securities Snapshot Bundle ($10) as a non-professional subscriber. Spain residents can open accounts through Interactive Brokers Ireland. The catch: you must maintain **$500 minimum equity** beyond subscription costs, and must log into TWS every 60 days to keep subscriptions active. No trading required—your funds earn interest while sitting idle. The TWS API provides real-time calculated Greeks (delta, gamma, theta, vega, IV) via `tickOptionComputation`. If you're comfortable having an unfunded brokerage account as a data conduit, this saves **$46.50/month** versus Polygon. **Verdict**: Best value if you accept brokerage account requirement.

---

## Strong alternatives discovered in research

### Theta Data: Best pure-API alternative at $40/month

Theta Data emerged as the **strongest challenger to Polygon**. Their Value plan at **$40/month** includes:
- Real-time access with tick-level Greeks calculated using exact underlying prices
- Unlimited API requests
- 4 years historical data
- 1-minute interval granularity
- Active Discord community and Python client library

No brokerage required, no geographic restrictions, and Greeks are properly calculated rather than estimated. This saves **$18/month** versus Polygon while providing comparable data quality. Their Standard ($80/month) and Pro ($160/month) tiers add tick-level data, streaming, and longer history if needed.

### Market Data App: Solid alternative at $30-75/month

Market Data App's Trader plan costs **$30/month** (annual) or $75/month (monthly) and includes real-time delta, gamma, theta, vega, and IV with quotes. Features include 100K daily API credits, full OPRA coverage, Google Sheets integration, and historical data back to 2005. A **30-day free trial** (no credit card) lets you evaluate before committing. One limitation: historical options don't include Greeks—only real-time quotes do. Documentation quality is excellent.

### Unusual Whales: Flow-focused at $48/month

At $48/month (or $37/month annual), Unusual Whales provides full Greeks plus specialized options flow analysis, dark pool data, and unusual activity alerts. API access requires annual subscription. Better suited for sentiment analysis than raw data feeds, but includes real Greeks if that workflow appeals to you.

---

## Providers that don't work for your use case

| Provider | Why it fails |
|----------|-------------|
| **Yahoo Finance/yfinance** | No native Greeks—must self-calculate; unofficial API can break without notice |
| **Schwab API** | Requires $25,000 minimum for international accounts; complex for pure data |
| **Intrinio** | Enterprise pricing starts ~$250/month; far exceeds budget |
| **Barchart OnDemand** | Enterprise pricing with no retail tier |
| **Quandl/Nasdaq Data Link** | No US equity options data available |

---

## Cost comparison summary

| Provider | Monthly cost | Greeks quality | Brokerage required | Spain/EU access | Data delay |
|----------|-------------|----------------|-------------------|-----------------|------------|
| **Polygon.io (current)** | $58 | Real (ORATS SMV) | No | Yes | 15-min |
| **Interactive Brokers** | ~$12 + $500 deposit | Real (calculated) | Yes | Yes (IBKR Ireland) | Real-time |
| **Theta Data Value** | $40 | Real (tick-level) | No | Yes | Real-time |
| **Market Data App** | $30-75 | Real | No | Yes | 15-min to RT |
| **Unusual Whales** | $48 | Real | No | Yes | Real-time |
| **ORATS Direct** | $49-99 | Real (SMV) | No | Likely yes | 15-min |
| **Tradier** | Free + $20 inactivity | Real (ORATS, hourly) | Yes | Yes | Real-time |
| **Alpha Vantage** | $200+ for RT options | Real | No | Yes | RT on premium |
| **CBOE LiveVol** | $599+ API / $110 platform | Real (institutional) | No | Yes | RT/15-min |

---

## Decision framework for your 30-day evaluation

**Keep Polygon.io ($58/month) if:**
- You value simplicity and want to avoid any brokerage account complications
- Your current setup works well and $18/month savings isn't worth switching costs
- You prefer the Polygon ecosystem (stocks + options integrated)

**Switch to Theta Data ($40/month) if:**
- Saving $18/month ($216/year) matters and you're willing to migrate
- You want tick-level Greeks with exact underlying price matching
- Their 4-year history meets your backtesting needs

**Switch to Interactive Brokers (~$12/month) if:**
- Saving $46/month ($552/year) justifies opening a brokerage account
- You're comfortable maintaining $500+ idle in an IBKR account
- You don't mind logging into TWS periodically to keep subscriptions active

**Try Market Data App's free trial if:**
- You want to test an alternative risk-free for 30 days
- The Google Sheets integration appeals to your workflow

---

## Hidden costs and gotchas to watch

Several providers have costs that aren't immediately obvious:

- **OPRA exchange fees** affect real-time data pricing across most platforms; 15-minute delayed data often avoids these
- **Tradier's $20/month international inactivity fee** makes "free" API access effectively $20/month minimum
- **Professional vs non-professional classification** dramatically changes pricing at IBKR (from $1.50 to $32.75 for OPRA) and other providers
- **CBOE LiveVol SIP fees** add $600+/month for real-time API access beyond base subscription
- **AWS storage fees** for ORATS bulk historical data can add $1-2K for intraday files
- **Annual plans vs monthly** often save 15-20% but lock in commitment

---

## Conclusion

Your Polygon.io setup at $58/month represents solid value with proven ORATS Greeks quality. The two realistic alternatives are **Theta Data at $40/month** (pure API, no strings attached, saves $18/month) and **Interactive Brokers at ~$12/month** (requires brokerage account with $500 deposit, saves $46/month). Most other providers either exceed budget, lack real Greeks, have documented quality issues, or impose brokerage requirements with hidden fees.

For a risk-free evaluation: sign up for Market Data App's 30-day trial and Theta Data's free tier simultaneously. Test their Greeks against Polygon's ORATS data for the same options. If quality matches, Theta Data offers the cleanest path to meaningful savings without brokerage complications.
