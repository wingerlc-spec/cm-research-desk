#!/usr/bin/env python3
"""CM research desk: datasets (v17, 14 Nov 2026). Runs after terminal_pulls.py with continue-on-error.

A history snapshots (append-only, out/history/):  estimates, iv, earnings reactions (+ one-time backfill of actual moves)
B pattern screens (out/terminal/screens/):         buyback_low_multiple, scare_no_estimate_damage, rotation, insider_clusters
C driver dashboards (out/terminal/drivers.json)
D rule test (out/rule_tests/dislocation_recovery.json)

Reuses screen.py helpers by import. Never fabricates: a failed field is blank, a failed section is noted in the manifest.
  python datasets.py [--out out] [--only A,B,C,D]
"""
import argparse, datetime as dt, gzip, io, json, sys, time, traceback, urllib.request, zlib
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screen  # noqa: E402

# ----------------------------------------------------------------------------- call budget (14 Nov 2026)
YF_SLEEP = 0.25            # seconds between per-ticker Yahoo calls
EST_MAX_NAMES = 260        # A1 estimate pulls per run
IV_MAX_NAMES = 220         # A2 chain snapshots per run
XBRL_MAX_NAMES = 220       # B1 companyconcept refreshes per run (3 calls each), cached in out/cache/
BACKFILL_MAX_CIKS = 300    # A3 one-time backfill: 8-K submissions calls per run until the universe is done
FORM4_MAX_DOCS = 500       # B4 Form 4 documents fetched per run (each parsed once ever, cached)
FORMER_MAX = 700           # D former S&P 500 members pulled for the survivorship line
RUNTIME_BUDGET_S = 18*60   # sections still pending after this are skipped and noted
MIN_MCAP = screen.MIN_MCAP
DROP_PCT, DROP_VOLX = -0.10, 2.5     # B2 and D: one-day drop of 10% or more on 2.5x the prior 20-day volume
SUBIND_MIN = 5
T0 = time.time()

def now_utc(): return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
def over_budget(): return time.time() - T0 > RUNTIME_BUDGET_S
def _f(x, nd=4):
    try:
        v = float(x)
        return round(v, nd) if np.isfinite(v) else None
    except Exception: return None

# ----------------------------------------------------------------------------- snapshot storage
def append_snapshot(folder, df, keys=("date", "ticker")):
    """Append rows to one gzip CSV per month (by the date column), de-duplicated on keys (last write wins). Returns rows written."""
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    if df is None or not len(df): return 0
    df = df.copy(); df["date"] = df["date"].astype(str)
    n = 0
    for month, part in df.groupby(df["date"].str[:7]):
        p = folder/f"{month}.csv.gz"
        old = pd.read_csv(p, dtype={"date": str, "ticker": str}) if p.exists() else None
        allr = pd.concat([old, part], ignore_index=True) if old is not None else part
        allr = allr.drop_duplicates(subset=list(keys), keep="last").sort_values(list(keys))
        with gzip.open(p, "wt", newline="") as fh: allr.to_csv(fh, index=False)
        n += len(part)
    return n

def read_history(folder):
    fs = sorted(Path(folder).glob("*.csv.gz"))
    if not fs: return pd.DataFrame()
    return pd.concat([pd.read_csv(f, dtype={"date": str, "ticker": str}) for f in fs], ignore_index=True)

def history_manifest(root):
    out = {}
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        h = read_history(d)
        if len(h): out[d.name] = dict(rows=int(len(h)), first_date=str(h["date"].min()), last_date=str(h["date"].max()), tickers=int(h["ticker"].nunique()), files=len(list(d.glob("*.csv.gz"))))
    for f in sorted(Path(root).glob("*.csv")):
        h = pd.read_csv(f, dtype=str)
        out[f.name] = dict(rows=int(len(h)), tickers=int(h["ticker"].nunique()) if "ticker" in h else None)
    for f in sorted(Path(root).glob("*.csv.gz")):
        h = pd.read_csv(f, dtype=str)
        out[f.name] = dict(rows=int(len(h)), tickers=int(h["ticker"].nunique()) if "ticker" in h else None)
    return out

# ----------------------------------------------------------------------------- coverage
def rotation_slice(tickers, weekday):
    """One fifth of the names by a stable hash, so every name is captured at least weekly (Mon=0 .. Fri=4; weekends map to 0, 1)."""
    return [t for t in tickers if zlib.crc32(t.encode()) % 5 == weekday % 5]

def coverage(core, big, weekday, cap):
    out = list(dict.fromkeys(list(core) + rotation_slice(sorted(big), weekday)))
    return out[:cap]

# ----------------------------------------------------------------------------- A1 estimates
def est_row(t, info, ee, re_, today):
    g = lambda df, idx, col: _f(df.loc[idx, col]) if df is not None and idx in df.index and col in df.columns else None
    return dict(date=today, ticker=t, eps_cur_fy=g(ee, "0y", "avg"), eps_next_fy=g(ee, "+1y", "avg"),
                rev_cur_fy=g(re_, "0y", "avg"), rev_next_fy=g(re_, "+1y", "avg"),
                n_analysts=_f(info.get("numberOfAnalystOpinions"), 0), target_mean=_f(info.get("targetMeanPrice"), 2),
                target_high=_f(info.get("targetHighPrice"), 2), target_low=_f(info.get("targetLowPrice"), 2),
                rec_mean=_f(info.get("recommendationMean"), 2), fwd_pe=_f(info.get("forwardPE"), 2))

def pull_estimates(names, today):
    import yfinance as yf
    rows, edates, fails = [], {}, 0
    for t in names:
        if over_budget(): break
        info, ee, re_ = {}, None, None
        tk = yf.Ticker(t)
        try: info = tk.info or {}
        except Exception: fails += 1
        try: ee = tk.earnings_estimate
        except Exception: pass
        try: re_ = tk.revenue_estimate
        except Exception: pass
        r = est_row(t, info, ee, re_, today)
        if any(v is not None for k, v in r.items() if k not in ("date", "ticker")): rows.append(r)
        for k in ("earningsTimestampStart", "earningsTimestamp"):
            v = info.get(k)
            if v:
                try: edates[t] = str(pd.Timestamp(int(v), unit="s").date()); break
                except Exception: pass
        time.sleep(YF_SLEEP)
    return pd.DataFrame(rows), edates, fails

# ----------------------------------------------------------------------------- A2 iv
def pick_expiry(exps, today, lo, hi, target):
    t0 = pd.Timestamp(today)
    c = [(abs((pd.Timestamp(e)-t0).days - target), e) for e in exps if lo <= (pd.Timestamp(e)-t0).days <= hi]
    return min(c)[1] if c else None

def iv_snapshot(t, S, today, earn=None, chosen=None):
    import yfinance as yf
    tk = yf.Ticker(t); exps = list(tk.options or []); t0 = pd.Timestamp(today)
    r = dict(date=today, ticker=t, last=round(float(S), 2))
    e30, e9 = pick_expiry(exps, today, 20, 45, 30), pick_expiry(exps, today, 150, 460, 270)
    coi = poi = 0; got = False
    for col, e in (("iv_atm_30d", e30), ("iv_atm_9m", e9)):
        if not e: continue
        try:
            ch = tk.option_chain(e); d = max((pd.Timestamp(e)-t0).days, 1)
            a = screen.atm_iv(ch.calls, ch.puts, S, d) or {}
            r[col] = a.get("atm_iv"); got = True
            coi += int(pd.to_numeric(ch.calls["openInterest"], errors="coerce").fillna(0).sum())
            poi += int(pd.to_numeric(ch.puts["openInterest"], errors="coerce").fillna(0).sum())
        except Exception: pass
        time.sleep(YF_SLEEP)
    if got: r.update(call_oi_total=coi, put_oi_total=poi)
    if earn and t0 <= pd.Timestamp(earn) <= t0 + pd.Timedelta(days=16):
        after = [e for e in exps if pd.Timestamp(e) > pd.Timestamp(earn)]
        if after:
            try:
                ch = tk.option_chain(after[0]); a = screen.atm_iv(ch.calls, ch.puts, S, max((pd.Timestamp(after[0])-t0).days, 1)) or {}
                if a.get("straddle_pct_of_spot") is not None:
                    r.update(earnings_date=earn, implied_move_pct=a["straddle_pct_of_spot"], implied_expiry=after[0])
            except Exception: pass
            time.sleep(YF_SLEEP)
    if chosen and chosen.get("iv") is not None:
        r.update(itm_iv=chosen.get("iv"), itm_spread_pct=chosen.get("spread_pct"))
    return r

IV_COLS = ["date", "ticker", "last", "iv_atm_30d", "iv_atm_9m", "call_oi_total", "put_oi_total", "itm_iv", "itm_spread_pct", "earnings_date", "implied_move_pct", "implied_expiry"]

def iv_rank_table(hist, today, min_obs=60):
    """Percentile of today's iv_atm_30d within the ticker's own history; 'building, N days' below min_obs."""
    out = []
    if not len(hist) or "iv_atm_30d" not in hist: return out
    h = hist.dropna(subset=["iv_atm_30d"])
    for t, g in h.groupby("ticker"):
        g = g.sort_values("date"); n = len(g); cur = g.iloc[-1]
        row = dict(ticker=t, date=cur["date"], iv_atm_30d=_f(cur["iv_atm_30d"]), n_obs=n)
        if n >= min_obs: row["iv_rank"] = round(float((g["iv_atm_30d"] < cur["iv_atm_30d"]).mean()*100), 1)
        else: row["status"] = f"building, {n} days"
        out.append(row)
    return out

