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
HOLD = 120                 # sessions (~6 months): time stop in every simulated trade. The book holds weeks to quarters.
PRICE_CAP = 60             # book rule (11 Oct): a delta 0.75-0.85 call 6-15 months out costs ~30-40% of the stock; ~$1,900 per slot caps the stock near $60
EARNINGS_WINDOW = 15       # sessions: a name reporting inside this window is researched as a post-print trigger, not an entry
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
    f["atr14"] = float(atr.iloc[-1])
    f.update(pivot=round(rhi, 2), base_low=round(rlo, 2), tightness=(rhi-rlo)/((rhi+rlo)/2),
             compression=float(atr.iloc[-1]/atr.iloc[-43]), dryup=float(v.tail(20).mean()/v.iloc[-60:-20].mean()),
             dist_pivot=(last/rhi-1)*100)
    f.update(s50=float(s50.iloc[-1]), s200=float(s200.iloc[-1]), hi52c=hi52, min20=float(c.tail(20).min()),
             pivot_c=float(c.iloc[-65:-5].max()), base_low_c=float(c.iloc[-65:-5].min()))
    bbw = 4*c.rolling(20).std()/s20
    f["bbw_pct"] = float((bbw.tail(504) < bbw.iloc[-1]).mean()*100)      # percentile of today's bandwidth, 2y
    # scare: worst single session inside the last 10, with its volume multiple and the trend before it
    ret = c.pct_change()*100
    kb = int(np.argmax(ret.tail(5).values)); pb = n-5+kb
    f.update(best_day=float(ret.iloc[pb]), best_day_date=str(c.index[pb].date()), best_day_volx=float(v.iloc[pb]/v.iloc[pb-20:pb].mean()),
             pre_gap_close=float(c.iloc[pb-1]), gap_close=float(c.iloc[pb]))
    k = int(np.argmin(ret.tail(10).values)); pos = n-10+k
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

def a_recovery(f):   # added 10 Oct 2026: the only pattern with pooled evidence. Strong vs SPY, still well off its high, long trend rising.
    if not (f.get("rs3", 0) >= 25 and f["dd52"] <= -15 and f["vs200"] > 0 and f["slope200"] > 0): return None
    return f.get("rs3", 0) - max(f["vs50"]-10, 0), f"+{f.get('rs3', 0):.0f}pts vs SPY in 3m, still {f['dd52']:.0f}% off the 52w high, {f['vs200']:+.0f}% over a rising 200d, {f['vs50']:+.1f}% vs the 50d"

def a_gap(f):   # candidate, added 11 Oct 2026: a big up-day on heavy volume in the last 5 sessions that has held. Earnings-drift style.
    if not (f["best_day"] >= 5 and f["best_day_volx"] >= 2.5 and f["last"] >= f["gap_close"]*0.97): return None
    return f["best_day"]*f["best_day_volx"], f"+{f['best_day']:.1f}% on {f['best_day_date']} at {f['best_day_volx']:.1f}x volume and holding ({(f['last']/f['gap_close']-1)*100:+.1f}% since)"

def a_unclassified(f):   # fits no archetype but the tape did something unusual. This is where new archetypes come from.
    hit = []
    if abs(f["d1"]) >= 5 and f["volx"] >= 2.5: hit.append(f"{f['d1']:+.1f}% on {f['volx']:.1f}x volume")
    if f["pos52"] >= 99 and f["volx"] >= 2: hit.append(f"52w high on {f['volx']:.1f}x volume")
    if f["pos52"] <= 1 and f["volx"] >= 2: hit.append(f"52w low on {f['volx']:.1f}x volume")
    if abs(f["vs200"]) < 1 and abs(f["w1"]) >= 6: hit.append(f"crossed the 200d with a {f['w1']:+.1f}% week")
    if f["bbw_pct"] <= 2: hit.append(f"tightest 20d range in 2 years ({f['bbw_pct']:.0f}th pct)")
    if not hit: return None
    return abs(f["d1"])*max(f["volx"], 1) + 10*len(hit), "; ".join(hit)

RULES = [("RECOVERY_LEADER", a_recovery), ("EVENT_GAP_UP", a_gap), ("BASE_COIL", a_base), ("MOMENTUM", a_momentum), ("NARRATIVE_SCARE", a_scare), ("VALUE_DIVERGENCE", a_value_div)]

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
ENTRY_STYLE = {"RECOVERY_LEADER": "strength", "EVENT_GAP_UP": "strength", "BASE_COIL": "confirmation", "MOMENTUM": "confirmation", "NARRATIVE_SCARE": "weakness", "VALUE_DIVERGENCE": "weakness",
               "MACRO_PUNISHED": "weakness", "UNCLASSIFIED": "none"}

def levels(f, arch):
    """Entry, stop, target from raw closes. Target None = no natural target; exit is the stop or the time stop."""
    last = f["last"]; floor20 = f["min20"]*0.98
    if arch == "RECOVERY_LEADER":
        return last, (f["s200"] if 0.06 <= 1-f["s200"]/last <= 0.25 else last*0.85), f["hi52c"]
    if arch == "EVENT_GAP_UP":
        return last, max(f["pre_gap_close"]*0.99, last*0.90), None
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

TARGET_BASIS = {"RECOVERY_LEADER": "the 52-week closing high", "EVENT_GAP_UP": "none: stop just under the pre-gap close, or the time stop", "BASE_COIL": "pivot plus the height of the base", "MOMENTUM": "none: stop or time stop only",
                "NARRATIVE_SCARE": "the close before the event", "VALUE_DIVERGENCE": "the 200-day if it is 5%+ above, else halfway back to the 52-week high",
                "MACRO_PUNISHED": "12% above entry (half the typical lag)", "UNCLASSIFIED": "none: stop or time stop only"}

def signal_days(x, arch, sec=None, spy=None):
    """Boolean series: the days in this stock's past when the same archetype condition was true."""
    c, v = x["close"], x["volume"]
    s20, s50, s200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    hi, lo = c.rolling(252).max(), c.rolling(252).min()
    if arch == "RECOVERY_LEADER" and spy is not None:
        j = c.index.intersection(spy.index); cs, ss = c[j], spy[j]; l200 = cs.rolling(200).mean()
        return ((cs/cs.shift(63)-ss/ss.shift(63)) >= 0.25) & (cs/cs.rolling(252).max()-1 <= -0.15) & (cs > l200) & (l200 > l200.shift(20))
    if arch == "EVENT_GAP_UP":
        return (c.pct_change() >= 0.05) & (v/v.rolling(20).mean().shift(1) >= 2.5)
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
    """Each start: exit at +T (if any), at the first WEEKLY close below -S (taken at that close, so gaps count), or at the close HOLD sessions later."""
    a = c.values; out = []
    for i in starts:
        if i+HOLD >= len(a): continue
        path = a[i+1:i+1+HOLD]/a[i]-1; res = path[-1]
        for k, r in enumerate(path):
            if (k+1) % 5 == 0 and r <= -S: res = r; break                       # stop tested on weekly closes only, exit at that close
            if T is not None and r >= T: res = T; break
        out.append(res*100)
    return np.array(out)

def thin(idx, gap=20):
    keep, last = [], -10**9
    for i in idx:
        if i-last >= gap: keep.append(i); last = i
    return keep

def rank_one(t, arch, f, x, sec, spy=None):
    entry, stop, target = levels(f, arch)
    S = 1-stop/entry; T = (target/entry-1) if target else None
    r = dict(ticker=t, archetype=arch, entry_style=ENTRY_STYLE[arch], entry=round(entry, 2), stop=round(stop, 2),
             target=round(target, 2) if target else None, risk_pct=round(S*100, 1), reward_pct=round(T*100, 1) if T else None,
             rr=round(T/S, 2) if T else None, target_basis=TARGET_BASIS.get(arch),
             shares_per_100_risk=round(100/(entry-stop), 2) if entry > stop else None,
             position_per_100_risk=round(100/(entry-stop)*entry, 0) if entry > stop else None)
    if T is not None and T <= 0.01: r.update(tier="PASS", reason="no room to the target"); return r
    c = x["close"]
    u = simulate(c, range(252, len(c)-HOLD, 5), T, S)                       # any day: this is the stock's drift
    sig = signal_days(x, arch, sec, spy)
    if sig is not None: sig = sig.reindex(c.index).fillna(False)
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

