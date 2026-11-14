#!/usr/bin/env python3
"""CM research desk: terminal data pulls (v16, 14 Nov 2026). Runs after screen.py in the same workflow.

Writes small JSON files to out/terminal/, each {meta: {source, pulled_utc, notes}, rows: [...]}:
  dc_spend.json        Census C30 value of construction put in place, private, data center, monthly ($M)
  dc_capex.json        quarterly cash paid for property and equipment (SEC XBRL companyconcept), six AI spenders
  earnings_dates.json  next earnings date for the ranked names plus terminal_watch.txt
  chains.json          option summary for terminal_watch.txt (same as screen.py) plus at-the-money vol reads
  manifest.json        each file, pulled time, row count, status ok | stale | failed (error class)

Never fabricates: a failed pull keeps the previous file (status stale) or writes nothing (status failed).
  python terminal_pulls.py [--out out] [--only dc_spend,dc_capex,earnings,chains]
"""
import argparse, datetime as dt, io, json, re, sys, time, urllib.request
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screen  # sec_get, SEC user agent, ticker_cik, option helpers

C30_PAGE = "https://www.census.gov/construction/c30/historical_data.html"
C30_SA = "https://www.census.gov/construction/c30/xlsx/privsatime.xlsx"
C30_NSA = "https://www.census.gov/construction/c30/xlsx/privnsatime.xlsx"
TIEOUT = {"2026-09": 96462, "2025-09": 50700}     # $M SAAR, from the owner's spec; revisions allowed up to TIEOUT_TOL
TIEOUT_TOL = 0.03
CAPEX_CO = [("Microsoft", "MSFT"), ("Alphabet", "GOOGL"), ("Amazon", "AMZN"), ("Meta", "META"), ("Oracle", "ORCL"), ("CoreWeave", "CRWV")]
CAPEX_CONCEPTS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
CAPEX_QUARTERS = 16
UA = "cm-research-desk/1.0 (github.com/wingerlc-spec/cm-research-desk)"

def now_utc(): return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")

def http_get(url, timeout=60, tries=3):
    err = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            err = e; time.sleep(2*(k+1))
    raise err

# ----------------------------------------------------------------------------- Census C30
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def parse_month(v):
    """Cell -> 'YYYY-MM' or None. Accepts datetimes, 'Sep-26', 'Sep 2026', 'Sept. 2026p', '2026-09', 'September 2026'."""
    if v is None: return None
    if isinstance(v, (dt.datetime, dt.date, pd.Timestamp)): return f"{v.year:04d}-{v.month:02d}"
    s = str(v).strip().lower().replace(".", " ").replace(",", " ")
    m = re.match(r"^(\d{4})[-/](\d{1,2})\b", s)
    if m and 1 <= int(m.group(2)) <= 12: return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.match(r"^([a-z]{3})[a-z]*[\s\-]+(\d{2}|\d{4})\s*[a-z()]*\s*$", s)
    if m and m.group(1) in MONTHS:
        y = int(m.group(2)); y = y + 2000 if y < 100 else y
        return f"{y:04d}-{MONTHS[m.group(1)]:02d}"
    return None

def parse_num(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace(",", "")
    try: return float(s)
    except ValueError: return None          # (NA), (S), (X), blanks: left out

def find_series(grid, label="data center"):
    """grid: list of rows (lists of cell values). Finds the cell whose text is the label and reads its series, whichever way
    the sheet runs: months across a header row above it, or months down a column beside it. Returns {YYYY-MM: value}."""
    norm = lambda v: re.sub(r"[^a-z ]", "", str(v or "").lower()).strip()
    hits = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if norm(v) in (label, label + "s")]
    if not hits: raise ValueError(f"no '{label}' cell in sheet")
    for r, c in hits:
        # months across: a row above with 12+ month cells
        for hr in range(r-1, -1, -1):
            cols = {j: parse_month(v) for j, v in enumerate(grid[hr])}
            cols = {j: m for j, m in cols.items() if m}
            if len(cols) >= 12:
                out = {m: parse_num(grid[r][j]) for j, m in cols.items() if j < len(grid[r])}
                out = {m: v for m, v in out.items() if v is not None}
                if out: return out
                break
        # months down: a column with 12+ month cells in rows below the label
        for mc in range(len(grid[r])):
            rows = {i: parse_month(grid[i][mc] if mc < len(grid[i]) else None) for i in range(r+1, len(grid))}
            rows = {i: m for i, m in rows.items() if m}
            if len(rows) >= 12:
                out = {m: parse_num(grid[i][c] if c < len(grid[i]) else None) for i, m in rows.items()}
                out = {m: v for m, v in out.items() if v is not None}
                if out: return out
    raise ValueError(f"'{label}' found but no month axis next to it")

