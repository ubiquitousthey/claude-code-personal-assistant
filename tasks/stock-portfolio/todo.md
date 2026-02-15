# TODO

## Research
- [ ] Register on Schwab Developer Portal (developer.schwab.com) and create app
- [ ] Test Schwab Trader API: account positions, balances, quotes endpoints
- [ ] Evaluate schwab-py library (https://github.com/alexgolec/schwab-py) for Python integration
- [ ] Evaluate news APIs for financial news by ticker (Finnhub news, NewsAPI, Google News RSS)
- [ ] Search GitHub for portfolio tracker projects, stock analysis tools, and Notion integrations
- [ ] Review yfinance capabilities for non-Schwab accounts (ML, Fidelity) - price history, dividends, splits
- [ ] Determine Schwab API rate limits and token refresh strategy
- [ ] Research dividend data sources for YieldMax ETFs (AMZY, NVDY, TSLY, ULTY, FIAT)

## Implementation

### Phase 1: Schwab API Setup & Authentication
- [ ] Register Schwab Developer Portal account (separate from trading account)
- [ ] Create registered app with "Market Data Production" + "Accounts and Trading Production"
- [ ] Implement OAuth 2.0 flow for Schwab API authentication
- [ ] Build token management (30-min access token refresh, refresh token storage)
- [ ] Test account positions endpoint - verify it returns holdings, cost basis, market value
- [ ] Store Schwab API credentials securely (env vars: SCHWAB_APP_KEY, SCHWAB_APP_SECRET, SCHWAB_REDIRECT_URI)
- [ ] Add schwab-py to project dependencies

### Phase 2: Notion Database & Data Import
- [ ] Design Notion portfolio database schema (consolidated view with per-account detail)
- [ ] Create Notion Holdings database via API
- [ ] Create Notion Daily Snapshots database via API
- [ ] Create Notion Dividend History database via API
- [ ] Build Schwab API position fetcher (auto-sync Schwab IRA, Roth IRA, Investment)
- [ ] Build CSV parser for non-Schwab accounts (ML IRA via Portfolio.csv, Fidelity 401K via Portfolio.csv)
- [ ] Write unified import script: Schwab API + CSV -> Notion
- [ ] Implement position consolidation logic (merge same ticker across accounts for display)
- [ ] Add NOTION_PORTFOLIO_DB_ID, NOTION_SNAPSHOT_DB_ID, NOTION_DIVIDEND_DB_ID to env config

### Phase 3: Daily Price Fetching & Valuation
- [ ] Build price fetcher: Schwab API (primary for Schwab tickers) + yfinance (fallback/ML/Fidelity)
- [ ] Handle special tickers: mutual funds (LRSCX, MALOX), Fidelity pooled funds (31565G759, 31617E778, LSSNX)
- [ ] Calculate per-position: current price, market value, unrealized gain/loss, % change
- [ ] Calculate consolidated per-ticker: total shares, blended cost basis, total gain/loss
- [ ] Calculate portfolio-level: total value, total gain/loss, day change, allocation percentages
- [ ] Update Notion Holdings database with latest prices and calculations
- [ ] Write daily snapshot to Notion Snapshots database (historical trend data)

### Phase 4: Dividend Tracking
- [ ] Fetch dividend data from yfinance (history + upcoming ex-dates)
- [ ] Track YieldMax ETF distributions specifically (monthly payers: AMZY, NVDY, TSLY, ULTY, FIAT)
- [ ] Calculate annual dividend income and yield per position
- [ ] Calculate portfolio-level dividend income (annual, monthly projected)
- [ ] Log dividend payments to Notion Dividend History database
- [ ] Include upcoming ex-dates in daily alert

### Phase 5: News Aggregation
- [ ] Implement news fetcher for portfolio tickers (batch by top holdings by value)
- [ ] Filter and rank news by relevance (earnings, analyst ratings, sector moves, breaking news)
- [ ] Deduplicate news across tickers (e.g., market-wide stories)
- [ ] Format news digest with ticker tags and sentiment indicators

### Phase 6: Telegram Alerts & Commands
- [ ] Create 9:30 PM ET portfolio summary message format
- [ ] Include: total value, day change, top movers (up/down), dividends, notable news
- [ ] Add actionable alerts: earnings upcoming, price drops >7%, dividend ex-dates
- [ ] Integrate with existing Telegram bot (scheduled message at 9:30 PM ET)
- [ ] Add `/portfolio` command to Telegram bot for on-demand summary
- [ ] Add `/portfolio dividends` sub-command for dividend summary
- [ ] Schedule daily alert using APScheduler (9:30 PM ET, weekdays only)

### Phase 7: Position Change Tracking & Monthly Reminders
- [ ] Implement position change detection (compare current vs previous sync)
- [ ] Log position adds/removes/quantity changes to Notion with timestamps
- [ ] For Schwab accounts: auto-detect changes via API
- [ ] For ML/Fidelity: detect changes when new CSV is uploaded
- [ ] Schedule monthly Telegram reminder (1st of month): "Update your ML and Fidelity positions"
- [ ] Include template message with instructions for CSV export from each brokerage

### Phase 8: Bot Integration & CSV Upload
- [ ] Add portfolio CSV as a recognized export type in export_processor.py
- [ ] Support re-importing updated Portfolio.csv via Telegram file upload (updates ML + Fidelity)
- [ ] Add portfolio summary to daily routine workflow
- [ ] Cache portfolio data locally for fast access (similar to Notion cache pattern)

### Phase 9: GitHub Discovery & Integration
- [ ] Search GitHub for: portfolio tracking tools, stock screeners, financial analysis libraries
- [ ] Evaluate: schwab-py, yfinance, openbb, finnhub-python, any Notion portfolio integrations
- [ ] Document recommended projects in doc.md
- [ ] Integrate useful libraries into the pipeline

## Verification
- [ ] Schwab API returns accurate positions matching ThinkorSwim display
- [ ] Import all ~50+ positions from all sources to Notion correctly
- [ ] Verify consolidated view merges same tickers properly (e.g., CRWD from ML + Fidelity)
- [ ] Verify price fetching works for all ticker types (stocks, ETFs, mutual funds, Fidelity pooled)
- [ ] Confirm 9:30 PM ET Telegram alert sends with accurate data (weekdays)
- [ ] Validate gain/loss calculations against brokerage statements
- [ ] Verify dividend tracking captures YieldMax distributions
- [ ] Test >7% price drop alert triggers correctly
- [ ] Confirm monthly position update reminder fires on 1st of month
- [ ] Test news relevance filtering (no spam, actionable content)
- [ ] Verify position change detection logs adds/removes accurately

---

## Acceptance Criteria

### Must Have
- [ ] Schwab accounts auto-synced via API (no manual CSV for Schwab)
- [ ] All portfolio positions tracked in Notion with current prices updated daily
- [ ] Consolidated view: same ticker across accounts shown as one row with total
- [ ] Daily 9:30 PM ET Telegram alert with portfolio summary, movers, and news
- [ ] Accurate gain/loss calculations (within $1 of brokerage values)
- [ ] Support for all three brokerages (ML, Schwab, Fidelity)
- [ ] >7% single-day price drop triggers alert
- [ ] News digest covering at least top 10 holdings by value
- [ ] Dividend tracking with upcoming ex-dates
- [ ] Position change tracking (adds/removes logged)
- [ ] Monthly reminder to update non-API positions (ML, Fidelity)

### Nice to Have
- [ ] Price history charts or sparklines in Notion
- [ ] Sector/allocation breakdown visualization
- [ ] Comparison to benchmark (S&P 500) performance
- [ ] Weekly/monthly performance summary in addition to daily
- [ ] Integration with Copilot spending data for holistic financial view
- [ ] Auto-detect Fidelity NetBenefits export format (if they offer CSV export)

### Out of Scope
- Automated trading or order placement
- Real-time price alerts (intraday)
- Tax optimization recommendations
- Merrill Lynch or Fidelity API integration (manual CSV only for now)
