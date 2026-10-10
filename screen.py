#!/usr/bin/env python3
"""CM research desk: chart screener.

Pulls daily bars for a universe, computes chart statistics, sorts names into archetypes and writes
  out/screen_output.json      survivors only, the file Claude reads
  out/market_state_full.json  every name, every field (never read into context; git history = prior state)
  out/charts/<TICKER>.png     one chart per survivor

Nothing about positions, levels or P&L belongs in this repo.

  python screen.py                      # live: yfinance, S&P 500 + lattice ETFs
  python screen.py --csv-dir data/      # offline test on Alpha Vantage style CSVs
"""
import argparse, datetime as dt, io, json, sys, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

UNIVERSE_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
SECTOR_ETF = {"Information Technology": "XLK", "Financials": "XLF", "Energy": "XLE", "Health Care": "XLV",
              "Industrials": "XLI", "Utilities": "XLU", "Consumer Discretionary": "XLY", "Consumer Staples": "XLP",
              "Real Estate": "XLRE", "Materials": "XLB", "Communication Services": "XLC"}
BENCH = ["SPY", "QQQ", "IWM"] + sorted(set(SECTOR_ETF.values()))
PER_ARCHETYPE = 8          # survivors charted per archetype
RANK_POOL = 12             # candidates per archetype sent to the ranking step
HOLD = 60                  # sessions: time stop used in every simulated trade
MIN_PRICE, MIN_DVOL, MIN_BARS = 5.0, 20e6, 260

# ----------------------------------------------------------------------------- data
SP400_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
UNIVERSE_NOTE = []

def parse_wiki_table(html):
    """First wikitable on the page -> {symbol: meta}. Columns found by header name, not position."""
    from bs4 import BeautifulSoup
    tb = BeautifulSoup(html, "html.parser").find("table", {"class": "wikitable"})
    rows = tb.find_all("tr"); hdr = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
    col = lambda *names: next(i for i, h in enumerate(hdr) if any(n in h for n in names))
    i_sym, i_name, i_sec, i_ind = col("symbol", "ticker"), col("security", "company"), col("gics sector", "sector"), col("sub-industry", "sub industry")
    out = {}
    for r in rows[1:]:
        c = [x.get_text(strip=True) for x in r.find_all(["th", "td"])]
        if len(c) > max(i_sym, i_name, i_sec, i_ind) and c[i_sym]:
            out[c[i_sym].replace(".", "-")] = dict(name=c[i_name], sector=c[i_sec], industry=c[i_ind], index="SP400")
    return out

def load_universe():
    raw = urllib.request.urlopen(UNIVERSE_URL, timeout=30).read().decode()
    df = pd.read_csv(io.StringIO(raw))
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)   # BRK.B -> BRK-B for Yahoo
    u = {r.Symbol: dict(name=r.Security, sector=r["GICS Sector"], industry=r["GICS Sub-Industry"], index="SP500") for _, r in df.iterrows()}
    try:
        req = urllib.request.Request(SP400_URL, headers={"User-Agent": "cm-research-desk/1.0 (github.com/wingerlc-spec/cm-research-desk)"})
        mid = parse_wiki_table(urllib.request.urlopen(req, timeout=30).read().decode())
        if len(mid) < 300: raise ValueError(f"only {len(mid)} rows parsed")
        for k, v in mid.items(): u.setdefault(k, v)
        UNIVERSE_NOTE.append(f"S&P 500 ({len(df)}) + S&P 400 ({len(mid)})")
    except Exception as e:
        UNIVERSE_NOTE.append(f"S&P 500 ONLY: S&P 400 list failed ({type(e).__name__}: {str(e)[:80]})")
    return u

def pull_yf(tickers):
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i+100]
        d = yf.download(chunk, period="10y", interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False)
        for t in chunk:
            try:
                x = d[t][["Close", "High", "Low", "Volume"]].dropna()
                if len(x): out[t] = x.rename(columns=str.lower)
            except Exception:
                pass
    return out