def sheet_grid(xlsx_bytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}

def series_from_xlsx(xlsx_bytes):
    errs = []
    for name, grid in sheet_grid(xlsx_bytes).items():
        try: return find_series(grid)
        except ValueError as e: errs.append(f"{name}: {e}")
    raise ValueError("; ".join(errs)[:300])

def tie_out(sa):
    bad = []
    for m, want in TIEOUT.items():
        got = sa.get(m)
        if got is None: bad.append(f"{m} absent")
        elif abs(got/want - 1) > TIEOUT_TOL: bad.append(f"{m} = {got:,.0f} vs {want:,} expected")
    return bad

def c30_links():
    """Start from the historical data page; fall back to the known file names."""
    sa, nsa = C30_SA, C30_NSA
    try:
        from bs4 import BeautifulSoup
        html = http_get(C30_PAGE).decode("utf-8", "replace")
        for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            h = a["href"]; full = urllib.request.urljoin(C30_PAGE, h)
            if h.endswith("privsatime.xlsx"): sa = full
            if h.endswith("privnsatime.xlsx"): nsa = full
    except Exception:
        pass
    return sa, nsa

def pull_dc_spend():
    notes = []
    sa_url, nsa_url = c30_links()
    sa = series_from_xlsx(http_get(sa_url))
    bad = tie_out(sa)
    if bad: raise ValueError("tie-out failed: " + "; ".join(bad))
    notes.append(f"tie-out ok within {TIEOUT_TOL:.0%}: " + ", ".join(f"{m} {sa[m]:,.0f}" for m in TIEOUT))
    nsa = {}
    try: nsa = series_from_xlsx(http_get(nsa_url))
    except Exception as e: notes.append(f"not seasonally adjusted series not available ({type(e).__name__})")
    rows = []
    for m in sorted(sa):
        r = dict(month=m, saar_musd=sa[m])
        if m in nsa: r["nsa_musd"] = nsa[m]
        rows.append(r)
    notes.append("$ millions. saar_musd = seasonally adjusted annual rate; nsa_musd = monthly value, not seasonally adjusted, where published.")
    return dict(source=f"US Census Bureau C30, private construction, data center ({sa_url}" + (f", {nsa_url}" if nsa else "") + ")", notes=notes), rows

# ----------------------------------------------------------------------------- SEC capex
def _days(a, b): return (pd.Timestamp(b) - pd.Timestamp(a)).days

def facts_to_quarters(facts):
    """facts: companyconcept USD entries {start, end, val, form, filed, fy, fp}. Cash-flow lines are year to date in 10-Qs and
    full year in the 10-K, so single quarters = YTD minus the previous YTD with the same start. A 3-month fact is used as is.
    Value per period = latest filing (restatements win); form and filed = the first filing that carried it.
    Returns {end: dict(start, end, val, form, filed, derived, restated)}."""
    per = {}
    for f in facts:
        if not f.get("start") or not f.get("end") or f.get("val") is None: continue
        if f.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A", "10-KT", "20-F", "40-F"): continue
        k = (f["start"], f["end"]); p = per.setdefault(k, dict(first=f, last=f, vals=set()))
        if f["filed"] < p["first"]["filed"]: p["first"] = f
        if f["filed"] >= p["last"]["filed"]: p["last"] = f
        p["vals"].add(float(f["val"]))
    q = {}
    def put(start, end, val, src, derived):
        if end in q and not q[end]["derived"]: return
        q[end] = dict(start=start, end=end, val=val, form=src["first"]["form"], filed=src["first"]["filed"], derived=derived,
                      restated=len(src["vals"]) > 1)
    for (s, e), p in per.items():
        n = _days(s, e)
        if 80 <= n <= 100: put(s, e, float(p["last"]["val"]), p, False)
    for (s, e), p in per.items():
        n = _days(s, e)
        if n <= 100: continue
        prev = [(s2, e2) for (s2, e2) in per if s2 == s and 80 <= _days(e2, e) <= 100]
        if not prev: continue
        s2, e2 = prev[0]
        qs = (pd.Timestamp(e2) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        put(qs, e, float(p["last"]["val"]) - float(per[(s2, e2)]["last"]["val"]), p, True)
    return q

def cal_quarter(start, end):
    """Calendar quarter holding the midpoint of the fiscal quarter, e.g. Jun-Aug -> Q3, Dec-Feb -> Q1."""
    mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start))/2
    return f"{mid.year} Q{(mid.month-1)//3+1}"

