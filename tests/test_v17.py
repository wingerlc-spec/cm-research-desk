"""Offline tests for v17 datasets.py (no network). Run: python -m pytest -q tests"""
import gzip, sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import datasets as D  # noqa: E402


def test_snapshot_append_and_dedup(tmp_path):
    a = pd.DataFrame([dict(date="2026-11-13", ticker="AAA", x=1), dict(date="2026-11-13", ticker="BBB", x=2), dict(date="2026-10-31", ticker="AAA", x=0)])
    assert D.append_snapshot(tmp_path, a) == 3
    b = pd.DataFrame([dict(date="2026-11-13", ticker="AAA", x=9), dict(date="2026-11-14", ticker="AAA", x=3)])
    D.append_snapshot(tmp_path, b)
    assert sorted(p.name for p in tmp_path.glob("*.csv.gz")) == ["2026-10.csv.gz", "2026-11.csv.gz"]
    h = D.read_history(tmp_path)
    assert len(h) == 4
    assert h[(h.date == "2026-11-13") & (h.ticker == "AAA")].x.item() == 9
    with gzip.open(tmp_path/"2026-11.csv.gz", "rt") as fh: assert fh.readline().startswith("date,ticker")

def test_rotation_slice_covers_everyone_weekly():
    names = [f"T{i}" for i in range(500)]
    parts = [set(D.rotation_slice(names, d)) for d in range(5)]
    assert set().union(*parts) == set(names) and sum(len(p) for p in parts) == 500
    assert D.rotation_slice(names, 5) == D.rotation_slice(names, 0)
    cov = D.coverage(["CORE1", "T3"], names, 2, 50)
    assert cov[:2] == ["CORE1", "T3"] and len(cov) == 50 and len(set(cov)) == 50

def test_iv_rank_building_then_ranked():
    rows = [dict(date=f"2026-{1+i//28:02d}-{1+i%28:02d}", ticker="AAA", iv_atm_30d=0.2 + i*0.001) for i in range(70)]
    rows += [dict(date="2026-11-13", ticker="BBB", iv_atm_30d=0.5)]
    out = {r["ticker"]: r for r in D.iv_rank_table(pd.DataFrame(rows), "2026-11-13")}
    assert out["AAA"]["iv_rank"] == pytest.approx(69/70*100, abs=0.1)
    assert out["BBB"]["status"] == "building, 1 days" and "iv_rank" not in out["BBB"]

def test_buyback_rule_and_ttm():
    assert D.buyback_pass(10e9, 0.6e9, -5, 8) and not D.buyback_pass(10e9, 0.4e9, -5, 8)
    assert not D.buyback_pass(10e9, 0.6e9, -3, 8) and not D.buyback_pass(10e9, 0.6e9, -5, 13) and not D.buyback_pass(4e9, 0.6e9, -5, 8)
    assert not D.buyback_pass(10e9, 0.6e9, -5, -4)
    f = lambda s, e, v, form="10-Q", filed="2026-01-01": dict(start=s, end=e, val=v, form=form, filed=filed)
    facts = [f("2025-01-01", "2025-03-31", 100), f("2025-01-01", "2025-06-30", 250), f("2025-01-01", "2025-09-30", 400),
             f("2025-01-01", "2025-12-31", 600, "10-K"), f("2026-01-01", "2026-03-31", 120), f("2026-01-01", "2026-06-30", 300),
             f("2026-01-01", "2026-09-30", 450)]
    r = D.ttm_from_facts(facts, "2026-11-14")
    assert r["value"] == pytest.approx(200 + 120 + 180 + 150) and r["last_end"] == "2026-09-30"
    assert D.ttm_from_facts(facts, "2027-11-14") is None                      # too old

def test_shares_yoy_sums_classes():
    sh = [dict(end="2025-10-20", val=100, accn="a1"), dict(end="2025-10-20", val=50, accn="a1"),
          dict(end="2026-10-20", val=90, accn="b1"), dict(end="2026-10-20", val=45, accn="b1"), dict(end="2026-07-20", val=140, accn="c1")]
    r = D.shares_yoy(sh)
    assert r["now"] == 135 and r["year_ago"] == 150 and r["change_pct"] == -10.0

def bars_with_drop(n=260, k=150, drop=0.15, volx=4.0, recover=True):
    c = np.full(n, 100.0); v = np.full(n, 1e6)
    c[k:] = 100*(1-drop); v[k] = volx*1e6
    if recover:
        for i in range(k+1, n): c[i] = min(100.5, c[i-1] + 1.0)
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.Series(c, idx), pd.Series(v, idx)

def test_drop_event_detection_thresholds():
    c, v = bars_with_drop()
    assert D.drop_events(c, v) == [150]
    c2, v2 = bars_with_drop(volx=2.0); assert D.drop_events(c2, v2) == []
    c3, v3 = bars_with_drop(drop=0.08); assert D.drop_events(c3, v3) == []

def test_gap_recovery_math():
    c, v = bars_with_drop()                     # gap 15, +1 a day from 85
    g = D.gap_recovery(c, 150)
    assert g["rec5"] == pytest.approx(5/15) and g["rec10"] == pytest.approx(10/15)
    assert g["closed60"] and g["days_to_close"] == 15 and g["two_thirds_day"] == 10
    c2, _ = bars_with_drop(recover=False); g2 = D.gap_recovery(c2, 150)
    assert g2["rec60"] == 0 and not g2["closed60"] and g2["two_thirds_day"] is None