def pull_csv(folder):
    out = {}
    for f in sorted(Path(folder).glob("*.csv")):
        d = pd.read_csv(f, parse_dates=["timestamp"]).sort_values("timestamp").set_index("timestamp")
        k = d["adjusted_close"] / d["close"] if "adjusted_close" in d else 1.0
        out[f.stem] = pd.DataFrame({"close": d["close"]*k, "high": d["high"]*k, "low": d["low"]*k, "volume": d["volume"]}).tail(2520)
    return out

# ----------------------------------------------------------------------------- features
def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + up/dn.replace(0, np.nan))

def features(t, x, spy):
    c, h, l, v = x["close"], x["high"], x["low"], x["volume"]
    n = len(c); last = float(c.iloc[-1])
    f = dict(ticker=t, date=str(c.index[-1].date()), last=round(last, 2), bars=n)
    f["dvol20"] = float((c*v).tail(20).mean())
    if n < MIN_BARS: f["skip"] = "history < 260 sessions"; return f
    r = lambda k: float(last/c.iloc[-1-k]-1)*100
    s20, s50, s200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    f.update(d1=r(1), w1=r(5), m1=r(21), m3=r(63), m6=r(126),
             vs20=(last/s20.iloc[-1]-1)*100, vs50=(last/s50.iloc[-1]-1)*100, vs200=(last/s200.iloc[-1]-1)*100,
             slope50=(s50.iloc[-1]/s50.iloc[-11]-1)*100, slope200=(s200.iloc[-1]/s200.iloc[-21]-1)*100,
             rsi=float(rsi(c).iloc[-1]))
    hi52, lo52 = float(c.tail(252).max()), float(c.tail(252).min())
    f["pos52"] = (last-lo52)/(hi52-lo52)*100 if hi52 > lo52 else 50.0
    f["dd52"] = (last/hi52-1)*100
    f["volx"] = float(v.iloc[-1]/v.iloc[-21:-1].mean())
    # base / coil (consolidation-screener-spec v3): range window t-65..t-6
    win_h, win_l = h.iloc[-65:-5], l.iloc[-65:-5]
    rhi, rlo = float(win_h.max()), float(win_l.min())
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    f.update(pivot=round(rhi, 2), base_low=round(rlo, 2), tightness=(rhi-rlo)/((rhi+rlo)/2),
             compression=float(atr.iloc[-1]/atr.iloc[-43]), dryup=float(v.tail(20).mean()/v.iloc[-60:-20].mean()),
             dist_pivot=(last/rhi-1)*100)
    f.update(s50=float(s50.iloc[-1]), s200=float(s200.iloc[-1]), hi52c=hi52, min20=float(c.tail(20).min()),
             pivot_c=float(c.iloc[-65:-5].max()), base_low_c=float(c.iloc[-65:-5].min()))
    bbw = 4*c.rolling(20).std()/s20
    f["bbw_pct"] = float((bbw.tail(504) < bbw.iloc[-1]).mean()*100)      # percentile of today's bandwidth, 2y
    # scare: worst single session inside the last 10, with its volume multiple and the trend before it
    ret = c.pct_change()*100; k = int(np.argmin(ret.tail(10).values)); pos = n-10+k
    f.update(worst_day=float(ret.iloc[pos]), worst_day_date=str(c.index[pos].date()),
             worst_day_volx=float(v.iloc[pos]/v.iloc[pos-20:pos].mean()),
             pre_vs200=float((c.iloc[pos-1]/s200.iloc[pos-1]-1)*100),
             pre_event_close=float(c.iloc[pos-1]), post_event_low=float(c.iloc[pos:].min()))
    # relative strength
    if spy is not None:
        j = c.index.intersection(spy.index)
        rel = (c[j]/spy[j])
        if len(rel) > 130:
            f["rs3"] = float(rel.iloc[-1]/rel.iloc[-64]-1)*100; f["rs6"] = float(rel.iloc[-1]/rel.iloc[-127]-1)*100
    # data sniff test: an unadjusted split or a bad print shows up as a huge one-day move
    big = ret.tail(130).abs().max()
    if big > 45: f["suspect"] = f"{big:.0f}% one-day move inside 130 sessions"
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items()}

