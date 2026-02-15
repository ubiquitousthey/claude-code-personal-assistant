# Stock Portfolio Tracker

## Background
Heath holds a diversified stock portfolio across multiple brokerages (Merrill Lynch, Schwab, Fidelity) in IRA, Roth IRA, Investment, and 401K accounts. The portfolio contains ~50+ positions spanning individual stocks, ETFs, and mutual funds with a total cost basis of ~$65K+. Currently the portfolio data lives only in a static CSV file (`Portfolio.csv`) with no automated tracking, price updates, or alerting. Heath wants daily visibility into portfolio performance, relevant market news, and actionable insights delivered via Telegram at 9:30 PM ET.

Heath has access to the **ThinkorSwim platform** and the **Schwab Trader API** (developer.schwab.com), which can pull real-time positions, balances, cost basis, and quotes directly for Schwab accounts. This eliminates manual CSV updates for the majority of holdings.

## Goals
- Sync portfolio holdings to a Notion database for persistent tracking and history
- Pull Schwab account positions automatically via Schwab Trader API (IRA, Roth IRA, Investment)
- Fetch daily stock prices and calculate consolidated gain/loss across all accounts
- Track dividends and distributions (especially YieldMax ETFs)
- Surface relevant market news for held tickers
- Send 9:30 PM ET Telegram alerts with portfolio summary and recommended actions
- Track position changes (adds/removes) and send monthly reminder to update holdings
- Discover useful open-source GitHub projects for portfolio analytics or automation

## Scope

### In Scope
- Notion database creation and schema design for portfolio holdings
- **Schwab Trader API integration** for automated position sync (Schwab IRA, Roth IRA, Investment accounts)
- CSV import pipeline for non-Schwab accounts (ML IRA, Fidelity 401K)
- Daily price fetching using yfinance (fallback) + Schwab API (primary for Schwab holdings)
- Consolidated portfolio view across all accounts (same ticker merged for display)
- Dividend/distribution tracking with yield calculations
- Daily portfolio valuation calculation (current value, gain/loss, % change)
- News aggregation for held tickers (financial news APIs)
- 9:30 PM ET Telegram alert via existing bot infrastructure
- Position change tracking (detect adds/removes, log history)
- Monthly Telegram reminder to review and update non-API positions (1st of each month)
- GitHub project discovery for portfolio tooling
- Integration with existing Telegram bot export processor pattern

### Out of Scope
- Real-time/intraday price streaming
- Automated trade execution
- Tax lot tracking or tax-loss harvesting calculations
- Options/derivatives analysis beyond YieldMax ETF holdings
- Portfolio rebalancing recommendations (v1 is informational only)
- Mobile app or web dashboard (Telegram + Notion is the UI)

## Dependencies
- [ ] **Schwab Developer Portal account** - Register at developer.schwab.com, create app, get API keys
- [ ] **Schwab OAuth tokens** - Link brokerage account, complete OAuth flow
- [ ] Free stock price API (yfinance - no key needed, fallback for non-Schwab)
- [ ] News API access (Finnhub free tier for company news)
- [ ] Notion API access (already configured via NOTION_API_KEY)
- [ ] Telegram bot running (already operational)
- [ ] Python environment with required packages (schwab-py, yfinance, requests, etc.)

## Resources
- Portfolio data (initial seed): `/workspace/Portfolio.csv`
- Schwab Developer Portal: https://developer.schwab.com
- schwab-py library: https://github.com/alexgolec/schwab-py
- Telegram bot: `/workspace/telegram-bot/`
- Export processor pattern: `/workspace/telegram-bot/src/bot/features/export_processor.py`
- Existing Notion integration: CLAUDE.md database IDs
- Copilot transaction analyzer (reference pattern): same export_processor.py
- Health sync script (reference pattern): `/workspace/scripts/apple_health_to_notion.py`
