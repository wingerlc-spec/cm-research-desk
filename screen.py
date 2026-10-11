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
        return last, (f["s50"] if 0.03 <= 1-f["s50"]/last <= 0.12 else last*0.90), f["hi52c"]
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

def tier(r, asof, bt=None):
    if "tier" in r: return
    pooled = (bt or {}).get(r["archetype"])
    if pooled:
        r["pooled_edge60"] = pooled["e60"]["edge"]; r["pooled_t"] = pooled["e60"]["t_clustered"]
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
        why.append(f"this archetype has done worse than ordinary days across all stocks (edge {pooled['e60']['edge']:+.1f}, t {pooled['e60']['t_clustered']})")
    elif pooled and pooled.get("verdict") != "WORKS":
        cap = True; r["note"] = f"archetype not yet shown to beat ordinary days (edge {pooled['e60']['edge']:+.1f}, t {pooled['e60']['t_clustered']}): capped at WATCH"
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
    for r in rows: tier(r, asof, bt)
    order = {"DEEP DIVE": 0, "AFTER PRINT": 1, "WATCH": 2, "PASS": 3}
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
    """Every past signal, every stock, 10 years. Result = return over the next 20 and 60 sessions MINUS SPY over the
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
        e20 = ((cs.shift(-20)/cs-1) - (ss.shift(-20)/ss-1)).values*100; e60 = ((cs.shift(-60)/cs-1) - (ss.shift(-60)/ss-1)).values*100
        ym = (cs.index.year*100 + cs.index.month).values
        secbar = bars.get(SECTOR_ETF.get((feats.get(t) or {}).get("sector") or "", ""))
        mk = spy_up.reindex(cs.index).fillna(False).values.astype(int)                       # 1 = SPY above its 200-day on the signal day
        if secbar is not None:
            sc = secbar["close"].reindex(cs.index).ffill()
            sk = ((sc/sc.shift(63) - ss/ss.shift(63)) > 0).values.astype(int)                 # 1 = the stock's sector beat SPY over the prior 3 months
        else:
            sk = np.full(len(cs), -1)
        for i in range(252, len(cs)-60, 10): base.append((e20[i], e60[i], ym[i], mk[i], sk[i]))
        for a in archs:
            try:
                sig = signal_days(x, a, secbar["close"] if secbar is not None else None, spy) if a in ENTRY_STYLE else extra_signals(x, a, spy)
            except Exception:
                sig = None
            if sig is None: continue
            sig = sig.reindex(cs.index).fillna(False).values
            for i in thin([k for k in np.flatnonzero(sig) if 252 <= k < len(cs)-60]): acc[a].append((e20[i], e60[i], ym[i], mk[i], sk[i]))
    COLS = ["e20", "e60", "ym", "mkt", "sec"]
    b = pd.DataFrame(base, columns=COLS).dropna()
    clip = {h: (float(b[h].quantile(0.01)), float(b[h].quantile(0.99))) for h in ("e20", "e60")}
    for h in clip: b[h] = b[h].clip(*clip[h])
    mid = int(b.ym.median())
    bm = {h: b.groupby("ym")[h].mean() for h in ("e20", "e60")}
    def stat(d):
        r = {"n": int(len(d)), "months_with_signals": int(d.ym.nunique())}
        for h in ("e20", "e60"):
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
        r["edge60_first_half"] = round(float(f1.e60.mean() - b[b.ym <= mid].e60.mean()), 2) if len(f1) else None
        r["edge60_second_half"] = round(float(f2.e60.mean() - b[b.ym > mid].e60.mean()), 2) if len(f2) else None
        cond = {}
        for label, col, val in (("spy_above_200d", "mkt", 1), ("spy_below_200d", "mkt", 0), ("sector_leading", "sec", 1), ("sector_lagging", "sec", 0)):
            ds, bs = d[d[col] == val], b[b[col] == val]
            if len(ds) >= 30 and len(bs) >= 30:
                pmc = (ds.groupby("ym").e60.mean() - bs.groupby("ym").e60.mean()).dropna()
                tcc = float(pmc.mean()/(pmc.std()/np.sqrt(len(pmc)))) if len(pmc) > 5 and pmc.std() > 0 else None
                cond[label] = dict(n=int(len(ds)), edge60=round(float(ds.e60.mean()-bs.e60.mean()), 2), t_clustered=round(tcc, 1) if tcc is not None else None)
        r["by_condition"] = cond
        e = r["e60"]
        r["verdict"] = ("WORKS" if (e["t_clustered"] or 0) >= 2 and e["edge"] > 0 and (r["edge60_first_half"] or 0) > 0 and (r["edge60_second_half"] or 0) > 0
                        else "HURTS" if (e["t_clustered"] or 0) <= -2 and e["edge"] < 0 else "NOT SHOWN")
        return r
    for a in archs:
        d = pd.DataFrame(acc[a], columns=COLS).dropna()
        if len(d) >= 30: out[a] = stat(d)
    out["_baseline"] = dict(n=int(len(b)), mean_excess_20=round(float(b.e20.mean()), 2), mean_excess_60=round(float(b.e60.mean()), 2),
                            median_60=round(float(b.e60.median()), 2), pct_beat_spy_60=round(float((b.e60 > 0).mean()*100), 0), split_month=mid, trim=clip)
    out["_now"] = dict(spy_above_200d=bool(spy_up.iloc[-1]),
                       sectors_leading=sorted(e for e in set(SECTOR_ETF.values()) if e in bars and len(bars[e]) > 70 and
                                              (bars[e]["close"].iloc[-1]/bars[e]["close"].iloc[-64] - spy.iloc[-1]/spy.iloc[-64]) > 0))
    out["_note"] = ("Excess return vs SPY after every past signal, all stocks pooled, signals at least 20 sessions apart per stock, results trimmed at the "
                    "baseline's 1st/99th percentile. edge = signal mean minus ordinary-day mean. t_clustered treats each calendar month as one observation. "
                    "WORKS = clustered t of 2 or more and positive in both halves. by_condition splits each archetype by whether SPY was above its 200-day and whether the stock's sector was beating SPY on the signal day: a condition is a candidate filter only if its edge and t are clearly better than the other side. Still uncorrected: survivorship (today's index members only, which flatters "
                    "anything that buys a fallen stock), no stops, no costs.")
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
        if not a_.startswith("_"): print(f"BACKTEST {a_:17} {r_['verdict']:9} n {r_['n']:6} months {r_['months_with_signals']:4} | 60d edge {r_['e60']['edge']:+.2f} (month-matched {r_['e60']['edge_month_matched']}) t {r_['e60']['t_clustered']} | median {r_['e60']['median']:+.2f} vs {r_['e60']['baseline_median']:+.2f} | beat SPY {r_['e60']['pct_beat_spy']:.0f}% vs {r_['e60']['baseline_pct_beat_spy']:.0f}% | halves {r_['edge60_first_half']} / {r_['edge60_second_half']} | 20d edge {r_['e20']['edge']:+.2f} t {r_['e20']['t_clustered']}")
    print("BACKTEST baseline", bt.get("_baseline"), bt.get("_error", ""))
    print("NOW", bt.get("_now"))
    print(f"RANKED {len(ranked)}: " + ", ".join(f"{k} {sum(1 for r in ranked if r['tier']==k)}" for k in ("DEEP DIVE", "AFTER PRINT", "WATCH", "PASS")))
    for r in ranked:
        if r["tier"] != "PASS": print(f"  {r['tier']:9} {r['ticker']:6} {r['archetype'][:10]:10} expR {r.get('exp_R')} ev {r.get('ev_used')} vs drift {r.get('ev_any_day')} n {r.get('n_setups')} rr {r.get('rr')} | {r.get('reason')}")
    for s in survivors: print(f"  {s['archetype']:17} #{s['rank']}/{s['of']:<3} {s['ticker']:6} {s['why']}")

if __name__ == "__main__":
    main()