def test_rotation_table_rank_change():
    idx = pd.bdate_range("2025-01-01", periods=200)
    spy = pd.Series(np.linspace(100, 110, 200), idx)
    up_late = np.r_[np.full(185, 50.0), np.linspace(50, 70, 15)]            # improving group
    flat = np.full(200, 50.0)
    down_late = np.r_[np.linspace(20, 60, 170), np.linspace(60, 50, 30)]
    closes = pd.DataFrame({"A1": up_late, "A2": up_late*1.01, "B1": flat, "C1": down_late}, index=idx)
    rt = D.rotation_table(closes, {"A": ["A1", "A2"], "B": ["B1"], "C": ["C1"]}, spy)
    assert rt.iloc[0]["group"] == "A" and rt.iloc[0]["rank_now"] == 1 and rt.iloc[0]["rank_change"] > 0
    assert rt.set_index("group").loc["A", "pct_above_50d"] == 100.0
    assert D.not_extended(105, 100) and not D.not_extended(110, 100) and D.not_extended(93, 100)

def test_driver_residual_z():
    rng = np.random.default_rng(1); n = 300
    m = rng.normal(0, 0.01, n); p = rng.normal(0, 0.02, n); e = rng.normal(0, 0.005, n)
    y = 0.001 + 0.8*m + 0.5*p + e
    r = D.driver_fit(y, m, p, 250)
    assert r["beta"] == pytest.approx(0.5, abs=0.05) and abs(r["z20"]) < 3 and r["r2"] > 0.5
    y2 = y.copy(); y2[-20:] += 0.01                                          # diverges 1% a day for 20 days
    assert D.driver_fit(y2, m, p, 250)["z20"] > 5
    assert D.driver_fit(y[:100], m[:100], p[:100], 250) is None

def test_reaction_picks_higher_volume_day():
    idx = pd.bdate_range("2026-01-01", periods=40)
    c = pd.Series(100.0, idx); v = pd.Series(1e6, idx)
    c.iloc[31:] = 110.0; v.iloc[31] = 5e6                                   # reported after close on day 30, reacted on day 31
    r = D.reaction(c, v, idx[30])
    assert r["reaction_date"] == str(idx[31].date()) and r["move_pct"] == 10.0 and r["volx"] == 5.0 and r["move5_pct"] == 10.0

def test_clusters_and_form4_parse():
    xml = """<ownershipDocument><reportingOwner><reportingOwnerId><rptOwnerCik>0001</rptOwnerCik><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId></reportingOwner>
    <nonDerivativeTable><nonDerivativeTransaction><transactionDate><value>2026-11-02</value></transactionDate><transactionCoding><transactionCode>P</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>1000</value></transactionShares><transactionPricePerShare><value>50.5</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction>
    <nonDerivativeTransaction><transactionDate><value>2026-11-03</value></transactionDate><transactionCoding><transactionCode>S</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>9</value></transactionShares><transactionPricePerShare><value>1</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""
    assert D.parse_form4(xml) == [("Doe Jane", "0001", "2026-11-02", 1000.0, 50.5)]
    b = pd.DataFrame([dict(ticker="X", owner=f"O{i}", owner_cik=str(i), date="2026-11-01", shares=4000, price=50.0) for i in range(3)]
                     + [dict(ticker="Y", owner="O1", owner_cik="1", date="2026-11-01", shares=1e6, price=50.0)]
                     + [dict(ticker="Z", owner=f"O{i}", owner_cik=str(i), date="2026-08-01", shares=1e5, price=50.0) for i in range(3)])
    cl = D.clusters(b, "2026-11-14")
    assert [r["ticker"] for r in cl] == ["X"] and cl[0]["total_usd"] == 600000 and cl[0]["n_insiders"] == 3

def test_clustered_diff_and_verdict():
    rng = np.random.default_rng(3); n = 600
    flag = rng.integers(0, 2, n); g = rng.integers(0, 60, n)
    y = 40 + 20*flag + rng.normal(0, 10, n)
    b, t = D.clustered_diff(y, flag, g)
    assert b == pytest.approx(20, abs=3) and t > 5 and D.verdict(b, t) == "WORKS"
    assert D.verdict(-1, -2.5) == "HURTS" and D.verdict(1, 1.0) == "NOT SHOWN" and D.verdict(1, None) == "NOT SHOWN"


def test_regime_states_and_overall():
    assert D.trend_state(90, 95, 100, -10) == "stress" and D.trend_state(101, 102, 100, -2) == "caution"
    assert D.trend_state(110, 105, 100, -8) == "caution" and D.trend_state(110, 105, 100, -3) == "ok"
    assert D.breadth_state(30) == "stress" and D.breadth_state(45) == "caution" and D.breadth_state(60) == "ok"
    assert D.credit_state(0.9, 1.0, 1.0, -0.01) == "stress" and D.credit_state(0.9, 1.0, 1.0, 0.01) == "caution"
    assert D.vix_state(20, 19) == "stress" and D.vix_state(26, 28) == "caution" and D.vix_state(15, 18) == "ok"
    assert D.overall(["stress", "stress", "ok"]) == "red" and D.overall(["stress", "ok"]) == "yellow"
    assert D.overall(["caution"]*3) == "yellow" and D.overall(["caution", "caution", "ok"]) == "green"

def test_threshold_clusters_chain():
    C = {"A": {"B": 0.7, "C": 0.2}, "B": {"A": 0.7, "C": 0.65}, "C": {"A": 0.2, "B": 0.65}, "D": {}}
    lab, comps = D.threshold_clusters(C, ["A", "B", "C", "D"])
    assert comps[0] == ["A", "B", "C"] and lab["A"] == (1, 3) and lab["D"] == (2, 1)

def test_beta():
    rng = np.random.default_rng(5); x = rng.normal(0, 0.01, 500); y = 1.5*x + rng.normal(0, 0.002, 500)
    assert D.beta(y, x) == pytest.approx(1.5, abs=0.05)