# ----------------------------------------------------------------------------- archetypes
# Each rule returns (score, reason) or None. Higher score = better example of the archetype.
def a_base(f):
    if not (f["tightness"] < 0.20 and f["compression"] < 1.0 and f["dryup"] < 1.0 and f["vs200"] > -5 and f["bbw_pct"] <= 30): return None   # tight vs its OWN history
    d = f["dist_pivot"]
    cls = "IN_BASE" if d < -3 else "AT_PIVOT" if d <= 0.5 else "BREAKOUT" if d <= 6 else None
    if cls is None: return None
    score = (0.20-f["tightness"])*200 + (1-f["compression"])*20 + (1-f["dryup"])*20 + (10 if cls == "AT_PIVOT" else 5 if cls == "BREAKOUT" else 0)
    return score, f"{cls}: 60d range {f['tightness']*100:.0f}%, ATR {f['compression']:.2f}x of 2m ago, volume {f['dryup']:.2f}x, {d:+.1f}% vs pivot {f['pivot']}"

def a_momentum(f):
    if not (f["pos52"] > 90 and f["m6"] > 20 and f["vs50"] > 0 and f["vs50"] < 15 and f["slope50"] > 0 and f["slope200"] > 0 and f.get("rs6", 0) > 10 and f["rsi"] < 80): return None
    return f.get("rs6", 0) + f["m3"]/2 - max(f["vs50"]-8, 0)*2, f"6m {f['m6']:+.0f}%, {f.get('rs6', 0):+.0f}pts vs SPY, {f['pos52']:.0f}% of 52w range, {f['vs50']:+.1f}% over a rising 50d"

def a_scare(f):
    if not (f["worst_day"] <= -7 and f["worst_day_volx"] >= 2.5 and f["pre_vs200"] > 0): return None
    return -f["worst_day"] + f["worst_day_volx"] + f["pre_vs200"]/5, f"{f['worst_day']:.1f}% on {f['worst_day_date']} at {f['worst_day_volx']:.1f}x volume; was {f['pre_vs200']:+.0f}% over the 200d before it; now RSI {f['rsi']:.0f}"

def a_value_div(f):   # price half only. The estimates half (revisions turning up) is added by estimates.py when a key exists.
    if not (f["dd52"] <= -25 and f["vs20"] > 0 and 0 < f["m1"] <= 25 and f["rsi"] > 45 and f["rsi"] < 65): return None   # over +25% in a month: the idea is gone
    return -f["dd52"]/2 + f["m1"], f"{f['dd52']:.0f}% off the 52w high, back over the 20d, 1m {f['m1']:+.1f}%. Needs estimates: revisions must be turning up"

def a_macro(f, sec):  # sector has recovered, the stock has not
    if sec is None: return None
    lag = f["m3"] - sec["m3"]
    if not (sec["vs50"] > 0 and sec["m1"] > 2 and lag < -10 and f["vs50"] < 0): return None
    return -lag, f"sector ETF {sec['ticker']} is {sec['vs50']:+.1f}% over its 50d and {sec['m1']:+.1f}% on the month; the stock lags it by {lag:.0f}pts over 3m and sits {f['vs50']:.1f}% under its own 50d. Driver to be named in research"

