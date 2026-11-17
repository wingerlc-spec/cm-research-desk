# US-dollar-denominated debt worldwide: size, issuance and holders (as of 17 November 2026)

Conventions: every figure carries its period. "Not found" means I could not read the number in a source during this session. Figures marked "(calc.)" are my arithmetic on cited numbers and belong to the Inferences sub-sections. The latest TIC data available on 17 Nov 2026 is for August 2026 (released 16 Oct 2026); the September 2026 release was not located.

Data files saved in `/home/claude/cm-research-desk/research_notes/Dollar versus renminbi debt markets/data/` (each has a header row and a `source_url` column):

- `tic_major_foreign_holders_monthly_2025-08_to_2026-08.csv` — Treasury TIC Table 5, top-20 holders, grand total, foreign official (bills / notes and bonds), 13 months
- `china_treasury_holdings_selected_points_2008_2026.csv` — China's holdings at selected dates (2008 trough, Nov 2013 peak, Dec 2021, 2025-26)
- `foreign_share_of_publicly_held_treasury_debt_2021_2025.csv` — CRS table: debt, foreign holdings, foreign share, Dec 2021 to Dec 2025
- `cofer_usd_share_quarterly_2000_2026.csv` — dollar share of allocated reserves, quarterly 2000 Q1 to 2026 Q2 (secondary compilation of IMF COFER)
- `sifma_us_fixed_income_outstanding_2015_2026Q2.csv` — SIFMA outstanding by asset class (Treasuries, corporates, munis, agency, CP), year-end 2015 to 2Q26
- `z1_treasury_holders_by_sector_2023_2025.csv` — Fed Z.1 table L.210, Treasury holders by sector, year-end 2023 to 2025
- `us_fiscal_and_treasury_issuance_fy2025_fy2026.csv` — receipts, outlays, deficit, net interest, gross and net bill/coupon issuance, FY2025 and FY2026

## 1. US Treasury market: size, issuance, mix, deficit, interest cost, auctions

### Takeaway
Marketable Treasuries outstanding were $31.8 trillion in September 2026 against $16.7 trillion at end-2019, with gross issuance of $31.2 trillion in FY2026 (86% bills) funding a $1.99 trillion deficit and $1.14 trillion of net interest. Demand has not failed, but the November 2026 refunding auctions cleared at 5.02% (10-year) and 5.44% (30-year) with tails and the lowest 10-year indirect share since October 2023.