def entry_quality(r, f, days_to_event=None):
    """Is TODAY'S price a good place to open a multi-week to multi-quarter position, given the written invalidation
    and target? 0-100, grade A/B/C. Short-term timing (ATR, RSI, distance from the 20-day) is deliberately NOT scored:
    this book holds deep in-the-money calls for months. Option fit (extrinsic cost, expiry, spread) is scored in research."""
    last, stop, tgt = f["last"], r.get("stop"), r.get("target")
    if not stop or stop >= last: return dict(entry_score=None, entry_grade="n/a", entry_note="invalidation at or above price")
    risk = last-stop; pts = {}; notes = []
    if tgt and tgt > last:
        rr = (tgt-last)/risk
        pts["reward_to_invalidation"] = 35 if rr >= 3 else 25 if rr >= 2 else 12 if rr >= 1.5 else 0
        r["limit_for_2R"] = round((tgt+2*stop)/3, 2)
        if rr < 2: notes.append(f"pays {rr:.1f} to 1 from here; limit {r['limit_for_2R']} for 2 to 1")
    else:
        e = r.get("exp_R") or 0; pts["reward_to_invalidation"] = 35 if e >= 0.5 else 25 if e >= 0.3 else 12 if e >= 0.15 else 0
    chase = (last/r["entry"]-1)*100 if r.get("entry") else 0
    pts["not_chasing"] = 20 if chase <= 1 else 12 if chase <= 4 else 5 if chase <= 8 else 0
    if chase > 4: notes.append(f"{chase:.1f}% above the planned entry")
    room = risk/last*100        # an ITM call needs room: too close and normal swings end the thesis, too far and the loss is large
    pts["room_to_invalidation"] = 15 if 8 <= room <= 20 else 8 if 5 <= room < 8 or 20 < room <= 30 else 0
    if room < 5: notes.append(f"invalidation only {room:.1f}% away: too tight for a months-long hold")
    if room > 30: notes.append(f"invalidation {room:.0f}% away: the call would lose most of its value before the thesis is wrong")
    trend = f.get("vs200", 0) > 0 and f.get("slope200", 0) > 0
    pts["long_trend_with_you"] = 10 if trend else 4 if f.get("slope200", 0) > 0 or f.get("vs200", 0) > 0 else 0
    score = round(sum(pts.values())/80*100)
    return dict(entry_score=score, entry_grade="A" if score >= 75 else "B" if score >= 55 else "C",
                entry_room_pct=round(room, 1), entry_points=pts, entry_note="; ".join(notes))

def tier(r, asof, bt=None):
    if "tier" in r: return
    pooled = (bt or {}).get(r["archetype"])
    if pooled:
        r["pooled_edge120"] = pooled["e120"]["edge"]; r["pooled_t"] = pooled["e120"]["t_clustered"]
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
    cap = False
    if pooled and pooled.get("verdict") == "HURTS":
        why.append(f"this archetype has done worse than ordinary days across all stocks (6-month edge {pooled['e120']['edge']:+.1f}, t {pooled['e120']['t_clustered']})")
    elif pooled and pooled.get("verdict") != "WORKS":
        cap = True; r["note"] = f"archetype not yet shown to beat ordinary days (6-month edge {pooled['e120']['edge']:+.1f}, t {pooled['e120']['t_clustered']}): capped at WATCH"
    hard = [w for w in why if not w.startswith("only ")]
    if not hard and not cap and r["exp_R"] >= 0.25: r.update(tier="DEEP DIVE", reason="; ".join(why) or "passes every scripted test")
    elif r["exp_R"] >= 0.10 and len(hard) <= 1: r.update(tier="WATCH", reason="; ".join(why) or r.get("note") or "thin expectancy")
    else: r.update(tier="PASS", reason="; ".join(why) or "thin expectancy")
    if days is not None and 0 <= days <= EARNINGS_WINDOW and r["tier"] in ("DEEP DIVE", "WATCH"):
        r["earnings_window"] = True
        if r["tier"] == "DEEP DIVE":
            r.update(tier="AFTER PRINT", reason=f"passes, but reports in {days} sessions ({r['next_earnings']}): write the trigger now, enter after the print")

def rank_all(cands, feats, bars, asof, live, bt=None):
    rows, fcache = [], {}
    def fund(t):
        if t not in fcache: fcache[t] = fundamentals(t) if live else {}
        return fcache[t]
    spy3 = feats.get("SPY", {}).get("m3")
    for arch, lst in cands.items():
        pool = lst[:RANK_POOL]
        if arch == "VALUE_DIVERGENCE" and live:
            # the archetype is "estimates rising while price is down": pull revisions for the whole list and let them choose
            wide = [(fund(t).get("rev30_pct"), score, t, why) for score, t, why in lst[:60]]
            kept = [w for w in wide if w[0] is None or w[0] > 0]
            kept.sort(key=lambda w: (-(w[0] if w[0] is not None else -1), -w[1]))
            pool = [(score, t, why + (f" Estimates {rev:+.1f}% in 30 days." if rev is not None else " Estimates not available.")) for rev, score, t, why in kept[:RANK_POOL]]
        for score, t, why in pool:
            f = feats[t]; etf = SECTOR_ETF.get(f.get("sector") or "", ""); sec = bars.get(etf)
            try:
                r = rank_one(t, arch, f, bars[t], sec["close"] if sec is not None else None, bars["SPY"]["close"] if "SPY" in bars else None)
            except Exception as e:
                r = dict(ticker=t, archetype=arch, tier="PASS", reason=f"rank error {type(e).__name__}")
            r.update(name=f.get("name"), sector=f.get("sector"), index=f.get("index"), last=f["last"], screen_why=why)
            sm3 = feats.get(etf, {}).get("m3")
            if sm3 is not None and spy3 is not None: r["sector_vs_spy_3m"] = round(sm3-spy3, 1)
            rows.append(r)
    if live:
        for r in rows:
            if "exp_R" in r and r["exp_R"] >= 0.05: r.update(fund(r["ticker"]))
    for r in rows:
        tier(r, asof, bt)
        if r["tier"] != "PASS" and "stop" in r:
            r.update(entry_quality(r, feats[r["ticker"]], r.get("sessions_to_earnings")))
    for r in rows:
        if r.get("last") and r["last"] > PRICE_CAP and r["tier"] in ("DEEP DIVE", "AFTER PRINT", "WATCH"):
            r.update(tier="TOO EXPENSIVE", reason=f"stock {r['last']} above the ${PRICE_CAP} cap: no deep ITM call fits a ~$1,900 slot (was {r['tier']}: {r.get('reason', '')})")
    order = {"DEEP DIVE": 0, "AFTER PRINT": 1, "WATCH": 2, "TOO EXPENSIVE": 3, "PASS": 4}
    rows.sort(key=lambda r: (order[r["tier"]], -(r.get("exp_R") or -9)))
    return rows

# ----------------------------------------------------------------------------- pooled backtest: does an archetype beat drift at all?
def extra_signals(x, arch, spy):
    """Candidate patterns proposed by research, tested before they are adopted."""
    c, v = x["close"], x["volume"]
    if arch == "GAP_UP_ON_VOLUME":
        return (c.pct_change() >= 0.08) & (v/v.rolling(20).mean().shift(1) >= 3)
    return None

