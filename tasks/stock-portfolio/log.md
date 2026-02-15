# Development Log

## 2026-02-06

### Done
- **All research tasks completed** - spec fully documented with code examples

### Research Summary

#### 1. schwab-py Library (✅ Recommended)
- **GitHub**: https://github.com/alexgolec/schwab-py (389 stars, MIT)
- **Key finding**: Handles OAuth automatically, 30-min access tokens auto-refresh
- **Gotcha**: Refresh tokens expire after 7 days - need browser re-auth
- **Rate limit**: 120 requests/minute
- **Code examples**: Authentication, get positions with cost basis, batch quotes

#### 2. yfinance Library (✅ For fallback)
- **GitHub**: https://github.com/ranaroussi/yfinance (21.4k stars)
- **Supports**: Stocks, ETFs, mutual funds (LRSCX, MALOX), YieldMax ETFs
- **Does NOT support**: Fidelity pooled funds (CUSIPs like 31565G759)
- **Best practice**: Use batch `yf.download()` with threading, implement exponential backoff
- **Rate limiting**: More aggressive now - cache results 15+ minutes

#### 3. News API (✅ Finnhub selected)
- **Winner**: Finnhub - 60 calls/min free tier, built-in sentiment
- **Rejected**: Alpha Vantage (25/day), EODHD (20/day), NewsAPI (no ticker filtering)
- **Python client**: finnhub-python (v2.4.25)
- **Code example**: Batch news fetch with deduplication

#### 4. APScheduler/JobQueue (✅ Built into telegram bot)
- Install: `pip install "python-telegram-bot[job-queue]"`
- 9:30 PM ET weekdays: `run_daily(days=(0,1,2,3,4), time=time(21,30,tzinfo=ET))`
- Monthly 1st: `run_monthly(day=1, when=time(9,0,tzinfo=ET))`
- Persistence: Re-register on startup with `replace_existing=True`

#### 5. GitHub Projects Evaluated
- **Essential**: schwab-py, yfinance, finnhub-python
- **Reference**: Ghostfolio (7.6k stars, TypeScript), notion-portfolio-tracker
- **Nice-to-have**: PyPortfolioOpt (optimization), Schwabdev (alternative)
- **Avoid**: bankroll (archived), Alpha Vantage news

### Blocking Dependencies
- Schwab Developer Portal approval (Heath registered, waiting)
- Finnhub API key (free registration at finnhub.io)

### Notes
- Fidelity pooled funds (31565G759, 31617E778, LSSNX) need manual NAV entry - yfinance doesn't support CUSIPs
- YieldMax ETFs (AMZY, NVDY, TSLY, ULTY, FIAT) fully supported by yfinance including dividends
- schwab-py requires Python 3.10+
- Callback URL must be exactly `https://127.0.0.1:8182` (no variations)

---

## 2026-02-05

### Done
- Task created with full nano-spec (README, todo, doc, log)
- Analyzed Portfolio.csv: ~50+ positions across 3 brokerages (ML, Schwab, Fidelity) and 4 account types (IRA, Roth IRA, Investment, 401K)
- Reviewed existing Telegram bot architecture and Notion integration patterns
- Identified Copilot spending analyzer as reference implementation pattern
- Documented technical architecture and data flow

### Revision 1 - Open Questions Resolved + Schwab API
- Heath confirmed: consolidated positions, >7% drop alert, track dividends, 9:30 PM ET alert, track adds/removes + monthly reminder
- Researched ThinkorSwim/Schwab API status:
  - TD Ameritrade API permanently discontinued (May 2024)
  - Schwab Trader API is live at developer.schwab.com (replacement)
  - ThinkorSwim itself has no public API
  - schwab-py (by alexgolec, same author as tda-api) is the community Python library
- Major architecture upgrade: Schwab API becomes primary data source for Schwab accounts (IRA, Roth IRA, Investment)
  - Eliminates manual CSV updates for majority of holdings
  - Provides real-time quotes, positions, cost basis directly
  - OAuth 2.0 with 30-min access tokens (auto-refreshed by schwab-py)
- CSV remains for ML IRA and Fidelity 401K (no retail APIs available)
- Added dividend tracking as Phase 4 with separate Notion database
- Added position change detection and monthly reminder system
- Updated phases from 6 to 9 to reflect expanded scope

---

<!-- Copy the template above for each day -->