### Cited Findings
**Size**
- Treasury securities outstanding: $31.8 trillion as of September 2026, up 7.1% year on year — [SIFMA Treasury statistics](https://www.sifma.org/research/statistics/us-treasury-securities-statistics)
- Year-end Treasury outstanding ($ trillion, SIFMA, values read from appendix charts and rounded): 2015 13.2; 2016 13.9; 2017 14.5; 2018 15.6; 2019 16.7; 2020 21.0; 2021 22.6; 2022 23.9; 2023 26.4; 2024 28.3; 2025 30.3; 2Q26 31.1. Precise table values: $28,276.2bn (2024), $30,267.3bn (2025), $31,082.2bn (2Q26, +8.5% y/y) — [SIFMA Fixed Income Outstanding 2Q26](https://www.sifma.org/wp-content/uploads/2026/06/SIFMA-Research-Quarterly-Fixed-Income-O-2Q26.pdf)
- Treasury's own portfolio measure: total Treasury notionals $32.1 trillion on 28 Oct 2026 (private $27.5 trillion; consolidated excluding currency and TGA $28.6 trillion) — [Treasury presentation to TBAC, Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf). Same measure: $31.4 trillion on 29 Jul 2026 — [Treasury presentation to TBAC, Q3 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ32026.pdf); $29.9 trillion on 29 Oct 2025 — [Treasury presentation to TBAC, Q4 2025](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42025.pdf)
- Total federal debt $40.2 trillion at 30 Sep 2026 ($37.6 trillion at 30 Sep 2025; $19.6 trillion at 30 Sep 2016); debt held by the public $32.4 trillion at 30 Sep 2026 ($14.2 trillion at 30 Sep 2016), about 98% of it marketable — [GAO-27-108795](https://www.gao.gov/assets/gao-27-108795.pdf)
- Total US debt crossed $40 trillion on 19 Aug 2026 — [24/7 Wall St, 29 Sep 2026](https://247wallst.com/investing/2026/09/29/china-holds-618-billion-of-u-s-debt-only-2-countries-hold-more/)
- Debt held by the public reached 100% of GDP in 2026, up from 99.0% at end-FY2025 — [CBO Monthly Budget Review, 9 Nov 2026](https://www.cbo.gov/publication/61986)

**Mix (bills, notes, bonds)**
- Share of Treasuries outstanding at 2Q26: notes 51.7%, bills 21.5% (22.1% in 1Q26; 20.2% in 2Q25), bonds 17.6%, TIPS 7.0%, FRN 2.3% — [SIFMA Fixed Income Outstanding 2Q26](https://www.sifma.org/wp-content/uploads/2026/06/SIFMA-Research-Quarterly-Fixed-Income-O-2Q26.pdf)
- Bills outstanding: about $6.4 trillion at 30 Sep 2025; about $6.69 trillion at 30 Jun 2026; about $7.12 trillion at 30 Sep 2026. Bill share 22.0% at 31 Oct 2025, 22.2% at 31 Jul 2026, 23.0% used in Treasury's latest scenario — [TBAC Q4 2025](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42025.pdf); [TBAC Q3 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ32026.pdf); [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)
- Fed Z.1 (marketable Treasuries held outside the federal government): $30,069.6bn at end-2025, of which bills $6,546.6bn and notes/bonds/TIPS $23,523.1bn; end-2023 total $26,226.6bn — [Fed Z.1 table L.210, 19 Mar 2026](https://www.federalreserve.gov/RELEASES/z1/20260319/html/l210.htm)

**Gross and net issuance, FY2025 and FY2026 ($bn, Treasury sources-and-uses tables)**

| | FY2025 | FY2026 |
|---|---|---|
| Gross bills | 24,768 | 26,782 |
| Net bills | 392 | 721 |
| Gross coupons | 4,384 | 4,395 |
| Net coupons | 1,904 | 1,601 |
| Gross total | not stated (see Inferences) | 31,177 |
| Maturing | not found | 29,118 |
| Net total (fiscal year to date) | 2,297 | 2,059 |
| Buybacks | 185 | not found for full year (60 in Jul-Sep 2026) |

— [TBAC Q4 2025](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42025.pdf); [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)
- July-September 2026 quarter: gross $8,063bn (bills $6,975bn, coupons $1,088bn), maturing $7,320bn, net $742bn; net marketable borrowing $802bn before $60bn of buybacks; cash balance $984bn at end-September (from $919bn) — [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)
- Forward: Treasury expects privately-held net marketable borrowing of $618bn in Oct-Dec 2026 (end-Dec cash $850bn) and $800bn in Jan-Mar 2027 (end-Mar cash $1,000bn). Primary dealer median for FY2027 net borrowing $2,118bn, FY2028 $2,218bn, FY2029 $2,220bn — [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)
- SIFMA counts: Treasury issuance $27.6 trillion year to date through October 2026 (+9.3% y/y); $30.5 trillion gross in calendar 2025 of which $4.8 trillion long-term; 3Q26 gross $8.6 trillion of which long-term $1,214.9bn — [SIFMA Treasury statistics](https://www.sifma.org/research/statistics/us-treasury-securities-statistics); [SIFMA Issuance and Trading 3Q26](https://www.sifma.org/wp-content/uploads/2026/07/SIFMA-Research-Quarterly-Fixed-Income-IT-3Q26.pdf)
- Buybacks: cumulative $515.3bn through October 2026 ($253.4bn liquidity support, $261.9bn cash management); liquidity-support caps for 10-20 year and 20-30 year buckets raised to $6bn per operation in September 2026 — [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)
- Treasury average daily trading volume $1,224.7bn year to date through October 2026 (+15.1% y/y) — [SIFMA Treasury statistics](https://www.sifma.org/research/statistics/us-treasury-securities-statistics)

**Deficit and interest cost ($bn, CBO)**

| | FY2025 | FY2026 | Change |
|---|---|---|---|
| Receipts | 5,235 | 5,403 | +169 (+3.2%) |
| Outlays | 7,010 | 7,396 | +386 (+5.5%) |
| Deficit | 1,775 | 1,992 | +217 (+12%) |
| Deficit, % of GDP | 5.8 | 6.2 | |
| Net interest on the public debt | 1,028 | 1,142 | +114 (+11.1%) |
| Customs duties | 195 | 173 | -22 (-11.1%) |

— [CBO Monthly Budget Review: Summary for FY2026 (PDF)](https://www.cbo.gov/system/files/2026-11/61986-MBR.pdf); [CBO publication page, 9 Nov 2026](https://www.cbo.gov/publication/61986)
- FY2026 revenues were $193bn (3%) below CBO's February 2026 projection; the 50-year average deficit is 3.8% of GDP — [CBO, 9 Nov 2026](https://www.cbo.gov/publication/61986)
- Interest on debt held by the public about $1.1 trillion in FY2026 versus about $392bn in FY2021 — [GAO-27-108795](https://www.gao.gov/assets/gao-27-108795.pdf)
- Deficit projections: primary dealer median $2,056bn (FY2027), $2,220bn (FY2028), $2,200bn (FY2029). The fetched text's OMB/CBO columns had inconsistent year labels, so I do not reproduce them — [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)

**Auctions and demand in 2026**
- 10-year yield 4.89% on 2 Nov 2026 — [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf). 30-year yield 5.49% on 25 Sep 2026 — [24/7 Wall St](https://247wallst.com/investing/2026/09/29/china-holds-618-billion-of-u-s-debt-only-2-countries-hold-more/)
- 10-year note auction, 11 Nov 2026: high yield 5.020% against 5.010% when-issued, a tail of about 1bp (widest since February); 5% coupon, the highest on a 10-year since 2006; bid-to-cover 2.468 (2.771 in October; weakest since May); indirect bidders 61.2% (80.3% in October; lowest since October 2023); direct 29.0% (17.1% prior; highest since September 2013); dealers 9.77% (largest since May). October's 10-year stopped at 5.317% — [CapWolf, 11 Nov 2026](https://capwolf.com/ugly-10y-treasury-auction-shows-weak-foreign-demand/) (market blog relaying auction results; Treasury's own results release not fetched)
- 30-year bond auction, 12 Nov 2026, $25bn: high yield 5.441% against 5.437% when-issued, tail 0.4bp (prior 0.1bp; six-auction average -0.1bp); bid-to-cover 2.36 (prior 2.54; average 2.44); indirect 68.11% (prior 72.32%; average 70.49%); direct 20.50%; dealers 11.39% (prior 6.79%; average 9.49%). Previous 30-year stopped at 5.618% — [Newsquawk, 12 Nov 2026](https://www.newsquawk.com/headlines/us-sells-usd-25bln-of-30-year-bonds-tail-04bps-). A second write-up gives bid-to-cover 2.401, calls the tail the largest since June, and says the 10-year yield rose above 5.10% afterwards — [CapWolf, 13 Nov 2026](https://capwolf.com/?p=139480)
- September 2026 auctions (Treasury's table): 10-year 15 Sep stop 4.834%, bid-to-cover 2.71, indirect 79.2%; 30-year 15 Sep 5.308%, 2.61, 79.5%; 20-year 18 Sep 5.420%, 2.57, 52.5%; 5-year 30 Sep 5.033%, 2.21, 54.3%; 2-year 30 Sep 4.787%, 2.63, 57.8% — [TBAC Q4 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ42026.pdf)
- June 2026 auctions: 10-year 15 Jun stop 4.538%, bid-to-cover 2.57, indirect 78.2%; 30-year 15 Jun 5.020%, 2.33, indirect 60.0%; 2-year 30 Jun 4.189%, 2.64 — [TBAC Q3 2026](https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ32026.pdf)
- Context cited for the November weakness: a hot CPI reading, hawkish policymaker comments, an AI-driven equity rally and heavy investment-grade corporate supply — [CapWolf, 11 Nov 2026](https://capwolf.com/ugly-10y-treasury-auction-shows-weak-foreign-demand/)

### Inferences
- FY2025 gross marketable issuance was about $29.2 trillion (calc.: 24,768 + 4,384), so FY2026 gross of $31.2 trillion was roughly 7% higher. Bills were about 86% of FY2026 gross issuance (calc.: 26,782 / 31,177) but only about 35% of net (calc.: 721 / 2,059), up from about 17% of net in FY2025 (calc.: 392 / 2,297). Net financing shifted towards bills in FY2026.
- Marketable debt roughly doubled between end-2019 ($16.7 trillion) and September 2026 ($31.8 trillion) (calc.: +90%).
- Net interest was about 21% of federal receipts in FY2026 (calc.: 1,142 / 5,403).
- Coupon stop-out yields rose about 50bp at the 10-year and 30-40bp at the 30-year between June and November 2026 auctions (calc. from the stop-out yields above), with a peak in October (10-year 5.317%, 30-year 5.618%).
- The November 10-year result is a shift in who bought (indirects down 19 points, directs up 12 points), not a failed sale: bid-to-cover stayed above 2.4.

### Gaps
- Dollar amounts outstanding by security type (notes, bonds, TIPS, FRN) from the Monthly Statement of the Public Debt for October 2026: not found; only SIFMA shares at 2Q26 and Treasury's bill totals were read.
- A Treasury-sourced 2019 marketable debt figure: not found; the $16.7 trillion end-2019 value is SIFMA's, read from a chart.
- Whether the FYTD "net total" lines (2,297 and 2,059) are before or after buybacks is unclear from the extracted tables. The July-September 2026 quarter shows 802 before buybacks and 742 after, which suggests the totals are after buybacks, but I did not confirm this.
- Full-year FY2026 buybacks, weighted average maturity and the average interest rate on the debt: not found (charts only).
- The official Treasury auction result releases for November 2026 were not fetched; the two sources for the 30-year disagree on bid-to-cover (2.36 versus 2.401).
- The 10-year auction size on 11 Nov 2026: not found.

## 2. Who holds Treasuries: foreign official and private, by country, the Fed, domestic sectors

### Takeaway
Foreign holdings were $9,331.7bn in August 2026, barely above a year earlier, with a clear split: official holders cut $164bn over twelve months (Japan and China leading) while private holders booked through the UK and other financial centres added more. The foreign share of the market has fallen from almost 50% in 2014 to roughly 30%, and China's holdings ($590.7bn) are 55% below their November 2013 peak.

### Cited Findings
**Totals, official versus private (TIC, August 2026, released 16 Oct 2026)**
- Total foreign holdings $9,331.7bn in August 2026 ($9,248.4bn July 2026; $9,249.1bn August 2025; 13-month high $9,487.3bn in February 2026) — [Treasury TIC Table 5](https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html)
- Foreign official holdings $3,755.6bn in August 2026 ($3,919.8bn August 2025; $4,009.6bn February 2026), of which bills $312.2bn ($457.3bn April 2026; $411.6bn August 2025) and notes and bonds $3,443.4bn ($3,508.2bn August 2025) — [Treasury TIC Table 5](https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html)
- Official share of foreign holdings 40.2% in August 2026, down from 42.4% a year earlier; "Central banks are letting bills mature without rolling them" — [PrimeRates, 19 Oct 2026](https://primerates.com/china-cuts-treasury-holdings-590-7-billion-lowest-since-2008/)
- June 2026: official holdings $3.78 trillion, the lowest since February 2024 and down $233bn since February; private holdings a record $5.52 trillion — [Wolf Street, 17 Aug 2026](https://wolfstreet.com/2026/08/17/foreign-central-banks-governments-dumped-treasuries-led-by-china-hong-kong-japan-which-raised-usd-for-yen-invention/)
- December 2025: official 41.9% ($3.9 trillion), private 58.1% ($5.4 trillion) — [CRS RS22331, 22 Apr 2026](https://www.everycrsreport.com/files/2026-04-22_RS22331_b3cd10cbb97d69a8900770fe151a6b46d742593d.pdf)
- TIC flows: July 2026 net portfolio inflow $83.7bn (private $73.5bn, official $10.2bn); 12 months to July 2026 $1,311.1bn (private $1,221.8bn, official $89.3bn) against $1,676.6bn in the 12 months to July 2025; foreign holdings of T-bills rose $49.4bn in the 12 months to July 2026 against $250.5bn the year before — [Treasury TIC press notice, 16 Sep 2026](https://home.treasury.gov/system/files/136/Press-notice-TIC-for-Sep-2026.pdf)
- Fed custody data: marketable Treasuries held in custody for foreign official and international accounts $2,531.4bn (week of 11 Nov 2026), down $217.7bn from a year earlier; foreign official reverse repos $336.4bn — [Fed H.4.1, 12 Nov 2026](https://www.federalreserve.gov/releases/h41/20261112/)

**Largest holders ($bn, TIC Table 5)**

| Holder | Aug 2026 | Jul 2026 | Apr 2026 | Dec 2025 | Aug 2025 |
|---|---|---|---|---|---|
| Japan | 1,068.3 | 1,103.9 | 1,209.9 | 1,185.5 | 1,183.9 |
| United Kingdom | 1,009.5 | 998.3 | 937.5 | 863.2 | 901.3 |
| China, Mainland | 590.7 | 618.0 | 651.1 | 684.4 | 699.7 |
| Belgium | 490.5 | 470.7 | 459.9 | 477.3 | 451.1 |
| Canada | 464.6 | 426.3 | 397.1 | 468.3 | 444.0 |
| Cayman Islands | 463.0 | 460.1 | 471.6 | 421.6 | 410.5 |
| Luxembourg | 448.2 | 442.1 | 430.6 | 434.9 | 410.8 |
| France | 363.4 | 348.4 | 393.3 | 368.9 | 389.1 |
| Ireland | 352.1 | 350.2 | 345.3 | 341.0 | 340.0 |
| Taiwan | 298.4 | 296.1 | 300.9 | 310.6 | 313.4 |
| Switzerland | 285.8 | 284.8 | 288.6 | 294.1 | 303.0 |
| Singapore | 277.9 | 277.7 | 277.5 | 278.4 | 261.0 |
| Hong Kong | 261.5 | 258.3 | 269.1 | 268.4 | 251.9 |
| India | 219.7 | 202.6 | 181.0 | 182.9 | 219.4 |
| Norway | 214.0 | 206.9 | 214.7 | 208.1 | 214.9 |
| Brazil | 168.4 | 168.0 | 168.6 | 168.7 | 184.6 |
| Saudi Arabia | 141.2 | 142.4 | 140.1 | 149.5 | 133.0 |
| Korea, South | 134.2 | 131.5 | 135.2 | 140.6 | 135.8 |
| Grand total | 9,331.7 | 9,248.4 | 9,350.1 | 9,270.5 | 9,249.1 |

— [Treasury TIC Table 5](https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html) (full 13-month table in the CSV)

**China since 2013**
- Peak $1,316.7bn in November 2013; $590.7bn in August 2026, a decline of $726.0bn (55.1%); August 2026 is the first reading below $600bn since August 2008 ($573.7bn); down $109.0bn (15.6%) over 12 months; China's share of foreign holdings 6.33% against 7.56% a year earlier — [PrimeRates, 19 Oct 2026](https://primerates.com/china-cuts-treasury-holdings-590-7-billion-lowest-since-2008/)
- December 2021: China $1,040.3bn (13.44% of foreign holdings, second-largest); December 2025: $683.5bn (7.37%, third-largest). Japan $1,300.8bn (16.81%) in December 2021 against $1,185.5bn (12.79%) in December 2025; UK $649.3bn against $866.0bn — [CRS RS22331](https://www.everycrsreport.com/files/2026-04-22_RS22331_b3cd10cbb97d69a8900770fe151a6b46d742593d.pdf)
- Reasons reported: Beijing wants to "lessen its dependence on the US dollar for reserves, trade settlement, and investment purposes", and has trimmed Treasuries to support the yuan as export inflows slowed — [Reuters via Metrobank, 18 Nov 2025](https://wealthinsights.metrobank.com.ph/reuters/update-1-foreign-demand-for-us-treasuries-slips-in-september-but-japan-steps-up-buying). The decline is described as a "long methodical process"; a 2016 drop was tied to defending the renminbi against capital flight — [Wolf Street, 17 Aug 2026](https://wolfstreet.com/2026/08/17/foreign-central-banks-governments-dumped-treasuries-led-by-china-hong-kong-japan-which-raised-usd-for-yen-invention/)
- Caveat: TIC data come from US custodians and can attribute holdings to the intermediary's country, inflating Belgium, Cayman Islands and Luxembourg; some analysts suggest Belgium holds Chinese custodial accounts — [PrimeRates](https://primerates.com/china-cuts-treasury-holdings-590-7-billion-lowest-since-2008/); [Tiger Brokers, 19 Nov 2025](https://www.itiger.com/news/1186483909)

**Japan in 2026 (lead followed: why the largest holder is shrinking)**
- Japan's holdings fell from $1,239.3bn (February 2026) to $1,068.3bn (August 2026); the November 2021 peak was $1.325 trillion — [Treasury TIC Table 5](https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html); [The Standard, 17 Sep 2026](https://www.thestandard.com.hk/finance/article/343058/Foreign-holdings-of-US-Treasuries-in-July-down-for-2nd-straight-month-data-shows)
- Japan's finance ministry spent a record ¥15.4 trillion ($96.5bn) supporting the yen between 30 July and 26 August 2026; the yen had reached about 164 per dollar; the 30-31 July action was a joint operation with the United States; the previous daily record was ¥6.3 trillion on 30 April 2026. Washington suggested Tokyo could use a 2020 Federal Reserve facility to raise dollars without selling Treasuries; Treasury Secretary Bessent said Washington would do "whatever it takes" to support the effort — [Bloomberg via BNN, 28 Aug 2026](https://www.bnnbloomberg.ca/business/economics/2026/08/28/japan-spent-record-965-billion-to-support-yen-over-past-month-ministry-data-shows/)
- Japan's foreign currency reserves fell a record $94.6bn (8.7%) in August 2026 to $995bn; securities within reserves fell $87.8bn to $840bn; reserves fell $174bn (14.9%) from May to August 2026 — [Wolf Street, 7 Sep 2026](https://wolfstreet.com/2026/09/07/by-dumping-us-treasuries-to-prop-up-the-yen-japans-foreign-currency-reserves-plunged-by-95-billion-in-august-but-dont-cry-for-japan-these-interventions-are-hugely-profitable/)

**Other movers**
- UK up $108.2bn in 12 months to $1,009.5bn; the UK is a booking centre for hedge funds and asset managers, so the figure reflects leveraged private demand more than reserves. India up from $181.0bn (April) to $219.7bn (August 2026) — [PrimeRates](https://primerates.com/china-cuts-treasury-holdings-590-7-billion-lowest-since-2008/)
- A Fed analysis cited by Wolf Street put Cayman-held Treasuries at about $1.8 trillion at end-2024 against $379bn in TIC attribution (basis-trade hedge funds) — [Wolf Street, 17 Aug 2026](https://wolfstreet.com/2026/08/17/foreign-central-banks-governments-dumped-treasuries-led-by-china-hong-kong-japan-which-raised-usd-for-yen-invention/) (reported in the article's comments section; treat as low confidence)
- BIS: foreign banks' claims on the US official sector were $3.8 trillion at end-June 2026; US official-sector claims were 79% of Canadian banks' foreign official-sector claims, 55% of Japanese banks', 34% of UK banks' and 27% of French banks' — [BIS statistical release, 29 Oct 2026](https://www.bis.org/publications/202610-commentary-ibs-gli.pdf)

**Foreign share over time**
- Foreign investors held 32% of marketable Treasuries in Q1 2025, down from almost 50% in 2014 — [Fed, International Role of the U.S. Dollar, 2025 edition](https://www.federalreserve.gov/econres/notes/feds-notes/the-international-role-of-the-u-s-dollar-2025-edition-20250718.html)
- Foreign share of publicly held debt: December 2021 34% ($7.7tn of $22.6tn); December 2022 30% ($7.2tn of $23.8tn); December 2023 30% ($7.9tn of $26.2tn); December 2024 30% ($8.6tn of $28.1tn); December 2025 31% ($9.2tn of $30.1tn). Interest paid to foreigners in 2025: $282.4bn — [CRS RS22331](https://www.everycrsreport.com/files/2026-04-22_RS22331_b3cd10cbb97d69a8900770fe151a6b46d742593d.pdf)

**Federal Reserve**
- Treasury securities held outright $4,586.6bn on 11 Nov 2026, up $393.6bn from 12 Nov 2025: bills $580.7bn (+$385.2bn y/y), nominal notes and bonds $3,620.7bn (+$45.7bn), TIPS $277.7bn (-$32.1bn). MBS $1,883.5bn (-$186.4bn y/y). Total assets $6,758.9bn (+$178.4bn y/y) — [Fed H.4.1, 12 Nov 2026](https://www.federalreserve.gov/releases/h41/20261112/)
- Fed (monetary authority) Treasury holdings at year-end: $4,403.1bn (2023), $3,819.9bn (2024), $3,859.2bn (2025) — [Fed Z.1 L.210](https://www.federalreserve.gov/RELEASES/z1/20260319/html/l210.htm)

**Domestic holders ($bn, Fed Z.1 L.210, year-end 2023 / 2024 / 2025)**
- Money market funds 2,269.5 / 2,994.9 / 3,517.8
- Households (includes hedge funds as a residual) 2,515.4 / 2,626.3 / 2,944.6
- US-chartered banks 1,329.2 / 1,536.8 / 1,744.8
- Mutual funds 1,373.3 / 1,503.7 / 1,675.1
- State and local governments 1,406.9 / 1,475.1 / 1,553.3
- Exchange-traded funds 502.3 / 555.8 / 706.8
- Private pension funds 484.8 / 523.3 / 605.5; state and local pension funds 402.7 / 468.6 / 529.9
- Property-casualty insurers 263.6 / 362.5 / 432.1; life insurers 182.0 / 187.3 / 207.3
- Brokers and dealers 328.7 / 454.2 / 542.5
- Rest of world 7,940.0 / 8,558.4 / 9,224.4
— [Fed Z.1 L.210, 19 Mar 2026](https://www.federalreserve.gov/RELEASES/z1/20260319/html/l210.htm)

### Inferences
- Foreign holdings were about 29% of marketable Treasuries in late summer 2026 (calc.: $9,331.7bn in August over SIFMA's $31.8tn in September; mismatched months and valuation bases, so approximate). Combined with the Fed note and CRS series, the path is roughly 50% (2014), 34% (2021), 30-31% (2022-2025), about 29% (2026).
- Foreign holdings grew 0.9% in the 12 months to August 2026 (calc.: 9,331.7 versus 9,249.1) while Treasuries outstanding grew about 7%, so foreigners absorbed almost none of the year's net supply. Private foreign holdings were about $5,576bn in August 2026 (calc.: total less official), up about $247bn from $5,329bn a year earlier, offsetting the $164bn official decline.
- The official decline is concentrated in bills (down $99bn in 12 months) rather than coupons (down $65bn) (calc. from Table 5).
- The Fed held about 14% of marketable Treasuries in November 2026 (calc.: 4,586.6 / 31,800) and was the largest single incremental buyer over the year, almost entirely in bills (+$385bn), consistent with reserve-management purchases.
- Domestic money market funds added $1.25 trillion of Treasuries between end-2023 and end-2025 (calc.), which matches the bill-heavy issuance in section 1.
- Japan's drop of about $171bn from February to August 2026 (calc.) lines up in timing and scale with yen intervention funding ($96.5bn in the 30 July to 26 August window alone). That is reserve use, not a portfolio judgment about US credit.
- China's reported decline overstates the fall in its true exposure to an unknown degree because of custodial holdings in Belgium and elsewhere; the direction since 2013 is not in doubt.

### Gaps
- TIC data for September 2026 (due mid-November 2026): not found; the Treasury press notice I fetched covered July data, and Table 5 ran to August.
- Year-by-year China holdings for 2014-2020 and 2022-2024: not found in a fetched source; only the selected points listed above.
- Fed Z.1 data for 2026 quarters: not found; the latest release read was 19 March 2026 (data through Q4 2025).
- Official Chinese statements (SAFE, PBoC) on reserve allocation: not found; the reasons cited are analysts' attributions via Reuters and a market blog.
- A long official time series of foreign share of marketable Treasuries (annual, 2010-2026): not found beyond the points above.

## 3. Dollar debt outside the United States (BIS)

### Takeaway
Dollar credit to non-bank borrowers outside the United States stood at $14.7 trillion at end-March 2026, growing 7.3% a year, with about 30% owed by emerging-market borrowers. It is still expanding, but euro-denominated credit is growing nearly twice as fast and has raised its share of foreign-currency credit from 22% to 28% since 2022.

### Cited Findings
- US dollar credit to non-banks outside the United States: $14.7 trillion at end-March 2026, annual growth 7.3%; about 30% owed by EMDE borrowers — [BIS statistical release, end-March 2026 (31 Jul 2026)](https://www.bis.org/statistics/rppb2607.htm); [BIS global liquidity indicators, July 2026](https://www.bis.org/statistics/gli2607.htm)
- Euro credit to non-banks outside the euro area: €5.1 trillion at end-March 2026, annual growth 12%; about 17% owed by EMDE borrowers. Euro share of foreign-currency credit rose from 22% to 28% globally, and from 14% to 18% in EMDEs, between end-Q3 2022 and end-Q1 2026 — [BIS statistical release, end-March 2026](https://www.bis.org/statistics/rppb2607.htm)
- End-June 2026 (released 29 Oct 2026): US dollar-denominated international debt securities grew 6.7% year on year against 13% for euro-denominated; euro-denominated bank loans have outpaced dollar loans since Q3 2024; the euro's share of loans to EMDEs has risen while its share of securities issued by EMDE borrowers has been relatively stable — [BIS commentary, October 2026](https://www.bis.org/publications/202610-commentary-ibs-gli)
- Cross-border bank credit: up $877bn in Q2 2026 to $40.7 trillion outstanding, annual growth 11%; dollar-denominated cross-border credit rose $383bn and euro-denominated $424bn in the quarter, both growing 11% year on year — [BIS statistical release, 29 Oct 2026](https://www.bis.org/publications/202610-commentary-ibs-gli.pdf)
- Cross-border credit to EMDEs rose $105bn in Q2 2026, annual growth 8.9%: emerging Europe 19%, Africa and Middle East 17%, Latin America and Caribbean 9.3%, emerging Asia -2.9% — [BIS statistical release, 29 Oct 2026](https://www.bis.org/publications/202610-commentary-ibs-gli.pdf)

### Inferences
- EMDE dollar credit was roughly $4.4 trillion at end-March 2026 (calc.: 30% of $14.7 trillion; BIS does not state the dollar figure in the text read).
- Dollar credit offshore is growing in line with or slightly above US Treasury debt (about 7% a year), so there is no contraction in offshore dollar borrowing. The shift is relative: euro credit is gaining share from a smaller base.
- Emerging Asia is the one region where cross-border bank credit is shrinking year on year, which is consistent with Chinese borrowers reducing foreign-currency bank debt, though the BIS text read does not attribute it.

### Gaps
- End-June 2026 level of dollar credit to non-banks outside the US, and its split between bank loans and debt securities: not found (the October release text gave growth rates only; the data sit in spreadsheet files I could not open).
- Level of dollar-denominated international debt securities outstanding (all issuers) for any 2026 quarter: not found.
- EMDE dollar credit level and growth rate as stated by BIS, and a multi-year history of the $14.7 trillion series: not found, so no CSV was built for BIS series.
- Yen-denominated credit: not found.

## 4. Other US dollar bond markets: corporates, agency, mortgage-backed

### Takeaway
US corporate bonds outstanding were $12.1 trillion at 2Q26, and 2026 issuance is running at a record pace ($2,342.6bn through October, +19.5%), with investment-grade supply already past the 2020 annual record on AI-related borrowing. SIFMA's outstanding total excluding mortgage and asset-backed securities was $51.4 trillion at 2Q26.

### Cited Findings
- US fixed income outstanding excluding MBS and ABS: $51,400.9bn at 2Q26 (+7.0% y/y); $49,809.7bn at end-2025; $47,033.2bn at end-2024 — [SIFMA Fixed Income Outstanding 2Q26](https://www.sifma.org/wp-content/uploads/2026/06/SIFMA-Research-Quarterly-Fixed-Income-O-2Q26.pdf)
- Corporate bonds outstanding: $12,131.1bn at 2Q26 (+4.2% y/y); $11,778.5bn end-2025; $11,336.4bn end-2024; about $8.9 trillion end-2019 and $7.7 trillion end-2015 (chart readings) — [SIFMA Fixed Income Outstanding 2Q26](https://www.sifma.org/wp-content/uploads/2026/06/SIFMA-Research-Quarterly-Fixed-Income-O-2Q26.pdf)
- Corporate bond issuance: $2,342.6bn year to date through October 2026 (+19.5% y/y); average daily trading $66.9bn (+13.9% y/y) — [SIFMA corporate bond statistics](https://www.sifma.org/resources/research/statistics/us-corporate-bonds-statistics/)
- Corporate issuance $649.6bn in 3Q26 (-13.0% q/q, +13.1% y/y); $2,195.1bn through the first three quarters of 2026; about $2.2 trillion in full-year 2025 and about $2.0 trillion in 2024 (chart readings). 3Q26 shares: investment grade 74.3%, high yield 16.3% — [SIFMA Issuance and Trading 3Q26](https://www.sifma.org/wp-content/uploads/2026/07/SIFMA-Research-Quarterly-Fixed-Income-IT-3Q26.pdf); [SIFMA quarterly page, 22 Oct 2026](https://www.sifma.org/research/statistics/research-quarterly-fixed-income-issuance-and-trading)
- US investment-grade issuance reached $1.76 trillion in 2026 by late October, passing the 2020 annual record of $1.75 trillion; 2025 total $1.59 trillion; nine US offerings of at least $25bn each in 2026; more than $300bn of AI-related funding raised in global high-grade markets in 2026, nearly three times the full-year 2025 amount (Bloomberg data) — [The Star / Bloomberg, 31 Oct 2026](https://www.thestar.com.my/business/business-news/2026/10/31/us-debts-raise-the-roof)
- Federal agency securities outstanding: $2,233.5bn at 2Q26 (+7.8% y/y; +6.7% q/q); $2,026.6bn end-2025. Composition at 2Q26: FHLB 59.6%, Farm Credit 21.5%, Freddie Mac 8.3%, Fannie Mae 8.0% — [SIFMA Fixed Income Outstanding 2Q26](https://www.sifma.org/wp-content/uploads/2026/06/SIFMA-Research-Quarterly-Fixed-Income-O-2Q26.pdf)
- Agency issuance $395.0bn in 3Q26 (+13.2% q/q, +30.1% y/y); about $1.4 trillion in 2025 — [SIFMA quarterly page](https://www.sifma.org/research/statistics/research-quarterly-fixed-income-issuance-and-trading); [SIFMA Issuance and Trading 3Q26](https://www.sifma.org/wp-content/uploads/2026/07/SIFMA-Research-Quarterly-Fixed-Income-IT-3Q26.pdf)
- MBS issuance: $1,752.7bn year to date through October 2026 (+13.9% y/y); $514.0bn in 3Q26; $1.9 trillion in 2025. Agency MBS average daily trading $369.0bn (+4.0% y/y) — [SIFMA MBS statistics, 4 Nov 2026](https://www.sifma.org/research/statistics/us-mortgage-backed-securities-statistics); [SIFMA Issuance and Trading 3Q26](https://www.sifma.org/wp-content/uploads/2026/07/SIFMA-Research-Quarterly-Fixed-Income-IT-3Q26.pdf)
- ABS issuance $517.4bn in 2025 — [SIFMA Issuance and Trading 3Q26](https://www.sifma.org/wp-content/uploads/2026/07/SIFMA-Research-Quarterly-Fixed-Income-IT-3Q26.pdf)
- Municipal bonds outstanding $4,541.1bn and commercial paper $1,413.0bn at 2Q26 — [SIFMA Fixed Income Outstanding 2Q26](https://www.sifma.org/wp-content/uploads/2026/06/SIFMA-Research-Quarterly-Fixed-Income-O-2Q26.pdf)
- Total US fixed income issuance $10,312.5bn year to date through October 2026 (+6.8% y/y); long-term issuance exceeded $3.0 trillion for a third consecutive quarter in 3Q26 — [SIFMA fixed income statistics](https://www.sifma.org/resources/research/statistics/us-fixed-income-securities-statistics/); [SIFMA quarterly page](https://www.sifma.org/research/statistics/research-quarterly-fixed-income-issuance-and-trading)
- The Fed held $1,883.5bn of MBS on 11 Nov 2026, down $186.4bn in a year — [Fed H.4.1](https://www.federalreserve.gov/releases/h41/20261112/)

### Inferences
- 3Q26 investment-grade issuance was about $483bn and high yield about $106bn (calc.: pie-chart shares times $649.6bn; SIFMA does not state the dollar split in the text read).
- Corporate issuance through October 2026 ($2,342.6bn) already exceeds SIFMA's full-year 2025 total (about $2.2 trillion).
- Treasuries have grown from 52% of SIFMA's ex-securitised total at end-2019 to 60% at 2Q26 (calc.: 16.7/32.3 and 31.1/51.4). The dollar bond market has become more government-heavy.

### Gaps
- Outstanding amounts of agency and non-agency MBS and of ABS: not found (SIFMA's outstanding report excludes securitised products; the statistics page gave no figure).
- Investment-grade and high-yield outstanding in dollars, and high-yield issuance for 2025 and 2026 year to date: not found.
- SIFMA-sourced investment-grade issuance for full-year 2025 and 2026 year to date: not found; the $1.59 trillion and $1.76 trillion figures are Bloomberg's and may use a different definition from SIFMA's.

## 5. The dollar's share in global systems

### Takeaway
The dollar was 56.7% of allocated official reserves at end-June 2026, down from 61.3% at end-2019 and above 70% in 2001, but it still accounts for roughly half to 60% of SWIFT payments, about 60% of foreign-currency debt issuance and about 81% of SWIFT trade finance. The slow decline in reserves has not carried over to payments or invoicing.

### Cited Findings
**Reserves (IMF COFER)**
- Dollar share of allocated reserves 56.7% at end-June 2026, down from 57.2% at end-March 2026; the decline "had been driven primarily by an increase in euro holdings"; IMF data released 30 Sep 2026 — [Central Banking, 1 Oct 2026](https://www.centralbanking.com/central-banks/economics/data/7977210/dollars-share-of-foreign-reserves-fell-slightly-in-q2-imf)
- Q2 2026 dollar reserves about $7.49 trillion of $13.22 trillion; Q4 values by year (%): 2013 61.7; 2014 62.7; 2015 64.2; 2016 64.7; 2017 62.7; 2018 62.1; 2019 61.3; 2020 59.5; 2021 59.4; 2022 59.0; 2023 59.0; 2024 58.4; 2025 56.5; 2026 Q1 57.2; 2026 Q2 56.7. Peak 71.4 in 2001 Q2 — [DaveManuel.com compilation of IMF COFER, updated 17 Nov 2026](https://www.davemanuel.com/dollar-share-of-world-reserves.php) (secondary source; full quarterly series in the CSV)
- Dollar share 56.8% of disclosed reserves at end-2025, the lowest in more than two decades; euro roughly one-fifth; total reserves above $13 trillion — [bne IntelliNews, 13 Jul 2026](https://www.intellinews.com/dollar-s-grip-on-global-reserves-slips-to-lowest-level-this-century-454331/); conflicts slightly with 56.5% for 2025 Q4 in [DaveManuel.com](https://www.davemanuel.com/dollar-share-of-world-reserves.php)
- Q2 2025: reported share fell from 57.79% to 56.32%, but 92% of the fall was exchange-rate valuation; at constant rates the share would have been 57.67% (euro 21.13% reported, 19.96% adjusted) — [IMF blog, 1 Oct 2025](https://www.imf.org/en/Blogs/Articles/2025/10/01/dollars-share-of-reserves-held-steady-in-second-quarter-when-adjusted-for-fx-moves). Conflict: the compilation above shows 56.9% for 2025 Q2 and 58.4% for 2025 Q1, which suggests later IMF revisions or a coverage change; the two series should not be mixed.
- Warning on a mislabelled figure: two crypto-news pages present 56.32% as "Q2 2026" data; the numbers are identical to the IMF's Q2 2025 blog and should not be used for 2026 — [TronWeekly](https://www.tronweekly.com/imf-data-shows-dollar-share-at-56-3-as-exchange-rates-skew-reserve-shifts/); [MEXC](https://www.mexc.com/news/452174)
- Fed summary: dollar 58% of disclosed reserves in 2024, down from a 72% peak in 2001 — [Fed, International Role of the U.S. Dollar, 2025 edition](https://www.federalreserve.gov/econres/notes/feds-notes/the-international-role-of-the-u-s-dollar-2025-edition-20250718.html)

**Payments and trade finance (SWIFT)**
- SWIFT global currency tracker, September 2026 edition: dollar 59.87% of global payments by value on one measure and 52.09% on the other; euro 13.25% and 21.37%; sterling 4.83% and 6.37%; yen 4.93% and 3.52%; renminbi 2.38% and 3.26% — [SWIFT Global Currency Tracker, September 2026](https://www.swift.com/sites/default/files/files/global-currency-tracker_september-2026.pdf). The extraction could not reliably tell which block is "all payments" and which is "excluding intra-eurozone payments"; see Gaps.
- Trade finance (letters of credit, by value): dollar 80.68%, renminbi 9.14%, euro 4.79%, yen 1.22% — [SWIFT Global Currency Tracker, September 2026](https://www.swift.com/sites/default/files/files/global-currency-tracker_september-2026.pdf)
- Fed benchmark: about 50% of SWIFT international payments in dollars, about 60% including intra-euro-area payments — [Fed, 2025 edition](https://www.federalreserve.gov/econres/notes/feds-notes/the-international-role-of-the-u-s-dollar-2025-edition-20250718.html)

**Debt issuance, invoicing, banking, FX (Fed, 2025 edition)**
- Foreign-currency debt issuance: about 60% in dollars since 2010, euro 26% — [Fed, 2025 edition](https://www.federalreserve.gov/econres/notes/feds-notes/the-international-role-of-the-u-s-dollar-2025-edition-20250718.html)
- Export invoicing, 1999-2019: dollar 96% in the Americas, 74% in Asia-Pacific, 79% in the rest of the world; Europe 66% euro — same source
- International banking: about 55% of claims and 60% of liabilities in dollars; euro about 20% — same source
- FX turnover: dollar on one side of about 88% of trades (April 2022); euro 31% — same source
- Index of international currency usage since 2010: dollar 65-70, euro about 24, yen about 7, sterling about 6, renminbi about 3 — same source

### Inferences
- Read against the Fed's benchmarks (about 60% of all payments, about 50% excluding intra-euro-area), the SWIFT September 2026 blocks most plausibly correspond to 59.87% for all payments and 52.09% excluding intra-eurozone flows, but the euro's higher share in the second block is the opposite of what excluding intra-eurozone payments should produce, so the labelling needs checking against the original PDF.
- On the COFER compilation, the dollar share fell 4.6 points between end-2019 (61.3%) and mid-2026 (56.7%), about 0.7 points a year, with the 2025 episode showing most quarter-to-quarter movement can be valuation.
- BIS growth rates in section 3 (dollar international debt securities +6.7% versus euro +13%) imply the dollar's roughly 60% share of foreign-currency debt issuance is edging down at the margin in 2025-26; the Fed's 2026 edition figure was not found to confirm.

### Gaps
- The IMF's own COFER release for Q2 2026 (the IMF data portal pages failed to load): renminbi, euro, yen and sterling shares for 2026 quarters: not found. The Q2 2026 dollar figure rests on Central Banking and one secondary compilation, which agree.
- A 2026 edition of the Fed's "International Role of the U.S. Dollar" note: not found; the figures above are from the July 2025 edition and mostly describe 2022-2024.
- Trade invoicing data later than 2019: not found.
- Clean labelling and month for the two SWIFT payment-share series, and a time series of the dollar's SWIFT share: not found.

## 6. Evidence in 2025-2026 of foreign investors reducing or hedging dollar debt exposure

### Takeaway
The evidence shows official reserve managers cutting Treasuries (down $164bn in a year, concentrated in bills, Japan and China) and a burst of currency hedging by pension funds in 2025 that partly reversed in 2026, not a broad private exit. Private foreign holdings are at or near record levels, though foreigners took up almost none of 2026's net Treasury supply and November 2026 auction participation was weak.

### Cited Findings
**Reduction by official holders**
- Foreign official Treasury holdings: $3,755.6bn in August 2026 against $3,919.8bn in August 2025 and $4,009.6bn in February 2026 — [Treasury TIC Table 5](https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html)
- Fed custody holdings for foreign official accounts down $217.7bn year on year to $2,531.4bn (11 Nov 2026) — [Fed H.4.1](https://www.federalreserve.gov/releases/h41/20261112/)
- June 2026: foreign holdings down $72bn in the month, official down $70bn; mainland China plus Hong Kong down $42bn in June and $84bn over 12 months; Japan down $26bn in June and $123bn since February — [Wolf Street, 17 Aug 2026](https://wolfstreet.com/2026/08/17/foreign-central-banks-governments-dumped-treasuries-led-by-china-hong-kong-japan-which-raised-usd-for-yen-invention/)
- July 2026: total foreign holdings $9.248 trillion, down for a second month, up 1.5% year on year; net Treasury outflow of $3.6bn in the month; China at its lowest since September 2008 — [The Standard, 17 Sep 2026](https://www.thestandard.com.hk/finance/article/343058/Foreign-holdings-of-US-Treasuries-in-July-down-for-2nd-straight-month-data-shows)
- August 2026: private buyers in Europe and the Caribbean more than replaced official selling, lifting the total by $83.3bn — [PrimeRates, 19 Oct 2026](https://primerates.com/china-cuts-treasury-holdings-590-7-billion-lowest-since-2008/)

**Hedging**
- Danish institutional investors raised dollar hedge ratios from about 60% (January 2025) to over 70% (December 2025); Australian superannuation funds (about $2.8 trillion in assets) raised hedge ratios in Q2 2025; Finnish pension funds held steady at about 70%. The dollar's "natural hedge" property for foreign investors weakened from 4 March 2025 and was re-established only by late August 2025; the dollar-Treasury correlation rose sharply again in early 2026 during tensions over Greenland. Yen hedging premium (3-month cross-currency basis) was 35bp on 9 April 2025 and 15-20bp in early 2026 — [Banque de France, Eco Notepad No. 444, 13 Apr 2026](https://www.banque-france.fr/en/publications-and-statistics/publications/are-foreign-investors-more-cautious-over-us-dollar)
- Despite that, non-residents' net purchases stayed strong: about $356bn of Treasuries and $253bn of US equities net bought in 2025 through end-July, against a 2015-24 average of $65bn for Treasuries; the authors say portfolio shifts take time and need monitoring — [Banque de France, 13 Apr 2026](https://www.banque-france.fr/en/publications-and-statistics/publications/are-foreign-investors-more-cautious-over-us-dollar)
- By July 2026 pension funds were unwinding hedges: Danish hedge ratios down about 5 points over a year at some funds, Canadian about 1 point, Dutch funds also retreating; the dollar was near a one-year high and US short rates about 140bp above the euro area's. Wells Fargo's Erik Nelson: sell America "wasn't all hype ... there were some genuine flows behind it", "But the hedging impulse has faded"; Corpay's Karl Schamotta: hedges fell "mostly passively, as firms let hedges roll off without replacement" — [Reuters via Kitco, 13 Jul 2026](https://www.kitco.com/news/off-the-wire/2026-07-13/global-pension-funds-pull-back-fx-hedges-dollar-woes-ease)
- IMF on 2025: the dollar index fell more than 10% in the first half of 2025, the largest first-half drop since 1973, yet the exchange-rate-adjusted reserve share was nearly unchanged — [IMF blog, 1 Oct 2025](https://www.imf.org/en/Blogs/Articles/2025/10/01/dollars-share-of-reserves-held-steady-in-second-quarter-when-adjusted-for-fx-moves)

**What official sources say**
- US Treasury: Secretary Bessent dismissed "Sell America" fears in November 2025, citing robust foreign participation in auctions (paraphrased in the source, which misspells his name) — [Tiger Brokers, 19 Nov 2025](https://www.itiger.com/news/1186483909). In August 2026 he said Washington would do "whatever it takes" to support Japan's yen defence, and Washington pointed Tokyo to a Fed facility for raising dollars without selling Treasuries — [Bloomberg via BNN, 28 Aug 2026](https://www.bnnbloomberg.ca/business/economics/2026/08/28/japan-spent-record-965-billion-to-support-yen-over-past-month-ministry-data-shows/)
- BIS (October 2026): foreign-currency credit in dollars is still expanding but euro-denominated credit is growing faster in both loans and securities, and the euro's share has risen since 2022 at both current and constant exchange rates — [BIS commentary, October 2026](https://www.bis.org/publications/202610-commentary-ibs-gli)
- Banque de France (April 2026): flows data do not show a retreat from dollar assets; the change is in hedging behaviour — [Banque de France](https://www.banque-france.fr/en/publications-and-statistics/publications/are-foreign-investors-more-cautious-over-us-dollar)
- Congressional Research Service: foreign share of publicly held debt 31% in December 2025 against 34% in December 2021 — [CRS RS22331](https://www.everycrsreport.com/files/2026-04-22_RS22331_b3cd10cbb97d69a8900770fe151a6b46d742593d.pdf)
- Market view in late 2025: "We see zero evidence of capital fleeing core U.S. assets" (Bank of America's Alex Cohen) — [Tiger Brokers, 19 Nov 2025](https://www.itiger.com/news/1186483909)

**Auction participation**
- 11 Nov 2026 10-year auction: indirect bidders (a category that includes foreign accounts) took 61.2%, the lowest since October 2023, after 80.3% in October — [CapWolf, 11 Nov 2026](https://capwolf.com/ugly-10y-treasury-auction-shows-weak-foreign-demand/)

### Inferences
- Three separate things are happening and should not be merged: (1) a decade-long Chinese reduction, partly obscured by custody; (2) a 2026 Japanese drawdown tied to record yen intervention; (3) a 2025 rise in hedge ratios by European and Australian pension funds that partly reversed by mid-2026 as the dollar recovered. None of the three is evidence of private investors selling dollar bonds outright.
- The stronger evidence of reduced appetite is in shares, not levels: foreign holdings flat while supply grows 7% a year, the foreign share falling from about 34% (2021) to about 29% (2026, calc.), and yields at 5% or more on the 10-year. Domestic buyers (money funds, the Fed in bills, direct bidders) are filling the gap.
- "Indirect bidders" is an imperfect proxy for foreign demand (it also includes domestic funds bidding through dealers), so the headline "weak foreign demand" for the November auction is the blog author's interpretation; Treasury's investor-class allotment data would be the test.
- Joint US-Japan intervention and the suggestion of a Fed facility indicate US officials were actively concerned in mid-2026 about forced Treasury sales by a large reserve holder.

### Gaps
- Fed Financial Stability Report (2026) or Treasury Borrowing Advisory Committee minutes commenting directly on foreign demand in 2026: not found; the TBAC presentation read contains foreign-holdings charts without stated values or commentary.
- Treasury investor-class auction allotment data (foreign share of awards) for 2026: not found.
- Whether Japan actually used a Fed facility in place of Treasury sales, and the quarterly intervention breakdown due in early November 2026: not found.
- Reasons for the sharp rise in 10-year yields to about 5% by October-November 2026 beyond the auction-day commentary (inflation data, Fed stance): not researched here; another researcher's file `us_acm_10y_term_premium_key_dates.csv` in the data folder may cover it.
- Updated hedge-ratio data after July 2026: not found.