def backtest(bars, feats, universe):
    """Every past signal, every stock, 10 years. Result = return over the next 60 and 120 sessions (about 3 and 6 months, the holding period of this book) MINUS SPY over the
    same sessions. Baseline = the same measure on ordinary days in the same stocks.
    Tightened 10 Oct 2026: results trimmed at the 1st and 99th percentile of the baseline (one bad print cannot carry an
    average); medians and beat rates shown against the baseline's; and the t-statistic is clustered by calendar month,
    because signals bunch up after sell-offs and are not independent."""
    spy = bars["SPY"]["close"]; out = {}
    archs = ["RECOVERY_LEADER", "EVENT_GAP_UP", "BASE_COIL", "MOMENTUM", "NARRATIVE_SCARE", "VALUE_DIVERGENCE", "MACRO_PUNISHED"]
    spy_up = (spy > spy.rolling(200).mean())
    acc = {a: [] for a in archs}; base = []
    for t in universe:
        x = bars.get(t)
        if x is None or len(x) < 400 or t in BENCH: continue
        c = x["close"]; j = c.index.intersection(spy.index)
        if len(j) < 400: continue
        cs, ss = c[j], spy[j]
        e60 = ((cs.shift(-60)/cs-1) - (ss.shift(-60)/ss-1)).values*100; e120 = ((cs.shift(-120)/cs-1) - (ss.shift(-120)/ss-1)).values*100
        ym = (cs.index.year*100 + cs.index.month).values
        secbar = bars.get(SECTOR_ETF.get((feats.get(t) or {}).get("sector") or "", ""))
        mk = spy_up.reindex(cs.index).fillna(False).values.astype(int)                       # 1 = SPY above its 200-day on the signal day
        if secbar is not None:
            sc = secbar["close"].reindex(cs.index).ffill()
            sk = ((sc/sc.shift(63) - ss/ss.shift(63)) > 0).values.astype(int)                 # 1 = the stock's sector beat SPY over the prior 3 months
        else:
            sk = np.full(len(cs), -1)
        for i in range(252, len(cs)-120, 10): base.append((e60[i], e120[i], ym[i], mk[i], sk[i]))
        for a in archs:
            try:
                sig = signal_days(x, a, secbar["close"] if secbar is not None else None, spy) if a in ENTRY_STYLE else extra_signals(x, a, spy)
            except Exception:
                sig = None
            if sig is None: continue
            sig = sig.reindex(cs.index).fillna(False).values
            for i in thin([k for k in np.flatnonzero(sig) if 252 <= k < len(cs)-120]): acc[a].append((e60[i], e120[i], ym[i], mk[i], sk[i]))
    COLS = ["e60", "e120", "ym", "mkt", "sec"]
    b = pd.DataFrame(base, columns=COLS).dropna()
    clip = {h: (float(b[h].quantile(0.01)), float(b[h].quantile(0.99))) for h in ("e60", "e120")}
    for h in clip: b[h] = b[h].clip(*clip[h])
    mid = int(b.ym.median())
    bm = {h: b.groupby("ym")[h].mean() for h in ("e60", "e120")}
    def stat(d):
        r = {"n": int(len(d)), "months_with_signals": int(d.ym.nunique())}
        for h in ("e60", "e120"):
            d[h] = d[h].clip(*clip[h])
            m = float(d[h].mean()); base_m = float(b[h].mean())
            pm = (d.groupby("ym")[h].mean() - bm[h]).dropna()                    # one observation per month: signal mean minus that month's ordinary days
            tc = float(pm.mean()/(pm.std()/np.sqrt(len(pm)))) if len(pm) > 5 and pm.std() > 0 else None
            r[h] = dict(mean_excess=round(m, 2), baseline=round(base_m, 2), edge=round(m-base_m, 2),
                        edge_month_matched=round(float(pm.mean()), 2) if len(pm) else None, t_clustered=round(tc, 1) if tc is not None else None,
                        pct_months_positive=round(float((pm > 0).mean()*100), 0) if len(pm) else None,
                        median=round(float(d[h].median()), 2), baseline_median=round(float(b[h].median()), 2),
                        pct_beat_spy=round(float((d[h] > 0).mean()*100), 0), baseline_pct_beat_spy=round(float((b[h] > 0).mean()*100), 0))
        f1, f2 = d[d.ym <= mid], d[d.ym > mid]
        r["edge120_first_half"] = round(float(f1.e120.mean() - b[b.ym <= mid].e120.mean()), 2) if len(f1) else None
        r["edge120_second_half"] = round(float(f2.e120.mean() - b[b.ym > mid].e120.mean()), 2) if len(f2) else None
        cond = {}
        for label, col, val in (("spy_above_200d", "mkt", 1), ("spy_below_200d", "mkt", 0), ("sector_leading", "sec", 1), ("sector_lagging", "sec", 0)):
            ds, bs = d[d[col] == val], b[b[col] == val]
            if len(ds) >= 30 and len(bs) >= 30:
                pmc = (ds.groupby("ym").e120.mean() - bs.groupby("ym").e120.mean()).dropna()
                tcc = float(pmc.mean()/(pmc.std()/np.sqrt(len(pmc)))) if len(pmc) > 5 and pmc.std() > 0 else None
                cond[label] = dict(n=int(len(ds)), edge120=round(float(ds.e120.mean()-bs.e120.mean()), 2), t_clustered=round(tcc, 1) if tcc is not None else None)
        r["by_condition"] = cond
        e = r["e120"]
        r["verdict"] = ("WORKS" if (e["t_clustered"] or 0) >= 2 and e["edge"] > 0 and (r["edge120_first_half"] or 0) > 0 and (r["edge120_second_half"] or 0) > 0
                        else "HURTS" if (e["t_clustered"] or 0) <= -2 and e["edge"] < 0 else "NOT SHOWN")
        return r
    for a in archs:
        d = pd.DataFrame(acc[a], columns=COLS).dropna()
        if len(d) >= 30: out[a] = stat(d)
    out["_baseline"] = dict(n=int(len(b)), mean_excess_60=round(float(b.e60.mean()), 2), mean_excess_120=round(float(b.e120.mean()), 2),
                            median_120=round(float(b.e120.median()), 2), pct_beat_spy_120=round(float((b.e120 > 0).mean()*100), 0), split_month=mid, trim=clip)
    out["_now"] = dict(spy_above_200d=bool(spy_up.iloc[-1]),
                       sectors_leading=sorted(e for e in set(SECTOR_ETF.values()) if e in bars and len(bars[e]) > 70 and
                                              (bars[e]["close"].iloc[-1]/bars[e]["close"].iloc[-64] - spy.iloc[-1]/spy.iloc[-64]) > 0))
    out["_note"] = ("Horizons are 60 and 120 sessions because the book holds for weeks to quarters. Excess return vs SPY after every past signal, all stocks pooled, signals at least 20 sessions apart per stock, results trimmed at the "
                    "baseline's 1st/99th percentile. edge = signal mean minus ordinary-day mean. t_clustered treats each calendar month as one observation. "
                    "WORKS = clustered t of 2 or more and positive in both halves. by_condition splits each archetype by whether SPY was above its 200-day and whether the stock's sector was beating SPY on the signal day: a condition is a candidate filter only if its edge and t are clearly better than the other side. Still uncorrected: survivorship (today's index members only, which flatters "
                    "anything that buys a fallen stock), no stops, no costs.")
    return out

# ----------------------------------------------------------------------------- survivorship test for RECOVERY_LEADER (added 11 Oct 2026)
DRIFT_RESULT = {}
DRIFT_STATS = {}    # v14: how many quarters qualified, lacked an 8-K date, failed the reaction test, became events
DRIFT_DETAIL = []   # one dict per earnings-drift event with the conditioning variables known at entry
LAST_EVENTS = {}   # lens events from the latest lens_tests run, reused to list today's candidates
FORMER_BARS = {}   # prices for former S&P 500 members, filled by survivorship_test and reused by the lens tests
SP500_HIST_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv"

def load_membership():
    raw = urllib.request.urlopen(SP500_HIST_URL, timeout=60).read().decode()
    m = pd.read_csv(io.StringIO(raw), parse_dates=["date"]).sort_values("date")
    m["set"] = m["tickers"].map(lambda x: set(t.strip().replace(".", "-") for t in str(x).split(",")))
    return m[["date", "set"]].reset_index(drop=True)

