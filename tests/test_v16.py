"""Offline tests for v16 (no network). Run: python -m pytest -q tests"""
import datetime as dt, io, json, sys
from math import erf, exp, log, sqrt
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import screen as S          # noqa: E402
import terminal_pulls as TP  # noqa: E402


# ---------------------------------------------------------------- Black-Scholes reference (independent of screen.py)
def ref_call(s, k, t, v, r):
    n = lambda x: 0.5*(1+erf(x/sqrt(2)))
    d1 = (log(s/k)+(r+v*v/2)*t)/(v*sqrt(t)); d2 = d1-v*sqrt(t)
    return s*n(d1)-k*exp(-r*t)*n(d2), n(d1)

def test_bs_textbook_value():
    # Hull: S=42, K=40, r=10%, sigma=20%, T=0.5 -> call 4.76, delta 0.779
    assert S.bs_call(42, 40, 0.5, 0.2, 0.10) == pytest.approx(4.76, abs=0.01)
    assert S.bs_delta(42, 40, 0.5, 0.2, 0.10) == pytest.approx(0.7791, abs=1e-3)

@pytest.mark.parametrize("s,k,t,v", [(100, 70, 0.75, 0.35), (55, 45, 0.5, 0.6), (300, 250, 1.2, 0.25), (20, 21, 0.4, 1.2)])
def test_delta_and_iv_roundtrip(s, k, t, v):
    px, d = ref_call(s, k, t, v, 0.04)
    assert S.bs_call(s, k, t, v) == pytest.approx(px, rel=1e-9)
    assert S.bs_delta(s, k, t, v) == pytest.approx(d, rel=1e-9)
    assert S.implied_vol(px, s, k, t) == pytest.approx(v, abs=1e-4)

def test_iv_put_and_bounds():
    p = S.bs_put(100, 110, 0.5, 0.3)
    assert S.implied_vol(p, 100, 110, 0.5, put=True) == pytest.approx(0.3, abs=1e-4)
    assert S.implied_vol(5.0, 100, 50, 1.0) is None          # below intrinsic: no vol fits
    assert S.implied_vol(0, 100, 90, 1.0) is None


# ---------------------------------------------------------------- contract selection on a synthetic chain
def synth_chain(spot, dte, vol=0.35, oi=None, spread=0.04, zero=False):
    rows = []
    for k in np.arange(spot*0.5, spot*1.2, spot*0.025):
        k = round(float(k), 1)
        px = ref_call(spot, k, dte/365, vol, 0.04)[0]
        bid, ask = (0.0, 0.0) if zero else (round(px*(1-spread/2), 2), round(px*(1+spread/2), 2))
        rows.append(dict(strike=k, bid=bid, ask=ask, lastPrice=round(px, 2), openInterest=(oi or {}).get(k, 50), volume=3,
                         impliedVolatility=vol if not zero else 1e-5))
    return rows

def contracts(spot, chains):
    out = []
    for exp_, dte, rows in chains:
        out += [S.contract_row(c, spot, exp_, dte) for c in rows]
    return out

def test_choose_prefers_nine_months_then_open_interest():
    spot = 100.0
    oi = {80.0: 400, 82.5: 900, 77.5: 150}
    rows = contracts(spot, [("2027-06-18", 216, synth_chain(spot, 216, oi=oi)),
                            ("2027-08-20", 279, synth_chain(spot, 279, oi=oi)),
                            ("2028-01-21", 433, synth_chain(spot, 433, oi=oi))])
    opt, alt = S.choose_contract(rows, spot)
    assert opt["expiry"] == "2027-08-20"
    assert S.DELTA_LO <= opt["delta"] <= S.DELTA_HI
    band = [r for r in rows if r["expiry"] == "2027-08-20" and r["delta"] and S.DELTA_LO <= r["delta"] <= S.DELTA_HI]
    assert opt["open_interest"] == max(r["open_interest"] for r in band)
    assert opt["cost_usd"] == pytest.approx(opt["ask"]*100)
    assert opt["breakeven"] == pytest.approx(opt["strike"] + opt["ask"])
    assert opt["liquidity"] == ("ok" if opt["open_interest"] >= 100 and opt["spread_pct"] <= 8 else "thin")
    assert alt is None or opt["liquidity"] == "thin"

def test_thin_choice_gets_alt():
    spot = 100.0
    oi = {k: 20 for k in np.arange(50, 120, 2.5)}; oi[90.0] = 3000      # only a delta ~0.6-0.7 strike is liquid
    rows = contracts(spot, [("2027-08-20", 279, synth_chain(spot, 279, oi={round(float(k), 1): v for k, v in oi.items()}))])
    opt, alt = S.choose_contract(rows, spot)
    assert opt["liquidity"] == "thin"
    assert alt is not None and alt["strike"] == 90.0 and alt["liquidity"] == "ok"
    assert S.ALT_DELTA_LO <= alt["delta"] <= S.ALT_DELTA_HI

