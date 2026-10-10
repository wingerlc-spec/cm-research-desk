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
PER_ARCHETYPE = 8          # survivors kept per archetype
MIN_PRICE, MIN_DVOL, MIN_BARS = 5.0, 20e6, 260

# ----------------------------------------------------------------------------- data
def load_universe():
    raw = urllib.request.urlopen(UNIVERSE_URL, timeout=30).read().decode()
    df = pd.read_csv(io.StringIO(raw))
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)   # BRK.B -> BRK-B for Yahoo
    return {r.Symbol: dict(name=r.Security, sector=r["GICS Sector"], industry=r["GICS Sub-Industry"]) for _, r in df.iterrows()}

def pull_yf(tickers):
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i+100]
        d = yf.download(chunk, period="3y", interval="1d", auto_adjust=True, group_by="ticker", threads=True, progress=False)
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
        out[f.stem] = pd.DataFrame({"close": d["close"]*k, "high": d["high"]*k, "low": d["low"]*k, "volume": d["volume"]}).tail(756)
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
    bbw = 4*c.rolling(20).std()/s20
    f["bbw_pct"] = float((bbw.tail(504) < bbw.iloc[-1]).mean()*100)      # percentile of today's bandwidth, 2y
    # scare: worst single session inside the last 10, with its volume multiple and the trend before it
    ret = c.pct_change()*100; k = int(np.argmin(ret.tail(10).values)); pos = n-10+k
    f.update(worst_day=float(ret.iloc[pos]), worst_day_date=str(c.index[pos].date()),
             worst_day_volx=float(v.iloc[pos]/v.iloc[pos-20:pos].mean()),
             pre_vs200=float((c.iloc[pos-1]/s200.iloc[pos-1]-1)*100))
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
    if not (f["tightness"] < 0.20 and f["compression"] < 1.0 and f["dryup"] < 1.0 and f["vs200"] > -5): return None
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
    if not (f["dd52"] <= -25 and f["vs20"] > 0 and f["m1"] > 0 and f["rsi"] > 45 and f["rsi"] < 65): return None
    return -f["dd52"]/2 + f["m1"], f"{f['dd52']:.0f}% off the 52w high, back over the 20d, 1m {f['m1']:+.1f}%. Needs estimates: revisions must be turning up"

def a_macro(f, sec):  # sector has recovered, the stock has not
    if sec is None: return None
    lag = f["m3"] - sec["m3"]
    if not (sec["vs50"] > 0 and sec["m1"] > 2 and lag < -10 and f["vs50"] < 0): return None
    return -lag, f"sector ETF {sec['ticker']} is {sec['vs50']:+.1f}% over its 50d and {sec['m1']:+.1f}% on the month; the stock lags it by {lag:.0f}pts over 3m and sits {f['vs50']:.1f}% under its own 50d. Driver to be named in research"

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
        for k, rule in RULES:
            r = rule(f)
            if r: cands[k].append((r[0], t, r[1]))
        sec = feats.get(SECTOR_ETF.get(f.get("sector") or "", ""))
        r = a_macro(f, sec if sec and "skip" not in sec else None)
        if r: cands["MACRO_PUNISHED"].append((r[0], t, r[1]))
    keep = ["ticker", "name", "sector", "industry", "last", "d1", "w1", "m1", "m3", "m6", "vs50", "vs200", "rsi", "pos52", "dd52", "volx",
            "rs3", "rs6", "bbw_pct", "pivot", "base_low", "dist_pivot", "worst_day", "worst_day_date"]
    for k, lst in cands.items():
        lst.sort(reverse=True); counts[k] = len(lst)
        for rank, (score, t, why) in enumerate(lst[:PER_ARCHETYPE], 1):
            f = feats[t]
            survivors.append(dict(archetype=k, rank=rank, of=len(lst), score=round(float(score), 1), why=why, chart=f"charts/{t}_{k}.png",
                                  **{x: f.get(x) for x in keep}))
            if not a.no_charts: chart(t, bars[t], f, k, out/"charts"/f"{t}_{k}.png")
    bench = {t: {x: feats[t].get(x) for x in ("last", "d1", "w1", "m1", "m3", "vs50", "vs200", "rsi", "pos52")} for t in BENCH if t in feats and "skip" not in feats[t]}
    ok = [f for f in feats.values() if "skip" not in f]
    breadth = dict(n=len(ok), pct_above_50d=round(float(np.mean([f["vs50"] > 0 for f in ok])*100), 1),
                   pct_above_200d=round(float(np.mean([f["vs200"] > 0 for f in ok])*100), 1),
                   pct_rsi_under_30=round(float(np.mean([f["rsi"] < 30 for f in ok])*100), 1),
                   pct_within_5_of_52w_high=round(float(np.mean([f["dd52"] > -5 for f in ok])*100), 1))
    (out/"screen_output.json").write_text(json.dumps(dict(
        asof=asof, generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), universe=len(feats), candidates_per_archetype=counts,
        dropped=dropped, breadth=breadth, benchmarks=bench, survivors=survivors,
        notes="Chart-only screen. VALUE_DIVERGENCE is the price half only until estimates are wired. MACRO_PUNISHED names no driver; research must."), indent=1))
    (out/"market_state_full.json").write_text(json.dumps(feats, indent=0, sort_keys=True))
    print(f"asof {asof} universe {len(feats)} dropped {dropped} candidates {counts} survivors {len(survivors)} breadth {breadth}")
    for s in survivors: print(f"  {s['archetype']:17} #{s['rank']}/{s['of']:<3} {s['ticker']:6} {s['why']}")

if __name__ == "__main__":
    main()
