# Government bond yields and policy rates: US versus China, with peers (2019 to 17 November 2026)

Conventions used throughout
- All numbers were read from a source during this session (17 Nov 2026). "Not found" means exactly that. Anything labelled DERIVED is simple arithmetic on two cited numbers.
- Source shorthand: AV = Alpha Vantage API (TREASURY_YIELD, FEDERAL_FUNDS_RATE, FX_MONTHLY; monthly values, dated the first of the month, are monthly averages for yields) — [Alpha Vantage](https://www.alphavantage.co/documentation/). FMP = Financial Modeling Prep treasury-rates endpoint (daily Treasury par yields) — [FMP](https://site.financialmodelingprep.com/developer/docs). FRED/OECD = OECD "Long-Term Government Bond Yields: 10-Year: Main (Including Benchmark)" monthly series on FRED. TE = Trading Economics.
- Basis warning: peer-country history is monthly (OECD, mostly monthly averages); "latest" peer values are TE spot quotes on 17 Nov 2026. Changes over 1/3/5 years are computed monthly-to-monthly on the same series so the basis is consistent.
- CSV convention: every file in `data/` has a single header row, no comment lines; first column is `date` (ISO; monthly series use the first day of the month), value columns in percent (or CNY per USD). Sparse/multi-source files carry extra `basis`/`source` columns. Values are saved exactly as returned by the source (hence long decimals for Germany/Canada).

Data files written by this note (all in `/home/claude/cm-research-desk/research_notes/Dollar versus renminbi debt markets/data/`)
- `us_10y_yield_monthly.csv` — US 10-year, monthly, Jan 2019 to Oct 2026 (AV)
- `us_fed_funds_effective_monthly.csv` — effective fed funds rate, monthly, Jan 2019 to Oct 2026 (AV)
- `us_treasury_2y_10y_30y_yearend_and_recent_daily.csv` — US 2y/10y/30y at each year-end 2019–2025 and daily 26 Oct to 16 Nov 2026 (FMP)
- `china_10y_yield_observations.csv` — every China 10-year observation found (sparse, mixed basis, with source column; one row is DERIVED and labelled)
- `china_10y_yield_daily_2026-09-21_to_2026-10-23.csv` — China 10-year daily closes (Investing.com)
- `china_yield_curve_snapshots.csv` — China curve by maturity, 16 and 17 Nov 2026 (ADB, TE)
- `policy_rate_events_us_china.csv` — dated policy-rate levels found for PBoC and Fed
- `peers_10y_yield_monthly_long.csv` — long format (date,country,value) for US, Japan, Germany, UK, France, Canada, Australia, South Korea, Switzerland, India, Jan 2019 to Sep/Oct 2026; plus one `peer_10y_monthly_<country>.csv` per country (date,value)
- `comparison_10y_yields_table.csv` — 10-year yields at end-2021, end-2023, end-2024, end-2025 (December monthly values) and latest, 12 countries
- `usdcny_month_end_close.csv` — USD/CNY closes: year-ends 2019–2023, month-ends Jan 2024 to 17 Nov 2026 (AV)
- `us_ig_corporate_effective_yield.csv` — ICE BofA US Corporate Index effective yield, year-ends 2023–2025 and daily 15 Oct to 13 Nov 2026 (FRED)

## 1. Current and year-end yields and policy rates in the US and China; when China's 10-year fell below the US; the gap now

### Takeaway
On 16–17 Nov 2026 the US curve sits at about 4.83% (2y), 5.12% (10y) and 5.46% (30y) against China at about 1.23–1.28% (2y), 1.62% (10y) and 2.07% (30y): a 10-year gap of about 3.5 percentage points, close to the record (3.5–3.7 points reported in Sep–Oct 2026). China's 10-year first traded below the US 10-year in April 2022 and hit an all-time low of about 1.59% on 6 Nov 2026 while the US 10-year was near its highest in 19 years.

### Cited Findings

US Treasury yields (daily par yields, FMP)

| Date | 2y | 10y | 30y |
|---|---|---|---|
| 2019-12-31 | 1.58 | 1.92 | 2.39 |
| 2020-12-31 | 0.13 | 0.93 | 1.65 |
| 2021-12-31 | 0.73 | 1.52 | 1.90 |
| 2022-12-30 | 4.41 | 3.88 | 3.97 |
| 2023-12-29 | 4.23 | 3.88 | 4.03 |
| 2024-12-31 | 4.25 | 4.58 | 4.78 |
| 2025-12-31 | 3.47 | 4.18 | 4.84 |
| 2026-11-13 | 4.88 | 5.15 | 5.47 |
| 2026-11-16 | 4.83 | 5.12 | 5.46 |

- All rows above — [FMP treasury-rates](https://site.financialmodelingprep.com/developer/docs). Also on 16 Nov 2026: 3-month 4.34%, 1-year 4.62%, 5-year 4.93%, 20-year 5.51% (same source).
- US 10-year monthly averages: Oct 2026 5.13%, Sep 2026 4.99%, Aug 2026 4.68%, Dec 2025 4.14%, Dec 2024 4.39%, Dec 2023 4.02%, Dec 2022 3.62%, Dec 2021 1.47%, Dec 2020 0.93%, Dec 2019 1.86% — [Alpha Vantage TREASURY_YIELD](https://www.alphavantage.co/documentation/). This confirms the desk's "about 5.1% in mid-November 2026" (5.10% on 12 Nov, 5.15% on 13 Nov, 5.12% on 16 Nov per FMP; TE shows 5.125% on 17 Nov — [Trading Economics](https://tradingeconomics.com/china/government-bond-yield)).
- The US 10-year rose above 5% on 15 Sep 2026 (5.02%), described as its highest in 19 years — [Al Jazeera, 16 Sep 2026](https://www.aljazeera.com/economy/2026/9/16/us-fed-raises-interest-rates-as-inflation-weighs-on-economy). It was 5.22% on Thursday 8 Oct 2026 — [The Star/SCMP, 10 Oct 2026](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/10/10/can-china-use-its-widening-us-yield-gap-to-boost-the-yuans-global-role).
- Effective fed funds rate, monthly average (December of each year): 2019 1.55%, 2020 0.09%, 2021 0.08%, 2022 4.10%, 2023 5.33%, 2024 4.48%, 2025 3.72%; Oct 2026 3.88% — [Alpha Vantage FEDERAL_FUNDS_RATE](https://www.alphavantage.co/documentation/). Target range since 16 Sep 2026: 3.75%–4.00% — [Saxo, 17 Sep 2026](https://www.home.saxo/content/articles/macro/fed-review-the-hike-was-expected-the-message-was-more-hawkish-17092026).

China government bond yields
- 17 Nov 2026 (TE): 1-year 1.22%, 2-year 1.28%, 3-year 1.30%, 5-year 1.44%, 7-year 1.49%, 10-year 1.62% (1.6186), 20-year 2.08%, 30-year 2.07%. Change over one year: 2y −0.163, 10y −0.206, 30y −0.022 points; over one month: 10y −0.045 — [Trading Economics](https://tradingeconomics.com/china/government-bond-yield).
- 16 Nov 2026 close (ADB): 2-year 1.229% (YTD −13.6bp), 5-year 1.353% (YTD −26.0bp), 10-year 1.620% (YTD −22.3bp) — [ADB AsianBondsOnline](https://asianbondsonline.adb.org/china/data.php). Note TE and ADB differ by about 5–9bp at the 2y and 5y points.
- All-time low: about 1.59% on 6 Nov 2026, attributed to safe-haven demand in an equity selloff and the PBoC's move to a 1.25% overnight policy rate — [Trading Economics news](https://tradingeconomics.com/china/government-bond-yield/news/599819).
- Other dated 10-year levels: 1.75% (17 Jun 2026) — [Reuters via Financial Express](https://today.thefinancialexpress.com.bd/print/china-bonds-emerge-as-surprise-haven-as-iran-war-reshapes-portfolios-1781712033); 1.683% (30 Sep 2026), 1.720% (9–10 Oct 2026), 1.590% (22 Oct 2026), 1.615% (23 Oct 2026) — [Investing.com](https://www.investing.com/rates-bonds/china-10-year-bond-yield-historical-data); briefly 1.87% on 4 Dec 2025 — [Caixin, 5 Dec 2025](https://www.caixinglobal.com/2025-12-05/analysis-is-it-time-to-go-long-chinas-government-bonds-102390039.html); monthly average about 3.24% in Jan 2021 falling to about 1.64% in Jan 2025, a 160bp drop over 49 months — [Sohu macro report](https://www.sohu.com/a/965128924_121123901); 2.1518% for Oct 2024 and 2.6751% a year earlier (CCDC monthly series) — [GuruFocus](https://gurufocus.com/economic_indicators/4447/longterm-government-bond-yields-10year-main-including-benchmark-for-china); 2.56% for Dec 2023 — [TheGlobalEconomy](https://www.theglobaleconomy.com/China/government_bond_yield/) (a GuruFocus search snippet showed 2.66% "as of 2023-12-01" for the same month; conflict unresolved — [GuruFocus mobile](https://m.gurufocus.com/economic_indicators/4447/longterm-government-bond-yields-10year-main-including-benchmark-for-china)).
- China 30-year: about 2.15% on 18 Aug 2026 — [Whalesbook, 19 Aug 2026](https://www.whalesbook.com/news/English/economy/China-Bond-Yields-Slip-to-215percent-as-Global-Rates-Hit-Multi-Year-Highs/6a85083c84d2dd5c12da8b80) (low-authority aggregator).
- PBoC policy rates: 7-day reverse repo 1.40% effective 7 May 2025, down 10bp from the rate set 27 Sep 2024; unchanged year to date in 2026 — [ADB AsianBondsOnline](https://asianbondsonline.adb.org/china/data.php). From Monday 2 Nov 2026 the main policy rate is the overnight reverse repo rate at 1.25% — [Caixin, 2 Nov 2026](https://www.caixinglobal.com/2026-11-02/china-shifts-main-policy-rate-to-overnight-reverse-repo-rate-102499911.html). Loan prime rates 3.0% (1-year) and 3.5% (5-year), unchanged for 17 consecutive months as of the October 2026 fixing — [TrendForce](https://datatrack.trendforce.com/blog/content/66047/chinas-1-year-lpr-remains-unchanged-at-30-for-17-consecutive-months-as-the-central-bank-brews-pricing-benchmark-transition) (page is AI-generated; headline consistent with investinglive and Dow Jones headlines seen in search).

Crossover and gap
- China's 10-year yield fell below the US 10-year in April 2022 (article dated 11 Apr 2022; spread −0.20bp), the first time in more than a decade; the spread was last that low in June 2010 — [Caixin, 11 Apr 2022](https://www.caixinglobal.com/2022-04-11/china-yield-premium-over-us-vanishes-as-treasury-yields-spike-101868328.html).
- Gap about 3.5 points on 8 Oct 2026 (US 5.22%, China 1.69%), versus "a record 3.7 points on 9 Sep" — [The Star/SCMP](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/10/10/can-china-use-its-widening-us-yield-gap-to-boost-the-yuans-global-role); contradicted on the record date/size by a report of "a record 352 basis points" in mid-October 2026 — [Nerdlyst](https://nerdlyst.com/foreign-holdings-of-china-bonds-september-2026/).

### Inferences
- DERIVED current gap: US 10y 5.12% (16 Nov, FMP) minus China 10y 1.62% (16 Nov, ADB) = 3.50 points. 2-year gap: 4.83 − 1.229 = about 3.60 points. 30-year gap: 5.46 − 2.07 (TE, 17 Nov) = about 3.39 points.
- DERIVED China end-2025 levels from ADB's YTD changes: 10y ≈ 1.843% (1.620 + 0.223), 5y ≈ 1.613%, 2y ≈ 1.365%. TE's one-year change implies about 1.82% in mid-Nov 2025.
- The China curve is steep at the long end (10y–30y about 45bp; 2y–10y about 34–39bp) while the 30-year has barely moved in a year (−0.02), so the 2026 rally is a front-end and belly story driven by policy-rate/liquidity easing rather than a collapse in long-run growth/inflation expectations.

### Gaps
- China 10-year year-end closes for 2019, 2020, 2021, 2022 and 2024: not found (FRED has no China long-term yield series under the OECD naming pattern; TheGlobalEconomy, GuruFocus, WorldGovernmentBonds, ChinaBond and Investing.com pages did not return history). End-2023 has two conflicting monthly values (2.56% / 2.66%). End-2025 is derived, not read.
- China 2-year and 30-year year-end history 2019–2025: not found.
- PBoC 7-day reverse repo level at each year-end 2019–2023: not found in this session (only the 27 Sep 2024, 7 May 2025 and 2 Nov 2026 change dates were read).
- Fed target ranges at year-ends were not read directly; effective-rate monthly averages are given instead.

## 2. How 10-year yields moved over 1, 3 and 5 years in 11 economies; is China alone?

### Takeaway
Over the past year and the past five years, China is the only one of the 11 named economies (and the only one of 12 including Switzerland) whose 10-year yield fell; every other market is up 0.4 to 1.9 points over one year. Over three years the claim is not strictly true: Switzerland's 10-year also fell (about −0.5 point), and Canada and India are roughly flat.

### Cited Findings

10-year yields, percent (monthly values; sources below the table)

| Country | Dec 2021 | Dec 2023 | Dec 2024 | Dec 2025 | Latest monthly | Spot 17 Nov 2026 (TE) |
|---|---|---|---|---|---|---|
| US | 1.47 | 4.02 | 4.39 | 4.14 | 5.13 (Oct 26) | 5.125 |
| Japan | 0.070 | 0.620 | 1.090 | 2.060 | 2.755 (Oct 26) | 2.877 |
| Germany | −0.384 | 2.102 | 2.179 | 2.814 | 3.416 (Oct 26) | 3.385 |
| France | 0.0493 | 2.6549 | 3.0164 | 3.5542 | 4.4771 (Sep 26) | 4.952 |
| UK | 0.8375 | 3.8622 | 4.4345 | 4.4826 | 5.2421 (Sep 26) | 5.3515 |
| Canada | 1.450 | 3.234 | 3.162 | 3.388 | 3.883 (Sep 26) | 3.819 |
| Australia | 1.609 | 4.187 | 4.313 | 4.719 | 5.265 (Oct 26) | 5.138 |
| India | 6.440 | 7.224 | 6.778 | 6.633 | 7.380 (Oct 26) | 7.280 |
| South Korea | 2.187 | 3.415 | 2.771 | 3.366 | 4.454 (Sep 26) | not found |
| Switzerland | −0.127 | 0.656 | 0.317 | 0.330 | 0.590 (Sep 26) | 0.5694 |
| Brazil | not found | not found | not found | not found | not found | 15.565 |
| China | not found | 2.56 | not found | ≈1.843 (derived) | — | 1.6186 |

- Sources: US — [Alpha Vantage](https://www.alphavantage.co/documentation/); Japan — [FRED IRLTLT01JPM156N](https://fred.stlouisfed.org/data/IRLTLT01JPM156N.txt); Germany — [FRED IRLTLT01DEM156N](https://fred.stlouisfed.org/data/IRLTLT01DEM156N.txt); France — [FRED IRLTLT01FRM156N](https://fred.stlouisfed.org/data/IRLTLT01FRM156N.txt); UK — [FRED IRLTLT01GBM156N](https://fred.stlouisfed.org/data/IRLTLT01GBM156N.txt); Canada — [FRED IRLTLT01CAM156N](https://fred.stlouisfed.org/data/IRLTLT01CAM156N.txt); Australia — [FRED IRLTLT01AUM156N](https://fred.stlouisfed.org/data/IRLTLT01AUM156N.txt); India — [FRED INDIRLTLT01STM](https://fred.stlouisfed.org/data/INDIRLTLT01STM.txt); South Korea — [FRED IRLTLT01KRM156N](https://fred.stlouisfed.org/data/IRLTLT01KRM156N.txt); Switzerland — [FRED IRLTLT01CHM156N](https://fred.stlouisfed.org/data/IRLTLT01CHM156N.txt); spot column and Brazil/China — [Trading Economics](https://tradingeconomics.com/china/government-bond-yield) (the TE cross-country table carries no per-row dates; page read 17 Nov 2026). TE also lists Italy 4.4684%, Russia 16.79%, South Africa 8.755%, Chile 6.00%.
- Brazil 10-year: 15.51% on 16 Nov 2026, about 1.85–1.90 points higher than a year earlier and 2.37–2.42 points higher than a month earlier; recent high 15.75% on 3 Nov 2026 — [Trading Economics Brazil](https://tradingeconomics.com/brazil/government-bond-yield).
- China 10-year one-year change: −0.206 point to 1.62% (17 Nov 2026) — [Trading Economics](https://tradingeconomics.com/china/government-bond-yield).
- Since the Iran war began, Chinese government bond yields fell 8bp while benchmark yields in the US, Britain, Europe and Japan rose 35–60bp; "Chinese yields are the lowest outside Switzerland" (Reuters, 17 Jun 2026) — [Financial Express](https://today.thefinancialexpress.com.bd/print/china-bonds-emerge-as-surprise-haven-as-iran-war-reshapes-portfolios-1781712033).
- Global milestones on 1 Sep 2026 (Reuters): Japan 10y 3% (first since 1996), Germany 3.35% (highest since 2011), UK 5.25% (highest since 2008), US 30y 5.27% — [BNN Bloomberg/Reuters](https://www.bnnbloomberg.ca/investing/2026/09/01/global-bond-rout-deepens-as-japan-yield-hits-key-milestone/).
- Press wording found stops short of "only": China's market is moving "in the opposite direction of most major global economies" — [Whalesbook, 19 Aug 2026](https://www.whalesbook.com/news/English/economy/China-Bond-Yields-Slip-to-215percent-as-Global-Rates-Hit-Multi-Year-Highs/6a85083c84d2dd5c12da8b80). No source read in this session used the exact phrase "the only major currency whose debt yields were going lower".

### Inferences

DERIVED changes in 10-year yield, percentage points, same-month monthly values (latest month vs the same month 1, 3 and 5 years earlier)

| Country | Latest month | 1 year | 3 years | 5 years |
|---|---|---|---|---|
| US | Oct 2026 | +1.07 (4.06→5.13) | +0.33 (4.80→5.13) | +3.55 (1.58→5.13) |
| Japan | Oct 2026 | +1.10 (1.655→2.755) | +1.81 (0.950) | +2.66 (0.095) |
| Germany | Oct 2026 | +0.80 (2.618→3.416) | +0.59 (2.823) | +3.62 (−0.204) |
| France | Sep 2026 | +0.96 (3.5172→4.4771) | +1.24 (3.2420) | +4.44 (0.0363) |
| UK | Sep 2026 | +0.55 (4.6885→5.2421) | +0.82 (4.4199) | +4.44 (0.8023) |
| Canada | Sep 2026 | +0.66 (3.2245→3.8825) | +0.07 (3.816) | +2.62 (1.263) |
| Australia | Oct 2026 | +1.03 (4.234→5.265) | +0.63 (4.633) | +3.56 (1.710) |
| India | Oct 2026 | +0.90 (6.482→7.380) | +0.03 (7.350) | +1.02 (6.360) |
| South Korea | Sep 2026 | +1.61 (2.849→4.454) | +0.51 (3.949) | +2.39 (2.061) |
| Switzerland | Sep 2026 | +0.39 (0.200→0.590) | −0.50 (1.087) | +0.76 (−0.166) |
| Brazil | 16 Nov 2026 | about +1.85 to +1.90 (TE) | not found | not found |
| China | 17 Nov 2026 | −0.21 (TE) | about −1.06 (2.6751 in Oct 2023 → 1.62) | about −1.6 (≈3.24 in Jan 2021 → 1.62; no Oct/Nov 2021 point found) |

- Count of the 11 named economies with a lower 10-year yield: 1 year — 1 (China); 3 years — 1 (China), with Canada (+0.07) and India (+0.03) essentially flat; 5 years — 1 (China; Brazil's 5-year change not found, but its yield is 15.5% and up sharply on the year).
- Adding Switzerland: it also qualifies over 3 years (−0.50), and over the window from its Dec 2022 peak (1.565%) or Dec 2023 (0.656%) to Dec 2025 (0.330%). But the Swiss 10-year has risen in 2026 (0.330% in Dec 2025 → 0.590% in Sep 2026, 0.5694% spot on 17 Nov). So the claim "China/renminbi is the only major one whose yields are going lower" is true for 2026 year to date, the last 12 months and the last five years, and false on a strict 3-year or 2023–2025 window because of Switzerland. Switzerland remains the only market with a lower absolute 10-year yield than China.
- Even on a 2024-to-date view the claim holds for the 11: India (6.78% Dec 2024 → 7.38% Oct 2026) and South Korea (2.77% → 4.45%) fell during 2024–25 but have since reversed.
- Why each path differs (drivers cited in sources): the US/Europe/UK/Japan selloff is attributed to the oil and gas shock from the US-Iran war and Russia-Ukraine, inflation expectations, deficit-driven supply (US debt US$40 trillion), heavy AI-related corporate issuance, price-sensitive buyers replacing central banks, and rate-hike pricing (ECB, Fed, BoJ) — [BNN Bloomberg/Reuters](https://www.bnnbloomberg.ca/investing/2026/09/01/global-bond-rout-deepens-as-japan-yield-hits-key-milestone/). China's divergence is attributed to ample energy reserves, structurally low price pressure from weak consumption, a dovish central bank, household savings flowing into bonds, abundant liquidity and capital controls that keep money at home — [Reuters via Financial Express](https://today.thefinancialexpress.com.bd/print/china-bonds-emerge-as-surprise-haven-as-iran-war-reshapes-portfolios-1781712033).

### Gaps
- TE spot for France (4.952%) is about 47bp above the Sep 2026 OECD monthly average (4.4771%) and would imply a spread of about 157bp over Germany; not corroborated by a second source in this session — treat as unverified.
- Brazil 10-year history (end-2021, 2023, 2024, 2025) and 3- and 5-year changes: not found (no FRED series; WorldGovernmentBonds page returned blanks; TE cross-country bonds table did not load).
- South Korea spot on 17 Nov 2026: not found (latest is the Sep 2026 monthly value).
- Exact origin of the quoted claim "the renminbi was the only major currency whose debt yields were going lower": not found.
- China 3- and 5-year changes are approximate because no same-month China observations for Nov 2023 and Nov 2021 were found.

## 3. Real yields and inflation in the US and China

### Takeaway
China is no longer in outright deflation on the headline measures: October 2026 CPI was +0.7% year on year and PPI +5.7% (a more-than-four-year high, energy and metals driven), but core CPI is only 0.8% and food prices are falling. US CPI ran at 3.7% in September 2026 with October up 0.4% on the month. On headline CPI the 10-year real yield is roughly +1.4 points in the US and +0.9 point in China; the US nominal premium is mostly an inflation premium plus roughly half a point of extra real yield.

### Cited Findings
- China CPI, Oct 2026: 0.0% m/m, +0.7% y/y; Jan–Oct average +0.9%. Core CPI (ex food and energy) +0.8% y/y, Jan–Oct +1.1%. Food −2.9% y/y — [NBS, Consumer Price Index in October 2026](https://www.stats.gov.cn/english/PressRelease/202611/t20261111_1965808.html).
- China PPI, Oct 2026: +5.7% y/y, +0.7% m/m; purchasing prices +7.9% y/y; Jan–Oct average PPI +2.7%. Largest rises: oil and gas extraction +35.0%, petroleum/coal/fuel processing +29.9%, non-ferrous smelting +18.6%, mining +27.9% — [NBS, Industrial Producer Price Indexes in October 2026](https://www.stats.gov.cn/english/PressRelease/202611/t20261111_1965806.html).
- Context: CPI eased from 0.9% in September (forecast 0.8%); PPI rose from 5.0% in September (forecast 5.3%); commentary describes "persistent upstream cost pressure and weak domestic demand, with higher input costs not yet passed through to consumers" — [Trading Economics news](https://tradingeconomics.com/china/government-bond-yield/news/599819).
- China CPI in late 2025/early 2026: Oct 2025 +0.2%, Nov 2025 +0.7%, Dec 2025 +0.8%, Jan 2026 +0.2% — [ADB market summary, Mar 2026](https://asianbondsonline.adb.org/china/market_summary/cn_market_summary_202603.pdf). Search-result headlines read (not fetched in full) gave Oct 2025 PPI −2.1% y/y and Sep 2025 PPI −2.8% — [Mysteel headline](https://www.mysteel.net/news/5103592-nbs-chinas-oct-cpi-gains-02-ppi-falls-21-yoy).
- China activity, Oct 2026: industrial production +4.8% y/y (three-month low), retail sales +0.4% (from 1.1%), fixed-asset investment −8.1% Jan–Oct, new-home prices −2.4% y/y, exports +35.2% y/y — [Trading Economics news](https://tradingeconomics.com/china/government-bond-yield/news/599819). Q2 2026 GDP growth 4.3% versus a 4.5–5.0% target — [Whalesbook](https://www.whalesbook.com/news/English/economy/China-Bond-Yields-Slip-to-215percent-as-Global-Rates-Hit-Multi-Year-Highs/6a85083c84d2dd5c12da8b80) (low-authority source).
- US CPI: Sep 2026 +0.6% m/m, 3.7% y/y; Oct 2026 +0.4% m/m (forecast +0.3%), core +0.3% m/m; no October year-on-year figure because the BLS did not collect October 2025 prices during the shutdown; energy +0.7% in October after +5.2% in September (released 10 Nov 2026) — [StockAnalysis, 10 Nov 2026](https://stockanalysis.com/news/us-cpi-rises-october-2026/). August 2026 CPI 3.4% y/y — [Al Jazeera](https://www.aljazeera.com/economy/2026/9/16/us-fed-raises-interest-rates-as-inflation-weighs-on-economy).
- US core measures: core CPI 2.6% y/y in Sep 2026; core PCE 3.0% in Aug 2026 (also 3.0% in June and July) — [Admiral Markets](https://admiralmarkets.com/analytics/traders-blog/fomc-october-2026-fed-holds-rates). Fed September projections: 2026 PCE inflation 3.7%, core PCE 3.4%; median PCE not back to 2% until 2029 — [Saxo](https://www.home.saxo/content/articles/macro/fed-review-the-hike-was-expected-the-message-was-more-hawkish-17092026).
- US 10-year breakeven inflation about 2.35% after the 16 Sep 2026 decision; rising long-term US yields are "driven mainly by higher real yields" — [Saxo](https://www.home.saxo/content/articles/macro/fed-review-the-hike-was-expected-the-message-was-more-hawkish-17092026); [BNN Bloomberg/Reuters](https://www.bnnbloomberg.ca/investing/2026/09/01/global-bond-rout-deepens-as-japan-yield-hits-key-milestone/).
- Energy shock: Brent near $109 on 15 Sep 2026; US diesel $6.31/gallon, a record — [Al Jazeera](https://www.aljazeera.com/economy/2026/9/16/us-fed-raises-interest-rates-as-inflation-weighs-on-economy); WTI just above $100, up 78% year to date on 28 Oct 2026 — [StockAnalysis](https://stockanalysis.com/news/fed-holds-rates-steady-oct-2026/).

### Inferences
- DERIVED ex-post real 10-year yields (nominal minus latest y/y inflation): US 5.12 − 3.7 (Sep CPI) ≈ +1.4; versus core PCE 3.0 ≈ +2.1; market-implied (10y about 5.0 on 16 Sep minus 2.35 breakeven) ≈ +2.65. China 1.62 − 0.7 (CPI) ≈ +0.9; versus core CPI 0.8 ≈ +0.8; versus PPI 5.7 ≈ −4.1 (deeply negative for producers).
- DERIVED real policy rates: Fed midpoint 3.875 − 3.7 ≈ +0.2; PBoC 1.25 − 0.7 ≈ +0.55. On headline CPI China's real policy rate is higher than the US's; on core measures the US is tighter.
- The "deflation" explanation for low Chinese yields is dated: PPI moved from −2.1% (Oct 2025) to +5.7% (Oct 2026). Yields fell anyway, which points to weak domestic demand (retail sales +0.4%, investment −8.1%), liquidity and policy easing as the 2026 drivers. The PPI rise is imported cost-push, with CPI and core CPI below 1%.
- A real-yield comparison deflated by producer prices would say Chinese corporate borrowers face sharply negative real rates in late 2026, the opposite of 2023–25.

### Gaps
- Monthly China CPI/PPI path for Feb–Sep 2026 (and the month PPI turned positive): not found in fetched sources.
- China GDP deflator for 2025–26: not found.
- US TIPS yields and October 2026 PCE: not found. US October CPI year on year is not published.

## 4. What the Fed and PBoC did in 2025–26 and what markets price next

### Takeaway
The desk's note is confirmed: the Fed raised rates by 25bp to 3.75%–4.00% on 16 Sep 2026 (its first hike since 2023, unanimous), held on 28 Oct in a 10–2 vote with two dissents for a hike, and markets price roughly 80–85% odds of another hike on 9 Dec with futures near 4.7% by Sep 2027. The PBoC has gone the other way: one 10bp cut in May 2025, loan prime rates frozen for 17 months, then on 2 Nov 2026 a switch to an overnight policy rate set at 1.25%, below the old 1.40% benchmark.

### Cited Findings
- Fed, 2025: effective fed funds averaged 4.33% from Jan to Aug 2025, then 4.22% (Sep), 4.09% (Oct), 3.88% (Nov), 3.72% (Dec) and 3.64% (Jan 2026), flat at 3.63–3.64% to Aug 2026, then 3.75% (Sep) and 3.88% (Oct 2026) — [Alpha Vantage FEDERAL_FUNDS_RATE](https://www.alphavantage.co/documentation/).
- 16 Sep 2026: +25bp to 3.75%–4.00%, unanimous; first increase since 2023; statement dropped the July language attributing inflation to supply shocks. Median projections: fed funds 4.1% end-2026 and end-2027, 3.9% end-2028; 16 of 18 policymakers expect at least one more hike in 2026. Chair Warsh called the move removing a "dose of accommodation" — [Saxo, 17 Sep 2026](https://www.home.saxo/content/articles/macro/fed-review-the-hike-was-expected-the-message-was-more-hawkish-17092026). Causes cited: fuel prices tied to the US-Iran war, tariffs and AI capital spending; President Trump said rates "should be 1%, or less" — [Al Jazeera](https://www.aljazeera.com/economy/2026/9/16/us-fed-raises-interest-rates-as-inflation-weighs-on-economy).
- 28 Oct 2026: held at 3.75%–4.00%, 10–2 (Hammack and Cook dissented for a hike); growth description upgraded from "solid" to "strong"; 10-year closed 5.03%; CME FedWatch 78% for a December hike — [StockAnalysis](https://stockanalysis.com/news/fed-holds-rates-steady-oct-2026/). Other reads: about 84–85% for a 9 Dec hike; futures about 4.7% by Sep 2027 (about three more hikes) — [Admiral Markets](https://admiralmarkets.com/analytics/traders-blog/fomc-october-2026-fed-holds-rates).
- 10 Nov 2026: before October CPI, better than 80% odds of a December hike; Governor Waller said a 50bp hike "should be considered" if core CPI came in around 0.3% or higher (it printed 0.3%); 2-year yield jumped to 4.69% from 4.55%. Next FOMC 8–9 Dec 2026 — [StockAnalysis](https://stockanalysis.com/news/us-cpi-rises-october-2026/).
- PBoC: 7-day reverse repo cut 10bp to 1.40% effective 7 May 2025 — [ADB](https://asianbondsonline.adb.org/china/data.php). Governor Pan previewed a shift to the overnight rate in Sep 2026; announced 30 Oct, effective 2 Nov 2026, overnight reverse repo at 1.25%; overnight market borrowing costs fell to about 1.25% from about 1.4% earlier in the year — [Caixin](https://www.caixinglobal.com/2026-11-02/china-shifts-main-policy-rate-to-overnight-reverse-repo-rate-102499911.html). The PBoC resumed government bond buying in Oct 2025 — [ADB market summary](https://asianbondsonline.adb.org/china/market_summary/cn_market_summary_202603.pdf).
- LPR 3.0%/3.5% unchanged for 17 months through Oct 2026; near-term expectation is no change, with any easing delivered by guiding short-term market rates lower — [TrendForce](https://datatrack.trendforce.com/blog/content/66047/chinas-1-year-lpr-remains-unchanged-at-30-for-17-consecutive-months-as-the-central-bank-brews-pricing-benchmark-transition). A search headline framed the Sep 2026 hold as "Fed hike narrows room to ease" — [investinglive](https://investinglive.com/central-banks/china-holds-loan-prime-rates-for-16th-month-as-fed-hike-narrows-room-to-ease/) (headline only; page not fetched).

### Inferences
- The effective-rate path implies three 25bp Fed cuts in Sep, Oct and Dec 2025 to a 3.50%–3.75% range, held until the Sep 2026 hike. This is inferred from monthly averages; the individual 2025 decisions were not read.
- Policy-rate gap: Fed midpoint 3.875% versus PBoC 1.25% = about 2.6 points, set to widen to about 2.9 points if the Fed hikes in December.
- Whether the 1.25% overnight rate is a "cut" is ambiguous: it is 15bp below the old 7-day rate but a different tenor; TE describes it as set "below the prior seven-day benchmark" and bond yields hit a record low four days later.

### Gaps
- Market pricing for PBoC moves (swap-implied) and any RRR changes in 2025–26: not found.
- Official Fed/PBoC statements were not read directly (secondary sources only); the fxstreet, Bloomberg, Edge Singapore, Morningstar/Dow Jones and NST pages could not be fetched.
- The 20 Nov 2026 LPR fixing has not happened yet.

## 5. The dollar–renminbi exchange rate and the renminbi as a funding currency

### Takeaway
The renminbi has appreciated steadily despite the record yield gap: USD/CNY is about 6.67 on 17 Nov 2026 versus 6.99 at end-2025 and 7.30 at end-2024. That combination (low rate, low volatility, mild appreciation) is why strategists now discuss the offshore yuan as an alternative to the yen for carry trades, but an appreciating funding currency erodes carry returns, and foreign holdings of onshore bonds are down about a fifth from the 2025 level.

### Cited Findings
- USD/CNY closes: 6.9632 (end-2019), 6.5272 (end-2020), 6.3561 (end-2021), 6.8972 (end-2022), 7.0978 (end-2023), 7.2994 (end-2024), 6.9879 (end-2025), 6.7050 (30 Sep 2026), 6.6558 (30 Oct 2026), 6.6660 (17 Nov 2026) — [Alpha Vantage FX_MONTHLY](https://www.alphavantage.co/documentation/). ADB shows 6.665 on 16 Nov 2026 with the yuan up 4.6% year to date against the dollar and 6.3% against the yen — [ADB](https://asianbondsonline.adb.org/china/data.php).
- Dollar index about 102 on 28 Oct 2026 — [Admiral Markets](https://admiralmarkets.com/analytics/traders-blog/fomc-october-2026-fed-holds-rates).
- Carry trade (Bloomberg, 9 Sep 2026): borrowing offshore yuan to invest in eight emerging-market currencies returned 1.5% over three months versus −1% funded in yen; Citigroup, Maybank, Societe Generale and BBVA flag the yuan as an alternative funding currency; USD/CNH put option volume up more than 60% month on month. Risks: the yuan is not freely convertible and long-term funding liquidity is thinner than for the yen — [Bloomingbit citing Bloomberg](https://en.bloomingbit.io/feed/news/120010).
- Yuan bond fundraising (onshore plus offshore) topped 1 trillion yuan by early Sep 2026, a record; yuan share of global reserves 2.11% in Q2 versus dollar 56.70%; an analyst notes carry-style borrowing "could cause persistent selling pressure" and that China's market "still lacks sufficient capacity to absorb and retain global capital" — [The Star/SCMP, 10 Oct 2026](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/10/10/can-china-use-its-widening-us-yield-gap-to-boost-the-yuans-global-role).
- Foreign holdings of interbank bonds: about 4 trillion yuan (end-Aug 2025), 3.12 trillion (end-Apr 2026), 3.21 trillion (end-May, first net buying since Apr 2025), 3.19 trillion (end-Sep 2026, about 1.7% of the market). Chinese bonds returned nearly 10% over 12 months for dollar-based investors (TE estimate), i.e. mostly currency — [Nerdlyst](https://nerdlyst.com/foreign-holdings-of-china-bonds-september-2026/) (secondary aggregator citing PBoC, Caixin, TE).
- Investor view (Reuters, Jun 2026): correlation between Chinese government bonds and European rates "close to zero"; "the absolute yield doesn't matter so much" (UBS AM); Guotai 10-Year China Treasury ETF +1.26% YTD versus iShares 7–10 Year Treasury ETF −2.57% — [Financial Express](https://today.thefinancialexpress.com.bd/print/china-bonds-emerge-as-surprise-haven-as-iran-war-reshapes-portfolios-1781712033).

### Inferences
- DERIVED: the dollar has fallen about 4.6% against the yuan in 2026 (6.9879 → 6.6660) and about 8.7% since end-2024 (7.2994 → 6.6660).
- A dollar-based investor borrowing yuan at about 1.3–1.6% to hold Treasuries at about 5% earned roughly 3.5 points of carry in 2026 but lost about 4.6% on the currency: unhedged yuan-funded dollar carry has been roughly break-even to negative this year. The yuan works as a funding currency only if it stops appreciating; against higher-yielding EM currencies it has worked (the +1.5% three-month figure).
- By covered interest parity, a roughly 3.5-point rate gap implies dollar-based investors who buy Chinese bonds and hedge back to dollars should pick up roughly the gap through the forward, lifting hedged yields toward US levels; conversely Chinese borrowers swapping yuan funding into dollars pay it away. This is theory, not a read number.
- For issuers, the incentive runs toward borrowing in yuan (panda/dim sum bonds) at under 2–3% rather than dollars at 5–6%, consistent with record yuan bond fundraising.

### Gaps
- Actual FX-hedged yields on Chinese government bonds or NCDs, USD/CNY swap points, and CNH HIBOR levels in 2026: not found.
- Size of yuan-funded carry positions: not found.
- Offshore CNH rate and CFETS basket index: not found.

## 6. Corporate borrowing costs

### Takeaway
US investment-grade bond yields are about 5.98% (13 Nov 2026), up more than a point from 4.84% at end-2025, with mortgage rates near 7%. China's benchmark loan prime rates are 3.0% (1-year) and 3.5% (5-year), so benchmark corporate borrowing costs in China are roughly half the US level in nominal terms; Chinese corporate bond yields were not found.

### Cited Findings
- ICE BofA US Corporate Index effective yield: 5.14% (end-2023), 5.35% (end-2024), 4.84% (end-2025), 5.79% (30 Oct 2026), 5.98% (13 Nov 2026) — [FRED BAMLC0A0CMEY](https://fred.stlouisfed.org/data/BAMLC0A0CMEY.txt).
- US mortgage rates "nearing 7%" in mid-Sep 2026 — [Saxo](https://www.home.saxo/content/articles/macro/fed-review-the-hike-was-expected-the-message-was-more-hawkish-17092026).
- China LPR: 1-year 3.0%, 5-year-plus 3.5%, unchanged for 17 months to Oct 2026; 1-year was 3.35% in 2024 — [TrendForce](https://datatrack.trendforce.com/blog/content/66047/chinas-1-year-lpr-remains-unchanged-at-30-for-17-consecutive-months-as-the-central-bank-brews-pricing-benchmark-transition).
- Large bond sales by big technology firms funding AI investment are cited as adding to pressure on US yields — [BNN Bloomberg/Reuters](https://www.bnnbloomberg.ca/investing/2026/09/01/global-bond-rout-deepens-as-japan-yield-hits-key-milestone/).
- China Q4 2025: corporate bond issuance down 5.4% q/q; local-currency bonds outstanding CNY174.7 trillion — [ADB market summary](https://asianbondsonline.adb.org/china/market_summary/cn_market_summary_202603.pdf).

### Inferences
- DERIVED: US IG spread over the 10-year Treasury is about 0.83 point (5.98 − 5.15 on 13 Nov 2026), versus about 0.66 at end-2025 (4.84 − 4.18): the rise in US corporate borrowing costs in 2026 is almost entirely the Treasury move.
- DERIVED: 1-year LPR minus China 10-year yield = about 1.4 points; the LPR has not followed government yields down (frozen since May 2025), so bank-loan borrowers have seen less relief than bond issuers. Deflated by PPI (+5.7%), a 3.0% loan rate is negative in real terms for producers; deflated by core CPI (0.8%) it is about +2.2.
- DERIVED nominal gap in benchmark corporate funding: US IG 5.98% versus China 1-year LPR 3.0% ≈ 3 points.

### Gaps
- Chinese corporate bond yields (ChinaBond AAA/AA+ by tenor), credit spreads, and the PBoC weighted-average corporate loan rate for 2026: not found (Cbonds index pages could not be fetched; no PBoC monetary policy report was read).
- US high-yield yields and bank prime rate: not searched.