def test_wide_spread_is_thin():
    spot = 100.0
    rows = contracts(spot, [("2027-08-20", 279, synth_chain(spot, 279, oi={k: 5000 for k in np.round(np.arange(50, 120, 2.5), 1)}, spread=0.20))])
    opt, _ = S.choose_contract(rows, spot)
    assert opt["spread_pct"] > 8 and opt["liquidity"] == "thin"

def test_stale_quotes_never_priced():
    spot = 100.0
    rows = contracts(spot, [("2027-08-20", 279, synth_chain(spot, 279, zero=True))])
    assert all(r["quote"] == "stale" and r["spread_pct"] is None and r["mid"] is None for r in rows)
    opt, alt = S.choose_contract(rows, spot)
    assert opt == {"liquidity": "none", "quote": "stale"} and alt is None

def test_iv_solved_when_chain_iv_insane():
    spot = 100.0
    c = synth_chain(spot, 279)[8]; c["impliedVolatility"] = 0.00001
    r = S.contract_row(c, spot, "2027-08-20", 279)
    assert r["iv_source"] == "solved from mid" and r["iv"] == pytest.approx(0.35, abs=0.01)

def test_slot_fit_and_apply():
    assert S.slot_fit({"cost_usd": 1900}) is True
    assert S.slot_fit({"cost_usd": 2500}) == "stretch"
    assert S.slot_fit({"cost_usd": 3100}) is False
    assert S.slot_fit({"liquidity": "none"}) is None
    row = dict(ticker="X", tier="WATCH", reason="thin expectancy")
    S.apply_options(row, {"option": {"cost_usd": 4200.0, "liquidity": "ok"}})
    assert row["tier"] == "WATCH" and row["fits_slot"] is False and row["instrument"] == "shares, or a smaller position" and "$4,200" in row["reason"]
    row2 = dict(ticker="Y", tier="DEEP DIVE", reason="r")
    S.apply_options(row2, None)
    assert row2["fits_slot"] is None and row2["tier"] == "DEEP DIVE"


# ---------------------------------------------------------------- market cap floor and cache
def test_mcap_merge_and_floor():
    cache = {"values": {"OLD": {"usd": 7e9, "date": "2026-11-06"}, "STALE": {"usd": 9e9, "date": "2026-10-01"}, "A": {"usd": 1e9, "date": "2026-11-10"}}}
    vals, src, new = S.merge_mcap({"A": 3e9, "B": 2e10}, cache, dt.date(2026, 11, 14))
    assert vals == {"OLD": 7e9, "A": 3e9, "B": 2e10} and src["OLD"] == "cache" and src["A"] == "live"
    assert new["values"]["A"] == {"usd": 3e9, "date": "2026-11-14"}
    assert S.below_floor("A", vals) and not S.below_floor("B", vals) and not S.below_floor("NOPE", vals)

def test_option_targets_cap_and_order():
    ranked = [dict(ticker=f"R{i}", tier="WATCH") for i in range(30)] + [dict(ticker="P", tier="PASS")]
    lc = {"candidates": [dict(ticker=f"L{i}") for i in range(30)] + [dict(ticker="R1")]}
    t = S.option_targets(ranked, lc)
    assert len(t) == 40 and t[0] == "R0" and t[30] == "L0" and "P" not in t


# ---------------------------------------------------------------- SEC year-to-date -> quarters
def f(start, end, val, form, filed):
    return dict(start=start, end=end, val=val, form=form, filed=filed)

def test_ytd_to_quarters_june_fiscal_year():
    # Microsoft-style fiscal year Jul-Jun: Q1 3m, H1 6m, 9m, FY; plus a comparative repeat with a revision
    facts = [f("2024-07-01", "2024-09-30", 100, "10-Q", "2024-10-30"),
             f("2024-07-01", "2024-12-31", 250, "10-Q", "2025-01-29"),
             f("2024-07-01", "2025-03-31", 420, "10-Q", "2025-04-30"),
             f("2024-07-01", "2025-06-30", 600, "10-K", "2025-07-30"),
             f("2024-07-01", "2024-09-30", 101, "10-Q", "2025-10-29"),   # restated in next year's Q1 comparative
             f("2025-07-01", "2025-09-30", 190, "10-Q", "2025-10-29")]
    q = TP.facts_to_quarters(facts)
    assert q["2024-09-30"]["val"] == 101 and q["2024-09-30"]["filed"] == "2024-10-30" and q["2024-09-30"]["restated"]
    assert q["2024-12-31"]["val"] == 250-101 and q["2024-12-31"]["derived"]
    assert q["2025-03-31"]["val"] == 170
    assert q["2025-06-30"]["val"] == 180 and q["2025-06-30"]["form"] == "10-K"
    assert TP.cal_quarter("2024-07-01", "2024-09-30") == "2024 Q3"
    assert TP.cal_quarter("2025-04-01", "2025-06-30") == "2025 Q2"