def capex_rows(company, sym, by_concept, n=CAPEX_QUARTERS):
    """by_concept: {concept: facts}. The first concept wins a quarter; the second fills quarters the first does not have."""
    merged = {}
    for concept in CAPEX_CONCEPTS:
        for end, v in facts_to_quarters(by_concept.get(concept) or []).items():
            if end not in merged: merged[end] = dict(v, concept=concept)
    rows = []
    for end in sorted(merged)[-n:]:
        v = merged[end]
        note = f"fiscal quarter {v['start']} to {v['end']}; {v['concept']}"
        if v["derived"]: note += "; year to date minus prior year to date"
        if v["restated"]: note += "; value revised in a later filing (latest used)"
        rows.append(dict(company=company, sym=sym, quarter=cal_quarter(v["start"], v["end"]), capex_musd=round(v["val"]/1e6, 1),
                         form=v["form"], filed=v["filed"], note=note))
    return rows

def pull_dc_capex():
    cik = screen.ticker_cik(); rows, notes = [], []
    for company, sym in CAPEX_CO:
        c = cik.get(sym)
        if not c: notes.append(f"{sym}: no CIK in SEC ticker file"); continue
        by = {}
        for concept in CAPEX_CONCEPTS:
            d = screen.sec_get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{c:010d}/us-gaap/{concept}.json")
            if d: by[concept] = (d.get("units") or {}).get("USD") or []
        r = capex_rows(company, sym, by)
        if not r: notes.append(f"{sym}: no capex facts found")
        rows += r
    if not rows: raise RuntimeError("no capex rows from SEC")
    notes.append("Cash paid for property and equipment, $ millions, single quarters. Fiscal quarters are mapped to the calendar quarter holding "
                 "their midpoint. A quarter not yet filed is absent.")
    return dict(source="SEC XBRL companyconcept (data.sec.gov)", notes=notes), rows

# ----------------------------------------------------------------------------- earnings dates
def read_watch(path):
    p = Path(path)
    if not p.exists(): return []
    out = []
    for line in p.read_text().splitlines():
        t = line.split("#")[0].strip().upper()
        if t and t not in out: out.append(t)
    return out

def next_earnings_yahoo(t, today):
    """Returns (date string or None, source, note)."""
    import yfinance as yf
    tk = yf.Ticker(t); past = None
    try:
        cal = tk.calendar; d = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if d:
            fut = [str(x) for x in d if pd.Timestamp(x) >= pd.Timestamp(today)]
            if fut: return fut[0], "yahoo calendar", ("date range " + " to ".join(str(x) for x in d) if len(d) > 1 else None)
            past = str(d[0])
    except Exception: pass
    try:
        ed = tk.get_earnings_dates(limit=8)
        if ed is not None and len(ed):
            idx = [pd.Timestamp(x).tz_localize(None) if pd.Timestamp(x).tzinfo else pd.Timestamp(x) for x in ed.index]
            fut = sorted(x for x in idx if x >= pd.Timestamp(today))
            if fut: return str(fut[0].date()), "yahoo earnings dates", None
    except Exception: pass
    return None, None, (f"Yahoo shows only a past date ({past})" if past else "not available from Yahoo")

def pull_earnings(out, watch, today):
    ranked = []
    try: ranked = [r["ticker"] for r in json.loads((out/"screen_output.json").read_text()).get("ranked", [])]
    except Exception: pass
    syms = list(dict.fromkeys(ranked + watch)); rows, n_ok = [], 0
    for t in syms:
        d, src, note = next_earnings_yahoo(t, today)
        r = dict(sym=t)
        if d: r["next_earnings"] = d; r["source"] = src; n_ok += 1
        if note: r["note"] = note
        rows.append(r); time.sleep(0.2)
    if not n_ok: raise RuntimeError("no earnings dates returned")
    return dict(source="Yahoo via yfinance", notes=[f"{n_ok} of {len(syms)} names have a next date; ranked names from screen_output.json plus terminal_watch.txt"]), rows