# ----------------------------------------------------------------------------- A3 earnings reactions
def reaction(c, v, d):
    """Earnings on date d (timing unknown): the reaction day is whichever of d and the next session traded more volume.
    move = close-to-close on the reaction day; move5 = close before the reaction day to 4 sessions after it (5 sessions)."""
    k0 = int(c.index.searchsorted(pd.Timestamp(d)))
    if k0 < 21 or k0 + 1 >= len(c): return None
    avg = float(v.iloc[k0-20:k0].mean())
    k = k0 if v.iloc[k0] >= v.iloc[k0+1] else k0+1
    out = dict(reaction_date=str(c.index[k].date()), move_pct=round(float(c.iloc[k]/c.iloc[k-1]-1)*100, 2),
               volx=round(float(v.iloc[k]/avg), 2) if avg > 0 else None)
    if k+4 < len(c): out["move5_pct"] = round(float(c.iloc[k+4]/c.iloc[k-1]-1)*100, 2)
    return out

def reactions_json(back, recent, n_last=12):
    allr = pd.concat([x for x in (back, recent) if x is not None and len(x)], ignore_index=True) if any(x is not None and len(x) for x in (back, recent)) else pd.DataFrame()
    out = {}
    if not len(allr): return out
    allr = allr.drop_duplicates(subset=["ticker", "earnings_date"], keep="last")
    for t, g in allr.groupby("ticker"):
        g = g.sort_values("earnings_date").tail(n_last)
        mv = pd.to_numeric(g["move_pct"], errors="coerce").dropna()
        rows = [{k: (None if pd.isna(x) else x) for k, x in r.items() if k in ("earnings_date", "reaction_date", "move_pct", "move5_pct", "implied_move_pct", "source")} for r in g.to_dict("records")]
        out[t] = dict(moves=rows, median_abs_move_pct=round(float(mv.abs().median()), 2) if len(mv) else None, n=int(len(mv)))
        iv = g.dropna(subset=["implied_move_pct"]) if "implied_move_pct" in g else []
        if len(iv): out[t]["implied_vs_actual"] = [dict(earnings_date=r["earnings_date"], implied=r["implied_move_pct"], actual_abs=abs(float(r["move_pct"]))) for r in iv.to_dict("records")]
    return out

# ----------------------------------------------------------------------------- B1 buyback, low multiple
def ttm_from_facts(facts, today, max_age=200):
    """Sum of the last four single quarters (YTD converted), only if contiguous and the latest ends within max_age days."""
    import terminal_pulls as TP
    q = TP.facts_to_quarters(facts)
    if len(q) < 4: return None
    ends = sorted(q)[-4:]
    if (pd.Timestamp(today) - pd.Timestamp(ends[-1])).days > max_age: return None
    for a, b in zip(ends, ends[1:]):
        if not 80 <= (pd.Timestamp(b) - pd.Timestamp(a)).days <= 100: return None
    return dict(value=sum(q[e]["val"] for e in ends), last_end=ends[-1])

def shares_yoy(facts):
    """Instant share counts: per (end, filing) sum the distinct values (class splits without dimensions), latest vs ~1 year earlier."""
    by = {}
    for f in facts:
        if f.get("end") and f.get("val") is not None: by.setdefault((f["end"], f.get("accn")), set()).add(float(f["val"]))
    pts = {}
    for (e, _), vals in sorted(by.items(), key=lambda kv: kv[0][0]): pts[e] = sum(vals)
    if not pts: return None
    e1 = max(pts); t1 = pd.Timestamp(e1)
    prior = [(abs((t1 - pd.Timestamp(e)).days - 365), e) for e in pts if 320 <= (t1 - pd.Timestamp(e)).days <= 410]
    if not prior: return None
    e0 = min(prior)[1]
    return dict(now=pts[e1], year_ago=pts[e0], end=e1, end_year_ago=e0, change_pct=round((pts[e1]/pts[e0]-1)*100, 2)) if pts[e0] else None

def buyback_pass(mcap, ttm_buyback, share_chg_pct, fwd_pe):
    """B1 rule: $5B+, TTM repurchases >= 5% of market cap, shares down >= 4% YoY, forward P/E at or below 12 (positive)."""
    if None in (mcap, ttm_buyback, share_chg_pct, fwd_pe): return False
    return mcap >= MIN_MCAP and ttm_buyback/mcap >= 0.05 and share_chg_pct <= -4 and 0 < fwd_pe <= 12

def xbrl_refresh(names, cikmap, cache, today):
    n = 0
    for t in names:
        if over_budget() or n >= XBRL_MAX_NAMES: break
        cik = cikmap.get(t)
        if not cik: continue
        rep = screen.sec_get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/PaymentsForRepurchaseOfCommonStock.json")
        sh = screen.sec_get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityCommonStockSharesOutstanding.json")
        sy = shares_yoy(((sh or {}).get("units") or {}).get("shares") or []); src = "dei:EntityCommonStockSharesOutstanding"
        if sy is None:
            sh2 = screen.sec_get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/CommonStockSharesOutstanding.json")
            sy = shares_yoy(((sh2 or {}).get("units") or {}).get("shares") or []); src = "us-gaap:CommonStockSharesOutstanding"
        ttm = ttm_from_facts(((rep or {}).get("units") or {}).get("USD") or [], today)
        cache[t] = dict(refreshed=today, ttm_buyback=ttm["value"] if ttm else None, buyback_last_end=ttm["last_end"] if ttm else None,
                        shares=sy, shares_source=src if sy else None)
        n += 1
    return n

# ----------------------------------------------------------------------------- B2 / D drop events
def drop_events(c, v, gap=20):
    """Indices of one-day drops of 10%+ on 2.5x+ the prior 20-day average volume, at least `gap` sessions apart."""
    ret = c.pct_change(); vx = v/v.rolling(20).mean().shift(1)
    idx = np.flatnonzero(((ret <= DROP_PCT) & (vx >= DROP_VOLX)).fillna(False).values)
    return screen.thin([i for i in idx if i >= 21], gap)

def gap_recovery(c, k, horizons=(5, 10, 20, 40, 60)):
    """Share of the gap (close before the drop minus the drop-day close) recovered h sessions later; full close within 60."""
    pre, low = float(c.iloc[k-1]), float(c.iloc[k]); g = pre - low
    if g <= 0: return None
    out = {f"rec{h}": (float(c.iloc[k+h]) - low)/g for h in horizons if k+h < len(c)}
    if k+60 < len(c):
        path = c.iloc[k+1:k+61].values
        hit = np.flatnonzero(path >= pre); out["closed60"] = bool(len(hit)); out["days_to_close"] = int(hit[0]+1) if len(hit) else None
        two = np.flatnonzero(path >= low + 2*g/3); out["two_thirds_day"] = int(two[0]+1) if len(two) else None
    return out

# ----------------------------------------------------------------------------- B3 rotation
def rotation_table(closes, groups, spy, lag=21):
    """closes: DataFrame (dates x tickers). groups: {name: [tickers]}. Returns one row per group with 1m/2m return vs SPY,
    percent above the 50-day now and `lag` sessions ago, and rank change (rank by 1m relative return, now vs lag ago)."""
    s50 = closes.rolling(50).mean()
    def rel(n, at):
        r = closes.iloc[at]/closes.iloc[at-n]-1; rs = spy.iloc[at]/spy.iloc[at-n]-1
        return r - rs
    now1, now2, past1 = rel(21, -1), rel(42, -1), rel(21, -1-lag)
    above_now = (closes.iloc[-1] > s50.iloc[-1]); above_past = (closes.iloc[-1-lag] > s50.iloc[-1-lag])
    rows = []
    for g, mem in groups.items():
        m = [t for t in mem if t in closes.columns and pd.notna(closes[t].iloc[-1]) and pd.notna(closes[t].iloc[-1-lag-42])]
        if not m: continue
        rows.append(dict(group=g, members=len(m), rel_1m_pct=round(float(now1[m].mean()*100), 2), rel_2m_pct=round(float(now2[m].mean()*100), 2),
                         rel_1m_month_ago_pct=round(float(past1[m].mean()*100), 2),
                         pct_above_50d=round(float(above_now[m].mean()*100), 1), pct_above_50d_month_ago=round(float(above_past[m].mean()*100), 1)))
    df = pd.DataFrame(rows)
    if not len(df): return df
    df["rank_now"] = df.rel_1m_pct.rank(ascending=False, method="min").astype(int)
    df["rank_month_ago"] = df.rel_1m_month_ago_pct.rank(ascending=False, method="min").astype(int)
    df["rank_change"] = df.rank_month_ago - df.rank_now
    df["breadth_change"] = df.pct_above_50d - df.pct_above_50d_month_ago
    return df.sort_values(["rank_change", "breadth_change"], ascending=False).reset_index(drop=True)

def not_extended(last, s50, band=0.08):
    return s50 is not None and s50 > 0 and abs(last/s50 - 1) <= band