def a_unclassified(f):   # fits no archetype but the tape did something unusual. This is where new archetypes come from.
    hit = []
    if abs(f["d1"]) >= 5 and f["volx"] >= 2.5: hit.append(f"{f['d1']:+.1f}% on {f['volx']:.1f}x volume")
    if f["pos52"] >= 99 and f["volx"] >= 2: hit.append(f"52w high on {f['volx']:.1f}x volume")
    if f["pos52"] <= 1 and f["volx"] >= 2: hit.append(f"52w low on {f['volx']:.1f}x volume")
    if abs(f["vs200"]) < 1 and abs(f["w1"]) >= 6: hit.append(f"crossed the 200d with a {f['w1']:+.1f}% week")
    if f["bbw_pct"] <= 2: hit.append(f"tightest 20d range in 2 years ({f['bbw_pct']:.0f}th pct)")
    if f.get("rs3", 0) >= 25 and f["dd52"] < -15: hit.append(f"+{f.get('rs3', 0):.0f}pts vs SPY in 3m while still {f['dd52']:.0f}% off the high")
    if not hit: return None
    return abs(f["d1"])*max(f["volx"], 1) + 10*len(hit), "; ".join(hit)

RULES = [("BASE_COIL", a_base), ("MOMENTUM", a_momentum), ("NARRATIVE_SCARE", a_scare), ("VALUE_DIVERGENCE", a_value_div)]

# ----------------------------------------------------------------------------- chart
PRICE, ACC, GRAY1, GRAY2, INK, PAPER = "#00568F", "#883136", "#8C948F", "#C9CEC9", "#171A19", "#FBF8F3"