# ----------------------------------------------------------------------------- chains for the watch list
def monthly_and_post_earnings(next_earn, today):
    def pick(exps):
        t0 = pd.Timestamp(today); out = {}
        monthly = [e for e in exps if screen.third_friday(pd.Timestamp(e)) and pd.Timestamp(e) > t0]
        if monthly: out["atm_nearest_monthly"] = monthly[0]
        if next_earn:
            after = [e for e in exps if pd.Timestamp(e) > pd.Timestamp(next_earn)]
            if after: out["atm_after_earnings"] = after[0]
        return out
    return pick

def pull_chains(out, watch, today):
    import yfinance as yf
    earn = {}
    try: earn = {r["sym"]: r.get("next_earnings") for r in json.loads((out/"terminal"/"earnings_dates.json").read_text())["rows"]}
    except Exception: pass
    rows, notes = [], []
    for t in watch:
        try:
            h = yf.Ticker(t).history(period="5d", auto_adjust=False)
            S = float(h["Close"].dropna().iloc[-1])
            s = screen.chain_summary(t, S, today, extra_expiries=monthly_and_post_earnings(earn.get(t), today))
            if earn.get(t): s["next_earnings"] = earn[t]
            a = s.get("atm_after_earnings") or {}
            if a.get("straddle_pct_of_spot") is not None: s["implied_move_pct"] = a["straddle_pct_of_spot"]
            rows.append(s)
        except Exception as e:
            rows.append(dict(sym=t, error=f"{type(e).__name__}: {str(e)[:100]}")); notes.append(f"{t}: {type(e).__name__}")
    if not any("option" in r for r in rows): raise RuntimeError("no chains returned")
    notes.append("Same selection rules as out/options.json. implied_move_pct = at-the-money straddle mid / spot for the first expiry after the next "
                 "earnings date (covers more than the earnings day). atm_iv averages the call and put iv at the strike nearest spot.")
    return dict(source="Yahoo via yfinance", notes=notes), rows

# ----------------------------------------------------------------------------- driver
def write(out, name, fn, manifest):
    p = out/"terminal"/name
    try:
        meta, rows = fn()
        meta = dict(meta, pulled_utc=now_utc())
        p.write_text(json.dumps(dict(meta=meta, rows=rows), indent=1, default=str))
        manifest[name] = dict(pulled_utc=meta["pulled_utc"], rows=len(rows), status="ok")
        print(f"{name}: ok, {len(rows)} rows")
    except Exception as e:
        prev = None
        try: prev = json.loads(p.read_text())
        except Exception: pass
        if prev:
            manifest[name] = dict(pulled_utc=prev.get("meta", {}).get("pulled_utc"), rows=len(prev.get("rows", [])), status="stale",
                                  error=type(e).__name__, detail=str(e)[:200])
        else:
            manifest[name] = dict(pulled_utc=None, rows=0, status="failed", error=type(e).__name__, detail=str(e)[:200])
        print(f"{name}: {manifest[name]['status']} ({type(e).__name__}: {str(e)[:200]})")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="out"); ap.add_argument("--watch", default="terminal_watch.txt")
    ap.add_argument("--only", default="dc_spend,dc_capex,earnings,chains")
    a = ap.parse_args(); out = Path(a.out); (out/"terminal").mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat(); watch = read_watch(a.watch); only = set(a.only.split(","))
    mp = out/"terminal"/"manifest.json"
    try: manifest = json.loads(mp.read_text()).get("files", {})
    except Exception: manifest = {}
    if "dc_spend" in only: write(out, "dc_spend.json", pull_dc_spend, manifest)
    if "dc_capex" in only: write(out, "dc_capex.json", pull_dc_capex, manifest)
    if "earnings" in only: write(out, "earnings_dates.json", lambda: pull_earnings(out, watch, today), manifest)
    if "chains" in only: write(out, "chains.json", lambda: pull_chains(out, watch, today), manifest)
    sp = out/"terminal"/"screen.json"
    if sp.exists():
        try:
            d = json.loads(sp.read_text())
            manifest["screen.json"] = dict(pulled_utc=d.get("generated_utc"), rows=len(d.get("rows", [])), status="ok", written_by="screen.py")
        except Exception as e:
            manifest["screen.json"] = dict(pulled_utc=None, rows=0, status="failed", error=type(e).__name__)
    mp.write_text(json.dumps(dict(generated_utc=now_utc(), files=manifest), indent=1))
    bad = [k for k, v in manifest.items() if v["status"] != "ok"]
    print("MANIFEST", {k: (v["status"], v["rows"]) for k, v in manifest.items()}, "| not ok:", bad)

if __name__ == "__main__":
    main()