def survivorship_test(bars, feats, live):
    """Does the recovery-leader edge survive point-in-time index membership? Five checks, all on S&P 500 history:
    A current_members: today's S&P 500 names only, signals on any date (the original, biased test)
    B point_in_time: only signals where the stock WAS in the S&P 500 on the signal date (removes stocks added after recovering)
    C with_dropouts: B plus former members no longer in the index, wherever Yahoo still has prices (partial fix for stocks that fell out)
    D ex_2020_21: C without signals from Mar 2020 to Dec 2021
    E by_index: today's S&P 500 vs S&P 400 members, original method
    Each: mean 120-session return vs SPY after the signal, minus the same on ordinary days in the same stocks, trimmed at
    the baseline's 1st/99th percentile, t clustered by month."""
    out = {}
    try:
        mem = load_membership()
    except Exception as e:
        return {"_error": f"membership download failed: {type(e).__name__}: {str(e)[:100]}"}
    dates = mem["date"].values
    def member(t, d):
        i = np.searchsorted(dates, np.datetime64(d), side="right") - 1
        return i >= 0 and t in mem["set"].iloc[i]
    spy = bars["SPY"]["close"]
    ever = set().union(*mem[mem["date"] >= spy.index[0]]["set"])
    dropped = sorted(t for t in ever if t not in bars and "." not in t)
    extra = {}
    if live and dropped:
        try: extra = pull_yf(dropped)
        except Exception: extra = {}
    FORMER_BARS.update(extra)
    out["former_members_in_window"] = len(dropped); out["former_members_with_prices"] = len(extra)
    def collect(tickers, source, pit):
        sig, base = [], []
        for t in tickers:
            x = source.get(t)
            if x is None or len(x) < 400 or t in BENCH: continue
            c = x["close"]; j = c.index.intersection(spy.index)
            if len(j) < 400: continue
            cs, ss = c[j], spy[j]
            e = ((cs.shift(-120)/cs-1) - (ss.shift(-120)/ss-1)).values*100
            ym = (cs.index.year*100 + cs.index.month).values
            for i in range(252, len(cs)-120, 10):
                if not pit or member(t, cs.index[i]): base.append((e[i], ym[i], t))
            try: sg = signal_days(x.loc[j], "RECOVERY_LEADER", None, spy).reindex(cs.index).fillna(False).values
            except Exception: continue
            for i in thin([k for k in np.flatnonzero(sg) if 252 <= k < len(cs)-120]):
                if not pit or member(t, cs.index[i]): sig.append((e[i], ym[i], t))
        return pd.DataFrame(sig, columns=["e", "ym", "t"]).dropna(), pd.DataFrame(base, columns=["e", "ym", "t"]).dropna()
    def score(d, b, label):
        if len(d) < 30 or len(b) < 100: return dict(test=label, n=int(len(d)), note="too few signals")
        lo, hi = float(b.e.quantile(0.01)), float(b.e.quantile(0.99)); d = d.assign(e=d.e.clip(lo, hi)); b = b.assign(e=b.e.clip(lo, hi))
        pm = (d.groupby("ym").e.mean() - b.groupby("ym").e.mean()).dropna()
        t = float(pm.mean()/(pm.std()/np.sqrt(len(pm)))) if len(pm) > 5 and pm.std() > 0 else None
        return dict(test=label, n=int(len(d)), stocks=int(d.t.nunique()), months=int(pm.size), edge120=round(float(d.e.mean()-b.e.mean()), 2),
                    t_clustered=round(t, 1) if t is not None else None, median=round(float(d.e.median()), 2), baseline_median=round(float(b.e.median()), 2),
                    pct_beat_spy=round(float((d.e > 0).mean()*100), 0), baseline_pct_beat_spy=round(float((b.e > 0).mean()*100), 0))
    sp5 = [t for t, f in feats.items() if f.get("index") == "SP500"]
    sp4 = [t for t, f in feats.items() if f.get("index") == "SP400"]
    a_s, a_b = collect(sp5, bars, False); out["A_current_members"] = score(a_s, a_b, "today's S&P 500 members, any date (original, biased)")
    b_s, b_b = collect(sp5, bars, True); out["B_point_in_time"] = score(b_s, b_b, "only signals while the stock was in the S&P 500")
    allsrc = dict(bars); allsrc.update(extra)
    c_s, c_b = collect(sp5 + list(extra), allsrc, True); out["C_with_dropouts"] = score(c_s, c_b, "B plus former members Yahoo still has")
    keep = ~c_s.ym.between(202003, 202112); keepb = ~c_b.ym.between(202003, 202112)
    out["D_ex_2020_21"] = score(c_s[keep], c_b[keepb], "C without Mar 2020 to Dec 2021")
    e_s, e_b = collect(sp4, bars, False); out["E_sp400_today"] = score(e_s, e_b, "today's S&P 400 members, any date")
    yr = {}
    if len(c_s):
        for y, g in c_s.assign(y=c_s.ym//100).groupby("y"):
            bb = c_b[c_b.ym//100 == y]
            if len(g) >= 10 and len(bb) >= 50: yr[int(y)] = dict(n=int(len(g)), edge120=round(float(g.e.mean()-bb.e.mean()), 2))
    out["C_by_year"] = yr
    out["_read"] = ("If the edge in B and C is close to A, survivorship was not driving it. If it shrinks toward zero in B or C, it was. "
                    "C is still incomplete: former members Yahoo no longer carries are missing, and those are disproportionately the failures.")
    return out

# ----------------------------------------------------------------------------- fundamental lens tests (added 11 Oct 2026)
# Data: SEC XBRL "frames" (one call per concept per period, every filer at once), keyed on CIK. Entry dates are set so the
# fundamental data was public: quarter end + 45 days for SEC-based signals (10-Q deadline 40 days for large filers), or the
# detected announcement day + 1 for earnings drift. Every test reports all stocks AND the point-in-time S&P 500 subset.
SEC_UA = __import__("os").environ.get("SEC_USER_AGENT") or "cm-research-desk research (github.com/wingerlc-spec/cm-research-desk)"
DUR = {"rev": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"], "ni": ["NetIncomeLoss"],
       "gp": ["GrossProfit"], "oi": ["OperatingIncomeLoss"], "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"]}
INST = {"inv": ["InventoryNet"], "cwl": ["ContractWithCustomerLiabilityCurrent"], "cwln": ["ContractWithCustomerLiabilityNoncurrent"],
        "ltd": ["LongTermDebt", "LongTermDebtNoncurrent"], "assets": ["Assets"]}
ANN = {"ni_fy": ["NetIncomeLoss"], "cfo_fy": ["NetCashProvidedByUsedInOperatingActivities"]}

def sec_get(url):
    import time
    for k in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": SEC_UA, "Accept-Encoding": "identity"})
            time.sleep(0.13)                                   # SEC fair-access limit is 10 requests a second
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code == 403: raise RuntimeError("SEC refused the request (403): set a SEC_USER_AGENT secret with a contact email")
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return None

def fetch_frame(concept, unit, period):
    d = sec_get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/{unit}/{period}.json")
    return {int(r["cik"]): float(r["val"]) for r in (d or {}).get("data", [])}

def load_fundamentals(years):
    """Returns {key: {period_label: {cik: value}}}. Quarterly durations use CY####Q#; instants CY####Q#I; annual CY####."""
    F = {}
    qs = [f"CY{y}Q{q}" for y in years for q in (1, 2, 3, 4)]
    for key, concepts in DUR.items():
        unit = "shares" if key == "shares" else "USD"
        F[key] = {}
        for p in qs:
            merged = {}
            for c in concepts:
                for cik, v in fetch_frame(c, unit, p).items(): merged.setdefault(cik, v)
            F[key][p] = merged
    for key, concepts in INST.items():
        F[key] = {}
        for p in qs:
            merged = {}
            for c in concepts:
                for cik, v in fetch_frame(c, "USD", p + "I").items(): merged.setdefault(cik, v)
            F[key][p] = merged
    for key, concepts in ANN.items():
        F[key] = {f"CY{y}": fetch_frame(concepts[0], "USD", f"CY{y}") for y in years}
    return F

def ticker_cik():
    d = sec_get("https://www.sec.gov/files/company_tickers.json") or {}
    return {v["ticker"].replace(".", "-"): int(v["cik_str"]) for v in d.values()}

def earnings_dates(ciks, start_year):
    """v14: real earnings release dates = SEC 8-K filings carrying Item 2.02 (Results of Operations). One submissions call per
    company plus its older-filings pages back to start_year. Returns {cik: sorted list of Timestamps}."""
    out = {}
    def take(block, acc):
        for f, d, it in zip(block.get("form", []), block.get("filingDate", []), block.get("items", [])):
            if f in ("8-K", "8-K/A") and "2.02" in (it or ""): acc.add(pd.Timestamp(d))
    for cik in ciks:
        d = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        if not d: continue
        acc = set(); take(d.get("filings", {}).get("recent", {}), acc)
        for extra in d.get("filings", {}).get("files", []):
            if str(extra.get("filingTo", "9999"))[:4] >= str(start_year):
                e = sec_get(f"https://data.sec.gov/submissions/{extra['name']}")
                if e: take(e, acc)
        if acc: out[cik] = sorted(acc)
    return out

def qlabel(y, q): return f"CY{y}Q{q}"
def qend(y, q): return pd.Timestamp(y, 3*q, 1) + pd.offsets.MonthEnd(0)

def lens_events(F, cikmap, bars, years, edates=None):
    """Scan every (stock, quarter) for the five fundamental signals. Returns {lens: [(ticker, entry_date, tag)]}."""
    ev = {k: [] for k in ("EARNINGS_DRIFT", "SHARE_SHRINK", "BILLINGS_AHEAD", "INVENTORY_REVERSAL")}
    edates = edates or {}; DRIFT_STATS.update(qualified=0, no_date=0, failed_reaction=0, events=0)
    DRIFT_DETAIL.clear(); spy_c = bars["SPY"]["close"]; spy_up = spy_c > spy_c.rolling(200).mean()
    tick = {c: t for t, c in cikmap.items() if t in bars}
    g = lambda key, y, q, cik: F[key].get(qlabel(y, q), {}).get(cik)
    def acc_ratio(cik, y):
        ni, cfo, a = F["ni_fy"].get(f"CY{y}", {}).get(cik), F["cfo_fy"].get(f"CY{y}", {}).get(cik), F["assets"].get(qlabel(y, 4), {}).get(cik)
        return (ni-cfo)/a if None not in (ni, cfo, a) and a else None
    acc_all = {y: sorted(v for v in (acc_ratio(c, y) for c in tick) if v is not None) for y in years}
    def high_accrual(cik, y):          # top quintile of (net income - operating cash flow) / assets, prior fiscal year
        r = acc_ratio(cik, y-1); arr = acc_all.get(y-1) or []
        return None if r is None or len(arr) < 50 else r >= arr[int(len(arr)*0.8)]
    for cik, t in tick.items():
        x = bars[t]; c, v = x["close"], x["volume"]
        ret = c.pct_change(); vr = v/v.rolling(20).mean().shift(1)
        for y in years[1:]:
            for q in (1, 2, 3, 4):
                py, pq = (y, q-1) if q > 1 else (y-1, 4)
                end = qend(y, q); entry45 = end + pd.Timedelta(days=45); tag = high_accrual(cik, y)
                rev, rev_ly = g("rev", y, q, cik), g("rev", y-1, q, cik)
                ni, ni_ly = g("ni", y, q, cik), g("ni", y-1, q, cik)
                # 1 earnings drift (v14): revenue +20% and OPERATING income +30% YoY (operating income positive a year ago), dated by the
                #   company's own 8-K Item 2.02 filed 10-75 days after quarter end. Reaction = close before the filing day to the close of
                #   the session after it (covers before-open and after-close reporters), must be +5% with 2x+ volume on either day.
                #   Entry: close of the second session after the filing day.
                oi, oi_ly = g("oi", y, q, cik), g("oi", y-1, q, cik)
                if rev and rev_ly and oi and oi_ly and rev_ly > 0 and oi_ly > 0 and rev/rev_ly-1 > 0.20 and oi/oi_ly-1 > 0.30:
                    DRIFT_STATS["qualified"] += 1
                    fd = [d for d in edates.get(cik, []) if end + pd.Timedelta(days=10) < d <= end + pd.Timedelta(days=75)]
                    k0 = int(c.index.searchsorted(fd[0])) if fd else None
                    if k0 is None: DRIFT_STATS["no_date"] += 1
                    elif 0 < k0 and k0+2 < len(c):
                        react2 = float(c.iloc[k0+1]/c.iloc[k0-1]-1); vx = float(np.nanmax(vr.iloc[k0:k0+2].values))
                        if not (react2 >= 0.05 and vx >= 2): DRIFT_STATS["failed_reaction"] += 1
                        else:
                            k = k0+1; DRIFT_STATS["events"] += 1
                            ev["EARNINGS_DRIFT"].append((t, c.index[k+1], tag))
                            if k > 260 and k+6 < len(c):
                                sh_q = g("shares", y, q, cik); cap = float(c.iloc[k])*sh_q if sh_q else None
                                rev_py = g("rev", py, pq, cik); rev_pyly = g("rev", py-1, pq, cik)
                                gp_, gp_ly = g("gp", y, q, cik), g("gp", y-1, q, cik)
                                ttm = [g("rev", *yq, cik) for yq in ((y, q), (py, pq))]
                                DRIFT_DETAIL.append(dict(
                                    t=t, ann=c.index[k], entry=c.index[k+1], entry_held=c.index[k+6],
                                    react=react2, volx=vx,
                                    held5=bool(c.iloc[k+5] >= c.iloc[k]),
                                    runup63=float(c.iloc[k0-1]/c.iloc[k0-64]-1),
                                    dist_high=float(c.iloc[k]/c.iloc[k-252:k].max()-1),
                                    spy_up=bool(spy_up.reindex([c.index[k+1]]).fillna(False).iloc[0]),
                                    cap=cap,
                                    ps=(cap/(2*sum(ttm))) if cap and all(ttm) else None,
                                    rev_accel=(rev/rev_ly-1) > (rev_py/rev_pyly-1) if rev_py and rev_pyly and rev_pyly > 0 else None,
                                    gm_expand=(gp_/rev > gp_ly/rev_ly) if gp_ and gp_ly else None,
                                    high_accrual=tag))
                # 2 share shrink: diluted shares down 3%+ YoY, long-term debt up less than 20%
                sh, sh_ly = g("shares", y, q, cik), g("shares", y-1, q, cik)
                d0, d1 = g("ltd", y, q, cik), g("ltd", y-1, q, cik)
                if sh and sh_ly and sh/sh_ly-1 <= -0.03 and (d0 is None or d1 is None or d1 == 0 or d0/d1-1 < 0.20):
                    ev["SHARE_SHRINK"].append((t, entry45, tag))
                # 3 billings ahead of revenue two quarters running: (revenue + change in contract liabilities) growth beats revenue growth by 15 pts
                def billings_gap(yy, qq):
                    pyy, pqq = (yy, qq-1) if qq > 1 else (yy-1, 4)
                    r0, r1 = g("rev", yy, qq, cik), g("rev", yy-1, qq, cik)
                    l = lambda a, b: (g("cwl", a, b, cik) or 0) + (g("cwln", a, b, cik) or 0)
                    if not (r0 and r1 and r1 > 0): return None
                    b0 = r0 + l(yy, qq) - l(pyy, pqq); b1 = r1 + l(yy-1, qq) - l(pyy-1, pqq)
                    if l(yy, qq) == 0 or b1 <= 0: return None
                    return (b0/b1-1) - (r0/r1-1)
                g1, g2 = billings_gap(y, q), billings_gap(py, pq)
                if g1 is not None and g2 is not None and g1 >= 0.15 and g2 >= 0.15:
                    ev["BILLINGS_AHEAD"].append((t, entry45, tag))
                # 4 inventory reversal: inventory down YoY two quarters running, revenue growth beats inventory growth by 15 pts,
                #   gross margin up on the prior quarter
                i0, i1, j0, j1 = g("inv", y, q, cik), g("inv", y-1, q, cik), g("inv", py, pq, cik), g("inv", py-1, pq, cik)
                gp0, gpp, rv0, rvp = g("gp", y, q, cik), g("gp", py, pq, cik), rev, g("rev", py, pq, cik)
                if None not in (i0, i1, j0, j1, rev, rev_ly, gp0, gpp, rvp) and i1 > 0 and j1 > 0 and rev_ly > 0 and rv0 and rvp:
                    if i0/i1-1 < 0 and j0/j1-1 < 0 and (rev/rev_ly-1) - (i0/i1-1) >= 0.15 and gp0/rv0 > gpp/rvp:
                        ev["INVENTORY_REVERSAL"].append((t, entry45, tag))
    return ev

def deletion_events(mem, bars):
    """S&P 500 deletions not explained by a takeover: the stock still trades 126 sessions later. Entry 10 sessions after deletion."""
    out = []
    for i in range(1, len(mem)):
        gone = mem["set"].iloc[i-1] - mem["set"].iloc[i]; d = mem["date"].iloc[i]
        for t in gone:
            x = bars.get(t)
            if x is None: continue
            c = x["close"]; k = c.index.searchsorted(d)
            if k+10+126 < len(c): out.append((t, c.index[k+10], None))
    return out

def event_score(events, bars, spy, members_fn=None):
    """Excess return vs SPY 60 and 120 sessions after entry, against ordinary days of the same stocks. Trimmed, month-clustered."""
    def ex(t, d):
        x = bars.get(t)
        if x is None: return None
        c = x["close"]; j = c.index.intersection(spy.index); cs, ss = c[j], spy[j]
        k = cs.index.searchsorted(d)
        if k+120 >= len(cs) or k < 1: return None
        return ((cs.iloc[k+60]/cs.iloc[k]-1)-(ss.iloc[k+60]/ss.iloc[k]-1))*100, ((cs.iloc[k+120]/cs.iloc[k]-1)-(ss.iloc[k+120]/ss.iloc[k]-1))*100, cs.index[k].year*100+cs.index[k].month
    rows, last = [], {}
    for t, d, tag in sorted(events, key=lambda e: (e[0], e[1])):
        if t in last and (d - last[t]).days < 120: continue           # one event per stock per ~4 months, so repeats do not pile up
        if members_fn and not members_fn(t, d): continue
        last[t] = d
        r = ex(t, d)
        if r: rows.append((*r, t, tag))
    if len(rows) < 30: return dict(n=len(rows), note="too few events")
    D = pd.DataFrame(rows, columns=["e60", "e120", "ym", "t", "tag"])
    base = []
    for t in D.t.unique():
        x = bars[t]; c = x["close"]; j = c.index.intersection(spy.index); cs, ss = c[j], spy[j]
        e120 = ((cs.shift(-120)/cs-1)-(ss.shift(-120)/ss-1)).values*100; e60 = ((cs.shift(-60)/cs-1)-(ss.shift(-60)/ss-1)).values*100
        ym = (cs.index.year*100+cs.index.month).values
        for i in range(252, len(cs)-120, 10):
            if members_fn and not members_fn(t, cs.index[i]): continue
            base.append((e60[i], e120[i], ym[i]))
    B = pd.DataFrame(base, columns=["e60", "e120", "ym"]).dropna()
    res = {"n": int(len(D)), "stocks": int(D.t.nunique()), "months": int(D.ym.nunique())}
    for h in ("e60", "e120"):
        lo, hi = B[h].quantile(0.01), B[h].quantile(0.99); d_, b_ = D[h].clip(lo, hi), B[h].clip(lo, hi)
        pm = (D.assign(v=d_).groupby("ym").v.mean() - B.assign(v=b_).groupby("ym").v.mean()).dropna()
        t_ = float(pm.mean()/(pm.std()/np.sqrt(len(pm)))) if len(pm) > 5 and pm.std() > 0 else None
        res[h] = dict(edge=round(float(d_.mean()-b_.mean()), 2), t_clustered=round(t_, 1) if t_ is not None else None,
                      median=round(float(d_.median()), 2), baseline_median=round(float(b_.median()), 2),
                      pct_beat_spy=round(float((d_ > 0).mean()*100), 0), baseline_pct_beat_spy=round(float((b_ > 0).mean()*100), 0))
    if D.tag.notna().any():
        for lab, sub in (("high_accrual", D[D.tag == True]), ("clean_earnings", D[D.tag == False])):
            if len(sub) >= 20: res[f"e120_{lab}"] = dict(n=int(len(sub)), mean=round(float(sub.e120.clip(B.e120.quantile(0.01), B.e120.quantile(0.99)).mean() - B.e120.clip(B.e120.quantile(0.01), B.e120.quantile(0.99)).mean()), 2))
    e = res["e120"]
    res["verdict"] = "WORKS" if (e["t_clustered"] or 0) >= 2 and e["edge"] > 0 else "HURTS" if (e["t_clustered"] or 0) <= -2 else "NOT SHOWN"
    return res

def lens_tests(bars, feats, live, F=None, cikmap=None, mem=None):
    spy = bars["SPY"]["close"]
    allbars = dict(bars); allbars.update(FORMER_BARS)
    years = list(range(max(2010, spy.index[0].year), spy.index[-1].year + 1))
    out = {"_note": ("Fundamental signals from SEC XBRL frames, entered when the data was public (quarter end + 45 days, or the day after a detected "
                     "earnings reaction). Each lens is scored on all stocks and on the point-in-time S&P 500 subset. WORKS needs a clustered t of 2+ "
                     "on the 6-month edge. Survivorship: former S&P 500 members are included where Yahoo has prices and SEC maps their ticker; "
                     "former mid caps are not, so the all-stocks line is flattered. Trust a lens only if the S&P 500 point-in-time line agrees.")}
    try:
        mem = mem if mem is not None else load_membership()
        dates = mem["date"].values
        def member(t, d):
            i = np.searchsorted(dates, np.datetime64(d), side="right") - 1
            return i >= 0 and t in mem["set"].iloc[i]
    except Exception as e:
        mem, member = None, None; out["_membership_error"] = str(e)[:120]
    if mem is not None:
        dev = deletion_events(mem, allbars)
        out["DELETION_REBOUND"] = dict(all=event_score(dev, allbars, spy), note="no SEC data needed; former members without Yahoo prices are missing")
    edates = None
    if F is None:
        if not live: return out
        try:
            cikmap = ticker_cik(); F = load_fundamentals(years)
            edates = earnings_dates(sorted({cikmap[t] for t in allbars if t in cikmap}), years[0])
        except Exception as e:
            out["_sec_error"] = f"{type(e).__name__}: {str(e)[:160]}"; return out
    out["_coverage"] = {k: int(np.mean([len(v) for v in F[k].values()])) for k in F}
    out["_drift_dates"] = f"8-K Item 2.02 dates found for {len(edates)} companies" if edates is not None else "no 8-K dates"
    ev = lens_events(F, cikmap, allbars, years, edates)
    out["_drift_stats"] = dict(DRIFT_STATS)
    LAST_EVENTS.clear(); LAST_EVENTS.update(ev)
    if mem is not None: LAST_EVENTS["DELETION_REBOUND"] = dev
    for lens, events in ev.items():
        out[lens] = dict(all=event_score(events, allbars, spy), sp500_point_in_time=event_score(events, allbars, spy, member) if member else None)
    try:
        DRIFT_RESULT.clear(); DRIFT_RESULT.update(drift_conditions(allbars, spy, member))
    except Exception as e:
        DRIFT_RESULT.clear(); DRIFT_RESULT["_error"] = f"{type(e).__name__}: {str(e)[:150]}"
    return out

def lens_verdict(r):
    """The decision rules fixed in strategy/lens-report-spec-2026-10-11.md, before any result was seen."""
    pit, al = r.get("sp500_point_in_time") or {}, r.get("all") or {}
    if "e120" not in pit:                       # deletion rebound: point-in-time by construction
        e = al.get("e120") or {}
        if not e: return "NO DATA", 0.0
        if (e["t_clustered"] or 0) >= 2.5 and e["edge"] > 0: return "ADOPT", e["edge"]
        return ("AVOID" if (e["t_clustered"] or 0) <= -2 else "PROMISING" if e["edge"] > 0 and (e["t_clustered"] or 0) >= 1.5 else "DROP"), 0.0
    p, a = pit["e120"], (al.get("e120") or {})
    tp, ta = p["t_clustered"] or 0, a.get("t_clustered") or 0
    typical_ok = p["median"] > p["baseline_median"]
    if p["edge"] >= 2 and typical_ok and (tp >= 2.5 or (tp >= 2 and ta >= 2 and a.get("edge", 0) > 0)): return "ADOPT", p["edge"]
    if tp <= -2: return "AVOID", 0.0
    if p["edge"] > 0 and a.get("edge", 0) > 0 and 1.5 <= tp < 2.5: return "PROMISING", 0.0
    return "DROP", 0.0

def lens_candidates(lens, bars, feats, live, asof):
    """Today's names: stocks whose latest lens event is recent enough to still be actionable (entry within the last 100 days).
    Score = sum of the measured point-in-time 6-month edges of the ADOPTED lenses firing. PROMISING hits are listed, not scored."""
    verdicts = {k: lens_verdict(v) for k, v in lens.items() if not k.startswith("_") and isinstance(v, dict)}
    cutoff = pd.Timestamp(asof) - pd.Timedelta(days=100)
    hits = {}
    for k, evs in LAST_EVENTS.items():
        for t, d, tag in evs:
            if pd.Timestamp(d) >= cutoff and t in bars and t not in BENCH:
                hits.setdefault(t, []).append(dict(lens=k, entry=str(pd.Timestamp(d).date()), high_accrual=tag, verdict=verdicts.get(k, ("?", 0))[0]))
    uber = bars.get("UBER"); rows = []
    for t, hs in hits.items():
        f = feats.get(t) or {}; last = float(bars[t]["close"].iloc[-1])
        lenses = sorted(set(h["lens"] for h in hs))
        score = sum(verdicts.get(l, ("", 0))[1] for l in lenses)
        corr = None
        if uber is not None and t != "UBER":
            j = bars[t]["close"].index.intersection(uber["close"].index)[-121:]
            if len(j) > 60: corr = round(float(bars[t]["close"][j].pct_change().corr(uber["close"][j].pct_change())), 2)
        rows.append(dict(ticker=t, name=f.get("name"), sector=f.get("sector"), index=f.get("index"), last=round(last, 2), score=round(score, 2),
                         lenses=lenses, adopted=[l for l in lenses if verdicts.get(l, ("",))[0] == "ADOPT"],
                         promising=[l for l in lenses if verdicts.get(l, ("",))[0] == "PROMISING"], hits=hs,
                         instrument="deep ITM call" if last <= PRICE_CAP else "shares (over the price cap)", uber_corr_120d=corr,
                         chart_gate=("falling hard: below the 50-day and 200-day" if f.get("vs50", 0) < 0 and f.get("vs200", 0) < -10
                                     else "spike: 20%+ over the 50-day" if f.get("vs50", 0) > 20 else "ok")))
    any_adopted = any(v[0] == "ADOPT" for v in verdicts.values())
    rows.sort(key=lambda r: (-r["score"], -len(r["promising"]), -len(r["lenses"])))
    top = rows[:60]
    if live:
        for r in top: r.update(fundamentals(r["ticker"]))
    if not any_adopted:   # fallback, labelled: no lens proven, rank by number of lens hits then 30-day estimate revisions
        top.sort(key=lambda r: (-len(r["promising"]), -len(r["lenses"]), -(r.get("rev30_pct") or -99)))
    return dict(asof=asof, verdicts={k: v[0] for k, v in verdicts.items()}, weights={k: v[1] for k, v in verdicts.items()},
                mode="ranked by adopted-lens edge" if any_adopted else "FALLBACK: no lens adopted; ranked by PROMISING-lens hits, then lens-hit count, then estimate revisions (unproven ideas)",
                n_names=len(rows), candidates=top)

# ----------------------------------------------------------------------------- what separates good and bad earnings-drift events (added 11 Oct 2026)
# Protocol, fixed before results: 10 yes/no conditions. DISCOVERY = events entered 2021 or earlier, CONFIRMATION = 2022 or later.
# A condition HELPS (or HURTS) only if: the yes-minus-no gap in 6-month excess return is at least 3 points in BOTH periods with the
# same sign, the discovery t is at least 2.8 (Bonferroni for 10 tests at 5%), and the confirmation t is at least 1.5.
# Held-5 is measured from day 6 for both groups (the information is not known before then).
DRIFT_CONDITIONS = [
    ("held5", "reaction held: close 5 sessions later at or above the reaction-day close", lambda d, m: d["held5"]),
    ("big_reaction", "reaction day up 10% or more (vs 5 to 10%)", lambda d, m: d["react"] >= 0.10),
    ("heavy_volume", "reaction volume 4x or more (vs 2 to 4x)", lambda d, m: d["volx"] >= 4),
    ("small_cap", "market value under $10B at the reaction", lambda d, m: d["cap"] < 10e9 if d["cap"] else None),
    ("market_up", "SPY above its 200-day at entry", lambda d, m: d["spy_up"]),
    ("ran_up_before", "3-month return before the print above the median event", lambda d, m: d["runup63"] > m["runup63"]),
    ("near_high", "within 10% of the 52-week high after the reaction", lambda d, m: d["dist_high"] > -0.10),
    ("cheap_sales", "price-to-sales below the median event", lambda d, m: d["ps"] < m["ps"] if d["ps"] else None),
    ("accelerating", "revenue growth faster than the prior quarter's", lambda d, m: d["rev_accel"]),
    ("margin_up", "gross margin above the same quarter last year", lambda d, m: d["gm_expand"]),
]

def drift_conditions(bars, spy, members_fn=None):
    if len(DRIFT_DETAIL) < 60: return {"_note": f"only {len(DRIFT_DETAIL)} drift events with full detail"}
    def ex120(t, d):
        x = bars.get(t)
        if x is None: return None
        c = x["close"]; j = c.index.intersection(spy.index); cs, ss = c[j], spy[j]; k = cs.index.searchsorted(d)
        if k+120 >= len(cs): return None
        return ((cs.iloc[k+120]/cs.iloc[k]-1)-(ss.iloc[k+120]/ss.iloc[k]-1))*100
    rows, last = [], {}
    for d in sorted(DRIFT_DETAIL, key=lambda z: (z["t"], z["entry"])):
        if d["t"] in last and (d["entry"]-last[d["t"]]).days < 120: continue
        last[d["t"]] = d["entry"]
        e, eh = ex120(d["t"], d["entry"]), ex120(d["t"], d["entry_held"])
        if e is None or eh is None: continue
        rows.append(dict(d, e=e, eh=eh, pit=bool(members_fn(d["t"], d["entry"])) if members_fn else None))
    D = pd.DataFrame(rows)
    lo, hi = D.e.quantile(0.02), D.e.quantile(0.98); D["e"] = D.e.clip(lo, hi); D["eh"] = D.eh.clip(lo, hi)
    med = {"runup63": D.runup63.median(), "ps": D.ps.dropna().median() if D.ps.notna().any() else None}
    D["disc"] = D.entry.map(lambda z: z.year <= 2021)
    def gap(sub, col, flag):
        a, b = sub[flag == True][col], sub[flag == False][col]
        if len(a) < 15 or len(b) < 15: return None
        diff = a.mean()-b.mean(); se = np.sqrt(a.var()/len(a) + b.var()/len(b))
        return dict(gap=round(float(diff), 2), t=round(float(diff/se), 2) if se > 0 else None, n_yes=int(len(a)), n_no=int(len(b)),
                    yes_mean=round(float(a.mean()), 2), no_mean=round(float(b.mean()), 2), yes_beat=round(float((a > 0).mean()*100)), no_beat=round(float((b > 0).mean()*100)))
    out = {"n_events": int(len(D)), "n_discovery": int(D.disc.sum()), "n_confirmation": int((~D.disc).sum()),
           "all_events_mean_6m_vs_spy": round(float(D.e.mean()), 2), "conditions": {}}
    for key, label, fn in DRIFT_CONDITIONS:
        flag = D.apply(lambda r: fn(r, med), axis=1)
        col = "eh" if key == "held5" else "e"
        res = {"label": label, "full": gap(D, col, flag), "discovery": gap(D[D.disc], col, flag[D.disc]), "confirmation": gap(D[~D.disc], col, flag[~D.disc])}
        if D.pit.notna().any(): res["sp500_point_in_time"] = gap(D[D.pit == True], col, flag[D.pit == True])
        di, co = res["discovery"], res["confirmation"]
        if di and co and di["t"] is not None and co["t"] is not None:
            same = np.sign(di["gap"]) == np.sign(co["gap"])
            ok = same and abs(di["gap"]) >= 3 and abs(co["gap"]) >= 3 and abs(di["t"]) >= 2.8 and abs(co["t"]) >= 1.5
            res["verdict"] = ("HELPS" if di["gap"] > 0 else "HURTS") if ok else ("CONSISTENT, NOT PROVEN" if same and abs(di["gap"]) >= 3 and abs(co["gap"]) >= 3 else "NO EFFECT")
        else:
            res["verdict"] = "TOO FEW EVENTS"
        out["conditions"][key] = res
    out["_rule"] = ("HELPS/HURTS needs a gap of 3+ points in both periods, same sign, discovery t 2.8+ (10 tests), confirmation t 1.5+. "
                    "CONSISTENT, NOT PROVEN: same sign and 3+ points both periods but not significant. Discovery = 2021 or earlier, confirmation = 2022 on.")
    return out

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
        for h in (20, 60, 120):
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
    keep = ["ticker", "name", "index", "sector", "industry", "last", "best_day", "best_day_date", "d1", "w1", "m1", "m3", "m6", "vs50", "vs200", "rsi", "pos52", "dd52", "volx",
            "rs3", "rs6", "bbw_pct", "pivot", "base_low", "dist_pivot", "worst_day", "worst_day_date"]
    for k, lst in cands.items():
        lst.sort(reverse=True); counts[k] = len(lst)
        for rank, (score, t, why) in enumerate(lst[:PER_ARCHETYPE], 1):
            f = feats[t]
            survivors.append(dict(archetype=k, rank=rank, of=len(lst), score=round(float(score), 1), why=why, chart=f"charts/{t}_{k}.png",
                                  **{x: f.get(x) for x in keep}))
            if not a.no_charts: chart(t, bars[t], f, k, out/"charts"/f"{t}_{k}.png")
    try:
        bt = backtest(bars, feats, [t for t in feats if "skip" not in feats[t] or feats[t].get("skip") == "deal-pinned"])
    except Exception as e:
        bt = {"_error": f"{type(e).__name__}: {str(e)[:120]}"}
    (out/"backtest.json").write_text(json.dumps(bt, indent=1))
    try:
        surv = survivorship_test(bars, feats, live=not a.csv_dir)
    except Exception as e:
        surv = {"_error": f"{type(e).__name__}: {str(e)[:150]}"}
    (out/"survivorship.json").write_text(json.dumps(surv, indent=1))
    try:
        lens = lens_tests(bars, feats, live=not a.csv_dir)
    except Exception as e:
        import traceback; lens = {"_error": f"{type(e).__name__}: {str(e)[:150]}", "_trace": traceback.format_exc()[-600:]}
    (out/"lens_tests.json").write_text(json.dumps(lens, indent=1, default=str))
    (out/"drift_conditions.json").write_text(json.dumps(DRIFT_RESULT, indent=1, default=str))
    print("DRIFT CONDITIONS events", DRIFT_RESULT.get("n_events"), "discovery", DRIFT_RESULT.get("n_discovery"), "confirmation", DRIFT_RESULT.get("n_confirmation"), DRIFT_RESULT.get("_error", ""), DRIFT_RESULT.get("_note", ""))
    for k_, r_ in (DRIFT_RESULT.get("conditions") or {}).items():
        f_, d_, c_ = r_.get("full") or {}, r_.get("discovery") or {}, r_.get("confirmation") or {}
        print(f"  {k_:14} {r_['verdict']:22} full gap {f_.get('gap')} t {f_.get('t')} | disc {d_.get('gap')} t {d_.get('t')} | conf {c_.get('gap')} t {c_.get('t')} | yes {f_.get('yes_mean')} n{f_.get('n_yes')} vs no {f_.get('no_mean')} n{f_.get('n_no')}")
    try:
        lc = lens_candidates(lens, {**bars, **FORMER_BARS}, feats, live=not a.csv_dir, asof=asof)
    except Exception as e:
        import traceback; lc = {"_error": f"{type(e).__name__}: {str(e)[:150]}", "_trace": traceback.format_exc()[-600:]}
    (out/"lens_candidates.json").write_text(json.dumps(lc, indent=1, default=str))
    print("LENS VERDICTS", lc.get("verdicts"), "|", lc.get("mode"), "| names", lc.get("n_names"), lc.get("_error", ""))
    for r_ in (lc.get("candidates") or [])[:15]:
        print(f"  CAND {r_['ticker']:6} score {r_['score']:5} {r_['last']:>8} {r_['instrument'][:13]:13} corrUBER {r_['uber_corr_120d']} gate {r_['chart_gate'][:20]:20} | {','.join(r_['lenses'])} | rev30 {r_.get('rev30_pct')}")
    for k_, v_ in lens.items():
        if k_.startswith("_"): print("LENS", k_, v_ if k_ != "_note" else ""); continue
        for sub, r_ in v_.items():
            if isinstance(r_, dict) and "e120" in r_:
                print(f"LENS {k_:19} {sub:20} {r_['verdict']:9} n {r_['n']:5} stocks {r_['stocks']:4} | 6m edge {r_['e120']['edge']:+.2f} t {r_['e120']['t_clustered']} | median {r_['e120']['median']:+.2f} vs {r_['e120']['baseline_median']:+.2f} | beat SPY {r_['e120']['pct_beat_spy']:.0f}% vs {r_['e120']['baseline_pct_beat_spy']:.0f}% | 3m edge {r_['e60']['edge']:+.2f} t {r_['e60']['t_clustered']} | accrual split {r_.get('e120_high_accrual')} / {r_.get('e120_clean_earnings')}")
            elif isinstance(r_, dict) and "note" in r_ and "n" in r_: print(f"LENS {k_:19} {sub:20} n {r_['n']} {r_['note']}")
    for k_, v_ in surv.items():
        if isinstance(v_, dict) and "test" in v_: print(f"SURVIVORSHIP {k_:18} n {v_.get('n')} stocks {v_.get('stocks')} | 6m edge {v_.get('edge120')} t {v_.get('t_clustered')} | beat SPY {v_.get('pct_beat_spy')}% vs {v_.get('baseline_pct_beat_spy')}% | {v_.get('test')}")
    print("SURVIVORSHIP former members", surv.get("former_members_in_window"), "with prices", surv.get("former_members_with_prices"), surv.get("_error", ""), "| by year", surv.get("C_by_year"))
    ranked = rank_all(cands, feats, bars, asof, live=not a.csv_dir, bt=bt)
    scorecard = track(out, survivors, bars, asof)
    bench = {t: {x: feats[t].get(x) for x in ("last", "d1", "w1", "m1", "m3", "vs50", "vs200", "rsi", "pos52")} for t in BENCH if t in feats and "skip" not in feats[t]}
    ok = [f for f in feats.values() if "skip" not in f]
    breadth = dict(n=len(ok), pct_above_50d=round(float(np.mean([f["vs50"] > 0 for f in ok])*100), 1),
                   pct_above_200d=round(float(np.mean([f["vs200"] > 0 for f in ok])*100), 1),
                   pct_rsi_under_30=round(float(np.mean([f["rsi"] < 30 for f in ok])*100), 1),
                   pct_within_5_of_52w_high=round(float(np.mean([f["dd52"] > -5 for f in ok])*100), 1))
    (out/"screen_output.json").write_text(json.dumps(dict(
        asof=asof, generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), universe=len(feats), candidates_per_archetype=counts,
        dropped=dropped, universe_note="; ".join(UNIVERSE_NOTE), scorecard=scorecard, backtest=bt, ranked=ranked, breadth=breadth, benchmarks=bench, survivors=survivors,
        notes="Prices are raw split-adjusted closes (dividends not added back). ranked[] simulates each setup's own stop, target and 60-session time stop on the stock's 10-year history, against the same trade taken on any day (the drift). Estimates and earnings dates are from Yahoo when available. MACRO_PUNISHED names no driver; research must."), indent=1))
    (out/"market_state_full.json").write_text(json.dumps(feats, indent=0, sort_keys=True))
    print(f"asof {asof} universe {len(feats)} dropped {dropped} candidates {counts} survivors {len(survivors)} breadth {breadth}")
    for a_, r_ in bt.items():
        if not a_.startswith("_"): print(f"BACKTEST {a_:17} {r_['verdict']:9} n {r_['n']:6} months {r_['months_with_signals']:4} | 120d edge {r_['e120']['edge']:+.2f} (month-matched {r_['e120']['edge_month_matched']}) t {r_['e120']['t_clustered']} | median {r_['e120']['median']:+.2f} vs {r_['e120']['baseline_median']:+.2f} | beat SPY {r_['e120']['pct_beat_spy']:.0f}% vs {r_['e120']['baseline_pct_beat_spy']:.0f}% | halves {r_['edge120_first_half']} / {r_['edge120_second_half']} | 60d edge {r_['e60']['edge']:+.2f} t {r_['e60']['t_clustered']}")
    print("BACKTEST baseline", bt.get("_baseline"), bt.get("_error", ""))
    print("NOW", bt.get("_now"))
    print(f"RANKED {len(ranked)}: " + ", ".join(f"{k} {sum(1 for r in ranked if r['tier']==k)}" for k in ("DEEP DIVE", "AFTER PRINT", "WATCH", "TOO EXPENSIVE", "PASS")))
    for r in ranked:
        if r["tier"] not in ("PASS", "TOO EXPENSIVE"): print(f"  {r['tier']:9} entry {r.get('entry_grade')}{r.get('entry_score')} {r['ticker']:6} {r['archetype'][:10]:10} expR {r.get('exp_R')} ev {r.get('ev_used')} vs drift {r.get('ev_any_day')} n {r.get('n_setups')} rr {r.get('rr')} | {r.get('reason')}")
    for s in survivors: print(f"  {s['archetype']:17} #{s['rank']}/{s['of']:<3} {s['ticker']:6} {s['why']}")

if __name__ == "__main__":
    main()