# ----------------------------------------------------------------------------- B4 insider clusters
def parse_form4(xml_text):
    """Open-market purchases (code P) from one Form 4 XML: [(owner, owner_cik, date, shares, price)]."""
    root = ET.fromstring(xml_text)
    owner = (root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or "").strip()
    ocik = (root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerCik") or "").strip()
    out = []
    for tr in root.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        if (tr.findtext("transactionCoding/transactionCode") or "").strip() != "P": continue
        if (tr.findtext("transactionAmounts/transactionAcquiredDisposedCode/value") or "A").strip() != "A": continue
        try:
            sh = float(tr.findtext("transactionAmounts/transactionShares/value")); px = float(tr.findtext("transactionAmounts/transactionPricePerShare/value") or "nan")
        except (TypeError, ValueError): continue
        out.append((owner, ocik, (tr.findtext("transactionDate/value") or "")[:10], sh, px))
    return out

def clusters(buys, today, window=30, min_insiders=3, min_usd=500_000):
    """buys: DataFrame ticker, owner_cik, owner, date, shares, price. Trailing `window` days from today."""
    if not len(buys): return []
    b = buys.copy(); b["date"] = pd.to_datetime(b["date"], errors="coerce"); b = b.dropna(subset=["date", "price"])
    b = b[(b["date"] > pd.Timestamp(today) - pd.Timedelta(days=window)) & (b["date"] <= pd.Timestamp(today))]
    b["usd"] = b["shares"]*b["price"]; out = []
    for t, g in b.groupby("ticker"):
        ins = g["owner_cik"].nunique(); tot = float(g["usd"].sum())
        if ins >= min_insiders and tot >= min_usd:
            out.append(dict(ticker=t, insiders=sorted(g["owner"].unique().tolist()), n_insiders=int(ins), total_usd=round(tot, 0),
                            first_date=str(g["date"].min().date()), last_date=str(g["date"].max().date()),
                            avg_price=round(tot/float(g["shares"].sum()), 2)))
    return sorted(out, key=lambda r: -r["total_usd"])

def sec_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": screen.SEC_UA, "Accept-Encoding": "identity"})
    for k in range(3):
        try:
            time.sleep(0.13); return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2*(k+1))
        except Exception: time.sleep(2*(k+1))
    return None

# ----------------------------------------------------------------------------- C drivers
def driver_fit(y, m, p, fit_n, hold=20):
    """y, m, p: aligned daily changes. Fit y = a + bm*m + bp*p on the fit_n sessions before the last `hold`, then z-score the
    summed out-of-sample residual over the last `hold` sessions. Returns beta (bp), r2, z."""
    n = len(y)
    if n < fit_n + hold: return None
    Y, M, P = y[-(fit_n+hold):-hold], m[-(fit_n+hold):-hold], p[-(fit_n+hold):-hold]
    X = np.column_stack([np.ones(len(Y)), M, P]); coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    res = Y - X @ coef; sd = float(res.std(ddof=3))
    r2 = 1 - float(res @ res)/float(((Y - Y.mean())**2).sum()) if Y.std() > 0 else None
    Xo = np.column_stack([np.ones(hold), m[-hold:], p[-hold:]]); ro = y[-hold:] - Xo @ coef
    z = float(ro.sum()/(sd*np.sqrt(hold))) if sd > 0 else None
    return dict(beta=round(float(coef[2]), 3), r2=round(r2, 3) if r2 is not None else None, z20=round(z, 2) if z is not None else None,
                resid_20d_pct=round(float(ro.sum())*100, 2))

def fred_series(sid):
    raw = urllib.request.urlopen(urllib.request.Request(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers={"User-Agent": "cm-research-desk/1.0"}), timeout=60).read().decode()
    d = pd.read_csv(io.StringIO(raw)); d.columns = ["date", "v"]
    d["v"] = pd.to_numeric(d["v"], errors="coerce"); d["date"] = pd.to_datetime(d["date"])
    return d.dropna().set_index("date")["v"]

# ----------------------------------------------------------------------------- D cluster-robust difference
def clustered_diff(y, flag, cluster):
    """OLS y = a + b*flag with standard errors clustered by `cluster`. Returns (b, t)."""
    y = np.asarray(y, float); x = np.asarray(flag, float); g = np.asarray(cluster)
    X = np.column_stack([np.ones(len(y)), x]); XtX_inv = np.linalg.inv(X.T @ X); b = XtX_inv @ X.T @ y; u = y - X @ b
    meat = np.zeros((2, 2))
    for c in np.unique(g):
        s = X[g == c].T @ u[g == c]; meat += np.outer(s, s)
    G = len(np.unique(g)); adj = G/(G-1) if G > 1 else 1.0
    V = adj * XtX_inv @ meat @ XtX_inv
    se = float(np.sqrt(V[1, 1])) if V[1, 1] > 0 else None
    return float(b[1]), (float(b[1]/se) if se else None)

def verdict(effect, t):
    """screen.py's convention: WORKS / NOT SHOWN / HURTS at |t| >= 2."""
    if t is None: return "NOT SHOWN"
    return "WORKS" if effect > 0 and t >= 2 else "HURTS" if effect < 0 and t <= -2 else "NOT SHOWN"

# ----------------------------------------------------------------------------- run
def jdump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, indent=1, default=str))

def screen_file(p, rule, asof, caveats, rows, extra=None):
    meta = dict(rule=rule, asof=asof, generated_utc=now_utc(), caveats=caveats)
    if extra: meta.update(extra)
    jdump(p, dict(meta=meta, rows=rows))

class Ctx: pass

def load_ctx(out):
    """Universe, bars, market caps, and the screen's outputs."""
    x = Ctx(); x.out = out; x.today = dt.date.today().isoformat()
    x.meta = screen.load_universe()
    extra = ["JETS", "KRE", "KBE", "GDX", "UNG", "SHY", "TLT", "BNO", "CPER", "GLD", "LUV", "DAL", "UAL", "AAL", "FCX", "SCCO", "NEM", "EQT", "CTRA",
             "LQD", "IEF", "HYG", "SMH", "^VIX", "^VIX3M"]
    import terminal_pulls as TP
    x.bars = screen.pull_yf(sorted(set(x.meta) | set(screen.BENCH) | set(extra) | set(TP.read_watch(Path(__file__).resolve().parent/"terminal_watch.txt"))))
    spy = x.bars["SPY"]["close"]; x.asof = str(spy.index[-1].date())
    try: x.mcap = {t: v["usd"] for t, v in json.loads((out/"mcap_cache.json").read_text())["values"].items()}
    except Exception: x.mcap = {}
    try: x.so = json.loads((out/"screen_output.json").read_text())
    except Exception: x.so = {}
    try: x.lc = json.loads((out/"lens_candidates.json").read_text())
    except Exception: x.lc = {}
    try: x.opts = json.loads((out/"options.json").read_text()).get("names", {})
    except Exception: x.opts = {}
    try: x.chains = {r["sym"]: r for r in json.loads((out/"terminal"/"chains.json").read_text())["rows"]}
    except Exception: x.chains = {}
    try: x.edates_file = {r["sym"]: r.get("next_earnings") for r in json.loads((out/"terminal"/"earnings_dates.json").read_text())["rows"]}
    except Exception: x.edates_file = {}
    import terminal_pulls as TP
    x.watch = TP.read_watch(Path(__file__).resolve().parent/"terminal_watch.txt")
    ranked = [r["ticker"] for r in x.so.get("ranked", [])]; cands = [c["ticker"] for c in (x.lc.get("candidates") or [])]
    x.core = list(dict.fromkeys(ranked + cands + x.watch))
    x.big = [t for t in x.meta if x.mcap.get(t, 0) >= MIN_MCAP and t in x.bars]
    x.cov = coverage([t for t in x.core if t in x.bars], x.big, dt.date.today().weekday(), max(EST_MAX_NAMES, IV_MAX_NAMES))
    x.cik = None
    return x

def ciks(x):
    if x.cik is None: x.cik = screen.ticker_cik()
    return x.cik

