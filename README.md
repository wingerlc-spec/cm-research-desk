# cm-research-desk

Nightly chart and fundamentals screener (screen.py) plus terminal data pulls (terminal_pulls.py), run by
.github/workflows/main.yml on weekdays at 23:30 UTC (5:30pm Central standard time, after the close). Outputs go to out/.

## Rules that shape the output
- No stock price cap (book rule changed 2 Nov 2026). The instrument stays a deep in-the-money call (delta 0.75 to 0.85,
  6 to 15 months out). Affordability is checked on the real contract: ask x 100 up to SLOT_USD ($2,000) fits, up to
  SLOT_STRETCH ($2,700) is a stretch, above that the research tier is kept but `fits_slot` is false and the instrument is
  "shares, or a smaller position". No chain data: `fits_slot` is null.
- Market cap floor of $5B (MIN_MCAP, no upper limit) on today's candidates only. Backtests, survivorship and lens tests keep
  their existing universes: applying today's market cap to history would be look-ahead. Names with no market cap stay in.
- Option liquidity: `ok` = open interest of 100 or more and a spread of 8 percent of mid or less. The floor is 100, not 500,
  because the owner's recent real fills were on strikes with open interest near 90.
- A failed pull leaves fields out and is noted. Nothing is guessed.

## Outputs
- out/screen_output.json, out/market_state_full.json, out/charts/: the screen
- out/options.json: option chain summary for up to 40 researched names
- out/mcap_cache.json: last good market cap per name (fallback up to 10 days old)
- out/terminal/: screen.json, dc_spend.json, dc_capex.json, earnings_dates.json, chains.json, manifest.json

## Tests
`python -m pytest -q tests` (offline). `python tests/make_csv_fixtures.py /tmp/fx` then
`python screen.py --csv-dir /tmp/fx --out /tmp/out --no-charts` for an offline smoke run on synthetic prices.

## CHANGELOG
### v16 (14 Nov 2026)
- Removed the $60 stock price cap and the TOO EXPENSIVE tier; added the SLOT_USD / SLOT_STRETCH check on the chosen option.
- Added the $5B market cap floor (Yahoo marketCap, bulk pull once per run, cached in out/mcap_cache.json) and `mcap_busd`
  on ranked rows and in market_state_full.json.
- Added option chains (Black-Scholes delta, rate 4 percent, dividends ignored) for DEEP DIVE, WATCH and AFTER PRINT names and
  the top lens candidates; chosen contract on each row, full summary in out/options.json.
- Added terminal_pulls.py (Census data center construction, hyperscaler capex from SEC XBRL, earnings dates, watch list
  chains) and out/terminal/screen.json. The workflow runs it with continue-on-error.
- Workflow: cron moved to 30 23 (standard time), beautifulsoup4 and openpyxl added to the install line, the stray nested
  workflow file removed.