def test_may_fiscal_year_maps_by_midpoint_and_unfiled_absent():
    # Oracle-style: quarters end Aug, Nov, Feb, May
    facts = [f("2025-06-01", "2025-08-31", 8500e6, "10-Q", "2025-09-10"),
             f("2025-06-01", "2025-11-30", 20500e6, "10-Q", "2025-12-12")]
    rows = TP.capex_rows("Oracle", "ORCL", {"PaymentsToAcquirePropertyPlantAndEquipment": facts})
    assert [(r["quarter"], r["capex_musd"]) for r in rows] == [("2025 Q3", 8500.0), ("2025 Q4", 12000.0)]
    assert all(r["capex_musd"] != 0 for r in rows)

def test_second_concept_fills_gaps_only():
    a = [f("2025-01-01", "2025-03-31", 10e6, "10-Q", "2025-05-01")]
    b = [f("2025-01-01", "2025-03-31", 99e6, "10-Q", "2025-05-01"), f("2025-04-01", "2025-06-30", 20e6, "10-Q", "2025-08-01")]
    rows = TP.capex_rows("Co", "CO", {"PaymentsToAcquirePropertyPlantAndEquipment": a, "PaymentsToAcquireProductiveAssets": b})
    assert [(r["quarter"], r["capex_musd"]) for r in rows] == [("2025 Q1", 10.0), ("2025 Q2", 20.0)]
    assert "ProductiveAssets" in rows[1]["note"]


# ---------------------------------------------------------------- Census sheet parser
def make_xlsx(grid):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    for r in grid: ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()

def months(n, start="2025-01"):
    return [p.strftime("%Y-%m") for p in pd.period_range(start, periods=n, freq="M")]

def test_census_parser_months_down():
    ms = pd.period_range("2024-10", "2026-09", freq="M")
    grid = [["Value of Private Construction Put in Place"], ["Seasonally adjusted annual rate, $ millions"], [],
            ["Date", "Total private", "Office", "Data center", "Commercial"]]
    for i, p in enumerate(ms):
        lab = p.to_timestamp().strftime("%b-%y") + ("p" if i == len(ms)-1 else "")
        dcv = 96462 if str(p) == "2026-09" else 50700 if str(p) == "2025-09" else 40000 + i*100
        grid.append([lab, 1_500_000, 60000, dcv if i != 3 else "(NA)", 100000])
    s = TP.series_from_xlsx(make_xlsx(grid))
    assert s["2026-09"] == 96462 and s["2025-09"] == 50700 and "2025-01" not in s and len(s) == len(ms)-1
    assert TP.tie_out(s) == []

def test_census_parser_months_across_and_tieout_failure():
    ms = months(24, "2024-10")
    grid = [["Type of construction"] + [dt.datetime.strptime(m, "%Y-%m") for m in ms],
            ["Office"] + [1]*24, ["Data center"] + [50000.0]*24]
    s = TP.series_from_xlsx(make_xlsx(grid))
    assert len(s) == 24
    bad = TP.tie_out(s)
    assert any("2026-09" in b for b in bad)

def test_parse_month_variants():
    assert TP.parse_month("Sep-26") == "2026-09" and TP.parse_month("Sept. 2026p") == "2026-09"
    assert TP.parse_month("September 2025") == "2025-09" and TP.parse_month("2026-09") == "2026-09"
    assert TP.parse_month("Data center") is None and TP.parse_month(dt.datetime(2026, 9, 1)) == "2026-09"


# ---------------------------------------------------------------- terminal screen file
def test_terminal_screen_size_and_fields():
    ranked = [dict(ticker=f"T{i}", tier="PASS" if i > 5 else "WATCH", reason="x"*50, option={"liquidity": "ok", "strike": 10}) for i in range(80)]
    lc = {"verdicts": {"SHARE_SHRINK": "DROP"}, "candidates": [dict(ticker=f"L{i}", lenses=["SHARE_SHRINK"]) for i in range(30)]}
    s = S.terminal_screen("2026-11-13", "note", ranked, lc)
    d = json.loads(s)
    assert len(s) < 150_000 and len(d["rows"]) == 80 and len(d["lens_candidates"]) == 15
    assert d["tiers"] == {"WATCH": 6, "PASS": 74} and set(S.SCREEN_FIELDS) == set(d["rows"][0])
    assert d["lens_candidates"][0]["lenses"] == [{"lens": "SHARE_SHRINK", "verdict": "DROP"}]

def test_third_friday():
    assert S.third_friday(pd.Timestamp("2027-01-15")) and not S.third_friday(pd.Timestamp("2027-01-22"))