def section_A(x, status):
    H = x.out/"history"
    # A1
    est, edates, fails = pull_estimates(x.cov[:EST_MAX_NAMES], x.today)
    n1 = append_snapshot(H/"estimates", est)
    status["history/estimates"] = dict(rows_written=n1, names=len(x.cov[:EST_MAX_NAMES]), info_failures=fails)
    # earnings dates seen (feeds A2 implied moves and A3)
    seen = [dict(date=x.today, ticker=t, earnings_date=d, source="yahoo info") for t, d in edates.items()]
    seen += [dict(date=x.today, ticker=t, earnings_date=d, source="earnings_dates.json") for t, d in x.edates_file.items() if d]
    seen += [dict(date=x.today, ticker=r["ticker"], earnings_date=r["next_earnings"][:10], source="screen ranked") for r in x.so.get("ranked", []) if r.get("next_earnings")]
    sp = H/"earnings_dates_seen.csv"; H.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(sp, dtype=str) if sp.exists() else pd.DataFrame(columns=["date", "ticker", "earnings_date", "source"])
    allseen = pd.concat([old, pd.DataFrame(seen)], ignore_index=True).drop_duplicates(subset=["ticker", "earnings_date"], keep="first")
    allseen.to_csv(sp, index=False)
    nxt = {}
    for r in allseen.itertuples():
        if r.earnings_date >= x.today and (r.ticker not in nxt or r.earnings_date < nxt[r.ticker]): nxt[r.ticker] = r.earnings_date
    # A2
    rows = []
    for t in x.cov[:IV_MAX_NAMES]:
        if over_budget(): break
        S = float(x.bars[t]["close"].iloc[-1]) if t in x.bars else None
        if not S: continue
        chosen = (x.opts.get(t) or x.chains.get(t) or {}).get("option")
        try: rows.append(iv_snapshot(t, S, x.today, nxt.get(t), chosen))
        except Exception: pass
    ivdf = pd.DataFrame(rows).reindex(columns=IV_COLS) if rows else pd.DataFrame(columns=IV_COLS)
    ivdf = ivdf[ivdf[["iv_atm_30d", "iv_atm_9m"]].notna().any(axis=1)] if len(ivdf) else ivdf
    n2 = append_snapshot(H/"iv", ivdf)
    status["history/iv"] = dict(rows_written=n2, names=len(rows))
    ivr = iv_rank_table(read_history(H/"iv"), x.today)
    jdump(x.out/"terminal"/"iv_rank.json", dict(meta=dict(source="out/history/iv", pulled_utc=now_utc(), notes=["iv_rank = percentile of today's 30-day at-the-money iv in the ticker's own snapshots; needs 60 observations"]), rows=ivr))
    status["terminal/iv_rank.json"] = dict(rows=len(ivr), ranked=sum(1 for r in ivr if "iv_rank" in r))
    # A3 nightly: covered names whose earnings date fell in the last 3 sessions (5-session move filled in for 10 sessions)
    spy = x.bars["SPY"]["close"]; cal = spy.index
    recent_cut = cal[-3] if len(cal) >= 3 else cal[0]; fill_cut = cal[-10]
    ivh = read_history(H/"iv")
    rp = H/"earnings_reactions.csv"
    rec = pd.read_csv(rp, dtype={"ticker": str, "earnings_date": str}) if rp.exists() else pd.DataFrame()
    new = []
    covered = set(x.cov) | set(x.core)
    for r in allseen.itertuples():
        d = pd.Timestamp(r.earnings_date)
        if r.ticker not in covered or r.ticker not in x.bars or d > cal[-1] or d < fill_cut: continue
        prior = rec[(rec.ticker == r.ticker) & (rec.earnings_date == r.earnings_date)] if len(rec) else []
        if d < recent_cut and (not len(prior) or pd.notna(prior.iloc[0].get("move5_pct"))): continue
        x_ = x.bars[r.ticker]; rr = reaction(x_["close"], x_["volume"], d)
        if not rr: continue
        row = dict(ticker=r.ticker, earnings_date=r.earnings_date, source="nightly", **rr)
        if len(ivh) and "implied_move_pct" in ivh:
            pre = ivh[(ivh.ticker == r.ticker) & (ivh.earnings_date == r.earnings_date) & (ivh.date < r.earnings_date)].dropna(subset=["implied_move_pct"])
            if len(pre): row["implied_move_pct"] = float(pre.sort_values("date").iloc[-1]["implied_move_pct"])
        new.append(row)
    rec = pd.concat([rec, pd.DataFrame(new)], ignore_index=True).drop_duplicates(subset=["ticker", "earnings_date"], keep="last") if new else rec
    if len(rec): rec.to_csv(rp, index=False)
    status["history/earnings_reactions.csv"] = dict(rows_written=len(new), total=int(len(rec)))
    # A3 backfill: actual moves only, from 8-K Item 2.02 dates, in chunks until the universe is done
    bp = H/"earnings_reactions_backfill.csv.gz"; state_p = x.out/"cache"/"backfill_state.json"
    try: state = json.loads(state_p.read_text())
    except Exception: state = {"done": []}
    back = pd.read_csv(bp, dtype={"ticker": str, "earnings_date": str}) if bp.exists() else pd.DataFrame()
    todo = [t for t in sorted(x.big) if t not in set(state["done"])]
    added = 0
    if todo and not over_budget():
        cm = ciks(x); chunk = [t for t in todo if t in cm][:BACKFILL_MAX_CIKS]
        ed = screen.earnings_dates(sorted({cm[t] for t in chunk}), int(x.today[:4]) - 4)
        inv = {}
        for t in chunk: inv.setdefault(cm[t], []).append(t)
        rows = []
        for cik, dts in ed.items():
            for t in inv.get(cik, []):
                b = x.bars.get(t)
                if b is None: continue
                for d in dts[-16:]:
                    rr = reaction(b["close"], b["volume"], d)
                    if rr: rows.append(dict(ticker=t, earnings_date=str(d.date()), source="8-K Item 2.02 backfill", **rr))
        if rows:
            back = pd.concat([back, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(subset=["ticker", "earnings_date"], keep="last")
            with gzip.open(bp, "wt", newline="") as fh: back.to_csv(fh, index=False)
            added = len(rows)
        state["done"] = sorted(set(state["done"]) | set(chunk) | {t for t in todo if t not in cm}); jdump(state_p, state)
    status["history/earnings_reactions_backfill"] = dict(rows_added=added, names_done=len(state["done"]), names_left=len([t for t in x.big if t not in set(state["done"])]))
    rj = reactions_json(back, rec)
    jdump(x.out/"terminal"/"earnings_reactions.json", dict(meta=dict(source="SEC 8-K Item 2.02 dates (backfill) and Yahoo earnings dates (nightly); prices from Yahoo", pulled_utc=now_utc(),
          notes=["Reaction day = whichever of the earnings date and the next session traded more volume (timing is not known). move_pct is close-to-close on that day; move5_pct runs from the close before it through 4 sessions after.",
                 "implied_move_pct = at-the-money straddle mid of the first expiry after the print / price, from the last iv snapshot before it; backfilled rows have no implied move."]),
          rows=[dict(ticker=t, **v) for t, v in sorted(rj.items())]))
    status["terminal/earnings_reactions.json"] = dict(rows=len(rj))

def section_B(x, status):
    S_ = x.out/"terminal"/"screens"; spy = x.bars["SPY"]["close"]
    feats = {}
    for t in x.meta:
        b = x.bars.get(t)
        if b is None or len(b) < 260: continue
        c = b["close"]; feats[t] = dict(last=float(c.iloc[-1]), hi52=float(c.tail(252).max()), s50=float(c.tail(50).mean()))
    est = read_history(x.out/"history"/"estimates")
    fpe = {}
    if len(est):
        for t, g in est.sort_values("date").groupby("ticker"):
            v = g["fwd_pe"].dropna()
            if len(v): fpe[t] = float(v.iloc[-1])
    nxt = {}
    try:
        seen = pd.read_csv(x.out/"history"/"earnings_dates_seen.csv", dtype=str)
        for r in seen.itertuples():
            if r.earnings_date >= x.today and (r.ticker not in nxt or r.earnings_date < nxt[r.ticker]): nxt[r.ticker] = r.earnings_date
    except Exception: pass
    # B1
    cp = x.out/"cache"/"buyback_xbrl.json"
    try: cache = json.loads(cp.read_text())
    except Exception: cache = {}
    order = [t for t in x.core if t in x.big] + [t for t in rotation_slice(sorted(x.big), dt.date.today().weekday())] + [t for t in sorted(x.big) if t not in cache]
    stale = lambda t: t not in cache or (pd.Timestamp(x.today) - pd.Timestamp(cache[t]["refreshed"])).days >= 5
    order = [t for t in dict.fromkeys(order) if stale(t)]
    n = xbrl_refresh(order, ciks(x), cache, x.today) if not over_budget() else 0
    jdump(cp, cache)
    import yfinance as yf
    rows = []
    for t, v in cache.items():
        mc = x.mcap.get(t)
        if not (v.get("ttm_buyback") and v.get("shares") and mc and mc >= MIN_MCAP): continue
        if not (v["ttm_buyback"]/mc >= 0.05 and v["shares"]["change_pct"] <= -4): continue
        pe = fpe.get(t)
        if pe is None:
            try: pe = _f(yf.Ticker(t).info.get("forwardPE"), 2); time.sleep(YF_SLEEP)
            except Exception: pe = None
        if not buyback_pass(mc, v["ttm_buyback"], v["shares"]["change_pct"], pe): continue
        f = feats.get(t, {}); m = x.meta.get(t, {})
        rows.append(dict(ticker=t, name=m.get("name"), sector=m.get("sector"), mcap_busd=round(mc/1e9, 2), buyback_yield_pct=round(v["ttm_buyback"]/mc*100, 2),
                         share_change_yoy_pct=v["shares"]["change_pct"], fwd_pe=pe, last=round(f["last"], 2) if f else None,
                         pct_from_52w_high=round((f["last"]/f["hi52"]-1)*100, 1) if f else None, next_earnings=nxt.get(t)))
    rows.sort(key=lambda r: -r["buyback_yield_pct"])
    screen_file(S_/"buyback_low_multiple.json", "Market cap $5B or more; cash spent on repurchases over the last four quarters (XBRL PaymentsForRepurchaseOfCommonStock) at least 5 percent of market cap; shares outstanding (XBRL dei cover page, else us-gaap) down 4 percent or more year over year; forward P/E between 0 and 12.",
                x.asof, ["SEC data is refreshed for about a fifth of the universe per night plus the ranked names, so a name can lag its latest filing by up to a week.",
                         "Repurchase cash includes shares withheld for taxes at some companies.", f"{len(cache)} of {len(x.big)} $5B+ names have SEC data cached so far."],
                rows, dict(xbrl_refreshed_this_run=n))
    status["terminal/screens/buyback_low_multiple.json"] = dict(rows=len(rows), cached=len(cache), refreshed=n)
    # B2
    rows = []
    hist_ok = len(est) and est["date"].nunique() >= 2
    for t in x.big:
        b = x.bars.get(t)
        if b is None or len(b) < 60: continue
        c, v = b["close"], b["volume"]
        ev = [k for k in drop_events(c.tail(60), v.tail(60), gap=1) if k >= len(c.tail(60)) - 15]
        if not ev: continue
        k = ev[-1]; cc = c.tail(60); vv = v.tail(60)
        ddate = str(cc.index[k].date()); pre = float(cc.iloc[k-1]); drop = float(cc.iloc[k]/pre-1)*100; vx = float(vv.iloc[k]/vv.iloc[k-20:k].mean())
        chg, basis = None, None
        if hist_ok:
            g = est[(est.ticker == t)].sort_values("date")
            before = g[g.date < ddate].dropna(subset=["eps_next_fy"]); after = g.dropna(subset=["eps_next_fy"])
            if len(before) and len(after) and before.iloc[-1]["eps_next_fy"]:
                chg = round((after.iloc[-1]["eps_next_fy"]/before.iloc[-1]["eps_next_fy"]-1)*100, 2); basis = "estimate snapshots"
        if chg is None:
            try:
                tr = yf.Ticker(t).eps_trend; row = tr.loc["+1y"]; days = (pd.Timestamp(x.asof) - pd.Timestamp(ddate)).days
                col = "7daysAgo" if days <= 7 else "30daysAgo"
                chg = round((float(row["current"])/float(row[col])-1)*100, 2); basis = f"Yahoo trend vs {col}; estimate history building"
            except Exception: pass
            time.sleep(YF_SLEEP)
        if chg is None or chg <= -2: continue
        last = float(c.iloc[-1])
        rows.append(dict(ticker=t, name=x.meta.get(t, {}).get("name"), drop_date=ddate, drop_pct=round(drop, 1), volume_multiple=round(vx, 1),
                         est_change_pct=chg, est_basis=basis, last=round(last, 2), pre_drop_close=round(pre, 2),
                         gap_left_pct=round((pre/last-1)*100, 1), next_earnings=nxt.get(t)))
    rows.sort(key=lambda r: r["drop_pct"])
    screen_file(S_/"scare_no_estimate_damage.json", "One-day drop of 10 percent or more on at least 2.5 times the prior 20-day volume in the last 15 sessions, $5B+ names, where next-year EPS estimates have fallen less than 2 percent since the day before the drop.",
                x.asof, ["Until estimate snapshots cover the drop date, the estimate change uses Yahoo's 7 or 30 day trend fields and is flagged 'estimate history building'.",
                         "gap_left_pct = how far the pre-drop close is above today's price."], rows)
    status["terminal/screens/scare_no_estimate_damage.json"] = dict(rows=len(rows))
    # B3
    sub = {}
    for t, m in x.meta.items():
        if t in x.bars and m.get("industry"): sub.setdefault(m["industry"], []).append(t)
    groups = {k: v for k, v in sub.items() if len(v) >= SUBIND_MIN}
    for sec, etf in screen.SECTOR_ETF.items():
        if etf in x.bars: groups[f"{etf} ({sec} ETF)"] = [etf]
    tick = sorted({t for v in groups.values() for t in v})
    closes = pd.DataFrame({t: x.bars[t]["close"] for t in tick}).reindex(spy.index).ffill(limit=3).tail(260)
    rt = rotation_table(closes, groups, spy.reindex(closes.index))
    top = []
    for r in rt.head(10).to_dict("records"):
        mem = []
        for t in groups[r["group"]]:
            f = feats.get(t)
            if f and x.mcap.get(t, 0) >= MIN_MCAP and not_extended(f["last"], f["s50"]):
                mem.append(dict(ticker=t, name=x.meta.get(t, {}).get("name"), mcap_busd=round(x.mcap[t]/1e9, 2), vs_50d_pct=round((f["last"]/f["s50"]-1)*100, 1)))
        top.append(dict(r, candidates=mem))
    screen_file(S_/"rotation.json", "Groups = GICS sub-industries with 5 or more names in the universe, plus the sector ETFs. Equal-weight 1 and 2 month return vs SPY, percent of members above their 50-day now and a month ago, rank change of the 1-month relative return (month ago rank minus rank now). Top 10 most improving groups; inside each, $5B+ members within 8 percent of their 50-day.",
                x.asof, ["Descriptive only: screen.py's own tests found chart patterns alone showed no reliable edge, so this is a place to look, not a signal."], top,
                dict(groups_ranked=int(len(rt))))
    status["terminal/screens/rotation.json"] = dict(rows=len(top), groups=int(len(rt)))
    # B4 (scope: ranked names, lens candidates and watch list; Form 4s cached so each is fetched once)
    f4p = x.out/"cache"/"form4.json"
    try: f4 = json.loads(f4p.read_text())
    except Exception: f4 = {"parsed": {}}
    cm = ciks(x); docs = 0; cut = (pd.Timestamp(x.today) - pd.Timedelta(days=30)).strftime("%Y-%m-%d"); buys = []
    scope = [t for t in x.core if t in cm]
    for t in scope:
        if over_budget() or docs >= FORM4_MAX_DOCS: break
        d = screen.sec_get(f"https://data.sec.gov/submissions/CIK{cm[t]:010d}.json")
        rec = ((d or {}).get("filings") or {}).get("recent") or {}
        for form, acc, fdate, doc in zip(rec.get("form", []), rec.get("accessionNumber", []), rec.get("filingDate", []), rec.get("primaryDocument", [])):
            if form != "4" or fdate < cut: continue
            if acc not in f4["parsed"]:
                if docs >= FORM4_MAX_DOCS: break
                url = f"https://www.sec.gov/Archives/edgar/data/{cm[t]}/{acc.replace('-', '')}/{doc.split('/')[-1]}"
                txt = sec_text(url); docs += 1
                try: f4["parsed"][acc] = dict(ticker=t, filed=fdate, buys=parse_form4(txt) if txt else [], ok=bool(txt))
                except ET.ParseError: f4["parsed"][acc] = dict(ticker=t, filed=fdate, buys=[], ok=False)
            for o, oc, dd, sh, px in f4["parsed"][acc]["buys"]:
                buys.append(dict(ticker=t, owner=o, owner_cik=oc, date=dd, shares=sh, price=px))
    old_cut = (pd.Timestamp(x.today) - pd.Timedelta(days=120)).strftime("%Y-%m-%d")
    f4["parsed"] = {k: v for k, v in f4["parsed"].items() if v["filed"] >= old_cut}; jdump(f4p, f4)
    cl = clusters(pd.DataFrame(buys), x.today)
    for r in cl:
        b = x.bars.get(r["ticker"])
        if b is not None: r["last"] = round(float(b["close"].iloc[-1]), 2); r["avg_price_vs_last_pct"] = round((r["avg_price"]/r["last"]-1)*100, 1)
    screen_file(S_/"insider_clusters.json", "Open-market purchases (Form 4, transaction code P) by 3 or more distinct insiders in the last 30 days totalling $500,000 or more.",
                x.asof, ["Scope: the ranked names, lens candidates and terminal_watch.txt only, not the whole universe, to stay inside the SEC call budget.",
                         "Route: the SEC submissions API per company (one call each) plus each new Form 4 XML once; parsed filings are cached in out/cache/form4.json."],
                cl, dict(names_scanned=len(scope), form4_fetched_this_run=docs))
    status["terminal/screens/insider_clusters.json"] = dict(rows=len(cl), names=len(scope), docs_fetched=docs)

DRIVERS = [("OIL", "BNO", "Brent via BNO (no clean jet fuel series on Yahoo)", ["DAL", "UAL", "AAL", "LUV", "JETS"]),
           ("CURVE_10S2S", "T10Y2Y", "10-year minus 2-year Treasury yield (FRED T10Y2Y), daily change in percentage points", ["KRE", "KBE"]),
           ("COPPER", "CPER", "copper via CPER", ["FCX", "SCCO"]),
           ("GOLD", "GLD", "gold via GLD", ["NEM", "GDX"]),
           ("NATGAS", "UNG", "natural gas via UNG", ["EQT", "CTRA"])]

def section_C(x, status):
    spy = x.bars["SPY"]["close"]; m = np.log(spy).diff(); out = {"meta": dict(asof=x.asof, generated_utc=now_utc(),
          notes=["beta = sensitivity of the stock's daily log return to the driver's daily change, controlling for SPY, fit on the 120 or 250 sessions before the last 20.",
                 "z20 = summed residual over the last 20 sessions divided by its expected spread: how far the stock has moved away from what the driver and the market imply. |z| >= 2 is flagged.",
                 "Extends screen.py's theme screen (same regression helper and proxies); it does not replace it."]), "drivers": []}
    banks = sorted([t for t, mm in x.meta.items() if mm.get("industry") == "Regional Banks" and t in x.bars], key=lambda t: -x.mcap.get(t, 0))[:5]
    for key, proxy, label, names in DRIVERS:
        note = None
        if proxy == "T10Y2Y":
            try:
                lvl = fred_series("T10Y2Y").reindex(spy.index).ffill(limit=3); p = lvl.diff(); chg = lambda n: round(float(lvl.iloc[-1] - lvl.iloc[-1-n]), 2)
            except Exception as e:
                r = (x.bars["TLT"]["close"]/x.bars["SHY"]["close"]).reindex(spy.index); p = -np.log(r).diff()
                lvl = r; chg = lambda n: round(float(-(r.iloc[-1]/r.iloc[-1-n]-1)*100), 2)
                note = f"FRED unreachable ({type(e).__name__}): proxy = minus the log change of TLT/SHY (curve steepening ~ long bonds lagging short ones)"
            names = names + banks
        else:
            if proxy not in x.bars: out["drivers"].append(dict(key=key, error=f"no prices for {proxy}")); continue
            pc = x.bars[proxy]["close"].reindex(spy.index); p = np.log(pc).diff(); chg = lambda n, pc=pc: round(float(pc.iloc[-1]/pc.iloc[-1-n]-1)*100, 2)
        d = dict(key=key, driver=proxy, label=label, change_1m=chg(21), change_3m=chg(63), change_6m=chg(126),
                 change_units="percentage points" if proxy == "T10Y2Y" and not note else "percent", stocks=[])
        if note: d["note"] = note
        for t in dict.fromkeys(names):
            if t not in x.bars: d["stocks"].append(dict(ticker=t, error="no prices")); continue
            y = np.log(x.bars[t]["close"].reindex(spy.index)).diff()
            D = pd.concat([y.rename("y"), m.rename("m"), p.rename("p")], axis=1).dropna()
            row = dict(ticker=t)
            for n in (120, 250):
                fr = driver_fit(D["y"].values, D["m"].values, D["p"].values, n)
                if fr: row[f"w{n}"] = fr
            zz = [abs(row[k]["z20"]) for k in ("w120", "w250") if k in row and row[k]["z20"] is not None]
            row["flag"] = bool(zz and max(zz) >= 2)
            d["stocks"].append(row)
        out["drivers"].append(d)
    jdump(x.out/"terminal"/"drivers.json", out)
    flags = [f"{d['key']}:{s['ticker']}" for d in out["drivers"] for s in d.get("stocks", []) if s.get("flag")]
    status["terminal/drivers.json"] = dict(rows=sum(len(d.get("stocks", [])) for d in out["drivers"]), flagged=flags)

def section_D(x, status):
    spy = x.bars["SPY"]["close"]
    former = {}
    try:
        mem = screen.load_membership(); dates = mem["date"].values
        member = lambda t, d: (lambda i: i >= 0 and t in mem["set"].iloc[i])(np.searchsorted(dates, np.datetime64(d), side="right") - 1)
        ever = set().union(*mem[mem["date"] >= spy.index[0]]["set"]); gone = sorted(t for t in ever if t not in x.bars and "." not in t)[:FORMER_MAX]
        if not over_budget(): former = screen.pull_yf(gone)
    except Exception as e:
        mem, member = None, None; status["rule_tests/membership_error"] = type(e).__name__
    src = dict(x.bars); src.update(former)
    ev = []
    for t, b in src.items():
        if t in screen.BENCH or len(b) < 300: continue
        c, v = b["close"], b["volume"]
        for k in drop_events(c, v):
            if k + 60 >= len(c): continue
            g = gap_recovery(c, k)
            if not g: continue
            avg_pre = float(v.iloc[k-20:k].mean()); vol10 = float(v.iloc[k+1:k+11].mean())
            fast = g.get("rec10", 0) >= 1/3 and vol10 > avg_pre
            hold = None
            if g.get("two_thirds_day"):
                j = k + g["two_thirds_day"]
                if j < k + 60: hold = float(c.iloc[k+60]/c.iloc[j]-1)*100
            d = c.index[k]
            ev.append(dict(ticker=t, date=d, ym=d.year*100+d.month, fast=fast, hold_after_two_thirds=hold,
                           pit=bool(member(t, d)) if member else None, former=t in former, **g))
    E = pd.DataFrame(ev)
    res = dict(meta=dict(asof=x.asof, generated_utc=now_utc(), events_rule="one-day drop of 10%+ on 2.5x+ the prior 20-day volume, at least 20 sessions apart per stock, with 60 sessions after",
                         survivorship=("Universe = today's S&P 500 and 400 plus former S&P 500 members Yahoo still has prices for; a point-in-time S&P 500 line is shown. "
                                       "It cannot fix: former members Yahoo no longer carries (disproportionately failures, so recovery rates are flattered) and former S&P 400 members.")))
    if len(E) < 30:
        res.update(n=int(len(E)), verdict="NOT SHOWN", summary=f"Only {len(E)} events: too few to test."); jdump(x.out/"rule_tests"/"dislocation_recovery.json", res)
        status["rule_tests/dislocation_recovery.json"] = dict(rows=int(len(E)), verdict="NOT SHOWN"); return
    def block(D):
        r = dict(n=int(len(D)), stocks=int(D.ticker.nunique()))
        for h in (5, 10, 20, 40, 60):
            col = D[f"rec{h}"].clip(-3, 3)
            r[f"median_gap_recovered_{h}d"] = round(float(col.median()), 3); r[f"mean_gap_recovered_{h}d"] = round(float(col.mean()), 3)
        r["pct_fully_closed_60d"] = round(float(D.closed60.mean()*100), 1)
        f, s = D[D.fast], D[~D.fast]
        r["fast"] = dict(n=int(len(f)), pct_closed_60d=round(float(f.closed60.mean()*100), 1) if len(f) else None)
        r["not_fast"] = dict(n=int(len(s)), pct_closed_60d=round(float(s.closed60.mean()*100), 1) if len(s) else None)
        if len(f) >= 10 and len(s) >= 10:
            b, t = clustered_diff(D.closed60.astype(float).values*100, D.fast.astype(float).values, D.ym.values)
            r["fast_minus_not_pts"] = round(b, 1); r["t_clustered"] = round(t, 2) if t is not None else None; r["verdict"] = verdict(b, t)
        R = D[D["rec10"] >= 1/3]                      # control: among events that recovered a third by day 10, does the volume matter?
        if R.fast.sum() >= 10 and (~R.fast).sum() >= 10:
            b2, t2 = clustered_diff(R.closed60.astype(float).values*100, R.fast.astype(float).values, R.ym.values)
            r["volume_control"] = dict(n=int(len(R)), with_volume_minus_without_pts=round(b2, 1), t_clustered=round(t2, 2) if t2 is not None else None,
                                       reads="events that recovered a third of the gap by day 10: above-average volume vs not")
        h = D.hold_after_two_thirds.dropna()
        if len(h) >= 10:
            hm = D.dropna(subset=["hold_after_two_thirds"])
            pm = hm.groupby("ym").hold_after_two_thirds.mean(); tt = float(pm.mean()/(pm.std()/np.sqrt(len(pm)))) if len(pm) > 5 and pm.std() > 0 else None
            r["hold_vs_sell_at_two_thirds"] = dict(n=int(len(h)), mean_extra_pct=round(float(h.clip(h.quantile(0.01), h.quantile(0.99)).mean()), 2),
                                                   median_extra_pct=round(float(h.median()), 2), t_clustered=round(tt, 2) if tt is not None else None,
                                                   reads="return from the close where two thirds of the gap is first recovered to the close 60 sessions after the drop; positive = holding paid")
        return r
    res["all"] = block(E)
    if E.pit.notna().any(): res["sp500_point_in_time"] = block(E[E.pit == True])
    a = res["all"]; v_ = a.get("verdict", "NOT SHOWN"); res["verdict"] = v_
    res["summary"] = (f"{a['n']} drops: {a['pct_fully_closed_60d']}% closed the gap within 60 sessions; fast recoveries on volume closed {a['fast']['pct_closed_60d']}% vs "
                      f"{a['not_fast']['pct_closed_60d']}% (difference {a.get('fast_minus_not_pts')} pts, clustered t {a.get('t_clustered')}): {v_}.")
    vc = a.get("volume_control") or {}
    res["summary"] += (" Caution: an event that has already recovered a third of the gap has less distance left, so it closes more often even in a random walk "
                       "(synthetic random-walk prices in the offline test gave a similar gap); the volume_control line, "
                       f"{vc.get('with_volume_minus_without_pts')} pts with t {vc.get('t_clustered')}, is the cleaner test of the volume part.")
    res["verdict_convention"] = "screen.py's WORKS / NOT SHOWN / HURTS (the spec's UNCLEAR = NOT SHOWN, FAILS = HURTS)"
    jdump(x.out/"rule_tests"/"dislocation_recovery.json", res)
    status["rule_tests/dislocation_recovery.json"] = dict(rows=a["n"], verdict=v_)

# ----------------------------------------------------------------------------- E regime, risk stats, correlation (added 14 Nov 2026)
# Thresholds fixed 14 Nov 2026, before any result was seen. Edit with a date, never after reading the history.
TREND_CAUTION_OFF_HIGH = -7.0      # percent below the 52-week high
BREADTH_CAUTION, BREADTH_STRESS = 50.0, 35.0   # percent of the universe above its 200-day
VIX_CAUTION = 25.0
LEAD_CAUTION_REL60 = -5.0          # SMH vs SPY over 60 sessions, points
CORR_CLUSTER = 0.6                 # E3 threshold clustering
CORR_MAX_NAMES = 40

def trend_state(last, s50, s200, off_high):
    if last < s200: return "stress"
    if last < s50 or off_high <= TREND_CAUTION_OFF_HIGH: return "caution"
    return "ok"

def breadth_state(pct200):
    return "stress" if pct200 < BREADTH_STRESS else "caution" if pct200 < BREADTH_CAUTION else "ok"

def credit_state(ratio, s50, s200, chg20):
    if ratio < s200 and chg20 < 0: return "stress"
    if ratio < s50 or ratio < s200: return "caution"
    return "ok"

def vix_state(vix, vix3m):
    if vix3m is not None and vix > vix3m: return "stress"
    if vix > VIX_CAUTION: return "caution"
    return "ok"

def lead_state(rel60, vs200):
    if vs200 < 0: return "stress"
    if rel60 <= LEAD_CAUTION_REL60: return "caution"
    return "ok"

def overall(states):
    s = sum(1 for x in states if x == "stress"); c = sum(1 for x in states if x == "caution")
    return "red" if s >= 2 else "yellow" if s >= 1 or c >= 3 else "green"

def threshold_clusters(C, names, thr=CORR_CLUSTER):
    """Connected components of the graph 'correlation >= thr'. Returns {name: (cluster id, size)}; ids by size, largest = 1."""
    adj = {n: [m for m in names if m != n and C.get(n, {}).get(m) is not None and C[n][m] >= thr] for n in names}
    seen, comps = set(), []
    for n in names:
        if n in seen: continue
        stack, comp = [n], []
        while stack:
            k = stack.pop()
            if k in seen: continue
            seen.add(k); comp.append(k); stack += adj[k]
        comps.append(sorted(comp))
    comps.sort(key=lambda c: (-len(c), c[0]))
    return {n: (i+1, len(c)) for i, c in enumerate(comps) for n in c}, comps

def beta(y, x):
    ok = ~(np.isnan(y) | np.isnan(x))
    y, x = y[ok], x[ok]
    return round(float(np.cov(y, x)[0, 1]/np.var(x, ddof=1)), 3) if len(y) > 10 and np.var(x) > 0 else None

def section_E(x, status):
    spy = x.bars["SPY"]["close"]; cal = spy.index
    def px(t): return x.bars[t]["close"].reindex(cal).ffill(limit=5) if t in x.bars else None
    # E1 gauges as daily series over the full history
    G = {}
    for t in ("SPY", "QQQ", "IWM"):
        c = px(t)
        if c is None: continue
        s50, s200, hi = c.rolling(50).mean(), c.rolling(200).mean(), c.rolling(252).max()
        G[f"trend_{t}"] = pd.Series([trend_state(a, b, d, (a/h-1)*100) if not np.isnan(d) else None for a, b, d, h in zip(c, s50, s200, hi)], cal)
        G[f"_trend_{t}"] = dict(last=round(float(c.iloc[-1]), 2), vs_50d_pct=round(float(c.iloc[-1]/s50.iloc[-1]-1)*100, 1),
                                vs_200d_pct=round(float(c.iloc[-1]/s200.iloc[-1]-1)*100, 1), off_52w_high_pct=round(float(c.iloc[-1]/hi.iloc[-1]-1)*100, 1))
    names = [t for t in x.meta if t in x.bars and t not in screen.BENCH]
    closes = pd.DataFrame({t: x.bars[t]["close"] for t in names}).reindex(cal).ffill(limit=5)
    valid200 = closes.rolling(200).mean().notna()
    a200 = ((closes > closes.rolling(200).mean()) & valid200).sum(axis=1)/valid200.sum(axis=1).replace(0, np.nan)*100
    a50 = (closes > closes.rolling(50).mean()).sum(axis=1)/closes.rolling(50).mean().notna().sum(axis=1).replace(0, np.nan)*100
    G["breadth"] = pd.Series([breadth_state(v) if not np.isnan(v) else None for v in a200], cal)
    for num, den in (("HYG", "LQD"), ("HYG", "IEF")):
        if num in x.bars and den in x.bars:
            r = px(num)/px(den); s50, s200, ch = r.rolling(50).mean(), r.rolling(200).mean(), r/r.shift(20)-1
            G[f"credit_{num}_{den}"] = pd.Series([credit_state(a, b, c_, d) if not np.isnan(c_) else None for a, b, c_, d in zip(r, s50, s200, ch)], cal)
            G[f"_credit_{num}_{den}"] = dict(ratio=round(float(r.iloc[-1]), 4), vs_50d_pct=round(float(r.iloc[-1]/s50.iloc[-1]-1)*100, 2),
                                             vs_200d_pct=round(float(r.iloc[-1]/s200.iloc[-1]-1)*100, 2), change_20d_pct=round(float(ch.iloc[-1])*100, 2))
    vix = px("^VIX"); v3 = px("^VIX3M")
    if vix is not None:
        G["volatility"] = pd.Series([vix_state(a, (b if v3 is not None and not np.isnan(b) else None)) if not np.isnan(a) else None
                                     for a, b in zip(vix, v3 if v3 is not None else [np.nan]*len(vix))], cal)
    smh = px("SMH")
    if smh is not None:
        rel60 = ((smh/smh.shift(60)) - (spy/spy.shift(60)))*100; rel20 = ((smh/smh.shift(20)) - (spy/spy.shift(20)))*100; vs200 = (smh/smh.rolling(200).mean()-1)*100
        G["leadership"] = pd.Series([lead_state(a, b) if not np.isnan(b) else None for a, b in zip(rel60, vs200)], cal)
    keys = [k for k in G if not k.startswith("_")]
    S = pd.DataFrame({k: G[k] for k in keys})
    state = S.apply(lambda r: overall([v for v in r if v]) if r.notna().sum() >= len(keys) - 1 else None, axis=1)
    last = S.iloc[-1]
    readings = {}
    for t in ("SPY", "QQQ", "IWM"):
        if f"_trend_{t}" in G:
            v = G[f"_trend_{t}"]; readings[f"trend_{t}"] = dict(state=last[f"trend_{t}"], value=v, reading=f"{t} {v['vs_200d_pct']:+.1f}% vs its 200-day, {v['vs_50d_pct']:+.1f}% vs its 50-day, {v['off_52w_high_pct']:.1f}% from its 52-week high")
    readings["breadth"] = dict(state=last["breadth"], value=dict(pct_above_200d=round(float(a200.iloc[-1]), 1), pct_above_50d=round(float(a50.iloc[-1]), 1),
                               change_20d_200d_pts=round(float(a200.iloc[-1]-a200.iloc[-21]), 1), change_20d_50d_pts=round(float(a50.iloc[-1]-a50.iloc[-21]), 1)),
                               reading=f"{a200.iloc[-1]:.0f}% of the universe above its 200-day ({a200.iloc[-1]-a200.iloc[-21]:+.0f} pts in 20 sessions), {a50.iloc[-1]:.0f}% above its 50-day")
    for k in [k for k in keys if k.startswith("credit_")]:
        v = G["_" + k]; readings[k] = dict(state=last[k], value=v, reading=f"{k[7:].replace('_', '/')} {v['vs_200d_pct']:+.2f}% vs its 200-day, {v['change_20d_pct']:+.2f}% in 20 sessions")
    if "volatility" in keys:
        vv, v3v = float(vix.iloc[-1]), (float(v3.iloc[-1]) if v3 is not None else None)
        readings["volatility"] = dict(state=last["volatility"], value=dict(vix=round(vv, 2), vix3m=round(v3v, 2) if v3v else None),
                                      reading=f"VIX {vv:.1f}" + (f" vs VIX3M {v3v:.1f} ({'backwardation' if vv > v3v else 'contango'})" if v3v else " (VIX3M not available)"))
    if "leadership" in keys:
        readings["leadership"] = dict(state=last["leadership"], value=dict(smh_vs_spy_20d_pts=round(float(rel20.iloc[-1]), 1), smh_vs_spy_60d_pts=round(float(rel60.iloc[-1]), 1), smh_vs_200d_pct=round(float(vs200.iloc[-1]), 1)),
                                      reading=f"SMH {rel20.iloc[-1]:+.1f} pts vs SPY over 20 sessions, {rel60.iloc[-1]:+.1f} over 60; {vs200.iloc[-1]:+.1f}% vs its own 200-day")
    states = [r["state"] for r in readings.values() if r["state"]]
    # history: forward SPY after red vs green, on the 10-year backfill
    fwd = spy.shift(-60)/spy - 1
    dd = pd.Series([float((spy.iloc[i+1:i+61]/spy.iloc[i]).min()-1) if i+60 < len(spy) else np.nan for i in range(len(spy))], cal)
    hist = {}
    for lab in ("green", "yellow", "red"):
        m = (state == lab) & fwd.notna()
        if m.sum():
            ym = (cal[m].year*100 + cal[m].month)
            hist[lab] = dict(days=int(m.sum()), months=int(pd.Series(ym).nunique()), fwd60_spy_mean_pct=round(float(fwd[m].mean()*100), 2),
                             fwd60_spy_median_pct=round(float(fwd[m].median()*100), 2), worst_drawdown_60d_mean_pct=round(float(dd[m].mean()*100), 2),
                             pct_drawdown_worse_than_10=round(float((dd[m] < -0.10).mean()*100), 1))
    g, r_ = hist.get("green"), hist.get("red")
    if g and r_:
        edge = r_["worst_drawdown_60d_mean_pct"] - g["worst_drawdown_60d_mean_pct"]
        summ = (f"Over {state.notna().sum()} sessions, red days ({r_['days']} days in {r_['months']} months) were followed by a 60-session SPY return of {r_['fwd60_spy_mean_pct']:+.1f}% on average "
                f"vs {g['fwd60_spy_mean_pct']:+.1f}% after green, and an average worst drawdown of {r_['worst_drawdown_60d_mean_pct']:.1f}% vs {g['worst_drawdown_60d_mean_pct']:.1f}%. ")
        summ += ("Red has marked deeper drawdowns ahead, but the days overlap heavily (few independent episodes), so treat it as a risk gauge, not a timing signal."
                 if edge <= -2 else "Red has not marked meaningfully worse drawdowns than green: no edge shown.")
        summ += " Credit and leadership gauges are in the history too; the universe is today's index members, which flatters breadth in the past."
    else:
        summ = "Not enough red or green days in the backfill to compare: no edge shown."
    h250 = [dict(date=str(d.date()), state=s_) for d, s_ in state.tail(250).items()]
    reg = dict(meta=dict(asof=x.asof, generated_utc=now_utc(), thresholds=dict(trend="stress below the 200-day; caution below the 50-day or 7%+ off the 52-week high",
               breadth=f"caution under {BREADTH_CAUTION:.0f}% above the 200-day, stress under {BREADTH_STRESS:.0f}%", credit="stress: ratio below its 200-day and down over 20 sessions; caution below its 50 or 200-day",
               volatility=f"stress: VIX above VIX3M (backwardation); caution: VIX above {VIX_CAUTION:.0f}", leadership=f"stress: SMH below its 200-day; caution: SMH {LEAD_CAUTION_REL60:.0f} pts or worse vs SPY over 60 sessions",
               overall="red = 2+ gauges in stress; yellow = any stress or 3+ caution; else green", fixed="14 Nov 2026")),
               overall=overall(states), n_stress=states.count("stress"), n_caution=states.count("caution"), gauges=readings,
               history_250=h250, backfill=dict(by_state=hist, summary=summ, first_date=str(state.dropna().index[0].date()) if state.notna().any() else None))
    jdump(x.out/"terminal"/"regime.json", reg)
    status["terminal/regime.json"] = dict(rows=len(readings), overall=reg["overall"], states={k: v["state"] for k, v in readings.items()})
    # E2 risk stats
    try: sj = json.loads((x.out/"terminal"/"screen.json").read_text())
    except Exception: sj = {"rows": []}
    tick = list(dict.fromkeys([r["ticker"] for r in sj.get("rows", [])] + x.watch))
    lr = lambda t: np.log(px(t)).diff() if t in x.bars else None
    rs = lr("SPY"); refs = {k: lr(k) for k in ("SPY", "QQQ", "SMH")}
    big_down = list(cal[(spy.pct_change() <= -0.03)][-3:])
    rows = []
    for t in tick:
        if t not in x.bars: rows.append(dict(ticker=t, error="no prices")); continue
        y = lr(t); sec = screen.SECTOR_ETF.get((x.meta.get(t) or {}).get("sector") or "")
        r = dict(ticker=t, sector_etf=sec or None)
        for n in (60, 250): r[f"beta_{n}"] = beta(y.tail(n).values, rs.tail(n).values)
        dn = (spy.pct_change() <= -0.01).tail(500); yy, ss = y.tail(500)[dn], rs.tail(500)[dn]
        r["downside_beta_500"] = beta(yy.values, ss.values); r["down_days_500"] = int(dn.sum())
        r["avg_return_spy_down_1pct"] = round(float(np.expm1(yy.mean())*100), 2) if len(yy.dropna()) else None
        for k, ref in list(refs.items()) + ([(sec, lr(sec))] if sec and sec in x.bars else []):
            for n in (60, 250):
                d = pd.concat([y, ref], axis=1).dropna().tail(n)
                r[f"corr_{k}_{n}"] = round(float(d.iloc[:, 0].corr(d.iloc[:, 1])), 2) if len(d) > 20 else None
        c = px(t); r["spy_down_3pct_days"] = [dict(date=str(d.date()), spy_pct=round(float(spy.loc[d]/spy.shift(1).loc[d]-1)*100, 2), stock_pct=round(float(c.loc[d]/c.shift(1).loc[d]-1)*100, 2) if not np.isnan(c.loc[d]) else None) for d in big_down]
        rows.append(r)
    jdump(x.out/"terminal"/"risk_stats.json", dict(meta=dict(source="Yahoo daily closes", pulled_utc=now_utc(), notes=["Betas and correlations on daily log returns. downside_beta_500 = beta on sessions where SPY fell 1% or more, last 500 sessions.",
          "spy_down_3pct_days = the stock's return on the last 3 sessions SPY fell 3% or more."]), rows=rows))
    status["terminal/risk_stats.json"] = dict(rows=len(rows))
    # E3 correlation and clusters
    cands = [r["ticker"] for r in sj.get("rows", []) if r.get("tier") in ("DEEP DIVE", "WATCH", "AFTER PRINT")]
    names = [t for t in dict.fromkeys(cands + x.watch) if t in x.bars][:CORR_MAX_NAMES]
    R = pd.DataFrame({t: lr(t) for t in names}).tail(60)
    C60 = R.corr().round(2)
    dmask = (spy.pct_change() < 0).reindex(cal)
    Rd = pd.DataFrame({t: lr(t) for t in names})[dmask].tail(250)
    Cd = Rd.corr().round(2)
    Cdict = {a: {b: (None if np.isnan(C60.loc[a, b]) else float(C60.loc[a, b])) for b in names} for a in names}
    lab, comps = threshold_clusters(Cdict, names)
    jdump(x.out/"terminal"/"corr_matrix.json", dict(meta=dict(asof=x.asof, generated_utc=now_utc(), notes=[f"corr_60 = 60-session correlation of daily log returns; corr_spy_down = correlation over the last 250 SPY down days.",
          f"Clusters: names linked by corr_60 of {CORR_CLUSTER} or more (chains count), largest cluster = 1. Several candidates in one cluster are one bet."]),
          names=names, corr_60=Cdict, corr_spy_down={a: {b: (None if np.isnan(Cd.loc[a, b]) else float(Cd.loc[a, b])) for b in names} for a in names},
          clusters=[dict(cluster=i+1, size=len(c), names=c) for i, c in enumerate(comps)]))
    for r in sj.get("rows", []):
        if r["ticker"] in lab: r["cluster"], r["cluster_size"] = lab[r["ticker"]]
    if sj.get("rows"): (x.out/"terminal"/"screen.json").write_text(json.dumps(sj, separators=(",", ":"), default=str))
    status["terminal/corr_matrix.json"] = dict(rows=len(names), largest_cluster=comps[0] if comps else [])

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="out"); ap.add_argument("--only", default="A,B,C,D,E")
    a = ap.parse_args(); out = Path(a.out); only = a.only.split(",")
    x = load_ctx(out); status = {}; secs = []
    print(f"datasets: universe {len(x.meta)} bars {len(x.bars)} big {len(x.big)} core {len(x.core)} coverage {len(x.cov)} ({time.time()-T0:.0f}s)")
    for key, fn in (("E", section_E), ("A", section_A), ("B", section_B), ("C", section_C), ("D", section_D)):
        if key not in only: continue
        if over_budget(): secs.append(dict(section=key, status="skipped", why="runtime budget")); continue
        t1 = time.time()
        try: fn(x, status); secs.append(dict(section=key, status="ok", seconds=round(time.time()-t1)))
        except Exception as e:
            secs.append(dict(section=key, status="failed", error=type(e).__name__, detail=str(e)[:200], trace=traceback.format_exc()[-500:]))
        print(f"section {key}: {secs[-1]['status']} ({time.time()-t1:.0f}s)")
    hm = history_manifest(out/"history") if (out/"history").exists() else {}
    jdump(out/"history"/"manifest.json", dict(generated_utc=now_utc(), datasets=hm))
    mp = out/"terminal"/"manifest.json"
    try: man = json.loads(mp.read_text())
    except Exception: man = {"files": {}}
    for k, v in status.items():
        if k.startswith("terminal/") or k.startswith("rule_tests/"):
            name = k.split("terminal/")[-1] if k.startswith("terminal/") else "../" + k
            man["files"][name] = dict(pulled_utc=now_utc(), rows=v.get("rows", 0), status="ok", written_by="datasets.py", **{kk: vv for kk, vv in v.items() if kk != "rows"})
    for s in secs:
        if s["status"] != "ok": man["files"][f"datasets section {s['section']}"] = dict(pulled_utc=now_utc(), rows=0, status="failed", error=s.get("error") or s.get("why"))
    man["datasets_runtime_s"] = round(time.time()-T0); man["generated_utc"] = now_utc()
    jdump(mp, man)
    print("DATASETS", json.dumps(status, default=str)); print("SECTIONS", secs, f"runtime {time.time()-T0:.0f}s")

if __name__ == "__main__":
    main()