def chart(t, x, f, arch, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = x["close"]; s50, s200 = c.rolling(50).mean(), c.rolling(200).mean(); w = 190
    fig, (ax, av) = plt.subplots(2, 1, figsize=(7, 3.6), dpi=110, gridspec_kw=dict(height_ratios=[4, 1], hspace=0.05), facecolor=PAPER)
    ax.set_facecolor(PAPER); av.set_facecolor(PAPER)
    ax.plot(c.index[-w:], s200.iloc[-w:], color=GRAY2, lw=1.2); ax.plot(c.index[-w:], s50.iloc[-w:], color=GRAY1, lw=1.2, ls="--")
    ax.plot(c.index[-w:], c.iloc[-w:], color=PRICE, lw=1.6)
    if arch == "BASE_COIL":
        for lv, lab in ((f["pivot"], "pivot"), (f["base_low"], "base low")):
            ax.axhline(lv, color=ACC, lw=0.8, ls=":"); ax.text(c.index[-w], lv, f" {lab} {lv}", color=ACC, fontsize=7, va="bottom")
    ax.set_title(f"{t}  {f['last']}   {arch}", loc="left", fontsize=10, color=INK, fontweight="bold")
    ax.tick_params(labelsize=7, labelbottom=False, length=0); av.tick_params(labelsize=7, length=0)
    av.bar(x.index[-w:], x["volume"].iloc[-w:], color=GRAY1, width=1.0); av.set_yticks([])
    for a in (ax, av):
        for s in a.spines.values(): s.set_visible(False)
    fig.savefig(path, bbox_inches="tight", facecolor=PAPER); plt.close(fig)

# ----------------------------------------------------------------------------- ranking: does this setup pay, on this stock's own history?
ENTRY_STYLE = {"BASE_COIL": "confirmation", "MOMENTUM": "confirmation", "NARRATIVE_SCARE": "weakness", "VALUE_DIVERGENCE": "weakness",
               "MACRO_PUNISHED": "weakness", "UNCLASSIFIED": "none"}

def levels(f, arch):
    """Entry, stop, target from raw closes. Target None = no natural target; exit is the stop or the time stop."""
    last = f["last"]; floor20 = f["min20"]*0.98
    if arch == "BASE_COIL":
        entry = max(f["pivot_c"], last); stop = f["s50"] if 0.03 <= 1-f["s50"]/entry <= 0.10 else entry*0.93
        return entry, stop, entry + (f["pivot_c"]-f["base_low_c"])
    if arch == "MOMENTUM":
        return last, (f["s50"] if 0.03 <= 1-f["s50"]/last <= 0.12 else last*0.90), None
    if arch == "NARRATIVE_SCARE":
        return last, min(f["post_event_low"]*0.97, last*0.95), f["pre_event_close"]
    if arch == "VALUE_DIVERGENCE":
        return last, min(floor20, last*0.95), (f["s200"] if f["s200"] > last*1.05 else last + 0.5*(f["hi52c"]-last))
    if arch == "MACRO_PUNISHED":
        return last, min(floor20, last*0.95), last*1.12
    return last, min(floor20, last*0.95), None

def signal_days(x, arch, sec=None):
    """Boolean series: the days in this stock's past when the same archetype condition was true."""
    c, v = x["close"], x["volume"]
    s20, s50, s200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    hi, lo = c.rolling(252).max(), c.rolling(252).min()
    if arch == "BASE_COIL":
        rhi, rlo = c.rolling(60).max().shift(5), c.rolling(60).min().shift(5)
        return ((rhi-rlo)/((rhi+rlo)/2) < 0.20) & (c > rhi) & (c.shift(1) <= rhi.shift(1))        # breakout day from a tight base
    if arch == "MOMENTUM":
        return ((c-lo)/(hi-lo) > 0.90) & (c/c.shift(126)-1 > 0.20) & (c > s50) & (c/s50-1 < 0.15) & (s50 > s50.shift(10)) & (s200 > s200.shift(20))
    if arch == "NARRATIVE_SCARE":
        return (c.pct_change() <= -0.07) & (v/v.rolling(20).mean().shift(1) >= 2.5) & (c.shift(1) > s200.shift(1))
    if arch == "VALUE_DIVERGENCE":
        return (c/hi-1 <= -0.25) & (c > s20) & (c/c.shift(21)-1 > 0) & (c/c.shift(21)-1 <= 0.25)
    if arch == "MACRO_PUNISHED" and sec is not None:
        j = c.index.intersection(sec.index); cs, ss = c[j], sec[j]
        return ((cs/cs.shift(63)-ss/ss.shift(63)) < -0.10) & (cs < cs.rolling(50).mean()) & (ss > ss.rolling(50).mean())
    return None

def simulate(c, starts, T, S):
    """Each start: exit at +T (if any), at -S, or at the close HOLD sessions later. Close-based. Returns % results."""
    a = c.values; out = []
    for i in starts:
        if i+HOLD >= len(a): continue
        path = a[i+1:i+1+HOLD]/a[i]-1; res = path[-1]
        for r in path:
            if r <= -S: res = -S; break
            if T is not None and r >= T: res = T; break
        out.append(res*100)
    return np.array(out)

def thin(idx, gap=20):
    keep, last = [], -10**9
    for i in idx:
        if i-last >= gap: keep.append(i); last = i
    return keep

def rank_one(t, arch, f, x, sec):
    entry, stop, target = levels(f, arch)
    S = 1-stop/entry; T = (target/entry-1) if target else None
    r = dict(ticker=t, archetype=arch, entry_style=ENTRY_STYLE[arch], entry=round(entry, 2), stop=round(stop, 2),
             target=round(target, 2) if target else None, risk_pct=round(S*100, 1), reward_pct=round(T*100, 1) if T else None,
             rr=round(T/S, 2) if T else None)
    if T is not None and T <= 0.01: r.update(tier="PASS", reason="no room to the target"); return r
    c = x["close"]
    u = simulate(c, range(252, len(c)-HOLD, 5), T, S)                       # any day: this is the stock's drift
    sig = signal_days(x, arch, sec)
    cond = simulate(c, thin([i for i in np.flatnonzero(sig.values) if i >= 252]), T, S) if sig is not None else np.array([])
    n = len(cond)
    if len(u) < 50: r.update(tier="PASS", reason="not enough history"); return r
    ev_u = float(u.mean()); ev_c = float(cond.mean()) if n else None
    ev = (n*ev_c + 10*ev_u)/(n+10) if n else ev_u                           # shrink a small sample toward the stock's own drift
    r.update(n_setups=n, ev_any_day=round(ev_u, 2), ev_setup=round(ev_c, 2) if n else None, ev_used=round(ev, 2),
             edge_vs_drift=round(ev-ev_u, 2), win_any_day=round(float((u > 0).mean()*100), 0),
             win_setup=round(float((cond > 0).mean()*100), 0) if n else None, exp_R=round(ev/(S*100), 2))
    return r

def fundamentals(t):
    """Free Yahoo fields. Every piece is optional: a failure leaves it out rather than guessing."""
    out = {}
    try:
        import yfinance as yf
        tk = yf.Ticker(t)
        try:
            i = tk.info
            for k_out, k_in in (("fwd_pe", "forwardPE"), ("trail_pe", "trailingPE"), ("analysts", "numberOfAnalystOpinions"), ("mean_target", "targetMeanPrice")):
                if i.get(k_in) is not None: out[k_out] = round(float(i[k_in]), 2)
        except Exception: pass
        try:
            tr = tk.eps_trend
            row = tr.loc["+1y"]; cur = float(row["current"])
            if cur: out.update(eps_next_fy=round(cur, 2), rev30_pct=round((cur/float(row["30daysAgo"])-1)*100, 1), rev90_pct=round((cur/float(row["90daysAgo"])-1)*100, 1))
        except Exception: pass
        try:
            cal = tk.calendar; d = cal.get("Earnings Date") if isinstance(cal, dict) else None
            if d: out["next_earnings"] = str(d[0])
        except Exception: pass
    except Exception: pass
    return out

def tier(r, asof):
    if "tier" in r: return
    days = None
    if r.get("next_earnings"):
        try: days = int(np.busday_count(asof, r["next_earnings"]))
        except Exception: pass
    r["sessions_to_earnings"] = days
    why = []
    if r["exp_R"] < 0: r.update(tier="PASS", reason="negative expectancy on its own history"); return
    if r["rr"] is not None and r["rr"] < 1.0: why.append(f"pays {r['rr']} to 1")
    if r["edge_vs_drift"] <= 0: why.append("no edge over the stock's normal drift")
    if not r.get("n_setups"): why.append("no past examples to test")
    elif r["n_setups"] < 5: why.append(f"only {r['n_setups']} past examples")
    if r["archetype"] == "VALUE_DIVERGENCE" and r.get("rev30_pct") is not None and r["rev30_pct"] <= 0: why.append("estimates not rising")
    if r["archetype"] == "MOMENTUM" and r.get("rev30_pct") is not None and r["rev30_pct"] < 0: why.append("estimates falling")
    if days is not None and 0 <= days <= 3: why.append(f"earnings in {days} sessions")
    hard = [w for w in why if not w.startswith("only ")]
    if not hard and r["exp_R"] >= 0.25: r.update(tier="DEEP DIVE", reason="; ".join(why) or "passes every scripted test")
    elif r["exp_R"] >= 0.10 and len(hard) <= 1: r.update(tier="WATCH", reason="; ".join(why) or "thin expectancy")
    else: r.update(tier="PASS", reason="; ".join(why) or "thin expectancy")

def rank_all(cands, feats, bars, asof, live):
    rows = []
    for arch, lst in cands.items():
        for score, t, why in lst[:RANK_POOL]:
            f = feats[t]; sec = bars.get(SECTOR_ETF.get(f.get("sector") or "", ""))
            try:
                r = rank_one(t, arch, f, bars[t], sec["close"] if sec is not None else None)
            except Exception as e:
                r = dict(ticker=t, archetype=arch, tier="PASS", reason=f"rank error {type(e).__name__}")
            r.update(name=f.get("name"), sector=f.get("sector"), index=f.get("index"), last=f["last"], screen_why=why)
            rows.append(r)
    if live:
        for r in rows:
            if "exp_R" in r and r["exp_R"] >= 0.05: r.update(fundamentals(r["ticker"]))
    for r in rows: tier(r, asof)
    order = {"DEEP DIVE": 0, "WATCH": 1, "PASS": 2}
    rows.sort(key=lambda r: (order[r["tier"]], -(r.get("exp_R") or -9)))
    return rows

# ----------------------------------------------------------------------------- outcome tracking
def track(out, survivors, bars, asof):
    """Log each survivor the first time it appears (once per 20 sessions), then score every logged call
    against SPY at 5, 20 and 40 sessions. This is what tells us whether an archetype is worth keeping."""
    hp = out/"history.csv"
    hist = pd.read_csv(hp, dtype=str) if hp.exists() else pd.DataFrame(columns=["date", "ticker", "archetype", "rank", "entry"])
    spy = bars.get("SPY"); cal = [str(d.date()) for d in spy.index] if spy is not None else []
    recent = set(cal[-20:])
    seen = {(r.ticker, r.archetype) for r in hist.itertuples() if r.date in recent}
    new = [dict(date=asof, ticker=s["ticker"], archetype=s["archetype"], rank=str(s["rank"]), entry=str(s["last"]))
           for s in survivors if (s["ticker"], s["archetype"]) not in seen]
    if new: hist = pd.concat([hist, pd.DataFrame(new)], ignore_index=True)
    hist.to_csv(hp, index=False)
    rows = []
    for r in hist.itertuples():
        if r.ticker not in bars or r.date not in cal: continue
        c = bars[r.ticker]["close"]; idx = [str(d.date()) for d in c.index]
        if r.date not in idx: continue
        i, j = idx.index(r.date), cal.index(r.date)
        for h in (5, 20, 40):
            if i+h < len(c) and j+h < len(cal):
                rows.append((r.archetype, h, (c.iloc[i+h]/c.iloc[i]-1)*100 - (spy["close"].iloc[j+h]/spy["close"].iloc[j]-1)*100))
    sc = {}
    if rows:
        d = pd.DataFrame(rows, columns=["a", "h", "x"])
        for (a_, h), g in d.groupby(["a", "h"]):
            sc.setdefault(a_, {})[f"{h}d"] = dict(n=int(len(g)), mean_excess=round(float(g.x.mean()), 2), pct_beat_spy=round(float((g.x > 0).mean()*100), 0))
    return dict(calls_logged=int(len(hist)), by_archetype=sc, note="excess return vs SPY from the close of the day first flagged; n under 25 is noise")

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--csv-dir"); ap.add_argument("--out", default="out"); ap.add_argument("--no-charts", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); (out/"charts").mkdir(parents=True, exist_ok=True)
    if a.csv_dir:
        bars = pull_csv(a.csv_dir); meta = {t: dict(name=t, sector=None, industry=None) for t in bars}
    else:
        meta = load_universe(); bars = pull_yf(sorted(set(meta) | set(BENCH)))
    spy = bars["SPY"]["close"] if "SPY" in bars else None
    feats = {t: features(t, x, spy) for t, x in bars.items()}
    dates = pd.Series([f["date"] for f in feats.values()]); asof = dates.mode().iloc[0]
    survivors, counts, dropped = [], {}, {}
    def drop(why): dropped[why] = dropped.get(why, 0) + 1
    cands = {k: [] for k, _ in RULES}; cands["MACRO_PUNISHED"] = []
    for t, f in feats.items():
        f.update(meta.get(t, {}))
        if t in BENCH: continue
        if "skip" in f: drop(f["skip"]); continue
        if f["date"] != asof: drop("stale last bar"); continue
        if f["last"] < MIN_PRICE or f["dvol20"] < MIN_DVOL: drop("liquidity gate"); continue
        if "suspect" in f: drop("suspect data"); continue
        if f["compression"] < 0.3: drop("deal-pinned (ATR under 0.3x of 2m ago)"); f["skip"] = "deal-pinned"; continue
        for k, rule in RULES:
            r = rule(f)
            if r: cands[k].append((r[0], t, r[1]))
        sec = feats.get(SECTOR_ETF.get(f.get("sector") or "", ""))
        r = a_macro(f, sec if sec and "skip" not in sec else None)
        if r: cands["MACRO_PUNISHED"].append((r[0], t, r[1]))
    classified = {t for lst in cands.values() for _, t, _ in lst}
    cands["UNCLASSIFIED"] = []
    for t, f in feats.items():
        if t in BENCH or t in classified or "skip" in f or "suspect" in f or f["date"] != asof or f["last"] < MIN_PRICE or f["dvol20"] < MIN_DVOL: continue
        r = a_unclassified(f)
        if r: cands["UNCLASSIFIED"].append((r[0], t, r[1]))
    keep = ["ticker", "name", "index", "sector", "industry", "last", "d1", "w1", "m1", "m3", "m6", "vs50", "vs200", "rsi", "pos52", "dd52", "volx",
            "rs3", "rs6", "bbw_pct", "pivot", "base_low", "dist_pivot", "worst_day", "worst_day_date"]
    for k, lst in cands.items():
        lst.sort(reverse=True); counts[k] = len(lst)
        for rank, (score, t, why) in enumerate(lst[:PER_ARCHETYPE], 1):
            f = feats[t]
            survivors.append(dict(archetype=k, rank=rank, of=len(lst), score=round(float(score), 1), why=why, chart=f"charts/{t}_{k}.png",
                                  **{x: f.get(x) for x in keep}))
            if not a.no_charts: chart(t, bars[t], f, k, out/"charts"/f"{t}_{k}.png")
    ranked = rank_all(cands, feats, bars, asof, live=not a.csv_dir)
    scorecard = track(out, survivors, bars, asof)
    bench = {t: {x: feats[t].get(x) for x in ("last", "d1", "w1", "m1", "m3", "vs50", "vs200", "rsi", "pos52")} for t in BENCH if t in feats and "skip" not in feats[t]}
    ok = [f for f in feats.values() if "skip" not in f]
    breadth = dict(n=len(ok), pct_above_50d=round(float(np.mean([f["vs50"] > 0 for f in ok])*100), 1),
                   pct_above_200d=round(float(np.mean([f["vs200"] > 0 for f in ok])*100), 1),
                   pct_rsi_under_30=round(float(np.mean([f["rsi"] < 30 for f in ok])*100), 1),
                   pct_within_5_of_52w_high=round(float(np.mean([f["dd52"] > -5 for f in ok])*100), 1))
    (out/"screen_output.json").write_text(json.dumps(dict(
        asof=asof, generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), universe=len(feats), candidates_per_archetype=counts,
        dropped=dropped, universe_note="; ".join(UNIVERSE_NOTE), scorecard=scorecard, ranked=ranked, breadth=breadth, benchmarks=bench, survivors=survivors,
        notes="Prices are raw split-adjusted closes (dividends not added back). ranked[] simulates each setup's own stop, target and 60-session time stop on the stock's 10-year history, against the same trade taken on any day (the drift). Estimates and earnings dates are from Yahoo when available. MACRO_PUNISHED names no driver; research must."), indent=1))
    (out/"market_state_full.json").write_text(json.dumps(feats, indent=0, sort_keys=True))
    print(f"asof {asof} universe {len(feats)} dropped {dropped} candidates {counts} survivors {len(survivors)} breadth {breadth}")
    print(f"RANKED {len(ranked)}: " + ", ".join(f"{k} {sum(1 for r in ranked if r['tier']==k)}" for k in ("DEEP DIVE", "WATCH", "PASS")))
    for r in ranked:
        if r["tier"] != "PASS": print(f"  {r['tier']:9} {r['ticker']:6} {r['archetype'][:10]:10} expR {r.get('exp_R')} ev {r.get('ev_used')} vs drift {r.get('ev_any_day')} n {r.get('n_setups')} rr {r.get('rr')} | {r.get('reason')}")
    for s in survivors: print(f"  {s['archetype']:17} #{s['rank']}/{s['of']:<3} {s['ticker']:6} {s['why']}")

if __name__ == "__main__":
    main()
