# Polygon.io Evaluation TODOs

**Subscription started:** 2026-01-21 17:57 CET
**Evaluation deadline:** 2026-02-15
**Cancel deadline:** 2026-02-19 (before renewal ~Feb 21)

---

## Week 1-2: Use Polygon (Jan 21 - Feb 3)

- [ ] Use portfolio-mcp daily for portfolio analysis
- [ ] Note any issues with Greeks quality
- [ ] Note any API errors or rate limits
- [ ] Track actual usage (how many calls/day?)
- [ ] Test covered call finder on real positions
- [ ] Test cash-secured put finder

## Week 3: Test Alternatives (Feb 3 - Feb 10)

- [ ] Sign up for Theta Data free tier
- [ ] Get Theta Data API key
- [ ] Test Theta Data Greeks vs Polygon for same options:
  - [ ] NVDA calls/puts
  - [ ] AAPL calls/puts
  - [ ] Compare delta, gamma, theta, vega values
- [ ] Check Theta Data latency
- [ ] Test Market Data App 30-day free trial (optional)

## Feb 10: Theta Data Test Day

- [ ] Run side-by-side comparison
- [ ] Document differences in a note
- [ ] Form preliminary opinion

## Feb 15: Decision Day

- [ ] Review month of Polygon usage
- [ ] Review Theta Data test results
- [ ] Make decision:
  - [ ] **Keep Polygon** ($58/mo) - if it works well and switching cost not worth $18/mo savings
  - [ ] **Switch to Theta Data** ($40/mo) - if quality matches and worth migration effort
  - [ ] **Switch to IBKR** (~$12/mo) - if willing to open brokerage account

## Feb 19: Action Day (if switching)

- [ ] Cancel Polygon subscription at polygon.io/dashboard/billing
- [ ] Set up chosen alternative
- [ ] Update portfolio-mcp code to use new provider
- [ ] Update .env with new API key
- [ ] Test everything works

---

## Cost Summary

| Provider | Monthly | Annual | Savings vs Polygon |
|----------|---------|--------|-------------------|
| Polygon (current) | $58 | $696 | - |
| Theta Data | $40 | $480 | $216/yr |
| IBKR | ~$12 | ~$144 | $552/yr |

---

## Calendar Reminders

✅ Imported to calendar:
- **Feb 10** - Test Theta Data API
- **Feb 15** - Decision day
- **Feb 19** - Last day to cancel Polygon
